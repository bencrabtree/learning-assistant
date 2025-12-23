# CLAUDE.md - AI Assistant Guide

**Last Updated:** December 2025
**Project:** ArXiv Learning Assistant
**Version:** 1.0

This document provides comprehensive guidance for AI assistants (like Claude) working with this codebase. It explains the project structure, architecture, development workflows, and key conventions to follow.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Project Structure](#project-structure)
3. [Tech Stack](#tech-stack)
4. [Development Workflow](#development-workflow)
5. [Architecture & Design](#architecture--design)
6. [Database Schema](#database-schema)
7. [Code Conventions](#code-conventions)
8. [Key Patterns](#key-patterns)
9. [Common Tasks](#common-tasks)
10. [Testing & Debugging](#testing--debugging)
11. [API Integration](#api-integration)
12. [Important Notes](#important-notes)

---

## Project Overview

### What is this?

**ArXiv Learning Assistant** is a multi-agent system that helps AI researchers stay on top of the flood of papers published daily on arXiv. It discovers, analyzes, explains, and curates research papers with personalized learning paths.

### Problem It Solves

- 200-300 new AI papers published daily on arXiv
- Existing solutions (RSS, Twitter) are too noisy or incomplete
- Manual tracking is time-consuming and inefficient

### Solution

Multi-agent LangGraph system that:
1. **Discovers** papers from multiple sources (arXiv, Twitter, HackerNews)
2. **Analyzes** papers with Claude to extract structured information
3. **Explains** papers in accessible language for learning
4. **Curates** papers based on relevance, social proof, and citation velocity
5. **Visualizes** connections through interactive knowledge graphs
6. **Tracks** reading progress and suggests next papers

### Design Principles

1. **Modularity** - Each agent is independent and testable
2. **Incremental Value** - Each phase delivers usable features
3. **Low Latency** - Async operations, caching, batching
4. **Cost Efficient** - Haiku for extraction, Sonnet for explanations
5. **Extensible** - Easy to add new sources and agents

---

## Project Structure

```
learning-assistant/
├── main.py                 # CLI entry point - all user commands
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variable template
├── README.md              # User-facing documentation
├── QUICKSTART.md          # 15-minute setup guide
├── CLAUDE.md              # This file - AI assistant guide
│
├── src/                   # Source code
│   ├── __init__.py
│   ├── config.py          # Configuration management (pydantic)
│   ├── database.py        # Database connection & session management
│   │
│   ├── models/            # Database models (SQLAlchemy ORM)
│   │   ├── __init__.py
│   │   └── paper.py       # Paper, Citation, SocialSignal, ReadingProgress
│   │
│   ├── agents/            # LangGraph agents
│   │   ├── __init__.py
│   │   └── discovery/     # Discovery agents
│   │       ├── __init__.py
│   │       └── arxiv_searcher.py  # ArXiv API integration
│   │
│   ├── services/          # External service clients
│   │   ├── __init__.py
│   │   └── claude_client.py       # Claude API wrapper
│   │
│   ├── visualization/     # Graph visualization
│   │   └── __init__.py
│   │
│   └── dashboard/         # Streamlit dashboard
│       └── __init__.py
│
├── tests/                 # Test files
│   └── __init__.py
│
├── docs/                  # Documentation
│   ├── design.md          # System architecture & design
│   ├── project_plan.md    # 6-week build plan
│   ├── langgraph_intro.md # LangGraph concepts
│   └── weekly/            # Weekly task breakdowns
│       ├── week1.md
│       ├── week2.md
│       ├── week3.md
│       ├── week4.md
│       ├── week5.md
│       └── week6.md
│
├── data/                  # Database & cache (gitignored)
│   └── papers.db          # SQLite database
│
└── logs/                  # Application logs (gitignored)
    └── app.log            # Rotating log file
```

### Key Files to Understand

| File | Purpose | When to Modify |
|------|---------|----------------|
| `main.py` | CLI commands & orchestration | Adding new commands |
| `src/config.py` | Environment variables & settings | Adding new configuration |
| `src/database.py` | Database connection & sessions | Changing DB setup |
| `src/models/paper.py` | Data models & schema | Adding/modifying tables |
| `docs/design.md` | Architecture reference | Understanding system design |
| `.env.example` | Required environment variables | Adding new API keys |

---

## Tech Stack

### Core Framework
- **LangGraph 0.3+** - Multi-agent orchestration & state management
- **LangChain 0.1+** - LLM framework & utilities
- **Anthropic 0.18+** - Claude API client

### Data & Storage
- **SQLAlchemy 2.0+** - ORM for database operations
- **SQLite 3** - Local database (can swap for Postgres)
- **NetworkX 3.2+** - Graph analysis & algorithms
- **Redis 5.0+** (optional) - Caching layer

### Discovery APIs
- **arxiv 2.1+** - ArXiv paper search
- **tweepy 4.14+** - Twitter API v2 client
- **semanticscholar 0.8+** - Citation data
- **beautifulsoup4 4.12+** - Web scraping
- **requests 2.31+** - HTTP client

### Visualization
- **Streamlit 1.29+** - Interactive dashboard
- **Plotly 5.18+** - Charts & visualizations
- **PyVis 0.3+** - Network graph rendering

### Utilities
- **pydantic 2.5+** - Settings validation
- **python-dotenv 1.0+** - Environment variable loading
- **loguru 0.7+** - Modern logging
- **apscheduler 3.10+** - Job scheduling
- **pytest 7.4+** - Testing framework
- **black 24.0+** - Code formatting

---

## Development Workflow

### Initial Setup

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 4. Initialize database
python main.py --init-db

# 5. Test the setup
python main.py --stats
```

### Daily Development Workflow

```bash
# Discover papers (development)
python main.py --discover --days 1

# Run with debug logging
python main.py --discover --days 1 --debug

# Check database status
python main.py --stats

# Reset database (WARNING: deletes all data)
python main.py --init-db --reset --yes
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test
pytest tests/test_database.py

# Format code
black .
```

---

## Architecture & Design

### High-Level System Design

```
┌─────────────────────────────────────────────────────────┐
│                 User Interface Layer                    │
├─────────────────────────────────────────────────────────┤
│  • Email Digest                                         │
│  • CLI Commands (main.py)                               │
│  • Dashboard (Streamlit)                                │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              Application Layer (LangGraph)              │
├─────────────────────────────────────────────────────────┤
│  • Supervisor Agent (Orchestrator)                      │
│  • Discovery Agent → ArXiv, Twitter, HN, Citations      │
│  • Reader Agent → Extract structure (Haiku)             │
│  • Explainer Agent → Simplify concepts (Sonnet)         │
│  • Curator Agent → Rank and filter                      │
│  • Graph Builder → Build relationships                  │
│  • Recommendation Agent → Suggest next reads            │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    Data Layer                           │
├─────────────────────────────────────────────────────────┤
│  • SQLite DB (Papers, Citations, Social Signals)        │
│  • Graph Store (NetworkX)                               │
│  • Cache (Redis - optional)                             │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              External Services Layer                    │
├─────────────────────────────────────────────────────────┤
│  • ArXiv API                                            │
│  • Claude API (Anthropic)                               │
│  • Twitter API v2                                       │
│  • Semantic Scholar API                                 │
│  • HackerNews Algolia API                               │
│  • SMTP (Email)                                         │
└─────────────────────────────────────────────────────────┘
```

### LangGraph State Machine

All agents share a common state object (`AgentState` TypedDict):

```python
AgentState = {
    "research_interests": List[str],
    "date_range": tuple[datetime, datetime],
    "raw_papers": List[dict],
    "social_signals": dict,
    "citation_data": dict,
    "analyzed_papers": List[dict],
    "explained_papers": List[dict],
    "scored_papers": List[dict],
    "final_selection": List[dict],
    "errors": List[str],
    "api_calls": dict
}
```

### Agent Specifications

#### 1. Discovery Agent
- **Purpose:** Find papers from multiple sources
- **Sub-agents:** ArxivSearcher, TwitterTracker, HNTracker, CitationTracker
- **Process:** Run in parallel → merge → deduplicate by arxiv_id
- **Caching:** arXiv (1h), Twitter/HN (15min), Citations (24h)

#### 2. Reader Agent
- **Purpose:** Extract structured information from papers
- **Model:** Claude 3.5 Haiku (fast, cheap, good at extraction)
- **Output:** main_claim, methodology, key_results, novel_contributions, limitations, concepts
- **Cost:** ~$0.001 per paper

#### 3. Explainer Agent
- **Purpose:** Generate learning-friendly explanations
- **Model:** Claude 3.5 Sonnet (better explanations)
- **Output:** eli5_summary, key_insight, learning_questions, prerequisites, related_concepts
- **Cost:** ~$0.015 per paper

#### 4. Curator Agent
- **Purpose:** Score and rank papers by relevance
- **Scoring:** Interest match (40%), Social proof (25%), Citation velocity (20%), Recency (10%), Lab prestige (5%)
- **Output:** Top N papers ranked by total score

---

## Database Schema

### Core Entities

#### Paper (papers table)
Primary entity representing an arXiv paper.

**Core Fields:**
- `arxiv_id` (PK) - Unique identifier (e.g., "2312.12345")
- `title`, `abstract`, `authors`, `published_date`
- `categories` - List of arXiv categories (JSON)
- `pdf_url`, `abstract_url`
- `discovered_at`, `discovered_by`
- `lab_published_by` - Optional lab attribution

**Analysis Fields (from Reader Agent):**
- `main_claim`, `methodology`, `key_results`
- `novel_contributions`, `limitations`, `concepts`
- `analyzed_at`

**Explanation Fields (from Explainer Agent):**
- `eli5_summary`, `key_insight`
- `learning_questions`, `prerequisites`, `related_concepts`
- `explained_at`

**Scoring Fields (from Curator Agent):**
- `relevance_score` (0-1, higher = more relevant)
- `score_components` - Breakdown for transparency
- `scored_at`

#### Citation (citations table)
Citation metrics tracked over time.

- `id` (PK) - Auto-incrementing
- `paper_id` (FK → papers.arxiv_id)
- `citation_count`, `measured_at`
- `citations_this_week`, `velocity_score`
- `source` - Where data came from (e.g., "semantic_scholar")

#### SocialSignal (social_signals table)
Social media mentions (Twitter, HN, Reddit).

- `id` (PK)
- `paper_id` (FK → papers.arxiv_id)
- `source` - "twitter", "hackernews", "reddit"
- `source_url`, `score`, `comments_count`
- `snippet`, `author`, `posted_at`
- `discovered_at`

#### ReadingProgress (reading_progress table)
User's reading journey and notes.

- `paper_id` (PK, FK → papers.arxiv_id)
- `status` - "unread", "reading", "finished", "archived"
- `started_at`, `finished_at`
- `rating` (1-5), `notes`, `time_spent_minutes`

### Relationships

```
Paper (1) ←→ (many) Citation
Paper (1) ←→ (many) SocialSignal
Paper (1) ←→ (1) ReadingProgress
```

All relationships use `CASCADE DELETE` - deleting a paper deletes related records.

### Indexes

Performance indexes on frequently queried columns:
- `idx_published_date` on papers.published_date
- `idx_relevance_score` on papers.relevance_score
- `idx_discovered_at` on papers.discovered_at
- `idx_citation_paper_measured` on (citations.paper_id, citations.measured_at)
- `idx_social_paper_source` on (social_signals.paper_id, social_signals.source)
- `idx_progress_status` on reading_progress.status

---

## Code Conventions

### Python Style
- **Formatting:** Black (line length 100)
- **Type Hints:** Use throughout for clarity
- **Docstrings:** Required for all public functions/classes
- **Naming:** snake_case for functions/variables, PascalCase for classes

### Logging
Use `loguru` for all logging:

```python
from loguru import logger

# Good logging practices
logger.info("Starting paper discovery...")
logger.debug(f"API response: {response}")
logger.warning("Rate limit approaching")
logger.error(f"Failed to fetch paper {arxiv_id}: {error}")
logger.exception("Full traceback:")  # Use in except blocks
```

### Error Handling

```python
# Always catch specific exceptions
try:
    paper = discover_papers(days_back=1)
except APIRateLimitError:
    logger.warning("Rate limited, backing off...")
    time.sleep(60)
except ConnectionError as e:
    logger.error(f"Network error: {e}")
    raise
except Exception as e:
    logger.exception("Unexpected error:")
    raise
```

### Configuration
- **All secrets in .env** - Never hardcode API keys
- **Use pydantic Settings** - Type-safe configuration
- **Provide defaults** - For non-sensitive settings
- **Document in .env.example** - Keep it updated

### Database Operations

**ALWAYS use context managers:**

```python
# ✅ GOOD - Automatic commit/rollback/cleanup
with get_db_session() as db:
    paper = db.query(Paper).filter_by(arxiv_id="2312.12345").first()
    paper.relevance_score = 0.9
    # Automatically commits on exit

# ❌ BAD - Manual session management
db = get_db()
paper = db.query(Paper).first()
db.commit()
db.close()  # Easy to forget!
```

---

## Key Patterns

### 1. SQLAlchemy ORM Pattern

**Querying:**
```python
with get_db_session() as db:
    # Simple query
    papers = db.query(Paper).all()

    # Filter
    recent_papers = db.query(Paper)\
        .filter(Paper.published_date > datetime(2024, 1, 1))\
        .all()

    # Complex query with joins
    papers_with_citations = db.query(Paper)\
        .join(Citation)\
        .filter(Citation.citation_count > 100)\
        .all()

    # Aggregation
    from sqlalchemy import func
    avg_score = db.query(func.avg(Paper.relevance_score)).scalar()
```

**Creating:**
```python
with get_db_session() as db:
    paper = Paper(
        arxiv_id="2312.12345",
        title="My Paper",
        abstract="This is cool",
        authors=["Alice", "Bob"],
        published_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://...",
        abstract_url="https://...",
        discovered_by="arxiv"
    )
    db.add(paper)
    # Automatically commits
```

**Updating:**
```python
with get_db_session() as db:
    paper = db.query(Paper).filter_by(arxiv_id="2312.12345").first()
    if paper:
        paper.relevance_score = 0.95
        paper.scored_at = datetime.utcnow()
    # Automatically commits
```

**Handling Duplicates:**
```python
from sqlalchemy.exc import IntegrityError

with get_db_session() as db:
    try:
        paper = Paper(arxiv_id="2312.12345", ...)
        db.add(paper)
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.warning("Paper already exists")
```

### 2. Configuration Pattern

```python
# src/config.py defines all settings
from src.config import settings, get_research_interests_list

# Access settings
api_key = settings.anthropic_api_key
model = settings.reader_model
interests = get_research_interests_list()

# Settings are validated at import time - app crashes fast if config is wrong
```

### 3. Logging Pattern

```python
# Set up once in main.py
from loguru import logger

logger.remove()  # Remove default
logger.add(sys.stdout, level="INFO", colorize=True)
logger.add("logs/app.log", rotation="10 MB", retention="30 days")

# Use everywhere
logger.info("Starting process...")
logger.debug(f"Details: {data}")
logger.error(f"Failed: {error}")
```

### 4. CLI Command Pattern

```python
# main.py structure
def handle_command(args):
    """
    Handle a specific command.

    Pattern:
    1. Log what you're doing
    2. Import dependencies (lazy loading)
    3. Try/except with proper error handling
    4. Log success/failure
    """
    logger.info("Starting command...")

    try:
        from src.agents.discovery import discover_papers
        result = discover_papers(days_back=args.days)
        logger.info(f"✅ Success: {result}")
    except Exception as e:
        logger.error(f"❌ Failed: {e}")
        if settings.log_level == "DEBUG":
            logger.exception("Full traceback:")
        sys.exit(1)
```

---

## Common Tasks

### Adding a New CLI Command

1. Add argument to parser in `main.py`:
```python
parser.add_argument(
    "--my-command",
    action="store_true",
    help="Description of what it does"
)
```

2. Create handler function:
```python
def handle_my_command(args):
    """Handle my new command."""
    logger.info("Running my command...")
    # Implementation
```

3. Wire it up in `main()`:
```python
if args.my_command:
    handle_my_command(args)
```

### Adding a New Database Model

1. Define model in `src/models/paper.py`:
```python
class MyNewModel(Base):
    __tablename__ = "my_table"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Add fields...
```

2. Run database migration:
```python
python main.py --init-db --reset  # Development only!
```

### Adding a New Agent

1. Create agent file in `src/agents/`:
```python
# src/agents/my_agent.py
from langgraph import StateGraph
from src.config import settings

def my_agent_node(state: AgentState) -> AgentState:
    """Process state and return updated state."""
    # Implementation
    return state

def create_my_agent() -> StateGraph:
    """Create agent graph."""
    graph = StateGraph()
    graph.add_node("my_node", my_agent_node)
    # Define flow...
    return graph.compile()
```

2. Import and use in main workflow.

### Adding New Configuration

1. Add to `src/config.py`:
```python
my_new_setting: str = Field(
    default="default_value",
    alias="MY_NEW_SETTING",
    description="What this controls"
)
```

2. Add to `.env.example`:
```bash
# My New Feature
MY_NEW_SETTING=example_value
```

3. Document in README.md if user-facing.

---

## Testing & Debugging

### Running Tests

```bash
# All tests
pytest

# Specific file
pytest tests/test_database.py

# Specific test
pytest tests/test_database.py::test_init_db

# With output
pytest -v -s

# With coverage
pytest --cov=src --cov-report=html
```

### Writing Tests

```python
import pytest
from src.database import init_db, get_db_session
from src.models.paper import Paper

def test_create_paper():
    """Test creating a paper."""
    init_db()

    with get_db_session() as db:
        paper = Paper(
            arxiv_id="test.12345",
            title="Test Paper",
            # ... other required fields
        )
        db.add(paper)

    with get_db_session() as db:
        found = db.query(Paper).filter_by(arxiv_id="test.12345").first()
        assert found is not None
        assert found.title == "Test Paper"
```

### Debugging Tips

1. **Use debug logging:**
```bash
python main.py --discover --debug
```

2. **Check database state:**
```bash
python main.py --stats
sqlite3 data/papers.db "SELECT * FROM papers LIMIT 5;"
```

3. **Inspect logs:**
```bash
tail -f logs/app.log
```

4. **Use Python debugger:**
```python
import pdb; pdb.set_trace()  # Breakpoint
```

---

## API Integration

### ArXiv API
- **Library:** `arxiv` Python package
- **Rate Limit:** 3 requests/second
- **Caching:** 1 hour recommended
- **Docs:** https://info.arxiv.org/help/api/index.html

### Claude API (Anthropic)
- **Library:** `anthropic` Python package
- **Models:** Haiku (fast/cheap), Sonnet (quality)
- **Rate Limits:** Tier-based (check console)
- **Best Practice:** Batch similar requests
- **Docs:** https://docs.anthropic.com/

### Twitter API v2
- **Library:** `tweepy`
- **Auth:** Bearer token
- **Rate Limit:** 450 requests/15min
- **Caching:** 15 minutes recommended
- **Docs:** https://developer.twitter.com/en/docs

### Semantic Scholar
- **Library:** `semanticscholar`
- **Rate Limit:** 100 req/5min (no key), 5000 req/5min (with key)
- **Batching:** Up to 500 IDs per request
- **Caching:** 24 hours recommended
- **Docs:** https://api.semanticscholar.org/

### HackerNews
- **API:** Algolia Search API
- **No Auth Required**
- **Query:** Search for "arxiv.org" in stories
- **Docs:** https://hn.algolia.com/api

---

## Important Notes

### For AI Assistants Working on This Code

1. **Always Read Before Modifying**
   - Use `Read` tool to view files before making changes
   - Understand existing patterns before adding new code
   - Check related files (models, config, etc.)

2. **Respect Existing Patterns**
   - Database: Always use `get_db_session()` context manager
   - Logging: Use `loguru.logger`, not `print()`
   - Config: Add to `src/config.py` and `.env.example`
   - Errors: Catch specific exceptions, log properly

3. **Don't Over-Engineer**
   - Keep solutions simple and focused
   - Only add what's requested
   - Don't add extra features "for the future"
   - Avoid premature abstractions

4. **Maintain Documentation**
   - Update this file when adding major features
   - Update docstrings for new functions
   - Update .env.example for new config
   - Keep README.md user-focused

5. **Test Your Changes**
   - Run `python main.py --stats` to verify DB connection
   - Test CLI commands manually
   - Check logs for errors
   - Consider edge cases

6. **Security**
   - Never commit API keys or secrets
   - Always use environment variables
   - Validate user input in CLI commands
   - Use parameterized SQL queries (ORM does this)

7. **Cost Awareness**
   - Use Haiku for simple extraction tasks
   - Use Sonnet for complex explanations
   - Batch API calls when possible
   - Implement caching to avoid redundant calls

### Current State (Week 1 Implementation)

✅ **Completed:**
- Project structure and setup
- Configuration management
- Database schema and models
- CLI framework
- Logging infrastructure
- ArXiv discovery (basic)

🚧 **In Progress:**
- Reader agent (analysis)
- Explainer agent
- Email digest generation

📋 **Upcoming:**
- Week 2: Social signals (Twitter, HN)
- Week 3: Citation tracking and velocity
- Week 4: Knowledge graph visualization
- Week 5: Reading progress dashboard
- Week 6: Production polish and synthesis

### Getting Help

- **LangGraph Docs:** https://python.langchain.com/docs/langgraph
- **Claude API:** https://docs.anthropic.com/
- **SQLAlchemy:** https://docs.sqlalchemy.org/
- **Streamlit:** https://docs.streamlit.io/
- **Design Doc:** `docs/design.md`
- **Project Plan:** `docs/project_plan.md`

---

## Quick Reference

### Common Commands
```bash
# Setup
python main.py --init-db

# Discover papers
python main.py --discover --days 1

# Check status
python main.py --stats

# Debug mode
python main.py --discover --debug

# Reset database
python main.py --init-db --reset --yes
```

### Import Patterns
```python
# Configuration
from src.config import settings, get_research_interests_list

# Database
from src.database import get_db_session, init_db
from src.models.paper import Paper, Citation, SocialSignal

# Logging
from loguru import logger

# Agents (when implemented)
from src.agents.discovery import discover_papers
```

### Database Queries
```python
# Simple query
with get_db_session() as db:
    papers = db.query(Paper).all()

# Filter
with get_db_session() as db:
    paper = db.query(Paper).filter_by(arxiv_id="2312.12345").first()

# Complex
with get_db_session() as db:
    papers = db.query(Paper)\
        .filter(Paper.relevance_score > 0.8)\
        .order_by(Paper.published_date.desc())\
        .limit(10)\
        .all()
```

---

**End of CLAUDE.md**

This document should be updated as the project evolves. When adding major features, update the relevant sections to keep this guide accurate and useful.
