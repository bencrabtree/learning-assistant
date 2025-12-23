# Test Suite

Unit tests for the ArXiv Learning Assistant with proper database isolation.

## Running Tests

```bash
# All tests
pytest

# Specific file
pytest tests/test_discovery.py

# With verbose output
pytest -v

# With coverage
pytest --cov=src
```

## Test Database Isolation

Tests use an **in-memory SQLite database** that's created fresh for each test. This ensures:
- Tests don't affect production data
- Each test runs in isolation
- Tests are fast (no disk I/O)
- No cleanup needed

### How It Works

```python
# conftest.py provides isolated database fixtures
@pytest.fixture
def db_session(test_session):
    """Provide isolated database session for tests."""
    return test_session

# Tests use the db_session fixture
def test_create_paper(db_session, sample_paper_data):
    with db_session() as db:
        paper = Paper(**sample_paper_data)
        db.add(paper)
```

## Test Coverage

### Discovery Agent Tests (`test_discovery.py`) - 9 tests

Tests the arXiv paper discovery functionality:

#### ✅ Regression Tests for Bug Fixes (4 tests)

**Timezone Comparison Bug:**
- `test_cutoff_date_is_timezone_aware` - Ensures cutoff date is timezone-aware (UTC)
- `test_date_comparison_with_timezone_aware_dates` - Verifies comparisons work
- `test_naive_vs_aware_datetime_comparison_fails` - Documents the original bug
- `test_aware_datetime_comparison_works` - Shows the fix works

**ArXiv API Attribute Bug:**
- `test_arxiv_result_uses_summary_not_abstract` - Ensures we use `result.summary` not `result.abstract`

#### Other Tests (4 tests)

- `test_build_query_single_category` - Query building with one category
- `test_build_query_multiple_categories` - Query building with multiple categories
- `test_parse_arxiv_id_from_url` - Extracting arXiv ID from URLs
- `test_cutoff_date_calculation` - Date arithmetic

### Database Tests (`test_database.py`) - 9 tests

Tests database operations with isolated in-memory database:

**Session Management:**
- `test_session_context_manager` - Context manager works correctly
- `test_session_commits_on_exit` - Auto-commit on context exit

**Paper Model:**
- `test_create_paper` - Create and retrieve papers
- `test_paper_primary_key` - Enforce unique arxiv_id constraint
- `test_paper_timestamps` - Auto-set discovered_at timestamp
- `test_paper_analysis_fields_default_none` - Default values for analysis fields
- `test_update_paper_analysis` - Update papers with analysis data

**Queries:**
- `test_query_unanalyzed_papers` - Filter papers by analyzed_at field
- `test_count_papers_by_category` - Count papers

## Test Principles

From CLAUDE.md Section 4:

**Write unit tests for bug fixes instead of adding inline comments.**

Bad:
```python
# Fix: arxiv library uses 'summary' not 'abstract'
paper_data = {"abstract": result.summary.strip()}
```

Good:
```python
# Just fix the code cleanly
paper_data = {"abstract": result.summary.strip()}

# Then add a regression test
def test_arxiv_result_uses_summary_not_abstract():
    """Ensure we use result.summary not result.abstract."""
    # Test code...
```

## Test Status

✅ **18/18 tests passing** with proper database isolation

## Future Tests Needed

- [ ] Reader agent tests (with mocked Claude API)
- [ ] Explainer agent tests (with mocked Claude API)
- [ ] Curator agent scoring tests
- [ ] LangGraph workflow integration tests
- [ ] Claude API client tests (with request mocking)
