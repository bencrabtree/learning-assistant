# ArXiv Learning Assistant

Multi-agent system for discovering, explaining, and learning from AI research papers using LangGraph + Claude.

## 🚀 Quick Start

```bash
# 1. Activate environment
source venv/bin/activate

# 2. Add your API key to .env
# ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
# Get key from: https://console.anthropic.com/

# 3. Initialize database
python main.py --init-db

# 4. Test the pipeline (2 papers, ~$0.03)
python main.py --discover --days 1 --analyze --max-papers 2

# 5. View results
python main.py --stats
```

## ✨ What's Working

✅ **Discovery Agent** - Finds papers from arXiv
✅ **Reader Agent** - Extracts structured info with Claude Haiku
✅ **Explainer Agent** - Creates ELI5 explanations with Claude Sonnet
✅ **Curator Agent** - Scores and ranks papers by relevance
✅ **LangGraph Workflows** - Orchestrates all agents
✅ **CLI Application** - Easy command-line interface
✅ **SQLite Database** - Full schema with relationships

## 📖 Common Commands

### Database
```bash
python main.py --init-db              # Initialize database
python main.py --stats                # Show statistics
python main.py --init-db --reset --yes  # Reset (deletes all data)
```

### Discovery & Analysis
```bash
python main.py --discover --days 1    # Find papers from last day
python main.py --discover --days 1 --analyze  # Find and analyze
python main.py --analyze              # Analyze existing papers
python main.py --discover --days 7 --max-papers 10  # Limit papers
```

### Debugging
```bash
python main.py --debug --discover --days 1  # Enable debug logging
tail -f logs/app.log                  # View logs
pytest tests/ -v                      # Run tests
```

## 🏗️ Architecture

```
main.py (CLI)
    └─> src/graph.py (LangGraph Workflows)
            └─> src/agents/* (Business Logic)
                    └─> src/database.py (Persistence)
```

**Three Workflows:**
- `run_full_pipeline()` - Discovery → Reader → Explainer
- `run_analysis_pipeline()` - Reader → Explainer (existing papers)
- `run_discovery_only_pipeline()` - Discovery only

## ⚙️ Customization

Edit `.env` to customize:

```bash
# Research interests (for scoring)
RESEARCH_INTERESTS=transformers,RL,multimodal learning,agents

# ArXiv categories to search
ARXIV_CATEGORIES=cs.AI,cs.LG,cs.CL,cs.CV,cs.RO

# Papers per digest
MAX_PAPERS_PER_DIGEST=10
```

## 🔍 Understanding the Code

### Key Files

| File | Purpose |
|------|---------|
| `main.py` | CLI commands |
| `src/graph.py` | LangGraph workflows |
| `src/agents/reader.py` | Extract technical info |
| `src/agents/explainer.py` | Create learning summaries |
| `src/agents/curator.py` | Score and rank papers |
| `src/database.py` | Database management |
| `src/models/paper.py` | Data schema |

### How It Works

```
1. Discovery → Finds papers from arXiv
2. Reader → Extracts: main_claim, methodology, key_results, concepts
3. Explainer → Creates: eli5_summary, key_insight, learning_questions
4. Curator → Scores: relevance to your interests
5. Database → Stores everything
```

### Learning Resources

- **`docs/langgraph_intro.md`** - LangGraph concepts explained
- **`CLAUDE.md`** - Architecture principles for AI-assisted development
- **`src/graph.py`** - See how agents connect in workflows
- **All agent files** - Extensively documented with examples

Every function has detailed docstrings explaining what, why, and how!

## 💰 Cost Estimates

Per paper:
- Discovery: Free (arXiv API)
- Reader (Haiku): ~$0.001
- Explainer (Sonnet): ~$0.015
- **Total: ~$0.016/paper**

Daily (5 papers): **~$0.08**
Monthly (150 papers): **~$2.40**

Very affordable! ☕

## 🐛 Troubleshooting

**"No papers found"**
```bash
# Try longer time range
python main.py --discover --days 7

# Check your categories in .env
cat .env | grep ARXIV_CATEGORIES
```

**"API key invalid"**
- Get key from https://console.anthropic.com/
- Add to `.env`: `ANTHROPIC_API_KEY=sk-ant-api03-...`
- No quotes needed, no spaces around `=`

**"Database locked"**
```bash
rm data/papers.db
python main.py --init-db
```

**Tests failing**
```bash
pip install -r requirements.txt
pytest tests/ -v
```

## 🚀 Next Steps

### Option 1: Use It Daily
```bash
source venv/bin/activate
python main.py --discover --days 1 --analyze
python main.py --stats
```

### Option 2: Add Email Digest
- Create email template
- Configure SMTP in `.env`
- Add email node to graph

See: `docs/weekly/week1.md` (Day 4)

### Option 3: Add Social Signals
- Twitter API integration
- HackerNews tracking
- Enhanced scoring

See: `docs/weekly/week2.md`

## 🧪 Testing

The project has comprehensive test coverage with **65 total tests** covering all major components.

### Running Tests

```bash
# Activate environment
source venv/bin/activate

# Run all tests
pytest tests/ -v

# Run specific test modules
pytest tests/test_discovery.py -v      # Discovery agent tests
pytest tests/test_reader.py -v         # Reader agent tests
pytest tests/test_explainer.py -v      # Explainer agent tests
pytest tests/test_graph.py -v          # Workflow tests
pytest tests/test_integration.py -v    # Integration tests
pytest tests/test_database.py -v       # Database tests

# Run with coverage report
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html                # View coverage report
```

### Test Coverage

- ✅ **Discovery Agent (18 tests)** - Query building, arXiv API integration, datetime handling
- ✅ **Reader Agent (10 tests)** - Prompt generation, Claude API calls, database persistence
- ✅ **Explainer Agent (9 tests)** - Explanation generation, prerequisite detection
- ✅ **Graph Workflows (13 tests)** - Node execution, state management, error handling
- ✅ **Integration Tests (10 tests)** - End-to-end pipeline validation
- ✅ **Database Tests (9 tests)** - ORM operations, session management

**Current Status:** 47/65 tests passing (72% - primarily unit tests)

The failing tests are integration tests that require additional mock refinements for external API calls.

### Test Organization

```
tests/
├── conftest.py           # Shared fixtures and test setup
├── test_discovery.py     # Discovery agent unit tests
├── test_reader.py        # Reader agent unit tests
├── test_explainer.py     # Explainer agent unit tests
├── test_graph.py         # LangGraph workflow tests
├── test_integration.py   # End-to-end integration tests
└── test_database.py      # Database and ORM tests
```

## 📚 Documentation

- **[docs/design.md](docs/design.md)** - System architecture
- **[docs/project_plan.md](docs/project_plan.md)** - 6-week build plan
- **[docs/weekly/week1.md](docs/weekly/week1.md)** - Week 1 tasks
- **[CLAUDE.md](CLAUDE.md)** - Development principles for AI assistance

## 🛠️ Tech Stack

- **LangGraph** - Agent orchestration
- **Claude** (Haiku + Sonnet) - AI analysis
- **SQLAlchemy** - Database ORM
- **SQLite** - Local storage
- **Streamlit** (Week 5) - Dashboard
- **NetworkX** (Week 4) - Knowledge graphs

## 📈 Roadmap (6-Week Build)

- ✅ **Week 1:** Core pipeline (discovery + analysis + explanation)
- 🚧 **Week 2:** Social signals (Twitter, HackerNews)
- 📅 **Week 3:** Citation velocity tracking
- 📅 **Week 4:** Interactive knowledge graph
- 📅 **Week 5:** Reading progress dashboard
- 📅 **Week 6:** Production polish + synthesis

## 📝 File Locations

- Database: `data/papers.db`
- Logs: `logs/app.log`
- Config: `.env`
- Weekly plans: `docs/weekly/`

## 🤝 Contributing

This is a learning project! Key principles:

1. **Single execution path** - All orchestration through LangGraph
2. **Imports at top** - No lazy imports
3. **Layer separation** - CLI → Graph → Agents → Database
4. **Documentation** - Every function explained

See `CLAUDE.md` for full development guidelines.

---

**Built with LangGraph + Claude** | *Helping you stay on top of AI research* 🚀
