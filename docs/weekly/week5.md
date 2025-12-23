# Week 5: Reading Progress Dashboard

**Goal:** Track learning journey with personalized insights

**Time:** 10-12 hours  
**Cost:** $10-20  
**Deliverable:** Dashboard showing reading stats and recommendations

---

## Day 1 (Saturday): Reading Progress Tracking (3-4 hours)

### Tasks

- [ ] Enhance ReadingProgress model
  - Add: time_spent_minutes, revisit_count
  - Track: reading sessions
- [ ] Create CLI commands for marking papers
- [ ] Create reading state machine
  - States: unread → reading → finished → archived
  - Track state transitions
- [ ] Log reading sessions
  - Start time, end time, duration

### Files to Create

- `src/models/reading_session.py`
- `src/services/progress_tracker.py`
- `migrations/005_add_reading_sessions.sql`

### CLI Commands

```bash
python main.py --mark-read arxiv:2401.12345 --rating 5
python main.py --mark-read arxiv:2401.12345 --note "Great paper!"
```

### Acceptance Criteria

✅ Can mark papers as read/finished  
✅ Reading sessions tracked  
✅ CLI commands work

---

## Day 2 (Sunday Morning): Dashboard Stats View (3-4 hours)

### Tasks

- [ ] Create "Reading Stats" page
  - Papers read this week/month/year
  - Time invested (estimated)
  - Topics covered (bar chart)
  - Favorite authors (ranked list)
  - Reading streak (calendar heatmap)
- [ ] Add charts with Plotly
  - Papers per week (line chart)
  - Topics distribution (pie chart)
  - Reading time trend (area chart)

### Files to Create

- `src/dashboard/components/reading_stats.py`
- `src/dashboard/components/charts.py`

### Stats to Display

- Papers read this week: 5
- Papers read this month: 18
- Total papers read: 142
- Time invested: 87 hours
- Reading streak: 23 days
- Favorite topics: [reasoning, RLHF, agents]

### Acceptance Criteria

✅ Reading stats calculate correctly  
✅ Charts display properly  
✅ Streak tracking works

---

## Day 3 (Sunday Afternoon): Concept Mastery Tracking (2-3 hours)

### Tasks

- [ ] Create Concept model
  - Track: name, papers mentioning it, mastery level
  - Calculate: beginner/intermediate/advanced
- [ ] Build concept heatmap
  - X-axis: Concepts
  - Y-axis: Mastery level
  - Color: Confidence
- [ ] Show concept connections
  - How concepts relate to papers

### Files to Create

- `src/models/concept.py`
- `src/services/concept_tracker.py`
- `src/dashboard/components/knowledge_map.py`

### Mastery Calculation

- Beginner: 1-2 papers read
- Intermediate: 3-5 papers read
- Advanced: 6+ papers read

### Acceptance Criteria

✅ Concepts extracted from papers  
✅ Mastery levels calculated  
✅ Heatmap displays

---

## Day 4 (Weeknight): Recommendation Engine (2-3 hours)

### Tasks

- [ ] Implement recommendation agent
  - "Next to Read" - based on prerequisites
  - "Related Papers" - similar to recent reads
  - "Fill Knowledge Gaps" - underexplored topics
- [ ] Use LLM for personalized suggestions
  - Input: reading history, concepts mastered
  - Output: 5 recommended papers with rationale
- [ ] Display on dashboard

### Files to Create

- `src/agents/recommendation_agent.py`
- `src/dashboard/components/recommendations.py`

### Recommendation Types

1. **Next to Read:** Papers that build on what you've read
2. **Fill Gaps:** Topics you mention but haven't mastered
3. **Related:** Similar to your recent favorites

### Acceptance Criteria

✅ Recommendations generated  
✅ Rationale provided  
✅ Display in dashboard

---

## Day 5 (Weeknight): Dashboard Integration (1-2 hours)

### Tasks

- [ ] Create multi-page Streamlit app
  - Page 1: Knowledge Graph
  - Page 2: Reading Stats
  - Page 3: Recommendations
  - Page 4: Paper Search
- [ ] Add navigation sidebar
- [ ] Add export features
  - Export stats as PDF report
  - Export reading list as CSV

### Files to Update

- `src/dashboard/app.py` - Multi-page structure

### Navigation

Sidebar pages:
- 🕸️ Knowledge Graph (Week 4)
- 📊 Reading Stats (new)
- 💡 Recommendations (new)
- 🔍 Search Papers

### Acceptance Criteria

✅ Multi-page navigation works  
✅ All pages accessible  
✅ Export features work

---

## Week 5 Acceptance Criteria

- ✅ Can mark papers as read/finished
- ✅ Dashboard shows reading statistics
- ✅ Tracks concept mastery levels
- ✅ Generates personalized recommendations
- ✅ Shows reading streak and trends
- ✅ Multi-page dashboard interface
- ✅ Can export progress reports

---

## Deliverable

```bash
streamlit run src/dashboard/app.py

# Dashboard pages:
# 1. Knowledge Graph (from Week 4)
# 2. Reading Stats (new)
#    - Papers read: 23 this month
#    - Time invested: 47 hours
#    - Streak: 15 days
# 3. Recommendations (new)
#    - Next: "Constitutional AI" (builds on RLHF knowledge)
#    - Gap: Learn more about RL fundamentals
```

---

## Troubleshooting

**Stats not calculating:**
- Check ReadingProgress records exist
- Verify state transitions logged

**Recommendations off:**
- Adjust scoring weights in config
- Check reading history has sufficient data

**Charts not rendering:**
- Update plotly: `pip install --upgrade plotly`
- Check data format

---

## Code Checkpoint

```bash
git commit -m "Week 5: Reading progress dashboard and recommendations"
git tag week5-dashboard
```

---

[← Week 4](week4.md) | [Week 6 →](week6.md)
