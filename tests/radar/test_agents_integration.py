"""
Integration tests for Radar Agents.

These tests use live data to verify each agent works correctly.
Marked with @pytest.mark.integration to run separately from unit tests.
"""

from datetime import datetime

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
from src.models.paper import Paper
from src.trackers.hackernews import fetch_hn_signals


def create_test_state(**overrides) -> RadarState:
    """Create a RadarState with sensible defaults for testing."""
    defaults = {
        "current_strategy": "",
        "strategies_tried": [],
        "iterations": 0,
        "max_iterations": 3,
        "papers_seen": [],
        "current_papers": None,
        "noteworthy_papers": [],
        "breakthrough_threshold": 0.6,
        "relevance_threshold": 0.5,
        "social_threshold": 0.3,
        "notification_sent": False,
        "cycle_stats": {},
        "errors": [],
    }
    defaults.update(overrides)
    return RadarState(**defaults)


def create_test_paper(
    arxiv_id: str = "2312.12345",
    title: str = "Test Paper",
    breakthrough_score: float | None = None,
    relevance_score: float | None = None,
    **kwargs,
) -> Paper:
    """Create a Paper object for testing."""
    paper = Paper(
        arxiv_id=arxiv_id,
        title=title,
        abstract="Test abstract for the paper.",
        authors=["Author One", "Author Two"],
        categories=["cs.AI"],
        published_date=datetime.now(),
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}.pdf",
    )
    paper.breakthrough_score = breakthrough_score
    paper.relevance_score = relevance_score
    for key, value in kwargs.items():
        setattr(paper, key, value)
    return paper


@pytest.mark.integration
class TestStrategyAgentIntegration:
    """Integration tests for StrategyAgent."""

    def test_selects_strategy_from_list(self):
        """Test that strategy agent selects from RADAR_STRATEGIES."""
        state = create_test_state()

        result = strategy_agent_node(state)

        assert result["current_strategy"] in RADAR_STRATEGIES
        assert result["iterations"] == 1

    def test_progresses_through_strategies(self):
        """Test that agent progresses through strategies."""
        state = create_test_state(strategies_tried=["recent_2_days"])

        result = strategy_agent_node(state)

        assert result["current_strategy"] == "recent_7_days"
        assert result["current_strategy"] not in state["strategies_tried"]


@pytest.mark.integration
class TestScannerAgentIntegration:
    """Integration tests for ScannerAgent."""

    def test_scanner_with_trending_social_fetches_hn_signals(self):
        """Test that scanner with trending_social strategy fetches HN signals.

        Note: This test mocks the database to isolate the HN API call.
        The database matching is tested separately.
        """
        from unittest.mock import MagicMock, patch

        state = create_test_state(current_strategy="trending_social")

        # Mock the database session to return empty list (no matching papers)
        mock_session = MagicMock()
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_session.query.return_value.filter.return_value.all.return_value = []

        with patch("src.agents.radar.scanner.get_db_session", return_value=mock_session):
            result = scanner_agent_node(state)

        # Should return a valid state without errors
        assert "current_papers" in result
        assert "cycle_stats" in result
        # trending_social strategy found papers from HN but 0 matched in (mocked empty) DB
        assert result["current_papers"] == []
        assert not result.get("errors"), f"Unexpected errors: {result.get('errors')}"


@pytest.mark.integration
class TestHackerNewsTrackerIntegration:
    """Integration tests for HackerNews signal fetching."""

    def test_fetch_hn_signals_returns_data(self):
        """Test that HN tracker returns actual papers."""
        signals = fetch_hn_signals(days_back=7)

        # Should find papers (HN always has arXiv discussions)
        assert len(signals) > 0, "Expected to find arXiv papers on HackerNews"

        # Verify structure
        first = signals[0]
        assert "arxiv_id" in first
        assert "score" in first
        assert "social_score" in first

    def test_hn_signals_sorted_by_social_score(self):
        """Test that signals are sorted by social score."""
        signals = fetch_hn_signals(days_back=7)

        if len(signals) > 1:
            scores = [s["social_score"] for s in signals]
            assert scores == sorted(scores, reverse=True)


@pytest.mark.integration
class TestFilterAgentIntegration:
    """Integration tests for FilterAgent."""

    def test_filters_duplicate_papers(self):
        """Test that filter agent removes duplicates."""
        paper1 = create_test_paper(arxiv_id="2312.11111")
        paper2 = create_test_paper(arxiv_id="2312.22222")
        paper3 = create_test_paper(arxiv_id="2312.11111")  # Duplicate

        state = create_test_state(
            current_papers=[paper1, paper2, paper3],
            papers_seen=[],
        )

        result = filter_agent_node(state)

        # Should have filtered out the duplicate
        assert len(result["current_papers"]) == 2
        arxiv_ids = [p.arxiv_id for p in result["current_papers"]]
        assert "2312.11111" in arxiv_ids
        assert "2312.22222" in arxiv_ids

    def test_tracks_papers_seen(self):
        """Test that papers are added to seen list."""
        paper = create_test_paper(arxiv_id="2312.99999")
        state = create_test_state(current_papers=[paper], papers_seen=[])

        result = filter_agent_node(state)

        assert "2312.99999" in result["papers_seen"]

    def test_returns_papers_when_input_provided(self):
        """Test happy path - returns papers when given papers."""
        papers = [
            create_test_paper(arxiv_id="2312.11111"),
            create_test_paper(arxiv_id="2312.22222"),
        ]
        state = create_test_state(current_papers=papers)

        result = filter_agent_node(state)

        assert len(result["current_papers"]) == 2


@pytest.mark.integration
class TestAssessorAgentIntegration:
    """Integration tests for AssessorAgent."""

    def test_skips_already_assessed_papers(self):
        """Test that assessed papers are not re-assessed."""
        paper = create_test_paper(breakthrough_score=0.8)
        state = create_test_state(current_papers=[paper])

        result = assessor_agent_node(state)

        # Should return same paper without calling assessor
        assert len(result["current_papers"]) == 1
        assert result["current_papers"][0].breakthrough_score == 0.8

    def test_returns_papers_when_input_provided(self):
        """Test happy path - returns papers."""
        paper = create_test_paper(breakthrough_score=0.7)
        state = create_test_state(current_papers=[paper])

        result = assessor_agent_node(state)

        assert len(result["current_papers"]) == 1


@pytest.mark.integration
class TestCuratorAgentIntegration:
    """Integration tests for CuratorAgent."""

    def test_returns_papers_when_input_provided(self):
        """Test happy path - returns papers."""
        papers = [
            create_test_paper(arxiv_id="2312.11111"),
            create_test_paper(arxiv_id="2312.22222"),
        ]
        state = create_test_state(current_papers=papers)

        result = curator_agent_node(state)

        assert len(result["current_papers"]) == 2

    def test_uses_precalculated_social_scores(self):
        """Test that curator uses hn_social_score from score_components.

        This test verifies the data format contract: curator should read
        pre-calculated social scores, not recalculate from raw data.
        """
        from src.agents.curator import CuratorAgent

        paper = create_test_paper(
            score_components={
                "hn_social_score": 0.45,  # Pre-calculated
                "twitter_social_score": 0.0,
                "hn_score": 250,  # Raw - should be ignored for scoring
                "hn_comments": 120,  # Raw - should be ignored for scoring
            },
        )

        curator = CuratorAgent(interests=[])
        social_score = curator.calculate_social_score(paper)

        # Should use pre-calculated hn_social_score (0.45)
        assert social_score == 0.45

    def test_uses_max_of_hn_and_twitter_scores(self):
        """Test that curator takes max of HN and Twitter social scores."""
        from src.agents.curator import CuratorAgent

        paper = create_test_paper(
            score_components={
                "hn_social_score": 0.2,
                "twitter_social_score": 0.4,  # Higher - should be used
            },
        )

        curator = CuratorAgent(interests=[])
        social_score = curator.calculate_social_score(paper)

        # Should return max(0.2, 0.4) = 0.4
        assert social_score == 0.4


@pytest.mark.integration
class TestDecisionAgentIntegration:
    """Integration tests for DecisionAgent."""

    def test_uses_precalculated_social_scores(self):
        """Test that decision agent uses hn_social_score and twitter_social_score.

        This test verifies the data format contract: the signal node stores
        pre-calculated scores in score_components, and decision agent should
        use these instead of recalculating from raw data.
        """
        paper = create_test_paper(
            breakthrough_score=0.3,  # Below threshold
            relevance_score=0.6,  # Above relevance threshold when combined
            score_components={
                "hn_social_score": 0.4,  # Above social threshold (0.3)
                "twitter_social_score": 0.0,
                "hn_score": 150,  # Raw data - should NOT be used for scoring
                "hn_comments": 50,
            },
        )
        state = create_test_state(
            current_papers=[paper],
            current_strategy="recent_2_days",
            social_threshold=0.3,
            relevance_threshold=0.5,
        )

        result = decision_agent_node(state)

        # Paper should be noteworthy because social (0.4) >= threshold (0.3)
        # AND relevance (0.6) >= threshold (0.5) = "trending+relevant"
        assert len(result["noteworthy_papers"]) == 1

    def test_uses_twitter_social_score_when_higher(self):
        """Test that decision agent takes max of HN and Twitter social scores."""
        paper = create_test_paper(
            breakthrough_score=0.3,
            relevance_score=0.6,
            score_components={
                "hn_social_score": 0.1,  # Low HN
                "twitter_social_score": 0.5,  # High Twitter - should be used
            },
        )
        state = create_test_state(
            current_papers=[paper],
            current_strategy="recent_2_days",
            social_threshold=0.4,  # Twitter score meets this
            relevance_threshold=0.5,
        )

        result = decision_agent_node(state)

        # Should be noteworthy via Twitter social score (0.5 >= 0.4)
        assert len(result["noteworthy_papers"]) == 1

    def test_identifies_breakthrough_paper(self):
        """Test that high breakthrough score paper is marked noteworthy."""
        paper = create_test_paper(
            breakthrough_score=0.8,  # Above 0.6 threshold
            relevance_score=0.5,
        )
        state = create_test_state(
            current_papers=[paper],
            current_strategy="recent_2_days",
        )

        result = decision_agent_node(state)

        assert len(result["noteworthy_papers"]) == 1

    def test_identifies_high_relevance_paper(self):
        """Test that high relevance paper is marked noteworthy."""
        paper = create_test_paper(
            breakthrough_score=0.3,
            relevance_score=0.9,  # Above 0.8 high relevance threshold
        )
        state = create_test_state(
            current_papers=[paper],
            current_strategy="recent_2_days",
        )

        result = decision_agent_node(state)

        assert len(result["noteworthy_papers"]) == 1

    def test_updates_strategies_tried(self):
        """Test that current strategy is added to tried list."""
        state = create_test_state(
            current_papers=[],
            current_strategy="recent_2_days",
            strategies_tried=[],
        )

        result = decision_agent_node(state)

        assert "recent_2_days" in result["strategies_tried"]


@pytest.mark.integration
class TestRouteDecisionIntegration:
    """Integration tests for route_decision function."""

    def test_returns_notify_when_noteworthy(self):
        """Test routing to notify when papers found."""
        paper = create_test_paper()
        state = create_test_state(noteworthy_papers=[paper])

        result = route_decision(state)

        assert result == "notify"

    def test_returns_expand_when_strategies_available(self):
        """Test routing to expand when more strategies available."""
        state = create_test_state(
            noteworthy_papers=[],
            iterations=1,
            strategies_tried=["recent_2_days"],
        )

        result = route_decision(state)

        assert result == "expand"

    def test_returns_done_at_max_iterations(self):
        """Test routing to done at max iterations."""
        state = create_test_state(
            noteworthy_papers=[],
            iterations=3,
            max_iterations=3,
        )

        result = route_decision(state)

        assert result == "done"


@pytest.mark.integration
class TestNotifierAgentIntegration:
    """Integration tests for NotifierAgent."""

    def test_handles_no_papers_gracefully(self):
        """Test that notifier handles empty paper list."""
        state = create_test_state(noteworthy_papers=[])

        result = notifier_agent_node(state)

        assert result["notification_sent"] is False
        assert not result.get("errors")


@pytest.mark.integration
class TestLogAgentIntegration:
    """Integration tests for LogAgent."""

    def test_returns_state_unchanged(self):
        """Test that log agent returns state without modification."""
        state = create_test_state(
            iterations=2,
            strategies_tried=["recent_2_days", "recent_7_days"],
            papers_seen=["paper1", "paper2"],
        )

        result = log_agent_node(state)

        assert result["iterations"] == 2
        assert len(result["strategies_tried"]) == 2
        assert len(result["papers_seen"]) == 2


@pytest.mark.integration
class TestFullAgentPipelineIntegration:
    """Integration tests for agent pipeline flow."""

    def test_strategy_to_filter_flow(self):
        """Test flow from strategy through filter."""
        # Start with strategy
        state = create_test_state()
        state = strategy_agent_node(state)

        assert state["current_strategy"] in RADAR_STRATEGIES

        # Simulate scanner output (skip actual scanning for speed)
        papers = [
            create_test_paper(arxiv_id="2312.11111"),
            create_test_paper(arxiv_id="2312.22222"),
        ]
        state["current_papers"] = papers

        # Run filter
        state = filter_agent_node(state)

        assert len(state["current_papers"]) == 2
        assert len(state["papers_seen"]) == 2

    def test_assess_to_decision_flow(self):
        """Test flow from assessor through decision."""
        paper = create_test_paper(
            arxiv_id="2312.12345",
            breakthrough_score=0.8,
            relevance_score=0.6,
        )
        state = create_test_state(
            current_papers=[paper],
            current_strategy="recent_2_days",
        )

        # Skip assessor (already assessed)
        state = assessor_agent_node(state)
        assert len(state["current_papers"]) == 1

        # Run curator
        state = curator_agent_node(state)
        assert len(state["current_papers"]) == 1

        # Run decision
        state = decision_agent_node(state)
        assert len(state["noteworthy_papers"]) == 1

        # Check routing
        route = route_decision(state)
        assert route == "notify"
