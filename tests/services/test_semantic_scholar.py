"""
Tests for Semantic Scholar API Client.

Tests citation data fetching including:
- API requests
- Citation count retrieval
- Paper updates
- Error handling
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.paper import Base, Paper
from src.services.semantic_scholar import SemanticScholarClient, fetch_citations_for_papers


@pytest.fixture
def engine():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create a database session for testing."""
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.close()


@pytest.fixture
def sample_paper():
    """Create a sample paper for testing."""
    return Paper(
        arxiv_id="2312.12345",
        title="Test Paper",
        abstract="Test abstract",
        authors=["Test Author"],
        published_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://arxiv.org/pdf/2312.12345.pdf",
        abstract_url="https://arxiv.org/abs/2312.12345",
        discovered_by="arxiv",
    )


@pytest.fixture
def mock_api_response():
    """Mock Semantic Scholar API response."""
    return {
        "paperId": "abc123",
        "title": "Test Paper",
        "citationCount": 150,
        "influentialCitationCount": 25,
    }


class TestSemanticScholarClient:
    """Tests for the Semantic Scholar API client."""

    def test_initialization_without_api_key(self):
        """Test client initialization without API key."""
        with patch("src.services.semantic_scholar.settings") as mock_settings:
            mock_settings.semantic_scholar_api_key = None
            client = SemanticScholarClient()
            assert client.api_key is None
            assert client.headers == {}

    def test_initialization_with_api_key(self):
        """Test client initialization with API key."""
        with patch("src.services.semantic_scholar.settings") as mock_settings:
            mock_settings.semantic_scholar_api_key = "test-key"
            client = SemanticScholarClient()
            assert client.api_key == "test-key"
            assert client.headers == {"x-api-key": "test-key"}


class TestGetCitationCounts:
    """Tests for citation count retrieval."""

    def test_get_citation_counts_success(self, mock_api_response):
        """Test successful citation count retrieval."""
        with patch("src.services.semantic_scholar.settings") as mock_settings:
            mock_settings.semantic_scholar_api_key = None

            with patch("src.services.semantic_scholar.requests.get") as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_api_response
                mock_get.return_value = mock_response

                client = SemanticScholarClient()
                result = client.get_citation_counts("2312.12345")

                assert result is not None
                assert result["citation_count"] == 150
                assert result["influential_citation_count"] == 25
                assert result["paper_id"] == "abc123"

    def test_get_citation_counts_not_found(self):
        """Test citation count retrieval for non-existent paper."""
        with patch("src.services.semantic_scholar.settings") as mock_settings:
            mock_settings.semantic_scholar_api_key = None

            with patch("src.services.semantic_scholar.requests.get") as mock_get:
                mock_response = Mock()
                mock_response.status_code = 404
                mock_get.return_value = mock_response

                client = SemanticScholarClient()
                result = client.get_citation_counts("9999.99999")

                assert result is None

    def test_get_citation_counts_rate_limited(self):
        """Test handling of rate limiting."""
        with patch("src.services.semantic_scholar.settings") as mock_settings:
            mock_settings.semantic_scholar_api_key = None

            with (
                patch("src.services.semantic_scholar.requests.get") as mock_get,
                patch("src.services.semantic_scholar.time.sleep"),
            ):
                mock_response = Mock()
                mock_response.status_code = 429
                mock_get.return_value = mock_response

                client = SemanticScholarClient()
                result = client.get_citation_counts("2312.12345")

                assert result is None

    def test_get_citation_counts_request_error(self):
        """Test handling of request errors."""
        with patch("src.services.semantic_scholar.settings") as mock_settings:
            mock_settings.semantic_scholar_api_key = None

            with patch("src.services.semantic_scholar.requests.get") as mock_get:
                import requests

                mock_get.side_effect = requests.RequestException("Network error")

                client = SemanticScholarClient()
                result = client.get_citation_counts("2312.12345")

                assert result is None


class TestUpdatePaperCitations:
    """Tests for updating paper citations in database."""

    def test_update_paper_citations_success(self, session, sample_paper, mock_api_response):
        """Test successful paper citation update."""
        session.add(sample_paper)
        session.commit()

        with patch("src.services.semantic_scholar.settings") as mock_settings:
            mock_settings.semantic_scholar_api_key = None

            with patch("src.services.semantic_scholar.requests.get") as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_api_response
                mock_get.return_value = mock_response

                with patch("src.services.semantic_scholar.get_db_session") as mock_db:
                    mock_db.return_value.__enter__.return_value = session
                    mock_db.return_value.__exit__.return_value = None

                    client = SemanticScholarClient()
                    success = client.update_paper_citations(sample_paper)

                    assert success is True

        updated = session.query(Paper).filter_by(arxiv_id="2312.12345").first()
        assert updated.citation_count == 150
        assert updated.influential_citation_count == 25

    def test_update_paper_citations_paper_not_found(self, sample_paper, mock_api_response):
        """Test citation update when paper not in database."""
        with patch("src.services.semantic_scholar.settings") as mock_settings:
            mock_settings.semantic_scholar_api_key = None

            with patch("src.services.semantic_scholar.requests.get") as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_api_response
                mock_get.return_value = mock_response

                with patch("src.services.semantic_scholar.get_db_session") as mock_db:
                    mock_session = Mock()
                    mock_session.query.return_value.filter_by.return_value.first.return_value = None
                    mock_db.return_value.__enter__.return_value = mock_session
                    mock_db.return_value.__exit__.return_value = None

                    client = SemanticScholarClient()
                    success = client.update_paper_citations(sample_paper)

                    assert success is False

    def test_update_paper_citations_api_fails(self, sample_paper):
        """Test citation update when API returns no data."""
        with patch("src.services.semantic_scholar.settings") as mock_settings:
            mock_settings.semantic_scholar_api_key = None

            with patch("src.services.semantic_scholar.requests.get") as mock_get:
                mock_response = Mock()
                mock_response.status_code = 404
                mock_get.return_value = mock_response

                client = SemanticScholarClient()
                success = client.update_paper_citations(sample_paper)

                assert success is False


class TestFetchCitationsForPapers:
    """Tests for batch citation fetching."""

    def test_fetch_empty_list(self):
        """Test fetching citations for empty list."""
        result = fetch_citations_for_papers([])
        assert result == 0

    def test_fetch_citations_batch(self, session, mock_api_response):
        """Test fetching citations for multiple papers."""
        papers = [
            Paper(
                arxiv_id=f"2312.1234{i}",
                title=f"Paper {i}",
                abstract="Test",
                authors=["Test"],
                published_date=datetime.now(),
                categories=["cs.AI"],
                pdf_url="https://example.com/pdf",
                abstract_url="https://example.com/abs",
                discovered_by="arxiv",
            )
            for i in range(3)
        ]

        for paper in papers:
            session.add(paper)
        session.commit()

        with (
            patch("src.services.semantic_scholar.settings") as mock_settings,
            patch("src.services.semantic_scholar.requests.get") as mock_get,
            patch("src.services.semantic_scholar.get_db_session") as mock_db,
            patch("src.services.semantic_scholar.time.sleep"),
        ):
            mock_settings.semantic_scholar_api_key = None

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_api_response
            mock_get.return_value = mock_response

            mock_db.return_value.__enter__.return_value = session
            mock_db.return_value.__exit__.return_value = None

            result = fetch_citations_for_papers(papers)

            assert result == 3
            assert mock_get.call_count == 3
