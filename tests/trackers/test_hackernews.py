"""
Tests for HackerNews Tracker.

Tests HN social signal tracking including:
- Algolia API integration
- arXiv ID extraction
- Social score calculation
- Signal aggregation
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from src.trackers.hackernews import HackerNewsTracker, fetch_hn_signals


@pytest.fixture
def tracker():
    """Create a HackerNews tracker instance."""
    return HackerNewsTracker()


@pytest.fixture
def mock_algolia_response():
    """Mock Algolia API response with HN stories."""
    return {
        "hits": [
            {
                "objectID": "12345",
                "title": "Show HN: New paper on arxiv.org/abs/2312.12345",
                "url": "https://arxiv.org/abs/2312.12345",
                "points": 250,
                "num_comments": 120,
                "created_at_i": int((datetime.now() - timedelta(days=1)).timestamp()),
            },
            {
                "objectID": "12346",
                "title": "Another arxiv paper arxiv.org/pdf/2312.67890",
                "url": "https://arxiv.org/pdf/2312.67890",
                "points": 75,
                "num_comments": 30,
                "created_at_i": int((datetime.now() - timedelta(days=2)).timestamp()),
            },
            {
                "objectID": "12347",
                "title": "Old paper",
                "url": "https://arxiv.org/abs/2312.11111",
                "points": 50,
                "num_comments": 10,
                "created_at_i": int((datetime.now() - timedelta(days=30)).timestamp()),
            },
        ]
    }


class TestArxivIdExtraction:
    """Tests for arXiv ID extraction from text and URLs."""

    def test_extract_from_abs_url(self, tracker):
        """Test extraction from arxiv.org/abs URL."""
        arxiv_id = tracker._extract_arxiv_id(None, "https://arxiv.org/abs/2312.12345")
        assert arxiv_id == "2312.12345"

    def test_extract_from_pdf_url(self, tracker):
        """Test extraction from arxiv.org/pdf URL."""
        arxiv_id = tracker._extract_arxiv_id(None, "https://arxiv.org/pdf/2312.12345.pdf")
        assert arxiv_id == "2312.12345"

    def test_extract_removes_version(self, tracker):
        """Test that version suffix is removed."""
        arxiv_id = tracker._extract_arxiv_id(None, "https://arxiv.org/abs/2312.12345v2")
        assert arxiv_id == "2312.12345"

    def test_extract_from_text(self, tracker):
        """Test extraction from text content."""
        text = "Check out this paper: arxiv.org/abs/2312.12345"
        arxiv_id = tracker._extract_arxiv_id(text, None)
        assert arxiv_id == "2312.12345"

    def test_no_arxiv_returns_none(self, tracker):
        """Test that non-arXiv URLs return None."""
        arxiv_id = tracker._extract_arxiv_id("Random text", "https://example.com")
        assert arxiv_id is None


class TestSocialScoreCalculation:
    """Tests for social score calculation."""

    def test_high_engagement_score(self, tracker):
        """Test score for highly engaged post."""
        data = {"score": 250, "comments_count": 120}
        score = tracker.calculate_social_score(data)
        # score > 200 = 0.30, comments > 100 = 0.15
        assert score == pytest.approx(0.45)

    def test_medium_engagement_score(self, tracker):
        """Test score for medium engagement."""
        data = {"score": 150, "comments_count": 60}
        score = tracker.calculate_social_score(data)
        # score > 100 = 0.20, comments > 50 = 0.10
        assert score == pytest.approx(0.30)

    def test_low_engagement_score(self, tracker):
        """Test score for low engagement."""
        data = {"score": 75, "comments_count": 25}
        score = tracker.calculate_social_score(data)
        # score > 50 = 0.10, comments > 20 = 0.05
        assert score == pytest.approx(0.15)

    def test_zero_engagement_score(self, tracker):
        """Test score for no engagement."""
        data = {"score": 0, "comments_count": 0}
        score = tracker.calculate_social_score(data)
        assert score == pytest.approx(0.0)

    def test_max_score_capped(self, tracker):
        """Test that score is capped (max from rubric is 0.45)."""
        data = {"score": 1000, "comments_count": 500}
        score = tracker.calculate_social_score(data)
        # Max from rubric: score > 200 = 0.30 + comments > 100 = 0.15 = 0.45
        assert score == pytest.approx(0.45)


class TestSearchArxivPapers:
    """Tests for searching arXiv papers on HN."""

    def test_search_returns_papers(self, tracker, mock_algolia_response):
        """Test that search returns papers within time range."""
        with patch.object(tracker, "_search_algolia") as mock_search:
            mock_search.return_value = mock_algolia_response

            papers = tracker.search_arxiv_papers(days_back=7)

            # Should only return papers from last 7 days (first 2)
            assert len(papers) == 2
            assert papers[0]["arxiv_id"] == "2312.12345"
            assert papers[1]["arxiv_id"] == "2312.67890"

    def test_search_aggregates_duplicate_posts(self, tracker):
        """Test that multiple posts about same paper are aggregated."""
        response = {
            "hits": [
                {
                    "objectID": "1",
                    "title": "Paper",
                    "url": "https://arxiv.org/abs/2312.12345",
                    "points": 100,
                    "num_comments": 50,
                    "created_at_i": int(datetime.now().timestamp()),
                },
                {
                    "objectID": "2",
                    "title": "Same Paper",
                    "url": "https://arxiv.org/abs/2312.12345",
                    "points": 150,
                    "num_comments": 75,
                    "created_at_i": int(datetime.now().timestamp()),
                },
            ]
        }

        with patch.object(tracker, "_search_algolia") as mock_search:
            mock_search.return_value = response

            papers = tracker.search_arxiv_papers(days_back=7)

            # Should aggregate into single entry
            assert len(papers) == 1
            assert papers[0]["arxiv_id"] == "2312.12345"
            assert papers[0]["score"] == 250  # 100 + 150
            assert papers[0]["comments_count"] == 125  # 50 + 75

    def test_search_handles_api_error(self, tracker):
        """Test that API errors return empty list."""
        with patch.object(tracker, "_search_algolia") as mock_search:
            mock_search.return_value = None

            papers = tracker.search_arxiv_papers(days_back=7)

            assert papers == []


class TestGetPaperSignals:
    """Tests for getting signals for specific paper."""

    def test_get_signals_found(self, tracker):
        """Test getting signals when paper exists on HN."""
        response = {
            "hits": [
                {
                    "objectID": "1",
                    "title": "Discussion about 2312.12345",
                    "url": "https://arxiv.org/abs/2312.12345",
                    "points": 100,
                    "num_comments": 50,
                }
            ]
        }

        with patch.object(tracker, "_search_algolia") as mock_search:
            mock_search.return_value = response

            signals = tracker.get_paper_signals("2312.12345")

            assert signals is not None
            assert signals["arxiv_id"] == "2312.12345"
            assert signals["score"] == 100
            assert signals["comments_count"] == 50
            assert signals["num_posts"] == 1

    def test_get_signals_not_found(self, tracker):
        """Test getting signals for paper not on HN."""
        response = {"hits": []}

        with patch.object(tracker, "_search_algolia") as mock_search:
            mock_search.return_value = response

            signals = tracker.get_paper_signals("2312.99999")

            assert signals is None


class TestFetchHnSignals:
    """Tests for the batch fetch function."""

    def test_fetch_adds_social_scores(self):
        """Test that fetch adds social scores to papers."""
        mock_papers = [
            {"arxiv_id": "2312.12345", "score": 250, "comments_count": 120},
            {"arxiv_id": "2312.67890", "score": 75, "comments_count": 30},
        ]

        with patch("src.trackers.hackernews.HackerNewsTracker.search_arxiv_papers") as mock_search:
            mock_search.return_value = mock_papers

            with patch(
                "src.trackers.hackernews.HackerNewsTracker.calculate_social_score"
            ) as mock_calc:
                mock_calc.side_effect = [0.45, 0.15]

                papers = fetch_hn_signals(days_back=7)

                assert len(papers) == 2
                assert papers[0]["social_score"] == 0.45
                assert papers[1]["social_score"] == 0.15

    def test_fetch_sorts_by_score(self):
        """Test that results are sorted by social score."""
        mock_papers = [
            {"arxiv_id": "1", "score": 50, "comments_count": 10},
            {"arxiv_id": "2", "score": 500, "comments_count": 200},
        ]

        with patch("src.trackers.hackernews.HackerNewsTracker") as mock_tracker_class:
            mock_instance = Mock()
            mock_instance.search_arxiv_papers.return_value = mock_papers
            mock_instance.calculate_social_score.side_effect = [0.1, 0.5]
            mock_tracker_class.return_value = mock_instance

            papers = fetch_hn_signals(days_back=7)

            # Higher score should come first
            assert papers[0]["social_score"] >= papers[1]["social_score"]
