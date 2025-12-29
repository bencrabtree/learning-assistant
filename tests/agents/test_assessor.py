"""
Tests for Assessor Agent.

Tests the breakthrough detection functionality including:
- Prompt generation
- Paper assessment with Claude
- Breakthrough score calculation
- Database persistence
- Error handling
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.agents.assessor import AssessorAgent, assess_papers_batch, get_breakthrough_papers
from src.models.paper import Base, Paper


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
    """Create a sample analyzed paper for testing."""
    return Paper(
        arxiv_id="2312.12345",
        title="Attention Is All You Need",
        abstract=(
            "We propose a new simple network architecture, the Transformer, "
            "based solely on attention mechanisms, dispensing with recurrence "
            "and convolutions entirely."
        ),
        authors=["Ashish Vaswani", "Noam Shazeer"],
        published_date=datetime(2023, 12, 6),
        categories=["cs.AI", "cs.LG"],
        pdf_url="https://arxiv.org/pdf/2312.12345.pdf",
        abstract_url="https://arxiv.org/abs/2312.12345",
        discovered_by="arxiv",
        main_claim="Transformers outperform RNNs on sequence tasks",
        methodology="Self-attention mechanism with positional encoding",
        novel_contributions="Pure attention architecture without recurrence",
        key_results=["BLEU score of 41.8 on translation"],
    )


@pytest.fixture
def mock_breakthrough_response():
    """Mock Claude API response for breakthrough assessment."""
    return {
        "novelty_score": 0.9,
        "impact_score": 0.95,
        "evidence_score": 0.85,
        "significance_score": 0.9,
        "reasoning": "Transformers fundamentally changed NLP by eliminating recurrence.",
        "key_strengths": ["Novel architecture", "Strong empirical results"],
        "key_weaknesses": ["Quadratic complexity with sequence length"],
        "read_priority": "immediate",
    }


@pytest.fixture
def mock_incremental_response():
    """Mock Claude API response for incremental paper."""
    return {
        "novelty_score": 0.4,
        "impact_score": 0.3,
        "evidence_score": 0.5,
        "significance_score": 0.4,
        "reasoning": "Minor improvement on existing approach.",
        "key_strengths": ["Good ablations"],
        "key_weaknesses": ["Limited novelty"],
        "read_priority": "when_free",
    }


class TestAssessorAgent:
    """Tests for the Assessor Agent class."""

    def test_initialization(self):
        """Test that Assessor Agent initializes correctly."""
        with patch("src.agents.assessor.get_claude_client") as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client

            assessor = AssessorAgent()

            assert assessor.client == mock_client
            assert assessor.WEIGHT_NOVELTY == 0.30
            assert assessor.WEIGHT_IMPACT == 0.30
            assert assessor.WEIGHT_EVIDENCE == 0.20
            assert assessor.WEIGHT_SIGNIFICANCE == 0.20
            assert assessor.BREAKTHROUGH_THRESHOLD == 0.8
            mock_get_client.assert_called_once()

    def test_build_assessment_prompt(self, sample_paper):
        """Test prompt generation includes paper analysis."""
        with patch("src.agents.assessor.get_claude_client"):
            assessor = AssessorAgent()
            prompt = assessor.build_assessment_prompt(sample_paper)

            # Verify paper details are in prompt
            assert sample_paper.title in prompt
            assert sample_paper.abstract in prompt
            assert sample_paper.main_claim in prompt
            assert sample_paper.methodology in prompt

            # Verify scoring criteria
            assert "NOVELTY" in prompt
            assert "IMPACT" in prompt
            assert "EVIDENCE" in prompt
            assert "SIGNIFICANCE" in prompt

            # Verify high bar messaging
            assert "high bar" in prompt.lower()
            assert "rare" in prompt.lower()

    def test_assess_paper_breakthrough(self, sample_paper, mock_breakthrough_response):
        """Test assessment of a breakthrough paper."""
        with patch("src.agents.assessor.get_claude_client") as mock_get_client:
            mock_client = Mock()
            mock_client.chat_json.return_value = mock_breakthrough_response
            mock_get_client.return_value = mock_client

            assessor = AssessorAgent()
            assessment = assessor.assess_paper(sample_paper)

            # Verify scores
            assert assessment["novelty_score"] == 0.9
            assert assessment["impact_score"] == 0.95
            assert assessment["evidence_score"] == 0.85
            assert assessment["significance_score"] == 0.9

            # Verify breakthrough calculation
            expected_score = 0.30 * 0.9 + 0.30 * 0.95 + 0.20 * 0.85 + 0.20 * 0.9
            assert abs(assessment["breakthrough_score"] - expected_score) < 0.01
            assert assessment["is_breakthrough"] is True

            # Verify metadata
            assert "key_strengths" in assessment
            assert "key_weaknesses" in assessment
            assert assessment["read_priority"] == "immediate"

    def test_assess_paper_incremental(self, sample_paper, mock_incremental_response):
        """Test assessment of an incremental paper."""
        with patch("src.agents.assessor.get_claude_client") as mock_get_client:
            mock_client = Mock()
            mock_client.chat_json.return_value = mock_incremental_response
            mock_get_client.return_value = mock_client

            assessor = AssessorAgent()
            assessment = assessor.assess_paper(sample_paper)

            # Verify low scores
            assert assessment["novelty_score"] == 0.4
            assert assessment["impact_score"] == 0.3

            # Verify not a breakthrough
            assert assessment["breakthrough_score"] < 0.8
            assert assessment["is_breakthrough"] is False

    def test_assess_paper_api_failure(self, sample_paper):
        """Test that API failures return safe defaults."""
        with patch("src.agents.assessor.get_claude_client") as mock_get_client:
            mock_client = Mock()
            mock_client.chat_json.side_effect = Exception("API rate limit exceeded")
            mock_get_client.return_value = mock_client

            assessor = AssessorAgent()
            assessment = assessor.assess_paper(sample_paper)

            # Should return safe defaults
            assert assessment["breakthrough_score"] == 0.5
            assert assessment["is_breakthrough"] is False
            assert assessment["confidence"] == 0.0
            assert "API rate limit" in assessment["reasoning"]

    def test_assess_paper_normalizes_scores(self, sample_paper):
        """Test that scores are normalized to 0-1 range."""
        out_of_range_response = {
            "novelty_score": 1.5,  # Over 1
            "impact_score": -0.2,  # Negative
            "evidence_score": 0.5,
            "significance_score": 0.5,
        }

        with patch("src.agents.assessor.get_claude_client") as mock_get_client:
            mock_client = Mock()
            mock_client.chat_json.return_value = out_of_range_response
            mock_get_client.return_value = mock_client

            assessor = AssessorAgent()
            assessment = assessor.assess_paper(sample_paper)

            # Scores should be clamped to 0-1
            assert 0 <= assessment["novelty_score"] <= 1
            assert 0 <= assessment["impact_score"] <= 1

    def test_assess_and_save(self, session, sample_paper, mock_breakthrough_response):
        """Test assessment with database persistence."""
        session.add(sample_paper)
        session.commit()

        with patch("src.agents.assessor.get_db_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = session
            mock_get_session.return_value.__exit__.return_value = None

            with patch("src.agents.assessor.get_claude_client") as mock_get_client:
                mock_client = Mock()
                mock_client.chat_json.return_value = mock_breakthrough_response
                mock_get_client.return_value = mock_client

                assessor = AssessorAgent()
                assessment = assessor.assess_and_save(sample_paper)

                assert assessment["is_breakthrough"] is True

        # Verify paper was updated in database
        updated = session.query(Paper).filter_by(arxiv_id=sample_paper.arxiv_id).first()
        assert updated.breakthrough_score is not None
        assert updated.assessed_at is not None


class TestBatchFunctions:
    """Tests for batch processing functions."""

    def test_assess_papers_batch(self, session, mock_breakthrough_response):
        """Test batch assessment function."""
        papers = [
            Paper(
                arxiv_id=f"2312.1234{i}",
                title=f"Paper {i}",
                abstract="Test abstract",
                authors=["Test"],
                published_date=datetime.utcnow(),
                categories=["cs.AI"],
                pdf_url="https://example.com/pdf",
                abstract_url="https://example.com/abs",
                discovered_by="arxiv",
                main_claim="Test claim",
            )
            for i in range(3)
        ]

        for paper in papers:
            session.add(paper)
        session.commit()

        with patch("src.agents.assessor.get_db_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = session
            mock_get_session.return_value.__exit__.return_value = None

            with patch("src.agents.assessor.get_claude_client") as mock_get_client:
                mock_client = Mock()
                mock_client.chat_json.return_value = mock_breakthrough_response
                mock_get_client.return_value = mock_client

                result_papers, assessments = assess_papers_batch(papers)

                assert len(result_papers) == 3
                assert len(assessments) == 3
                assert all("arxiv_id" in a for a in assessments)
                assert all("breakthrough_score" in a for a in assessments)

    def test_get_breakthrough_papers(
        self, session, mock_breakthrough_response, mock_incremental_response
    ):
        """Test filtering to breakthrough papers only."""
        papers = [
            Paper(
                arxiv_id=f"2312.1234{i}",
                title=f"Paper {i}",
                abstract="Test abstract",
                authors=["Test"],
                published_date=datetime.utcnow(),
                categories=["cs.AI"],
                pdf_url="https://example.com/pdf",
                abstract_url="https://example.com/abs",
                discovered_by="arxiv",
                main_claim="Test claim",
            )
            for i in range(3)
        ]

        for paper in papers:
            session.add(paper)
        session.commit()

        with patch("src.agents.assessor.get_db_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = session
            mock_get_session.return_value.__exit__.return_value = None

            with patch("src.agents.assessor.get_claude_client") as mock_get_client:
                mock_client = Mock()
                # First paper is breakthrough, others are incremental
                mock_client.chat_json.side_effect = [
                    mock_breakthrough_response,
                    mock_incremental_response,
                    mock_incremental_response,
                ]
                mock_get_client.return_value = mock_client

                breakthroughs = get_breakthrough_papers(papers)

                # Only first paper should be a breakthrough
                assert len(breakthroughs) == 1
                assert breakthroughs[0].arxiv_id == "2312.12340"


class TestPromptEngineering:
    """Tests for prompt quality."""

    def test_prompt_enforces_high_bar(self, sample_paper):
        """Test that prompt emphasizes high bar for breakthroughs."""
        with patch("src.agents.assessor.get_claude_client"):
            assessor = AssessorAgent()
            prompt = assessor.build_assessment_prompt(sample_paper)

            # Should emphasize rarity
            assert "HIGH BAR" in prompt or "high bar" in prompt.lower()
            assert "rare" in prompt.lower() or "1-2%" in prompt

    def test_prompt_includes_scoring_rubric(self, sample_paper):
        """Test that prompt includes detailed scoring rubric."""
        with patch("src.agents.assessor.get_claude_client"):
            assessor = AssessorAgent()
            prompt = assessor.build_assessment_prompt(sample_paper)

            # Should have score ranges
            assert "0.9" in prompt or "0.8" in prompt
            assert "0.0" in prompt or "0.4" in prompt
