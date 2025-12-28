# Milestone 4: Truly Agentic LangGraph Workflow

**Status:** Planned
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

## Key Concepts

### Conditional Edges
The graph decides at runtime which node to execute next:
```python
def should_notify(state: RadarState) -> str:
    if state["noteworthy_papers"]:
        return "notify"
    elif state["iterations"] >= state["max_iterations"]:
        return "log_nothing"
    else:
        return "expand_search"
```

### Iterative Search
The graph can loop back to try different strategies:
1. First: Scan last 2 days
2. If nothing: Expand to 7 days
3. If nothing: Try different categories
4. If nothing: Check trending from HN/Twitter

### State Accumulation
State grows across iterations:
```python
class RadarState(TypedDict):
    papers_seen: set[str]           # Don't re-process
    strategies_tried: list[str]     # Track what we've tried
    noteworthy_papers: list[Paper]  # Accumulate findings
    iterations: int                  # Track loop count
    max_iterations: int              # Prevent infinite loops
```

---

## Workflow Design

```
┌─────────────────────────────────────────────────────────────────┐
│                    RADAR WORKFLOW (LangGraph)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   START → scan_papers → assess_batch → check_noteworthy         │
│                                              │                  │
│                             ┌────────────────┴───────────┐      │
│                             ▼                            ▼      │
│                       (found noteworthy?)                       │
│                             │                            │      │
│                        NO   │                       YES  │      │
│                             ▼                            ▼      │
│                      expand_search ─────────────────► notify    │
│                            │                             │      │
│                            ▼                             ▼      │
│                      (max iterations?)                  END     │
│                            │                                    │
│                       YES  │  NO                                │
│                            ▼   └──► back to scan_papers         │
│                       log_nothing → END                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Features

### 1. Graph-Based Radar Workflow
- All decision logic in the graph
- Clear visualization of flow
- Easy to modify/extend

### 2. Expansion Strategies
Multiple ways to find papers when initial scan fails:
- `expand_timeframe` - Look further back
- `expand_categories` - Try related categories
- `check_social` - Focus on HN/Twitter trending
- `lower_threshold` - Accept lower scores temporarily

### 3. Persistent State
- Checkpoint state between runs
- Resume from last position
- Audit trail of decisions

### 4. Autonomous Decision-Making
The graph decides:
- When to notify vs continue searching
- Which expansion strategy to try
- When to give up (max iterations)

---

## Implementation Plan

### Phase 1: Create Radar Graph
```python
# src/graph.py

def create_radar_workflow() -> StateGraph:
    """Create the agentic radar workflow."""
    graph = StateGraph(RadarState)

    # Nodes
    graph.add_node("scan_papers", scan_papers_node)
    graph.add_node("assess_batch", assess_batch_node)
    graph.add_node("expand_search", expand_search_node)
    graph.add_node("notify", notify_node)
    graph.add_node("log_nothing", log_nothing_node)

    # Edges
    graph.add_edge(START, "scan_papers")
    graph.add_edge("scan_papers", "assess_batch")
    graph.add_conditional_edges(
        "assess_batch",
        should_notify_or_expand,
        {
            "notify": "notify",
            "expand": "expand_search",
            "done": "log_nothing"
        }
    )
    graph.add_conditional_edges(
        "expand_search",
        should_continue,
        {
            "continue": "scan_papers",
            "stop": "log_nothing"
        }
    )
    graph.add_edge("notify", END)
    graph.add_edge("log_nothing", END)

    return graph.compile()
```

### Phase 2: Node Implementations
Each node is a focused function:
- `scan_papers_node` - Discover papers based on current strategy
- `assess_batch_node` - Score and filter papers
- `expand_search_node` - Choose and apply expansion strategy
- `notify_node` - Send notification
- `log_nothing_node` - Log that nothing was found

### Phase 3: Integrate with Daemon
The daemon just invokes the graph:
```python
def _run_scan_cycle(self) -> dict:
    workflow = create_radar_workflow()
    result = workflow.invoke({
        "papers_seen": set(),
        "strategies_tried": [],
        "noteworthy_papers": [],
        "iterations": 0,
        "max_iterations": 3,
    })
    return result
```

---

## Files to Modify/Create

- `src/graph.py` - Add `create_radar_workflow()`, radar nodes
- `src/radar/daemon.py` - Simplify to just invoke workflow
- `tests/test_graph.py` - Add radar workflow tests

---

## Learning Objectives

This milestone teaches key LangGraph patterns:

1. **Conditional Edges** - Runtime decision-making
2. **Iterative Workflows** - Loops with termination conditions
3. **State Evolution** - Tracking progress across iterations
4. **Autonomous Agents** - Graph decides, not Python code

---

## Success Criteria

- [ ] Radar is a proper LangGraph workflow
- [ ] Conditional edges for notify/expand decisions
- [ ] Multiple expansion strategies
- [ ] State accumulates across iterations
- [ ] Tests cover all graph paths
- [ ] Daemon just invokes the workflow
- [ ] Clear visualization of the workflow

---

## Future Extensions

Once this pattern is established:
- Apply to other workflows (daily digest, weekly synthesis)
- Add human-in-the-loop checkpoints
- Implement subgraphs for complex operations
- Add streaming for real-time updates
