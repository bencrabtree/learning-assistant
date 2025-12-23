# QuickStart Guide

## Initial Setup (First Time Only)

```bash
# 1. Navigate to project directory
cd ~/Workplace/arxiv-learning-assistant

# 2. Activate virtual environment
source venv/bin/activate

# 3. Add your Anthropic API key to .env
# Open .env in your editor and add:
# ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here

# 4. Initialize database
python main.py --init-db

# 5. Verify setup
python main.py --stats
```

---

## Daily Workflow (After Setup)

```bash
# Activate environment (do this every time you open a new terminal)
source venv/bin/activate

# Discover new papers
python main.py --discover --days 1

# Generate and send digest email
python main.py --digest

# Check database stats
python main.py --stats
```

---

## Common Commands

### Database
```bash
# Initialize database
python main.py --init-db

# Reset database (WARNING: deletes all data)
python main.py --init-db --reset --yes

# Show statistics
python main.py --stats
```

### Discovery
```bash
# Find papers from last 1 day
python main.py --discover --days 1

# Find papers from last week
python main.py --discover --days 7

# Find and analyze immediately
python main.py --discover --days 1 --analyze
```

### Analysis
```bash
# Analyze papers in database
python main.py --analyze

# Generate email digest
python main.py --digest
```

### Debugging
```bash
# Enable debug logging
python main.py --debug --discover --days 1

# View logs
tail -f logs/app.log

# Check specific component
python src/services/claude_client.py
python src/agents/discovery/arxiv_searcher.py
```

---

## File Locations

- **Database:** `data/papers.db`
- **Logs:** `logs/app.log`
- **Config:** `.env`
- **Weekly plans:** `docs/weekly/week1.md` through `week6.md`

---

## Getting Your API Key

1. Go to https://console.anthropic.com/
2. Sign in or create account
3. Navigate to API Keys
4. Create a new key
5. Copy it to `.env` file

---

## Next Steps

After initial setup, continue with:
1. Read `SETUP_STATUS.md` for detailed progress tracking
2. Read `docs/langgraph_intro.md` to understand LangGraph
3. Follow `docs/weekly/week1.md` for Day 2 tasks

---

## Troubleshooting

**Virtual environment not activating?**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Missing dependencies?**
```bash
pip install -r requirements.txt
```

**API key not working?**
- Make sure it starts with `sk-ant-api03-`
- No quotes needed in `.env` file
- No spaces around the `=` sign

**Database errors?**
```bash
rm data/papers.db
python main.py --init-db
```

---

## Week 1 Checklist

- [x] Environment setup
- [x] Database initialized
- [x] Config system working
- [x] ArXiv discovery scaffold ready
- [ ] Test arXiv discovery (Day 2)
- [ ] Implement Reader agent (Day 3)
- [ ] Implement Explainer agent (Day 3)
- [ ] Implement Curator agent (Day 4)
- [ ] Build email system (Day 4)
- [ ] Integrate with LangGraph (Day 5)
- [ ] Send first digest email! (Day 5)

You're on track! 🚀
