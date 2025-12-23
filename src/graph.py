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

Our Workflow (Week 1 MVP):
    START → Discovery → Reader → Explainer → END

Future workflows will add:
- Parallel discovery sources (Twitter, HN, Citations)
- Curator for scoring/ranking
- Email generation
- Conditional branching (retry logic, error handling)

Example usage:
    graph = create_workflow()
    result = graph.invoke({
        "days_back": 1,
        "categories": ["cs.AI", "cs.LG"]
    })
    papers = result["explained_papers"]
"""

from typing import TypedDict, List, Optional, Annotated
from datetime import datetime
from langgraph.graph import StateGraph, END
from loguru import logger

from src.models.paper import Paper
from src.agents.discovery import discover_papers
from src.agents.reader import analyze_papers_batch
from src.agents.explainer import explain_papers_batch


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

    days_back: Optional[int]
    """How many days back to search for papers (default: 1)"""

    categories: Optional[List[str]]
    """Which arXiv categories to search (default: from config)"""

    max_papers: Optional[int]
    """Maximum number of papers to process (default: unlimited)"""

    # ========================================================================
    # Intermediate Fields - What agents produce
    # ========================================================================

    discovered_papers: Optional[List[Paper]]
    """Papers found by Discovery agent"""

    analyzed_papers: Optional[List[Paper]]
    """Papers analyzed by Reader agent (with main_claim, methodology, etc.)"""

    explained_papers: Optional[List[Paper]]
    """Papers explained by Explainer agent (with eli5_summary, etc.)"""

    # ========================================================================
    # Output Fields - Final results
    # ========================================================================

    final_papers: Optional[List[Paper]]
    """Final set of papers to include in digest (after scoring/filtering)"""

    # ========================================================================
    # Metadata Fields - Tracking and logging
    # ========================================================================

    errors: Optional[List[str]]
    """List of errors encountered during execution"""

    stats: Optional[dict]
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
        state["errors"].append(f"Discovery error: {str(e)}")
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
        state["errors"].append(f"Reader error: {str(e)}")
        state["analyzed_papers"] = []

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
            return state

        logger.info(f"Explaining {len(papers)} papers with Claude Sonnet...")

        # Call explainer agent
        # This will explain papers and save to database
        explained = explain_papers_batch(papers)

        logger.info(f"✅ Explanation complete: {len(explained)} papers")

        # Update state
        state["explained_papers"] = explained
        # For now, final_papers = explained_papers (no filtering yet)
        state["final_papers"] = explained

        # Update stats
        if "stats" not in state or state["stats"] is None:
            state["stats"] = {}
        state["stats"]["explained_count"] = len(explained)

    except Exception as e:
        logger.error(f"❌ Explainer node failed: {e}")
        if "errors" not in state or state["errors"] is None:
            state["errors"] = []
        state["errors"].append(f"Explainer error: {str(e)}")
        state["explained_papers"] = []
        state["final_papers"] = []

    return state


# ============================================================================
# Graph Construction
# ============================================================================

def create_workflow() -> StateGraph:
    """
    Create the LangGraph workflow.

    This defines the execution flow of our agent system.

    Week 1 MVP Flow:
        START → Discovery → Reader → Explainer → END

    Future expansions:
        - Add Curator node (scoring/ranking)
        - Add Email node (generate and send digest)
        - Add parallel discovery (Twitter, HN)
        - Add conditional edges (retry logic)

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

    # Define edges (what runs next)
    # set_entry_point: This is where execution starts
    workflow.set_entry_point("discovery")

    # Add sequential edges (A → B means "run B after A")
    workflow.add_edge("discovery", "reader")
    workflow.add_edge("reader", "explainer")

    # set_finish_point: This is where execution ends
    workflow.add_edge("explainer", END)

    # Compile the graph
    # This validates the graph and prepares it for execution
    app = workflow.compile()

    logger.info("✅ Workflow built successfully!")
    logger.info("Flow: START → Discovery → Reader → Explainer → END")

    return app


# ============================================================================
# Convenience functions
# ============================================================================

def run_full_pipeline(
    days_back: int = 1,
    categories: Optional[List[str]] = None,
    max_papers: Optional[int] = None,
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
        print(f"\n⚠️  Errors:")
        for error in errors:
            print(f"  - {error}")

    print("\n✅ Workflow test complete!")
