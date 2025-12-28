"""
LogAgent - Logs the cycle results when nothing was found.

This agent logs the final results when the radar completes
without finding any noteworthy papers.
"""

from loguru import logger

from src.agents.radar.state import RadarState


def log_agent_node(state: RadarState) -> RadarState:
    """
    LogAgent: Logs the cycle results when nothing was found.

    Records the final state of the radar cycle including:
    - Number of iterations completed
    - Strategies tried
    - Total papers scanned

    Args:
        state: Current radar workflow state

    Returns:
        Unchanged state (terminal node)
    """
    logger.info("📝 LogAgent - Logging cycle results...")

    iterations = state.get("iterations", 0)
    strategies_tried = state.get("strategies_tried", [])
    papers_seen = state.get("papers_seen", [])

    logger.info(
        f"Cycle complete: {iterations} iterations, {len(strategies_tried)} strategies tried"
    )
    logger.info(f"Papers scanned: {len(papers_seen)}")
    logger.info(f"Strategies tried: {strategies_tried}")
    logger.info("No noteworthy papers found this cycle")

    return state
