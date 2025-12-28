"""
AssessorAgent (Radar) - Evaluates papers for breakthrough potential.

This agent wraps the existing AssessorAgent to work with the radar workflow.
It runs breakthrough assessment on unassessed papers.
"""

from loguru import logger

from src.agents.assessor import assess_papers_batch
from src.agents.radar.state import RadarState


def assessor_agent_node(state: RadarState) -> RadarState:
    """
    AssessorAgent: Evaluates papers for breakthrough potential.

    Uses the existing assess_papers_batch function to evaluate
    novelty, impact, evidence quality, and significance.

    Args:
        state: Current radar workflow state

    Returns:
        Updated state with assessed papers
    """
    logger.info("🎯 AssessorAgent - Evaluating breakthrough potential...")

    current_papers = state.get("current_papers", []) or []

    if not current_papers:
        logger.info("No papers to assess")
        return state

    try:
        # Filter to papers that need assessment
        unassessed = [p for p in current_papers if p.breakthrough_score is None]

        if unassessed:
            logger.info(f"Assessing {len(unassessed)} papers...")
            assessed_papers, _ = assess_papers_batch(unassessed)
            logger.info(f"✅ Assessed {len(assessed_papers)} papers")

            # Merge back - create lookup by arxiv_id
            assessed_map = {p.arxiv_id: p for p in assessed_papers}
            for i, paper in enumerate(current_papers):
                if paper.arxiv_id in assessed_map:
                    current_papers[i] = assessed_map[paper.arxiv_id]
        else:
            logger.info("All papers already assessed")

        state["current_papers"] = current_papers

    except Exception as e:
        logger.error(f"❌ AssessorAgent failed: {e}")
        if "errors" not in state or state["errors"] is None:
            state["errors"] = []
        state["errors"].append(f"Assessor error: {e!s}")

    return state
