# ArXiv Learning Assistant

An intelligent multi-agent system that transforms the overwhelming flood of AI research into personalized, accessible learning materials.

## The Problem

With 200-300 new AI papers published daily on arXiv, staying current with research is nearly impossible. Existing solutions are either too noisy (RSS feeds) or miss important developments (social media). Researchers and practitioners need a way to:

- **Filter** the flood of papers to what's relevant
- **Understand** complex papers without deep expertise in every subfield
- **Track** their learning progress and build knowledge systematically

## The Solution

This system uses a multi-agent architecture built on LangGraph and Claude AI to:

1. **Discover** papers from arXiv based on configurable research interests
2. **Analyze** papers with Claude to extract structured information (claims, methodology, results)
3. **Explain** complex concepts in accessible language with learning-oriented summaries
4. **Curate** content by scoring papers on relevance, novelty, and impact
5. **Store** everything in a queryable knowledge base for later retrieval

The result: A personalized research assistant that helps you stay current without drowning in noise.

## Architecture

### System Design

The application follows a clean, layered architecture with separation of concerns:

```
┌─────────────────────────────────────┐
│     CLI Interface (main.py)         │
├─────────────────────────────────────┤
│  LangGraph Workflows (src/graph.py) │
│  • Discovery Pipeline               │
│  • Analysis Pipeline                │
│  • Full Pipeline                    │
├─────────────────────────────────────┤
│         Agent Layer                 │
│  • Discovery Agent (arXiv API)      │
│  • Reader Agent (Claude Haiku)      │
│  • Explainer Agent (Claude Sonnet)  │
│  • Curator Agent (Scoring)          │
├─────────────────────────────────────┤
│    Persistence Layer                │
│  • SQLAlchemy ORM                   │
│  • SQLite Database                  │
└─────────────────────────────────────┘
```

### Multi-Agent Workflow

Each agent is a specialized component with a single responsibility:

**Discovery Agent**
- Queries arXiv API with configurable categories and date ranges
- Filters papers by publication date and relevance
- Handles duplicate detection and deduplication

**Reader Agent**
- Uses Claude 3.5 Haiku for fast, cost-efficient extraction
- Outputs structured JSON: main_claim, methodology, key_results, concepts, limitations
- Implements error handling and retry logic

**Explainer Agent**
- Uses Claude Sonnet 4.5 for high-quality explanations
- Generates ELI5 summaries, key insights, and learning questions
- Identifies prerequisite concepts for learning paths

**Curator Agent**
- Scores papers based on multiple factors (interest match, novelty, citation velocity)
- Ranks and filters to top N most relevant papers
- Provides transparent scoring breakdowns

### State Management

LangGraph orchestrates agent execution and manages shared state:

```python
PipelineState = {
    "discovered_papers": List[Paper],
    "analyzed_papers": List[Analysis],
    "explained_papers": List[Explanation],
    "final_selection": List[RankedPaper],
    "errors": List[str],
}
```

State flows through the graph, with each agent reading inputs and writing outputs. This enables:
- **Fault tolerance** - Agents continue on partial failures
- **Observability** - Full state inspection at each step
- **Flexibility** - Easy to add/remove agents or change flow

## Key Features

### Intelligent Paper Discovery
- Configurable arXiv category filtering (cs.AI, cs.LG, cs.CL, etc.)
- Date-based queries with timezone-aware filtering
- Duplicate detection using arXiv IDs

### Structured Analysis
- Automated extraction of paper structure (claims, methods, results)
- Identification of key technical concepts and terminology
- Analysis of limitations and future work

### Learning-Oriented Explanations
- ELI5 summaries for quick understanding
- Key insights highlighting the "so what?"
- Learning questions to guide deeper study
- Prerequisite concept identification

### Personalized Curation
- Relevance scoring based on research interests
- Configurable filtering and ranking
- Transparent score components for debugging

### Comprehensive Testing
- 79 unit and integration tests covering all components
- Regression tests for critical bugs
- In-memory database for fast, isolated testing
- See [TESTING.md](TESTING.md) for details

## Technical Implementation

### Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Agent Orchestration | LangGraph | Multi-agent workflow management |
| LLM Integration | Claude AI (Haiku + Sonnet) | Analysis and explanation |
| Data Persistence | SQLAlchemy + SQLite | Structured storage and retrieval |
| Testing | pytest | Unit, integration, and regression tests |
| Configuration | pydantic + python-dotenv | Type-safe settings management |

### Database Schema

The system uses a normalized schema with proper relationships:

```sql
papers (
    arxiv_id PRIMARY KEY,
    title, abstract, authors, published_date,
    categories, pdf_url, discovered_at,
    -- Analysis fields
    main_claim, methodology, key_results, concepts,
    -- Explanation fields
    eli5_summary, key_insight, learning_questions,
    -- Curation fields
    relevance_score, score_components
)
```

### Cost Efficiency

The system is designed to be cost-effective:

- **Discovery**: Free (arXiv API)
- **Reader**: ~$0.001/paper (Haiku)
- **Explainer**: ~$0.015/paper (Sonnet)
- **Total**: ~$0.016/paper

Processing 10 papers/day costs ~$5/month.

## Usage

### Setup

```bash
# 1. Clone and install dependencies
git clone <repository>
cd arxiv-learning-assistant
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys and preferences

# 3. Initialize database
python main.py --init-db
```

### Configuration

Edit `.env` to customize behavior:

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here

# Research interests (comma-separated)
RESEARCH_INTERESTS=transformers,reinforcement learning,multimodal learning

# ArXiv categories to monitor
ARXIV_CATEGORIES=cs.AI,cs.LG,cs.CL,cs.CV

# Curation settings
MAX_PAPERS_PER_DIGEST=10
```

### Running Pipelines

```bash
# Discover and analyze papers from the last day
python main.py --discover --days 1 --analyze

# Discover papers from last week, limit to 5
python main.py --discover --days 7 --max-papers 5

# Analyze already-discovered papers
python main.py --analyze

# View statistics
python main.py --stats
```

### Database Operations

```bash
# View database statistics
python main.py --stats

# Reset database (careful!)
python main.py --init-db --reset --yes

# Enable debug logging
python main.py --debug --discover --days 1
```

## Development

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test suite
pytest tests/test_discovery.py -v
pytest tests/test_reader.py -v
pytest tests/test_claude_client.py -v

# With coverage
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

### Project Structure

```
arxiv-learning-assistant/
├── main.py                    # CLI entry point
├── src/
│   ├── graph.py              # LangGraph workflow definitions
│   ├── config.py             # Configuration management
│   ├── database.py           # Database session management
│   ├── agents/               # Agent implementations
│   │   ├── discovery.py      # arXiv discovery
│   │   ├── reader.py         # Paper analysis
│   │   ├── explainer.py      # Explanation generation
│   │   └── curator.py        # Scoring and ranking
│   ├── models/               # SQLAlchemy models
│   │   └── paper.py          # Paper schema
│   └── services/             # External services
│       └── claude_client.py  # Claude API wrapper
├── tests/                    # Comprehensive test suite
├── docs/                     # Documentation
└── data/                     # Database and logs (gitignored)
```

### Architecture Principles

The codebase follows clean architecture principles:

1. **Single Execution Path** - All orchestration goes through LangGraph workflows
2. **Layer Separation** - CLI → Graph → Agents → Database, no layer skipping
3. **Dependency Injection** - External dependencies (Claude client, database) are injected
4. **Comprehensive Testing** - All agents and workflows have unit and integration tests

See [CLAUDE.md](CLAUDE.md) for detailed development guidelines.

## Documentation

- **[TESTING.md](TESTING.md)** - Complete test suite documentation
- **[docs/design.md](docs/design.md)** - Detailed system architecture
- **[docs/langgraph_intro.md](docs/langgraph_intro.md)** - LangGraph concepts
- **[CLAUDE.md](CLAUDE.md)** - Development principles and patterns

## Future Enhancements

Potential directions for extension:

- **Social Signals**: Integrate Twitter, HackerNews, and Reddit mentions for impact scoring
- **Citation Velocity**: Track paper citations over time to identify emerging trends
- **Knowledge Graphs**: Build concept networks to visualize relationships between papers
- **Email Digests**: Automated daily/weekly summaries of top papers
- **Web Dashboard**: Streamlit interface for exploring papers and tracking progress

## License

MIT License - See LICENSE file for details

---

**Built with LangGraph and Claude AI**
