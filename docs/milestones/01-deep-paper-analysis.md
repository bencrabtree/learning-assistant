# Milestone 1: Deep Paper Analysis Engine

## The Ideal

A researcher can comprehend a complex AI paper in **minutes** rather than hours - understanding not just *what* it claims, but *how* it works and *why* it matters.

## The Problem

- **200-300 AI papers** published daily on arXiv
- Abstracts alone don't provide deep understanding
- Reading full papers is time-consuming (2-4 hours each)
- No way to quickly assess if a paper is worth the time investment

## The Solution

Build an AI-powered analysis engine that:

1. **Extracts structured information** from papers (claims, methodology, results)
2. **Generates accessible explanations** for complex concepts
3. **Provides learning scaffolding** (prerequisites, questions to explore)
4. **Creates audit trails** for transparency and reproducibility

## Core Capabilities

### Reader Agent (Claude 3.5 Haiku)

**Purpose:** Fast, structured extraction of paper content

**Extracts:**
- `main_claim`: The central thesis of the paper
- `methodology`: How they approached the problem
- `key_results`: What they found
- `novel_contributions`: What's new compared to prior work
- `limitations`: Acknowledged weaknesses or scope constraints
- `concepts`: Key technical concepts used

**Why Haiku:** Speed and cost-efficiency for extraction tasks (~$0.001 per paper)

### Explainer Agent (Claude 3.5 Sonnet)

**Purpose:** Transform technical content into accessible learning material

**Generates:**
- `eli5_summary`: Explain-like-I'm-5 version of the paper
- `key_insight`: The one thing to remember
- `learning_questions`: Questions to deepen understanding
- `prerequisites`: What you should know first
- `related_concepts`: Connections to other ideas

**Why Sonnet:** Better at nuanced explanations and teaching (~$0.015 per paper)

### Citation Integration (Semantic Scholar)

**Purpose:** Provide initial relevance signals

**Tracks:**
- Citation count (community validation)
- Influential citations (high-quality references)
- Paper metadata (authors, venue, year)

**Why It Matters:** Citations indicate papers the research community values

### Audit Trail System

**Purpose:** Full transparency on analysis provenance

**Tracks:**
- `analyzed_at`: When Reader Agent processed the paper
- `explained_at`: When Explainer Agent generated learning content
- `discovered_by`: Source that found the paper (arxiv, twitter, etc.)
- `citations_updated_at`: Last citation data refresh

**Why It Matters:** Reproducibility and debugging - know exactly when/how analysis happened

## User Experience

### Rich Terminal UI

Beautiful command-line interface with:
- **Color-coded output** (importance levels, status indicators)
- **Structured display** (sections, headers, bullet points)
- **Interactive exploration** (drill into details)

### Basic Relevance Scoring

Simple keyword-matching algorithm:
- Match user research interests against paper concepts
- Score 0-1 (foundation for future ML-based scoring)
- Filter noise, surface relevant papers

## Technical Architecture

```
┌─────────────────────────────────────────┐
│          Discovery Pipeline             │
│  (arXiv API → Raw Paper Metadata)       │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│           Reader Agent                  │
│  (Haiku → Structured Extraction)        │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│         Explainer Agent                 │
│  (Sonnet → Learning Content)            │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│        SQLite Database                  │
│  (Papers + Analysis + Explanations)     │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│          Rich CLI Display               │
│  (Terminal UI with colors/formatting)   │
└─────────────────────────────────────────┘
```

## Database Schema

### Paper Model

Core fields:
- Identity: `arxiv_id`, `title`, `authors`, `abstract`
- Discovery: `discovered_at`, `discovered_by`
- Analysis: `main_claim`, `methodology`, `key_results`, `limitations`, `concepts`
- Explanation: `eli5_summary`, `key_insight`, `learning_questions`, `prerequisites`
- Citations: `citation_count`, `influential_citation_count`
- Audit: `analyzed_at`, `explained_at`, `citations_updated_at`

## Success Metrics

- **Analysis speed:** < 30 seconds per paper (Haiku + Sonnet combined)
- **Cost efficiency:** < $0.02 per paper (extraction + explanation)
- **User comprehension:** Researchers understand paper core in 5-10 minutes
- **Coverage:** 80% of discovered papers analyzed within 24 hours

## What This Enables

This milestone creates the **foundation** for everything else:

- **Social signals** (Milestone 2) need analyzed papers to rank
- **Citation velocity** (Milestone 3) builds on citation data collected here
- **Knowledge graphs** (Milestone 4) connect papers based on concepts extracted here
- **Progress tracking** (Milestone 5) monitors which analyzed papers you've read
- **Synthesis** (Milestone 6) summarizes insights from explained content

Without deep paper analysis, the system is just a discovery feed. With it, we enable **learning**.

## Key Decisions

### Why Two Agents (Reader + Explainer)?

**Separation of concerns:**
- Reader: Fast, cheap, structured extraction (data processing)
- Explainer: Thoughtful, nuanced teaching (learning support)

**Different models for different tasks:**
- Haiku excels at extraction and structured output
- Sonnet excels at explanations and teaching

### Why Keyword Matching for Scoring?

**Simplicity first:**
- Keyword matching is transparent and debuggable
- Provides immediate utility (filter noise)
- Foundation for future ML-based scoring

**Future enhancement path:**
- Collect user feedback on relevance
- Train embedding-based similarity model
- Incorporate citation velocity and social signals

### Why SQLite?

**Development speed:**
- Zero configuration
- Single-file portability
- Excellent for < 1M papers

**Future path to Postgres:**
- Schema is PostgreSQL-compatible
- Easy migration when scale demands it

## What's Next

After this milestone, we have papers deeply analyzed and explained. Next milestone adds **social proof** to identify which papers the research community is excited about right now.
