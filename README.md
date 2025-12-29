# ArXiv Learning Assistant

**A personal AI research assistant that helps you stay current with AI research without drowning in papers.**

---

## Project Vision

Transform the overwhelming flood of AI research into a **personalized, systematic learning experience**. This is a learning project focused on understanding LangGraph and multi-agent systems while building something genuinely useful.

**For development practices and coding standards**, see [CLAUDE.md](CLAUDE.md).

---

## The Problem We're Solving

**200-300 AI papers** are published on arXiv **every day**. For researchers, practitioners, and AI enthusiasts, staying current is nearly impossible:

- **Signal vs. Noise:** Most papers aren't relevant to your specific interests
- **Comprehension Barrier:** Complex papers require hours to understand
- **No Learning Path:** Hard to know what order to read papers in
- **Progress Invisible:** Can't track what you've learned or what gaps remain
- **Context Missing:** Papers exist in isolation, relationships unclear

**Current solutions don't work:**
- RSS feeds: Too noisy, no filtering
- Twitter: Fragmented, ephemeral, biased
- Manual tracking: Time-consuming, doesn't scale

**We need a system that:**
1. Finds papers relevant to your interests
2. Explains them in accessible language
3. Ranks them by importance (social proof, citations, trends)
4. Shows how they relate to each other
5. Tracks your learning progress
6. Recommends what to read next

---

## The Solution: Multi-Agent Learning Pipeline

This project builds an autonomous **multi-agent system** using:
- **LangGraph** for workflow orchestration
- **Claude AI** for deep paper analysis and explanation
- **Multiple data sources** for discovery and ranking (arXiv, Twitter, Semantic Scholar)
- **Knowledge graphs** for visualization and relationship mapping

### High-Level Capabilities

**Discovery & Analysis**
- Automatically discover papers from arXiv daily
- Extract structured information (claims, methodology, results)
- Generate accessible explanations (ELI5 summaries, key insights)
- Track citations and compute velocity (papers gaining momentum)

**Ranking & Curation**
- Score by relevance to your research interests
- Incorporate social proof (Twitter mentions, HackerNews discussions)
- Detect trending papers before they become canonical
- Filter noise, surface high-quality papers

**Learning Support**
- Visual knowledge graphs showing paper relationships
- Reading path recommendations (what to read first)
- Progress tracking (papers read, concepts mastered)
- Personalized recommendations based on your journey
- Weekly synthesis reports (themes, insights, connections)

**Automation**
- Fully autonomous operation (scheduled discovery & analysis)
- Daily email digests with top papers
- Weekly learning summaries
- No manual intervention required

---

## Quick Start

### Prerequisites
- Python 3.11+
- Anthropic API key (for Claude)
- Optional: Twitter API key, Semantic Scholar API key

### Setup

```bash
# 1. Clone and create virtual environment
git clone https://github.com/yourusername/learning-assistant
cd learning-assistant
python -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 4. Initialize database
python main.py --init-db

# 5. Test the setup
python main.py --discover --days 1
```

### Basic Usage

```bash
# 1. Run the core workflow - discover and analyze papers
python main.py --discover --days 1 --analyze --max-papers 5

# 2. Explore interactively (RECOMMENDED!)
python main.py --explore
```

That's it! The `--explore` command gives you a rich interactive interface to browse, read, and manage all your papers.

### Interactive Explorer (`--explore`) - Recommended

The `--explore` command launches a **rich Text User Interface (TUI)** for browsing and interacting with your analyzed papers. This is the best way to review your workflow results.

**Main Features:**
- 📊 **Interactive table** - Browse all papers with arrow keys
- 🔍 **Full paper details** - Press Enter to view complete analysis and explanation
- 📖 **Reading tracker** - Mark papers as unread/reading/finished
- 💾 **Export to JSON** - Save papers for further processing
- 🗑️ **Delete papers** - Remove papers you don't need
- 🎨 **Visual status** - See at a glance what's analyzed, explained, and read

**Keyboard Shortcuts:**

*In the paper list:*
- `↑/↓` - Navigate papers
- `Enter` - View paper details
- `q` - Quit application

*In paper detail view:*
- `Esc` or `q` - Back to list
- `e` - Export current paper to JSON file (saved in `exports/` folder)
- `r` - Toggle reading status (unread → reading → finished → unread)
- `d` - Delete paper from database

**Status Indicators:**

*Reading Status:*
- `○` - Unread
- `◐` - Reading
- `●` - Finished

*Processing Status:*
- `✓✓` - Analyzed + Explained (complete)
- `✓` - Analyzed only
- `-` - Not processed yet

**Example Workflow:**
```bash
# 1. Run discovery and analysis
python main.py --discover --days 3 --analyze --max-papers 10

# 2. Launch explorer to review results
python main.py --explore

# 3. Browse with ↑/↓, press Enter on interesting papers
# 4. Mark papers you've read with 'r'
# 5. Export important papers with 'e'
# 6. Delete irrelevant papers with 'd'
```

**Exported Files:**
- Location: `exports/<arxiv_id>_<timestamp>.json`
- Contains: Full metadata, abstract, analysis, explanation, and reading status
- Use for: Building your own tools, importing to notebooks, archiving

---

### Other Commands

**Discovery and Analysis:**
```bash
# Just discover papers (don't analyze yet)
python main.py --discover --days 3

# Analyze previously discovered papers
python main.py --analyze
```

**View Current State (Non-Interactive):**
```bash
python main.py --stats                     # Database statistics
python main.py --list                      # Recent papers (default: 10)
python main.py --list --limit 20           # Show 20 recent papers
python main.py --show 2512.18878v1         # View specific paper details
```

**Export Data as JSON:**
```bash
python main.py --list --format json                      # Export list as JSON
python main.py --show 2512.18878v1 --format json         # Export paper as JSON
```

---

## Technology Stack

### Core Framework
- **LangGraph 0.3+** - Multi-agent orchestration
- **LangChain 0.1+** - LLM framework
- **Claude API** - Paper analysis and explanation

### Data & Storage
- **SQLAlchemy 2.0+** - ORM for database operations
- **SQLite** - Local database (easily upgradable to PostgreSQL)
- **NetworkX** - Graph analysis

### Discovery APIs
- **arXiv** - Paper discovery
- **Semantic Scholar** - Citation data
- **Twitter API** - Social signals
- **HackerNews Algolia** - Community signals

### Visualization
- **Streamlit** - Interactive dashboard
- **PyVis** - Network graph rendering
- **Plotly** - Charts and visualizations

---

## Project Structure

```
learning-assistant/
├── main.py                 # CLI entry point
├── CLAUDE.md              # Development guide (best practices, preferences)
├── TESTING.md             # Testing guide
├── README.md              # This file (project overview)
│
├── src/                   # Source code
│   ├── models/            # Database models (SQLAlchemy ORM)
│   ├── agents/            # LangGraph agents
│   ├── services/          # External service clients
│   ├── graph.py           # LangGraph workflow definitions
│   ├── config.py          # Configuration management
│   └── database.py        # Database connection
│
├── tests/                 # Test files (80%+ coverage)
│   ├── conftest.py        # Shared fixtures
│   └── agents/            # Agent-specific tests
│
├── docs/                  # Documentation
│   ├── milestones/        # Milestone breakdowns (work backwards from goals)
│   ├── design.md          # System architecture & design decisions
│   ├── project_plan.md    # Original 6-week build plan
│   └── langgraph_intro.md # LangGraph concepts and patterns
│
├── scripts/               # Utility scripts
│   ├── validate-ci.sh     # Run all CI/CD checks locally
│   └── check-pr.sh        # Quick pre-PR validation
│
└── data/                  # Database & cache (gitignored)
    └── papers.db          # SQLite database
```

---

## Learning Objectives

This is a **learning project** focused on understanding:

### LangGraph Patterns
- Shared context management (state flowing through agents)
- State evolution over time (tracking changes)
- Checkpointing and persistence (resume workflows)
- Audit trails and replay (debugging and transparency)

### Multi-Agent Systems
- Agent specialization (Reader, Explainer, Curator, etc.)
- Parallel execution and state merging
- Decision logging and observability
- Error handling and retry logic

### Production Patterns
- Testing strategies (unit, integration, E2E with 80%+ coverage)
- Performance optimization (caching, parallel API calls for ~5x speedup)
- Monitoring and alerting
- Automated workflows (scheduled jobs)

**For deep dives**, see:
- [docs/langgraph_intro.md](docs/langgraph_intro.md) - LangGraph concepts explained
- [docs/milestones/](docs/milestones/) - Detailed milestone breakdowns
- [CLAUDE.md](CLAUDE.md) - Development best practices

---

## Development Milestones

The project is structured around **8 major milestones**, each delivering usable value. See [docs/milestones/](docs/milestones/) for detailed breakdowns.

### Milestone 1: Deep Paper Analysis Engine
**Status:** ✅ Complete

**Delivers:** Single-paper deep dive with structured extraction and accessible explanations

**Key features:**
- Reader Agent (Claude Haiku) - Fast, structured extraction
- Explainer Agent (Claude Sonnet) - Learning-oriented explanations
- Citation integration (Semantic Scholar)
- Audit trails for transparency
- Rich CLI with color-coded output

**Value:** Understand a complex paper in minutes rather than hours

---

### Milestone 2: Social Proof & Community Signals
**Status:** ✅ Complete

**Delivers:** Identify "hot papers" via Twitter, HackerNews, and breakthrough detection

**Key features:**
- Twitter tracker (AI lab accounts: Anthropic, OpenAI, DeepMind, etc.)
- HackerNews tracker (Algolia API for arXiv discussions)
- Semantic Scholar integration (citation counts, influential citations)
- AssessorAgent - Breakthrough detection (novelty, impact, evidence, significance)
- CuratorAgent - Multi-signal scoring (interest match + social proof + citations + breakthrough)
- Extended LangGraph workflow: discovery → reader → explainer → signals → assessor → curator

**Value:** Discover important papers before citations accumulate, identify breakthrough research

**Try it:**
```bash
# Run full pipeline with social signals and breakthrough detection
python main.py --discover --days 3 --analyze --max-papers 10

# View results in interactive explorer
python main.py --explore
```

---

### Milestone 3: Research Radar Daemon
**Status:** 🔄 In Progress (PR #14)

**Delivers:** Background monitoring with email notifications for important papers

**Key features:**
- Background daemon with configurable schedule
- Dual discovery mode (new papers + rising/trending older papers)
- Noteworthy filtering (breakthrough score, social signals, relevance)
- Email notifications (HTML/plaintext, Gmail SMTP support)
- CLI commands: `--radar`, `--radar-once`, `--test-email`

**Value:** Proactive notifications when important research appears

---

### Milestone 4: Agentic LangGraph Workflow
**Status:** 📋 Planned

**Delivers:** Truly agentic radar using LangGraph patterns

**Key features:**
- Radar loop as a LangGraph workflow with conditional edges
- Runtime decision-making (notify vs expand search)
- Iterative search with expansion strategies
- State accumulation across iterations
- Autonomous graph-based decision making

**Value:** Learn core LangGraph patterns (conditional routing, state evolution)

---

### Milestone 5: Citation Velocity & Trend Detection
**Status:** 📋 Planned

**Delivers:** Detect papers gaining research momentum

**Key features:**
- Historical citation tracking
- Velocity calculation (citations/week growth rate)
- Breakout detection (papers accelerating)
- Trend analysis across research areas
- "Worth revisiting" recommendations

**Value:** Read papers before they become canonical

---

### Milestone 6: Interactive Knowledge Graph
**Status:** 📋 Planned

**Delivers:** Visual, explorable research landscape

**Key features:**
- NetworkX graph (papers as nodes, citations as edges)
- Graph algorithms (PageRank, community detection, reading paths)
- Interactive visualization (PyVis + Streamlit)
- Topic clustering and influence detection
- Reading order recommendations

**Value:** Understand how papers connect and find your learning path

---

### Milestone 7: Learning Progress & Personalization
**Status:** 📋 Planned

**Delivers:** Track learning journey and get personalized recommendations

**Key features:**
- Reading progress tracking (papers read, time spent, ratings)
- Concept mastery levels (beginner → intermediate → advanced)
- Statistics dashboard (papers/week, streaks, favorite topics)
- Personalized recommendations ("Next to Read", "Fill Gaps", "Related")
- Habit reinforcement (streaks, achievements)

**Value:** Systematic learning path that builds on what you know

---

### Milestone 8: Synthesis & Production Readiness
**Status:** 📋 Planned

**Delivers:** Weekly insights and fully autonomous operation

**Key features:**
- Synthesis Agent (weekly learning reports)
- Knowledge gap detector
- Enhanced emails (daily digest, weekly synthesis)
- Performance optimization (Redis caching, parallel execution)
- Complete automation (scheduled jobs, zero manual work)
- Production reliability (monitoring, error handling, testing)

**Value:** Hands-off system that consolidates learning and delivers insights

---

## Future Enhancements

**Beyond the 8 milestones**, potential extensions include:

- **Multi-user support** - Team research collaboration
- **Zotero/Mendeley integration** - Sync with existing tools
- **Mobile app** - Read on the go
- **Voice interface** - "What should I read today?"
- **Paper summarization podcast** - TTS for learning while commuting
- **Collaborative annotations** - Shared notes and discussions

---

## Contributing

This is primarily a learning project, but contributions are welcome!

**Before contributing:**
1. Read [CLAUDE.md](CLAUDE.md) for coding standards
2. Run `./scripts/validate-ci.sh` before submitting PRs
3. Ensure 80%+ test coverage for new code
4. Follow existing architectural patterns

**Areas where help is appreciated:**
- Documentation improvements
- Test coverage expansion
- Performance optimization
- Additional data sources (Reddit, Mastodon, etc.)

---

## Resources

### Documentation
- [CLAUDE.md](CLAUDE.md) - Development guide and best practices
- [TESTING.md](TESTING.md) - Testing guide and standards
- [docs/milestones/](docs/milestones/) - Milestone breakdowns
- [docs/langgraph_intro.md](docs/langgraph_intro.md) - LangGraph patterns
- [docs/design.md](docs/design.md) - Architecture decisions

### External
- [LangGraph Documentation](https://python.langchain.com/docs/langgraph)
- [Claude API Documentation](https://docs.anthropic.com/)
- [arXiv API Guide](https://info.arxiv.org/help/api/index.html)
- [Semantic Scholar API](https://api.semanticscholar.org/)

---

## License

MIT License - See [LICENSE](LICENSE) file for details

---

## Acknowledgments

- **Anthropic** for Claude API and LangGraph framework
- **arXiv** for open access to research papers
- **Semantic Scholar** for citation data

---

**Questions? Issues? Ideas?**

Open an issue on GitHub or reach out via the discussions tab. This is a learning project - questions and suggestions are always welcome!
