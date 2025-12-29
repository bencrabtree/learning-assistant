"""
ScannerAgent - Executes the search strategy.

This agent discovers papers based on the current strategy:
- recent_2_days: Last 2 days of arXiv papers
- hn_discovery: Discover new papers trending on HackerNews
- recent_7_days: Last 7 days
- recent_14_days: Last 14 days
- trending_social: Focus on HN/Twitter trending papers in database
- lower_threshold: Use relaxed scoring thresholds
"""

from loguru import logger

from src.agents.radar.state import RadarState
from src.database import get_db_session
from src.models.paper import Paper


def scanner_agent_node(state: RadarState) -> RadarState:
    """
    ScannerAgent: Executes the search strategy.

    Based on the selected strategy, discovers papers from:
    - arXiv API (for recent_X_days strategies)
    - HackerNews signals (for trending_social)
    - Database with relaxed thresholds (for lower_threshold)

    Args:
        state: Current radar workflow state

    Returns:
        Updated state with discovered papers
    """
    logger.info(
        """
╔═╗╔═╗╔═╗╔╗╔╔╗╔╔═╗╦═╗
╚═╗║  ╠═╣║║║║║║║╣ ╠╦╝
╚═╝╚═╝╩ ╩╝╚╝╝╚╝╚═╝╩╚═ AGENT
    """
    )
    logger.info("🔍 Executing search...")

    strategy = state.get("current_strategy", "recent_2_days")

    try:
        # Determine days_back based on strategy
        days_map = {
            "recent_2_days": 2,
            "hn_discovery": 7,  # Check last week of HN
            "recent_7_days": 7,
            "recent_14_days": 14,
            "trending_social": 7,
            "lower_threshold": 3,
        }
        days_back = days_map.get(strategy, 2)

        # Run discovery pipeline
        if strategy == "hn_discovery":
            # Social-first discovery: Find NEW papers trending on HackerNews
            from src.agents.discovery import discover_papers_from_hn

            logger.info("Discovering papers from HackerNews (min_score=20)")
            papers = discover_papers_from_hn(days_back=days_back, min_score=20)
            logger.info(f"Found {len(papers)} papers from HN")
            # Papers will be analyzed by the radar workflow's reader/explainer nodes
        elif strategy == "trending_social":
            # Focus on social signals - get HN trending papers from database
            from sqlalchemy import or_

            from src.trackers.hackernews import fetch_hn_signals

            hn_signals = fetch_hn_signals(days_back=days_back)
            logger.info(f"Found {len(hn_signals)} papers with HN signals")

            # Get papers from database that match these signals
            # HN strips version (2512.14693), DB has version (2512.14693v1)
            # Use LIKE matching to handle version suffix
            arxiv_ids = [s.get("arxiv_id") for s in hn_signals if s.get("arxiv_id")]
            with get_db_session() as db:
                if arxiv_ids:
                    # Match papers where arxiv_id starts with any of the HN ids
                    conditions = [Paper.arxiv_id.like(f"{aid}%") for aid in arxiv_ids]
                    papers = db.query(Paper).filter(or_(*conditions)).all()
                else:
                    papers = []
            logger.info(f"Matched {len(papers)} papers from database")
        else:
            # Standard discovery - import here to avoid circular imports
            from src.graph import run_full_pipeline

            result = run_full_pipeline(days_back=days_back, max_papers=30)
            papers = result.get("ranked_papers", []) or result.get("final_papers", []) or []

        logger.info(f"✅ ScannerAgent found {len(papers)} papers")
        state["current_papers"] = papers

        # Update stats
        if "cycle_stats" not in state or state["cycle_stats"] is None:
            state["cycle_stats"] = {}
        state["cycle_stats"][f"papers_found_{strategy}"] = len(papers)

    except Exception as e:
        logger.error(f"❌ ScannerAgent failed: {e}")
        state["current_papers"] = []
        if "errors" not in state or state["errors"] is None:
            state["errors"] = []
        state["errors"].append(f"Scanner error: {e!s}")

    return state
