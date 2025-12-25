"""
Unit tests for Database operations.

Tests database connection, session management, and model operations.
"""

from datetime import UTC, datetime

import pytest

from src.models.paper import Paper


class TestDatabaseSession:
    """Test session management with context manager."""

    def test_session_context_manager(self, db_session):
        """Test that session context manager works correctly."""
        with db_session() as db:
            # Should be able to query
            count = db.query(Paper).count()
            assert isinstance(count, int)
            assert count == 0  # Fresh database

    def test_session_commits_on_exit(self, db_session):
        """Test that changes are committed when context exits."""
        paper_id = "test.commit.12345"

        # Create paper in context
        with db_session() as db:
            paper = Paper(
                arxiv_id=paper_id,
                title="Test Commit",
                abstract="Testing auto-commit",
                authors=["Test"],
                published_date=datetime.now(UTC),
                categories=["cs.AI"],
                pdf_url="http://example.com/pdf",
                abstract_url="http://example.com/abs",
                discovered_by="test",
            )
            db.add(paper)

        # Should be able to find it in new session
        with db_session() as db:
            found = db.query(Paper).filter_by(arxiv_id=paper_id).first()
            assert found is not None
            assert found.title == "Test Commit"


class TestPaperModel:
    """Test Paper model operations."""

    def test_create_paper(self, db_session, sample_paper_data):
        """Test creating a paper in the database."""
        with db_session() as db:
            paper = Paper(**sample_paper_data)
            db.add(paper)

        # Verify it was saved
        with db_session() as db:
            found = db.query(Paper).filter_by(arxiv_id=sample_paper_data["arxiv_id"]).first()
            assert found is not None
            assert found.title == sample_paper_data["title"]

    def test_paper_primary_key(self, db_session, sample_paper_data):
        """Test that arxiv_id is the primary key."""
        from sqlalchemy.exc import IntegrityError

        with db_session() as db:
            paper = Paper(**sample_paper_data)
            db.add(paper)

        # Try to add duplicate (should fail)
        with pytest.raises(IntegrityError), db_session() as db:
            duplicate = Paper(**sample_paper_data)
            db.add(duplicate)

    def test_paper_timestamps(self, db_session):
        """Test that discovered_at timestamp is set automatically."""
        with db_session() as db:
            paper = Paper(
                arxiv_id="test.timestamp.123",
                title="Timestamp Test",
                abstract="Testing timestamps",
                authors=["Test"],
                published_date=datetime.now(UTC),
                categories=["cs.AI"],
                pdf_url="http://example.com/pdf",
                abstract_url="http://example.com/abs",
                discovered_by="test",
            )
            db.add(paper)

        # Check timestamp was set
        with db_session() as db:
            found = db.query(Paper).filter_by(arxiv_id="test.timestamp.123").first()
            assert found.discovered_at is not None
            assert isinstance(found.discovered_at, datetime)

    def test_paper_analysis_fields_default_none(self, db_session, sample_paper_data):
        """Test that analysis fields default to None."""
        with db_session() as db:
            paper = Paper(**sample_paper_data)
            db.add(paper)

        with db_session() as db:
            found = db.query(Paper).filter_by(arxiv_id=sample_paper_data["arxiv_id"]).first()
            # Analysis fields should be None for new papers
            assert found.main_claim is None
            assert found.methodology is None
            assert found.analyzed_at is None

    def test_update_paper_analysis(self, db_session, sample_paper_data):
        """Test updating paper with analysis data."""
        # Create paper
        with db_session() as db:
            paper = Paper(**sample_paper_data)
            db.add(paper)

        # Update with analysis
        with db_session() as db:
            paper = db.query(Paper).filter_by(arxiv_id=sample_paper_data["arxiv_id"]).first()
            paper.main_claim = "This is the main claim"
            paper.methodology = "They used transformers"
            paper.analyzed_at = datetime.now(UTC)

        # Verify update
        with db_session() as db:
            paper = db.query(Paper).filter_by(arxiv_id=sample_paper_data["arxiv_id"]).first()
            assert paper.main_claim == "This is the main claim"
            assert paper.methodology == "They used transformers"
            assert paper.analyzed_at is not None


class TestDatabaseQueries:
    """Test common database query patterns."""

    def test_query_unanalyzed_papers(self, db_session):
        """Test querying for papers that haven't been analyzed."""
        # Create analyzed and unanalyzed papers
        with db_session() as db:
            analyzed = Paper(
                arxiv_id="analyzed.123",
                title="Analyzed",
                abstract="Abstract",
                authors=["Test"],
                published_date=datetime.now(UTC),
                categories=["cs.AI"],
                pdf_url="http://example.com/pdf",
                abstract_url="http://example.com/abs",
                discovered_by="test",
            )
            analyzed.analyzed_at = datetime.now(UTC)

            unanalyzed = Paper(
                arxiv_id="unanalyzed.123",
                title="Unanalyzed",
                abstract="Abstract",
                authors=["Test"],
                published_date=datetime.now(UTC),
                categories=["cs.AI"],
                pdf_url="http://example.com/pdf2",
                abstract_url="http://example.com/abs2",
                discovered_by="test",
            )

            db.add(analyzed)
            db.add(unanalyzed)

        # Query unanalyzed
        with db_session() as db:
            unanalyzed_papers = db.query(Paper).filter(Paper.analyzed_at.is_(None)).all()
            assert len(unanalyzed_papers) == 1
            assert unanalyzed_papers[0].arxiv_id == "unanalyzed.123"

    def test_count_papers_by_category(self, db_session):
        """Test counting papers by category."""
        with db_session() as db:
            # Add papers in different categories
            for i in range(3):
                paper = Paper(
                    arxiv_id=f"ai.{i}",
                    title=f"AI Paper {i}",
                    abstract="Abstract",
                    authors=["Test"],
                    published_date=datetime.now(UTC),
                    categories=["cs.AI"],
                    pdf_url=f"http://example.com/pdf{i}",
                    abstract_url=f"http://example.com/abs{i}",
                    discovered_by="test",
                )
                db.add(paper)

        with db_session() as db:
            total = db.query(Paper).count()
            assert total == 3  # Exactly 3 in isolated test database
