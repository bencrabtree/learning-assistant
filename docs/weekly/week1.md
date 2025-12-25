# Week 1: Foundation + Deep Paper Analysis

**Timeline:** Wed 12/25 - Sat 12/28 (3 days)
**Goal:** Individual paper deep-dive with full auditability
**Focus:** Make single-paper analysis AMAZING
**Deliverable:** Interactive CLI showing rich paper analysis

---

## ✅ Day 1 (Wed 12/25): Foundation - COMPLETE

**Completed:**
- ✅ Project structure setup
- ✅ Database models (Paper, Citation, SocialSignal)
- ✅ Configuration management (pydantic settings)
- ✅ Basic arXiv discovery
- ✅ Logging infrastructure
- ✅ Pre-commit hooks (Black, Ruff, MyPy, Bandit)
- ✅ GitHub Actions CI/CD
- ✅ Testing framework (pytest with >80% coverage requirement)

---

## 🔨 Day 2 (Thu 12/26): Reader + Explainer + Citations

**Goal:** Deep paper analysis with Claude + citation data

### Tasks (TDD Approach)

#### 1. Write Tests FIRST (30 min)
```python
# tests/test_reader_agent.py
def test_reader_extracts_structured_info():
    """Reader agent extracts main_claim, methodology, key_results."""
    pass

def test_reader_handles_claude_api_failure():
    """Reader agent gracefully handles API failures."""
    pass

def test_reader_batch_processing():
    """Reader agent can analyze multiple papers efficiently."""
    pass

# tests/test_explainer_agent.py
def test_explainer_generates_eli5_summary():
    """Explainer generates accessible ELI5 summaries."""
    pass

def test_explainer_creates_learning_questions():
    """Explainer creates relevant learning questions."""
    pass

# tests/test_semantic_scholar.py
def test_fetch_citation_count():
    """Semantic Scholar client fetches citation counts (mocked)."""
    pass

def test_batch_citation_fetching():
    """Can fetch citations for multiple papers in batch."""
    pass
```

#### 2. Implement Reader Agent (1-2 hours)

**File:** `src/agents/reader.py`

```python
class ReaderAgent:
    """
    Analyzes papers using Claude Haiku for structured extraction.

    Extracts:
    - main_claim: Core thesis of the paper
    - methodology: Research approach
    - key_results: Main findings
    - novel_contributions: What's new
    - limitations: Known weaknesses
    - concepts: Key technical concepts
    """

    def analyze_paper(self, paper: dict) -> dict:
        """Analyze a single paper."""
        pass

    def batch_analyze(self, papers: list[dict]) -> list[dict]:
        """Analyze multiple papers efficiently."""
        pass
```

**Key Features:**
- Use Claude 3.5 Haiku (fast, cheap: ~$0.001/paper)
- Structured JSON output with pydantic validation
- Error handling with retries
- Cost tracking
- Batch processing for efficiency

#### 3. Implement Explainer Agent (1-2 hours)

**File:** `src/agents/explainer.py`

```python
class ExplainerAgent:
    """
    Generates learning-friendly explanations using Claude Sonnet.

    Generates:
    - eli5_summary: Explain Like I'm 5 summary
    - key_insight: The one thing to remember
    - learning_questions: Questions to deepen understanding
    - prerequisites: What to know first
    - related_concepts: Connected ideas
    """

    def explain_paper(self, paper: dict, analysis: dict) -> dict:
        """Generate explanation for analyzed paper."""
        pass
```

**Key Features:**
- Use Claude 3.5 Sonnet (better explanations: ~$0.015/paper)
- Takes Reader output as context
- Learning-focused prompts
- Cost tracking

#### 4. Implement Semantic Scholar Integration (1 hour)

**File:** `src/services/semantic_scholar.py`

```python
class SemanticScholarClient:
    """
    Free citation data from Semantic Scholar API.

    Rate limits:
    - Without API key: 100 req/5min
    - With free API key: 5000 req/5min
    - Batch: Up to 500 IDs per request
    """

    def get_citation_count(self, arxiv_id: str) -> int:
        """Get citation count for arXiv paper."""
        pass

    def batch_get_citations(self, arxiv_ids: list[str]) -> dict:
        """Get citations for multiple papers efficiently."""
        pass

    def get_influential_citations(self, arxiv_id: str) -> list:
        """Get highly influential citations."""
        pass
```

**Key Features:**
- FREE API (no cost!)
- Batch requests for efficiency
- Caching (24h TTL)
- Citation velocity tracking (prep for Week 2)

#### 5. Integration Tests (30 min)

```python
# tests/test_full_analysis_pipeline.py
def test_discovery_to_analysis_pipeline(test_db):
    """Full workflow: discover → analyze → explain → save."""
    # 1. Discover papers (mocked arXiv)
    # 2. Analyze with Reader (mocked Claude Haiku)
    # 3. Explain with Explainer (mocked Claude Sonnet)
    # 4. Fetch citations (mocked Semantic Scholar)
    # 5. Save to database
    # 6. Verify all fields populated
    pass
```

#### 6. Update Database Models (30 min)

**File:** `src/models/paper.py`

Add fields:
```python
# Reader Agent outputs
main_claim: str | None
methodology: str | None
key_results: str | None
novel_contributions: str | None
limitations: str | None
concepts: list[str]  # JSON field
analyzed_at: datetime | None

# Explainer Agent outputs
eli5_summary: str | None
key_insight: str | None
learning_questions: list[str]  # JSON field
prerequisites: list[str]  # JSON field
related_concepts: list[str]  # JSON field
explained_at: datetime | None

# Citation data (Semantic Scholar)
citation_count: int
influential_citation_count: int
citations_updated_at: datetime | None
```

### Acceptance Criteria

- ✅ All unit tests pass (>80% coverage)
- ✅ Integration test: full pipeline works
- ✅ Mocked Claude API (don't burn credits in tests)
- ✅ Mocked Semantic Scholar API
- ✅ Type hints on all functions
- ✅ Black/Ruff/MyPy pass
- ✅ Database migration successful
- ✅ Manual test with 1-2 real papers

### Test Commands

```bash
# Run tests
pytest tests/test_reader_agent.py -v
pytest tests/test_explainer_agent.py -v
pytest tests/test_semantic_scholar.py -v

# Coverage check
pytest --cov=src/agents --cov=src/services --cov-report=term-missing

# Integration test
pytest tests/test_full_analysis_pipeline.py -v

# Manual test (uses real APIs)
python -c "
from src.agents.reader import ReaderAgent
from src.agents.explainer import ExplainerAgent

# Analyze one paper
reader = ReaderAgent()
result = reader.analyze_paper({'arxiv_id': '2312.12345', ...})
print(result)
"
```

---

## 🔨 Day 3 (Fri 12/27): Interactive CLI

**Goal:** Beautiful terminal UI with `rich` library

### Tasks (TDD Approach)

#### 1. Write Tests FIRST (30 min)

```python
# tests/test_cli_browser.py
def test_paper_rendering():
    """CLI renders paper details correctly."""
    pass

def test_color_coding_by_importance():
    """Papers color-coded by relevance score."""
    pass

def test_empty_database_handling():
    """Graceful handling of empty database."""
    pass

# tests/test_cli_navigation.py (snapshot tests)
def test_paper_list_format():
    """Paper list matches expected format."""
    pass
```

#### 2. Implement CLI Browser (2-3 hours)

**File:** `src/cli/browser.py`

```python
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

class PaperBrowser:
    """Interactive terminal browser for papers."""

    def display_papers(self, papers: list[Paper]):
        """Display papers in a beautiful table."""
        pass

    def display_paper_details(self, paper: Paper):
        """Show full details for a single paper."""
        pass

    def render_analysis(self, paper: Paper):
        """Render analysis section (Reader output)."""
        pass

    def render_explanation(self, paper: Paper):
        """Render explanation section (Explainer output)."""
        pass
```

**Features:**
- Rich table with columns: Rank, Title, Authors, Date, Citations, Score
- Color-coded rows:
  - 🔴 Red (score 0.9-1.0): Must read
  - 🟡 Yellow (score 0.7-0.9): Should read
  - 🟢 Green (score <0.7): Optional
- Scrollable with arrow keys (using `rich.prompt`)
- Full paper details on selection
- Audit trail visible (analyzed_at, explained_at)

#### 3. Add CLI Commands (1 hour)

**File:** `main.py`

```python
@click.command()
@click.option('--browse', is_flag=True, help='Browse papers in interactive CLI')
@click.option('--days', default=1, help='Papers from last N days')
def cli(browse, days):
    if browse:
        handle_browse(days)
```

### Acceptance Criteria

- ✅ Unit tests for all CLI components
- ✅ Snapshot tests for formatting (verify output matches expected)
- ✅ Manual QA: actually use it and verify UX
- ✅ Error handling tested (empty DB, malformed data)
- ✅ Audit info visible (analyzed_at timestamps)

### Test Commands

```bash
# Run CLI (manual test)
python main.py --discover --days 1
python main.py --browse --days 1

# Should see:
# - Beautiful table of papers
# - Color-coded by importance
# - Can view details
# - Shows analysis + explanation + citations
```

---

## 🔨 Day 4 (Sat 12/28): Polish + Audit

**Goal:** Production-ready analysis pipeline

### Tasks

#### 1. Basic Scoring Algorithm (1 hour)

**File:** `src/agents/curator.py`

```python
def calculate_relevance_score(paper: dict, interests: list[str]) -> float:
    """
    Simple keyword-based scoring for Week 1.

    Week 2 will add:
    - Social signals (Twitter, HN)
    - Lab prestige weighting
    - Citation velocity
    - LLM-powered relevance
    """
    # For now: simple keyword matching
    pass
```

**Tests:**
```python
def test_keyword_matching_score():
    """Papers with matching keywords score higher."""
    pass

def test_score_normalization():
    """Scores normalized to 0-1 range."""
    pass
```

#### 2. Audit Logging (1 hour)

**File:** `src/utils/audit.py`

```python
def log_analysis_event(paper_id: str, event_type: str, metadata: dict):
    """Log analysis events for debugging."""
    pass

def get_audit_trail(paper_id: str) -> list[dict]:
    """Get full audit trail for a paper."""
    pass
```

**Audit events:**
- `discovered`: When paper found
- `analyzed`: When Reader agent processed
- `explained`: When Explainer agent processed
- `citations_fetched`: When Semantic Scholar called
- `scored`: When Curator scored

#### 3. Error Handling (1 hour)

**Tests:**
```python
def test_claude_api_failure_handling():
    """Graceful handling of Claude API failures."""
    pass

def test_semantic_scholar_rate_limit():
    """Retry with backoff on rate limits."""
    pass

def test_database_connection_error():
    """Proper error logging on DB failures."""
    pass
```

#### 4. End-to-End Test (1 hour)

```python
# tests/test_e2e_week1.py
def test_full_week1_workflow():
    """
    End-to-end test of Week 1 functionality:
    1. Discover papers from arXiv
    2. Analyze with Reader agent
    3. Explain with Explainer agent
    4. Fetch citations
    5. Score papers
    6. Browse in CLI
    7. Verify audit logs
    """
    pass
```

#### 5. Coverage Report (30 min)

```bash
# Generate coverage report
pytest --cov=src --cov-report=html --cov-report=term-missing

# Review uncovered lines
open htmlcov/index.html

# Add tests for edge cases
# Target: >80% coverage
```

### Acceptance Criteria

- ✅ >80% test coverage overall
- ✅ All error paths tested
- ✅ E2E test passes
- ✅ No flaky tests
- ✅ Audit trail complete
- ✅ Pre-commit hooks pass
- ✅ CI/CD green

---

## Week 1 Final Deliverable

### What You Can Do

```bash
# 1. Discover papers from arXiv
python main.py --discover --days 1

# 2. Browse papers in beautiful terminal UI
python main.py --browse --days 1
```

### What You See

**Terminal output:**
```
┌─────────────────────────────────────────────────────────────────┐
│                     ArXiv Papers (Last 1 Day)                   │
├───┬─────────────────────────┬────────────┬────────┬────────────┤
│ # │ Title                   │ Authors    │  Cites │  Score     │
├───┼─────────────────────────┼────────────┼────────┼────────────┤
│ 1 │ 🔥 Constitutional AI... │ Anthropic  │    234 │ 0.95 ████  │
│ 2 │ ⚡ GRPO: Generative... │ DeepSeek   │    189 │ 0.89 ███▌  │
│ 3 │ 🧠 Chain-of-Thought... │ Google     │     45 │ 0.78 ███   │
└───┴─────────────────────────┴────────────┴────────┴────────────┘

[Press Enter to view details, Q to quit]
```

**Paper details (on Enter):**
```
═══════════════════════════════════════════════════════════════
Constitutional AI: Harmlessness from AI Feedback
───────────────────────────────────────────────────────────────
Authors: Bai et al. (Anthropic)
Published: 2023-12-06
Citations: 234 (📈 +12% this week)
ArXiv: https://arxiv.org/abs/2312.xxxx

📊 ANALYSIS (analyzed 2025-12-26 14:32)
───────────────────────────────────────────────────────────────
Main Claim: Constitutional AI enables models to self-improve
           harmlessness through AI feedback rather than human
           feedback alone.

Methodology: Two-stage RLHF with critique and revision

Key Results:
  • Reduced harmfulness by 50% with minimal helpfulness loss
  • Scales better than pure human feedback
  • Transparent value learning

Concepts: RLHF, Constitutional AI, AI feedback, value alignment

🎓 EXPLANATION (explained 2025-12-26 14:35)
───────────────────────────────────────────────────────────────
ELI5: Instead of humans telling the AI what's good/bad, we
     give it a "constitution" (rules) and let it judge its
     own responses. Like teaching someone values and letting
     them self-correct.

Key Insight: You can make AI safer by teaching it principles
            rather than labeling every single example.

Learning Questions:
  1. How does CAI compare to traditional RLHF?
  2. What makes a good "constitution"?
  3. Can this work for other values beyond harmlessness?

Prerequisites:
  • RLHF basics
  • Preference learning

═══════════════════════════════════════════════════════════════
```

---

## Success Metrics

- ✅ Can discover papers from arXiv (last N days)
- ✅ Claude extracts structured info (Reader)
- ✅ Claude creates ELI5 explanations (Explainer)
- ✅ Citation counts from Semantic Scholar (free!)
- ✅ Beautiful interactive CLI with `rich`
- ✅ Full audit trail (analyzed_at, explained_at, etc.)
- ✅ >80% test coverage
- ✅ All CI/CD checks passing
- ✅ Cost: ~$5-10 for 100 papers

---

## Troubleshooting

**Tests failing:**
```bash
# Check pre-commit hooks
pre-commit run --all-files

# Run tests with verbose output
pytest -vv --tb=long

# Check coverage
pytest --cov=src --cov-report=term-missing
```

**API errors:**
```bash
# Verify .env file
cat .env | grep ANTHROPIC_API_KEY

# Test Claude connection
python -c "from src.services.claude_client import ClaudeClient; print(ClaudeClient().test_connection())"
```

**Database issues:**
```bash
# Reset database
python main.py --init-db --reset --yes

# Check schema
sqlite3 data/papers.db ".schema papers"
```

---

[← Back to Project Plan](../project_plan.md) | [Week 2 →](week2.md)
