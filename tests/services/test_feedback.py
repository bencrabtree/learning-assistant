"""
Tests for the feedback recording service.
"""

from datetime import UTC, datetime
from unittest.mock import patch

from src.models.paper import Paper, ReadingProgress
from src.services.feedback import (
    RATING_MAP,
    get_feedback_stats,
    get_paper_feedback,
    record_feedback,
)


class TestRatingMap:
    """Test rating value mappings."""

    def test_good_rating_maps_to_5(self):
        """Test good rating maps to 5."""
        assert RATING_MAP["good"] == 5

    def test_neutral_rating_maps_to_3(self):
        """Test neutral rating maps to 3."""
        assert RATING_MAP["neutral"] == 3

    def test_bad_rating_maps_to_1(self):
        """Test bad rating maps to 1."""
        assert RATING_MAP["bad"] == 1


class TestRecordFeedback:
    """Test recording feedback on papers."""

    def test_record_feedback_with_string_good(self, db_session):
        """Test recording feedback with 'good' string."""
        # Create a paper
        with db_session() as db:
            paper = Paper(
                arxiv_id="2312.test.1",
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
            result = record_feedback("2312.test.1", "good", source="email")

        assert result["success"] is True
        assert result["rating"] == 5
        assert "Thanks for your feedback" in result["message"]

    def test_record_feedback_with_string_bad(self, db_session):
        """Test recording feedback with 'bad' string."""
        with db_session() as db:
            paper = Paper(
                arxiv_id="2312.test.2",
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
            result = record_feedback("2312.test.2", "bad", source="cli")

        assert result["success"] is True
        assert result["rating"] == 1

    def test_record_feedback_with_integer(self, db_session):
        """Test recording feedback with integer value."""
        with db_session() as db:
            paper = Paper(
                arxiv_id="2312.test.3",
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
            result = record_feedback("2312.test.3", 4, source="tui")

        assert result["success"] is True
        assert result["rating"] == 4

    def test_record_feedback_invalid_string(self):
        """Test recording feedback with invalid string."""
        result = record_feedback("2312.test.4", "excellent")

        assert result["success"] is False
        assert "Invalid rating" in result["message"]

    def test_record_feedback_invalid_range(self):
        """Test recording feedback with out-of-range value."""
        result = record_feedback("2312.test.5", 10)

        assert result["success"] is False
        assert "must be 1-5" in result["message"]

    def test_record_feedback_paper_not_found(self, db_session):
        """Test recording feedback for non-existent paper."""
        with patch("src.services.feedback.get_db_session", db_session):
            result = record_feedback("nonexistent.paper", "good")

        assert result["success"] is False
        assert "not found" in result["message"]

    def test_record_feedback_creates_progress(self, db_session):
        """Test that recording feedback creates ReadingProgress if not exists."""
        with db_session() as db:
            paper = Paper(
                arxiv_id="2312.test.6",
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

        # Record feedback
        with patch("src.services.feedback.get_db_session", db_session):
            result = record_feedback("2312.test.6", "neutral", source="email")
        assert result["success"] is True

        # Verify ReadingProgress was created
        with db_session() as db:
            progress = db.query(ReadingProgress).filter_by(paper_id="2312.test.6").first()
            assert progress is not None
            assert progress.rating == 3

    def test_record_feedback_updates_existing_progress(self, db_session):
        """Test that recording feedback updates existing ReadingProgress."""
        with db_session() as db:
            paper = Paper(
                arxiv_id="2312.test.7",
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
            progress = ReadingProgress(paper_id="2312.test.7", status="reading")
            db.add(progress)

        # Record feedback
        with patch("src.services.feedback.get_db_session", db_session):
            result = record_feedback("2312.test.7", "good", source="cli")
        assert result["success"] is True

        # Verify ReadingProgress was updated
        with db_session() as db:
            progress = db.query(ReadingProgress).filter_by(paper_id="2312.test.7").first()
            assert progress.rating == 5


class TestGetPaperFeedback:
    """Test getting feedback for a paper."""

    def test_get_feedback_exists(self, db_session):
        """Test getting existing feedback."""
        with db_session() as db:
            paper = Paper(
                arxiv_id="2312.feedback.1",
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
            progress = ReadingProgress(
                paper_id="2312.feedback.1",
                status="finished",
                rating=4,
            )
            db.add(progress)

        with patch("src.services.feedback.get_db_session", db_session):
            result = get_paper_feedback("2312.feedback.1")

        assert result is not None
        assert result["rating"] == 4

    def test_get_feedback_not_exists(self, db_session):
        """Test getting feedback for paper without feedback."""
        with patch("src.services.feedback.get_db_session", db_session):
            result = get_paper_feedback("nonexistent.paper")
        assert result is None

    def test_get_feedback_no_rating(self, db_session):
        """Test getting feedback when progress exists but no rating."""
        with db_session() as db:
            paper = Paper(
                arxiv_id="2312.feedback.2",
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
            progress = ReadingProgress(paper_id="2312.feedback.2", status="reading")
            db.add(progress)

        with patch("src.services.feedback.get_db_session", db_session):
            result = get_paper_feedback("2312.feedback.2")
        assert result is None


class TestGetFeedbackStats:
    """Test getting feedback statistics."""

    def test_get_stats_empty(self, db_session):
        """Test getting stats with no feedback."""
        with patch("src.services.feedback.get_db_session", db_session):
            result = get_feedback_stats()

        assert result["total_feedback"] == 0
        assert result["good"] == 0
        assert result["neutral"] == 0
        assert result["bad"] == 0

    def test_get_stats_with_feedback(self, db_session):
        """Test getting stats with various feedback."""
        with db_session() as db:
            for i in range(3):
                paper = Paper(
                    arxiv_id=f"2312.stats.{i}",
                    title=f"Test Paper {i}",
                    abstract="Abstract",
                    authors=["Author"],
                    published_date=datetime.now(UTC),
                    categories=["cs.AI"],
                    pdf_url="http://example.com/pdf",
                    abstract_url="http://example.com/abs",
                    discovered_by="test",
                )
                db.add(paper)

            # Add feedback: good (5), neutral (3), bad (1)
            db.add(ReadingProgress(paper_id="2312.stats.0", status="finished", rating=5))
            db.add(ReadingProgress(paper_id="2312.stats.1", status="finished", rating=3))
            db.add(ReadingProgress(paper_id="2312.stats.2", status="finished", rating=1))

        with patch("src.services.feedback.get_db_session", db_session):
            result = get_feedback_stats()

        assert result["total_feedback"] == 3
        assert result["good"] == 1
        assert result["neutral"] == 1
        assert result["bad"] == 1
