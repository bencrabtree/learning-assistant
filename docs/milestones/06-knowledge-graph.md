# Milestone 6: Interactive Knowledge Graph

**Status:** Planned
**Priority:** Medium
**Dependencies:** Milestone 5 (Citation Velocity)

## The Ideal

Researchers can **visually explore the research landscape** - seeing how papers connect, identifying influential works, and discovering optimal reading paths.

## The Problem

- **Papers exist in isolation:** Current view is linear list, no relationships shown
- **Hard to find reading order:** Which papers should you read first to understand later ones?
- **Topic clusters invisible:** Can't see emerging research areas or communities
- **Influence unclear:** Which papers are most central to the field?

## The Solution

Build an **interactive, visual knowledge graph** where:

1. **Nodes = Papers** (sized by importance, colored by reading status)
2. **Edges = Citations** (weighted by relationship strength)
3. **Algorithms reveal structure** (PageRank, communities, reading paths)
4. **Web dashboard enables exploration** (filter, zoom, click for details)

## Core Capabilities

### Graph Construction (NetworkX)

**Nodes:**
- Paper metadata (title, authors, abstract)
- Computed properties (PageRank, community, centrality)
- Reading status (unread, reading, finished, archived)

**Edges:**
- Citation relationships (A cites B)
- Edge weight = citation context strength (how important the citation is)
- Directional (A → B means A cites B)

**Graph statistics:**
- \# nodes, # edges, density
- Average degree, clustering coefficient
- Connected components

### Graph Algorithms

**PageRank (Influence Detection):**
- Identifies most influential papers
- Papers cited by influential papers rank higher
- Used to size nodes in visualization

**Louvain Community Detection:**
- Finds topic clusters/research communities
- Papers that heavily cite each other cluster together
- Used to color nodes by topic

**Topological Sort (Reading Order):**
- Finds optimal reading sequence
- Papers with no prerequisites come first
- Papers that cite others come after
- Detects circular citations (manual ordering needed)

**Centrality Measures:**
- **Betweenness:** Papers that bridge different topics
- **Closeness:** Papers central to entire graph
- **Degree:** Most connected papers

### Interactive Visualization (PyVis)

**Physics simulation:**
- Papers repel each other (anti-gravity)
- Citations pull papers together (spring force)
- Graph self-organizes into meaningful layout

**Node styling:**
- **Size:** By PageRank (influence)
- **Color:** By reading status
  - Red: Unread
  - Yellow: Currently reading
  - Green: Finished
  - Gray: Archived
- **Label:** Paper title (hover for details)

**Edge styling:**
- **Thickness:** By citation strength
- **Arrows:** Show citation direction
- **Curved:** Avoid overlap

**Interactivity:**
- Click node: Show paper details, analysis, explanation
- Hover node: Preview title and metadata
- Zoom/pan: Explore large graphs
- Filter: By date, status, topic, author

### Streamlit Dashboard

**Multi-page web app:**

**Page 1: Knowledge Graph**
- Interactive Pyvis visualization
- Filters (date range, reading status, topic)
- Search (find specific papers)
- Export (PNG, SVG, JSON)

**Page 2: Reading Paths**
- Topological sort recommendations
- "What should I read next?" based on prerequisites
- "Papers that cite this one" (what builds on it)
- "Papers this cites" (what it builds on)

**Page 3: Topic Clusters**
- Community detection results
- Papers grouped by research area
- Topic labels (auto-generated from keywords)
- Cluster statistics

**Page 4: Paper Search**
- Full-text search across titles/abstracts
- Filter by multiple dimensions
- Quick analysis view

## User Experience

### Visual Exploration

**Scenario: Understanding a research area**

1. **Load graph:** All papers from past 6 months
2. **Run community detection:** See 5-8 topic clusters emerge
3. **Click a cluster:** See papers in that research area
4. **Identify hub papers:** Largest nodes = most influential
5. **Find reading path:** Topological sort shows order
6. **Track progress:** Color changes as you read papers

### Discovery Workflows

**"What are the foundations of this paper?"**
- Click paper → Show papers it cites → Color by reading status
- Reveals what you need to read first

**"What builds on this paper?"**
- Click paper → Show papers citing it → Sort by PageRank
- Reveals what's important in the literature that followed

**"What should I read in this topic cluster?"**
- Select community → Sort by PageRank → Start with highest-ranked unread paper
- Ensures you read most influential works first

## Technical Architecture

```
┌─────────────────────────────────────────┐
│    Citation Data (from Milestone 3)    │
│  (papers + citation relationships)      │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│     NetworkX Graph Construction         │
│  (nodes=papers, edges=citations)        │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│       Graph Algorithm Pipeline          │
│  PageRank → Community → Centrality      │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│         PyVis Visualization             │
│  (HTML + JS interactive graph)          │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│       Streamlit Dashboard               │
│  (web UI for exploration)               │
└─────────────────────────────────────────┘
```

## Database Schema Additions

### Paper Model Extensions

Add computed graph properties:
```python
class Paper:
    # ... existing fields ...

    # Graph properties
    pagerank_score: float | None       # Influence measure
    community_id: int | None           # Topic cluster
    betweenness_centrality: float | None
    degree: int | None                 # # of citations
```

## Success Metrics

- **Graph size:** 500+ papers, 2000+ citation edges
- **Community detection:** Identifies 5-10 meaningful topic clusters
- **Reading path accuracy:** 90%+ of topological sort suggestions are logically sound
- **User engagement:** Researchers spend 10+ minutes exploring graph per session
- **Discoverability:** Users find 3+ relevant papers via graph navigation

## What This Enables

**Builds on previous milestones:**
- M1 (Analysis): Shows analyzed paper details on click
- M2 (Social Signals): Can size/color nodes by social proof
- M3-M4 (Radar & Agentic): Integrates with discovery workflow
- M5 (Citation Velocity): Can animate graph over time, show velocity trends

**Enables future milestones:**
- M7 (Progress Tracking): Visual progress indicator (% of graph read)
- M8 (Synthesis): Identify themes by analyzing community structures

## Key Decisions

### Why NetworkX vs Neo4j?

**Development speed:**
- NetworkX: Pure Python, no database setup
- Neo4j: Graph database, more setup complexity

**Scale considerations:**
- NetworkX: Good for < 100K nodes (plenty for this use case)
- Neo4j: Better for millions of nodes

**Future path:** Can migrate to Neo4j if graph exceeds 50K papers

### Why PyVis vs D3.js?

**Ease of use:**
- PyVis: Python → HTML in 5 lines of code
- D3.js: Requires JavaScript expertise, more control

**Good enough:**
- PyVis physics engine works well
- Interactivity sufficient for exploration

**Future:** Could add D3 for custom visualizations if needed

### Why Streamlit vs Custom Web App?

**Rapid prototyping:**
- Streamlit: Dashboard in minutes, auto-reload, clean UI
- Custom app: More work, more control

**Dashboard fit:**
- Streamlit excellent for data apps
- Less suitable for production SaaS

**Future:** Production version could use FastAPI + React

### Why Store Graph Properties in Database?

**Performance:**
- PageRank/community detection take 5-30 seconds
- Pre-compute and cache in database
- Refresh nightly

**Queryability:**
- Can query "papers with PageRank > 0.8"
- Can filter by community

## What's Next

After this milestone, we have a visual research landscape. Next milestone adds **progress tracking** to monitor your learning journey and generate personalized recommendations.
