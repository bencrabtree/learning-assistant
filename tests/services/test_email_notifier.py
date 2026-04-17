"""
Tests for the email notification service.

These tests verify the email notification functionality without
actually sending emails.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.models.paper import Paper
from src.services.email_notifier import (
    EmailNotifier,
    send_paper_notification,
    test_email_connection,
)


class TestEmailNotifier:
    """Tests for EmailNotifier class."""

    def test_initialization_loads_settings(self):
        """Test that notifier loads settings correctly."""
        with patch("src.services.email_notifier.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.test.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "test@test.com"
            mock_settings.smtp_password = "password123"
            mock_settings.recipient_email = "recipient@test.com"
            mock_settings.email_recipient = None

            notifier = EmailNotifier()

            assert notifier.smtp_host == "smtp.test.com"
            assert notifier.smtp_port == 587
            assert notifier.username == "test@test.com"
            assert notifier.password == "password123"
            assert notifier.recipient == "recipient@test.com"

    def test_is_configured_when_all_fields_present(self):
        """Test is_configured returns True when all fields set."""
        with patch("src.services.email_notifier.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.test.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "test@test.com"
            mock_settings.smtp_password = "password123"
            mock_settings.recipient_email = "recipient@test.com"
            mock_settings.email_recipient = None

            notifier = EmailNotifier()
            assert notifier.is_configured() is True

    def test_is_configured_when_missing_fields(self):
        """Test is_configured returns False when fields missing."""
        with patch("src.services.email_notifier.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.test.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = None  # Missing
            mock_settings.smtp_password = "password123"
            mock_settings.recipient_email = "recipient@test.com"
            mock_settings.email_recipient = None

            notifier = EmailNotifier()
            assert notifier.is_configured() is False


class TestEmailContent:
    """Tests for email content building."""

    @pytest.fixture
    def notifier(self):
        """Create a configured notifier."""
        with patch("src.services.email_notifier.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.test.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "test@test.com"
            mock_settings.smtp_password = "password123"
            mock_settings.recipient_email = "recipient@test.com"
            mock_settings.email_recipient = None
            return EmailNotifier()

    @pytest.fixture
    def sample_paper(self):
        """Create a sample paper for testing."""
        return Paper(
            arxiv_id="2312.12345",
            title="Test Paper: A Novel Approach",
            abstract="This is a test abstract that describes the paper.",
            authors=["Alice Smith", "Bob Jones", "Carol Williams", "David Brown"],
            published_date=datetime(2023, 12, 15),
            categories=["cs.AI", "cs.LG"],
            pdf_url="https://arxiv.org/pdf/2312.12345",
            abstract_url="https://arxiv.org/abs/2312.12345",
            eli5_summary="A simple explanation of the paper",
            breakthrough_score=0.85,
            relevance_score=0.7,
            score_components={"hn_score": 150},
        )

    def test_build_subject_breakthrough_single(self, notifier, sample_paper):
        """Test subject line for single breakthrough paper."""
        subject = notifier._build_subject([sample_paper], "breakthrough")
        assert "Breakthrough" in subject
        assert "Test Paper" in subject

    def test_build_subject_trending_multiple(self, notifier, sample_paper):
        """Test subject line for multiple trending papers."""
        papers = [sample_paper, sample_paper]
        subject = notifier._build_subject(papers, "trending")
        assert "Trending" in subject
        assert "2" in subject

    def test_build_subject_noteworthy(self, notifier, sample_paper):
        """Test subject line for noteworthy papers."""
        subject = notifier._build_subject([sample_paper], "noteworthy")
        assert "Noteworthy" in subject

    def test_build_html_contains_paper_info(self, notifier, sample_paper):
        """Test HTML contains paper information."""
        html = notifier._build_html([sample_paper], "breakthrough")

        assert sample_paper.title in html
        assert "Alice Smith" in html
        assert sample_paper.abstract_url in html
        assert "Breakthrough: 85%" in html

    def test_build_html_truncates_authors(self, notifier, sample_paper):
        """Test HTML truncates long author lists."""
        html = notifier._build_html([sample_paper], "breakthrough")
        # Should show first 3 authors plus "..."
        assert "Alice Smith" in html
        assert "Bob Jones" in html
        assert "Carol Williams" in html
        assert "..." in html

    def test_build_plaintext_contains_paper_info(self, notifier, sample_paper):
        """Test plaintext contains paper information."""
        text = notifier._build_plaintext([sample_paper], "breakthrough")

        assert sample_paper.title in text
        assert sample_paper.abstract_url in text
        assert "Alice Smith" in text

    def test_build_html_digest_banner_present_when_url_set(self, notifier, sample_paper):
        """Digest audio banner renders when digest_audio_url is supplied."""
        url = "https://pub-xxx.r2.dev/digests/2026-04-17.mp3"
        html = notifier._build_html([sample_paper], "digest", digest_audio_url=url)
        assert url in html
        assert "Listen to today's digest" in html

    def test_build_html_digest_banner_absent_when_url_none(self, notifier, sample_paper):
        """Digest audio banner is omitted when no URL is supplied."""
        html = notifier._build_html([sample_paper], "digest")
        assert "Listen to today's digest" not in html

    def test_build_plaintext_digest_link_present_when_url_set(self, notifier, sample_paper):
        """Plaintext body includes digest listen link when URL supplied."""
        url = "https://pub-xxx.r2.dev/digests/2026-04-17.mp3"
        text = notifier._build_plaintext([sample_paper], "digest", digest_audio_url=url)
        assert url in text
        assert "Listen to today's digest" in text

    def test_format_scores_with_all_scores(self, notifier, sample_paper):
        """Test score formatting with all scores present."""
        scores = notifier._format_scores(sample_paper)

        assert "Breakthrough: 85%" in scores
        assert "Relevance: 70%" in scores
        assert "HN: 150" in scores

    def test_format_scores_no_scores(self, notifier):
        """Test score formatting with no scores."""
        paper = Paper(
            arxiv_id="2312.12345",
            title="Test",
            abstract="Test",
            authors=["Test"],
            published_date=datetime.now(),
            categories=["cs.AI"],
            pdf_url="http://test.com",
            abstract_url="http://test.com",
        )
        scores = notifier._format_scores(paper)
        assert scores == "New discovery"


class TestSendEmail:
    """Tests for email sending functionality."""

    @pytest.fixture
    def sample_paper(self):
        """Create a sample paper for testing."""
        return Paper(
            arxiv_id="2312.12345",
            title="Test Paper",
            abstract="Test abstract",
            authors=["Test Author"],
            published_date=datetime(2023, 12, 15),
            categories=["cs.AI"],
            pdf_url="https://arxiv.org/pdf/2312.12345",
            abstract_url="https://arxiv.org/abs/2312.12345",
        )

    def test_send_paper_alert_when_not_configured(self, sample_paper):
        """Test that alert returns False when not configured."""
        with patch("src.services.email_notifier.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.test.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = None  # Not configured
            mock_settings.smtp_password = None
            mock_settings.recipient_email = None
            mock_settings.email_recipient = None

            notifier = EmailNotifier()
            result = notifier.send_paper_alert([sample_paper], "breakthrough")

            assert result is False

    def test_send_paper_alert_empty_list(self):
        """Test that alert returns True for empty paper list."""
        with patch("src.services.email_notifier.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.test.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "test@test.com"
            mock_settings.smtp_password = "password"
            mock_settings.recipient_email = "recipient@test.com"
            mock_settings.email_recipient = None

            notifier = EmailNotifier()
            result = notifier.send_paper_alert([], "breakthrough")

            assert result is True

    @patch("src.services.email_notifier.smtplib.SMTP")
    def test_send_paper_alert_success(self, mock_smtp, sample_paper):
        """Test successful email sending."""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        with patch("src.services.email_notifier.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.test.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "test@test.com"
            mock_settings.smtp_password = "password"
            mock_settings.recipient_email = "recipient@test.com"
            mock_settings.email_recipient = None

            notifier = EmailNotifier()
            result = notifier.send_paper_alert([sample_paper], "breakthrough")

            assert result is True
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with("test@test.com", "password")
            mock_server.send_message.assert_called_once()

    @patch("src.services.email_notifier.smtplib.SMTP")
    def test_send_paper_alert_failure(self, mock_smtp, sample_paper):
        """Test email sending failure."""
        mock_smtp.return_value.__enter__ = MagicMock(side_effect=Exception("SMTP Error"))
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        with patch("src.services.email_notifier.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.test.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "test@test.com"
            mock_settings.smtp_password = "password"
            mock_settings.recipient_email = "recipient@test.com"
            mock_settings.email_recipient = None

            notifier = EmailNotifier()
            result = notifier.send_paper_alert([sample_paper], "breakthrough")

            assert result is False


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    @patch("src.services.email_notifier.EmailNotifier")
    def test_send_paper_notification(self, mock_notifier_class):
        """Test send_paper_notification convenience function."""
        mock_notifier = MagicMock()
        mock_notifier.send_paper_alert.return_value = True
        mock_notifier_class.return_value = mock_notifier

        papers = [MagicMock()]
        result = send_paper_notification(papers, "trending")

        assert result is True
        mock_notifier.send_paper_alert.assert_called_once_with(papers, "trending")

    @patch("src.services.email_notifier.smtplib.SMTP")
    def test_test_email_connection_success(self, mock_smtp):
        """Test successful connection test."""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        with patch("src.services.email_notifier.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.test.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = "test@test.com"
            mock_settings.smtp_password = "password"
            mock_settings.recipient_email = "recipient@test.com"
            mock_settings.email_recipient = None

            result = test_email_connection()

            assert result is True
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once()

    def test_test_email_connection_not_configured(self):
        """Test connection test when not configured."""
        with patch("src.services.email_notifier.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.test.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_username = None
            mock_settings.smtp_password = None
            mock_settings.recipient_email = None
            mock_settings.email_recipient = None

            result = test_email_connection()

            assert result is False
