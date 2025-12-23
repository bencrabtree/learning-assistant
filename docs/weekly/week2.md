# Week 2: Social Signals - Twitter & HackerNews

**Goal:** Enhance discovery with social proof signals

**Time:** 10-12 hours  
**Cost:** $5-15  
**Deliverable:** Email prioritizes "hot" papers with Twitter/HN mentions

---

## Day 1 (Saturday): Twitter Tracker (3-4 hours)

### Tasks

- [ ] Set up Twitter API v2 client
- [ ] Implement TwitterTracker
- [ ] Monitor AI lab accounts
- [ ] Extract arXiv links from tweets
- [ ] Collect metrics (likes, retweets, replies)
- [ ] Save as SocialSignal records
- [ ] Update database schema

### Files to Create

- `src/agents/discovery/twitter_tracker.py`
- `src/models/social_signal.py`
- `migrations/002_add_social_signals.sql`

### Config Addition

```bash
# .env
TWITTER_BEARER_TOKEN=your_token
LAB_TWITTER_ACCOUNTS=@AnthropicAI,@OpenAI,@GoogleDeepMind,@MetaAI
```

### Acceptance Criteria

✅ Can fetch tweets from lab accounts  
✅ Extracts arXiv links  
✅ Saves social signals to DB

---

## Day 2 (Sunday Morning): HackerNews Tracker (3-4 hours)

### Tasks

- [ ] Implement HN scraper using Algolia API
- [ ] Search for arXiv links in stories
- [ ] Filter: front page + "Show HN"
- [ ] Collect: points, comments, timestamp
- [ ] Save as SocialSignal records
- [ ] Handle rate limiting
- [ ] Add tests

### Files to Create

- `src/agents/discovery/hn_tracker.py`
- `tests/test_hn_tracker.py`

### HN Algolia API

```
GET https://hn.algolia.com/api/v1/search?query=arxiv.org&tags=story
```

### Acceptance Criteria

✅ Can scrape HN for arXiv links  
✅ Saves points + comments  
✅ Handles rate limits

---

## Day 3 (Sunday Afternoon): Enhanced Scoring (2-3 hours)

### Tasks

- [ ] Update scoring algorithm
- [ ] Add social_score component
- [ ] Weight: interest (40%), social (30%), recency (30%)
- [ ] Normalize scores to 0-100
- [ ] Update Curator agent
- [ ] Update email template with social badges

### Files to Update

- `src/agents/curator.py` - New scoring function
- `src/templates/email_digest.html` - Add badges

### Social Badges

- 🔥 Mentioned by @AnthropicAI
- 📰 #1 on HackerNews (234 points)
- 🐦 12 Twitter mentions

### Acceptance Criteria

✅ Papers scored by multi-signal  
✅ Social proof visible in email  
✅ High-social papers ranked higher

---

## Day 4 (Weeknight): Lab Website Tracker (2-3 hours)

### Tasks

- [ ] Scrape lab publication pages
  - Anthropic: anthropic.com/research
  - OpenAI: openai.com/research
  - DeepMind: deepmind.google/research/publications
- [ ] Extract: title, authors, arXiv link
- [ ] Add "lab_published_by" field
- [ ] Give bonus points to lab publications

### Files to Create

- `src/agents/discovery/lab_tracker.py`
- `src/scrapers/` - HTML parsing utilities

### Acceptance Criteria

✅ Can scrape lab sites  
✅ Identifies official publications  
✅ Lab bonus applied to scoring

---

## Day 5 (Weeknight): Integration & Testing (1-2 hours)

### Tasks

- [ ] Update LangGraph to run all trackers in parallel
- [ ] Deduplicate papers by arxiv_id
- [ ] Merge social signals from multiple sources
- [ ] Test full pipeline
- [ ] Send test email with social proof

### Parallel Discovery

Run ArXiv, Twitter, HN, Labs concurrently with asyncio.gather()

### Test Command

```bash
python main.py --discover --days 3 --digest
```

### Expected Email

Shows papers with:
- 🐦 12 Twitter mentions
- 🔥 #2 on HN (189 points)
- 🏛️ Published by Anthropic

### Acceptance Criteria

✅ All trackers run in parallel  
✅ Deduplication works  
✅ Social signals merged  
✅ Email shows social proof

---

## Week 2 Acceptance Criteria

- ✅ Tracks Twitter mentions from AI labs
- ✅ Scrapes HackerNews for trending papers
- ✅ Scrapes lab publication pages
- ✅ Papers scored by multi-signal algorithm
- ✅ Email shows social proof badges
- ✅ Discovery runs fast (parallel execution)

---

## Troubleshooting

**Twitter API errors:**
- Verify bearer token in .env
- Check rate limits (450 req/15min)

**HN scraping fails:**
- Use Algolia API, not HTML scraping
- Respect rate limits

**Lab sites change:**
- Update URLs in config
- Add error handling for missing pages

---

## Code Checkpoint

```bash
git commit -m "Week 2: Social signals (Twitter, HN, lab tracking)"
git tag week2-social-signals
```

---

[← Week 1](week1.md) | [Week 3 →](week3.md)
