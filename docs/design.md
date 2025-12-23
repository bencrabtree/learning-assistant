# System Design Document

**Project:** ArXiv Learning Assistant  
**Version:** 1.0  
**Last Updated:** December 2025

---

## Overview

### Problem Statement

AI researchers face 200-300 new papers daily on arXiv cs.AI alone. Current solutions are insufficient:
- arXiv RSS: Too noisy, no filtering
- Twitter/HN: Serendipitous but incomplete
- Manual tracking: Time-consuming

### Solution

Multi-agent system that discovers, analyzes, explains, curates, and tracks papers with personalized learning paths.

### Design Principles

1. **Modularity** - Each agent is independent and testable
2. **Incremental Value** - Each phase delivers usable features
3. **Low Latency** - Async operations, caching, batching
4. **Cost Efficient** - Haiku for simple tasks, Sonnet for explanations
5. **Extensible** - Easy to add new sources

---

## Architecture

### High-Level System Design

```
User Interface Layer
├── Email Digest
├── Dashboard (Streamlit)
└── CLI Commands

Application Layer (LangGraph)
├── Supervisor Agent (Orchestrator)
├── Discovery Agent → ArXiv, Twitter, HN, Citations, Labs
├── Reader Agent → Extract structure
├── Explainer Agent → Simplify concepts
├── Curator Agent → Rank and filter
├── Graph Builder → Build relationships
└── Recommendation Agent → Suggest next reads

Data Layer
├── SQLite DB (Papers, Citations, Progress)
├── Graph Store (NetworkX)
└── Cache (Redis optional)

External Services Layer
├── ArXiv API
├── Twitter API
├── Semantic Scholar
├── Claude API
└── SMTP (Email)
```

### Technology Stack

**Core:**
- langgraph 0.3+, langchain 0.1+, anthropic 0.18+

**Data:**
- sqlalchemy 2.0+, sqlite3, networkx 3.2+, redis (optional)

**Discovery:**
- arxiv 2.1+, tweepy 4.14+, requests, beautifulsoup4, semanticscholar 0.8+

**Visualization:**
- streamlit 1.29+, plotly 5.18+, pyvis 0.3+

**Utilities:**
- apscheduler 3.10+, pydantic 2.5+, python-dotenv 1.0+, loguru 0.7+

---

## Agent Design

### LangGraph State Machine

All agents share a common state object:

**AgentState TypedDict:**
- research_interests: List[str]
- date_range: tuple[datetime, datetime]
- raw_papers: List[dict]
- social_signals: dict
- citation_data: dict
- analyzed_papers: List[dict]
- explained_papers: List[dict]
- scored_papers: List[dict]
- final_selection: List[dict]
- errors: List[str]
- api_calls: dict

### Agent Specifications

#### 1. Discovery Agent (Coordinator)

**Sub-agents:**
- ArxivSearcher - Query arXiv API by category/keyword
- TwitterTracker - Monitor AI lab accounts
- HNTracker - Scrape HackerNews
- CitationTracker - Fetch citation counts/velocity
- LabTracker - Scrape lab publication pages

**Process:** Run all sub-agents in parallel → merge → deduplicate by arxiv_id

**Caching:**
- arXiv: 1 hour
- Twitter/HN: 15 minutes
- Citations: 24 hours

#### 2. Reader Agent

**Input:** Raw paper (title, abstract, authors, arxiv_id)

**Output Structure:**
- main_claim
- methodology
- key_results (List)
- novel_contributions
- limitations
- concepts (List)

**Model:** Claude 3.5 Haiku (fast, cheap, good at extraction)
**Cost:** ~$0.001 per paper

#### 3. Explainer Agent

**Input:** Structured analysis from Reader

**Output Structure:**
- eli5_summary
- key_insight
- learning_questions (List)
- prerequisites (List)
- related_concepts (List)

**Model:** Claude 3.5 Sonnet (better explanations)
**Cost:** ~$0.015 per paper

#### 4. Curator Agent

**Scoring Algorithm:**
- Interest match (40%) - Semantic similarity to research interests
- Social proof (25%) - Twitter mentions + HN score
- Citation velocity (20%) - Rate of new citations
- Recency (10%) - How new the paper is
- Lab prestige (5%) - Published by top lab

**Output:** Top N papers ranked by total score

---

## Data Models

### Core Entities

**Paper:**
- arxiv_id (PK)
- title, authors, abstract, published_date
- categories, pdf_url, abstract_url
- discovered_at, discovered_by
- Analysis fields (main_claim, methodology, key_results, etc)
- Explanation fields (eli5_summary, key_insight, etc)
- Scoring fields (relevance_score, components)
- lab_published_by

**Citation:**
- paper_id (FK)
- citation_count, measured_at
- citations_this_week, velocity_score
- source (semantic_scholar)

**SocialSignal:**
- paper_id (FK)
- source (twitter, hn, reddit)
- source_url, score, comments_count
- snippet, author, posted_at

**ReadingProgress:**
- paper_id (FK)
- status (unread, reading, finished, archived)
- started_at, finished_at
- rating (1-5), notes
- time_spent_minutes

**Concept:**
- name, papers (List of arxiv_ids)
- mastery_level (beginner/intermediate/advanced)
- first_encountered, last_encountered

**PaperRelationship:**
- source_paper_id, target_paper_id
- relationship_type (cites, builds_on, extends)
- strength (0-1)

---

## Discovery Pipeline

### Phase 1: Multi-Source Fetching (Parallel)
Run all discovery sources concurrently → Merge results → Deduplicate by arxiv_id

### Phase 2: Enrichment (Sequential)
Batch fetch citations (max 100 per request) → Calculate velocity → Build relationships

### Phase 3: Analysis (Batched LLM)
Batch papers in groups of 10 → Reader agent (Haiku) → Explainer agent (Sonnet) → Merge results

---

## Knowledge Graph

### Graph Construction

**Nodes:** Papers  
**Edges:** Relationships (citations, concept overlap, author overlap)

### Graph Analysis

- Most influential (PageRank)
- Topic clusters (Community detection)
- Reading order (Topological sort)
- Knowledge gaps (Disconnected components)
- Similar papers (Shortest paths)

### Visualization

**Node styling:**
- Color: Reading status (red=unread, yellow=reading, green=finished)
- Size: Relevance score
- Label: Paper title (truncated)

**Edge styling:**
- Width: Relationship strength
- Type: Citation vs concept similarity

**Physics:** Force-directed layout with adjustable gravity/spring length

---

## Scoring Algorithm

### Multi-Signal Ranking Weights

```
WEIGHT_INTEREST_MATCH = 0.40    # 40%
WEIGHT_SOCIAL_PROOF = 0.25      # 25%
WEIGHT_CITATION_VELOCITY = 0.20 # 20%
WEIGHT_RECENCY = 0.10           # 10%
WEIGHT_LAB_PRESTIGE = 0.05      # 5%
```

### Interest Match
Use sentence-transformers (all-MiniLM-L6-v2) for semantic similarity between paper concepts and user interests. Returns 0-1 score.

### Social Proof Score
Combine Twitter mentions (weighted by follower count) + HN points/comments. Normalize and cap.

### Citation Velocity
Calculate % growth week-over-week. Flag "breakout papers" with >20% velocity.

---

## API Integrations

### arXiv API
- Rate limit: 3 requests/second
- Cache: 1 hour
- Batch queries when possible

### Twitter API (v2)
- Rate limit: 450 requests/15min
- Cache: 15 minutes
- Use bearer token auth

### Semantic Scholar API
- Rate limit: 100 req/5min (no key), 5000 req/5min (with key)
- Batch: Up to 500 IDs per request
- Cache: 24 hours

### HackerNews Algolia API
- No auth required
- Search for "arxiv.org" in stories
- Rate limit: Respect API guidelines

---

## Performance Considerations

### Latency Targets
- Discovery: < 10 seconds for 3-day window
- Analysis: < 30 seconds for 20 papers
- Graph build: < 5 seconds for 1000 papers
- Dashboard load: < 2 seconds

### Optimization Strategies

**1. Caching**
- Use Redis or in-memory dict
- Different TTLs per source

**2. Async/Parallel**
- Run discovery sources concurrently
- Batch LLM calls

**3. Batch API Calls**
- Semantic Scholar: 500 IDs per request
- Claude: 10 papers per batch

**4. Database Indexing**
- Index: published_date, relevance_score, concepts
- Use GIN index for JSON arrays

---

## Security & Privacy

### API Keys
- Store in .env (never commit)
- Provide .env.example template

### Data Privacy
- No personal data collection
- Local SQLite storage
- No telemetry

### Rate Limiting
- Implement sleep_and_retry decorators
- Respect API rate limits

---

## Future Enhancements

### Phase 7+
- Podcast generation (NotebookLM style)
- Obsidian integration
- Mobile app (React Native)
- Collaborative features
- PDF processing
- Code analysis
- Multi-language support
- Browser extension

---

**End of Design Document**
