"""
Tests for Explainer Agent.

Tests the complete Explainer Agent workflow including:
- ELI5 summary generation
- Learning questions creation
- Prerequisites identification
- Related concepts extraction
- Database saving
- Error handling
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.paper import Base, Paper
from src.agents.explainer import ExplainerAgent, explain_papers_batch


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
def analyzed_paper():
    """Create a paper that has already been analyzed by Reader Agent."""
    return Paper(
        arxiv_id="2312.12345",
        title="Constitutional AI: Harmlessness from AI Feedback",
        abstract=(
            "We introduce Constitutional AI (CAI), a method for training AI "
            "assistants to be helpful, harmless, and honest."
        ),
        authors=["Amanda Askell", "Yuntao Bai"],
        published_date=datetime(2023, 12, 6),
        categories=["cs.AI", "cs.LG"],
        pdf_url="https://arxiv.org/pdf/2312.12345.pdf",
        abstract_url="https://arxiv.org/abs/2312.12345",
        discovered_by="arxiv",
        # Reader Agent outputs
        main_claim="Constitutional AI enables safer AI through principles",
        methodology="Two-stage RLHF with critique and revision",
        key_results=["50% reduction in harmful outputs", "Maintains helpfulness"],
        novel_contributions="Self-improvement through constitutional feedback",
        limitations="Requires well-defined constitution",
        concepts=["RLHF", "Constitutional AI", "AI Safety"],
        analyzed_at=datetime.utcnow(),
    )


@pytest.fixture
def mock_explanation_response():
    """Mock Claude API response with typical explanation."""
    return {
        "eli5_summary": (
            "Instead of humans telling the AI what's good or bad for every single "
            "thing, we give it a set of rules (like a constitution) and let it judge "
            "its own responses. Like teaching someone values and letting them self-correct."
        ),
        "key_insight": (
            "You can make AI safer by teaching it principles rather than "
            "labeling every single example."
        ),
        "learning_questions": [
            "How does Constitutional AI compare to traditional RLHF?",
            "What makes a good 'constitution' for an AI system?",
            "Can this work for other AI alignment goals beyond harmlessness?",
        ],
        "prerequisites": ["RLHF basics", "Reinforcement learning fundamentals"],
        "related_concepts": ["Value alignment", "AI feedback", "Preference learning"],
    }


class TestExplainerAgent:
    """Tests for the Explainer Agent class."""

    def test_initialization(self):
        """Test that Explainer Agent initializes correctly."""
        with patch("src.agents.explainer.get_claude_client") as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client

            explainer = ExplainerAgent()

            assert explainer.client == mock_client
            assert explainer.model is not None
            mock_get_client.assert_called_once()

    def test_build_explanation_prompt(self, analyzed_paper):
        """Test prompt generation includes paper and analysis."""
        with patch("src.agents.explainer.get_claude_client"):
            explainer = ExplainerAgent()
            prompt = explainer.build_explanation_prompt(analyzed_paper)

            # Verify paper details
            assert analyzed_paper.title in prompt

            # Verify analysis is included (not abstract - uses Reader output)
            assert analyzed_paper.main_claim in prompt
            assert analyzed_paper.methodology in prompt

            # Verify JSON schema is in prompt
            assert "eli5_summary" in prompt
            assert "key_insight" in prompt
            assert "learning_questions" in prompt
            assert "prerequisites" in prompt
            assert "related_concepts" in prompt

    def test_explain_paper_success(self, analyzed_paper, mock_explanation_response):
        """Test successful paper explanation."""
        with patch("src.agents.explainer.get_claude_client") as mock_get_client:
            mock_client = Mock()
            mock_client.chat_json.return_value = mock_explanation_response
            mock_get_client.return_value = mock_client

            explainer = ExplainerAgent()
            explanation = explainer.explain_paper(analyzed_paper)

            # Verify all fields present
            assert "self-correct" in explanation["eli5_summary"]
            assert "principles" in explanation["key_insight"]
            assert len(explanation["learning_questions"]) == 3
            assert "RLHF basics" in explanation["prerequisites"]
            assert "Value alignment" in explanation["related_concepts"]

            # Verify Claude was called
            mock_client.chat_json.assert_called_once()
            call_kwargs = mock_client.chat_json.call_args[1]
            assert "prompt" in call_kwargs
            assert call_kwargs["temperature"] == 0.7  # Higher for creativity

    def test_explain_paper_missing_fields(self, analyzed_paper):
        """Test explanation handles missing fields gracefully."""
        incomplete_response = {
            "eli5_summary": "Test summary",
            # Missing other fields
        }

        with patch("src.agents.explainer.get_claude_client") as mock_get_client:
            mock_client = Mock()
            mock_client.chat_json.return_value = incomplete_response
            mock_get_client.return_value = mock_client

            explainer = ExplainerAgent()
            explanation = explainer.explain_paper(analyzed_paper)

            # Verify missing fields filled with defaults
            assert explanation["eli5_summary"] == "Test summary"
            assert explanation["key_insight"] == "Not available"
            assert explanation["learning_questions"] == []
            assert explanation["prerequisites"] == []
            assert explanation["related_concepts"] == []

    def test_explain_paper_api_failure(self, analyzed_paper):
        """Test that API failures are properly raised."""
        with patch("src.agents.explainer.get_claude_client") as mock_get_client:
            mock_client = Mock()
            mock_client.chat_json.side_effect = Exception("API timeout")
            mock_get_client.return_value = mock_client

            explainer = ExplainerAgent()

            with pytest.raises(Exception) as exc_info:
                explainer.explain_paper(analyzed_paper)

            assert "API timeout" in str(exc_info.value)

    def test_explain_unanalyzed_paper_fails(self):
        """Test that explainer requires analysis first."""
        paper_without_analysis = Paper(
            arxiv_id="2312.12346",
            title="Unanalyzed Paper",
            abstract="No analysis yet",
            authors=["Test"],
            published_date=datetime.utcnow(),
            categories=["cs.AI"],
            pdf_url="https://example.com/pdf",
            abstract_url="https://example.com/abs",
            discovered_by="arxiv",
            # No analysis fields populated
            analyzed_at=None,
        )

        with patch("src.agents.explainer.get_claude_client") as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client

            explainer = ExplainerAgent()

            with pytest.raises(ValueError) as exc_info:
                explainer.explain_paper(paper_without_analysis)

            assert "must be analyzed" in str(exc_info.value).lower()

    def test_explain_multiple_papers(self, mock_explanation_response):
        """Test explaining multiple papers in batch."""
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
                methodology="Test method",
                analyzed_at=datetime.utcnow(),
            )
            for i in range(3)
        ]

        with patch("src.agents.explainer.get_claude_client") as mock_get_client:
            mock_client = Mock()
            mock_client.chat_json.return_value = mock_explanation_response
            mock_get_client.return_value = mock_client

            explainer = ExplainerAgent()
            results = explainer.explain_papers(papers)

            assert len(results) == 3
            assert all("arxiv_id" in r for r in results)
            assert all("explanation" in r for r in results)
            assert mock_client.chat_json.call_count == 3

    def test_explain_papers_with_failures(self, mock_explanation_response):
        """Test batch explanation continues despite individual failures."""
        papers = [
            Paper(
                arxiv_id=f"2312.1234{i}",
                title=f"Paper {i}",
                abstract="Test",
                authors=["Test"],
                published_date=datetime.utcnow(),
                categories=["cs.AI"],
                pdf_url="https://example.com/pdf",
                abstract_url="https://example.com/abs",
                discovered_by="arxiv",
                main_claim="Test",
                analyzed_at=datetime.utcnow(),
            )
            for i in range(3)
        ]

        with patch("src.agents.explainer.get_claude_client") as mock_get_client:
            mock_client = Mock()
            # First succeeds, second fails, third succeeds
            mock_client.chat_json.side_effect = [
                mock_explanation_response,
                Exception("API error"),
                mock_explanation_response,
            ]
            mock_get_client.return_value = mock_client

            explainer = ExplainerAgent()
            results = explainer.explain_papers(papers)

            # Should get 2 successful results
            assert len(results) == 2
            assert results[0]["arxiv_id"] == "2312.12340"
            assert results[1]["arxiv_id"] == "2312.12342"

    def test_save_explanation(self, session, analyzed_paper, mock_explanation_response):
        """Test saving explanation to database."""
        session.add(analyzed_paper)
        session.commit()

        with patch("src.agents.explainer.get_db_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = session
            mock_get_session.return_value.__exit__.return_value = None

            with patch("src.agents.explainer.get_claude_client"):
                explainer = ExplainerAgent()
                explainer.save_explanation(
                    analyzed_paper.arxiv_id, mock_explanation_response
                )

        # Verify paper was updated
        updated = (
            session.query(Paper).filter_by(arxiv_id=analyzed_paper.arxiv_id).first()
        )
        assert "self-correct" in updated.eli5_summary
        assert updated.key_insight is not None
        assert len(updated.learning_questions) == 3
        assert updated.explained_at is not None

    def test_save_explanation_paper_not_found(self):
        """Test that save_explanation raises error for non-existent paper."""
        with patch("src.agents.explainer.get_db_session") as mock_get_session:
            mock_session = Mock()
            mock_session.query.return_value.filter_by.return_value.first.return_value = (
                None
            )
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None

            with patch("src.agents.explainer.get_claude_client"):
                explainer = ExplainerAgent()

                with pytest.raises(ValueError) as exc_info:
                    explainer.save_explanation("nonexistent-id", {})

                assert "not found" in str(exc_info.value).lower()

    def test_explain_and_save(self, session, mock_explanation_response):
        """Test end-to-end explanation and saving."""
        papers = [
            Paper(
                arxiv_id=f"2312.1234{i}",
                title=f"Paper {i}",
                abstract="Test",
                authors=["Test"],
                published_date=datetime.utcnow(),
                categories=["cs.AI"],
                pdf_url="https://example.com/pdf",
                abstract_url="https://example.com/abs",
                discovered_by="arxiv",
                main_claim="Test claim",
                analyzed_at=datetime.utcnow(),
            )
            for i in range(2)
        ]

        for paper in papers:
            session.add(paper)
        session.commit()

        with patch("src.agents.explainer.get_db_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = session
            mock_get_session.return_value.__exit__.return_value = None

            with patch("src.agents.explainer.get_claude_client") as mock_get_client:
                mock_client = Mock()
                mock_client.chat_json.return_value = mock_explanation_response
                mock_get_client.return_value = mock_client

                explainer = ExplainerAgent()
                count = explainer.explain_and_save(papers)

                assert count == 2
                assert mock_client.chat_json.call_count == 2

        # Verify both papers updated
        for paper in papers:
            updated = session.query(Paper).filter_by(arxiv_id=paper.arxiv_id).first()
            assert updated.explained_at is not None
            assert updated.eli5_summary is not None


class TestStandaloneFunctions:
    """Tests for standalone functions used in LangGraph."""

    def test_explain_papers_batch(self, session, mock_explanation_response):
        """Test batch explanation function for LangGraph integration."""
        papers = [
            Paper(
                arxiv_id=f"2312.1234{i}",
                title=f"Paper {i}",
                abstract="Test",
                authors=["Test"],
                published_date=datetime.utcnow(),
                categories=["cs.AI"],
                pdf_url="https://example.com/pdf",
                abstract_url="https://example.com/abs",
                discovered_by="arxiv",
                main_claim="Test",
                analyzed_at=datetime.utcnow(),
            )
            for i in range(2)
        ]

        for paper in papers:
            session.add(paper)
        session.commit()

        with patch("src.agents.explainer.get_db_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = session
            mock_get_session.return_value.__exit__.return_value = None

            with patch("src.agents.explainer.get_claude_client") as mock_get_client:
                mock_client = Mock()
                mock_client.chat_json.return_value = mock_explanation_response
                mock_get_client.return_value = mock_client

                updated_papers = explain_papers_batch(papers)

                assert len(updated_papers) == 2
                assert all(p.explained_at is not None for p in updated_papers)
                assert all(p.eli5_summary is not None for p in updated_papers)


class TestPromptEngineering:
    """Tests for prompt quality and educational focus."""

    def test_prompt_is_learning_focused(self, analyzed_paper):
        """Test that prompts emphasize learning and accessibility."""
        with patch("src.agents.explainer.get_claude_client"):
            explainer = ExplainerAgent()
            prompt = explainer.build_explanation_prompt(analyzed_paper)

            # Should focus on learning
            assert "learn" in prompt.lower() or "understand" in prompt.lower()
            assert "eli5" in prompt.lower() or "explain like" in prompt.lower()

            # Should request questions
            assert "question" in prompt.lower()

    def test_prompt_includes_analysis_context(self, analyzed_paper):
        """Test that prompts use Reader Agent output as context."""
        with patch("src.agents.explainer.get_claude_client"):
            explainer = ExplainerAgent()
            prompt = explainer.build_explanation_prompt(analyzed_paper)

            # Should include analysis as context
            assert analyzed_paper.main_claim in prompt
            assert analyzed_paper.methodology in prompt
            if analyzed_paper.concepts:
                assert any(concept in prompt for concept in analyzed_paper.concepts)
