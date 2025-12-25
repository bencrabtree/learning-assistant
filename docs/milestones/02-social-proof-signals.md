# Milestone 2: Social Proof & Community Signals

## The Ideal

Identify papers that matter **right now** - before citations accumulate - by monitoring where the research community discusses and shares papers.

## The Problem

- **Citation lag:** Papers take months to accumulate citations
- **Missing early signals:** Important papers start trending on Twitter/HN before academic citations appear
- **Noise filtering:** Need to know what the community is actually excited about, not just what's published

## The Solution

Aggregate social signals from multiple sources where researchers actively discuss papers:

1. **Twitter/X:** Monitor AI lab accounts and researcher discussions
2. **HackerNews:** Track arXiv links on front page and "Show HN"
3. **Lab websites:** Identify official lab releases (higher prestige signal)

## Core Capabilities

### Twitter Tracker

**Monitors:**
- AI lab accounts (@AnthropicAI, @OpenAI, @GoogleDeepMind, etc.)
- Researcher accounts (configurable list)
- Hashtags (#arXiv, #MachineLearning)

**Extracts:**
- arXiv links from tweets
- Engagement metrics (likes, retweets, replies)
- Author prestige (follower count)

**Signals:**
- 🐦 **Lab mention:** Official lab account shared the paper
- 🔥 **Viral:** > 100 likes or 50 retweets
- 💬 **Discussion:** > 20 replies (indicates controversy/interest)

### HackerNews Tracker

**Uses:** Algolia Search API (no rate limits)

**Searches for:**
- arXiv links in HN stories
- Front page posts (higher signal)
- "Show HN" posts (community submissions)

**Extracts:**
- HN score (upvotes)
- Comment count
- Time on front page

**Signals:**
- 🎯 **Front page:** Made it to HN front page
- 🏆 **Top 10:** Reached top 10 on HN
- 💭 **Active discussion:** > 50 comments

### Lab Website Tracker

**Scrapes:**
- /research or /publications pages of major labs
- Official arXiv accounts (some labs have dedicated feeds)

**Extracts:**
- Publication announcements
- Lab affiliation
- Release notes/blog posts

**Signals:**
- 🏛️ **Official release:** Lab's official publication page
- 🌟 **Featured:** Highlighted on lab homepage

## Scoring Algorithm

Multi-signal weighted scoring (0-1 scale):

```
total_score = (
    interest_match * 0.40 +      # User research interests
    social_proof * 0.30 +         # Twitter + HN engagement
    recency * 0.30               # How recent (decay over 30 days)
)
```

**Social proof breakdown:**
- Lab mention: +0.3
- HN front page: +0.25
- Viral Twitter: +0.2
- Active HN discussion: +0.15
- Official lab release: +0.1

## User Experience

### Email Digest Enhancements

**Social badges:**
- 🔥 **Trending:** High social proof score
- 🐦 **Lab mention:** Official lab shared
- 🎯 **HN front page:** Top HN discussion

**Sorted by:**
1. Social proof score (descending)
2. Recency (tie-breaker)

**Sections:**
- "Hot Papers" (social proof > 0.7)
- "Rising" (social proof 0.5-0.7)
- "Worth watching" (social proof 0.3-0.5)

## Technical Architecture

```
┌─────────────────────────────────────────┐
│     Parallel Social Trackers            │
│  ┌─────────┬──────────┬──────────┐      │
│  │ Twitter │ HackerN  │ Lab Sites│      │
│  └─────────┴──────────┴──────────┘      │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│      Signal Aggregation                 │
│  (Dedupe by arXiv ID, merge signals)    │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│     SocialSignal Table                  │
│  (source, url, score, posted_at)        │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│     Enhanced Scoring                    │
│  (Interest + Social Proof + Recency)    │
└─────────────────────────────────────────┘
```

## Database Schema

### SocialSignal Model

```python
class SocialSignal:
    paper_id: str              # Foreign key to Paper
    source: str                # "twitter", "hackernews", "lab_website"
    source_url: str            # Link to original post
    score: float               # Engagement metric (0-1)
    comments_count: int        # Number of comments/replies
    snippet: str               # Preview text
    author: str                # Who shared it
    posted_at: datetime        # When it was posted
    discovered_at: datetime    # When we found it
```

## Success Metrics

- **Leading indicator:** Identify papers 7-14 days before citation counts rise
- **Precision:** 70%+ of "hot papers" receive > 20 citations within 6 months
- **Latency:** Social signals collected within 1 hour of posting
- **Coverage:** Monitor 50+ AI lab accounts and top HN posts daily

## What This Enables

**Builds on Milestone 1:**
- Uses analyzed papers (main_claim, concepts) for interest matching
- Enriches papers with social proof scores

**Enables future milestones:**
- Citation velocity (M3) can cross-reference: did social buzz predict citation growth?
- Knowledge graphs (M4) can size nodes by social proof
- Progress tracking (M5) can prioritize "hot papers" for reading recommendations

## Key Decisions

### Why Twitter/HN Over Reddit/Forums?

**Signal quality:**
- Twitter: Researchers and lab accounts have verified prestige
- HN: Technical community with good signal-to-noise
- Reddit: Higher noise, harder to extract clean signals

**Future expansion:** Can add Reddit/forums later if signal quality proves valuable

### Why Real-time Tracking vs Daily Batch?

**Hybrid approach:**
- HN: API queries every 6 hours (good enough for HN's pace)
- Twitter: Stream API for real-time lab mentions (higher value)
- Lab sites: Daily scrape (they update infrequently)

**Why:** Balance freshness with API rate limits and cost

### Why Weight Social Proof at 30%?

**Balanced approach:**
- Interest match (40%): Still primary - papers must be relevant
- Social proof (30%): Important signal, but not dominant
- Recency (30%): Freshness matters

**Tunable:** Users can adjust weights in config

## What's Next

After this milestone, we identify papers with community excitement. Next milestone adds **citation velocity** to detect papers gaining research momentum over time.
