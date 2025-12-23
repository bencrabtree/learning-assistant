# Week 4: Knowledge Graph Visualization

**Goal:** Interactive graph showing how papers connect

**Time:** 12-15 hours  
**Cost:** $15-25  
**Deliverable:** Web UI with clickable knowledge graph

---

## Day 1 (Saturday): Graph Construction (4-5 hours)

### Tasks

- [ ] Build NetworkX graph from database
- [ ] Nodes: Papers (with metadata)
- [ ] Edges: Citations (directed), concept overlap
- [ ] Edge weights: Relationship strength
- [ ] Implement graph algorithms
  - PageRank (influential papers)
  - Community detection (topic clusters)
  - Shortest path (reading prerequisites)
  - Centrality measures
- [ ] Cache graph (Redis or pickle)

### Files to Create

- `src/services/graph_analyzer.py`
- `src/services/graph_cache.py`

### Graph Algorithms

- **PageRank:** Find most influential papers
- **Louvain:** Detect topic communities
- **Topological sort:** Reading order
- **Shortest path:** Prerequisites between papers

### Acceptance Criteria

✅ Graph built from database  
✅ Algorithms return results  
✅ Graph cached for performance

---

## Day 2 (Sunday Morning): Interactive Visualization (4-5 hours)

### Tasks

- [ ] Choose visualization: Pyvis (recommended for MVP)
- [ ] Create graph renderer
- [ ] Node colors: by reading status
  - Red: unread
  - Yellow: reading
  - Green: finished
  - Gray: archived
- [ ] Node sizes: by importance (PageRank)
- [ ] Edge thickness: by strength
- [ ] Interactive: click to see details
- [ ] Physics simulation for layout
- [ ] Export as HTML

### Files to Create

- `src/visualization/graph_renderer.py`
- `src/visualization/templates/graph.html`

### Interactivity

- Click node → show paper details
- Hover → see title/abstract
- Zoom/pan controls
- Filter by date/status/topic

### Acceptance Criteria

✅ Graph renders in browser  
✅ Nodes/edges styled correctly  
✅ Interactive features work  
✅ Exports as standalone HTML

---

## Day 3 (Sunday Afternoon): Streamlit Dashboard (2-3 hours)

### Tasks

- [ ] Create Streamlit app
- [ ] Sidebar: Filters (date, status, topics)
- [ ] Main: Embedded graph visualization
- [ ] Add graph controls
  - Zoom, filter, search
- [ ] Display paper details on click
  - Title, abstract, ELI5, questions
  - Links: arXiv, PDF, citations

### Files to Create

- `src/dashboard/app.py`
- `src/dashboard/components/graph_view.py`
- `src/dashboard/components/paper_details.py`

### Dashboard Layout

```
Sidebar:
- Date range filter
- Status filter
- Topic filter
- Search box

Main:
- Graph visualization
- Paper details panel (appears on click)
```

### Run Command

```bash
streamlit run src/dashboard/app.py
```

### Acceptance Criteria

✅ Dashboard loads at localhost:8501  
✅ Filters work  
✅ Graph embedded properly  
✅ Paper details display on click

---

## Day 4 (Weeknight): Graph Features (1-2 hours)

### Tasks

- [ ] Add "Reading Path" feature
  - Topological sort of citation graph
  - Show optimal reading order
  - Highlight prerequisite papers
- [ ] Add "Similar Papers" finder
  - Based on concept overlap
  - Based on citation proximity
- [ ] Add "Topic Clusters" view
  - Visualize communities (different colors)
  - Label clusters with topics

### Files to Update

- `src/services/graph_analyzer.py` - New algorithms
- `src/dashboard/components/reading_path.py` - New component

### Reading Path

Given a paper, find:
1. Prerequisites (papers it cites)
2. Optimal order to read them
3. Display as vertical path in graph

### Acceptance Criteria

✅ Reading path calculates correctly  
✅ Similar papers found  
✅ Topic clusters visible

---

## Day 5 (Weeknight): Polish & Export (1-2 hours)

### Tasks

- [ ] Add graph export
  - PNG/SVG for sharing
  - JSON for Obsidian import
- [ ] Optimize performance
  - Lazy load large graphs
  - Limit visible nodes (top 100)
  - Add pagination
- [ ] Write dashboard guide

### Files to Create

- `docs/dashboard_guide.md`
- `src/visualization/graph_exporter.py`

### Performance

For large graphs (>200 papers):
- Show only top 100 by relevance
- Add "Load more" button
- Filter to specific date range

### Acceptance Criteria

✅ Can export graph as image  
✅ Large graphs perform well  
✅ Documentation complete

---

## Week 4 Acceptance Criteria

- ✅ Can visualize paper citation graph
- ✅ Interactive: click, zoom, filter
- ✅ Nodes colored by reading status
- ✅ Shows prerequisite reading paths
- ✅ Identifies topic clusters
- ✅ Web dashboard runs locally
- ✅ Can export graph

---

## Deliverable

```bash
streamlit run src/dashboard/app.py

# Features:
# - Visual graph of all papers
# - Click paper → see explanation
# - "Show Reading Path" button
# - Filter by status/topic/date
# - Export graph as PNG
```

---

## Troubleshooting

**Graph won't load:**
- Check database has papers with relationships
- Reduce number of visible nodes

**Dashboard slow:**
- Enable caching in config
- Limit graph to 100 nodes
- Use Streamlit caching decorators

**Export fails:**
- Install dependencies: `pip install kaleido`
- Check write permissions

---

## Code Checkpoint

```bash
git commit -m "Week 4: Knowledge graph visualization"
git tag week4-knowledge-graph
```

---

[← Week 3](week3.md) | [Week 5 →](week5.md)
