# Week 3: Citation Intelligence - Velocity Tracking

**Goal:** Surface papers gaining research momentum

**Time:** 10-12 hours  
**Cost:** $10-20  
**Deliverable:** Email highlights "fastest growing papers this week"

---

## Day 1 (Saturday): Semantic Scholar Integration (3-4 hours)

### Tasks

- [ ] Set up Semantic Scholar API client
- [ ] Register for API key (optional, increases rate limit)
- [ ] Implement batch citation fetcher
- [ ] Convert arXiv IDs to S2 paper IDs
- [ ] Fetch: total citations, citing papers, references
- [ ] Create Citation model
- [ ] Track citation_count over time
- [ ] Save citation history to database

### Files to Create

- `src/services/semantic_scholar.py`
- `src/models/citation.py`
- `src/agents/discovery/citation_tracker.py`
- `migrations/003_add_citations.sql`

### Semantic Scholar API

- Free tier: 100 requests/5min
- With key: 5000 requests/5min
- Batch: Up to 500 IDs per request

### Acceptance Criteria

✅ Can fetch citations in batches  
✅ Citation data saved to DB  
✅ Historical tracking works

---

## Day 2 (Sunday Morning): Citation Velocity Calculation (3-4 hours)

### Tasks

- [ ] Implement velocity algorithm
- [ ] velocity = (this_week - last_week) / total
- [ ] Normalize to 0-1 scale
- [ ] Identify "breakout papers"
  - New papers (<1 month) with >5 citations/week
  - Established papers with >20% velocity
- [ ] Add velocity_score to Paper model
- [ ] Update scoring algorithm (20% weight)

### Files to Update

- `src/agents/curator.py` - Add citation component
- `src/models/paper.py` - Add velocity fields

### Breakout Detection

Flag papers with:
- High velocity (>20%)
- Recent publication (<30 days)
- Minimum citation threshold (>5/week)

### Acceptance Criteria

✅ Velocity calculated correctly  
✅ Breakout papers identified  
✅ Scoring includes citations (20%)

---

## Day 3 (Sunday Afternoon): Paper Relationships (2-3 hours)

### Tasks

- [ ] Build citation graph
- [ ] Paper X cites Paper Y → directed edge
- [ ] Extract from Semantic Scholar references
- [ ] Create PaperRelationship model
- [ ] Types: "cites", "cited_by"
- [ ] Store relationship strength
- [ ] Identify paper clusters

### Files to Create

- `src/models/paper_relationship.py`
- `src/services/graph_builder.py`
- `migrations/004_add_relationships.sql`

### Graph Structure

Directed graph where edges represent citations. Used for:
- Finding influential papers
- Detecting topic clusters
- Building reading paths (Week 4)

### Acceptance Criteria

✅ Citation graph built from DB  
✅ Relationships stored  
✅ Can identify clusters

---

## Day 4 (Weeknight): Email Enhancements (1-2 hours)

### Tasks

- [ ] Update email template
- [ ] Show citation count + velocity
- [ ] Add "📈 +45% citations this week"
- [ ] Add "🔥 Breakout paper alert!"
- [ ] Create "Trending Papers" section
- [ ] Separate from regular papers
- [ ] Explain why they're trending

### Files to Update

- `src/templates/email_digest.html`
- `src/agents/curator.py` - Separate trending section

### Email Sections

1. **Trending This Week** (3 papers)
   - High velocity papers
   - Citation stats visible
   
2. **Top Papers** (5 papers)
   - Standard ranked by all signals

### Acceptance Criteria

✅ Citation velocity visible  
✅ Trending section works  
✅ Breakout alerts show

---

## Day 5 (Weeknight): Scheduled Automation (1-2 hours)

### Tasks

- [ ] Add cron job scheduler (APScheduler)
- [ ] Run discovery daily at 8am
- [ ] Send digest at 9am
- [ ] Create systemd service (Linux) or launchd (Mac)
- [ ] Add logging for monitoring

### Files to Create

- `src/scheduler.py`
- `scripts/install_service.sh`
- `config/arxiv_assistant.service` (systemd)

### Scheduling

```python
# Daily at 8am: discover papers
# Daily at 9am: send digest
# Sunday 6pm: weekly summary (Week 6)
```

### Test

```bash
python main.py --schedule-daily
```

### Acceptance Criteria

✅ Scheduler runs tasks automatically  
✅ Logs capture activity  
✅ Can be stopped/started as service

---

## Week 3 Acceptance Criteria

- ✅ Fetches citation counts from Semantic Scholar
- ✅ Calculates citation velocity
- ✅ Identifies breakout papers
- ✅ Builds paper citation relationships
- ✅ Email shows trending papers
- ✅ Runs automatically every morning

---

## Troubleshooting

**Semantic Scholar rate limits:**
- Get API key for higher limits
- Use batch requests (500 at a time)

**Velocity calculation errors:**
- Handle division by zero
- Check for missing historical data

**Scheduler not running:**
- Check service is enabled
- View logs: `journalctl -u arxiv-assistant`

---

## Code Checkpoint

```bash
git commit -m "Week 3: Citation velocity and automated scheduling"
git tag week3-citations
```

---

[← Week 2](week2.md) | [Week 4 →](week4.md)
