# LangGraph Introduction for Beginners

## What is LangGraph?

LangGraph is a framework for building **stateful, multi-agent workflows**. Think of it as a way to orchestrate multiple AI agents that work together to solve complex tasks.

### Key Concepts

#### 1. Agents

An **agent** is a component that performs a specific task. Examples:
- Discovery Agent: Finds papers on arXiv
- Reader Agent: Extracts information from papers
- Explainer Agent: Generates explanations

Each agent is **independent** and **focused** on one thing.

#### 2. State

The **state** is a shared data structure that agents read from and write to. It's like a shared whiteboard where agents post their results.

```python
from typing import TypedDict, List

class AgentState(TypedDict):
    """Shared state that all agents can access"""
    raw_papers: List[dict]        # Discovery agent writes here
    analyzed_papers: List[dict]   # Reader agent writes here
    explained_papers: List[dict]  # Explainer agent writes here
```

Why use state?
- Agents can see what other agents have done
- Results flow from one agent to the next
- Easy to debug (inspect state at any point)

#### 3. Graph

A **graph** defines the workflow - which agents run and in what order.

```
START → Discovery → Reader → Explainer → Curator → Email → END
```

Nodes = Agents (do work)
Edges = Flow (what runs next)

#### 4. Why LangGraph?

Instead of this mess:
```python
# Manual orchestration (error-prone, hard to maintain)
papers = discover_papers()
analyzed = []
for paper in papers:
    analyzed.append(read_paper(paper))
explained = []
for paper in analyzed:
    explained.append(explain_paper(paper))
# ... more nested loops ...
```

We write this:
```python
# LangGraph orchestration (clean, declarative)
graph = StateGraph(AgentState)
graph.add_node("discover", discovery_agent)
graph.add_node("read", reader_agent)
graph.add_node("explain", explainer_agent)
graph.add_edge("discover", "read")
graph.add_edge("read", "explain")
graph.add_edge("explain", END)
```

Benefits:
- ✅ Clear flow visualization
- ✅ Easy to add/remove agents
- ✅ Built-in error handling
- ✅ Automatic state management
- ✅ Can inspect state at any step

## How We Use LangGraph

### Week 1: Simple Sequential Flow

```
START → Discovery → Reader → Explainer → Curator → END
```

Each agent runs one after another, passing results via the state.

### Later Weeks: Parallel Execution

```
                    ┌→ Twitter ──┐
START → Discovery → ├→ HN ───────┤ → Merge → Analyze → END
                    └→ Citations ┘
```

Multiple discovery sources run in parallel, then results are merged.

### Even Later: Conditional Flow

```
START → Analyze → [Has errors?]
                     ├─ Yes → Retry
                     └─ No → Continue → END
```

Agents can make decisions about what runs next.

## Our Agent Architecture

Each agent follows this pattern:

```python
def my_agent(state: AgentState) -> AgentState:
    """
    1. Read from state
    2. Do work
    3. Write to state
    4. Return updated state
    """
    # Read input
    raw_data = state["raw_papers"]

    # Do work
    result = process(raw_data)

    # Write output
    state["processed_papers"] = result

    # Return updated state
    return state
```

Key points:
- Agents are **pure functions** (same input → same output)
- Agents **don't modify state directly** (return new state)
- Agents are **composable** (can be reused in different graphs)

## Next Steps

1. Read `src/agents/discovery/arxiv_searcher.py` - Simple agent example
2. Read `src/graph.py` (when we build it) - See how agents connect
3. Experiment with modifying the graph flow

## Resources

- [LangGraph Docs](https://python.langchain.com/docs/langgraph)
- [LangGraph Quickstart](https://python.langchain.com/docs/langgraph/tutorials/introduction)
- [Example Agents](https://github.com/langchain-ai/langgraph/tree/main/examples)
