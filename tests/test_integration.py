"""
End-to-End Integration Tests

Simplified integration tests focusing on workflow orchestration.
Complex database integration testing is covered by unit tests.
"""

from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest

from src.database import init_db
from src.graph import (
    run_analysis_pipeline,
    run_discovery_only_pipeline,
    run_full_pipeline,
)
from src.models.paper import Paper


@pytest.fixture(scope="function")
def integration_db():
    """Create a clean database for integration tests."""
    init_db()
    yield


@pytest.mark.integration
class TestWorkflowOrchestration:
    """Test workflow orchestration without database complexity."""

    @patch("src.graph.discover_papers")
    @patch("src.graph.analyze_papers_batch")
    @patch("src.graph.explain_papers_batch")
    @patch("src.graph.fetch_hn_signals")
    @patch("src.graph.fetch_twitter_signals")
    @patch("src.graph.assess_papers_batch")
    @patch("src.graph.curate_papers_batch")
    def test_full_pipeline_orchestration(
        self,
        mock_curate,
        mock_assess,
        mock_twitter,
        mock_hn,
        mock_explain,
        mock_analyze,
        mock_discover,
    ):
        """Test that full pipeline correctly orchestrates all agents."""
        # Create simple mock papers (not Mock objects, but simple dicts)
        mock_papers = [
            Mock(
                arxiv_id=f"2312.{i}",
                title=f"Paper {i}",
                main_claim=None,
                analyzed_at=None,
                eli5_summary=None,
                explained_at=None,
                breakthrough_score=None,
                assessed_at=None,
                relevance_score=None,
            )
            for i in range(2)
        ]

        mock_discover.return_value = mock_papers

        analyzed = mock_papers.copy()
        for p in analyzed:
            p.main_claim = "Test claim"
            p.analyzed_at = datetime.now(UTC)
        mock_analyze.return_value = analyzed

        explained = analyzed.copy()
        for p in explained:
            p.eli5_summary = "Simple explanation"
            p.explained_at = datetime.now(UTC)
        mock_explain.return_value = explained

        # Mock social signals
        mock_hn.return_value = []
        mock_twitter.return_value = []

        # Mock assessor (returns tuple of papers, assessments)
        assessed = explained.copy()
        for p in assessed:
            p.breakthrough_score = 0.5
            p.assessed_at = datetime.now(UTC)
        assessments = [{"is_breakthrough": False} for _ in assessed]
        mock_assess.return_value = (assessed, assessments)

        ranked = assessed.copy()
        for p in ranked:
            p.relevance_score = 0.7
        mock_curate.return_value = ranked

        result = run_full_pipeline(days_back=1, max_papers=2)

        # Verify workflow executed correctly
        assert result["stats"]["discovered_count"] == 2
        assert result["stats"]["analyzed_count"] == 2
        assert result["stats"]["explained_count"] == 2
        assert len(result["errors"]) == 0

    @patch("src.graph.discover_papers")
    def test_discovery_only_workflow_orchestration(self, mock_discover):
        """Test discovery-only workflow orchestration."""
        mock_papers = [Mock(arxiv_id=f"2312.{i}", title=f"Paper {i}") for i in range(3)]

        mock_discover.return_value = mock_papers

        result = run_discovery_only_pipeline(days_back=1)

        assert result["stats"]["discovered_count"] == 3
        mock_discover.assert_called_once()

    @patch("src.graph.get_db_session")
    @patch("src.graph.analyze_papers_batch")
    @patch("src.graph.explain_papers_batch")
    def test_analysis_pipeline_orchestration(
        self, mock_explain, mock_analyze, mock_get_session, db_session
    ):
        """Test analysis pipeline orchestration."""
        mock_get_session.side_effect = lambda: db_session()

        # Create papers in test database
        with db_session() as db:
            for i in range(2):
                paper = Paper(
                    arxiv_id=f"2312.test.{i}",
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

        # Get papers for mocking
        with db_session() as db:
            papers = db.query(Paper).all()

        analyzed = papers.copy()
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


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling in workflows."""

    @patch("src.graph.discover_papers")
    def test_pipeline_handles_discovery_failure(self, mock_discover):
        """Test that pipeline handles discovery failures gracefully."""
        mock_discover.side_effect = Exception("Network timeout")

        result = run_full_pipeline(days_back=1)

        assert len(result["errors"]) > 0
        assert result["stats"].get("discovered_count", 0) == 0

    @patch("src.graph.discover_papers")
    @patch("src.graph.analyze_papers_batch")
    @patch("src.graph.explain_papers_batch")
    @patch("src.graph.fetch_hn_signals")
    @patch("src.graph.fetch_twitter_signals")
    @patch("src.graph.assess_papers_batch")
    @patch("src.graph.curate_papers_batch")
    def test_pipeline_continues_after_analysis_failure(
        self,
        mock_curate,
        mock_assess,
        mock_twitter,
        mock_hn,
        mock_explain,
        mock_analyze,
        mock_discover,
    ):
        """Test that pipeline continues after partial failures."""
        mock_papers = [Mock(arxiv_id=f"2312.{i}", title=f"Paper {i}") for i in range(2)]
        mock_discover.return_value = mock_papers

        # Analysis fails but pipeline should continue
        mock_analyze.side_effect = Exception("Rate limit exceeded")
        mock_explain.return_value = []
        mock_hn.return_value = []
        mock_twitter.return_value = []
        mock_assess.return_value = ([], [])
        mock_curate.return_value = []

        result = run_full_pipeline(days_back=1)

        assert result["stats"]["discovered_count"] == 2
        assert result["stats"]["analyzed_count"] == 0
        assert len(result["errors"]) > 0


@pytest.mark.integration
class TestStateManagement:
    """Test state propagation through workflows."""

    @patch("src.graph.discover_papers")
    @patch("src.graph.analyze_papers_batch")
    @patch("src.graph.explain_papers_batch")
    @patch("src.graph.fetch_hn_signals")
    @patch("src.graph.fetch_twitter_signals")
    @patch("src.graph.assess_papers_batch")
    @patch("src.graph.curate_papers_batch")
    def test_max_papers_limit_enforced(
        self,
        mock_curate,
        mock_assess,
        mock_twitter,
        mock_hn,
        mock_explain,
        mock_analyze,
        mock_discover,
    ):
        """Test that max_papers limit is enforced."""
        mock_papers = [Mock(arxiv_id=f"2312.{i}", title=f"Paper {i}") for i in range(5)]
        mock_discover.return_value = mock_papers
        mock_analyze.return_value = mock_papers[:2]
        mock_explain.return_value = mock_papers[:2]
        mock_hn.return_value = []
        mock_twitter.return_value = []
        mock_assess.return_value = (mock_papers[:2], [{"is_breakthrough": False}] * 2)
        mock_curate.return_value = mock_papers[:2]

        result = run_full_pipeline(days_back=1, max_papers=2)

        # Should process exactly 2 papers
        assert result["stats"]["discovered_count"] == 2

    @patch("src.graph.get_db_session")
    def test_analysis_pipeline_with_no_papers(self, mock_get_session, db_session):
        """Test analysis pipeline when no papers exist."""
        mock_get_session.side_effect = lambda: db_session()

        result = run_analysis_pipeline()

        assert result["stats"]["discovered_count"] == 0
        assert result["stats"]["analyzed_count"] == 0
        assert result["stats"]["explained_count"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
