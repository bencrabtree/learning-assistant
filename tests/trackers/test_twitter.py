"""
Tests for Twitter Tracker.

Tests Twitter social signal tracking including:
- API integration
- arXiv ID extraction from tweets
- Social score calculation
- Lab account identification
"""

from unittest.mock import Mock, patch

import pytest

from src.trackers.twitter import TwitterTracker, fetch_twitter_signals


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Mock()
    settings.twitter_bearer_token = "test-bearer-token"
    settings.lab_twitter_accounts = "AnthropicAI,OpenAI"
    return settings


@pytest.fixture
def tracker(mock_settings):
    """Create a Twitter tracker instance with mocked settings."""
    with patch("src.config.settings", mock_settings):
        return TwitterTracker(bearer_token="test-token")


@pytest.fixture
def unconfigured_tracker():
    """Create a Twitter tracker without API key."""
    mock_settings = Mock()
    mock_settings.twitter_bearer_token = None
    mock_settings.lab_twitter_accounts = None

    with patch("src.config.settings", mock_settings):
        return TwitterTracker(bearer_token=None)


class TestTrackerConfiguration:
    """Tests for tracker configuration."""

    def test_configured_with_token(self, tracker):
        """Test tracker is configured with bearer token."""
        assert tracker._is_configured() is True

    def test_not_configured_without_token(self, unconfigured_tracker):
        """Test tracker is not configured without token."""
        assert unconfigured_tracker._is_configured() is False

    def test_default_lab_accounts(self, mock_settings):
        """Test default lab accounts are loaded."""
        mock_settings.lab_twitter_accounts = None
        with patch("src.config.settings", mock_settings):
            tracker = TwitterTracker(bearer_token="test")
            assert "AnthropicAI" in tracker.lab_accounts
            assert "OpenAI" in tracker.lab_accounts
            assert "GoogleDeepMind" in tracker.lab_accounts

    def test_custom_lab_accounts(self, mock_settings):
        """Test custom lab accounts are loaded from config."""
        mock_settings.lab_twitter_accounts = "CustomLab,AnotherLab"
        with patch("src.config.settings", mock_settings):
            tracker = TwitterTracker(bearer_token="test")
            assert tracker.lab_accounts == ["CustomLab", "AnotherLab"]


class TestArxivExtraction:
    """Tests for arXiv ID extraction from tweets."""

    def test_extract_from_abs_url(self, tracker):
        """Test extraction from arxiv.org/abs URL."""
        text = "Check out arxiv.org/abs/2312.12345"
        ids = tracker._extract_arxiv_urls(text)
        assert ids == ["2312.12345"]

    def test_extract_from_pdf_url(self, tracker):
        """Test extraction from arxiv.org/pdf URL."""
        text = "Paper: https://arxiv.org/pdf/2312.12345"
        ids = tracker._extract_arxiv_urls(text)
        assert ids == ["2312.12345"]

    def test_extract_multiple_ids(self, tracker):
        """Test extraction of multiple IDs from one tweet."""
        text = "Two papers: arxiv.org/abs/2312.12345 and arxiv.org/abs/2312.67890"
        ids = tracker._extract_arxiv_urls(text)
        assert "2312.12345" in ids
        assert "2312.67890" in ids
        assert len(ids) == 2

    def test_no_duplicates(self, tracker):
        """Test that duplicate IDs are not returned."""
        text = "arxiv.org/abs/2312.12345 arxiv.org/pdf/2312.12345"
        ids = tracker._extract_arxiv_urls(text)
        assert len(ids) == 1
        assert ids[0] == "2312.12345"

    def test_extract_bare_id(self, tracker):
        """Test extraction from arxiv: prefix."""
        text = "Read arxiv: 2312.12345"
        ids = tracker._extract_arxiv_urls(text)
        assert ids == ["2312.12345"]


class TestSocialScoreCalculation:
    """Tests for social score calculation."""

    def test_high_engagement_score(self, tracker):
        """Test score for highly engaged tweet."""
        data = {
            "likes": 1500,
            "retweets": 600,
            "quote_count": 60,
            "is_lab_account": True,
        }
        score = tracker.calculate_social_score(data)
        # likes > 1000 = 0.25, retweets > 500 = 0.15, quotes > 50 = 0.05, lab = 0.10
        # Total = 0.55, capped at 0.5
        assert score == pytest.approx(0.5)

    def test_medium_engagement_score(self, tracker):
        """Test score for medium engagement."""
        data = {
            "likes": 150,
            "retweets": 75,
            "quote_count": 10,
            "is_lab_account": False,
        }
        score = tracker.calculate_social_score(data)
        # likes > 100 = 0.15, retweets > 50 = 0.05
        assert score == pytest.approx(0.20)

    def test_lab_account_bonus(self, tracker):
        """Test that lab account gets bonus."""
        data_lab = {
            "likes": 50,
            "retweets": 20,
            "quote_count": 5,
            "is_lab_account": True,
        }
        data_non_lab = {
            "likes": 50,
            "retweets": 20,
            "quote_count": 5,
            "is_lab_account": False,
        }

        score_lab = tracker.calculate_social_score(data_lab)
        score_non_lab = tracker.calculate_social_score(data_non_lab)

        assert score_lab > score_non_lab
        assert score_lab - score_non_lab == pytest.approx(0.10)

    def test_zero_engagement(self, tracker):
        """Test score for no engagement."""
        data = {
            "likes": 0,
            "retweets": 0,
            "quote_count": 0,
            "is_lab_account": False,
        }
        score = tracker.calculate_social_score(data)
        assert score == pytest.approx(0.0)


class TestSearchArxivTweets:
    """Tests for searching tweets about arXiv papers."""

    def test_search_unconfigured_returns_empty(self, unconfigured_tracker):
        """Test that unconfigured tracker returns empty list."""
        papers = unconfigured_tracker.search_arxiv_tweets(days_back=7)
        assert papers == []

    def test_search_returns_papers(self, tracker):
        """Test that search returns papers from tweets."""
        mock_response = {
            "data": [
                {
                    "id": "123",
                    "text": "New paper: arxiv.org/abs/2312.12345",
                    "author_id": "user1",
                    "created_at": "2024-12-20T10:00:00Z",
                    "public_metrics": {
                        "like_count": 100,
                        "retweet_count": 50,
                        "reply_count": 10,
                        "quote_count": 5,
                    },
                }
            ],
            "includes": {"users": [{"id": "user1", "username": "researcher", "verified": True}]},
        }

        with patch.object(tracker, "_make_request") as mock_request:
            mock_request.return_value = mock_response

            papers = tracker.search_arxiv_tweets(days_back=7)

            assert len(papers) == 1
            assert papers[0]["arxiv_id"] == "2312.12345"
            assert papers[0]["likes"] == 100
            assert papers[0]["retweets"] == 50

    def test_search_identifies_lab_accounts(self, tracker):
        """Test that lab accounts are identified."""
        mock_response = {
            "data": [
                {
                    "id": "123",
                    "text": "Our new paper: arxiv.org/abs/2312.12345",
                    "author_id": "lab1",
                    "created_at": "2024-12-20T10:00:00Z",
                    "public_metrics": {
                        "like_count": 1000,
                        "retweet_count": 500,
                        "reply_count": 100,
                        "quote_count": 50,
                    },
                }
            ],
            "includes": {"users": [{"id": "lab1", "username": "AnthropicAI", "verified": True}]},
        }

        with patch.object(tracker, "_make_request") as mock_request:
            mock_request.return_value = mock_response

            papers = tracker.search_arxiv_tweets(days_back=7)

            assert len(papers) == 1
            assert papers[0]["is_lab_account"] is True

    def test_search_aggregates_tweets(self, tracker):
        """Test that multiple tweets about same paper are aggregated."""
        mock_response = {
            "data": [
                {
                    "id": "1",
                    "text": "Paper: arxiv.org/abs/2312.12345",
                    "author_id": "u1",
                    "created_at": "2024-12-20T10:00:00Z",
                    "public_metrics": {
                        "like_count": 50,
                        "retweet_count": 25,
                        "reply_count": 5,
                        "quote_count": 2,
                    },
                },
                {
                    "id": "2",
                    "text": "Same paper: arxiv.org/abs/2312.12345",
                    "author_id": "u2",
                    "created_at": "2024-12-20T11:00:00Z",
                    "public_metrics": {
                        "like_count": 100,
                        "retweet_count": 50,
                        "reply_count": 10,
                        "quote_count": 5,
                    },
                },
            ],
            "includes": {
                "users": [
                    {"id": "u1", "username": "user1"},
                    {"id": "u2", "username": "user2"},
                ]
            },
        }

        with patch.object(tracker, "_make_request") as mock_request:
            mock_request.return_value = mock_response

            papers = tracker.search_arxiv_tweets(days_back=7)

            assert len(papers) == 1
            assert papers[0]["arxiv_id"] == "2312.12345"
            assert papers[0]["likes"] == 150  # 50 + 100
            assert papers[0]["retweets"] == 75  # 25 + 50


class TestFetchTwitterSignals:
    """Tests for the batch fetch function."""

    def test_fetch_unconfigured_returns_empty(self, mock_settings):
        """Test that fetch returns empty list when not configured."""
        mock_settings.twitter_bearer_token = None
        with patch("src.config.settings", mock_settings):
            papers = fetch_twitter_signals(days_back=7)
            assert papers == []

    def test_fetch_adds_social_scores(self, mock_settings):
        """Test that fetch adds social scores to papers."""
        with (
            patch("src.config.settings", mock_settings),
            patch("src.trackers.twitter.TwitterTracker") as mock_tracker_class,
        ):
            mock_instance = Mock()
            mock_instance._is_configured.return_value = True
            mock_instance.search_arxiv_tweets.return_value = [
                {"arxiv_id": "1", "likes": 100, "retweets": 50},
                {"arxiv_id": "2", "likes": 500, "retweets": 200},
            ]
            mock_instance.calculate_social_score.side_effect = [0.2, 0.4]
            mock_tracker_class.return_value = mock_instance

            papers = fetch_twitter_signals(days_back=7)

            assert len(papers) == 2
            # Should be sorted by social score (descending)
            assert papers[0]["social_score"] >= papers[1]["social_score"]
