# Week 1: Foundation - Core Discovery & Explanation

**Goal:** Build the MVP - daily email digest with AI-explained papers

**Time:** 12-15 hours  
**Cost:** $10-30  
**Deliverable:** Manual trigger sends email with 5 explained papers

---

## Day 1 (Saturday): Project Setup (2-3 hours)

### Tasks

- [ ] Set up virtual environment
- [ ] Install dependencies from requirements.txt
- [ ] Create .env file with API keys
- [ ] Initialize SQLite database
- [ ] Verify Claude API connection

### Files to Create

- `src/config.py` - Already exists ✓
- `src/database.py` - Already exists ✓
- `src/models/paper.py` - Already exists ✓
- `.env` - Copy from .env.example

### Commands

```bash
cd /Users/bencrabtree/Workplace/arxiv-learning-assistant
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your keys

# Test
python main.py --init-db
```

### Acceptance Criteria

✅ Virtual environment active  
✅ All dependencies installed  
✅ Database initialized  
✅ Claude API key verified

---

## Day 2 (Sunday Morning): Discovery Agent v1 (3-4 hours)

### Tasks

- [ ] Implement arXiv search agent
- [ ] Query by categories (cs.AI, cs.LG, cs.CL)
- [ ] Filter by date range
- [ ] Parse results into Paper objects
- [ ] Save to database
- [ ] Add basic caching
- [ ] Write tests

### Files to Create

- `src/agents/discovery/arxiv_search.py`
- `src/agents/discovery/base.py` - Base tracker interface
- `tests/test_arxiv_search.py`

### Key Implementation

ArXiv API wrapper that:
1. Builds query from categories + date filter
2. Fetches results (max 1000)
3. Converts to Paper objects
4. Saves to database

### Test Command

```bash
python -c "from src.agents.discovery.arxiv_search import fetch_papers; \
           papers = fetch_papers(days=1); print(f'Found {len(papers)} papers')"
```

### Acceptance Criteria

✅ Can fetch papers from arXiv  
✅ Papers saved to database  
✅ Basic caching works  
✅ Tests pass

---

## Day 3 (Sunday Afternoon): Reader & Explainer Agents (3-4 hours)

### Tasks

#### Reader Agent
- [ ] Create prompt for structured extraction
- [ ] Use Claude 3.5 Haiku
- [ ] Extract: main claim, methodology, key results, concepts
- [ ] Save analysis to database
- [ ] Batch processing for multiple papers

#### Explainer Agent
- [ ] Create prompt for ELI5 + learning questions
- [ ] Use Claude 3.5 Sonnet
- [ ] Generate: summary, insight, questions, prerequisites
- [ ] Save explanation to database

### Files to Create

- `src/agents/reader.py`
- `src/agents/explainer.py`
- `src/services/claude_client.py` - API wrapper
- `tests/test_agents.py`

### Prompt Templates

**Reader Prompt:** Extract structured info (JSON response)  
**Explainer Prompt:** Simplify for learning (JSON response)

### Test

Pick one paper → Run both agents → Verify output quality

### Acceptance Criteria

✅ Reader extracts structured info  
✅ Explainer creates ELI5 summaries  
✅ Both save to database  
✅ Batch processing works

---

## Day 4 (Weeknight): Curator Agent & Email (2-3 hours)

### Tasks

- [ ] Implement simple scoring algorithm
- [ ] Rank papers by keyword matching
- [ ] Select top 5 papers
- [ ] Create HTML email template
- [ ] Implement SMTP email sender
- [ ] Test email delivery

### Files to Create

- `src/agents/curator.py`
- `src/services/email_sender.py`
- `src/templates/email_digest.html`

### Email Template

Include for each paper:
- Title, authors
- ELI5 summary
- Key insight
- Learning questions
- Links (arXiv abstract, PDF)

### Acceptance Criteria

✅ Papers scored by relevance  
✅ Top 5 selected  
✅ HTML email looks good  
✅ Email sends successfully

---

## Day 5 (Weeknight): LangGraph Integration (2-3 hours)

### Tasks

- [ ] Create LangGraph workflow
- [ ] Define AgentState TypedDict
- [ ] Add nodes: discovery → reader → explainer → curator
- [ ] Add sequential edges
- [ ] Compile graph
- [ ] Create main.py CLI
- [ ] Run full pipeline
- [ ] Send test email

### Files to Create

- `src/graph.py` - LangGraph orchestration
- Update `main.py` - Already exists, add --discover and --digest

### Graph Flow

```
START → discovery → reader → explainer → curator → email → END
```

### Test Full Pipeline

```bash
python main.py --discover --days 1 --digest
# Should receive email with 5 papers
```

### Acceptance Criteria

✅ LangGraph orchestrates all agents  
✅ Full pipeline runs successfully  
✅ Email received with 5 papers  
✅ All data in database

---

## Week 1 Acceptance Criteria

At end of week, you should have:

- ✅ Can fetch papers from arXiv (last N days)
- ✅ Claude extracts structured info (Reader)
- ✅ Claude creates ELI5 explanations (Explainer)
- ✅ Receives HTML email with top 5 papers
- ✅ All data saved to SQLite
- ✅ Basic tests pass

---

## Troubleshooting

**"Module not found" errors:**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

**"Database locked":**
```bash
rm data/papers.db
python main.py --init-db
```

**"API key invalid":**
Check .env file for correct ANTHROPIC_API_KEY

**Email not sending:**
- Use Gmail app-specific password (not main password)
- Enable "Less secure app access" if needed

---

## Code Checkpoint

```bash
git add .
git commit -m "Week 1: MVP - Core discovery and email digest"
git tag week1-mvp
```

---

[← Back to Project Plan](../project_plan.md) | [Week 2 →](week2.md)
