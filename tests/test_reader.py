"""
Comprehensive Unit Tests for Reader Agent - FINAL VERSION

Properly mocked with working database session isolation.
"""

from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest

from src.agents.reader import ReaderAgent, analyze_papers_batch
from src.models.paper import Paper


@pytest.fixture
def sample_paper(db_session):
    """Create a sample paper in the test database."""
    with db_session() as db:
        paper = Paper(
            arxiv_id="2312.12345",
            title="Multi-Agent Coordination with LLMs",
            abstract="This paper presents a novel approach to multi-agent systems.",
            authors=["Alice Smith", "Bob Jones", "Carol Lee"],
            published_date=datetime(2024, 12, 20, tzinfo=UTC),
            categories=["cs.AI", "cs.LG"],
            pdf_url="http://arxiv.org/pdf/2312.12345",
            abstract_url="http://arxiv.org/abs/2312.12345",
            discovered_by="arxiv",
        )
        db.add(paper)

    with db_session() as db:
        return db.query(Paper).filter_by(arxiv_id="2312.12345").first()


@pytest.fixture
def mock_claude_analysis():
    """Mock Claude API response for analysis."""
    return {
        "main_claim": "LLMs can coordinate multi-agent systems effectively",
        "methodology": "Framework using Claude API for communication",
        "key_results": ["85% success rate", "40% reduced overhead"],
        "novel_contributions": "First LLM-based coordination framework",
        "limitations": "Only simulated environments",
        "concepts": ["multi-agent", "LLMs", "coordination"],
    }


class TestReaderAgent:
    """Test ReaderAgent class with proper database isolation."""

    def test_init(self):
        """Test agent initialization."""
        reader = ReaderAgent()
        assert reader.client is not None
        assert reader.model is not None

    def test_build_analysis_prompt_structure(self, sample_paper):
        """Test that analysis prompt contains required fields."""
        reader = ReaderAgent()
        prompt = reader.build_analysis_prompt(sample_paper)

        assert sample_paper.title in prompt
        assert "Alice Smith" in prompt
        assert "main_claim" in prompt

    def test_build_analysis_prompt_truncates_long_author_list(self, db_session):
        """Test that long author lists are truncated with 'et al.'."""
        with db_session() as db:
            paper = Paper(
                arxiv_id="2312.99999",
                title="Test Paper",
                abstract="Abstract",
                authors=["A", "B", "C", "D", "E", "F"],
                published_date=datetime.now(UTC),
                categories=["cs.AI"],
                pdf_url="http://example.com/pdf",
                abstract_url="http://example.com/abs",
                discovered_by="test",
            )
            db.add(paper)

        with db_session() as db:
            paper = db.query(Paper).filter_by(arxiv_id="2312.99999").first()
            reader = ReaderAgent()
            prompt = reader.build_analysis_prompt(paper)
            assert "A, B, C et al." in prompt

    @patch("src.agents.reader.get_claude_client")
    def test_analyze_paper_success(self, mock_get_client, sample_paper, mock_claude_analysis):
        """Test successful paper analysis."""
        mock_client = Mock()
        mock_client.chat_json.return_value = mock_claude_analysis
        mock_get_client.return_value = mock_client

        reader = ReaderAgent()
        reader.client = mock_client

        analysis = reader.analyze_paper(sample_paper)

        assert analysis["main_claim"] == mock_claude_analysis["main_claim"]

    @patch("src.agents.reader.get_claude_client")
    def test_analyze_paper_missing_fields(self, mock_get_client, sample_paper):
        """Test that missing fields are filled with defaults."""
        incomplete_analysis = {"main_claim": "Some claim"}
        mock_client = Mock()
        mock_client.chat_json.return_value = incomplete_analysis
        mock_get_client.return_value = mock_client

        reader = ReaderAgent()
        reader.client = mock_client

        analysis = reader.analyze_paper(sample_paper)

        assert analysis["main_claim"] == "Some claim"
        assert analysis["key_results"] == []

    @patch("src.agents.reader.get_claude_client")
    def test_analyze_paper_api_error(self, mock_get_client, sample_paper):
        """Test handling of Claude API errors."""
        mock_client = Mock()
        mock_client.chat_json.side_effect = Exception("API rate limit exceeded")
        mock_get_client.return_value = mock_client

        reader = ReaderAgent()
        reader.client = mock_client

        with pytest.raises(Exception) as exc_info:
            reader.analyze_paper(sample_paper)

        assert "API rate limit exceeded" in str(exc_info.value)

    def test_save_analysis(self, db_session, mock_claude_analysis):
        """Test saving analysis to database with proper session mocking."""
        # Create paper in test database
        with db_session() as db:
            paper = Paper(
                arxiv_id="2312.save.test",
                title="Test",
                abstract="Abstract",
                authors=["Test"],
                published_date=datetime.now(UTC),
                categories=["cs.AI"],
                pdf_url="http://example.com/pdf",
                abstract_url="http://example.com/abs",
                discovered_by="test",
            )
            db.add(paper)

        # Patch get_db_session to return a function that calls db_session
        with patch("src.agents.reader.get_db_session", side_effect=lambda: db_session()):
            reader = ReaderAgent()
            reader.save_analysis("2312.save.test", mock_claude_analysis)

        # Verify saved
        with db_session() as db:
            paper = db.query(Paper).filter_by(arxiv_id="2312.save.test").first()
            assert paper.main_claim == mock_claude_analysis["main_claim"]
            assert paper.analyzed_at is not None

    def test_save_analysis_paper_not_found(self, db_session, mock_claude_analysis):
        """Test error when paper doesn't exist."""
        with patch("src.agents.reader.get_db_session", side_effect=lambda: db_session()):
            reader = ReaderAgent()
            with pytest.raises(ValueError) as exc_info:
                reader.save_analysis("nonexistent.123", mock_claude_analysis)
            assert "not found" in str(exc_info.value).lower()

    @patch.object(ReaderAgent, "analyze_paper")
    @patch.object(ReaderAgent, "save_analysis")
    def test_analyze_and_save(self, mock_save, mock_analyze, db_session):
        """Test analyze_and_save processes all papers."""
        papers = []
        for i in range(3):
            with db_session() as db:
                paper = Paper(
                    arxiv_id=f"2312.batch.{i}",
                    title=f"Paper {i}",
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
                papers.append(db.query(Paper).filter_by(arxiv_id=f"2312.batch.{i}").first())

        mock_analyze.return_value = {"main_claim": "Test"}

        reader = ReaderAgent()
        count = reader.analyze_and_save(papers)

        assert count == 3

    @patch.object(ReaderAgent, "analyze_paper")
    def test_analyze_and_save_continues_on_error(self, mock_analyze, db_session):
        """Test that processing continues even if some papers fail."""
        papers = []
        for i in range(3):
            with db_session() as db:
                paper = Paper(
                    arxiv_id=f"2312.error.{i}",
                    title=f"Paper {i}",
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
                papers.append(db.query(Paper).filter_by(arxiv_id=f"2312.error.{i}").first())

        def side_effect(paper):
            if "error.1" in paper.arxiv_id:
                raise Exception("Analysis failed")
            return {"main_claim": "Success"}

        mock_analyze.side_effect = side_effect

        # Mock get_db_session for save_analysis calls
        with patch("src.agents.reader.get_db_session", side_effect=lambda: db_session()):
            reader = ReaderAgent()
            count = reader.analyze_and_save(papers)

        assert count == 2


class TestAnalyzePapersBatch:
    """Test standalone analyze_papers_batch function."""

    @patch.object(ReaderAgent, "analyze_and_save")
    def test_analyze_papers_batch(self, mock_analyze_and_save, db_session):
        """Test analyze_papers_batch function with proper session mocking."""
        papers = []
        for i in range(2):
            with db_session() as db:
                paper = Paper(
                    arxiv_id=f"2312.function.{i}",
                    title=f"Paper {i}",
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
                papers.append(db.query(Paper).filter_by(arxiv_id=f"2312.function.{i}").first())

        mock_analyze_and_save.return_value = 2

        with patch("src.agents.reader.get_db_session", side_effect=lambda: db_session()):
            result = analyze_papers_batch(papers)

        assert isinstance(result, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
