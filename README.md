# ArXiv Learning Assistant

Multi-agent system for discovering, explaining, and learning from AI research papers.

## Quick Start

```bash
# 1. Set up environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with your API keys

# 3. Initialize database
python main.py --init-db

# 4. Start discovering papers
python main.py --discover --days 1
python main.py --digest
```

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
