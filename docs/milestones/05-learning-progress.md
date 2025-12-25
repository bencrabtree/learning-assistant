# Milestone 5: Learning Progress & Personalization

## The Ideal

Researchers have a **personalized learning path** that builds systematically on what they know, tracks their progress, and recommends what to read next based on their specific journey.

## The Problem

- **No progress visibility:** Can't see how much you've learned or how far you've come
- **No personalization:** Everyone gets the same recommendations
- **No concept mastery tracking:** Don't know which concepts you understand deeply vs superficially
- **No habit reinforcement:** No streaks, goals, or motivation to keep reading

## The Solution

Create a comprehensive **learning progress system** that:

1. **Tracks reading journey** (what, when, how long, ratings)
2. **Monitors concept mastery** (beginner → intermediate → advanced)
3. **Generates personalized recommendations** (build on what you know)
4. **Visualizes progress** (stats, streaks, achievements)

## Core Capabilities

### Reading Progress Tracking

**Track for each paper:**
- `status`: unread, reading, finished, archived
- `started_at`: When you began reading
- `finished_at`: When you completed it
- `time_spent_minutes`: Estimated reading time
- `rating`: 1-5 stars (optional)
- `notes`: Personal annotations

**Session logging:**
- Track reading sessions with start/end times
- Calculate average reading speed
- Identify peak reading hours

### Statistics Dashboard

**Reading metrics:**
- **Papers read:** Per day/week/month/year
- **Time invested:** Total hours spent reading
- **Reading streak:** Consecutive days with activity
- **Reading velocity:** Papers per week (trend over time)

**Topic analysis:**
- **Favorite topics:** Based on papers read and rated highly
- **Topic distribution:** Pie chart of categories
- **Emerging interests:** New topics you're exploring

**Author tracking:**
- **Favorite authors:** Most-read researchers
- **Author follow:** Get notified when they publish

### Concept Mastery Tracking

**Mastery levels:**
- **Beginner (1-2 papers):** Awareness, basic understanding
- **Intermediate (3-5 papers):** Solid grasp, can explain
- **Advanced (6+ papers):** Deep expertise, can apply

**Concept map:**
- Extract concepts from all read papers
- Count papers per concept
- Visualize as heatmap (color by mastery level)

**Concept relationships:**
- "Understanding X requires understanding Y" (prerequisites)
- "X and Y are related concepts" (siblings)

### Personalized Recommendations

**"Next to Read" algorithm:**

```python
def recommend_next_papers(user_progress):
    """Personalized recommendations based on learning journey."""

    # 1. Find concepts you've mastered
    mastered = concepts with intermediate/advanced mastery

    # 2. Find papers building on those concepts
    candidates = papers citing/using mastered concepts

    # 3. Filter by prerequisites
    readable = candidates where all prerequisites are mastered

    # 4. Score by:
    #    - Builds on what you know (40%)
    #    - High PageRank/social proof (30%)
    #    - Matches interests (20%)
    #    - Recent/trending (10%)

    # 5. Return top 10
    return sorted(readable, key=score, reverse=True)[:10]
```

**"Fill Knowledge Gaps":**
- Identify concepts mentioned in 5+ papers you haven't mastered
- Recommend foundational papers for those concepts
- "You've read about [transformers] 8 times but only have basic understanding. Try these papers..."

**"Related Papers":**
- Find papers similar to ones you rated 4-5 stars
- Embedding similarity or citation overlap
- "You loved [Paper A], you might also like..."

### Habit Reinforcement

**Streaks:**
- Daily reading streak counter
- Weekly goal (e.g., "Read 3 papers per week")
- Celebrate milestones (10-day streak, 50 papers read)

**Achievements:**
- 🏆 **First Paper:** Read your first paper
- 🔥 **Week Streak:** 7 days in a row
- 📚 **Voracious:** 50 papers read
- 🎓 **Expert:** Advanced mastery in 5+ concepts
- 🌟 **Trendsetter:** Read 10 trending papers early

## User Experience

### Multi-Page Dashboard

**Page 1: Overview**
- Reading stats (today, this week, all-time)
- Current streak
- Papers in progress
- Quick actions (mark as read, rate)

**Page 2: Knowledge Map**
- Heatmap of concept mastery
- Click concept → See papers you've read
- Identify knowledge gaps

**Page 3: Recommendations**
- "Next to Read" (10 personalized suggestions)
- "Fill Gaps" (concepts to deepen)
- "Related" (similar to papers you loved)

**Page 4: Reading History**
- Chronological list of all read papers
- Filter by date, topic, rating
- Export reading list

**Page 5: Statistics**
- Line chart: Papers per week over time
- Pie chart: Topic distribution
- Bar chart: Time spent by category
- Heatmap: Reading activity (calendar view)

## Technical Architecture

```
┌─────────────────────────────────────────┐
│    ReadingProgress Table                │
│  (paper_id, status, ratings, notes)     │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│    Concept Extraction                   │
│  (from analyzed papers)                 │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│   Concept Mastery Calculation           │
│  (count papers per concept)             │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│  Recommendation Engine                  │
│  (ML-based or rule-based)               │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│    Streamlit Dashboard                  │
│  (visualizations + interactions)        │
└─────────────────────────────────────────┘
```

## Database Schema

### ReadingProgress Model

```python
class ReadingProgress:
    paper_id: str              # PK, FK to Paper
    status: str                # "unread", "reading", "finished", "archived"
    started_at: datetime | None
    finished_at: datetime | None
    time_spent_minutes: int | None
    rating: int | None         # 1-5 stars
    notes: str | None          # Personal annotations
```

### ConceptMastery Model (optional)

```python
class ConceptMastery:
    concept: str               # PK (e.g., "transformers")
    paper_count: int           # # of papers read on this concept
    mastery_level: str         # "beginner", "intermediate", "advanced"
    last_updated: datetime
```

## Success Metrics

- **Engagement:** 60%+ of read papers are rated
- **Streaks:** 30%+ of users maintain 7+ day reading streak
- **Recommendation accuracy:** 40%+ of "Next to Read" suggestions are actually read
- **Knowledge gaps filled:** 50%+ of "Fill Gaps" suggestions lead to reading
- **Progress visibility:** Users can answer "What have I learned this month?"

## What This Enables

**Builds on previous milestones:**
- M1 (Analysis): Tracks which analyzed papers you've read
- M2 (Social Signals): Can recommend trending papers you haven't read
- M3 (Citation Velocity): Can suggest re-reading papers that are now trending
- M4 (Knowledge Graph): Visualize progress (% of graph read, color by status)

**Enables next milestone:**
- M6 (Synthesis): Uses reading history to generate weekly insights

## Key Decisions

### Why Track Time Spent?

**Learning insights:**
- Helps estimate how long papers take to read
- Can recommend papers that fit your available time
- Understand your reading speed trends

**Not perfect:** Time tracking is estimated (start to finish), not active reading time

### Why 1-5 Star Ratings?

**Simple and familiar:**
- Everyone understands star ratings
- Quick to provide (low friction)
- Easy to aggregate (average rating)

**Alternative considered:** Like/dislike (binary) - less nuanced

### Why Three Recommendation Types?

**Different needs:**
- "Next to Read": Systematic learning path (build on what you know)
- "Fill Gaps": Address weaknesses (concepts you're missing)
- "Related": Serendipity (discover adjacent areas)

**Together:** Cover exploration (Related) and exploitation (Next/Gaps) trade-off

### Why Rule-Based vs ML Recommendations?

**Start simple:**
- Rule-based is transparent and debuggable
- Works with small amounts of data
- No training required

**Future enhancement:**
- Collect user feedback on recommendations
- Train embedding model or collaborative filtering
- A/B test rule-based vs ML

## What's Next

After this milestone, we have personalized learning paths. Final milestone adds **weekly synthesis** to consolidate insights and **production automation** for hands-off operation.
