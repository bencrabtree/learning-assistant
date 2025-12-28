# Milestone 5: Citation Velocity & Trend Detection

**Status:** Planned
**Priority:** Medium
**Dependencies:** Milestone 4 (Agentic LangGraph)

## The Ideal

Get ahead of research trends by reading papers **before they become canonical** - identify which papers are gaining momentum in the research community.

## The Problem

- **Static citations mislead:** A paper with 10 citations could be dead or just getting started
- **Can't predict impact:** Citation *count* doesn't show if a paper is becoming important
- **Miss emerging trends:** Papers entering the conversation are invisible in static metrics

## The Solution

Track citation **velocity** (rate of change) rather than just counts:

1. **Historical tracking:** Store citation counts over time
2. **Velocity calculation:** Citations this week - citations last week
3. **Breakout detection:** Flag papers with unusual acceleration
4. **Trend analysis:** Identify papers entering the research conversation

## Core Capabilities

### Semantic Scholar Integration

**API Usage:**
- Batch fetch citations (up to 500 paper IDs per request)
- Rate limit: 100 req/5min (no key) or 5000 req/5min (with key)
- Data: citation count, influential citations, references

**Caching Strategy:**
- 24-hour cache for citation data (citations don't change hourly)
- Refresh daily at 8am
- Historical snapshots stored in database

### Velocity Algorithm

**Simple velocity (per week):**
```python
velocity = (citations_this_week - citations_last_week) / max(total_citations, 1)
```

**Normalized to 0-1:**
- 0.0: No growth
- 0.5: Moderate growth (10% increase)
- 1.0: Explosive growth (100%+ increase)

**Smoothing:**
- 7-day moving average to reduce noise
- Ignore single-day spikes

### Breakout Detection

**Criteria for "breakout papers":**

**New papers (< 1 month):**
- \> 5 citations/week absolute growth
- Velocity > 0.8 (80% week-over-week growth)

**Established papers (> 1 month):**
- \> 20% velocity growth
- Sustained over 2+ weeks

**Signals:**
- 📈 **Rising:** Velocity > 0.5
- 🚀 **Breakout:** Velocity > 0.8
- ⭐ **Established:** > 100 citations + still growing

### Citation Graph

**Build relationships:**
- Node = Paper
- Edge = Citation (Paper A cites Paper B)
- Edge weight = Relevance (how central the citation is)

**Graph queries:**
- "What papers cite this one?" (forward citations)
- "What papers does this cite?" (backward citations)
- "What are the most influential papers in this subgraph?"

## User Experience

### Email Digest: Trending Section

**"Trending This Week":**
- Papers ranked by citation velocity
- Show: title, velocity score, absolute citation growth
- Badge: 📈 Rising, 🚀 Breakout, ⭐ Established

**"Worth Revisiting":**
- Papers you read 1-2 months ago that are now trending
- Suggests re-reading to see what sparked the interest

### CLI Commands

```bash
# Show trending papers
python main.py --trending --days 7

# Show citation velocity for specific paper
python main.py --velocity --arxiv-id 2312.12345

# Find papers citing this one
python main.py --citations-of 2312.12345
```

## Technical Architecture

```
┌─────────────────────────────────────────┐
│    Daily Citation Refresh (8am)         │
│  (Semantic Scholar Batch API)           │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│     Citation History Table              │
│  (paper_id, count, measured_at)         │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│      Velocity Calculation               │
│  (week-over-week delta)                 │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│    Breakout Detection                   │
│  (flag papers with high velocity)       │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│   Enhanced Paper Scoring                │
│  (add velocity to scoring mix)          │
└─────────────────────────────────────────┘
```

## Database Schema

### Citation Model

```python
class Citation:
    id: int                    # Auto-increment PK
    paper_id: str              # Foreign key to Paper
    citation_count: int        # Total citations
    measured_at: datetime      # When we measured
    citations_this_week: int   # New citations in past 7 days
    velocity_score: float      # Normalized velocity (0-1)
    source: str                # "semantic_scholar"
```

**Indexes:**
- (paper_id, measured_at) for time-series queries
- velocity_score for trending queries

## Success Metrics

- **Predictive power:** Papers with high velocity receive 2x more citations in next 30 days
- **Lead time:** Identify trending papers 14-21 days before they hit 100 citations
- **Coverage:** Track citations for 95%+ of discovered papers
- **Freshness:** Citation data updated daily

## What This Enables

**Builds on previous milestones:**
- M1 (Analysis): Needs analyzed papers to track citations for
- M2 (Social Signals): Can cross-validate - do social signals predict citation velocity?
- M3-M4 (Radar & Agentic): Integrates velocity into discovery workflow

**Enables future milestones:**
- M6 (Knowledge Graph): Use citation edges to build relationship graph
- M7 (Progress Tracking): Recommend trending papers you haven't read yet
- M8 (Synthesis): Identify emerging trends across multiple trending papers

## Key Decisions

### Why Weekly Velocity vs Daily?

**Noise reduction:**
- Daily citation changes are too volatile
- Weekly smooths out weekend/weekday patterns
- Matches researcher behavior (weekly paper reading)

**Future:** Can add daily velocity for very recent papers if needed

### Why Semantic Scholar vs Google Scholar?

**API access:**
- Semantic Scholar: Full API with batch operations
- Google Scholar: No official API, requires scraping

**Data quality:**
- Semantic Scholar: Structured, clean, citation context
- Google Scholar: More coverage but harder to parse

**Future:** Can add CrossRef or OpenAlex as additional sources

### Why Store Historical Snapshots?

**Essential for velocity:**
- Can't calculate velocity without historical data
- Enables time-series analysis (seasonal patterns, etc.)
- Supports "rewind" queries ("what was trending 6 months ago?")

**Storage cost:**
- ~1KB per paper per day = 365KB per paper per year
- For 10K papers = 3.6GB per year (manageable)

## What's Next

After this milestone, we identify papers gaining research momentum. Next milestone adds **visual knowledge graphs** to show how papers connect and what reading path to take.
