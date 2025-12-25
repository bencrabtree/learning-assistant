"""
Tests for Paper model and database schema.

Tests the complete Paper model including:
- Core metadata fields
- Reader agent outputs
- Explainer agent outputs
- Citation data
- Scoring fields
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.paper import Base, Citation, Paper


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


class TestPaperModel:
    """Tests for the Paper model."""

    def test_create_basic_paper(self, session):
        """Test creating a paper with minimal required fields."""
        paper = Paper(
            arxiv_id="2312.12345",
            title="Test Paper on AI Safety",
            abstract="This paper explores AI safety through constitutional approaches.",
            authors=["Alice Smith", "Bob Jones"],
            published_date=datetime(2023, 12, 15),
            categories=["cs.AI", "cs.LG"],
            pdf_url="https://arxiv.org/pdf/2312.12345.pdf",
            abstract_url="https://arxiv.org/abs/2312.12345",
            discovered_by="arxiv",
        )

        session.add(paper)
        session.commit()

        # Verify it was saved
        retrieved = session.query(Paper).filter_by(arxiv_id="2312.12345").first()
        assert retrieved is not None
        assert retrieved.title == "Test Paper on AI Safety"
        assert len(retrieved.authors) == 2
        assert "cs.AI" in retrieved.categories

    def test_paper_with_reader_agent_outputs(self, session):
        """Test paper with analysis fields populated by Reader agent."""
        paper = Paper(
            arxiv_id="2312.12346",
            title="Constitutional AI Research",
            abstract="Testing abstract",
            authors=["Researcher One"],
            published_date=datetime.utcnow(),
            categories=["cs.AI"],
            pdf_url="https://example.com/pdf",
            abstract_url="https://example.com/abs",
            discovered_by="arxiv",
            # Reader agent outputs
            main_claim="Constitutional AI enables safer AI through principles",
            methodology="Two-stage RLHF with critique and revision",
            key_results=["50% reduction in harmful outputs", "Maintains helpfulness"],
            novel_contributions="Self-improvement through constitutional feedback",
            limitations="Requires well-defined constitution",
            concepts=["RLHF", "Constitutional AI", "AI Safety"],
            analyzed_at=datetime.utcnow(),
        )

        session.add(paper)
        session.commit()

        retrieved = session.query(Paper).filter_by(arxiv_id="2312.12346").first()
        assert retrieved.main_claim is not None
        assert "Constitutional AI" in retrieved.main_claim
        assert len(retrieved.key_results) == 2
        assert "RLHF" in retrieved.concepts
        assert retrieved.analyzed_at is not None

    def test_paper_with_explainer_agent_outputs(self, session):
        """Test paper with explanation fields populated by Explainer agent."""
        paper = Paper(
            arxiv_id="2312.12347",
            title="ELI5 Test Paper",
            abstract="Testing abstract",
            authors=["Explainer Test"],
            published_date=datetime.utcnow(),
            categories=["cs.AI"],
            pdf_url="https://example.com/pdf",
            abstract_url="https://example.com/abs",
            discovered_by="arxiv",
            # Explainer agent outputs
            eli5_summary="Like teaching someone values and letting them self-correct",
            key_insight="Principles scale better than examples",
            learning_questions=[
                "How does CAI compare to RLHF?",
                "What makes a good constitution?",
            ],
            prerequisites=["RLHF basics", "Reinforcement learning"],
            related_concepts=["Value alignment", "AI feedback"],
            explained_at=datetime.utcnow(),
        )

        session.add(paper)
        session.commit()

        retrieved = session.query(Paper).filter_by(arxiv_id="2312.12347").first()
        assert retrieved.eli5_summary is not None
        assert "self-correct" in retrieved.eli5_summary
        assert len(retrieved.learning_questions) == 2
        assert "RLHF basics" in retrieved.prerequisites
        assert retrieved.explained_at is not None

    def test_paper_with_citation_data(self, session):
        """Test paper with citation metrics from Semantic Scholar."""
        paper = Paper(
            arxiv_id="2312.12348",
            title="Highly Cited Paper",
            abstract="Testing citations",
            authors=["Citation Test"],
            published_date=datetime.utcnow() - timedelta(days=30),
            categories=["cs.AI"],
            pdf_url="https://example.com/pdf",
            abstract_url="https://example.com/abs",
            discovered_by="arxiv",
            # Citation data
            citation_count=234,
            influential_citation_count=45,
            citations_updated_at=datetime.utcnow(),
        )

        session.add(paper)
        session.commit()

        retrieved = session.query(Paper).filter_by(arxiv_id="2312.12348").first()
        assert retrieved.citation_count == 234
        assert retrieved.influential_citation_count == 45
        assert retrieved.citations_updated_at is not None

    def test_paper_with_scoring(self, session):
        """Test paper with relevance scoring."""
        paper = Paper(
            arxiv_id="2312.12349",
            title="Relevant Paper",
            abstract="Testing scoring",
            authors=["Score Test"],
            published_date=datetime.utcnow(),
            categories=["cs.AI"],
            pdf_url="https://example.com/pdf",
            abstract_url="https://example.com/abs",
            discovered_by="arxiv",
            # Scoring data
            relevance_score=0.92,
            score_components={
                "interest_match": 0.95,
                "social_proof": 0.85,
                "citation_velocity": 0.90,
                "recency": 1.0,
            },
            scored_at=datetime.utcnow(),
        )

        session.add(paper)
        session.commit()

        retrieved = session.query(Paper).filter_by(arxiv_id="2312.12349").first()
        assert retrieved.relevance_score == 0.92
        assert retrieved.score_components["interest_match"] == 0.95
        assert retrieved.scored_at is not None

    def test_complete_paper_workflow(self, session):
        """Test complete workflow: discovery → analysis → explanation → scoring."""
        discovered_at = datetime.utcnow()

        # 1. Discovered
        paper = Paper(
            arxiv_id="2312.12350",
            title="Complete Workflow Test",
            abstract="Testing full pipeline",
            authors=["Workflow Test"],
            published_date=datetime.utcnow() - timedelta(days=1),
            categories=["cs.AI"],
            pdf_url="https://example.com/pdf",
            abstract_url="https://example.com/abs",
            discovered_by="arxiv",
            discovered_at=discovered_at,
        )
        session.add(paper)
        session.commit()

        # 2. Analyzed by Reader
        paper.main_claim = "Test claim"
        paper.methodology = "Test methodology"
        paper.analyzed_at = discovered_at + timedelta(minutes=5)
        session.commit()

        # 3. Explained by Explainer
        paper.eli5_summary = "Test ELI5"
        paper.key_insight = "Test insight"
        paper.explained_at = discovered_at + timedelta(minutes=10)
        session.commit()

        # 4. Citations fetched
        paper.citation_count = 15
        paper.citations_updated_at = discovered_at + timedelta(minutes=15)
        session.commit()

        # 5. Scored by Curator
        paper.relevance_score = 0.85
        paper.scored_at = discovered_at + timedelta(minutes=20)
        session.commit()

        # Verify complete pipeline
        retrieved = session.query(Paper).filter_by(arxiv_id="2312.12350").first()
        assert retrieved.discovered_at is not None
        assert retrieved.analyzed_at is not None
        assert retrieved.explained_at is not None
        assert retrieved.citations_updated_at is not None
        assert retrieved.scored_at is not None
        assert retrieved.relevance_score == 0.85


class TestCitationModel:
    """Tests for the Citation model (historical tracking)."""

    def test_create_citation_record(self, session):
        """Test creating a citation record."""
        # First create a paper
        paper = Paper(
            arxiv_id="2312.12351",
            title="Citation Test Paper",
            abstract="Testing citations",
            authors=["Test Author"],
            published_date=datetime.utcnow(),
            categories=["cs.AI"],
            pdf_url="https://example.com/pdf",
            abstract_url="https://example.com/abs",
            discovered_by="arxiv",
        )
        session.add(paper)
        session.commit()

        # Add citation record
        citation = Citation(
            paper_id="2312.12351",
            citation_count=50,
            citations_this_week=5,
            velocity_score=0.1,
            source="semantic_scholar",
        )
        session.add(citation)
        session.commit()

        # Verify
        retrieved = (
            session.query(Citation).filter_by(paper_id="2312.12351").first()
        )
        assert retrieved.citation_count == 50
        assert retrieved.citations_this_week == 5
        assert retrieved.source == "semantic_scholar"

    def test_citation_cascade_delete(self, session):
        """Test that deleting a paper deletes its citations."""
        paper = Paper(
            arxiv_id="2312.12352",
            title="Delete Test",
            abstract="Testing cascade delete",
            authors=["Test"],
            published_date=datetime.utcnow(),
            categories=["cs.AI"],
            pdf_url="https://example.com/pdf",
            abstract_url="https://example.com/abs",
            discovered_by="arxiv",
        )
        session.add(paper)

        citation = Citation(paper_id="2312.12352", citation_count=10)
        session.add(citation)
        session.commit()

        # Delete paper
        session.delete(paper)
        session.commit()

        # Citations should be gone
        assert session.query(Citation).filter_by(paper_id="2312.12352").count() == 0


class TestDefaultValues:
    """Test that default values work correctly."""

    def test_citation_count_defaults_to_zero(self, session):
        """Test that citation_count defaults to 0."""
        paper = Paper(
            arxiv_id="2312.12353",
            title="Default Test",
            abstract="Testing defaults",
            authors=["Test"],
            published_date=datetime.utcnow(),
            categories=["cs.AI"],
            pdf_url="https://example.com/pdf",
            abstract_url="https://example.com/abs",
            discovered_by="arxiv",
        )
        session.add(paper)
        session.commit()

        retrieved = session.query(Paper).filter_by(arxiv_id="2312.12353").first()
        assert retrieved.citation_count == 0
        assert retrieved.influential_citation_count == 0

    def test_discovered_at_auto_populated(self, session):
        """Test that discovered_at is automatically set."""
        before = datetime.utcnow()

        paper = Paper(
            arxiv_id="2312.12354",
            title="Auto Timestamp Test",
            abstract="Testing auto timestamp",
            authors=["Test"],
            published_date=datetime.utcnow(),
            categories=["cs.AI"],
            pdf_url="https://example.com/pdf",
            abstract_url="https://example.com/abs",
            discovered_by="arxiv",
        )
        session.add(paper)
        session.commit()

        after = datetime.utcnow()

        retrieved = session.query(Paper).filter_by(arxiv_id="2312.12354").first()
        assert before <= retrieved.discovered_at <= after


class TestJSONFields:
    """Test JSON field handling."""

    def test_empty_lists_in_json_fields(self, session):
        """Test that empty lists work in JSON fields."""
        paper = Paper(
            arxiv_id="2312.12355",
            title="Empty JSON Test",
            abstract="Testing empty JSON",
            authors=[],  # Empty list
            published_date=datetime.utcnow(),
            categories=[],  # Empty list
            pdf_url="https://example.com/pdf",
            abstract_url="https://example.com/abs",
            discovered_by="arxiv",
            key_results=[],  # Empty list
            concepts=[],  # Empty list
        )
        session.add(paper)
        session.commit()

        retrieved = session.query(Paper).filter_by(arxiv_id="2312.12355").first()
        assert retrieved.authors == []
        assert retrieved.categories == []
        assert retrieved.key_results == []
        assert retrieved.concepts == []

    def test_none_values_in_optional_json_fields(self, session):
        """Test that None works for optional JSON fields."""
        paper = Paper(
            arxiv_id="2312.12356",
            title="None JSON Test",
            abstract="Testing None in JSON",
            authors=["Test"],
            published_date=datetime.utcnow(),
            categories=["cs.AI"],
            pdf_url="https://example.com/pdf",
            abstract_url="https://example.com/abs",
            discovered_by="arxiv",
            # Optional JSON fields left as None
            key_results=None,
            concepts=None,
            learning_questions=None,
        )
        session.add(paper)
        session.commit()

        retrieved = session.query(Paper).filter_by(arxiv_id="2312.12356").first()
        assert retrieved.key_results is None
        assert retrieved.concepts is None
        assert retrieved.learning_questions is None
