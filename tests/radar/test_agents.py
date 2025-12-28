"""
Tests for the Radar Agent functions.

These tests verify the individual agent node functions that make up
the agentic radar workflow.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.agents.radar import (
    RADAR_STRATEGIES,
    RadarState,
    assessor_agent_node,
    curator_agent_node,
    decision_agent_node,
    filter_agent_node,
    log_agent_node,
    notifier_agent_node,
    route_decision,
    scanner_agent_node,
    strategy_agent_node,
)


@pytest.fixture
def empty_state() -> RadarState:
    """Create an empty radar state for testing."""
    return RadarState(
        current_strategy="",
        strategies_tried=[],
        iterations=0,
        max_iterations=3,
        papers_seen=[],
        current_papers=None,
        noteworthy_papers=[],
        breakthrough_threshold=0.6,
        relevance_threshold=0.5,
        social_threshold=0.3,
        notification_sent=False,
        cycle_stats={},
        errors=[],
    )


@pytest.fixture
def mock_paper():
    """Create a mock Paper object."""
    paper = MagicMock()
    paper.arxiv_id = "2312.12345"
    paper.title = "Test Paper Title"
    paper.breakthrough_score = None
    paper.relevance_score = None
    paper.score_components = {}
    return paper


class TestRadarStrategies:
    """Tests for RADAR_STRATEGIES constant."""

    def test_strategies_list_exists(self):
        """Test that RADAR_STRATEGIES is defined."""
        assert RADAR_STRATEGIES is not None
        assert isinstance(RADAR_STRATEGIES, list)
        assert len(RADAR_STRATEGIES) > 0

    def test_strategies_contains_expected(self):
        """Test that RADAR_STRATEGIES contains expected values."""
        assert "recent_2_days" in RADAR_STRATEGIES
        assert "recent_7_days" in RADAR_STRATEGIES
        assert "trending_social" in RADAR_STRATEGIES


class TestStrategyAgentNode:
    """Tests for strategy_agent_node function."""

    def test_selects_first_strategy_on_empty(self, empty_state):
        """Test that first strategy is selected when none tried."""
        result = strategy_agent_node(empty_state)

        assert result["current_strategy"] == RADAR_STRATEGIES[0]
        assert result["iterations"] == 1

    def test_selects_next_untried_strategy(self, empty_state):
        """Test that next untried strategy is selected."""
        empty_state["strategies_tried"] = [RADAR_STRATEGIES[0]]

        result = strategy_agent_node(empty_state)

        assert result["current_strategy"] == RADAR_STRATEGIES[1]

    def test_uses_fallback_when_exhausted(self, empty_state):
        """Test fallback when all strategies tried."""
        empty_state["strategies_tried"] = RADAR_STRATEGIES.copy()

        result = strategy_agent_node(empty_state)

        assert result["current_strategy"] == RADAR_STRATEGIES[-1]

    def test_increments_iterations(self, empty_state):
        """Test that iterations counter increments."""
        empty_state["iterations"] = 2

        result = strategy_agent_node(empty_state)

        assert result["iterations"] == 3


class TestScannerAgentNode:
    """Tests for scanner_agent_node function."""

    @patch("src.graph.run_full_pipeline")
    def test_scanner_with_standard_strategy(self, mock_pipeline, empty_state, mock_paper):
        """Test scanner with standard discovery strategy."""
        mock_pipeline.return_value = {"ranked_papers": [mock_paper]}
        empty_state["current_strategy"] = "recent_2_days"

        result = scanner_agent_node(empty_state)

        assert len(result["current_papers"]) == 1
        mock_pipeline.assert_called_once_with(days_back=2, max_papers=30)

    @patch("src.agents.radar.scanner.get_db_session")
    @patch("src.trackers.hackernews.fetch_hn_signals")
    def test_scanner_with_trending_social_strategy(self, mock_hn, mock_db, empty_state, mock_paper):
        """Test scanner with trending_social strategy."""
        mock_hn.return_value = [{"arxiv_id": "2312.12345"}]
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_session.query.return_value.filter.return_value.all.return_value = [mock_paper]
        mock_db.return_value = mock_session
        empty_state["current_strategy"] = "trending_social"

        result = scanner_agent_node(empty_state)

        assert "current_papers" in result
        mock_hn.assert_called_once()

    @patch("src.graph.run_full_pipeline")
    def test_scanner_handles_exception(self, mock_pipeline, empty_state):
        """Test scanner handles exceptions gracefully."""
        mock_pipeline.side_effect = Exception("API error")
        empty_state["current_strategy"] = "recent_2_days"

        result = scanner_agent_node(empty_state)

        assert result["current_papers"] == []
        assert len(result["errors"]) > 0
        assert "Scanner error" in result["errors"][0]


class TestFilterAgentNode:
    """Tests for filter_agent_node function."""

    def test_filters_duplicate_papers(self, empty_state, mock_paper):
        """Test that duplicate papers are filtered."""
        paper1 = MagicMock()
        paper1.arxiv_id = "2312.12345"
        paper2 = MagicMock()
        paper2.arxiv_id = "2312.67890"

        empty_state["current_papers"] = [paper1, paper2]
        empty_state["papers_seen"] = ["2312.12345"]  # Already seen

        result = filter_agent_node(empty_state)

        assert len(result["current_papers"]) == 1
        assert result["current_papers"][0].arxiv_id == "2312.67890"

    def test_updates_papers_seen(self, empty_state, mock_paper):
        """Test that papers_seen is updated."""
        empty_state["current_papers"] = [mock_paper]
        empty_state["papers_seen"] = []

        result = filter_agent_node(empty_state)

        assert mock_paper.arxiv_id in result["papers_seen"]

    def test_handles_empty_papers(self, empty_state):
        """Test handling of empty papers list."""
        empty_state["current_papers"] = []

        result = filter_agent_node(empty_state)

        assert result["current_papers"] == []


class TestAssessorAgentNode:
    """Tests for assessor_agent_node function."""

    @patch("src.agents.radar.radar_assessor.assess_papers_batch")
    def test_assesses_unassessed_papers(self, mock_assess, empty_state, mock_paper):
        """Test that unassessed papers are assessed."""
        mock_paper.breakthrough_score = None
        assessed_paper = MagicMock()
        assessed_paper.arxiv_id = mock_paper.arxiv_id
        assessed_paper.breakthrough_score = 0.8
        mock_assess.return_value = ([assessed_paper], [])
        empty_state["current_papers"] = [mock_paper]

        result = assessor_agent_node(empty_state)

        mock_assess.assert_called_once()
        assert result["current_papers"][0].breakthrough_score == 0.8

    def test_skips_already_assessed_papers(self, empty_state, mock_paper):
        """Test that already assessed papers are skipped."""
        mock_paper.breakthrough_score = 0.7
        empty_state["current_papers"] = [mock_paper]

        with patch("src.agents.radar.radar_assessor.assess_papers_batch") as mock_assess:
            assessor_agent_node(empty_state)
            mock_assess.assert_not_called()

    def test_handles_empty_papers(self, empty_state):
        """Test handling of empty papers list."""
        empty_state["current_papers"] = []

        result = assessor_agent_node(empty_state)

        assert result["current_papers"] == []


class TestCuratorAgentNode:
    """Tests for curator_agent_node function."""

    @patch("src.agents.radar.radar_curator.curate_papers_batch")
    def test_curates_papers(self, mock_curate, empty_state, mock_paper):
        """Test that papers are curated."""
        mock_curate.return_value = [mock_paper]
        empty_state["current_papers"] = [mock_paper]

        curator_agent_node(empty_state)

        mock_curate.assert_called_once_with([mock_paper])

    def test_handles_empty_papers(self, empty_state):
        """Test handling of empty papers list."""
        empty_state["current_papers"] = []

        result = curator_agent_node(empty_state)

        assert result["current_papers"] == []


class TestDecisionAgentNode:
    """Tests for decision_agent_node function."""

    def test_identifies_breakthrough_papers(self, empty_state, mock_paper):
        """Test that breakthrough papers are marked noteworthy."""
        mock_paper.breakthrough_score = 0.8  # Above 0.6 threshold
        mock_paper.relevance_score = 0.5
        empty_state["current_papers"] = [mock_paper]
        empty_state["current_strategy"] = "recent_2_days"

        result = decision_agent_node(empty_state)

        assert len(result["noteworthy_papers"]) == 1

    def test_identifies_high_relevance_papers(self, empty_state, mock_paper):
        """Test that high relevance papers are marked noteworthy."""
        mock_paper.breakthrough_score = 0.3
        mock_paper.relevance_score = 0.85  # Above 0.8 threshold
        empty_state["current_papers"] = [mock_paper]
        empty_state["current_strategy"] = "recent_2_days"

        result = decision_agent_node(empty_state)

        assert len(result["noteworthy_papers"]) == 1

    def test_lower_threshold_strategy_reduces_thresholds(self, empty_state, mock_paper):
        """Test that lower_threshold strategy reduces thresholds."""
        mock_paper.breakthrough_score = 0.5  # Would be below 0.6, but 0.6*0.8=0.48
        mock_paper.relevance_score = 0.5
        empty_state["current_papers"] = [mock_paper]
        empty_state["current_strategy"] = "lower_threshold"

        result = decision_agent_node(empty_state)

        assert len(result["noteworthy_papers"]) == 1

    def test_updates_strategies_tried(self, empty_state):
        """Test that strategies_tried is updated."""
        empty_state["current_papers"] = []
        empty_state["current_strategy"] = "recent_2_days"
        empty_state["strategies_tried"] = []

        result = decision_agent_node(empty_state)

        assert "recent_2_days" in result["strategies_tried"]


class TestRouteDecision:
    """Tests for route_decision function."""

    def test_returns_notify_when_noteworthy(self, empty_state, mock_paper):
        """Test that 'notify' is returned when noteworthy papers exist."""
        empty_state["noteworthy_papers"] = [mock_paper]

        result = route_decision(empty_state)

        assert result == "notify"

    def test_returns_done_at_max_iterations(self, empty_state):
        """Test that 'done' is returned at max iterations."""
        empty_state["noteworthy_papers"] = []
        empty_state["iterations"] = 3
        empty_state["max_iterations"] = 3

        result = route_decision(empty_state)

        assert result == "done"

    def test_returns_done_when_strategies_exhausted(self, empty_state):
        """Test that 'done' is returned when all strategies tried."""
        empty_state["noteworthy_papers"] = []
        empty_state["strategies_tried"] = RADAR_STRATEGIES.copy()

        result = route_decision(empty_state)

        assert result == "done"

    def test_returns_expand_otherwise(self, empty_state):
        """Test that 'expand' is returned when more strategies available."""
        empty_state["noteworthy_papers"] = []
        empty_state["iterations"] = 1
        empty_state["strategies_tried"] = [RADAR_STRATEGIES[0]]

        result = route_decision(empty_state)

        assert result == "expand"


class TestNotifierAgentNode:
    """Tests for notifier_agent_node function."""

    @patch("src.agents.radar.notifier.send_paper_notification")
    def test_sends_notification_for_noteworthy(self, mock_send, empty_state, mock_paper):
        """Test that notification is sent for noteworthy papers."""
        mock_send.return_value = True
        mock_paper.breakthrough_score = 0.8
        empty_state["noteworthy_papers"] = [mock_paper]

        result = notifier_agent_node(empty_state)

        assert result["notification_sent"] is True
        mock_send.assert_called_once()

    def test_handles_no_papers(self, empty_state):
        """Test handling when no papers to notify about."""
        empty_state["noteworthy_papers"] = []

        result = notifier_agent_node(empty_state)

        assert result["notification_sent"] is False

    @patch("src.agents.radar.notifier.send_paper_notification")
    def test_handles_send_failure(self, mock_send, empty_state, mock_paper):
        """Test handling of notification send failure."""
        mock_send.side_effect = Exception("Email error")
        empty_state["noteworthy_papers"] = [mock_paper]

        result = notifier_agent_node(empty_state)

        assert result["notification_sent"] is False
        assert len(result["errors"]) > 0


class TestLogAgentNode:
    """Tests for log_agent_node function."""

    def test_logs_cycle_results(self, empty_state):
        """Test that log agent logs results."""
        empty_state["iterations"] = 2
        empty_state["strategies_tried"] = ["recent_2_days", "recent_7_days"]
        empty_state["papers_seen"] = ["paper1", "paper2"]

        result = log_agent_node(empty_state)

        # Log agent returns state unchanged
        assert result["iterations"] == 2
        assert len(result["strategies_tried"]) == 2
