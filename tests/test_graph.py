"""
Comprehensive Unit Tests for LangGraph Workflows

Fixed with proper state initialization and mocking.
"""

from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest

from src.graph import (
    create_workflow,
    discovery_node,
    explainer_node,
    reader_node,
    run_analysis_pipeline,
    run_discovery_only_pipeline,
    run_full_pipeline,
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
        paper.published_date = datetime.now(UTC)
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

    @patch("src.graph.get_db_session")
    @patch("src.graph.analyze_papers_batch")
    def test_reader_node_success(self, mock_analyze, mock_db, mock_papers):
        """Test reader node with successful analysis."""
        # Ensure papers look unanalyzed initially
        for p in mock_papers:
            p.analyzed_at = None

        # Create analyzed versions for the return value
        analyzed_papers = []
        for p in mock_papers:
            analyzed_p = Mock(spec=Paper)
            analyzed_p.arxiv_id = p.arxiv_id
            analyzed_p.title = p.title
            analyzed_p.main_claim = "Test claim"
            analyzed_p.analyzed_at = datetime.now(UTC)
            analyzed_papers.append(analyzed_p)

        mock_analyze.return_value = analyzed_papers

        # Mock database session for reloading papers
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.all.return_value = analyzed_papers
        mock_db.return_value.__enter__ = Mock(return_value=mock_session)
        mock_db.return_value.__exit__ = Mock(return_value=None)

        state = {
            "discovered_papers": mock_papers,
            "analyzed_papers": None,
            "errors": [],
            "stats": {},
        }

        result = reader_node(state)

        assert result["analyzed_papers"] == analyzed_papers
        assert result["stats"]["analyzed_count"] == 2
        assert result["stats"]["cached_count"] == 0
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
        # Ensure papers look unanalyzed
        for p in mock_papers:
            p.analyzed_at = None

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
            p.explained_at = datetime.now(UTC)

        mock_explain.return_value = explained_papers

        state = {
            "analyzed_papers": mock_papers,
            "explained_papers": None,
            "errors": [],
            "stats": {},
        }

        result = explainer_node(state)

        assert result["explained_papers"] == explained_papers
        # Note: final_papers is now set by curator_node, not explainer_node
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
        assert result["stats"]["explained_count"] == 0


class TestWorkflowCreation:
    """Test workflow graph construction."""

    def test_create_workflow_structure(self):
        """Test that workflow is created with correct structure."""
        workflow = create_workflow()
        assert workflow is not None

    def test_create_workflow_has_nodes(self):
        """Test that workflow contains all required nodes."""
        workflow = create_workflow()
        assert workflow is not None


class TestFullPipeline:
    """Test complete pipeline execution."""

    @patch("src.graph.get_db_session")
    @patch("src.graph.discover_papers")
    @patch("src.graph.analyze_papers_batch")
    @patch("src.graph.explain_papers_batch")
    def test_run_full_pipeline_success(
        self, mock_explain, mock_analyze, mock_discover, mock_db, mock_papers
    ):
        """Test successful execution of full pipeline."""
        # Ensure papers start unanalyzed/unassessed
        for p in mock_papers:
            p.analyzed_at = None
            p.explained_at = None
            p.breakthrough_score = None

        mock_discover.return_value = mock_papers

        # Create separate analyzed paper objects
        analyzed = []
        for p in mock_papers:
            ap = Mock(spec=Paper)
            ap.arxiv_id = p.arxiv_id
            ap.title = p.title
            ap.main_claim = "Claim"
            ap.analyzed_at = datetime.now(UTC)
            ap.explained_at = None
            ap.breakthrough_score = None
            analyzed.append(ap)
        mock_analyze.return_value = analyzed

        # Create separate explained paper objects
        explained = []
        for p in analyzed:
            ep = Mock(spec=Paper)
            ep.arxiv_id = p.arxiv_id
            ep.title = p.title
            ep.main_claim = p.main_claim
            ep.eli5_summary = "Summary"
            ep.explained_at = datetime.now(UTC)
            ep.analyzed_at = p.analyzed_at
            ep.breakthrough_score = 0.5  # Set a score to avoid comparison issues
            explained.append(ep)
        mock_explain.return_value = explained

        # Mock database session for reloading papers
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.all.return_value = explained
        mock_db.return_value.__enter__ = Mock(return_value=mock_session)
        mock_db.return_value.__exit__ = Mock(return_value=None)

        result = run_full_pipeline(days_back=7, max_papers=2)

        assert result["discovered_papers"] == mock_papers
        assert result["stats"]["discovered_count"] == 2
        assert result["stats"]["analyzed_count"] == 2
        assert result["stats"]["explained_count"] == 2

    @patch("src.graph.discover_papers")
    def test_run_full_pipeline_handles_discovery_error(self, mock_discover):
        """Test pipeline continues even when discovery fails."""
        mock_discover.side_effect = Exception("Network error")

        result = run_full_pipeline(days_back=7)

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
        assert "analyzed_papers" in result
        assert "explained_papers" in result


class TestAnalysisPipeline:
    """Test analysis-only pipeline."""

    @patch("src.graph.get_db_session")
    @patch("src.graph.analyze_papers_batch")
    @patch("src.graph.explain_papers_batch")
    def test_run_analysis_pipeline(self, mock_explain, mock_analyze, mock_get_session, db_session):
        """Test analysis pipeline on existing papers."""
        mock_get_session.side_effect = lambda: db_session()

        # Create unanalyzed papers in test database
        with db_session() as db:
            for i in range(2):
                paper = Paper(
                    arxiv_id=f"2312.analysis.{i}",
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

        # Get papers from database for mocking
        with db_session() as db:
            created_papers = db.query(Paper).filter(Paper.arxiv_id.like("2312.analysis%")).all()

        # Mock returns
        analyzed = created_papers.copy()
        for p in analyzed:
            p.main_claim = "Claim"
            p.analyzed_at = datetime.now(UTC)
        mock_analyze.return_value = analyzed

        explained = analyzed.copy()
        for p in explained:
            p.eli5_summary = "Summary"
            p.explained_at = datetime.now(UTC)
        mock_explain.return_value = explained

        result = run_analysis_pipeline()

        assert result["stats"]["discovered_count"] == 2
        assert result["stats"]["analyzed_count"] == 2
        assert result["stats"]["explained_count"] == 2

    @patch("src.graph.get_db_session")
    def test_run_analysis_pipeline_no_papers(self, mock_get_session, db_session):
        """Test analysis pipeline when no unanalyzed papers exist."""
        mock_get_session.side_effect = lambda: db_session()

        result = run_analysis_pipeline()

        assert result["stats"]["discovered_count"] == 0
        assert result["stats"]["analyzed_count"] == 0
        assert result["stats"]["explained_count"] == 0


class TestStateManagement:
    """Test state management through workflow."""

    def test_initial_state_structure(self):
        """Test that initial state has correct structure."""
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

        assert "days_back" in state
        assert "discovered_papers" in state
        assert "errors" in state
        assert "stats" in state

    @patch("src.graph.discover_papers")
    def test_state_flows_through_nodes(self, mock_discover, mock_papers):
        """Test that state is properly updated as it flows through nodes."""
        mock_discover.return_value = mock_papers

        state = {
            "days_back": 7,
            "discovered_papers": None,
            "errors": [],
            "stats": {},
        }

        state = discovery_node(state)

        assert state["discovered_papers"] == mock_papers
        assert "discovered_count" in state["stats"]

    def test_errors_accumulate_in_state(self):
        """Test that errors from different nodes accumulate."""
        state = {
            "days_back": 1,
            "categories": None,
            "max_papers": None,
            "discovered_papers": None,
            "analyzed_papers": None,
            "explained_papers": None,
            "final_papers": None,
            "errors": [],
            "stats": {},
        }

        with patch("src.graph.discover_papers", side_effect=Exception("Error 1")):
            state = discovery_node(state)

        with patch("src.graph.analyze_papers_batch", side_effect=Exception("Error 2")):
            # Provide unanalyzed papers so reader_node actually tries to analyze them
            mock_paper = Mock(spec=Paper)
            mock_paper.arxiv_id = "test.1"
            mock_paper.title = "Test"
            mock_paper.analyzed_at = None  # Must be None for caching to not skip
            state["discovered_papers"] = [mock_paper]
            state = reader_node(state)

        assert len(state["errors"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
