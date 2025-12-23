# CLAUDE.md - AI Assistant Guide

**Last Updated:** December 2025
**Project:** ArXiv Learning Assistant
**Version:** 1.0

This document provides comprehensive guidance for AI assistants (like Claude) working with this codebase. It explains the project structure, architecture, development workflows, and key conventions to follow.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Project Structure](#project-structure)
3. [Tech Stack](#tech-stack)
4. [Development Workflow](#development-workflow)
5. [Architecture & Design](#architecture--design)
6. [Learning Objectives & Advanced Patterns](#learning-objectives--advanced-patterns)
7. [Database Schema](#database-schema)
8. [Code Conventions](#code-conventions)
9. [Key Patterns](#key-patterns)
10. [Common Tasks](#common-tasks)
11. [Testing & Debugging](#testing--debugging)
12. [API Integration](#api-integration)
13. [Important Notes](#important-notes)

---

## Project Overview

### What is this?

**ArXiv Learning Assistant** is a multi-agent system that helps AI researchers stay on top of the flood of papers published daily on arXiv. It discovers, analyzes, explains, and curates research papers with personalized learning paths.

### Problem It Solves

- 200-300 new AI papers published daily on arXiv
- Existing solutions (RSS, Twitter) are too noisy or incomplete
- Manual tracking is time-consuming and inefficient

### Solution

Multi-agent LangGraph system that:
1. **Discovers** papers from multiple sources (arXiv, Twitter, HackerNews)
2. **Analyzes** papers with Claude to extract structured information
3. **Explains** papers in accessible language for learning
4. **Curates** papers based on relevance, social proof, and citation velocity
5. **Visualizes** connections through interactive knowledge graphs
6. **Tracks** reading progress and suggests next papers

### Design Principles

1. **Modularity** - Each agent is independent and testable
2. **Incremental Value** - Each phase delivers usable features
3. **Low Latency** - Async operations, caching, batching
4. **Cost Efficient** - Haiku for extraction, Sonnet for explanations
5. **Extensible** - Easy to add new sources and agents

---

## Project Structure

```
learning-assistant/
├── main.py                 # CLI entry point - all user commands
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variable template
├── README.md              # User-facing documentation
├── QUICKSTART.md          # 15-minute setup guide
├── CLAUDE.md              # This file - AI assistant guide
│
├── src/                   # Source code
│   ├── __init__.py
│   ├── config.py          # Configuration management (pydantic)
│   ├── database.py        # Database connection & session management
│   │
│   ├── models/            # Database models (SQLAlchemy ORM)
│   │   ├── __init__.py
│   │   └── paper.py       # Paper, Citation, SocialSignal, ReadingProgress
│   │
│   ├── agents/            # LangGraph agents
│   │   ├── __init__.py
│   │   └── discovery/     # Discovery agents
│   │       ├── __init__.py
│   │       └── arxiv_searcher.py  # ArXiv API integration
│   │
│   ├── services/          # External service clients
│   │   ├── __init__.py
│   │   └── claude_client.py       # Claude API wrapper
│   │
│   ├── visualization/     # Graph visualization
│   │   └── __init__.py
│   │
│   └── dashboard/         # Streamlit dashboard
│       └── __init__.py
│
├── tests/                 # Test files
│   └── __init__.py
│
├── docs/                  # Documentation
│   ├── design.md          # System architecture & design
│   ├── project_plan.md    # 6-week build plan
│   ├── langgraph_intro.md # LangGraph concepts
│   └── weekly/            # Weekly task breakdowns
│       ├── week1.md
│       ├── week2.md
│       ├── week3.md
│       ├── week4.md
│       ├── week5.md
│       └── week6.md
│
├── data/                  # Database & cache (gitignored)
│   └── papers.db          # SQLite database
│
└── logs/                  # Application logs (gitignored)
    └── app.log            # Rotating log file
```

### Key Files to Understand

| File | Purpose | When to Modify |
|------|---------|----------------|
| `main.py` | CLI commands & orchestration | Adding new commands |
| `src/config.py` | Environment variables & settings | Adding new configuration |
| `src/database.py` | Database connection & sessions | Changing DB setup |
| `src/models/paper.py` | Data models & schema | Adding/modifying tables |
| `docs/design.md` | Architecture reference | Understanding system design |
| `.env.example` | Required environment variables | Adding new API keys |

---

## Tech Stack

### Core Framework
- **LangGraph 0.3+** - Multi-agent orchestration & state management
- **LangChain 0.1+** - LLM framework & utilities
- **Anthropic 0.18+** - Claude API client

### Data & Storage
- **SQLAlchemy 2.0+** - ORM for database operations
- **SQLite 3** - Local database (can swap for Postgres)
- **NetworkX 3.2+** - Graph analysis & algorithms
- **Redis 5.0+** (optional) - Caching layer

### Discovery APIs
- **arxiv 2.1+** - ArXiv paper search
- **tweepy 4.14+** - Twitter API v2 client
- **semanticscholar 0.8+** - Citation data
- **beautifulsoup4 4.12+** - Web scraping
- **requests 2.31+** - HTTP client

### Visualization
- **Streamlit 1.29+** - Interactive dashboard
- **Plotly 5.18+** - Charts & visualizations
- **PyVis 0.3+** - Network graph rendering

### Utilities
- **pydantic 2.5+** - Settings validation
- **python-dotenv 1.0+** - Environment variable loading
- **loguru 0.7+** - Modern logging
- **apscheduler 3.10+** - Job scheduling
- **pytest 7.4+** - Testing framework
- **black 24.0+** - Code formatting

---

## Development Workflow

### Initial Setup

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 4. Initialize database
python main.py --init-db

# 5. Test the setup
python main.py --stats
```

### Daily Development Workflow

```bash
# Discover papers (development)
python main.py --discover --days 1

# Run with debug logging
python main.py --discover --days 1 --debug

# Check database status
python main.py --stats

# Reset database (WARNING: deletes all data)
python main.py --init-db --reset --yes
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test
pytest tests/test_database.py

# Format code
black .
```

---

## Architecture & Design

### High-Level System Design

```
┌─────────────────────────────────────────────────────────┐
│                 User Interface Layer                    │
├─────────────────────────────────────────────────────────┤
│  • Email Digest                                         │
│  • CLI Commands (main.py)                               │
│  • Dashboard (Streamlit)                                │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              Application Layer (LangGraph)              │
├─────────────────────────────────────────────────────────┤
│  • Supervisor Agent (Orchestrator)                      │
│  • Discovery Agent → ArXiv, Twitter, HN, Citations      │
│  • Reader Agent → Extract structure (Haiku)             │
│  • Explainer Agent → Simplify concepts (Sonnet)         │
│  • Curator Agent → Rank and filter                      │
│  • Graph Builder → Build relationships                  │
│  • Recommendation Agent → Suggest next reads            │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    Data Layer                           │
├─────────────────────────────────────────────────────────┤
│  • SQLite DB (Papers, Citations, Social Signals)        │
│  • Graph Store (NetworkX)                               │
│  • Cache (Redis - optional)                             │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              External Services Layer                    │
├─────────────────────────────────────────────────────────┤
│  • ArXiv API                                            │
│  • Claude API (Anthropic)                               │
│  • Twitter API v2                                       │
│  • Semantic Scholar API                                 │
│  • HackerNews Algolia API                               │
│  • SMTP (Email)                                         │
└─────────────────────────────────────────────────────────┘
```

### LangGraph State Machine

All agents share a common state object (`AgentState` TypedDict):

```python
AgentState = {
    "research_interests": List[str],
    "date_range": tuple[datetime, datetime],
    "raw_papers": List[dict],
    "social_signals": dict,
    "citation_data": dict,
    "analyzed_papers": List[dict],
    "explained_papers": List[dict],
    "scored_papers": List[dict],
    "final_selection": List[dict],
    "errors": List[str],
    "api_calls": dict
}
```

### Agent Specifications

#### 1. Discovery Agent
- **Purpose:** Find papers from multiple sources
- **Sub-agents:** ArxivSearcher, TwitterTracker, HNTracker, CitationTracker
- **Process:** Run in parallel → merge → deduplicate by arxiv_id
- **Caching:** arXiv (1h), Twitter/HN (15min), Citations (24h)

#### 2. Reader Agent
- **Purpose:** Extract structured information from papers
- **Model:** Claude 3.5 Haiku (fast, cheap, good at extraction)
- **Output:** main_claim, methodology, key_results, novel_contributions, limitations, concepts
- **Cost:** ~$0.001 per paper

#### 3. Explainer Agent
- **Purpose:** Generate learning-friendly explanations
- **Model:** Claude 3.5 Sonnet (better explanations)
- **Output:** eli5_summary, key_insight, learning_questions, prerequisites, related_concepts
- **Cost:** ~$0.015 per paper

#### 4. Curator Agent
- **Purpose:** Score and rank papers by relevance
- **Scoring:** Interest match (40%), Social proof (25%), Citation velocity (20%), Recency (10%), Lab prestige (5%)
- **Output:** Top N papers ranked by total score

---

## Learning Objectives & Advanced Patterns

**This is a learning project!** The primary goal is to understand LangGraph and multi-agent systems, specifically focusing on:

1. **Shared Context Management** - How agents communicate through state
2. **Evolution Over Time** - How state changes as it flows through agents
3. **Auditability** - How to track, debug, and replay agent decisions

This section covers advanced LangGraph patterns essential for production multi-agent systems.

---

### 1. Shared Context Management

#### What is Shared Context?

In LangGraph, **state** is the shared context that all agents can read from and write to. Think of it as a living document that evolves as it passes through the graph.

**Example: Paper Processing State**

```python
from typing import TypedDict, List, Annotated
from langgraph.graph import add_messages

class PaperProcessingState(TypedDict):
    """
    Shared state for the paper processing workflow.

    Each agent reads what it needs and writes its results.
    State flows: Discovery → Reader → Explainer → Curator
    """
    # Input configuration
    research_interests: List[str]
    date_range: tuple[datetime, datetime]

    # Discovery agent writes these
    raw_papers: List[dict]
    discovery_errors: List[str]

    # Reader agent writes these
    analyzed_papers: List[dict]
    analysis_errors: List[str]

    # Explainer agent writes these
    explained_papers: List[dict]
    explanation_errors: List[str]

    # Curator agent writes these
    scored_papers: List[dict]
    final_selection: List[dict]

    # Metadata for tracking
    total_api_calls: int
    total_cost_usd: float
    processing_time_seconds: float
```

#### State Reducers: Managing Concurrent Updates

When multiple agents run in parallel, they might update the same state field. **Reducers** define how to merge these updates.

```python
from typing import Annotated
from operator import add
from langgraph.graph import StateGraph

class ParallelDiscoveryState(TypedDict):
    """
    State with reducers for parallel discovery agents.

    Multiple discovery sources (arXiv, Twitter, HN) run in parallel.
    We need to combine their results without losing data.
    """
    # Simple replacement (last write wins)
    query: str

    # Add reducer: concatenate lists from parallel agents
    raw_papers: Annotated[List[dict], add]

    # Custom reducer: merge error lists and deduplicate
    errors: Annotated[List[str], lambda old, new: list(set(old + new))]

    # Custom reducer: sum API call counts
    api_calls: Annotated[int, lambda old, new: old + new]

# Usage example
def arxiv_discovery(state: ParallelDiscoveryState) -> ParallelDiscoveryState:
    """ArXiv discovery agent."""
    papers = fetch_from_arxiv(state["query"])
    return {
        "raw_papers": papers,  # Will be ADDED to existing papers
        "api_calls": 1,        # Will be SUMMED with other calls
    }

def twitter_discovery(state: ParallelDiscoveryState) -> ParallelDiscoveryState:
    """Twitter discovery agent."""
    papers = fetch_from_twitter(state["query"])
    return {
        "raw_papers": papers,  # Will be ADDED to existing papers
        "api_calls": 5,        # Will be SUMMED with other calls
    }

# After both agents run in parallel:
# state["raw_papers"] = arxiv_papers + twitter_papers
# state["api_calls"] = 1 + 5 = 6
```

#### Message History Pattern

For conversational agents or iterative refinement, use the message history pattern:

```python
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import add_messages

class ConversationalState(TypedDict):
    """
    State that maintains conversation history.

    The add_messages reducer automatically:
    - Appends new messages to the list
    - Handles message deduplication by ID
    - Preserves message order
    """
    # Automatically managed message list
    messages: Annotated[List[BaseMessage], add_messages]

    # Other state fields
    paper_id: str
    user_question: str

# Example: Interactive paper Q&A agent
def paper_qa_agent(state: ConversationalState) -> ConversationalState:
    """Answer questions about a paper using conversation history."""
    # Get full conversation context
    history = state["messages"]

    # Generate response using history
    response = claude_client.chat(
        messages=history + [HumanMessage(content=state["user_question"])]
    )

    return {
        "messages": [AIMessage(content=response)]  # Added to history
    }
```

---

### 2. Evolution Over Time: Checkpointing & Persistence

#### Why Checkpointing?

Checkpointing lets you:
- **Resume** interrupted workflows
- **Replay** workflows for debugging
- **Audit** what happened at each step
- **Time-travel** debug by inspecting state at any point

#### Implementing Checkpointing

```python
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, END

# Create a checkpointer (persists to SQLite)
checkpointer = SqliteSaver.from_conn_string("checkpoints.db")

# Build your graph
graph = StateGraph(PaperProcessingState)
graph.add_node("discovery", discovery_agent)
graph.add_node("reader", reader_agent)
graph.add_node("explainer", explainer_agent)
graph.add_edge("discovery", "reader")
graph.add_edge("reader", "explainer")
graph.add_edge("explainer", END)

# Compile with checkpointing enabled
app = graph.compile(checkpointer=checkpointer)

# Run with a thread_id to enable persistence
config = {"configurable": {"thread_id": "paper-run-2024-01-15"}}
result = app.invoke(initial_state, config=config)

# Resume from checkpoint later (e.g., after a crash)
resumed_result = app.invoke(None, config=config)  # Continues from last checkpoint

# Get state at any point
checkpoint = checkpointer.get(config)
print(f"State at checkpoint: {checkpoint.values}")
```

#### Checkpoint Strategy for This Project

```python
# src/graph.py

def create_paper_processing_graph(enable_checkpointing=True):
    """
    Create the main paper processing graph with optional checkpointing.

    Checkpointing is useful for:
    - Long-running batch jobs (process 1000 papers)
    - Debugging (inspect state at each agent)
    - Cost tracking (resume without re-running expensive API calls)
    """
    graph = StateGraph(PaperProcessingState)

    # Add all agents
    graph.add_node("discovery", discovery_agent)
    graph.add_node("reader", reader_agent)
    graph.add_node("explainer", explainer_agent)
    graph.add_node("curator", curator_agent)

    # Define flow
    graph.add_edge("discovery", "reader")
    graph.add_edge("reader", "explainer")
    graph.add_edge("explainer", "curator")
    graph.add_edge("curator", END)

    # Compile with checkpointing
    if enable_checkpointing:
        from langgraph.checkpoint.sqlite import SqliteSaver
        checkpointer = SqliteSaver.from_conn_string("data/checkpoints.db")
        return graph.compile(checkpointer=checkpointer)
    else:
        return graph.compile()

# Usage: Resume after interruption
def process_papers_with_resume(days_back=1):
    """Process papers with automatic resume capability."""
    from datetime import datetime

    app = create_paper_processing_graph(enable_checkpointing=True)

    # Use date-based thread_id for idempotency
    thread_id = f"discovery-{datetime.now().date()}"
    config = {"configurable": {"thread_id": thread_id}}

    try:
        result = app.invoke(
            {"date_range": (datetime.now() - timedelta(days=days_back), datetime.now())},
            config=config
        )
        return result
    except KeyboardInterrupt:
        logger.warning("Interrupted! Progress saved. Re-run to continue.")
        raise
```

---

### 3. Auditability: Decision Logging & Replay

#### Decision Logging Pattern

Track **why** agents made decisions, not just **what** they did:

```python
from datetime import datetime
from typing import List, Dict
import json

class AuditLog(TypedDict):
    """Audit log entry for agent decisions."""
    timestamp: datetime
    agent_name: str
    decision: str
    reasoning: str
    input_snapshot: Dict
    output_snapshot: Dict
    metadata: Dict

class AuditableState(PaperProcessingState):
    """State with audit trail."""
    audit_log: Annotated[List[AuditLog], add]

def curator_agent_with_logging(state: AuditableState) -> AuditableState:
    """
    Curator agent that logs its decisions.

    For each paper it selects or rejects, it logs:
    - What decision was made
    - Why it was made (scores, thresholds)
    - Input/output state snapshots
    """
    papers = state["explained_papers"]

    # Score papers
    scored = []
    audit_entries = []

    for paper in papers:
        score = calculate_relevance_score(paper, state["research_interests"])

        # Decision: include or exclude?
        threshold = 0.7
        included = score >= threshold

        # Log the decision
        audit_entries.append({
            "timestamp": datetime.utcnow(),
            "agent_name": "curator",
            "decision": "include" if included else "exclude",
            "reasoning": f"Score {score:.2f} vs threshold {threshold}",
            "input_snapshot": {
                "paper_id": paper["arxiv_id"],
                "paper_title": paper["title"],
                "score_components": paper.get("score_components", {}),
            },
            "output_snapshot": {
                "final_score": score,
                "included": included,
            },
            "metadata": {
                "research_interests": state["research_interests"],
                "threshold": threshold,
            }
        })

        if included:
            scored.append({**paper, "relevance_score": score})

    return {
        "scored_papers": scored,
        "final_selection": sorted(scored, key=lambda p: p["relevance_score"], reverse=True)[:5],
        "audit_log": audit_entries
    }

# Save audit log to database or file
def save_audit_log(state: AuditableState, run_id: str):
    """Persist audit log for later analysis."""
    with open(f"logs/audit-{run_id}.jsonl", "w") as f:
        for entry in state["audit_log"]:
            f.write(json.dumps(entry, default=str) + "\n")
```

#### Replay & Debugging

```python
def replay_workflow(checkpoint_db: str, thread_id: str):
    """
    Replay a workflow step-by-step for debugging.

    This is invaluable for:
    - Understanding why certain papers were selected
    - Debugging scoring algorithms
    - Optimizing prompts based on historical runs
    """
    from langgraph.checkpoint.sqlite import SqliteSaver

    checkpointer = SqliteSaver.from_conn_string(checkpoint_db)

    # Get all checkpoints for this thread
    checkpoints = checkpointer.list({"configurable": {"thread_id": thread_id}})

    print(f"Replaying workflow: {thread_id}")
    print("=" * 60)

    for i, checkpoint in enumerate(checkpoints):
        print(f"\nStep {i+1}: {checkpoint.metadata.get('step', 'unknown')}")
        print(f"Timestamp: {checkpoint.metadata.get('timestamp')}")

        state = checkpoint.values

        # Show key metrics at this step
        print(f"Papers discovered: {len(state.get('raw_papers', []))}")
        print(f"Papers analyzed: {len(state.get('analyzed_papers', []))}")
        print(f"Papers explained: {len(state.get('explained_papers', []))}")
        print(f"Final selection: {len(state.get('final_selection', []))}")
        print(f"Total cost: ${state.get('total_cost_usd', 0):.2f}")
        print(f"Errors: {len(state.get('discovery_errors', []) + state.get('analysis_errors', []))}")

# Usage:
# replay_workflow("data/checkpoints.db", "discovery-2024-01-15")
```

#### Visualization for Debugging

```python
def visualize_state_evolution(checkpoint_db: str, thread_id: str):
    """
    Visualize how state evolved through the graph.

    Shows:
    - How many items at each stage
    - Cost accumulation over time
    - Error distribution by agent
    """
    import matplotlib.pyplot as plt
    from langgraph.checkpoint.sqlite import SqliteSaver

    checkpointer = SqliteSaver.from_conn_string(checkpoint_db)
    checkpoints = list(checkpointer.list({"configurable": {"thread_id": thread_id}}))

    # Extract metrics
    steps = []
    papers_count = []
    costs = []

    for cp in checkpoints:
        state = cp.values
        steps.append(cp.metadata.get('step', 'unknown'))
        papers_count.append(len(state.get('raw_papers', [])))
        costs.append(state.get('total_cost_usd', 0))

    # Plot
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

    ax1.plot(steps, papers_count, marker='o')
    ax1.set_title('Papers in Pipeline by Step')
    ax1.set_ylabel('Paper Count')

    ax2.plot(steps, costs, marker='o', color='red')
    ax2.set_title('Cumulative API Cost by Step')
    ax2.set_ylabel('Cost (USD)')
    ax2.set_xlabel('Pipeline Step')

    plt.tight_layout()
    plt.savefig(f'logs/state-evolution-{thread_id}.png')
```

---

### 4. Human-in-the-Loop Patterns

Sometimes you want human approval before proceeding:

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

def create_human_in_loop_graph():
    """
    Graph that pauses for human approval before sending emails.

    Flow:
    1. Discovery → Reader → Explainer → Curator
    2. PAUSE for human review
    3. If approved → Send email
    4. If rejected → Log and exit
    """
    graph = StateGraph(PaperProcessingState)

    # Add agents
    graph.add_node("discovery", discovery_agent)
    graph.add_node("reader", reader_agent)
    graph.add_node("explainer", explainer_agent)
    graph.add_node("curator", curator_agent)
    graph.add_node("send_email", email_agent)

    # Define flow with conditional edge
    graph.add_edge("discovery", "reader")
    graph.add_edge("reader", "explainer")
    graph.add_edge("explainer", "curator")

    # PAUSE here - human decides next step
    graph.add_conditional_edges(
        "curator",
        human_approval_gate,  # Function that returns "approved" or "rejected"
        {
            "approved": "send_email",
            "rejected": END,
        }
    )
    graph.add_edge("send_email", END)

    # Must use checkpointing for human-in-loop
    checkpointer = SqliteSaver.from_conn_string("data/checkpoints.db")
    return graph.compile(checkpointer=checkpointer, interrupt_before=["send_email"])

# Run with interruption
app = create_human_in_loop_graph()
config = {"configurable": {"thread_id": "review-2024-01-15"}}

# Initial run - stops before email
result = app.invoke(initial_state, config=config)
print("Pipeline paused. Review the papers:")
for paper in result["final_selection"]:
    print(f"- {paper['title']}")

# Human reviews and approves
approval = input("Send email? (y/n): ")

# Continue with approval
if approval.lower() == 'y':
    app.update_state(config, {"approved": True})
    final_result = app.invoke(None, config=config)
else:
    print("Email cancelled")
```

---

### 5. Advanced Graph Patterns

#### Conditional Routing Based on State

```python
def route_based_on_quality(state: PaperProcessingState) -> str:
    """
    Decide next step based on paper quality.

    - High quality (score > 0.9) → Skip review, send immediately
    - Medium quality (0.7-0.9) → Human review
    - Low quality (< 0.7) → Discard
    """
    avg_score = sum(p["relevance_score"] for p in state["scored_papers"]) / len(state["scored_papers"])

    if avg_score > 0.9:
        return "auto_send"
    elif avg_score > 0.7:
        return "human_review"
    else:
        return "discard"

# In graph definition:
graph.add_conditional_edges(
    "curator",
    route_based_on_quality,
    {
        "auto_send": "send_email",
        "human_review": "review_node",
        "discard": END,
    }
)
```

#### Sub-graphs for Composability

```python
def create_analysis_subgraph():
    """
    Reusable sub-graph for paper analysis.

    Can be used in:
    - Main discovery pipeline
    - Ad-hoc paper analysis
    - Batch re-processing
    """
    subgraph = StateGraph(PaperProcessingState)
    subgraph.add_node("reader", reader_agent)
    subgraph.add_node("explainer", explainer_agent)
    subgraph.add_edge("reader", "explainer")
    subgraph.add_edge("explainer", END)
    return subgraph.compile()

def create_main_graph():
    """Main graph that uses the analysis sub-graph."""
    graph = StateGraph(PaperProcessingState)

    # Regular nodes
    graph.add_node("discovery", discovery_agent)
    graph.add_node("curator", curator_agent)

    # Sub-graph as a node
    analysis_subgraph = create_analysis_subgraph()
    graph.add_node("analyze", analysis_subgraph)

    # Connect
    graph.add_edge("discovery", "analyze")
    graph.add_edge("analyze", "curator")
    graph.add_edge("curator", END)

    return graph.compile()
```

#### Retry Logic with Exponential Backoff

```python
def create_resilient_agent(agent_func, max_retries=3):
    """
    Wrap an agent with retry logic.

    Useful for:
    - API rate limits
    - Transient network errors
    - Flaky external services
    """
    def resilient_agent(state: PaperProcessingState) -> PaperProcessingState:
        import time

        for attempt in range(max_retries):
            try:
                return agent_func(state)
            except RateLimitError as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Rate limited. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed after {max_retries} attempts")
                    return {
                        "errors": [f"Agent failed after {max_retries} retries: {e}"]
                    }

    return resilient_agent

# Usage:
graph.add_node("reader", create_resilient_agent(reader_agent))
```

---

### 6. Best Practices for Production

#### State Design Principles

1. **Keep state flat** - Avoid deep nesting
2. **Use type hints** - TypedDict for validation
3. **Document reducers** - Explain merge logic
4. **Include metadata** - Track costs, timing, errors
5. **Plan for debugging** - Include audit fields from day 1

#### Checkpointing Strategy

```python
# Good: Checkpoint after expensive operations
graph.add_node("expensive_llm_call", llm_agent)  # Checkpoint automatically saved

# Bad: Too frequent checkpointing (performance hit)
# Don't checkpoint after every tiny operation

# Best practice: Checkpoint at logical boundaries
# - After each major agent
# - Before/after API calls
# - At decision points
```

#### Monitoring & Observability

```python
def instrumented_agent(agent_name: str, agent_func):
    """Wrap agent with monitoring."""
    def wrapper(state):
        start = time.time()

        try:
            result = agent_func(state)
            duration = time.time() - start

            # Log metrics
            logger.info(f"{agent_name} completed in {duration:.2f}s")
            metrics.record(f"{agent_name}.duration", duration)
            metrics.record(f"{agent_name}.success", 1)

            return result
        except Exception as e:
            logger.error(f"{agent_name} failed: {e}")
            metrics.record(f"{agent_name}.errors", 1)
            raise

    return wrapper
```

---

### 7. Learning Exercises

To master these patterns, try:

1. **Add checkpointing** to the main pipeline
   - Save state after each agent
   - Implement resume functionality
   - Build a replay debugger

2. **Implement audit logging** for the curator agent
   - Log why each paper was selected/rejected
   - Track score components
   - Visualize decision patterns

3. **Build a human-in-loop review flow**
   - Pause before sending emails
   - Allow editing of paper selections
   - Track approval rates

4. **Add conditional routing** based on paper count
   - If < 5 papers → expand search criteria
   - If > 20 papers → increase threshold
   - If 0 papers → alert user

5. **Instrument the entire pipeline**
   - Track timing for each agent
   - Monitor API costs in real-time
   - Set up alerts for errors

---

## Database Schema

### Core Entities

#### Paper (papers table)
Primary entity representing an arXiv paper.

**Core Fields:**
- `arxiv_id` (PK) - Unique identifier (e.g., "2312.12345")
- `title`, `abstract`, `authors`, `published_date`
- `categories` - List of arXiv categories (JSON)
- `pdf_url`, `abstract_url`
- `discovered_at`, `discovered_by`
- `lab_published_by` - Optional lab attribution

**Analysis Fields (from Reader Agent):**
- `main_claim`, `methodology`, `key_results`
- `novel_contributions`, `limitations`, `concepts`
- `analyzed_at`

**Explanation Fields (from Explainer Agent):**
- `eli5_summary`, `key_insight`
- `learning_questions`, `prerequisites`, `related_concepts`
- `explained_at`

**Scoring Fields (from Curator Agent):**
- `relevance_score` (0-1, higher = more relevant)
- `score_components` - Breakdown for transparency
- `scored_at`

#### Citation (citations table)
Citation metrics tracked over time.

- `id` (PK) - Auto-incrementing
- `paper_id` (FK → papers.arxiv_id)
- `citation_count`, `measured_at`
- `citations_this_week`, `velocity_score`
- `source` - Where data came from (e.g., "semantic_scholar")

#### SocialSignal (social_signals table)
Social media mentions (Twitter, HN, Reddit).

- `id` (PK)
- `paper_id` (FK → papers.arxiv_id)
- `source` - "twitter", "hackernews", "reddit"
- `source_url`, `score`, `comments_count`
- `snippet`, `author`, `posted_at`
- `discovered_at`

#### ReadingProgress (reading_progress table)
User's reading journey and notes.

- `paper_id` (PK, FK → papers.arxiv_id)
- `status` - "unread", "reading", "finished", "archived"
- `started_at`, `finished_at`
- `rating` (1-5), `notes`, `time_spent_minutes`

### Relationships

```
Paper (1) ←→ (many) Citation
Paper (1) ←→ (many) SocialSignal
Paper (1) ←→ (1) ReadingProgress
```

All relationships use `CASCADE DELETE` - deleting a paper deletes related records.

### Indexes

Performance indexes on frequently queried columns:
- `idx_published_date` on papers.published_date
- `idx_relevance_score` on papers.relevance_score
- `idx_discovered_at` on papers.discovered_at
- `idx_citation_paper_measured` on (citations.paper_id, citations.measured_at)
- `idx_social_paper_source` on (social_signals.paper_id, social_signals.source)
- `idx_progress_status` on reading_progress.status

---

## Code Conventions

### Python Style
- **Formatting:** Black (line length 100)
- **Type Hints:** Use throughout for clarity
- **Docstrings:** Required for all public functions/classes
- **Naming:** snake_case for functions/variables, PascalCase for classes

### Logging
Use `loguru` for all logging:

```python
from loguru import logger

# Good logging practices
logger.info("Starting paper discovery...")
logger.debug(f"API response: {response}")
logger.warning("Rate limit approaching")
logger.error(f"Failed to fetch paper {arxiv_id}: {error}")
logger.exception("Full traceback:")  # Use in except blocks
```

### Error Handling

```python
# Always catch specific exceptions
try:
    paper = discover_papers(days_back=1)
except APIRateLimitError:
    logger.warning("Rate limited, backing off...")
    time.sleep(60)
except ConnectionError as e:
    logger.error(f"Network error: {e}")
    raise
except Exception as e:
    logger.exception("Unexpected error:")
    raise
```

### Configuration
- **All secrets in .env** - Never hardcode API keys
- **Use pydantic Settings** - Type-safe configuration
- **Provide defaults** - For non-sensitive settings
- **Document in .env.example** - Keep it updated

### Database Operations

**ALWAYS use context managers:**

```python
# ✅ GOOD - Automatic commit/rollback/cleanup
with get_db_session() as db:
    paper = db.query(Paper).filter_by(arxiv_id="2312.12345").first()
    paper.relevance_score = 0.9
    # Automatically commits on exit

# ❌ BAD - Manual session management
db = get_db()
paper = db.query(Paper).first()
db.commit()
db.close()  # Easy to forget!
```

---

## Key Patterns

### 1. SQLAlchemy ORM Pattern

**Querying:**
```python
with get_db_session() as db:
    # Simple query
    papers = db.query(Paper).all()

    # Filter
    recent_papers = db.query(Paper)\
        .filter(Paper.published_date > datetime(2024, 1, 1))\
        .all()

    # Complex query with joins
    papers_with_citations = db.query(Paper)\
        .join(Citation)\
        .filter(Citation.citation_count > 100)\
        .all()

    # Aggregation
    from sqlalchemy import func
    avg_score = db.query(func.avg(Paper.relevance_score)).scalar()
```

**Creating:**
```python
with get_db_session() as db:
    paper = Paper(
        arxiv_id="2312.12345",
        title="My Paper",
        abstract="This is cool",
        authors=["Alice", "Bob"],
        published_date=datetime.now(),
        categories=["cs.AI"],
        pdf_url="https://...",
        abstract_url="https://...",
        discovered_by="arxiv"
    )
    db.add(paper)
    # Automatically commits
```

**Updating:**
```python
with get_db_session() as db:
    paper = db.query(Paper).filter_by(arxiv_id="2312.12345").first()
    if paper:
        paper.relevance_score = 0.95
        paper.scored_at = datetime.utcnow()
    # Automatically commits
```

**Handling Duplicates:**
```python
from sqlalchemy.exc import IntegrityError

with get_db_session() as db:
    try:
        paper = Paper(arxiv_id="2312.12345", ...)
        db.add(paper)
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.warning("Paper already exists")
```

### 2. Configuration Pattern

```python
# src/config.py defines all settings
from src.config import settings, get_research_interests_list

# Access settings
api_key = settings.anthropic_api_key
model = settings.reader_model
interests = get_research_interests_list()

# Settings are validated at import time - app crashes fast if config is wrong
```

### 3. Logging Pattern

```python
# Set up once in main.py
from loguru import logger

logger.remove()  # Remove default
logger.add(sys.stdout, level="INFO", colorize=True)
logger.add("logs/app.log", rotation="10 MB", retention="30 days")

# Use everywhere
logger.info("Starting process...")
logger.debug(f"Details: {data}")
logger.error(f"Failed: {error}")
```

### 4. CLI Command Pattern

```python
# main.py structure
def handle_command(args):
    """
    Handle a specific command.

    Pattern:
    1. Log what you're doing
    2. Import dependencies (lazy loading)
    3. Try/except with proper error handling
    4. Log success/failure
    """
    logger.info("Starting command...")

    try:
        from src.agents.discovery import discover_papers
        result = discover_papers(days_back=args.days)
        logger.info(f"✅ Success: {result}")
    except Exception as e:
        logger.error(f"❌ Failed: {e}")
        if settings.log_level == "DEBUG":
            logger.exception("Full traceback:")
        sys.exit(1)
```

---

## Common Tasks

### Adding a New CLI Command

1. Add argument to parser in `main.py`:
```python
parser.add_argument(
    "--my-command",
    action="store_true",
    help="Description of what it does"
)
```

2. Create handler function:
```python
def handle_my_command(args):
    """Handle my new command."""
    logger.info("Running my command...")
    # Implementation
```

3. Wire it up in `main()`:
```python
if args.my_command:
    handle_my_command(args)
```

### Adding a New Database Model

1. Define model in `src/models/paper.py`:
```python
class MyNewModel(Base):
    __tablename__ = "my_table"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Add fields...
```

2. Run database migration:
```python
python main.py --init-db --reset  # Development only!
```

### Adding a New Agent

1. Create agent file in `src/agents/`:
```python
# src/agents/my_agent.py
from langgraph import StateGraph
from src.config import settings

def my_agent_node(state: AgentState) -> AgentState:
    """Process state and return updated state."""
    # Implementation
    return state

def create_my_agent() -> StateGraph:
    """Create agent graph."""
    graph = StateGraph()
    graph.add_node("my_node", my_agent_node)
    # Define flow...
    return graph.compile()
```

2. Import and use in main workflow.

### Adding New Configuration

1. Add to `src/config.py`:
```python
my_new_setting: str = Field(
    default="default_value",
    alias="MY_NEW_SETTING",
    description="What this controls"
)
```

2. Add to `.env.example`:
```bash
# My New Feature
MY_NEW_SETTING=example_value
```

3. Document in README.md if user-facing.

---

## Testing & Debugging

### Running Tests

```bash
# All tests
pytest

# Specific file
pytest tests/test_database.py

# Specific test
pytest tests/test_database.py::test_init_db

# With output
pytest -v -s

# With coverage
pytest --cov=src --cov-report=html
```

### Writing Tests

```python
import pytest
from src.database import init_db, get_db_session
from src.models.paper import Paper

def test_create_paper():
    """Test creating a paper."""
    init_db()

    with get_db_session() as db:
        paper = Paper(
            arxiv_id="test.12345",
            title="Test Paper",
            # ... other required fields
        )
        db.add(paper)

    with get_db_session() as db:
        found = db.query(Paper).filter_by(arxiv_id="test.12345").first()
        assert found is not None
        assert found.title == "Test Paper"
```

### Debugging Tips

1. **Use debug logging:**
```bash
python main.py --discover --debug
```

2. **Check database state:**
```bash
python main.py --stats
sqlite3 data/papers.db "SELECT * FROM papers LIMIT 5;"
```

3. **Inspect logs:**
```bash
tail -f logs/app.log
```

4. **Use Python debugger:**
```python
import pdb; pdb.set_trace()  # Breakpoint
```

---

## API Integration

### ArXiv API
- **Library:** `arxiv` Python package
- **Rate Limit:** 3 requests/second
- **Caching:** 1 hour recommended
- **Docs:** https://info.arxiv.org/help/api/index.html

### Claude API (Anthropic)
- **Library:** `anthropic` Python package
- **Models:** Haiku (fast/cheap), Sonnet (quality)
- **Rate Limits:** Tier-based (check console)
- **Best Practice:** Batch similar requests
- **Docs:** https://docs.anthropic.com/

### Twitter API v2
- **Library:** `tweepy`
- **Auth:** Bearer token
- **Rate Limit:** 450 requests/15min
- **Caching:** 15 minutes recommended
- **Docs:** https://developer.twitter.com/en/docs

### Semantic Scholar
- **Library:** `semanticscholar`
- **Rate Limit:** 100 req/5min (no key), 5000 req/5min (with key)
- **Batching:** Up to 500 IDs per request
- **Caching:** 24 hours recommended
- **Docs:** https://api.semanticscholar.org/

### HackerNews
- **API:** Algolia Search API
- **No Auth Required**
- **Query:** Search for "arxiv.org" in stories
- **Docs:** https://hn.algolia.com/api

---

## Important Notes

### For AI Assistants Working on This Code

1. **Always Read Before Modifying**
   - Use `Read` tool to view files before making changes
   - Understand existing patterns before adding new code
   - Check related files (models, config, etc.)

2. **Respect Existing Patterns**
   - Database: Always use `get_db_session()` context manager
   - Logging: Use `loguru.logger`, not `print()`
   - Config: Add to `src/config.py` and `.env.example`
   - Errors: Catch specific exceptions, log properly

3. **Don't Over-Engineer**
   - Keep solutions simple and focused
   - Only add what's requested
   - Don't add extra features "for the future"
   - Avoid premature abstractions

4. **Maintain Documentation**
   - Update this file when adding major features
   - Update docstrings for new functions
   - Update .env.example for new config
   - Keep README.md user-focused

5. **Test Your Changes**
   - Run `python main.py --stats` to verify DB connection
   - Test CLI commands manually
   - Check logs for errors
   - Consider edge cases

6. **Security**
   - Never commit API keys or secrets
   - Always use environment variables
   - Validate user input in CLI commands
   - Use parameterized SQL queries (ORM does this)

7. **Cost Awareness**
   - Use Haiku for simple extraction tasks
   - Use Sonnet for complex explanations
   - Batch API calls when possible
   - Implement caching to avoid redundant calls

### Current State (Week 1 Implementation)

✅ **Completed:**
- Project structure and setup
- Configuration management
- Database schema and models
- CLI framework
- Logging infrastructure
- ArXiv discovery (basic)

🚧 **In Progress:**
- Reader agent (analysis)
- Explainer agent
- Email digest generation

📋 **Upcoming:**
- Week 2: Social signals (Twitter, HN)
- Week 3: Citation tracking and velocity
- Week 4: Knowledge graph visualization
- Week 5: Reading progress dashboard
- Week 6: Production polish and synthesis

### Getting Help

- **LangGraph Docs:** https://python.langchain.com/docs/langgraph
- **Claude API:** https://docs.anthropic.com/
- **SQLAlchemy:** https://docs.sqlalchemy.org/
- **Streamlit:** https://docs.streamlit.io/
- **Design Doc:** `docs/design.md`
- **Project Plan:** `docs/project_plan.md`

---

## Quick Reference

### Common Commands
```bash
# Setup
python main.py --init-db

# Discover papers
python main.py --discover --days 1

# Check status
python main.py --stats

# Debug mode
python main.py --discover --debug

# Reset database
python main.py --init-db --reset --yes
```

### Import Patterns
```python
# Configuration
from src.config import settings, get_research_interests_list

# Database
from src.database import get_db_session, init_db
from src.models.paper import Paper, Citation, SocialSignal

# Logging
from loguru import logger

# Agents (when implemented)
from src.agents.discovery import discover_papers
```

### Database Queries
```python
# Simple query
with get_db_session() as db:
    papers = db.query(Paper).all()

# Filter
with get_db_session() as db:
    paper = db.query(Paper).filter_by(arxiv_id="2312.12345").first()

# Complex
with get_db_session() as db:
    papers = db.query(Paper)\
        .filter(Paper.relevance_score > 0.8)\
        .order_by(Paper.published_date.desc())\
        .limit(10)\
        .all()
```

---

**End of CLAUDE.md**

This document should be updated as the project evolves. When adding major features, update the relevant sections to keep this guide accurate and useful.
