"""
DecisionAgent - Decides whether to notify, expand, or stop.

This agent evaluates papers against thresholds and determines:
- NOTIFY: Found noteworthy papers, send notification
- EXPAND: No noteworthy papers, try next strategy
- DONE: Exhausted strategies or max iterations, stop
"""

from loguru import logger

from src.agents.radar.state import RADAR_STRATEGIES, RadarState
from src.models.paper import Paper


def _get_social_score(paper: Paper) -> float:
    """Get combined social score from HN and Twitter signals.

    Uses pre-calculated social scores stored in score_components.
    Returns the maximum of HN and Twitter scores (not sum, to avoid double-counting).
    """
    if not paper.score_components:
        return 0.0

    # Use pre-calculated scores from signal node
    hn_social = paper.score_components.get("hn_social_score", 0.0)
    twitter_social = paper.score_components.get("twitter_social_score", 0.0)

    # Return max score (a paper trending on either platform is noteworthy)
    return max(hn_social, twitter_social)


def decision_agent_node(state: RadarState) -> RadarState:
    """
    DecisionAgent: Decides whether to notify, expand, or stop.

    Evaluates each paper against thresholds to determine noteworthiness:
    - Breakthrough score > threshold
    - High relevance (> 0.8)
    - Trending + relevant (social + relevance combo)

    Args:
        state: Current radar workflow state

    Returns:
        Updated state with noteworthy papers and strategies_tried
    """
    logger.info(
        """
╔╦╗╔═╗╔═╗╦╔═╗╦╔═╗╔╗╔
 ║║║╣ ║  ║╚═╗║║ ║║║║
═╩╝╚═╝╚═╝╩╚═╝╩╚═╝╝╚╝ AGENT
    """
    )
    logger.info("🤔 Evaluating findings...")

    current_papers = state.get("current_papers", []) or []
    noteworthy = list(state.get("noteworthy_papers", []))

    breakthrough_threshold = state.get("breakthrough_threshold", 0.6)
    relevance_threshold = state.get("relevance_threshold", 0.5)
    social_threshold = state.get("social_threshold", 0.3)
    current_strategy = state.get("current_strategy", "")

    # Lower thresholds if using that strategy
    if current_strategy == "lower_threshold":
        breakthrough_threshold *= 0.8
        relevance_threshold *= 0.8

    # Check each paper for noteworthiness
    for paper in current_papers:
        is_noteworthy = False
        reasons = []

        # Check breakthrough
        if paper.breakthrough_score and paper.breakthrough_score >= breakthrough_threshold:
            is_noteworthy = True
            reasons.append(f"breakthrough={paper.breakthrough_score:.0%}")

        # Check high relevance
        if paper.relevance_score and paper.relevance_score >= 0.8:
            is_noteworthy = True
            reasons.append(f"high_relevance={paper.relevance_score:.0%}")

        # Check social + relevance combo
        social_score = _get_social_score(paper)
        if (
            social_score >= social_threshold
            and paper.relevance_score
            and paper.relevance_score >= relevance_threshold
        ):
            is_noteworthy = True
            reasons.append("trending+relevant")

        if is_noteworthy:
            logger.info(f"📌 Noteworthy: {paper.title[:50]}... ({', '.join(reasons)})")
            noteworthy.append(paper)

    state["noteworthy_papers"] = noteworthy

    # Update strategies tried
    strategies_tried = list(state.get("strategies_tried", []))
    if current_strategy and current_strategy not in strategies_tried:
        strategies_tried.append(current_strategy)
    state["strategies_tried"] = strategies_tried

    logger.info(f"Found {len(noteworthy)} noteworthy papers total")

    return state


def route_decision(state: RadarState) -> str:
    """
    Route from DecisionAgent to next node.

    This is the conditional routing function used by LangGraph
    to determine the next step in the workflow.

    Returns:
        "notify" - Found noteworthy papers
        "expand" - No papers, try next strategy
        "done" - Max iterations or strategies exhausted
    """
    noteworthy = state.get("noteworthy_papers", [])
    iterations = state.get("iterations", 0)
    max_iterations = state.get("max_iterations", 3)
    strategies_tried = state.get("strategies_tried", [])

    if noteworthy:
        logger.info("Decision: NOTIFY - Found noteworthy papers")
        return "notify"
    elif iterations >= max_iterations:
        logger.info("Decision: DONE - Max iterations reached")
        return "done"
    elif len(strategies_tried) >= len(RADAR_STRATEGIES):
        logger.info("Decision: DONE - All strategies exhausted")
        return "done"
    else:
        logger.info("Decision: EXPAND - Trying next strategy")
        return "expand"
