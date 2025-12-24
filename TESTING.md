# Testing Documentation

## Overview

This document provides comprehensive information about the test suite for the ArXiv Learning Assistant project.

## Test Statistics

- **Total Tests:** 65
- **Passing:** 48 (74%)  
- **Failing:** 17 (26% - database session isolation in integration tests)

**Latest Run:** All core discovery and database unit tests passing (100%)!

Integration tests need database session mocking refinement to fully pass.

## Test Categories

### 1. Discovery Agent Tests (`test_discovery.py`) - 18 tests ✅

**Coverage:**
- Query building for arXiv API
- Paper fetching and parsing
- Date filtering with timezone awareness
- Database persistence
- Duplicate handling
- Error recovery

**Key Tests:**
- `test_build_query_single_category` - Validates query string construction
- `test_build_query_multiple_categories` - Tests OR logic for multiple categories
- `test_cutoff_date_is_timezone_aware` - Regression test for timezone bug
- `test_arxiv_result_uses_summary_not_abstract` - Regression test for field naming
- `test_date_comparison_with_timezone_aware_dates` - DateTime comparison safety

**Regression Tests:**
These tests document and prevent previously-fixed bugs:
1. **Timezone Bug**: Using `datetime.now()` instead of `datetime.now(timezone.utc)` caused comparison errors
2. **Field Naming Bug**: Accessing `result.abstract` instead of `result.summary` from arXiv API

### 2. Reader Agent Tests (`test_reader.py`) - 10 tests

**Coverage:**
- Agent initialization
- Prompt construction for Claude API
- Paper analysis with structured extraction
- Missing field handling
- Database persistence
- Batch processing
- Error recovery

**Key Tests:**
- `test_build_analysis_prompt_structure` - Validates prompt contains required fields
- `test_analyze_paper_success` - Tests successful Claude API integration
- `test_analyze_paper_missing_fields` - Tests default value insertion
- `test_save_analysis` - Tests database update operations
- `test_analyze_and_save_continues_on_error` - Tests fault tolerance

**Status:** ⚠️ 8/10 passing (2 failures related to database session isolation)

### 3. Explainer Agent Tests (`test_explainer.py`) - 9 tests

**Coverage:**
- Learning-friendly explanation generation
- Prerequisite paper analysis requirement
- Claude Sonnet integration
- ELI5 summary creation
- Learning question generation
- Database persistence

**Key Tests:**
- `test_build_explanation_prompt_requires_analysis` - Validates prerequisite check
- `test_explain_paper_success` - Tests Claude Sonnet integration
- `test_explain_paper_missing_fields` - Tests graceful degradation
- `test_explain_and_save_skips_unanalyzed` - Tests paper filtering logic

**Status:** ⚠️ 6/9 passing (3 failures related to database session isolation)

### 4. Graph Workflow Tests (`test_graph.py`) - 13 tests

**Coverage:**
- LangGraph node execution
- State management and propagation
- Error handling in workflows
- Full pipeline execution
- Discovery-only pipeline
- Analysis-only pipeline

**Key Tests:**
- `test_discovery_node_success` - Tests discovery node execution
- `test_reader_node_handles_errors` - Tests error propagation
- `test_run_full_pipeline_success` - Tests complete workflow
- `test_state_flows_through_nodes` - Tests state updates

**Status:** ⚠️ 10/13 passing (3 failures in analysis pipeline tests)

### 5. Integration Tests (`test_integration.py`) - 10 tests

**Coverage:**
- End-to-end pipeline execution
- Discovery → Reader → Explainer flow
- Database persistence across agents
- Error recovery and fault tolerance
- Duplicate paper handling
- State propagation through full workflow

**Key Tests:**
- `test_full_pipeline_end_to_end` - Complete workflow validation
- `test_discovery_only_workflow` - Discovery-only flow
- `test_pipeline_continues_after_partial_failures` - Fault tolerance
- `test_duplicate_papers_not_created` - Idempotency check

**Status:** ⚠️ 1/10 passing (9 failures due to Mock object serialization issues)

### 6. Database Tests (`test_database.py`) - 9 tests ✅

**Coverage:**
- SQLAlchemy session management
- Context manager functionality
- Paper model operations
- Primary key constraints
- Timestamp automation
- Query operations

**Key Tests:**
- `test_session_commits_on_exit` - Tests auto-commit behavior
- `test_paper_primary_key` - Tests duplicate prevention
- `test_query_unanalyzed_papers` - Tests filtering logic
- `test_update_paper_analysis` - Tests field updates

**Status:** ✅ 9/9 passing - All database tests pass!

## Running Tests

### All Tests
```bash
source venv/bin/activate
pytest tests/ -v
```

### Specific Test Modules
```bash
pytest tests/test_discovery.py -v      # Discovery agent
pytest tests/test_reader.py -v         # Reader agent
pytest tests/test_explainer.py -v      # Explainer agent
pytest tests/test_graph.py -v          # Workflows
pytest tests/test_integration.py -v    # Integration
pytest tests/test_database.py -v       # Database
```

### With Coverage
```bash
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

### Run Only Passing Tests
```bash
pytest tests/test_discovery.py tests/test_database.py -v
```

## Known Issues & Solutions

### Issue 1: Integration Test Mock Serialization
**Problem:** Mock objects (e.g., Mock author objects) cannot be serialized to JSON for database insertion.

**Solution:** Update mock fixtures to return serializable data structures:
```python
# Instead of:
result.authors = [Mock(name="Alice"), Mock(name="Bob")]

# Use:
result.authors = [type('Author', (), {'name': 'Alice'}), type('Author', (), {'name': 'Bob'})]
```

### Issue 2: Database Session Isolation
**Problem:** Some tests create data in test database session but code uses production `get_db_session()`.

**Solution:** Mock `get_db_session` to return test session:
```python
with patch('src.agents.reader.get_db_session', return_value=db_session):
    reader.save_analysis(arxiv_id, analysis)
```

### Issue 3: State Initialization
**Problem:** Some graph tests don't properly initialize all required state fields.

**Solution:** Use complete initial state:
```python
state = {
    "days_back": 7,
    "categories": None,
    "max_papers": None,
    "discovered_papers": None,
    "analyzed_papers": None,
    "explained_papers": None,
    "final_papers": None,
    "errors": [],
    "stats": {},
}
```

## Test Fixtures

### Shared Fixtures (conftest.py)

- `test_engine` - In-memory SQLite database
- `test_session` - Isolated database session
- `db_session` - Database session context manager
- `mock_arxiv_result` - Mock arXiv API response
- `sample_paper_data` - Sample paper dictionary

### Usage Example
```python
def test_my_feature(db_session, mock_arxiv_result):
    """Test uses both fixtures."""
    with db_session() as db:
        # Use test database
        paper = Paper(**mock_arxiv_result)
        db.add(paper)
```

## Writing New Tests

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

### Mocking External APIs
```python
@patch('src.agents.reader.get_claude_client')
def test_with_claude(mock_get_client):
    """Test with mocked Claude API."""
    mock_client = Mock()
    mock_client.chat_json.return_value = {"key": "value"}
    mock_get_client.return_value = mock_client

    # Test code here
```

### Database Tests
```python
def test_database_operation(db_session):
    """Test with isolated database."""
    with db_session() as db:
        # Create
        paper = Paper(arxiv_id="test.123", ...)
        db.add(paper)

    with db_session() as db:
        # Verify
        found = db.query(Paper).filter_by(arxiv_id="test.123").first()
        assert found is not None
```

## Continuous Improvement

### Priority Fixes
1. **Fix integration test mocks** - Replace Mock objects with serializable alternatives
2. **Add database session mocking** - Ensure tests use test database consistently
3. **Increase coverage** - Add tests for curator agent (when implemented)
4. **Add performance tests** - Ensure API calls stay within rate limits

### Coverage Goals
- Discovery Agent: 100% (currently ~95%)
- Reader Agent: 100% (currently ~90%)
- Explainer Agent: 100% (currently ~85%)
- Graph Workflows: 100% (currently ~85%)
- Integration Tests: 100% (currently ~10%)
- Database: 100% (currently 100% ✅)

## Regression Test Policy

**When fixing bugs:**
1. Write a test that reproduces the bug
2. Fix the bug
3. Verify the test now passes
4. Keep the test to prevent regression

**Example from project:**
```python
def test_cutoff_date_is_timezone_aware(self):
    """
    REGRESSION TEST: Ensure cutoff date is timezone-aware.

    Bug: datetime.now() returns naive datetime, but arXiv API returns
    timezone-aware datetimes, causing comparison errors.

    Fix: Use datetime.now(timezone.utc) for timezone-aware cutoff.
    """
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
