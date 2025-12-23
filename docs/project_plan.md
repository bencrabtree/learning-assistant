# Project Plan: ArXiv Learning Assistant

**Timeline:** 6 weeks (December 2025 - February 2026)  
**Total Effort:** ~60-75 hours  
**Budget:** $60-125 (Claude API costs)

---

## Overview

Incremental 6-week build delivering usable features each week. Every week builds on previous work and ships working code.

## Weekly Plans

📋 **[Week 1: Foundation - Core Discovery & Explanation](weekly/week1.md)**  
Goal: Daily email with AI-explained papers  
Time: 12-15 hours | Cost: $10-30

📋 **[Week 2: Social Signals - Twitter & HackerNews](weekly/week2.md)**  
Goal: Papers ranked by social proof  
Time: 10-12 hours | Cost: $5-15

📋 **[Week 3: Citation Intelligence - Velocity Tracking](weekly/week3.md)**  
Goal: Surface trending papers  
Time: 10-12 hours | Cost: $10-20

📋 **[Week 4: Knowledge Graph Visualization](weekly/week4.md)**  
Goal: Interactive graph showing connections  
Time: 12-15 hours | Cost: $15-25

📋 **[Week 5: Reading Progress Dashboard](weekly/week5.md)**  
Goal: Track learning journey  
Time: 10-12 hours | Cost: $10-20

📋 **[Week 6: Polish & Advanced Features](weekly/week6.md)**  
Goal: Production-ready system  
Time: 8-10 hours | Cost: $10-15

---

## Success Metrics

### After Week 1
- ✅ Receiving daily emails
- ✅ Papers relevant to interests
- ✅ Explanations are helpful

### After Week 3
- ✅ Email highlights important papers
- ✅ System runs automatically
- ✅ Low false positives (<10%)

### After Week 6
- ✅ Use dashboard regularly (3+ times/week)
- ✅ Reading 2x more papers
- ✅ Feel less overwhelmed
- ✅ Recommend to colleagues

---

## Time & Cost Summary

| Week | Focus | Hours | Cost | Deliverable |
|------|-------|-------|------|-------------|
| 1 | Foundation | 12-15 | $10-30 | Email digest |
| 2 | Social Signals | 10-12 | $5-15 | Twitter/HN ranking |
| 3 | Citations | 10-12 | $10-20 | Trending papers |
| 4 | Knowledge Graph | 12-15 | $15-25 | Interactive viz |
| 5 | Dashboard | 10-12 | $10-20 | Progress tracking |
| 6 | Polish | 8-10 | $10-15 | Production ready |
| **Total** | **62-76** | **$60-125** | **Complete system** |

**Monthly Ongoing:** $15-30 (mostly Claude API)

---

## Getting Help

### Resources
- **LangGraph Docs:** https://python.langchain.com/docs/langgraph
- **Claude API:** https://docs.anthropic.com/
- **Streamlit Docs:** https://docs.streamlit.io/
- **NetworkX Guide:** https://networkx.org/documentation/

### Troubleshooting

**Common Issues:**
- API connection errors → Check .env keys
- No papers found → Verify arXiv categories
- Email not sending → Check SMTP credentials
- Dashboard slow → Enable Redis caching

See individual weekly plans for detailed troubleshooting.

---

**Ready to start Week 1!** 🚀
