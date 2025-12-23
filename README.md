# ArXiv Learning Assistant

Multi-agent system for discovering, explaining, and learning from AI research papers using LangGraph + Claude.

## 🚀 Quick Start

```bash
# 1. Set up environment (already done!)
source venv/bin/activate

# 2. Add your API key to .env
# ANTHROPIC_API_KEY=sk-ant-api03-your-key-here

# 3. Initialize database
python main.py --init-db

# 4. Test the full pipeline (recommended - start here!)
python main.py --discover --days 1 --analyze --max-papers 2

# 5. View results
python main.py --stats
```

## ✨ What's Working Now

✅ **Discovery Agent** - Finds papers from arXiv
✅ **Reader Agent** - Extracts structured info with Claude Haiku
✅ **Explainer Agent** - Creates ELI5 explanations with Claude Sonnet
✅ **Curator Agent** - Scores and ranks papers by relevance
✅ **LangGraph Workflow** - Orchestrates all agents
✅ **CLI Application** - Easy command-line interface
✅ **Database** - SQLite storage with full schema

## Features (6-Week Build)

- **Week 1:** Daily email with AI-explained papers
- **Week 2:** Social proof signals (Twitter, HN)
- **Week 3:** Citation velocity tracking
- **Week 4:** Interactive knowledge graph
- **Week 5:** Reading progress dashboard
- **Week 6:** Production-ready with synthesis

## Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Get running in 15 minutes
- **[docs/project_plan.md](docs/project_plan.md)** - Detailed weekly tasks
- **[docs/design.md](docs/design.md)** - System architecture

## Tech Stack

- LangGraph - Agent orchestration
- Claude - AI explanations
- StreamLit - Dashboard
- NetworkX - Knowledge graphs
- SQLite - Local database

Built to help you stay on top of AI research! 🚀
