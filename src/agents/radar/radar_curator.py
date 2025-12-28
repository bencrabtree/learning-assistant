"""
CuratorAgent (Radar) - Scores and ranks papers.

This agent wraps the existing CuratorAgent to work with the radar workflow.
It applies multi-signal scoring using the existing curator.
"""

from loguru import logger

from src.agents.curator import curate_papers_batch
from src.agents.radar.state import RadarState


def curator_agent_node(state: RadarState) -> RadarState:
    """
    CuratorAgent: Scores and ranks papers.

    Uses the existing curate_papers_batch function to apply
    multi-signal scoring (interest match + social proof + citations + breakthrough).

    Args:
        state: Current radar workflow state

    Returns:
        Updated state with curated/ranked papers
    """
    logger.info("📊 CuratorAgent - Scoring and ranking...")

    current_papers = state.get("current_papers", []) or []

    if not current_papers:
        logger.info("No papers to curate")
        return state

    try:
        ranked_papers = curate_papers_batch(current_papers)
        logger.info(f"✅ Curated {len(ranked_papers)} papers")

        state["current_papers"] = ranked_papers

    except Exception as e:
        logger.error(f"❌ CuratorAgent failed: {e}")
        if "errors" not in state or state["errors"] is None:
            state["errors"] = []
        state["errors"].append(f"Curator error: {e!s}")

    return state
