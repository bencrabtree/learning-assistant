"""
StrategyAgent - Selects the next search strategy.

This agent decides which search strategy to use based on:
- What strategies have already been tried
- Whether we're in the first iteration or expanding
"""

from loguru import logger

from src.agents.radar.state import RADAR_STRATEGIES, RadarState


def strategy_agent_node(state: RadarState) -> RadarState:
    """
    StrategyAgent: Selects the next search strategy.

    Strategies are tried in order:
    1. recent_2_days - Last 2 days of arXiv papers
    2. recent_7_days - Last 7 days
    3. recent_14_days - Last 14 days
    4. trending_social - Focus on HN/Twitter trending
    5. lower_threshold - Relax scoring thresholds

    Args:
        state: Current radar workflow state

    Returns:
        Updated state with selected strategy
    """
    logger.info(
        """
╔═╗╔╦╗╦═╗╔═╗╔╦╗╔═╗╔═╗╦ ╦
╚═╗ ║ ╠╦╝╠═╣ ║ ║╣ ║ ╦╚╦╝
╚═╝ ╩ ╩╚═╩ ╩ ╩ ╚═╝╚═╝ ╩  AGENT
    """
    )
    logger.info("🎯 Selecting search strategy...")

    strategies_tried = state.get("strategies_tried", [])
    iterations = state.get("iterations", 0)

    # Find next untried strategy
    next_strategy = None
    for strategy in RADAR_STRATEGIES:
        if strategy not in strategies_tried:
            next_strategy = strategy
            break

    if next_strategy is None:
        # All strategies exhausted, use last one
        next_strategy = RADAR_STRATEGIES[-1]
        logger.warning("All strategies exhausted, using fallback")

    logger.info(f"Selected strategy: {next_strategy} (iteration {iterations + 1})")

    state["current_strategy"] = next_strategy
    state["iterations"] = iterations + 1

    return state
