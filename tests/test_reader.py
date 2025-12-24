"""
Comprehensive Unit Tests for Reader Agent

Tests cover:
- ReaderAgent class initialization
- Prompt building
- Paper analysis with Claude
- Analysis saving to database
- Batch processing
- Error handling
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from src.agents.reader import ReaderAgent, analyze_papers_batch
from src.models.paper import Paper
from src.database import get_db_session


@pytest.fixture
def sample_paper(db_session):
    """Create a sample paper in the database."""
    with db_session() as db:
        paper = Paper(
            arxiv_id="2312.12345",
            title="Multi-Agent Coordination with LLMs",
            abstract="This paper presents a novel approach to multi-agent systems using large language models for coordination and communication.",
            authors=["Alice Smith", "Bob Jones", "Carol Lee"],
            published_date=datetime(2024, 12, 20, tzinfo=timezone.utc),
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
        "main_claim": "LLMs can effectively coordinate multi-agent systems through natural language communication",
        "methodology": "Proposed framework using Claude API for agent communication with experiments on coordination tasks",
        "key_results": [
            "Achieved 85% success rate on collaborative tasks",
            "Reduced coordination overhead by 40%",
            "Demonstrated emergent behaviors in complex scenarios",
        ],
        "novel_contributions": "First framework to use LLMs for real-time multi-agent coordination with formal guarantees",
        "limitations": "Evaluated only in simulated environments; computational cost is high",
        "concepts": [
            "multi-agent systems",
            "large language models",
            "coordination protocols",
            "emergent behavior",
            "natural language communication",
        ],
    }


class TestReaderAgent:
    """Test ReaderAgent class."""

    def test_init(self):
        """Test agent initialization."""
        reader = ReaderAgent()
        assert reader.client is not None
        assert reader.model is not None

    def test_build_analysis_prompt_structure(self, sample_paper):
        """Test that analysis prompt contains required fields."""
        reader = ReaderAgent()
        prompt = reader.build_analysis_prompt(sample_paper)

        # Check prompt contains paper details
        assert sample_paper.title in prompt
        assert "Alice Smith" in prompt
        assert "2024-12-20" in prompt

        # Check prompt requests JSON fields
        assert "main_claim" in prompt
        assert "methodology" in prompt
        assert "key_results" in prompt
        assert "novel_contributions" in prompt
        assert "limitations" in prompt
        assert "concepts" in prompt

    def test_build_analysis_prompt_truncates_long_author_list(self, db_session):
        """Test that long author lists are truncated with 'et al.'."""
        with db_session() as db:
            paper = Paper(
                arxiv_id="2312.99999",
                title="Test Paper",
                abstract="Abstract",
                authors=["A", "B", "C", "D", "E", "F"],  # 6 authors
                published_date=datetime.now(timezone.utc),
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

            # Should show first 3 + et al.
            assert "A, B, C et al." in prompt

    @patch("src.agents.reader.get_claude_client")
    def test_analyze_paper_success(
        self, mock_get_client, sample_paper, mock_claude_analysis
    ):
        """Test successful paper analysis."""
        # Setup mock
        mock_client = Mock()
        mock_client.chat_json.return_value = mock_claude_analysis
        mock_get_client.return_value = mock_client

        reader = ReaderAgent()
        reader.client = mock_client

        analysis = reader.analyze_paper(sample_paper)

        # Verify analysis
        assert analysis["main_claim"] == mock_claude_analysis["main_claim"]
        assert len(analysis["key_results"]) == 3
        assert len(analysis["concepts"]) == 5

        # Verify Claude was called with correct parameters
        mock_client.chat_json.assert_called_once()
        call_kwargs = mock_client.chat_json.call_args[1]
        assert call_kwargs["temperature"] == 0.3  # Low temperature for consistency

    @patch("src.agents.reader.get_claude_client")
    def test_analyze_paper_missing_fields(self, mock_get_client, sample_paper):
        """Test that missing fields are filled with defaults."""
        # Setup mock with incomplete response
        incomplete_analysis = {
            "main_claim": "Some claim",
            # Missing other fields
        }
        mock_client = Mock()
        mock_client.chat_json.return_value = incomplete_analysis
        mock_get_client.return_value = mock_client

        reader = ReaderAgent()
        reader.client = mock_client

        analysis = reader.analyze_paper(sample_paper)

        # Check defaults were added
        assert analysis["main_claim"] == "Some claim"
        assert analysis["key_results"] == []
        assert analysis["concepts"] == []
        assert analysis["methodology"] == "Not available"

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
        """Test saving analysis to database."""
        # Create paper
        with db_session() as db:
            paper = Paper(
                arxiv_id="2312.save.test",
                title="Test",
                abstract="Abstract",
                authors=["Test"],
                published_date=datetime.now(timezone.utc),
                categories=["cs.AI"],
                pdf_url="http://example.com/pdf",
                abstract_url="http://example.com/abs",
                discovered_by="test",
            )
            db.add(paper)

        reader = ReaderAgent()
        reader.save_analysis("2312.save.test", mock_claude_analysis)

        # Verify saved
        with db_session() as db:
            paper = db.query(Paper).filter_by(arxiv_id="2312.save.test").first()
            assert paper.main_claim == mock_claude_analysis["main_claim"]
            assert paper.methodology == mock_claude_analysis["methodology"]
            assert paper.key_results == mock_claude_analysis["key_results"]
            assert paper.concepts == mock_claude_analysis["concepts"]
            assert paper.analyzed_at is not None

    def test_save_analysis_paper_not_found(self, mock_claude_analysis):
        """Test error when trying to save analysis for non-existent paper."""
        reader = ReaderAgent()

        with pytest.raises(ValueError) as exc_info:
            reader.save_analysis("nonexistent.123", mock_claude_analysis)

        assert "not found" in str(exc_info.value).lower()

    @patch.object(ReaderAgent, "analyze_paper")
    @patch.object(ReaderAgent, "save_analysis")
    def test_analyze_and_save(self, mock_save, mock_analyze, db_session):
        """Test analyze_and_save processes all papers."""
        # Create test papers
        papers = []
        for i in range(3):
            with db_session() as db:
                paper = Paper(
                    arxiv_id=f"2312.batch.{i}",
                    title=f"Paper {i}",
                    abstract="Abstract",
                    authors=["Test"],
                    published_date=datetime.now(timezone.utc),
                    categories=["cs.AI"],
                    pdf_url=f"http://example.com/pdf{i}",
                    abstract_url=f"http://example.com/abs{i}",
                    discovered_by="test",
                )
                db.add(paper)

            with db_session() as db:
                papers.append(
                    db.query(Paper).filter_by(arxiv_id=f"2312.batch.{i}").first()
                )

        mock_analyze.return_value = {"main_claim": "Test"}

        reader = ReaderAgent()
        count = reader.analyze_and_save(papers)

        assert count == 3
        assert mock_analyze.call_count == 3
        assert mock_save.call_count == 3

    @patch.object(ReaderAgent, "analyze_paper")
    def test_analyze_and_save_continues_on_error(self, mock_analyze, db_session):
        """Test that analyze_and_save continues processing even if some papers fail."""
        # Create test papers
        papers = []
        for i in range(3):
            with db_session() as db:
                paper = Paper(
                    arxiv_id=f"2312.error.{i}",
                    title=f"Paper {i}",
                    abstract="Abstract",
                    authors=["Test"],
                    published_date=datetime.now(timezone.utc),
                    categories=["cs.AI"],
                    pdf_url=f"http://example.com/pdf{i}",
                    abstract_url=f"http://example.com/abs{i}",
                    discovered_by="test",
                )
                db.add(paper)

            with db_session() as db:
                papers.append(
                    db.query(Paper).filter_by(arxiv_id=f"2312.error.{i}").first()
                )

        # Make second paper fail
        def side_effect(paper):
            if "error.1" in paper.arxiv_id:
                raise Exception("Analysis failed")
            return {"main_claim": "Success"}

        mock_analyze.side_effect = side_effect

        reader = ReaderAgent()
        count = reader.analyze_and_save(papers)

        # Should have processed 2 out of 3 (skipped the failed one)
        assert count == 2


class TestAnalyzePapersBatch:
    """Test the standalone analyze_papers_batch function."""

    @patch.object(ReaderAgent, "analyze_and_save")
    def test_analyze_papers_batch(self, mock_analyze_and_save, db_session):
        """Test analyze_papers_batch function."""
        # Create papers
        papers = []
        for i in range(2):
            with db_session() as db:
                paper = Paper(
                    arxiv_id=f"2312.function.{i}",
                    title=f"Paper {i}",
                    abstract="Abstract",
                    authors=["Test"],
                    published_date=datetime.now(timezone.utc),
                    categories=["cs.AI"],
                    pdf_url=f"http://example.com/pdf{i}",
                    abstract_url=f"http://example.com/abs{i}",
                    discovered_by="test",
                )
                db.add(paper)

            with db_session() as db:
                papers.append(
                    db.query(Paper).filter_by(arxiv_id=f"2312.function.{i}").first()
                )

        mock_analyze_and_save.return_value = 2

        # Call function
        with patch("src.agents.reader.get_db_session", return_value=db_session):
            result = analyze_papers_batch(papers)

        # Should reload papers from database
        assert isinstance(result, list)
        mock_analyze_and_save.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
