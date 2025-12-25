"""
Pytest configuration and shared fixtures.

This file defines common test fixtures used across multiple test files.
"""

import os
from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set environment variables BEFORE any imports
# This runs at module import time, before pytest fixture system
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-mock-for-testing")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("LOG_LEVEL", "ERROR")


# Import AFTER setting environment
from src.models.paper import Base


@pytest.fixture(scope="function")
def test_engine():
    """
    Create an in-memory SQLite database for testing.

    Each test gets a fresh database that's completely isolated.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_session(test_engine):
    """
    Create a database session for testing.

    This session is bound to the test database, not the production one.
    """
    test_session_local = sessionmaker(  # noqa: N806
        bind=test_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    @contextmanager
    def _get_test_session():
        session = test_session_local()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    return _get_test_session


@pytest.fixture
def db_session(test_session):
    """
    Provide a database session for a single test.

    Usage in tests:
        def test_something(db_session):
            with db_session() as db:
                paper = Paper(...)
                db.add(paper)
    """
    return test_session


@pytest.fixture
def mock_arxiv_result():
    """Create a mock arXiv Result object for testing."""
    result = Mock()
    result.entry_id = "http://arxiv.org/abs/2312.12345v1"
    result.title = "Test Paper Title"
    result.summary = "This is the paper abstract"

    # Create mock authors with proper name attribute
    author1 = Mock()
    author1.name = "Alice Smith"
    author2 = Mock()
    author2.name = "Bob Jones"
    result.authors = [author1, author2]

    result.published = datetime(2024, 12, 20, 10, 30, 0, tzinfo=UTC)
    result.categories = ["cs.AI", "cs.LG"]
    result.pdf_url = "http://arxiv.org/pdf/2312.12345v1"
    return result


@pytest.fixture
def sample_paper_data():
    """Sample paper data dictionary for testing."""
    return {
        "arxiv_id": "2312.12345",
        "title": "Test Paper",
        "abstract": "This is a test abstract",
        "authors": ["Alice Smith", "Bob Jones"],
        "published_date": datetime(2024, 12, 20, tzinfo=UTC),
        "categories": ["cs.AI", "cs.LG"],
        "pdf_url": "http://arxiv.org/pdf/2312.12345",
        "abstract_url": "http://arxiv.org/abs/2312.12345",
        "discovered_by": "arxiv",
    }
