# Milestone 4: Truly Agentic LangGraph Workflow

**Status:** In Progress
**Priority:** High - Core learning objective
**Dependencies:** Milestone 3 (Research Radar)

---

## Overview

Refactor the Research Radar to use LangGraph's agentic patterns. The radar loop becomes a proper LangGraph workflow with conditional edges, iterative search, and autonomous decision-making.

**The Problem:**
- Current radar is just Python code calling `run_full_pipeline()`
- The "agentic" logic (continue vs notify) is outside the graph
- Not leveraging LangGraph's power (conditional routing, state evolution)

**The Solution:**
- Make the radar loop itself a LangGraph workflow
- Use conditional edges for decision points
- State accumulates across iterations (seen papers, strategies tried)
- The graph decides when to stop based on what it finds

---

## Agentic Workflow Architecture

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AGENTIC RADAR WORKFLOW                               │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         DISCOVERY PHASE                              │   │
│  │                                                                      │   │
│  │   START ──► StrategyAgent ──► ScannerAgent ──► FilterAgent          │   │
│  │                  │                                    │              │   │
│  │                  │ (selects search                    │ (removes     │   │
│  │                  │  strategy)                         │  duplicates) │   │
│  └──────────────────┼────────────────────────────────────┼──────────────┘   │
│                     │                                    │                  │
│  ┌──────────────────┼────────────────────────────────────┼──────────────┐   │
│  │                  ▼        ASSESSMENT PHASE            ▼              │   │
│  │                                                                      │   │
│  │              AssessorAgent ──────────────► CuratorAgent              │   │
│  │                  │                              │                    │   │
│  │                  │ (breakthrough                │ (scores &          │   │
│  │                  │  detection)                  │  ranks)            │   │
│  └──────────────────┼──────────────────────────────┼────────────────────┘   │
│                     │                              │                        │
│  ┌──────────────────┼──────────────────────────────┼────────────────────┐   │
│  │                  ▼        DECISION PHASE        ▼                    │   │
│  │                                                                      │   │
│  │                      DecisionAgent                                   │   │
│  │                           │                                          │   │
│  │              ┌────────────┼────────────┐                             │   │
│  │              ▼            ▼            ▼                             │   │
│  │          [NOTIFY]    [EXPAND]     [DONE]                             │   │
│  │              │            │            │                             │   │
│  │              ▼            ▼            ▼                             │   │
│  │        NotifierAgent  StrategyAgent  LogAgent                        │   │
│  │              │            │            │                             │   │
│  │              ▼            │            ▼                             │   │
│  │            END      (loop back)      END                             │   │
│  │                     to DISCOVERY                                     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Detailed Agent Responsibilities

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AGENT ROSTER                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │  StrategyAgent  │    │  ScannerAgent   │    │  FilterAgent    │         │
│  ├─────────────────┤    ├─────────────────┤    ├─────────────────┤         │
│  │ • Selects next  │    │ • Executes      │    │ • Removes seen  │         │
│  │   search        │    │   arXiv search  │    │   papers        │         │
│  │   strategy      │    │ • Fetches HN    │    │ • Deduplicates  │         │
│  │ • Tracks tried  │    │   signals       │    │ • Updates       │         │
│  │   strategies    │    │ • Fetches       │    │   papers_seen   │         │
│  │ • Decides       │    │   Twitter       │    │   in state      │         │
│  │   expansion     │    │   signals       │    │                 │         │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘         │
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │  AssessorAgent  │    │  CuratorAgent   │    │  DecisionAgent  │         │
│  ├─────────────────┤    ├─────────────────┤    ├─────────────────┤         │
│  │ • Breakthrough  │    │ • Multi-signal  │    │ • Evaluates     │         │
│  │   detection     │    │   scoring       │    │   noteworthy    │         │
│  │ • Novelty/      │    │ • Ranking by    │    │   threshold     │         │
│  │   impact        │    │   relevance     │    │ • Routes to     │         │
│  │   scoring       │    │ • Interest      │    │   NOTIFY/       │         │
│  │ • Evidence      │    │   matching      │    │   EXPAND/DONE   │         │
│  │   quality       │    │                 │    │ • Checks max    │         │
│  │                 │    │                 │    │   iterations    │         │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘         │
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐                                │
│  │  NotifierAgent  │    │    LogAgent     │                                │
│  ├─────────────────┤    ├─────────────────┤                                │
│  │ • Formats       │    │ • Logs cycle    │                                │
│  │   notification  │    │   results       │                                │
│  │ • Sends email   │    │ • Records       │                                │
│  │ • Records       │    │   strategies    │                                │
│  │   delivery      │    │   tried         │                                │
│  │   status        │    │ • Audit trail   │                                │
│  └─────────────────┘    └─────────────────┘                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### State Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           STATE EVOLUTION                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ITERATION 1                                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ papers_seen: {}                                                      │   │
│  │ strategies_tried: []                                                 │   │
│  │ current_strategy: "recent_2_days"                                    │   │
│  │ noteworthy_papers: []                                                │   │
│  │ iterations: 0                                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│  ITERATION 2 (after expand_timeframe)                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ papers_seen: {"2312.001", "2312.002", "2312.003"}                    │   │
│  │ strategies_tried: ["recent_2_days"]                                  │   │
│  │ current_strategy: "recent_7_days"                                    │   │
│  │ noteworthy_papers: []                                                │   │
│  │ iterations: 1                                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│  ITERATION 3 (after check_social)                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ papers_seen: {"2312.001", "2312.002", ..., "2312.010"}               │   │
│  │ strategies_tried: ["recent_2_days", "recent_7_days"]                 │   │
│  │ current_strategy: "trending_social"                                  │   │
│  │ noteworthy_papers: [Paper("Breakthrough Discovery")]                 │   │
│  │ iterations: 2                                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│                         [NOTIFY] ──► END                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Concepts

### Conditional Edges
The graph decides at runtime which node to execute next:
```python
def decision_agent(state: RadarState) -> str:
    """DecisionAgent: Routes workflow based on findings."""
    if state["noteworthy_papers"]:
        return "notify"
    elif state["iterations"] >= state["max_iterations"]:
        return "done"
    else:
        return "expand"
```

### Expansion Strategies
The StrategyAgent selects from multiple search strategies:
```python
EXPANSION_STRATEGIES = [
    "recent_2_days",      # Initial: Last 2 days
    "recent_7_days",      # Expand: Last 7 days
    "recent_14_days",     # Expand: Last 14 days
    "trending_social",    # Focus: HN/Twitter trending
    "lower_threshold",    # Relax: Accept lower scores
]
```

### State Accumulation
State grows across iterations:
```python
class RadarState(TypedDict):
    # Iteration tracking
    papers_seen: set[str]           # Don't re-process
    strategies_tried: list[str]     # Track what we've tried
    current_strategy: str           # Active strategy

    # Results accumulation
    noteworthy_papers: list[Paper]  # Accumulate findings
    all_papers: list[Paper]         # All discovered papers

    # Control flow
    iterations: int                 # Track loop count
    max_iterations: int             # Prevent infinite loops

    # Metadata
    cycle_stats: dict               # Statistics per iteration
    errors: list[str]               # Error tracking
```

---

## Implementation

### Graph Construction

```python
def create_radar_workflow() -> StateGraph:
    """Create the agentic radar workflow with conditional routing."""
    graph = StateGraph(RadarState)

    # Add agent nodes
    graph.add_node("strategy_agent", strategy_agent_node)
    graph.add_node("scanner_agent", scanner_agent_node)
    graph.add_node("filter_agent", filter_agent_node)
    graph.add_node("assessor_agent", assessor_agent_node)
    graph.add_node("curator_agent", curator_agent_node)
    graph.add_node("decision_agent", decision_agent_node)
    graph.add_node("notifier_agent", notifier_agent_node)
    graph.add_node("log_agent", log_agent_node)

    # Define flow
    graph.add_edge(START, "strategy_agent")
    graph.add_edge("strategy_agent", "scanner_agent")
    graph.add_edge("scanner_agent", "filter_agent")
    graph.add_edge("filter_agent", "assessor_agent")
    graph.add_edge("assessor_agent", "curator_agent")
    graph.add_edge("curator_agent", "decision_agent")

    # Conditional routing from decision agent
    graph.add_conditional_edges(
        "decision_agent",
        route_decision,
        {
            "notify": "notifier_agent",
            "expand": "strategy_agent",  # Loop back
            "done": "log_agent"
        }
    )

    graph.add_edge("notifier_agent", END)
    graph.add_edge("log_agent", END)

    return graph.compile()
```

---

## Files to Modify/Create

| File | Changes |
|------|---------|
| `src/graph.py` | Add `RadarState`, `create_radar_workflow()`, all agent nodes |
| `src/radar/daemon.py` | Simplify to just invoke workflow, remove redundant logic |
| `tests/test_graph.py` | Add radar workflow tests for all paths |
| `tests/radar/test_daemon.py` | Update for new integration |

---

## Success Criteria

- [x] Radar is a proper LangGraph workflow
- [ ] 6+ agent nodes with clear responsibilities
- [ ] Conditional edges for notify/expand/done decisions
- [ ] Multiple expansion strategies (timeframe, social, threshold)
- [ ] State accumulates across iterations (papers_seen, strategies_tried)
- [ ] Tests cover all graph paths (notify, expand loop, max iterations)
- [ ] Daemon simplified to just invoke the workflow
- [ ] Dead code cleaned up from daemon.py
- [ ] Flow diagrams in docs and README

---

## Learning Objectives

This milestone teaches key LangGraph patterns:

1. **Conditional Edges** - Runtime decision-making based on state
2. **Iterative Workflows** - Loops with termination conditions
3. **State Evolution** - Tracking progress across iterations
4. **Agent Composition** - Multiple specialized agents working together
5. **Autonomous Decision-Making** - Graph decides, not Python code

---

## Future Extensions

Once this pattern is established:
- Apply to other workflows (daily digest, weekly synthesis)
- Add human-in-the-loop checkpoints
- Implement subgraphs for complex operations
- Add streaming for real-time updates
- Checkpoint state between daemon runs for resume capability
