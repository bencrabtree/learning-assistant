"""
End-to-End Integration Tests

These tests verify that all components work together correctly:
- Full discovery → reader → explainer workflow
- Database persistence across agents
- Error recovery and graceful degradation
- Real LangGraph execution (with mocked external APIs)
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from src.graph import run_full_pipeline, run_analysis_pipeline, run_discovery_only_pipeline
from src.models.paper import Paper
from src.database import get_db_session, init_db


@pytest.fixture(scope="function")
def integration_db():
    """Create a clean database for integration tests."""
    init_db()
    yield
    # Cleanup would go here if needed


@pytest.fixture
def mock_arxiv_results():
    """Create mock arXiv search results with serializable authors."""
    # Create a simple class for mock authors that's JSON serializable
    class MockAuthor:
        def __init__(self, name):
            self.name = name

    results = []
    for i in range(3):
        result = Mock()
        result.entry_id = f"http://arxiv.org/abs/2312.1234{i}v1"
        result.title = f"Test Paper {i}: Multi-Agent Systems"
        result.summary = f"This paper {i} presents a novel approach to coordination."
        result.authors = [MockAuthor(f"Author {i}A"), MockAuthor(f"Author {i}B")]
        result.published = datetime.now(timezone.utc)
        result.categories = ["cs.AI", "cs.LG"]
        result.pdf_url = f"http://arxiv.org/pdf/2312.1234{i}v1"
        results.append(result)
    return results


class TestFullWorkflowIntegration:
    """Test complete end-to-end workflow."""

    @patch("src.agents.discovery.arxiv.Search")
    @patch("src.services.claude_client.ClaudeClient.chat_json")
    def test_full_pipeline_end_to_end(
        self, mock_claude, mock_arxiv_search, integration_db, mock_arxiv_results
    ):
        """
        Test complete pipeline from discovery to explanation.

        This test verifies:
        1. Papers are discovered from arXiv
        2. Papers are saved to database
        3. Papers are analyzed by reader agent
        4. Papers are explained by explainer agent
        5. All data persists correctly
        """
        # Setup mocks
        mock_search_instance = Mock()
        mock_search_instance.results.return_value = mock_arxiv_results[:2]  # Limit to 2
        mock_arxiv_search.return_value = mock_search_instance

        # Mock Claude responses
        def claude_side_effect(prompt, **kwargs):
            # Return analysis for reader
            if "main_claim" in prompt:
                return {
                    "main_claim": "Test claim",
                    "methodology": "Test methodology",
                    "key_results": ["Result 1", "Result 2"],
                    "novel_contributions": "Novel contribution",
                    "limitations": "Limitations",
                    "concepts": ["concept1", "concept2"],
                }
            # Return explanation for explainer
            else:
                return {
                    "eli5_summary": "Simple explanation",
                    "key_insight": "Key insight",
                    "learning_questions": ["Q1", "Q2"],
                    "prerequisites": ["P1", "P2"],
                    "related_concepts": ["C1", "C2"],
                }

        mock_claude.side_effect = claude_side_effect

        # Run full pipeline
        result = run_full_pipeline(days_back=1, max_papers=2)

        # Verify workflow completed
        assert result["stats"]["discovered_count"] == 2
        assert result["stats"]["analyzed_count"] == 2
        assert result["stats"]["explained_count"] == 2
        assert len(result["errors"]) == 0

        # Verify papers are in database with all fields populated
        with get_db_session() as db:
            papers = db.query(Paper).all()
            assert len(papers) == 2

            for paper in papers:
                # Discovery fields
                assert paper.title is not None
                assert paper.abstract is not None
                assert paper.discovered_at is not None

                # Analysis fields
                assert paper.main_claim == "Test claim"
                assert paper.methodology == "Test methodology"
                assert len(paper.key_results) == 2
                assert paper.analyzed_at is not None

                # Explanation fields
                assert paper.eli5_summary == "Simple explanation"
                assert paper.key_insight == "Key insight"
                assert len(paper.learning_questions) == 2
                assert paper.explained_at is not None

    @patch("src.agents.discovery.arxiv.Search")
    def test_discovery_only_workflow(
        self, mock_arxiv_search, integration_db, mock_arxiv_results
    ):
        """
        Test discovery-only workflow.

        Verifies that papers can be discovered and saved
        without running analysis.
        """
        # Setup mock
        mock_search_instance = Mock()
        mock_search_instance.results.return_value = mock_arxiv_results[:3]
        mock_arxiv_search.return_value = mock_search_instance

        # Run discovery only
        result = run_discovery_only_pipeline(days_back=1)

        # Verify discovery completed
        assert result["stats"]["discovered_count"] == 3

        # Verify papers in database (not analyzed)
        with get_db_session() as db:
            papers = db.query(Paper).all()
            assert len(papers) == 3

            for paper in papers:
                assert paper.title is not None
                assert paper.discovered_at is not None
                # Should NOT be analyzed
                assert paper.analyzed_at is None
                assert paper.main_claim is None

    @patch("src.agents.discovery.arxiv.Search")
    @patch("src.services.claude_client.ClaudeClient.chat_json")
    def test_analysis_pipeline_on_existing_papers(
        self, mock_claude, mock_arxiv_search, integration_db, mock_arxiv_results
    ):
        """
        Test two-step workflow: discover first, then analyze.

        This tests that papers can be discovered in one session
        and analyzed in a separate session.
        """
        # Step 1: Discover papers
        mock_search_instance = Mock()
        mock_search_instance.results.return_value = mock_arxiv_results[:2]
        mock_arxiv_search.return_value = mock_search_instance

        discovery_result = run_discovery_only_pipeline(days_back=1)
        assert discovery_result["stats"]["discovered_count"] == 2

        # Step 2: Analyze the discovered papers
        def claude_side_effect(prompt, **kwargs):
            if "main_claim" in prompt:
                return {
                    "main_claim": "Analyzed claim",
                    "methodology": "Method",
                    "key_results": ["R1"],
                    "novel_contributions": "Novel",
                    "limitations": "Limits",
                    "concepts": ["C1"],
                }
            else:
                return {
                    "eli5_summary": "Summary",
                    "key_insight": "Insight",
                    "learning_questions": ["Q1"],
                    "prerequisites": ["P1"],
                    "related_concepts": ["RC1"],
                }

        mock_claude.side_effect = claude_side_effect

        analysis_result = run_analysis_pipeline()

        # Verify analysis completed
        assert analysis_result["stats"]["discovered_count"] == 2
        assert analysis_result["stats"]["analyzed_count"] == 2
        assert analysis_result["stats"]["explained_count"] == 2

        # Verify papers are now analyzed
        with get_db_session() as db:
            papers = db.query(Paper).all()
            assert len(papers) == 2

            for paper in papers:
                assert paper.main_claim == "Analyzed claim"
                assert paper.eli5_summary == "Summary"


class TestErrorRecovery:
    """Test error handling and recovery in integration scenarios."""

    @patch("src.agents.discovery.arxiv.Search")
    @patch("src.services.claude_client.ClaudeClient.chat_json")
    def test_pipeline_continues_after_partial_failures(
        self, mock_claude, mock_arxiv_search, integration_db, mock_arxiv_results
    ):
        """
        Test that pipeline continues processing even when some papers fail.

        If paper 2 fails analysis, papers 1 and 3 should still be processed.
        """
        # Setup discovery
        mock_search_instance = Mock()
        mock_search_instance.results.return_value = mock_arxiv_results
        mock_arxiv_search.return_value = mock_search_instance

        # Setup Claude to fail on second paper
        call_count = [0]

        def claude_side_effect(prompt, **kwargs):
            if "main_claim" in prompt:
                call_count[0] += 1
                if call_count[0] == 2:  # Fail on second paper
                    raise Exception("Rate limit exceeded")
                return {
                    "main_claim": "Claim",
                    "methodology": "Method",
                    "key_results": ["R1"],
                    "novel_contributions": "Novel",
                    "limitations": "Limits",
                    "concepts": ["C1"],
                }
            else:
                return {
                    "eli5_summary": "Summary",
                    "key_insight": "Insight",
                    "learning_questions": ["Q1"],
                    "prerequisites": ["P1"],
                    "related_concepts": ["RC1"],
                }

        mock_claude.side_effect = claude_side_effect

        # Run pipeline
        result = run_full_pipeline(days_back=1, max_papers=3)

        # Should have discovered all 3
        assert result["stats"]["discovered_count"] == 3

        # Should have analyzed 2 (one failed)
        assert result["stats"]["analyzed_count"] == 2

        # Verify database state
        with get_db_session() as db:
            analyzed_papers = (
                db.query(Paper).filter(Paper.analyzed_at.isnot(None)).all()
            )
            unanalyzed_papers = db.query(Paper).filter(Paper.analyzed_at.is_(None)).all()

            assert len(analyzed_papers) == 2
            assert len(unanalyzed_papers) == 1

    @patch("src.agents.discovery.arxiv.Search")
    def test_pipeline_handles_discovery_failure_gracefully(
        self, mock_arxiv_search, integration_db
    ):
        """
        Test that pipeline handles discovery failures gracefully.

        If discovery fails completely, subsequent stages should handle empty input.
        """
        # Setup discovery to fail
        mock_arxiv_search.side_effect = Exception("Network timeout")

        # Run pipeline
        result = run_full_pipeline(days_back=1)

        # Should complete but with errors
        assert len(result["errors"]) > 0
        assert result["stats"].get("discovered_count", 0) == 0
        assert result["stats"].get("analyzed_count", 0) == 0
        assert result["stats"].get("explained_count", 0) == 0

        # Database should be empty
        with get_db_session() as db:
            papers = db.query(Paper).all()
            assert len(papers) == 0


class TestDatabaseConsistency:
    """Test database consistency across workflow stages."""

    @patch("src.agents.discovery.arxiv.Search")
    @patch("src.services.claude_client.ClaudeClient.chat_json")
    def test_duplicate_papers_not_created(
        self, mock_claude, mock_arxiv_search, integration_db, mock_arxiv_results
    ):
        """
        Test that running discovery twice doesn't create duplicates.
        """
        # Setup mocks
        mock_search_instance = Mock()
        mock_search_instance.results.return_value = mock_arxiv_results[:2]
        mock_arxiv_search.return_value = mock_search_instance

        # Run discovery twice
        result1 = run_discovery_only_pipeline(days_back=1)
        result2 = run_discovery_only_pipeline(days_back=1)

        # First run discovers 2, second run discovers 0 (duplicates)
        assert result1["stats"]["discovered_count"] == 2
        assert result2["stats"]["discovered_count"] == 2  # Found but not saved

        # Database should have exactly 2 papers
        with get_db_session() as db:
            papers = db.query(Paper).all()
            assert len(papers) == 2

    @patch("src.agents.discovery.arxiv.Search")
    @patch("src.services.claude_client.ClaudeClient.chat_json")
    def test_analysis_updates_existing_papers(
        self, mock_claude, mock_arxiv_search, integration_db, mock_arxiv_results
    ):
        """
        Test that analysis updates existing papers rather than creating new ones.
        """
        # Discover papers
        mock_search_instance = Mock()
        mock_search_instance.results.return_value = mock_arxiv_results[:1]
        mock_arxiv_search.return_value = mock_search_instance

        discovery_result = run_discovery_only_pipeline(days_back=1)
        paper_count_after_discovery = discovery_result["stats"]["discovered_count"]

        # Setup Claude mock
        mock_claude.return_value = {
            "main_claim": "Updated claim",
            "methodology": "Method",
            "key_results": ["R1"],
            "novel_contributions": "Novel",
            "limitations": "Limits",
            "concepts": ["C1"],
        }

        # Analyze papers
        analysis_result = run_analysis_pipeline()

        # Should still have same number of papers
        with get_db_session() as db:
            papers = db.query(Paper).all()
            assert len(papers) == paper_count_after_discovery

            # Paper should be updated
            paper = papers[0]
            assert paper.main_claim == "Updated claim"


class TestStatePropagation:
    """Test that state propagates correctly through workflow."""

    @patch("src.agents.discovery.arxiv.Search")
    @patch("src.services.claude_client.ClaudeClient.chat_json")
    def test_max_papers_limit_enforced(
        self, mock_claude, mock_arxiv_search, integration_db, mock_arxiv_results
    ):
        """
        Test that max_papers limit is enforced throughout pipeline.
        """
        # Setup to return 5 papers but limit to 2
        mock_search_instance = Mock()
        mock_search_instance.results.return_value = mock_arxiv_results + mock_arxiv_results[:2]  # 5 total
        mock_arxiv_search.return_value = mock_search_instance

        mock_claude.return_value = {
            "main_claim": "Claim",
            "methodology": "Method",
            "key_results": ["R1"],
            "novel_contributions": "Novel",
            "limitations": "Limits",
            "concepts": ["C1"],
        }

        # Run with max_papers=2
        result = run_full_pipeline(days_back=1, max_papers=2)

        # Should process exactly 2 papers
        assert result["stats"]["discovered_count"] == 2
        assert result["stats"]["analyzed_count"] == 2

        with get_db_session() as db:
            papers = db.query(Paper).all()
            assert len(papers) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
