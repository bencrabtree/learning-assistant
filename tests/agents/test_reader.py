"""
Tests for Reader Agent.

Tests the complete Reader Agent workflow including:
- Prompt generation
- Paper analysis with Claude
- Batch processing
- Database saving
- Error handling
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.paper import Base, Paper
from src.agents.reader import ReaderAgent, analyze_papers_batch


@pytest.fixture
def engine():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create a database session for testing."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_paper():
    """Create a sample paper for testing."""
    return Paper(
        arxiv_id="2312.12345",
        title="Constitutional AI: Harmlessness from AI Feedback",
        abstract=(
            "We introduce Constitutional AI (CAI), a method for training AI "
            "assistants to be helpful, harmless, and honest. The key innovation "
            "is using AI feedback instead of human feedback for harmlessness. "
            "We show this approach can reduce harmful outputs by 50% while "
            "maintaining helpfulness."
        ),
        authors=["Amanda Askell", "Yuntao Bai", "Deep Ganguli"],
        published_date=datetime(2023, 12, 6),
        categories=["cs.AI", "cs.LG"],
        pdf_url="https://arxiv.org/pdf/2312.12345.pdf",
        abstract_url="https://arxiv.org/abs/2312.12345",
        discovered_by="arxiv",
    )


@pytest.fixture
def mock_claude_response():
    """Mock Claude API response with typical analysis."""
    return {
        "main_claim": (
            "Constitutional AI enables models to self-improve harmlessness "
            "through AI feedback rather than human feedback alone."
        ),
        "methodology": "Two-stage RLHF with critique and revision",
        "key_results": [
            "50% reduction in harmful outputs",
            "Minimal loss in helpfulness",
            "Scales better than pure human feedback",
        ],
        "novel_contributions": (
            "Using AI-generated critiques for RLHF instead of only human labels"
        ),
        "limitations": "Requires well-defined constitution and may not catch all edge cases",
        "concepts": ["RLHF", "Constitutional AI", "AI feedback", "value alignment"],
    }


class TestReaderAgent:
    """Tests for the Reader Agent class."""

    def test_initialization(self):
        """Test that Reader Agent initializes correctly."""
        with patch("src.agents.reader.get_claude_client") as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client

            reader = ReaderAgent()

            assert reader.client == mock_client
            assert reader.model is not None
            mock_get_client.assert_called_once()

    def test_build_analysis_prompt(self, sample_paper):
        """Test prompt generation includes all paper details."""
        with patch("src.agents.reader.get_claude_client"):
            reader = ReaderAgent()
            prompt = reader.build_analysis_prompt(sample_paper)

            # Verify paper details are in prompt
            assert sample_paper.title in prompt
            assert sample_paper.abstract in prompt
            assert "Amanda Askell" in prompt
            assert "2023-12-06" in prompt
            assert "cs.AI" in prompt

            # Verify JSON schema is in prompt
            assert "main_claim" in prompt
            assert "methodology" in prompt
            assert "key_results" in prompt
            assert "novel_contributions" in prompt
            assert "limitations" in prompt
            assert "concepts" in prompt

    def test_analyze_paper_success(self, sample_paper, mock_claude_response):
        """Test successful paper analysis."""
        with patch("src.agents.reader.get_claude_client") as mock_get_client:
            mock_client = Mock()
            mock_client.chat_json.return_value = mock_claude_response
            mock_get_client.return_value = mock_client

            reader = ReaderAgent()
            analysis = reader.analyze_paper(sample_paper)

            # Verify all fields present
            assert analysis["main_claim"] == mock_claude_response["main_claim"]
            assert analysis["methodology"] == mock_claude_response["methodology"]
            assert len(analysis["key_results"]) == 3
            assert "RLHF" in analysis["concepts"]

            # Verify Claude was called correctly
            mock_client.chat_json.assert_called_once()
            call_kwargs = mock_client.chat_json.call_args[1]
            assert "prompt" in call_kwargs
            assert "model" in call_kwargs
            assert call_kwargs["temperature"] == 0.3

    def test_analyze_paper_missing_fields(self, sample_paper):
        """Test analysis handles missing fields gracefully."""
        incomplete_response = {
            "main_claim": "Test claim",
            # Missing other fields
        }

        with patch("src.agents.reader.get_claude_client") as mock_get_client:
            mock_client = Mock()
            mock_client.chat_json.return_value = incomplete_response
            mock_get_client.return_value = mock_client

            reader = ReaderAgent()
            analysis = reader.analyze_paper(sample_paper)

            # Verify missing fields are filled with defaults
            assert analysis["main_claim"] == "Test claim"
            assert analysis["methodology"] == "Not available"
            assert analysis["key_results"] == []
            assert analysis["concepts"] == []

    def test_analyze_paper_api_failure(self, sample_paper):
        """Test that API failures are properly raised."""
        with patch("src.agents.reader.get_claude_client") as mock_get_client:
            mock_client = Mock()
            mock_client.chat_json.side_effect = Exception("API rate limit exceeded")
            mock_get_client.return_value = mock_client

            reader = ReaderAgent()

            with pytest.raises(Exception) as exc_info:
                reader.analyze_paper(sample_paper)

            assert "API rate limit exceeded" in str(exc_info.value)

    def test_analyze_multiple_papers(self, mock_claude_response):
        """Test analyzing multiple papers in batch."""
        papers = [
            Paper(
                arxiv_id=f"2312.1234{i}",
                title=f"Paper {i}",
                abstract="Test abstract",
                authors=["Test Author"],
                published_date=datetime.utcnow(),
                categories=["cs.AI"],
                pdf_url="https://example.com/pdf",
                abstract_url="https://example.com/abs",
                discovered_by="arxiv",
            )
            for i in range(3)
        ]

        with patch("src.agents.reader.get_claude_client") as mock_get_client:
            mock_client = Mock()
            mock_client.chat_json.return_value = mock_claude_response
            mock_get_client.return_value = mock_client

            reader = ReaderAgent()
            results = reader.analyze_papers(papers)

            assert len(results) == 3
            assert all("arxiv_id" in r for r in results)
            assert all("analysis" in r for r in results)
            assert mock_client.chat_json.call_count == 3

    def test_analyze_papers_with_failures(self, mock_claude_response):
        """Test batch analysis continues despite individual failures."""
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
            )
            for i in range(3)
        ]

        with patch("src.agents.reader.get_claude_client") as mock_get_client:
            mock_client = Mock()
            # First call succeeds, second fails, third succeeds
            mock_client.chat_json.side_effect = [
                mock_claude_response,
                Exception("API error"),
                mock_claude_response,
            ]
            mock_get_client.return_value = mock_client

            reader = ReaderAgent()
            results = reader.analyze_papers(papers)

            # Should get 2 successful results (1st and 3rd)
            assert len(results) == 2
            assert results[0]["arxiv_id"] == "2312.12340"
            assert results[1]["arxiv_id"] == "2312.12342"

    def test_save_analysis(self, session, sample_paper, mock_claude_response):
        """Test saving analysis to database."""
        # Add paper to database
        session.add(sample_paper)
        session.commit()

        with patch("src.agents.reader.get_db_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = session
            mock_get_session.return_value.__exit__.return_value = None

            with patch("src.agents.reader.get_claude_client"):
                reader = ReaderAgent()
                reader.save_analysis(sample_paper.arxiv_id, mock_claude_response)

        # Verify paper was updated
        updated_paper = (
            session.query(Paper).filter_by(arxiv_id=sample_paper.arxiv_id).first()
        )
        assert updated_paper.main_claim == mock_claude_response["main_claim"]
        assert updated_paper.methodology == mock_claude_response["methodology"]
        assert len(updated_paper.key_results) == 3
        assert updated_paper.analyzed_at is not None

    def test_save_analysis_paper_not_found(self):
        """Test that save_analysis raises error for non-existent paper."""
        with patch("src.agents.reader.get_db_session") as mock_get_session:
            mock_session = Mock()
            mock_session.query.return_value.filter_by.return_value.first.return_value = (
                None
            )
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None

            with patch("src.agents.reader.get_claude_client"):
                reader = ReaderAgent()

                with pytest.raises(ValueError) as exc_info:
                    reader.save_analysis("nonexistent-id", {})

                assert "not found" in str(exc_info.value).lower()

    def test_analyze_and_save(self, session, mock_claude_response):
        """Test end-to-end analysis and saving."""
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
            )
            for i in range(2)
        ]

        for paper in papers:
            session.add(paper)
        session.commit()

        with patch("src.agents.reader.get_db_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = session
            mock_get_session.return_value.__exit__.return_value = None

            with patch("src.agents.reader.get_claude_client") as mock_get_client:
                mock_client = Mock()
                mock_client.chat_json.return_value = mock_claude_response
                mock_get_client.return_value = mock_client

                reader = ReaderAgent()
                count = reader.analyze_and_save(papers)

                assert count == 2
                assert mock_client.chat_json.call_count == 2

        # Verify both papers were updated in database
        for paper in papers:
            updated = session.query(Paper).filter_by(arxiv_id=paper.arxiv_id).first()
            assert updated.analyzed_at is not None
            assert updated.main_claim is not None


class TestStandaloneFunctions:
    """Tests for standalone functions used in LangGraph."""

    def test_analyze_papers_batch(self, session, mock_claude_response):
        """Test batch analysis function for LangGraph integration."""
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
            )
            for i in range(2)
        ]

        for paper in papers:
            session.add(paper)
        session.commit()

        with patch("src.agents.reader.get_db_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = session
            mock_get_session.return_value.__exit__.return_value = None

            with patch("src.agents.reader.get_claude_client") as mock_get_client:
                mock_client = Mock()
                mock_client.chat_json.return_value = mock_claude_response
                mock_get_client.return_value = mock_client

                updated_papers = analyze_papers_batch(papers)

                assert len(updated_papers) == 2
                assert all(p.analyzed_at is not None for p in updated_papers)
                assert all(p.main_claim is not None for p in updated_papers)


class TestPromptEngineering:
    """Tests for prompt quality and structure."""

    def test_prompt_includes_research_interests_context(self, sample_paper):
        """Test that prompts are properly formatted for ML researchers."""
        with patch("src.agents.reader.get_claude_client"):
            reader = ReaderAgent()
            prompt = reader.build_analysis_prompt(sample_paper)

            # Should be concise and technical
            assert "concise" in prompt.lower()
            assert "technical" in prompt.lower()

            # Should request extraction not interpretation
            assert "extract" in prompt.lower()

    def test_prompt_handles_long_author_lists(self):
        """Test that long author lists are truncated with et al."""
        paper = Paper(
            arxiv_id="2312.12345",
            title="Test Paper",
            abstract="Test abstract",
            authors=["Author 1", "Author 2", "Author 3", "Author 4", "Author 5"],
            published_date=datetime.utcnow(),
            categories=["cs.AI"],
            pdf_url="https://example.com/pdf",
            abstract_url="https://example.com/abs",
            discovered_by="arxiv",
        )

        with patch("src.agents.reader.get_claude_client"):
            reader = ReaderAgent()
            prompt = reader.build_analysis_prompt(paper)

            assert "et al." in prompt
            # Should only show first 3 authors
            assert "Author 1" in prompt
            assert "Author 2" in prompt
            assert "Author 3" in prompt
            # Author 4 and 5 should not appear individually
            assert prompt.count("Author 4") == 0
