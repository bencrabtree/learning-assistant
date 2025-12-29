"""
Radar workflow state and constants.

This module defines the shared state that flows through the radar workflow.
"""

from typing import TypedDict

from src.models.paper import Paper


class RadarState(TypedDict):
    """
    State for the agentic radar workflow.

    This state evolves across iterations as the workflow:
    1. Tries different search strategies
    2. Accumulates seen papers (to avoid re-processing)
    3. Collects noteworthy papers for notification
    4. Decides when to notify, expand search, or stop
    """

    # Strategy & Iteration Tracking
    current_strategy: str
    """Current search strategy being executed."""

    strategies_tried: list[str]
    """List of strategies already attempted this cycle."""

    iterations: int
    """Number of iterations completed."""

    max_iterations: int
    """Maximum iterations before stopping (prevents infinite loops)."""

    # Paper Tracking
    papers_seen: list[str]
    """arXiv IDs of papers already processed (avoid duplicates)."""

    current_papers: list[Paper] | None
    """Papers found in current iteration."""

    noteworthy_papers: list[Paper]
    """Papers that meet notification threshold (accumulated)."""

    # Thresholds
    breakthrough_threshold: float
    """Minimum breakthrough score to be noteworthy."""

    relevance_threshold: float
    """Minimum relevance score to be noteworthy."""

    social_threshold: float
    """Minimum social score for trending + relevant."""

    # Results & Metadata
    notification_sent: bool
    """Whether a notification was sent."""

    cycle_stats: dict
    """Statistics for this radar cycle."""

    errors: list[str]
    """Errors encountered during execution."""


# Expansion strategies in order of preference
RADAR_STRATEGIES = [
    "recent_2_days",
    "hn_discovery",  # Social-first discovery from HackerNews
    "recent_7_days",
    "recent_14_days",
    "trending_social",
    "lower_threshold",
]
