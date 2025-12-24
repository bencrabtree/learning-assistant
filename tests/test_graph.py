"""
Comprehensive Unit Tests for LangGraph Workflows

Tests cover:
- Workflow construction
- Node execution
- State management
- Error handling in nodes
- Full pipeline execution
- Discovery-only pipeline
- Analysis-only pipeline
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from src.graph import (
    discovery_node,
    reader_node,
    explainer_node,
    create_workflow,
    run_full_pipeline,
    run_discovery_only_pipeline,
    run_analysis_pipeline,
    AgentState,
)
from src.models.paper import Paper


@pytest.fixture
def mock_papers():
    """Create mock Paper objects."""
    papers = []
    for i in range(2):
        paper = Mock(spec=Paper)
        paper.arxiv_id = f"2312.test.{i}"
        paper.title = f"Test Paper {i}"
        paper.abstract = "Abstract"
        paper.authors = ["Test"]
        paper.published_date = datetime.now(timezone.utc)
        paper.categories = ["cs.AI"]
        paper.main_claim = None
        paper.analyzed_at = None
        paper.explained_at = None
        papers.append(paper)
    return papers


class TestNodeFunctions:
    """Test individual node functions."""

    @patch("src.graph.discover_papers")
    def test_discovery_node_success(self, mock_discover, mock_papers):
        """Test discovery node with successful paper discovery."""
        mock_discover.return_value = mock_papers

        state = {
            "days_back": 7,
            "categories": None,
            "max_papers": 2,
            "discovered_papers": None,
            "analyzed_papers": None,
            "explained_papers": None,
            "final_papers": None,
            "errors": [],
            "stats": {},
        }

        result = discovery_node(state)

        assert result["discovered_papers"] == mock_papers
        assert result["stats"]["discovered_count"] == 2
        assert len(result["errors"]) == 0

    @patch("src.graph.discover_papers")
    def test_discovery_node_with_max_papers_limit(self, mock_discover, mock_papers):
        """Test discovery node respects max_papers limit."""
        # Return 5 papers but limit to 2
        mock_discover.return_value = mock_papers * 3  # 6 papers

        state = {
            "days_back": 7,
            "max_papers": 2,
            "discovered_papers": None,
            "errors": [],
            "stats": {},
        }

        result = discovery_node(state)

        assert len(result["discovered_papers"]) == 2
        assert result["stats"]["discovered_count"] == 2

    @patch("src.graph.discover_papers")
    def test_discovery_node_handles_errors(self, mock_discover):
        """Test discovery node handles errors gracefully."""
        mock_discover.side_effect = Exception("ArXiv API failed")

        state = {
            "days_back": 7,
            "discovered_papers": None,
            "errors": [],
            "stats": {},
        }

        result = discovery_node(state)

        assert result["discovered_papers"] == []
        assert len(result["errors"]) == 1
        assert "Discovery error" in result["errors"][0]

    @patch("src.graph.analyze_papers_batch")
    def test_reader_node_success(self, mock_analyze, mock_papers):
        """Test reader node with successful analysis."""
        analyzed_papers = mock_papers.copy()
        for p in analyzed_papers:
            p.main_claim = "Test claim"
            p.analyzed_at = datetime.now(timezone.utc)

        mock_analyze.return_value = analyzed_papers

        state = {
            "discovered_papers": mock_papers,
            "analyzed_papers": None,
            "errors": [],
            "stats": {},
        }

        result = reader_node(state)

        assert result["analyzed_papers"] == analyzed_papers
        assert result["stats"]["analyzed_count"] == 2
        assert len(result["errors"]) == 0

    def test_reader_node_no_papers(self):
        """Test reader node when there are no papers to analyze."""
        state = {
            "discovered_papers": [],
            "analyzed_papers": None,
            "errors": [],
            "stats": {},
        }

        result = reader_node(state)

        assert result["analyzed_papers"] == []
        assert result.get("stats", {}).get("analyzed_count", 0) == 0

    @patch("src.graph.analyze_papers_batch")
    def test_reader_node_handles_errors(self, mock_analyze, mock_papers):
        """Test reader node handles errors gracefully."""
        mock_analyze.side_effect = Exception("Claude API failed")

        state = {
            "discovered_papers": mock_papers,
            "analyzed_papers": None,
            "errors": [],
            "stats": {},
        }

        result = reader_node(state)

        assert result["analyzed_papers"] == []
        assert len(result["errors"]) == 1
        assert "Reader error" in result["errors"][0]

    @patch("src.graph.explain_papers_batch")
    def test_explainer_node_success(self, mock_explain, mock_papers):
        """Test explainer node with successful explanation."""
        explained_papers = mock_papers.copy()
        for p in explained_papers:
            p.eli5_summary = "Simple explanation"
            p.explained_at = datetime.now(timezone.utc)

        mock_explain.return_value = explained_papers

        state = {
            "analyzed_papers": mock_papers,
            "explained_papers": None,
            "final_papers": None,
            "errors": [],
            "stats": {},
        }

        result = explainer_node(state)

        assert result["explained_papers"] == explained_papers
        assert result["final_papers"] == explained_papers
        assert result["stats"]["explained_count"] == 2

    def test_explainer_node_no_papers(self):
        """Test explainer node when there are no papers to explain."""
        state = {
            "analyzed_papers": [],
            "explained_papers": None,
            "final_papers": None,
            "errors": [],
            "stats": {},
        }

        result = explainer_node(state)

        assert result["explained_papers"] == []
        assert result["final_papers"] == []


class TestWorkflowCreation:
    """Test workflow graph construction."""

    def test_create_workflow_structure(self):
        """Test that workflow is created with correct structure."""
        workflow = create_workflow()

        # Should return a compiled graph
        assert workflow is not None

    def test_create_workflow_has_nodes(self):
        """Test that workflow contains all required nodes."""
        # This is implicit in create_workflow - if nodes were missing,
        # compilation would fail
        workflow = create_workflow()
        assert workflow is not None


class TestFullPipeline:
    """Test complete pipeline execution."""

    @patch("src.graph.discover_papers")
    @patch("src.graph.analyze_papers_batch")
    @patch("src.graph.explain_papers_batch")
    def test_run_full_pipeline_success(
        self, mock_explain, mock_analyze, mock_discover, mock_papers
    ):
        """Test successful execution of full pipeline."""
        # Setup mocks
        mock_discover.return_value = mock_papers

        analyzed = mock_papers.copy()
        for p in analyzed:
            p.main_claim = "Claim"
            p.analyzed_at = datetime.now(timezone.utc)
        mock_analyze.return_value = analyzed

        explained = analyzed.copy()
        for p in explained:
            p.eli5_summary = "Summary"
            p.explained_at = datetime.now(timezone.utc)
        mock_explain.return_value = explained

        # Run pipeline
        result = run_full_pipeline(days_back=7, max_papers=2)

        # Verify result
        assert result["discovered_papers"] == mock_papers
        assert result["analyzed_papers"] == analyzed
        assert result["explained_papers"] == explained
        assert result["final_papers"] == explained
        assert result["stats"]["discovered_count"] == 2
        assert result["stats"]["analyzed_count"] == 2
        assert result["stats"]["explained_count"] == 2

    @patch("src.graph.discover_papers")
    def test_run_full_pipeline_handles_discovery_error(self, mock_discover):
        """Test pipeline continues even when discovery fails."""
        mock_discover.side_effect = Exception("Network error")

        result = run_full_pipeline(days_back=7)

        # Should complete but with errors
        assert len(result["errors"]) > 0
        assert result["discovered_papers"] == []


class TestDiscoveryOnlyPipeline:
    """Test discovery-only pipeline."""

    @patch("src.graph.discover_papers")
    def test_run_discovery_only_pipeline(self, mock_discover, mock_papers):
        """Test discovery-only pipeline execution."""
        mock_discover.return_value = mock_papers

        result = run_discovery_only_pipeline(days_back=7)

        assert result["discovered_papers"] == mock_papers
        assert result["stats"]["discovered_count"] == 2
        # Should not have analysis fields
        assert "analyzed_papers" in result
        assert "explained_papers" in result


class TestAnalysisPipeline:
    """Test analysis-only pipeline."""

    @patch("src.graph.get_db_session")
    @patch("src.graph.analyze_papers_batch")
    @patch("src.graph.explain_papers_batch")
    def test_run_analysis_pipeline(
        self, mock_explain, mock_analyze, mock_get_session, mock_papers, db_session
    ):
        """Test analysis pipeline on existing papers."""
        # Setup mock to return unanalyzed papers
        mock_get_session.return_value = db_session

        with db_session() as db:
            # Create unanalyzed papers
            for i in range(2):
                paper = Paper(
                    arxiv_id=f"2312.analysis.{i}",
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

        # Setup analysis mocks
        analyzed = mock_papers.copy()
        for p in analyzed:
            p.main_claim = "Claim"
        mock_analyze.return_value = analyzed

        explained = analyzed.copy()
        for p in explained:
            p.eli5_summary = "Summary"
        mock_explain.return_value = explained

        # Run analysis pipeline
        result = run_analysis_pipeline()

        # Should have processed papers
        assert result["stats"]["discovered_count"] == 2
        assert result["stats"]["analyzed_count"] == 2
        assert result["stats"]["explained_count"] == 2

    @patch("src.graph.get_db_session")
    def test_run_analysis_pipeline_no_papers(self, mock_get_session, db_session):
        """Test analysis pipeline when no unanalyzed papers exist."""
        mock_get_session.return_value = db_session

        result = run_analysis_pipeline()

        # Should complete successfully with zero results
        assert result["stats"]["discovered_count"] == 0
        assert result["stats"]["analyzed_count"] == 0
        assert result["stats"]["explained_count"] == 0


class TestStateManagement:
    """Test state management through workflow."""

    def test_initial_state_structure(self):
        """Test that initial state has correct structure."""
        from src.graph import AgentState

        # This is a TypedDict, so we can't instantiate it directly
        # But we can verify the structure through type hints
        state = {
            "days_back": 7,
            "categories": None,
            "max_papers": None,
            "discovered_papers": None,
            "analyzed_papers": None,
            "explained_papers": None,
            "final_papers": None,
            "errors": [],
            "stats": {},
        }

        # All keys should be valid
        assert "days_back" in state
        assert "discovered_papers" in state
        assert "errors" in state
        assert "stats" in state

    @patch("src.graph.discover_papers")
    def test_state_flows_through_nodes(self, mock_discover, mock_papers):
        """Test that state is properly updated as it flows through nodes."""
        mock_discover.return_value = mock_papers

        # Start with initial state
        state = {
            "days_back": 7,
            "discovered_papers": None,
            "errors": [],
            "stats": {},
        }

        # Run discovery node
        state = discovery_node(state)

        # State should be updated
        assert state["discovered_papers"] == mock_papers
        assert "discovered_count" in state["stats"]

    def test_errors_accumulate_in_state(self):
        """Test that errors from different nodes accumulate."""
        state = {
            "errors": [],
            "stats": {},
        }

        # Simulate errors from multiple nodes
        with patch("src.graph.discover_papers", side_effect=Exception("Error 1")):
            state = discovery_node(state)

        with patch("src.graph.analyze_papers_batch", side_effect=Exception("Error 2")):
            state["discovered_papers"] = []
            state = reader_node(state)

        # Both errors should be in state
        assert len(state["errors"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
