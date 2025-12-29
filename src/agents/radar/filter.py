"""
FilterAgent - Removes duplicates and already-seen papers.

This agent:
- Filters out papers we've already processed
- Updates the papers_seen list
- Ensures no duplicate processing across iterations
"""

from loguru import logger

from src.agents.radar.state import RadarState


def filter_agent_node(state: RadarState) -> RadarState:
    """
    FilterAgent: Removes duplicates and already-seen papers.

    Maintains the papers_seen set across iterations to prevent
    re-processing the same papers when expanding search.

    Args:
        state: Current radar workflow state

    Returns:
        Updated state with filtered papers and updated papers_seen
    """
    logger.info(
        """
╔═╗╦╦ ╔╦╗╔═╗╦═╗
╠╣ ║║  ║ ║╣ ╠╦╝
╚  ╩╩═╝╩ ╚═╝╩╚═ AGENT
    """
    )
    logger.info("🔎 Removing duplicates...")

    current_papers = state.get("current_papers", []) or []
    papers_seen = set(state.get("papers_seen", []))

    # Filter out already-seen papers
    new_papers = []
    for paper in current_papers:
        if paper.arxiv_id not in papers_seen:
            new_papers.append(paper)
            papers_seen.add(paper.arxiv_id)

    filtered_count = len(current_papers) - len(new_papers)
    logger.info(f"Filtered {filtered_count} duplicates, {len(new_papers)} new papers")

    state["current_papers"] = new_papers
    state["papers_seen"] = list(papers_seen)

    return state
