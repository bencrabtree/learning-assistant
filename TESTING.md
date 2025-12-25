# Testing Documentation

Comprehensive testing setup for the ArXiv Learning Assistant.

## Quick Start

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_discovery.py
```

## Environment Setup

### Automatic Environment Mocking

Tests automatically mock required environment variables - **no `.env` file needed**:

```python
# tests/conftest.py sets at import time:
ANTHROPIC_API_KEY=sk-ant-test-key-mock-for-testing
DATABASE_URL=sqlite:///:memory:
LOG_LEVEL=ERROR
```

This ensures:
- ✅ Tests run in CI/CD without configuration
- ✅ No accidental API calls during testing
- ✅ No production data access
- ✅ Fast execution (in-memory database)

## Test Organization

### Discovery Agent Tests (`test_discovery.py`)

Tests arXiv paper discovery functionality.

**Coverage:**
- Query building for arXiv API
- Paper fetching and parsing
- Date filtering with timezone awareness
- ArXiv ID extraction from URLs

**Key Regression Tests:**
- Timezone-aware datetime comparison
- ArXiv API attribute usage (`.summary` not `.abstract`)
- Date comparison edge cases

**Documented Bug Fixes:**
1. **Timezone Bug**: Using `datetime.now()` instead of `datetime.now(timezone.utc)` caused comparison errors
2. **Field Naming Bug**: Accessing `result.abstract` instead of `result.summary` from arXiv API

### Database Tests (`test_database.py`)

Tests database operations with isolated in-memory database.

**Coverage:**
- SQLAlchemy session management
- Context manager functionality
- Paper model CRUD operations
- Primary key constraints
- Timestamp automation
- Query operations

### Claude Client Tests (`test_claude_client.py`)

Tests Claude API wrapper for proper parameter formatting.

**Coverage:**
- System prompt format validation (list of text blocks)
- API parameter construction
- JSON response parsing
- Markdown code block stripping
- Retry logic for malformed JSON
- Cost estimation
- Singleton pattern

**Critical Regression Tests:**
- **System Prompt Format**: Ensures system parameter is formatted as `[{"type": "text", "text": "..."}]` not plain string
- **System Prompt Omission**: Verifies system parameter is excluded when not provided

### Reader Agent Tests (`test_reader.py`)

Tests Claude API integration for paper analysis.

**Coverage:**
- Structured extraction with JSON mode
- Prompt construction
- Batch processing
- Error handling and fault tolerance

### Explainer Agent Tests (`test_explainer.py`)

Tests learning-friendly explanation generation.

**Coverage:**
- ELI5 summary generation
- Learning question generation
- Prerequisite analysis check
- Claude Sonnet integration

### Graph Workflow Tests (`test_graph.py`)

Tests LangGraph orchestration.

**Coverage:**
- Node execution
- State management and propagation
- Error handling in workflows
- Multiple pipeline variants (full, discovery-only, analysis-only)

### Integration Tests (`test_integration.py`, `test_pipeline.py`)

Tests end-to-end workflows.

**Coverage:**
- Complete pipeline execution
- Database persistence across agents
- Configuration loading
- Agent initialization
- Fault tolerance

## Running Tests

### Basic Commands

```bash
# All tests
pytest

# Specific test file
pytest tests/test_discovery.py

# Specific test
pytest tests/test_discovery.py::TestDiscoveryAgent::test_build_query_single_category

# With verbose output
pytest -v

# Stop on first failure
pytest -x
```

### Coverage Reports

```bash
# Generate coverage report
pytest --cov=src --cov-report=html

# Open coverage report
open htmlcov/index.html
```

### Debugging Tests

```bash
# Show print statements
pytest -s

# Verbose with print statements
pytest -v -s

# Show slowest tests
pytest --durations=10
```

## Writing Tests

### Test Structure

```python
class TestMyFeature:
    """Test suite for my feature."""

    def test_basic_functionality(self):
        """Test description."""
        # Arrange
        input_data = {...}

        # Act
        result = my_function(input_data)

        # Assert
        assert result == expected
```

### Using Database Session

```python
def test_create_paper(db_session, sample_paper_data):
    """Test with isolated database."""
    # Create
    with db_session() as db:
        paper = Paper(**sample_paper_data)
        db.add(paper)

    # Verify
    with db_session() as db:
        found = db.query(Paper).filter_by(
            arxiv_id=sample_paper_data["arxiv_id"]
        ).first()
        assert found is not None
```

### Using Mock ArXiv Results

```python
def test_arxiv_parsing(mock_arxiv_result):
    """Test with mocked arXiv API response."""
    # Mock already has proper structure
    assert mock_arxiv_result.summary == "This is the paper abstract"
    assert mock_arxiv_result.authors[0].name == "Alice Smith"
```

### Testing Exception Handling

```python
def test_duplicate_paper(db_session, sample_paper_data):
    """Test duplicate detection."""
    from sqlalchemy.exc import IntegrityError

    with db_session() as db:
        paper = Paper(**sample_paper_data)
        db.add(paper)

    # Try to add duplicate
    with pytest.raises(IntegrityError):
        with db_session() as db:
            duplicate = Paper(**sample_paper_data)
            db.add(duplicate)
```

## Test Principles

### 1. Test Bug Fixes, Don't Comment Them

From CLAUDE.md Section 4:

❌ **Bad:**
```python
# Fix: arxiv library uses 'summary' not 'abstract'
paper_data = {"abstract": result.summary.strip()}
```

✅ **Good:**
```python
# Clean code
paper_data = {"abstract": result.summary.strip()}

# Regression test prevents bug from returning
def test_arxiv_result_uses_summary_not_abstract():
    """Ensure we use result.summary not result.abstract."""
    assert paper_data["abstract"] == mock_result.summary
```

### 2. Isolated Tests

- Each test runs independently
- No shared state between tests
- Fresh database for each test
- No production data contamination

### 3. Fast Tests

- In-memory database (no disk I/O)
- Mocked external APIs
- Parallel execution safe

## Shared Fixtures

Defined in `tests/conftest.py`:

- `test_engine` - In-memory SQLite database
- `test_session` - Isolated database session factory
- `db_session` - Database session context manager
- `mock_arxiv_result` - Mock arXiv API response
- `sample_paper_data` - Sample paper dictionary

## Troubleshooting

### Tests Fail with "Missing ANTHROPIC_API_KEY"

Should never happen with current setup. If it does:

```bash
# Verify conftest.py has environment setup
grep "ANTHROPIC_API_KEY" tests/conftest.py
```

### Tests Hit Production Database

Should never happen. Tests use `:memory:` database. Check test isolation:

```bash
# Verify in-memory database
pytest tests/test_database.py::TestDatabaseSession::test_session_context_manager -v
# Should show 0 papers in fresh database
```

### Tests Are Slow

```bash
# Show slowest tests
pytest --durations=10

# All tests should be < 0.1s with in-memory database
```

## CI/CD Integration

Tests run in CI without any setup:

```yaml
# .github/workflows/test.yml
- name: Run tests
  run: pytest -v
```

No environment variables or database configuration needed!

## Best Practices

1. **Always use fixtures** - `db_session`, `mock_arxiv_result`, `sample_paper_data`
2. **Test one thing** - Each test verifies a single behavior
3. **Use descriptive names** - `test_timezone_aware_datetime_comparison_works`
4. **Add regression tests** - For every bug fix
5. **Keep tests fast** - Mock external APIs, use in-memory database
6. **Run tests before commit** - Ensure nothing breaks

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html)
- [Mocking with unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [CLAUDE.md](CLAUDE.md) - Testing principles (Section 4)
