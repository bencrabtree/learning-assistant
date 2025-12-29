"""
Tests for the feedback server.
"""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from src.models.paper import Paper
from src.services.feedback_server import app


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestHealthEndpoint:
    """Test the health check endpoint."""

    def test_health_returns_ok(self, client):
        """Test health endpoint returns OK status."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json == {"status": "ok"}


class TestFeedbackEndpoint:
    """Test the feedback endpoint."""

    def test_feedback_good_success(self, client, db_session):
        """Test successful good feedback."""
        # Create a paper
        with db_session() as db:
            paper = Paper(
                arxiv_id="2312.server.1",
                title="Test Paper for Server",
                abstract="Abstract",
                authors=["Author"],
                published_date=datetime.now(UTC),
                categories=["cs.AI"],
                pdf_url="http://example.com/pdf",
                abstract_url="http://example.com/abs",
                discovered_by="test",
            )
            db.add(paper)

        with patch("src.services.feedback.get_db_session", db_session):
            response = client.get("/feedback/2312.server.1/good")

        assert response.status_code == 200
        assert b"Thanks for your feedback" in response.data

    def test_feedback_neutral_success(self, client, db_session):
        """Test successful neutral feedback."""
        with db_session() as db:
            paper = Paper(
                arxiv_id="2312.server.2",
                title="Test Paper",
                abstract="Abstract",
                authors=["Author"],
                published_date=datetime.now(UTC),
                categories=["cs.AI"],
                pdf_url="http://example.com/pdf",
                abstract_url="http://example.com/abs",
                discovered_by="test",
            )
            db.add(paper)

        with patch("src.services.feedback.get_db_session", db_session):
            response = client.get("/feedback/2312.server.2/neutral")

        assert response.status_code == 200
        assert b"Thanks for your feedback" in response.data

    def test_feedback_bad_success(self, client, db_session):
        """Test successful bad feedback."""
        with db_session() as db:
            paper = Paper(
                arxiv_id="2312.server.3",
                title="Test Paper",
                abstract="Abstract",
                authors=["Author"],
                published_date=datetime.now(UTC),
                categories=["cs.AI"],
                pdf_url="http://example.com/pdf",
                abstract_url="http://example.com/abs",
                discovered_by="test",
            )
            db.add(paper)

        with patch("src.services.feedback.get_db_session", db_session):
            response = client.get("/feedback/2312.server.3/bad")

        assert response.status_code == 200
        assert b"Thanks for your feedback" in response.data

    def test_feedback_paper_not_found(self, client, db_session):
        """Test feedback for non-existent paper."""
        with patch("src.services.feedback.get_db_session", db_session):
            response = client.get("/feedback/nonexistent.paper/good")

        assert response.status_code == 400
        assert b"Feedback Failed" in response.data
        assert b"not found" in response.data

    def test_feedback_invalid_rating(self, client):
        """Test feedback with invalid rating."""
        # Invalid rating returns 400 without needing to check DB
        response = client.get("/feedback/2312.server.4/excellent")

        assert response.status_code == 400
        assert b"Feedback Failed" in response.data


class TestResponseHtml:
    """Test the HTML response format."""

    def test_response_contains_arxiv_link(self, client, db_session):
        """Test that response contains arXiv link."""
        with db_session() as db:
            paper = Paper(
                arxiv_id="2312.html.1",
                title="Test Paper",
                abstract="Abstract",
                authors=["Author"],
                published_date=datetime.now(UTC),
                categories=["cs.AI"],
                pdf_url="http://example.com/pdf",
                abstract_url="http://example.com/abs",
                discovered_by="test",
            )
            db.add(paper)

        with patch("src.services.feedback.get_db_session", db_session):
            response = client.get("/feedback/2312.html.1/good")

        assert b"https://arxiv.org/abs/2312.html.1" in response.data
        assert b"View paper on arXiv" in response.data

    def test_response_has_success_class(self, client, db_session):
        """Test successful response has success class."""
        with db_session() as db:
            paper = Paper(
                arxiv_id="2312.html.2",
                title="Test Paper",
                abstract="Abstract",
                authors=["Author"],
                published_date=datetime.now(UTC),
                categories=["cs.AI"],
                pdf_url="http://example.com/pdf",
                abstract_url="http://example.com/abs",
                discovered_by="test",
            )
            db.add(paper)

        with patch("src.services.feedback.get_db_session", db_session):
            response = client.get("/feedback/2312.html.2/good")

        assert b'class="success"' in response.data

    def test_error_response_has_error_class(self, client, db_session):
        """Test error response has error class."""
        with patch("src.services.feedback.get_db_session", db_session):
            response = client.get("/feedback/nonexistent/good")

        assert b'class="error"' in response.data
