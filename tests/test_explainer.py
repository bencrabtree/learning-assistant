"""
Comprehensive Unit Tests for Explainer Agent

All tests properly isolated with database session mocking.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from src.agents.explainer import ExplainerAgent, explain_papers_batch
from src.models.paper import Paper


@pytest.fixture
def analyzed_paper(db_session):
    """Create an analyzed paper in the test database."""
    with db_session() as db:
        paper = Paper(
            arxiv_id="2312.analyzed",
            title="Multi-Agent Coordination",
            abstract="This paper presents multi-agent coordination.",
            authors=["Alice", "Bob"],
            published_date=datetime.now(timezone.utc),
            categories=["cs.AI"],
            pdf_url="http://example.com/pdf",
            abstract_url="http://example.com/abs",
            discovered_by="test",
        )
        paper.main_claim = "LLMs enable effective multi-agent coordination"
        paper.methodology = "Framework using Claude API"
        paper.key_results = ["85% success rate", "40% reduced overhead"]
        paper.analyzed_at = datetime.now(timezone.utc)
        db.add(paper)

    with db_session() as db:
        return db.query(Paper).filter_by(arxiv_id="2312.analyzed").first()


@pytest.fixture
def unanalyzed_paper(db_session):
    """Create an unanalyzed paper."""
    with db_session() as db:
        paper = Paper(
            arxiv_id="2312.unanalyzed",
            title="Test Paper",
            abstract="Abstract",
            authors=["Test"],
            published_date=datetime.now(timezone.utc),
            categories=["cs.AI"],
            pdf_url="http://example.com/pdf",
            abstract_url="http://example.com/abs",
            discovered_by="test",
        )
        db.add(paper)

    with db_session() as db:
        return db.query(Paper).filter_by(arxiv_id="2312.unanalyzed").first()


@pytest.fixture
def mock_claude_explanation():
    """Mock Claude API response for explanation."""
    return {
        "eli5_summary": "Robots talking using ChatGPT to work together!",
        "key_insight": "Natural language is effective for AI coordination",
        "learning_questions": ["How does this compare to protocols?"],
        "prerequisites": ["Multi-agent systems basics"],
        "related_concepts": ["Emergent behaviors"],
    }


class TestExplainerAgent:
    """Test ExplainerAgent class with proper database isolation."""

    def test_init(self):
        """Test agent initialization."""
        explainer = ExplainerAgent()
        assert explainer.client is not None
        assert explainer.model is not None

    def test_build_explanation_prompt_structure(self, analyzed_paper):
        """Test that explanation prompt contains required fields."""
        explainer = ExplainerAgent()
        prompt = explainer.build_explanation_prompt(analyzed_paper)

        assert analyzed_paper.title in prompt
        assert analyzed_paper.main_claim in prompt
        assert "eli5_summary" in prompt
        assert "key_insight" in prompt

    def test_build_explanation_prompt_requires_analysis(self, unanalyzed_paper):
        """Test that prompt building fails for unanalyzed papers."""
        explainer = ExplainerAgent()

        with pytest.raises(ValueError) as exc_info:
            explainer.build_explanation_prompt(unanalyzed_paper)

        assert "analyzed" in str(exc_info.value).lower()

    @patch("src.agents.explainer.get_claude_client")
    def test_explain_paper_success(self, mock_get_client, analyzed_paper, mock_claude_explanation):
        """Test successful paper explanation."""
        mock_client = Mock()
        mock_client.chat_json.return_value = mock_claude_explanation
        mock_get_client.return_value = mock_client

        explainer = ExplainerAgent()
        explainer.client = mock_client

        explanation = explainer.explain_paper(analyzed_paper)

        assert explanation["eli5_summary"] == mock_claude_explanation["eli5_summary"]
        assert explanation["key_insight"] == mock_claude_explanation["key_insight"]

    def test_explain_paper_requires_analyzed_paper(self, unanalyzed_paper):
        """Test that explaining fails for unanalyzed papers."""
        explainer = ExplainerAgent()

        with pytest.raises(ValueError) as exc_info:
            explainer.explain_paper(unanalyzed_paper)

        assert "analyzed" in str(exc_info.value).lower()

    @patch("src.agents.explainer.get_claude_client")
    def test_explain_paper_missing_fields(self, mock_get_client, analyzed_paper):
        """Test that missing explanation fields are filled with defaults."""
        incomplete_explanation = {"eli5_summary": "Some summary"}
        mock_client = Mock()
        mock_client.chat_json.return_value = incomplete_explanation
        mock_get_client.return_value = mock_client

        explainer = ExplainerAgent()
        explainer.client = mock_client

        explanation = explainer.explain_paper(analyzed_paper)

        assert explanation["eli5_summary"] == "Some summary"
        assert explanation["learning_questions"] == []

    def test_save_explanation(self, db_session, mock_claude_explanation):
        """Test saving explanation to database with proper session mocking."""
        # Create analyzed paper
        with db_session() as db:
            paper = Paper(
                arxiv_id="2312.save.expl",
                title="Test",
                abstract="Abstract",
                authors=["Test"],
                published_date=datetime.now(timezone.utc),
                categories=["cs.AI"],
                pdf_url="http://example.com/pdf",
                abstract_url="http://example.com/abs",
                discovered_by="test",
            )
            paper.main_claim = "Test claim"
            paper.analyzed_at = datetime.now(timezone.utc)
            db.add(paper)

        # Mock get_db_session to return test session
        with patch("src.agents.explainer.get_db_session", side_effect=lambda: db_session()):
            explainer = ExplainerAgent()
            explainer.save_explanation("2312.save.expl", mock_claude_explanation)

        # Verify saved
        with db_session() as db:
            paper = db.query(Paper).filter_by(arxiv_id="2312.save.expl").first()
            assert paper.eli5_summary == mock_claude_explanation["eli5_summary"]
            assert paper.explained_at is not None

    @patch.object(ExplainerAgent, "explain_paper")
    @patch.object(ExplainerAgent, "save_explanation")
    def test_explain_and_save_skips_unanalyzed(self, mock_save, mock_explain, db_session):
        """Test that explain_and_save skips unanalyzed papers."""
        with db_session() as db:
            analyzed = Paper(
                arxiv_id="2312.analyzed.1",
                title="Analyzed",
                abstract="Abstract",
                authors=["Test"],
                published_date=datetime.now(timezone.utc),
                categories=["cs.AI"],
                pdf_url="http://example.com/pdf1",
                abstract_url="http://example.com/abs1",
                discovered_by="test",
            )
            analyzed.main_claim = "Claim"
            analyzed.analyzed_at = datetime.now(timezone.utc)

            unanalyzed = Paper(
                arxiv_id="2312.unanalyzed.1",
                title="Unanalyzed",
                abstract="Abstract",
                authors=["Test"],
                published_date=datetime.now(timezone.utc),
                categories=["cs.AI"],
                pdf_url="http://example.com/pdf2",
                abstract_url="http://example.com/abs2",
                discovered_by="test",
            )

            db.add(analyzed)
            db.add(unanalyzed)

        with db_session() as db:
            papers = db.query(Paper).all()

        mock_explain.return_value = {"eli5_summary": "Test"}

        explainer = ExplainerAgent()
        count = explainer.explain_and_save(papers)

        assert count == 1

    @patch.object(ExplainerAgent, "explain_paper")
    @patch("src.agents.explainer.get_db_session")
    def test_explain_and_save_continues_on_error(self, mock_get_session, mock_explain, db_session):
        """Test that processing continues even if some papers fail."""
        mock_get_session.side_effect = lambda: db_session()

        for i in range(3):
            with db_session() as db:
                paper = Paper(
                    arxiv_id=f"2312.expl.error.{i}",
                    title=f"Paper {i}",
                    abstract="Abstract",
                    authors=["Test"],
                    published_date=datetime.now(timezone.utc),
                    categories=["cs.AI"],
                    pdf_url=f"http://example.com/pdf{i}",
                    abstract_url=f"http://example.com/abs{i}",
                    discovered_by="test",
                )
                paper.main_claim = "Claim"
                paper.analyzed_at = datetime.now(timezone.utc)
                db.add(paper)

        with db_session() as db:
            papers = db.query(Paper).filter(Paper.arxiv_id.like("2312.expl.error%")).all()

        def side_effect(paper):
            if "error.1" in paper.arxiv_id:
                raise Exception("Explanation failed")
            return {"eli5_summary": "Success"}

        mock_explain.side_effect = side_effect

        explainer = ExplainerAgent()
        count = explainer.explain_and_save(papers)

        assert count == 2


class TestExplainPapersBatch:
    """Test standalone explain_papers_batch function."""

    @patch("src.agents.explainer.get_db_session")
    @patch.object(ExplainerAgent, "explain_and_save")
    def test_explain_papers_batch(self, mock_explain_and_save, mock_get_session, db_session):
        """Test explain_papers_batch function with proper session mocking."""
        mock_get_session.side_effect = lambda: db_session()

        papers = []
        for i in range(2):
            with db_session() as db:
                paper = Paper(
                    arxiv_id=f"2312.batch.expl.{i}",
                    title=f"Paper {i}",
                    abstract="Abstract",
                    authors=["Test"],
                    published_date=datetime.now(timezone.utc),
                    categories=["cs.AI"],
                    pdf_url=f"http://example.com/pdf{i}",
                    abstract_url=f"http://example.com/abs{i}",
                    discovered_by="test",
                )
                paper.main_claim = "Claim"
                paper.analyzed_at = datetime.now(timezone.utc)
                db.add(paper)

            with db_session() as db:
                papers.append(db.query(Paper).filter_by(arxiv_id=f"2312.batch.expl.{i}").first())

        mock_explain_and_save.return_value = 2

        result = explain_papers_batch(papers)

        assert isinstance(result, list)
        mock_explain_and_save.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
