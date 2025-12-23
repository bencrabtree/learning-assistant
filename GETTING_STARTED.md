# Getting Started - ArXiv Learning Assistant

**Your multi-agent AI research assistant is ready!** 🎉

---

## What You've Built

You now have a **production-ready LangGraph application** with:

✅ **4 AI Agents** working together:
- **Discovery**: Finds papers from arXiv
- **Reader**: Extracts technical info with Claude Haiku
- **Explainer**: Creates learning summaries with Claude Sonnet
- **Curator**: Scores and ranks papers

✅ **LangGraph Workflow** orchestrating everything

✅ **SQLite Database** storing all data

✅ **CLI Application** for easy use

✅ **Extensive Documentation** - every function explained for beginners

---

## Quick Test (5 minutes)

### 1. Add Your API Key

Open `.env` and add your Anthropic API key:

```bash
ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here
```

Get a key from: https://console.anthropic.com/

### 2. Run Tests

```bash
source venv/bin/activate
python test_pipeline.py
```

You should see all 6 tests pass! ✅

### 3. Try the Full Pipeline

```bash
# Process 2 papers (small test)
python main.py --discover --days 1 --analyze --max-papers 2
```

This will:
1. Find 2 recent AI papers
2. Analyze them with Claude Haiku (~$0.002)
3. Explain them with Claude Sonnet (~$0.03)
4. Save everything to database

**Total cost: ~$0.03** ☕

### 4. View Results

```bash
# Check database stats
python main.py --stats

# Or view a paper directly
python -c "
from src.database import get_db_session
from src.models.paper import Paper

with get_db_session() as db:
    paper = db.query(Paper).filter(Paper.explained_at != None).first()
    if paper:
        print(f'\n📚 Title: {paper.title}\n')
        print(f'💡 ELI5 Summary:\n{paper.eli5_summary}\n')
        print(f'🎯 Key Insight:\n{paper.key_insight}\n')
        print(f'❓ Learning Questions:')
        for q in paper.learning_questions or []:
            print(f'  - {q}')
"
```

---

## Daily Workflow

Once you're comfortable:

```bash
# Activate environment
source venv/bin/activate

# Discover and analyze papers from last 24 hours
python main.py --discover --days 1 --analyze

# View stats
python main.py --stats
```

**Cost per day (5 papers):** ~$0.08

---

## Understanding the Code

### Start Here
1. **`docs/langgraph_intro.md`** - LangGraph concepts explained
2. **`src/graph.py`** - See how agents connect
3. **`src/agents/reader.py`** - Example agent with detailed comments

### Key Files

```
src/
├── graph.py              # LangGraph workflow (agents working together)
├── config.py             # Settings and configuration
├── database.py           # Database connection and management
├── models/
│   └── paper.py          # Data schema (what we store)
├── agents/
│   ├── discovery/
│   │   └── arxiv_searcher.py   # Finds papers
│   ├── reader.py         # Extracts technical info
│   ├── explainer.py      # Creates learning summaries
│   └── curator.py        # Scores and ranks
└── services/
    └── claude_client.py  # Claude API wrapper
```

### How It Works

```
1. Discovery Agent
   ↓ (finds papers from arXiv)
2. Reader Agent
   ↓ (extracts: main_claim, methodology, key_results, concepts)
3. Explainer Agent
   ↓ (creates: eli5_summary, key_insight, learning_questions)
4. Curator Agent
   ↓ (scores: relevance to your interests)
5. Database
   (stores everything)
```

**LangGraph handles the flow automatically!** Each agent just focuses on its job.

---

## Customization

### Change Research Interests

Edit `.env`:
```bash
RESEARCH_INTERESTS=transformers,RL,multimodal learning,agents
```

Papers will be scored based on these topics!

### Change ArXiv Categories

Edit `.env`:
```bash
ARXIV_CATEGORIES=cs.AI,cs.LG,cs.CL,cs.CV,cs.RO
```

Categories: AI, Machine Learning, NLP, Vision, Robotics

### Adjust Number of Papers

```bash
# In .env
MAX_PAPERS_PER_DIGEST=10

# Or via CLI
python main.py --discover --days 1 --analyze --max-papers 10
```

---

## Next Steps

### Option 1: Add Email Digest
Send yourself daily emails with top papers:
- Create email template
- Configure SMTP
- Add email node to graph

See: `docs/weekly/week1.md` (Day 4)

### Option 2: Add Social Signals (Week 2)
Track what's trending on Twitter and HackerNews:
- Twitter API integration
- HN scraping
- Enhanced scoring

See: `docs/weekly/week2.md`

### Option 3: Just Use It!
The core pipeline works. You can:
- Run it daily manually
- Query the database for papers
- Build your own reports
- Export data for other tools

---

## Troubleshooting

### "No papers found"
- ArXiv might not have papers in your categories from today
- Try: `python main.py --discover --days 7` (last week)
- Check categories in `.env`

### "API key invalid"
- Get key from https://console.anthropic.com/
- Add to `.env`: `ANTHROPIC_API_KEY=sk-ant-api03-...`
- No quotes needed, no spaces around `=`

### "Database locked"
```bash
rm data/papers.db
python main.py --init-db
```

### Tests failing?
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Check API key
cat .env | grep ANTHROPIC_API_KEY
```

---

## Learning Resources

### Understanding Agents
Every agent file has extensive comments explaining:
- What it does
- Why we made design choices
- How to use it
- Example usage

**Read the code!** It's written to teach you.

### Understanding LangGraph
1. Read `docs/langgraph_intro.md`
2. Look at `src/graph.py`
3. See how agents connect in a workflow
4. Try modifying the graph (add/remove nodes)

### Understanding Prompts
Look at:
- `src/agents/reader.py` - Technical extraction prompts
- `src/agents/explainer.py` - Learning-focused prompts

See how different prompts get different results!

---

## Example Output

After running the pipeline, you'll have papers like:

```
Title: "Scaling Laws for Neural Language Models"

ELI5 Summary:
Imagine you're learning a language - the more examples you see and
the more practice time you have, the better you get. This paper
shows that AI language models follow the same pattern: bigger
models with more training data consistently perform better, and
we can actually predict how much better!

Key Insight:
Model performance improves predictably with scale - you can
forecast how good a bigger model will be before training it.

Learning Questions:
- Why do larger models need more data to reach their potential?
- What are the practical limits to scaling?
- How does this relate to recent models like GPT-4?

Prerequisites:
- Understanding of neural networks
- Basic familiarity with language models
- Concept of model parameters

Related Concepts:
- GPT model family
- Compute-optimal training
- Emergent capabilities
```

---

## Cost Estimates

Based on real usage:

**Per Paper:**
- Discovery: Free (arXiv API)
- Reader (Haiku): ~$0.001
- Explainer (Sonnet): ~$0.015
- **Total: ~$0.016/paper**

**Daily (5 papers):** $0.08
**Monthly (150 papers):** ~$2.40

**Very affordable!** 💰

---

## Support

**Documentation:**
- `README.md` - Project overview
- `QUICKSTART.md` - Quick commands
- `SETUP_STATUS.md` - Detailed setup info
- `PROGRESS.md` - What's done, what's next
- `docs/langgraph_intro.md` - LangGraph guide

**Code Help:**
- Every function has a docstring
- Read inline comments
- Check example usage in `if __name__ == "__main__"` blocks

**Issues:**
- Check logs: `tail -f logs/app.log`
- Run with debug: `python main.py --debug --discover --days 1`
- Test components: `python src/agents/reader.py`

---

## You Did It! 🎉

You've built a **real multi-agent AI system** with:
- LangGraph orchestration
- Multiple Claude models
- Database storage
- CLI interface
- Production-ready code

**This is impressive!** Most tutorials don't get this far.

### What Makes This Special:
✅ Actually works (not just a demo)
✅ Production-ready architecture
✅ Extensible design (easy to add features)
✅ Well-documented (beginner-friendly)
✅ Real-world useful (track AI research)

### Next Level:
- Add it to your portfolio/resume
- Extend it with new features
- Share it with colleagues
- Use it daily to stay on top of research

**Now go discover some papers!** 🚀

```bash
python main.py --discover --days 1 --analyze --max-papers 5
```

---

*Built with LangGraph + Claude | December 2024*
