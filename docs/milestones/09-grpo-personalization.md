# Milestone 9: GRPO Personalization

**Status:** Planned
**Priority:** High - Core differentiator
**Dependencies:** Milestone 7 (Learning Progress), Milestone 4 (Agentic LangGraph)

---

## Overview

Use GRPO (Group Relative Policy Optimization) to fine-tune the analysis agent on user preferences. The system learns what papers YOU find interesting and adjusts its scoring and explanations accordingly.

**The Problem:**
- Current scoring uses static weights (interest: 25%, social: 25%, citation: 20%, breakthrough: 30%)
- "Research interests" are manually configured keywords
- No learning from user feedback over time
- Same analysis style for all users

**The Solution:**
- Collect preference signals from favorites, ratings, reading patterns
- Extract preference embeddings from seed papers
- Use GRPO to fine-tune analysis agent on preference data
- Continuously improve as user provides more feedback

---

## Architecture

### Feedback Collection

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        FEEDBACK SIGNALS                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   EXPLICIT FEEDBACK                    IMPLICIT FEEDBACK                 │
│   ─────────────────                    ─────────────────                 │
│                                                                          │
│   --like <paper>    ──┐                Reading time      ──┐            │
│   --rate good/bad   ──┼──► Preference  Click-through     ──┼──► Signals │
│   --favorite        ──┘    Database    Email opens       ──┘            │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Preference Extraction

From your seed papers, extract:

1. **Topic Preferences**
   - Concepts that appear frequently (GRPO, test-time compute, reasoning)
   - Categories preferred (cs.AI, cs.LG, cs.CL)
   - Research areas (RL, language models, multimodal)

2. **Paper Type Preferences**
   - Major releases vs incremental improvements
   - Theoretical vs empirical
   - Open-source vs proprietary
   - Length/depth preferences

3. **Quality Signals**
   - What makes a paper "good" to you?
   - Breakthrough threshold calibration
   - Social proof sensitivity

### GRPO Training Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        GRPO TRAINING PIPELINE                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   1. PREPARE TRAINING DATA                                               │
│   ─────────────────────────                                              │
│   Favorites (positive) ──► Format as preference pairs                    │
│   Ignored (negative)   ──►                                               │
│                                                                          │
│   2. EXTRACT PREFERENCE EMBEDDING                                        │
│   ────────────────────────────────                                       │
│   Seed papers ──► Claude analysis ──► Preference description             │
│   "User prefers: GRPO variants, test-time compute, major model          │
│    releases. Values: breakthrough potential, practical impact."          │
│                                                                          │
│   3. GRPO FINE-TUNING                                                    │
│   ───────────────────                                                    │
│   Base model + Preference pairs ──► GRPO training ──► Personalized model │
│                                                                          │
│   4. DEPLOY & ITERATE                                                    │
│   ───────────────────                                                    │
│   Use personalized model for analysis                                    │
│   Collect new feedback ──► Periodic retraining                          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Preference Data Collection
- [x] Favorites system (`--like`, `--unlike`, `--favorites`)
- [x] Seed paper concept extraction
- [x] Interest scoring from favorites
- [ ] Rating system integration (good/neutral/bad)
- [ ] Reading time tracking
- [ ] Preference database schema

### Phase 2: Preference Extraction
- [ ] Analyze seed papers for common themes
- [ ] Generate preference description prompt
- [ ] Create preference embedding from favorites
- [ ] Build comparison pairs (liked vs ignored)

### Phase 3: GRPO Training
- [ ] Format training data for GRPO
- [ ] Set up training pipeline (local or API-based)
- [ ] Train personalized scorer
- [ ] Evaluate on held-out preferences

### Phase 4: Deployment
- [ ] Integrate personalized model into scoring
- [ ] A/B test personalized vs baseline
- [ ] Continuous learning from new feedback
- [ ] Model versioning and rollback

---

## Key Technical Decisions

### What to Personalize?

**Option A: Scoring weights only**
- Simplest approach
- Learn optimal weights for (interest, social, citation, breakthrough)
- Pro: No model training required
- Con: Limited personalization

**Option B: Preference prompt injection**
- Add preference description to analysis prompts
- "This user prefers papers about GRPO and test-time compute..."
- Pro: Works with any model, easy to update
- Con: Uses tokens, may not deeply influence

**Option C: Full GRPO fine-tuning** (Recommended)
- Fine-tune analysis model on preference pairs
- Most powerful personalization
- Pro: Deep learning of preferences
- Con: Requires training infrastructure

### Training Data Format

```json
{
  "preferred": {
    "arxiv_id": "2501.12948",
    "title": "DeepSeek-R1: Incentivizing Reasoning...",
    "concepts": ["reinforcement learning", "reasoning", "GRPO"],
    "user_action": "favorited"
  },
  "rejected": {
    "arxiv_id": "2512.19156",
    "title": "Classical billiards can compute...",
    "concepts": ["Turing completeness", "physics"],
    "user_action": "ignored"
  }
}
```

### Minimum Data Requirements

- **10+ favorites** before first training
- **50+ preference pairs** for meaningful personalization
- **Weekly retraining** with accumulated data

---

## Success Metrics

1. **Preference Accuracy**
   - Can model predict which papers user will like?
   - Target: 80%+ accuracy on held-out test set

2. **Email Engagement**
   - Click-through rate on digest emails
   - Rating distribution (more "good" than "bad")

3. **Qualitative Satisfaction**
   - User reports receiving more relevant papers
   - Fewer "why did I get this?" complaints

---

## Dependencies

- **Milestone 7**: Reading progress and rating system
- **Milestone 4**: Agentic workflow for training integration
- **Infrastructure**: GPU access for training (or API-based approach)

---

## Resources

- [GRPO Paper](https://arxiv.org/abs/2402.03300) - DeepSeekMath
- [Anthropic Fine-tuning Docs](https://docs.anthropic.com/en/docs/fine-tuning)
- [Preference Learning Survey](https://arxiv.org/abs/2312.16171)

---

## Notes

This milestone transforms the assistant from a generic tool to a **personal research companion** that genuinely understands your interests. The feedback loop is key:

```
Use system ──► Provide feedback ──► Model improves ──► Better recommendations ──► Use more
```

The more you use it, the better it gets. This is the core value proposition.
