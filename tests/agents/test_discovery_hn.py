"""
Tests for HackerNews-based paper discovery.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from src.agents.discovery import discover_papers_from_hn
from src.models.paper import Paper


class TestDiscoverPapersFromHN:
    """Test the discover_papers_from_hn function."""

    def test_returns_empty_when_no_hn_papers(self, db_session):
        """Test returns empty list when no HN papers found."""
        with patch("src.trackers.hackernews.fetch_hn_signals") as mock_fetch:
            mock_fetch.return_value = []

            with patch("src.agents.discovery.get_db_session", db_session):
                papers = discover_papers_from_hn(days_back=7, min_score=10)

            assert papers == []
            mock_fetch.assert_called_once_with(days_back=7)

    def test_filters_by_min_score(self, db_session):
        """Test that papers below min_score are filtered out."""
        hn_papers = [
            {"arxiv_id": "2312.high", "score": 100, "comments_count": 50, "posts": ["1"]},
            {"arxiv_id": "2312.low", "score": 5, "comments_count": 2, "posts": ["2"]},
        ]

        # Mock arXiv response for the high-score paper
        mock_result = MagicMock()
        mock_result.entry_id = "http://arxiv.org/abs/2312.high"
        mock_result.title = "High Score Paper"
        mock_result.summary = "Abstract"
        mock_result.authors = [MagicMock()]
        mock_result.authors[0].name = "Author"
        mock_result.published = datetime.now(UTC)
        mock_result.categories = ["cs.AI"]
        mock_result.pdf_url = "http://arxiv.org/pdf/2312.high"

        mock_search = MagicMock()
        mock_search.results.return_value = iter([mock_result])

        with (
            patch("src.trackers.hackernews.fetch_hn_signals") as mock_fetch,
            patch("src.agents.discovery.arxiv.Search", return_value=mock_search),
            patch("src.agents.discovery.get_db_session", db_session),
        ):
            mock_fetch.return_value = hn_papers

            # With min_score=10, only the high-score paper should be considered
            papers = discover_papers_from_hn(days_back=7, min_score=10)

            # Should filter out the low-score paper
            assert mock_fetch.called
            # Only the high-score paper should be discovered
            assert len(papers) == 1
            assert papers[0].arxiv_id == "2312.high"

    def test_skips_existing_papers(self, db_session):
        """Test that papers already in database are not re-fetched from arXiv."""
        # Create an existing paper
        with db_session() as db:
            existing = Paper(
                arxiv_id="2312.existing",
                title="Existing Paper",
                abstract="Abstract",
                authors=["Author"],
                published_date=datetime.now(UTC),
                categories=["cs.AI"],
                pdf_url="http://example.com/pdf",
                abstract_url="http://example.com/abs",
                discovered_by="arxiv",
            )
            db.add(existing)

        hn_papers = [
            {
                "arxiv_id": "2312.existing",
                "score": 100,
                "comments_count": 50,
                "posts": ["123"],
                "social_score": 0.3,
            },
        ]

        with patch("src.trackers.hackernews.fetch_hn_signals") as mock_fetch:
            mock_fetch.return_value = hn_papers

            with patch("src.agents.discovery.get_db_session", db_session):
                discover_papers_from_hn(days_back=7, min_score=10)

        # Should update existing paper with HN signals
        with db_session() as db:
            paper = db.query(Paper).filter_by(arxiv_id="2312.existing").first()
            assert paper is not None
            assert paper.score_components is not None
            assert paper.score_components.get("hn_score") == 100
            assert paper.score_components.get("hn_comments") == 50

    def test_stores_hn_signals_in_score_components(self, db_session):
        """Test that HN signals are stored in score_components."""
        # Create an existing paper to update
        with db_session() as db:
            paper = Paper(
                arxiv_id="2312.signals",
                title="Test Paper",
                abstract="Abstract",
                authors=["Author"],
                published_date=datetime.now(UTC),
                categories=["cs.AI"],
                pdf_url="http://example.com/pdf",
                abstract_url="http://example.com/abs",
                discovered_by="arxiv",
            )
            db.add(paper)

        hn_papers = [
            {
                "arxiv_id": "2312.signals",
                "score": 150,
                "comments_count": 75,
                "posts": ["post1", "post2"],
                "social_score": 0.35,
            },
        ]

        with patch("src.trackers.hackernews.fetch_hn_signals") as mock_fetch:
            mock_fetch.return_value = hn_papers

            with patch("src.agents.discovery.get_db_session", db_session):
                discover_papers_from_hn(days_back=7, min_score=10)

        # Verify HN signals were stored
        with db_session() as db:
            paper = db.query(Paper).filter_by(arxiv_id="2312.signals").first()
            assert paper.score_components["hn_score"] == 150
            assert paper.score_components["hn_comments"] == 75
            assert paper.score_components["hn_posts"] == 2
            assert paper.score_components["social_score"] == 0.35

    def test_uses_correct_days_back_parameter(self, db_session):
        """Test that days_back is passed correctly to fetch_hn_signals."""
        with patch("src.trackers.hackernews.fetch_hn_signals") as mock_fetch:
            mock_fetch.return_value = []

            with patch("src.agents.discovery.get_db_session", db_session):
                discover_papers_from_hn(days_back=14, min_score=5)

            mock_fetch.assert_called_once_with(days_back=14)


class TestDiscoverPapersFromHNIntegration:
    """Integration tests for HN discovery (marked for slower execution)."""

    @pytest.mark.integration
    def test_full_flow_with_mocked_arxiv(self, db_session):
        """Test full flow with mocked arXiv API."""
        # Mock HN response
        hn_papers = [
            {
                "arxiv_id": "2312.newpaper",
                "score": 200,
                "comments_count": 100,
                "posts": ["post1"],
                "social_score": 0.45,
            },
        ]

        # Mock arXiv response
        mock_result = MagicMock()
        mock_result.entry_id = "http://arxiv.org/abs/2312.newpaper"
        mock_result.title = "  New Paper Title  "
        mock_result.summary = "  Paper abstract  "
        mock_result.authors = [MagicMock(name="Author One")]
        mock_result.authors[0].name = "Author One"
        mock_result.published = datetime.now(UTC)
        mock_result.categories = ["cs.AI", "cs.LG"]
        mock_result.pdf_url = "http://arxiv.org/pdf/2312.newpaper"

        mock_search = MagicMock()
        mock_search.results.return_value = iter([mock_result])

        with (
            patch("src.trackers.hackernews.fetch_hn_signals") as mock_fetch,
            patch("src.agents.discovery.arxiv.Search", return_value=mock_search),
            patch("src.agents.discovery.get_db_session", db_session),
        ):
            mock_fetch.return_value = hn_papers

            papers = discover_papers_from_hn(days_back=7, min_score=10)

        # Verify paper was created
        assert len(papers) == 1
        paper = papers[0]
        assert paper.arxiv_id == "2312.newpaper"
        assert paper.discovered_by == "hackernews"
        assert paper.score_components["hn_score"] == 200
