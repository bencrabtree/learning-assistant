# CLAUDE.md - Development Guide & Steering Logic

**Last Updated:** December 2025
**Purpose:** Best practices, coding preferences, and development steering for AI assistants and contributors

---

## Project Overview

This is a **learning project** building an AI-powered research assistant for arXiv papers. The primary goal is to learn LangGraph and multi-agent systems while creating something useful.

**For detailed project information**, see [README.md](README.md) (motivation, features, architecture).
**For milestone breakdowns**, see [docs/milestones/](docs/milestones/) (work backwards from ideal goals).

**This document focuses on HOW to develop**, not WHAT to build.

---

## Development Philosophy

### 1. Learning First, Production Second

**This is a learning project.** Priorities:

1. **Understand LangGraph patterns** (shared context, evolution, auditability)
2. **Build incrementally** (each milestone delivers usable value)
3. **Document learnings** (write down what you discover)
4. **Experiment freely** (try things, fail fast, iterate)

**Not a production SaaS.** Don't over-engineer for scale we don't need.

### 2. Incremental Value Delivery

Each milestone should deliver **working, usable features**:

- ✅ Milestone 1: Can analyze and explain papers (immediate value)
- ✅ Milestone 2: Can rank by social proof (builds on M1)
- ✅ Milestone 3: Can detect trending papers (builds on M1+M2)

**Avoid:** Building infrastructure that won't be used for months.

### 3. Simple Solutions First

**Default to the simplest thing that works:**

- SQLite before PostgreSQL
- Keyword matching before ML embeddings
- Rule-based recommendations before neural networks
- Synchronous before async (unless obviously needed)

**Complexity when needed:** If simple solution has clear limitations, upgrade.

---

## Critical Architecture Principles

### 1. Single Execution Path Through LangGraph

**All orchestration MUST go through LangGraph workflows.**

✅ **Correct:**
```python
# main.py - CLI layer
from src.graph import run_discovery_pipeline

def handle_discover(args):
    result = run_discovery_pipeline(days_back=args.days)
```

❌ **Wrong:**
```python
# main.py - Calling agents directly
from src.agents.reader import ReaderAgent

def handle_discover(args):
    reader = ReaderAgent()  # Bypasses graph!
    reader.analyze_papers(papers)
```

**Why:** LangGraph IS the orchestration layer. Bypassing it creates inconsistent paths.

### 2. All Imports at Top of File

**No lazy imports inside functions** (except for rare circular dependencies).

✅ **Correct:**
```python
from src.models.paper import Paper
from src.agents.reader import ReaderAgent

def analyze():
    reader = ReaderAgent()
```

❌ **Wrong:**
```python
def analyze():
    from src.agents.reader import ReaderAgent  # Don't do this
```

**Why:** Makes dependencies obvious, fails fast, standard Python practice.

### 3. Layer Separation

| Layer | Responsibility | Examples |
|-------|---------------|----------|
| **Agents** | Business logic | `ReaderAgent.analyze_paper()` |
| **Graph** | Orchestration | `run_discovery_pipeline()` |
| **CLI** | User interface | `handle_discover()` |
| **Database** | Persistence | `get_db_session()` |
| **Services** | External APIs | `ClaudeClient.chat()` |

**Don't mix layers.** CLI doesn't call agents directly. Agents don't call graph.

### 4. Test Bug Fixes, Don't Comment Them

❌ **Wrong:**
```python
# Fix: arxiv library uses 'summary' not 'abstract'
paper_data = {
    "abstract": result.summary.strip(),  # Bug fix: was result.abstract
}
```

✅ **Correct:**
```python
# Code is clean
paper_data = {
    "abstract": result.summary.strip(),
}
```

**With test:**
```python
def test_arxiv_result_parsing():
    """Ensure we correctly parse arXiv API Result objects."""
    mock_result = Mock()
    mock_result.summary = "This is the abstract"

    agent = DiscoveryAgent()
    paper_data = agent._parse_result(mock_result)

    assert paper_data["abstract"] == "This is the abstract"
```

**Why:** Tests prevent regressions. Comments clutter code. Tests document behavior.

---

## Testing & Quality Standards

### Pre-Push Validation

**ALWAYS run before pushing:**

```bash
./scripts/validate-ci.sh
```

This runs **exactly** what GitHub Actions will run:
- Black formatting
- isort import sorting
- Ruff linting
- MyPy type checking
- Bandit security scan
- Unit tests (80% coverage requirement)
- Integration tests

**Zero wasted CI/CD runs. Zero wasted time.**

### Testing Standards

**Unit tests:**
- Required for all new code
- 80% coverage threshold
- Fast (< 0.1s per test)
- Isolated (mock external dependencies)

**Integration tests:**
- Mark with `@pytest.mark.integration`
- Test workflow orchestration
- No coverage requirement (they test integration, not code paths)
- Run separately: `pytest -m integration`

**Test organization:**
```
tests/
├── conftest.py           # Shared fixtures
├── test_*.py             # Test files mirror src/ structure
└── agents/
    ├── test_reader.py
    └── test_explainer.py
```

### Code Quality Checklist

Before committing:

- [ ] All imports at top of file
- [ ] All orchestration in `src/graph.py`
- [ ] `main.py` only calls graph workflows
- [ ] Agents don't call other agents
- [ ] Functions have docstrings
- [ ] Follows existing patterns
- [ ] Bug fixes have unit tests
- [ ] Ran `./scripts/validate-ci.sh` and all checks passed

---

## Pull Request Guidelines

### Always Create Descriptive PRs

**Branch naming:**
- `feat/email-digest` - New features
- `fix/claude-api-format` - Bug fixes
- `refactor/agent-structure` - Code refactoring
- `docs/update-readme` - Documentation

**PR template location:** `.github/pull_request_template.md`

This template automatically populates when you create a PR on GitHub. Fill out ALL sections completely.

**Why:** PR descriptions are documentation for future reference and serve as release notes.

### Step-by-Step PR Creation Process

**1. Pre-Push Validation (CRITICAL)**

Before creating a PR, **always** run the validation script:

```bash
./scripts/validate-ci.sh
```

This ensures:
- ✅ Code is formatted (Black)
- ✅ Imports are sorted (isort)
- ✅ No lint errors (Ruff)
- ✅ Type checking passes (MyPy)
- ✅ Security scan passes (Bandit)
- ✅ Unit tests pass with >80% coverage
- ✅ Integration tests pass

**If any check fails, fix it before pushing.** This saves CI/CD time and tokens.

**2. Commit Your Changes**

```bash
# Stage all changes
git add -A

# Create descriptive commit
git commit -m "feat: Add email digest functionality

- Implement daily email scheduling
- Add HTML email templates
- Configure SMTP settings
"

# Verify commit
git log -1
```

**3. Push to Remote**

```bash
# Push with upstream tracking
git push -u origin your-branch-name

# Example:
git push -u origin feat/email-digest
```

**4. Create Pull Request**

GitHub will show a URL after pushing:
```
remote: Create a pull request for 'your-branch-name' on GitHub by visiting:
remote:      https://github.com/user/repo/pull/new/your-branch-name
```

Visit that URL or use GitHub CLI:
```bash
gh pr create --title "Your PR Title" --body "PR description here"
```

**5. Fill Out PR Description**

Use the template and fill in ALL sections:

```markdown
## Summary
[1-2 sentence description of what this accomplishes]

## Changes
- [Specific change 1 with file/function references]
- [Specific change 2]
- [Specific change 3]

## Testing
- [x] All tests pass locally (`./scripts/validate-ci.sh`)
- [x] Added new tests for [specific functionality]
- [x] Manually tested [specific scenarios]

## Type of Change
- [x] Bug fix
- [ ] New feature
- [ ] Refactor
- [ ] Documentation
- [ ] Tests
```

**6. Request Review (if applicable)**

- Assign reviewers if working with a team
- Link related issues with `Fixes #123` or `Relates to #456`
- Add labels (bug, enhancement, documentation, etc.)

### PR Review Checklist

Before requesting review, verify:

- [ ] PR title is clear and descriptive
- [ ] All sections of template are filled out
- [ ] Changes are focused (one feature/fix per PR)
- [ ] No unrelated changes included
- [ ] Tests cover new functionality
- [ ] Documentation updated if needed
- [ ] No secrets or sensitive data committed
- [ ] CI/CD checks are passing

### Common PR Mistakes to Avoid

❌ **Don't:**
- Create PR without running `validate-ci.sh` first
- Leave template sections blank or with placeholder text
- Mix unrelated changes in one PR
- Commit commented-out code or debug statements
- Push directly to main branch
- Include secrets in commit history

✅ **Do:**
- Run validation before every push
- Write descriptive commit messages
- Keep PRs focused and atomic
- Reference related issues
- Update documentation with code changes
- Clean up debug code before committing

---

## Coding Preferences

### 1. Python Style

- **Formatting:** Black (line length 100)
- **Type hints:** Use throughout (modern Python 3.10+ syntax: `str | None` not `Optional[str]`)
- **Docstrings:** Required for all public functions/classes (Google style)
- **Naming:** `snake_case` for functions/variables, `PascalCase` for classes

### 2. Error Handling

**Catch specific exceptions:**

```python
try:
    papers = discover_papers(days_back=1)
except APIRateLimitError:
    logger.warning("Rate limited, backing off...")
    time.sleep(60)
except ConnectionError as e:
    logger.error(f"Network error: {e}")
    raise
```

**Log errors properly:**

```python
from loguru import logger

logger.info("Starting discovery...")
logger.debug(f"API response: {response}")
logger.warning("Rate limit approaching")
logger.error(f"Failed to fetch paper: {error}")
logger.exception("Full traceback:")  # Use in except blocks
```

### 3. Database Operations

**ALWAYS use context managers:**

```python
# ✅ Correct
with get_db_session() as db:
    paper = db.query(Paper).filter_by(arxiv_id="2312.12345").first()
    paper.relevance_score = 0.9
    # Automatically commits on exit

# ❌ Wrong
db = get_db()
paper = db.query(Paper).first()
db.commit()
db.close()  # Easy to forget!
```

### 4. Configuration

- **All secrets in `.env`** - Never hardcode API keys
- **Use Pydantic Settings** - Type-safe configuration
- **Provide defaults** - For non-sensitive settings
- **Document in `.env.example`** - Keep it updated

### 5. Common Patterns

**SQLAlchemy queries:**
```python
with get_db_session() as db:
    # Simple filter
    papers = db.query(Paper).filter_by(arxiv_id="2312.12345").all()

    # Complex query with joins
    papers = db.query(Paper)\
        .join(Citation)\
        .filter(Citation.citation_count > 100)\
        .order_by(Paper.published_date.desc())\
        .limit(10)\
        .all()
```

**Handling duplicates:**
```python
from sqlalchemy.exc import IntegrityError

with get_db_session() as db:
    try:
        db.add(paper)
    except IntegrityError:
        db.rollback()
        logger.warning(f"Paper {paper.arxiv_id} already exists")
```

---

## Common Pitfalls to Avoid

### 1. Over-Engineering

❌ **Don't:**
- Add features not explicitly requested
- Refactor code that works fine
- Create abstractions for one-time use
- Add configuration for hypothetical future needs

✅ **Do:**
- Solve the immediate problem simply
- Only refactor when clear duplication exists
- Add features when requested or clearly needed

### 2. Backwards Compatibility Hacks

❌ **Don't:**
- Rename unused vars to `_var` to keep them
- Re-export types just for compatibility
- Add `# removed` comments for deleted code

✅ **Do:**
- Delete unused code completely
- Trust version control for history
- Make clean breaks when refactoring

### 3. Security Issues

**Always validate at system boundaries:**
- User input (CLI arguments)
- External API responses
- File uploads
- Database queries (use parameterized queries - ORM does this)

**Never:**
- Execute user-provided code
- Concatenate SQL queries with user input
- Trust external data without validation
- Commit secrets to git

---

## Development Workflow

### Initial Setup

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 4. Initialize database
python main.py --init-db

# 5. Verify setup
./scripts/validate-ci.sh
```

### Daily Development

```bash
# Run validation before committing
./scripts/validate-ci.sh

# Run specific tests
pytest tests/test_reader.py -v

# Format code
black --line-length=100 .
isort --profile=black --line-length=100 .

# Lint code
ruff check src/ tests/
```

---

## Learning Objectives

This project focuses on understanding:

1. **LangGraph patterns:**
   - Shared context management
   - State evolution through agents
   - Checkpointing and persistence
   - Audit trails and replay

2. **Multi-agent systems:**
   - Agent specialization (Reader, Explainer, Curator)
   - Parallel execution and state merging
   - Decision logging and observability

3. **Production patterns:**
   - Testing strategies (unit, integration, E2E)
   - Error handling and retry logic
   - Performance optimization (caching, batching)
   - Monitoring and alerting

**For deep dives on LangGraph**, see [docs/langgraph_intro.md](docs/langgraph_intro.md).

---

## Getting Help

- **LangGraph concepts:** [docs/langgraph_intro.md](docs/langgraph_intro.md)
- **Project milestones:** [docs/milestones/](docs/milestones/)
- **Testing guide:** [TESTING.md](TESTING.md)
- **Project overview:** [README.md](README.md)

**External resources:**
- LangGraph Docs: https://python.langchain.com/docs/langgraph
- Claude API: https://docs.anthropic.com/
- SQLAlchemy: https://docs.sqlalchemy.org/

---

## Quick Reference

**Essential commands:**
```bash
# Validate all code before pushing
./scripts/validate-ci.sh

# Run unit tests only (with coverage)
pytest -m "not integration" --cov=src

# Run integration tests only
pytest -m integration

# Format and lint
black --line-length=100 .
ruff check --fix src/ tests/

# Initialize database
python main.py --init-db
```

**Remember:**
1. Run `./scripts/validate-ci.sh` before every push
2. All orchestration goes through LangGraph
3. Test bug fixes, don't comment them
4. Keep it simple until complexity is needed
5. Document learnings as you go

---

**End of CLAUDE.md**

This document should evolve as development patterns emerge. Update it when discovering better approaches or common issues.
