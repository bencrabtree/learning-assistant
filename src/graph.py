"""
LangGraph Workflow - Agent Orchestration

This module defines the LangGraph workflow that orchestrates all our agents.

Key Concepts:
- StateGraph = A graph where nodes share a common state
- Node = A function that does work and updates state
- Edge = Defines what runs next
- State = A TypedDict that flows through the graph

LangGraph Benefits:
- Declarative workflow definition (easy to visualize)
- Automatic state management (no manual passing)
- Built-in error handling
- Easy to modify (add/remove agents)
- Clear execution flow

Our Workflow (Milestone 2):
    START → Discovery → Reader → Explainer → Signals → Assessor → Curator → END

Milestone 2 additions:
- Social signals (HackerNews engagement)
- Breakthrough detection (Claude assessment)
- Multi-signal scoring and ranking

Example usage:
    graph = create_workflow()
    result = graph.invoke({
        "days_back": 1,
        "categories": ["cs.AI", "cs.LG"]
    })
    papers = result["final_papers"]
"""

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from loguru import logger

from src.agents.assessor import assess_papers_batch
from src.agents.curator import curate_papers_batch
from src.agents.discovery import discover_papers
from src.agents.explainer import explain_papers_batch
from src.agents.reader import analyze_papers_batch
from src.database import get_db_session
from src.models.paper import Paper
from src.trackers.hackernews import fetch_hn_signals
from src.trackers.twitter import fetch_twitter_signals

# ============================================================================
# State Definition
# ============================================================================


class AgentState(TypedDict):
    """
    Shared state that flows through the agent workflow.

    This is the "whiteboard" where agents read inputs and write outputs.

    How LangGraph handles state:
    1. START node receives initial state
    2. Each node reads from state, does work, writes to state
    3. State flows to next node
    4. END node receives final state

    Type hints:
    - TypedDict = Dictionary with specific keys and types
    - Optional[X] = Can be None or type X
    - List[X] = List containing type X
    - Annotated[X, ...] = Type X with metadata (for LangGraph merging)

    State fields explained:
    - Input fields: What the user provides
    - Intermediate fields: What agents produce
    - Output fields: Final results
    - Metadata fields: Tracking and logging
    """

    # ========================================================================
    # Input Fields - What the user provides
    # ========================================================================

    days_back: int | None
    """How many days back to search for papers (default: 1)"""

    categories: list[str] | None
    """Which arXiv categories to search (default: from config)"""

    max_papers: int | None
    """Maximum number of papers to process (default: unlimited)"""

    # ========================================================================
    # Intermediate Fields - What agents produce
    # ========================================================================

    discovered_papers: list[Paper] | None
    """Papers found by Discovery agent"""

    analyzed_papers: list[Paper] | None
    """Papers analyzed by Reader agent (with main_claim, methodology, etc.)"""

    explained_papers: list[Paper] | None
    """Papers explained by Explainer agent (with eli5_summary, etc.)"""

    # ========================================================================
    # Social Signal Fields - From signal trackers (Milestone 2)
    # ========================================================================

    hn_signals: list[dict[str, Any]] | None
    """HackerNews engagement data for papers"""

    twitter_signals: list[dict[str, Any]] | None
    """Twitter engagement data for papers"""

    # ========================================================================
    # Assessment Fields - From assessor agent (Milestone 2)
    # ========================================================================

    assessments: list[dict[str, Any]] | None
    """Breakthrough assessments for papers"""

    assessed_papers: list[Paper] | None
    """Papers after breakthrough assessment"""

    # ========================================================================
    # Output Fields - Final results
    # ========================================================================

    ranked_papers: list[Paper] | None
    """Papers after multi-signal scoring and ranking"""

    final_papers: list[Paper] | None
    """Final set of papers to include in digest (after scoring/filtering)"""

    # ========================================================================
    # Metadata Fields - Tracking and logging
    # ========================================================================

    errors: list[str] | None
    """List of errors encountered during execution"""

    stats: dict | None
    """Statistics about the run (counts, timing, costs)"""


# ============================================================================
# Node Functions - Each node does specific work
# ============================================================================


def discovery_node(state: AgentState) -> AgentState:
    """
    Discovery Node - Find new papers from arXiv.

    This is the first node in the workflow. It:
    1. Reads input parameters from state (days_back, categories)
    2. Calls the Discovery agent
    3. Writes results to state (discovered_papers)
    4. Returns updated state

    LangGraph will automatically:
    - Pass the current state to this function
    - Merge the returned state with the existing state
    - Move to the next node

    Args:
        state: Current workflow state

    Returns:
        Updated state with discovered_papers

    Example:
        state = {"days_back": 1, "categories": ["cs.AI"]}
        new_state = discovery_node(state)
        # new_state now has "discovered_papers" field
    """
    logger.info("🔍 Discovery Node - Finding papers...")

    try:
        # Get parameters from state (with defaults)
        days_back = state.get("days_back", 1)
        categories = state.get("categories", None)
        max_papers = state.get("max_papers", None)

        logger.info(f"Parameters: days_back={days_back}, categories={categories}")

        # Call discovery agent
        papers = discover_papers(
            days_back=days_back,
            categories=categories,
        )

        # Limit if max_papers specified
        if max_papers and len(papers) > max_papers:
            logger.info(f"Limiting to {max_papers} papers (found {len(papers)})")
            papers = papers[:max_papers]

        logger.info(f"✅ Discovery complete: {len(papers)} papers")

        # Update state
        state["discovered_papers"] = papers

        # Initialize stats
        if "stats" not in state or state["stats"] is None:
            state["stats"] = {}
        state["stats"]["discovered_count"] = len(papers)

    except Exception as e:
        logger.error(f"❌ Discovery node failed: {e}")
        if "errors" not in state or state["errors"] is None:
            state["errors"] = []
        state["errors"].append(f"Discovery error: {e!s}")
        # Set empty list so downstream nodes can handle gracefully
        state["discovered_papers"] = []

    return state


def reader_node(state: AgentState) -> AgentState:
    """
    Reader Node - Analyze papers with Claude.

    This node:
    1. Reads discovered_papers from state
    2. Calls the Reader agent to analyze each paper
    3. Writes results to state (analyzed_papers)

    The Reader agent uses Claude Haiku to extract:
    - Main claim
    - Methodology
    - Key results
    - Technical concepts
    - Limitations

    Args:
        state: Current workflow state

    Returns:
        Updated state with analyzed_papers
    """
    logger.info("📖 Reader Node - Analyzing papers...")

    try:
        # Get papers from previous node
        papers = state.get("discovered_papers", [])

        if not papers:
            logger.warning("No papers to analyze")
            state["analyzed_papers"] = []
            if "stats" not in state or state["stats"] is None:
                state["stats"] = {}
            state["stats"]["analyzed_count"] = 0
            return state

        logger.info(f"Analyzing {len(papers)} papers with Claude Haiku...")

        # Call reader agent
        # This will analyze papers and save to database
        analyzed = analyze_papers_batch(papers)

        logger.info(f"✅ Analysis complete: {len(analyzed)} papers")

        # Update state
        state["analyzed_papers"] = analyzed

        # Update stats
        if "stats" not in state or state["stats"] is None:
            state["stats"] = {}
        state["stats"]["analyzed_count"] = len(analyzed)

    except Exception as e:
        logger.error(f"❌ Reader node failed: {e}")
        if "errors" not in state or state["errors"] is None:
            state["errors"] = []
        state["errors"].append(f"Reader error: {e!s}")
        state["analyzed_papers"] = []
        if "stats" not in state or state["stats"] is None:
            state["stats"] = {}
        state["stats"]["analyzed_count"] = 0

    return state


def explainer_node(state: AgentState) -> AgentState:
    """
    Explainer Node - Generate learning-friendly explanations.

    This node:
    1. Reads analyzed_papers from state
    2. Calls the Explainer agent
    3. Writes results to state (explained_papers)

    The Explainer agent uses Claude Sonnet to generate:
    - ELI5 summary
    - Key insight
    - Learning questions
    - Prerequisites
    - Related concepts

    Args:
        state: Current workflow state

    Returns:
        Updated state with explained_papers
    """
    logger.info("💡 Explainer Node - Creating explanations...")

    try:
        # Get papers from previous node
        papers = state.get("analyzed_papers", [])

        if not papers:
            logger.warning("No papers to explain")
            state["explained_papers"] = []
            state["final_papers"] = []
            if "stats" not in state or state["stats"] is None:
                state["stats"] = {}
            state["stats"]["explained_count"] = 0
            return state

        logger.info(f"Explaining {len(papers)} papers with Claude Sonnet...")

        # Call explainer agent
        # This will explain papers and save to database
        explained = explain_papers_batch(papers)

        logger.info(f"✅ Explanation complete: {len(explained)} papers")

        # Update state
        state["explained_papers"] = explained

        # Update stats
        if "stats" not in state or state["stats"] is None:
            state["stats"] = {}
        state["stats"]["explained_count"] = len(explained)

    except Exception as e:
        logger.error(f"❌ Explainer node failed: {e}")
        if "errors" not in state or state["errors"] is None:
            state["errors"] = []
        state["errors"].append(f"Explainer error: {e!s}")
        state["explained_papers"] = []

    return state


def signal_node(state: AgentState) -> AgentState:
    """
    Signal Node - Fetch social signals from HackerNews and Twitter.

    This node:
    1. Fetches HN signals for arXiv papers
    2. Fetches Twitter signals (if configured)
    3. Matches signals to discovered papers
    4. Stores signal data in paper.score_components

    Args:
        state: Current workflow state

    Returns:
        Updated state with hn_signals and twitter_signals
    """
    logger.info("📡 Signal Node - Fetching social signals...")

    try:
        papers = state.get("explained_papers", [])
        days_back = state.get("days_back", 7)

        if not papers:
            logger.warning("No papers to fetch signals for")
            state["hn_signals"] = []
            state["twitter_signals"] = []
            return state

        # Fetch HN signals
        hn_signals = fetch_hn_signals(days_back=days_back)
        logger.info(f"Found {len(hn_signals)} papers mentioned on HN")

        # Fetch Twitter signals (optional - requires API key)
        twitter_signals = fetch_twitter_signals(days_back=days_back)
        if twitter_signals:
            logger.info(f"Found {len(twitter_signals)} papers mentioned on Twitter")

        # Create lookups by arxiv_id
        hn_map = {s["arxiv_id"]: s for s in hn_signals}
        twitter_map = {s["arxiv_id"]: s for s in twitter_signals}

        # Match signals to papers and update score_components
        hn_matched = 0
        twitter_matched = 0

        with get_db_session() as db:
            for paper in papers:
                if paper.score_components is None:
                    paper.score_components = {}

                # Match HN signals
                if paper.arxiv_id in hn_map:
                    signal = hn_map[paper.arxiv_id]
                    paper.score_components["hn_score"] = signal.get("score", 0)
                    paper.score_components["hn_comments"] = signal.get("comments_count", 0)
                    paper.score_components["hn_social_score"] = signal.get("social_score", 0.0)
                    hn_matched += 1

                # Match Twitter signals
                if paper.arxiv_id in twitter_map:
                    signal = twitter_map[paper.arxiv_id]
                    paper.score_components["twitter_likes"] = signal.get("likes", 0)
                    paper.score_components["twitter_retweets"] = signal.get("retweets", 0)
                    paper.score_components["twitter_social_score"] = signal.get("social_score", 0.0)
                    paper.score_components["twitter_is_lab"] = signal.get("is_lab_account", False)
                    twitter_matched += 1

                # Update in database if any signals matched
                if paper.arxiv_id in hn_map or paper.arxiv_id in twitter_map:
                    db_paper = db.query(Paper).filter_by(arxiv_id=paper.arxiv_id).first()
                    if db_paper:
                        db_paper.score_components = paper.score_components

        logger.info(f"✅ Matched {hn_matched} papers with HN, {twitter_matched} with Twitter")

        state["hn_signals"] = hn_signals
        state["twitter_signals"] = twitter_signals
        if "stats" not in state or state["stats"] is None:
            state["stats"] = {}
        state["stats"]["hn_signals_count"] = len(hn_signals)
        state["stats"]["hn_matched_count"] = hn_matched
        state["stats"]["twitter_signals_count"] = len(twitter_signals)
        state["stats"]["twitter_matched_count"] = twitter_matched

    except Exception as e:
        logger.error(f"❌ Signal node failed: {e}")
        if "errors" not in state or state["errors"] is None:
            state["errors"] = []
        state["errors"].append(f"Signal error: {e!s}")
        state["hn_signals"] = []
        state["twitter_signals"] = []

    return state


def assessor_node(state: AgentState) -> AgentState:
    """
    Assessor Node - Evaluate papers for breakthrough potential.

    This node:
    1. Reads explained papers from state
    2. Runs breakthrough assessment with Claude
    3. Stores breakthrough_score on papers

    The Assessor agent evaluates:
    - Novelty (how original is the approach)
    - Impact (potential to change the field)
    - Evidence (quality of experimental validation)
    - Significance (importance of problem being solved)

    Args:
        state: Current workflow state

    Returns:
        Updated state with assessments and assessed_papers
    """
    logger.info("🎯 Assessor Node - Evaluating breakthrough potential...")

    try:
        papers = state.get("explained_papers", [])

        if not papers:
            logger.warning("No papers to assess")
            state["assessments"] = []
            state["assessed_papers"] = []
            return state

        logger.info(f"Assessing {len(papers)} papers for breakthrough potential...")

        # Run batch assessment
        assessed_papers, assessments = assess_papers_batch(papers)

        breakthrough_count = sum(1 for a in assessments if a.get("is_breakthrough", False))
        logger.info(
            f"✅ Assessment complete: {breakthrough_count}/{len(papers)} breakthroughs detected"
        )

        state["assessments"] = assessments
        state["assessed_papers"] = assessed_papers

        if "stats" not in state or state["stats"] is None:
            state["stats"] = {}
        state["stats"]["assessed_count"] = len(assessed_papers)
        state["stats"]["breakthrough_count"] = breakthrough_count

    except Exception as e:
        logger.error(f"❌ Assessor node failed: {e}")
        if "errors" not in state or state["errors"] is None:
            state["errors"] = []
        state["errors"].append(f"Assessor error: {e!s}")
        state["assessments"] = []
        state["assessed_papers"] = state.get("explained_papers", [])

    return state


def curator_node(state: AgentState) -> AgentState:
    """
    Curator Node - Score and rank papers using multi-signal scoring.

    This node:
    1. Reads assessed papers from state
    2. Calculates combined scores from all signals
    3. Ranks papers by relevance
    4. Selects final papers for digest

    Scoring weights:
    - Interest match: 25%
    - Social proof: 25%
    - Citation score: 20%
    - Breakthrough: 30%

    Args:
        state: Current workflow state

    Returns:
        Updated state with ranked_papers and final_papers
    """
    logger.info("📊 Curator Node - Scoring and ranking papers...")

    try:
        papers = state.get("assessed_papers", [])

        if not papers:
            logger.warning("No papers to curate")
            state["ranked_papers"] = []
            state["final_papers"] = []
            return state

        logger.info(f"Curating {len(papers)} papers with multi-signal scoring...")

        # Run curator (scores, ranks, saves)
        ranked_papers = curate_papers_batch(papers)

        logger.info(f"✅ Curation complete: {len(ranked_papers)} papers ranked")

        # Log top papers
        if ranked_papers:
            logger.info("Top 5 papers by relevance:")
            for i, paper in enumerate(ranked_papers[:5], 1):
                score = paper.relevance_score or 0
                logger.info(f"  {i}. [{score:.2f}] {paper.title[:60]}...")

        state["ranked_papers"] = ranked_papers
        state["final_papers"] = ranked_papers

        if "stats" not in state or state["stats"] is None:
            state["stats"] = {}
        state["stats"]["curated_count"] = len(ranked_papers)

    except Exception as e:
        logger.error(f"❌ Curator node failed: {e}")
        if "errors" not in state or state["errors"] is None:
            state["errors"] = []
        state["errors"].append(f"Curator error: {e!s}")
        state["ranked_papers"] = []
        state["final_papers"] = state.get("assessed_papers", [])

    return state


# ============================================================================
# Graph Construction
# ============================================================================


def create_workflow() -> StateGraph:
    """
    Create the LangGraph workflow.

    This defines the execution flow of our agent system.

    Milestone 2 Flow:
        START → Discovery → Reader → Explainer → Signals → Assessor → Curator → END

    The workflow:
    1. Discovery: Find papers from arXiv
    2. Reader: Analyze papers with Claude Haiku
    3. Explainer: Generate ELI5 explanations with Claude Sonnet
    4. Signals: Fetch HackerNews social signals
    5. Assessor: Evaluate breakthrough potential
    6. Curator: Multi-signal scoring and ranking

    Returns:
        Compiled StateGraph ready to execute

    Example:
        workflow = create_workflow()
        result = workflow.invoke({"days_back": 1})
        papers = result["final_papers"]
    """
    logger.info("🏗️  Building LangGraph workflow...")

    # Create the graph with our state type
    workflow = StateGraph(AgentState)

    # Add nodes (each node is a function that updates state)
    workflow.add_node("discovery", discovery_node)
    workflow.add_node("reader", reader_node)
    workflow.add_node("explainer", explainer_node)
    workflow.add_node("signals", signal_node)
    workflow.add_node("assessor", assessor_node)
    workflow.add_node("curator", curator_node)

    # Define edges (what runs next)
    # set_entry_point: This is where execution starts
    workflow.set_entry_point("discovery")

    # Add sequential edges (A → B means "run B after A")
    workflow.add_edge("discovery", "reader")
    workflow.add_edge("reader", "explainer")
    workflow.add_edge("explainer", "signals")
    workflow.add_edge("signals", "assessor")
    workflow.add_edge("assessor", "curator")

    # set_finish_point: This is where execution ends
    workflow.add_edge("curator", END)

    # Compile the graph
    # This validates the graph and prepares it for execution
    app = workflow.compile()

    logger.info("✅ Workflow built successfully!")
    logger.info("Flow: START → Discovery → Reader → Explainer → Signals → Assessor → Curator → END")

    return app


# ============================================================================
# Convenience functions
# ============================================================================


def run_full_pipeline(
    days_back: int = 1,
    categories: list[str] | None = None,
    max_papers: int | None = None,
) -> AgentState:
    """
    Run the full paper discovery and analysis pipeline.

    This is a convenience function that:
    1. Creates the workflow
    2. Sets up initial state
    3. Executes the graph
    4. Returns final state

    Args:
        days_back: How many days back to search
        categories: Which arXiv categories to search
        max_papers: Maximum number of papers to process

    Returns:
        Final state with all results

    Example:
        result = run_full_pipeline(days_back=1, max_papers=5)
        for paper in result["final_papers"]:
            print(f"- {paper.title}")
            print(f"  {paper.eli5_summary}")
    """
    logger.info("🚀 Starting full pipeline...")
    logger.info(f"Parameters: days_back={days_back}, max_papers={max_papers}")

    # Create workflow
    workflow = create_workflow()

    # Set up initial state
    initial_state: AgentState = {
        "days_back": days_back,
        "categories": categories,
        "max_papers": max_papers,
        "discovered_papers": None,
        "analyzed_papers": None,
        "explained_papers": None,
        "hn_signals": None,
        "twitter_signals": None,
        "assessments": None,
        "assessed_papers": None,
        "ranked_papers": None,
        "final_papers": None,
        "errors": [],
        "stats": {},
    }

    # Execute workflow
    try:
        final_state = workflow.invoke(initial_state)

        # Log results
        logger.info("✅ Pipeline complete!")
        logger.info(f"Stats: {final_state.get('stats', {})}")

        if final_state.get("errors"):
            logger.warning(f"Errors encountered: {final_state['errors']}")

        return final_state

    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
        raise


def run_discovery_only_pipeline(
    days_back: int = 1,
    categories: list[str] | None = None,
    max_papers: int | None = None,
) -> AgentState:
    """
    Run discovery pipeline without analysis.

    This workflow:
    1. Discovers papers from arXiv
    2. Saves them to database
    3. Returns without analyzing

    Use this when you just want to find and store papers for later processing.

    Args:
        days_back: How many days back to search
        categories: Which arXiv categories to search
        max_papers: Maximum number of papers to process

    Returns:
        State with discovered papers

    Example:
        result = run_discovery_only_pipeline(days_back=7)
        papers = result["discovered_papers"]
        print(f"Found {len(papers)} papers")
    """
    logger.info("🚀 Starting discovery-only pipeline...")

    # Create a discovery-only workflow
    workflow = StateGraph(AgentState)
    workflow.add_node("discovery", discovery_node)

    workflow.set_entry_point("discovery")
    workflow.add_edge("discovery", END)

    app = workflow.compile()

    # Set up initial state
    initial_state: AgentState = {
        "days_back": days_back,
        "categories": categories,
        "max_papers": max_papers,
        "discovered_papers": None,
        "analyzed_papers": None,
        "explained_papers": None,
        "hn_signals": None,
        "twitter_signals": None,
        "assessments": None,
        "assessed_papers": None,
        "ranked_papers": None,
        "final_papers": None,
        "errors": [],
        "stats": {},
    }

    # Execute workflow
    try:
        final_state = app.invoke(initial_state)

        logger.info("✅ Discovery pipeline complete!")
        logger.info(f"Stats: {final_state.get('stats', {})}")

        if final_state.get("errors"):
            logger.warning(f"Errors encountered: {final_state['errors']}")

        return final_state

    except Exception as e:
        logger.error(f"❌ Discovery pipeline failed: {e}")
        raise


def run_analysis_pipeline() -> AgentState:
    """
    Run analysis pipeline on existing papers in database.

    This workflow:
    1. Loads papers from database that haven't been analyzed
    2. Runs Reader agent
    3. Runs Explainer agent
    4. Returns results

    Use this when you want to analyze papers that are already discovered
    but haven't been processed yet.

    Returns:
        Final state with analyzed and explained papers

    Example:
        result = run_analysis_pipeline()
        count = result["stats"]["analyzed_count"]
        print(f"Analyzed {count} papers")
    """
    logger.info("🚀 Starting analysis pipeline...")

    # Load unanalyzed papers from database
    with get_db_session() as db:
        unanalyzed = db.query(Paper).filter(Paper.analyzed_at.is_(None)).all()

    if not unanalyzed:
        logger.info("No unanalyzed papers found")
        return {
            "days_back": None,
            "categories": None,
            "max_papers": None,
            "discovered_papers": [],
            "analyzed_papers": [],
            "explained_papers": [],
            "hn_signals": [],
            "twitter_signals": [],
            "assessments": [],
            "assessed_papers": [],
            "ranked_papers": [],
            "final_papers": [],
            "errors": [],
            "stats": {
                "discovered_count": 0,
                "analyzed_count": 0,
                "explained_count": 0,
            },
        }

    logger.info(f"Found {len(unanalyzed)} unanalyzed papers")

    # Create a simplified workflow (skip discovery)
    workflow = StateGraph(AgentState)
    workflow.add_node("reader", reader_node)
    workflow.add_node("explainer", explainer_node)

    workflow.set_entry_point("reader")
    workflow.add_edge("reader", "explainer")
    workflow.add_edge("explainer", END)

    app = workflow.compile()

    # Set up initial state with existing papers
    initial_state: AgentState = {
        "days_back": None,
        "categories": None,
        "max_papers": None,
        "discovered_papers": unanalyzed,  # Use existing papers
        "analyzed_papers": None,
        "explained_papers": None,
        "hn_signals": None,
        "twitter_signals": None,
        "assessments": None,
        "assessed_papers": None,
        "ranked_papers": None,
        "final_papers": None,
        "errors": [],
        "stats": {"discovered_count": len(unanalyzed)},
    }

    # Execute workflow
    try:
        final_state = app.invoke(initial_state)

        logger.info("✅ Analysis pipeline complete!")
        logger.info(f"Stats: {final_state.get('stats', {})}")

        if final_state.get("errors"):
            logger.warning(f"Errors encountered: {final_state['errors']}")

        return final_state

    except Exception as e:
        logger.error(f"❌ Analysis pipeline failed: {e}")
        raise


if __name__ == "__main__":
    # Test the workflow
    print("Testing LangGraph Workflow...")
    print("=" * 80)

    # Run with limited papers for testing
    result = run_full_pipeline(days_back=1, max_papers=2)

    print("\n📊 RESULTS:")
    print("=" * 80)

    stats = result.get("stats", {})
    print(f"Discovered: {stats.get('discovered_count', 0)} papers")
    print(f"Analyzed:   {stats.get('analyzed_count', 0)} papers")
    print(f"Explained:  {stats.get('explained_count', 0)} papers")

    final_papers = result.get("final_papers", [])
    print(f"\n📚 Final Papers ({len(final_papers)}):")
    for i, paper in enumerate(final_papers, 1):
        print(f"\n{i}. {paper.title}")
        if paper.eli5_summary:
            print(f"   💡 {paper.eli5_summary[:100]}...")

    errors = result.get("errors", [])
    if errors:
        print("\n⚠️  Errors:")
        for error in errors:
            print(f"  - {error}")

    print("\n✅ Workflow test complete!")
