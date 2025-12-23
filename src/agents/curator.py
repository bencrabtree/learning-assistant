"""
Curator Agent - Paper Scoring and Ranking

This agent scores and ranks papers based on relevance to user interests.

Key Concepts:
- Curation = Selecting the best/most relevant papers from a larger set
- Scoring = Assigning a relevance score (0-1) to each paper
- Ranking = Sorting papers by score (highest first)
- Multi-signal = Combining multiple factors into one score

Week 1 MVP: Simple keyword matching
- Match paper concepts against user interests
- Basic scoring algorithm
- Select top N papers

Future weeks will add:
- Week 2: Social proof (Twitter mentions, HN upvotes)
- Week 3: Citation velocity (papers gaining citations fast)
- Week 4: Semantic similarity (embeddings)
- Week 5: Personalized scoring (based on reading history)

Example:
    curator = CuratorAgent()
    scored_papers = curator.score_papers(papers)
    top_5 = scored_papers[:5]  # Get top 5 papers
"""

from typing import List, Dict, Any, Optional
from loguru import logger

from src.models.paper import Paper
from src.config import settings, get_research_interests_list
from src.database import get_db_session


class CuratorAgent:
    """
    Agent that scores and ranks papers by relevance.

    Week 1 MVP uses simple keyword matching.
    Future versions will incorporate:
    - Social signals (Twitter, HN)
    - Citation metrics
    - Semantic similarity
    - User reading history
    """

    def __init__(self, interests: Optional[List[str]] = None):
        """
        Initialize the Curator agent.

        Args:
            interests: List of research interests (defaults to config)
        """
        self.interests = interests or get_research_interests_list()
        logger.debug(f"CuratorAgent initialized with interests: {self.interests}")

    def score_paper(self, paper: Paper) -> float:
        """
        Score a single paper based on relevance to interests.

        Week 1 MVP Scoring Algorithm:
        - Match paper concepts against user interests
        - Score = (matching_concepts / total_interests)
        - Range: 0.0 to 1.0

        Args:
            paper: Paper object to score

        Returns:
            Relevance score (0-1, higher = more relevant)

        Example:
            curator = CuratorAgent(interests=["transformers", "NLP"])
            paper = Paper(concepts=["transformers", "attention", "BERT"])
            score = curator.score_paper(paper)
            # score might be 0.5 (1 match out of 2 interests)
        """
        if not paper.concepts:
            # No concepts extracted yet
            logger.warning(f"Paper {paper.arxiv_id} has no concepts")
            return 0.0

        # Convert to lowercase for case-insensitive matching
        paper_concepts = [c.lower() for c in paper.concepts]
        user_interests = [i.lower() for i in self.interests]

        # Count matches
        matches = 0
        for interest in user_interests:
            # Check if interest appears in any concept
            # Example: interest="transformer" matches concept="transformer architecture"
            for concept in paper_concepts:
                if interest in concept or concept in interest:
                    matches += 1
                    break  # Don't count same interest twice

        # Calculate score
        # Score = matches / total_interests
        # If you're interested in 5 topics and paper matches 2, score = 0.4
        score = matches / len(user_interests) if user_interests else 0.0

        logger.debug(f"Paper {paper.arxiv_id}: {matches} matches, score={score:.2f}")

        return score

    def score_papers(self, papers: List[Paper]) -> List[Paper]:
        """
        Score all papers and sort by relevance.

        Args:
            papers: List of Paper objects

        Returns:
            List of papers sorted by relevance (highest first)

        Example:
            curator = CuratorAgent()
            papers = db.query(Paper).all()
            ranked = curator.score_papers(papers)
            top_5 = ranked[:5]
        """
        logger.info(f"Scoring {len(papers)} papers...")

        scored_papers = []

        for paper in papers:
            try:
                # Calculate score
                score = self.score_paper(paper)

                # Store score in paper object (for display)
                paper.relevance_score = score

                scored_papers.append(paper)

            except Exception as e:
                logger.error(f"Failed to score {paper.arxiv_id}: {e}")
                # Include with score 0
                paper.relevance_score = 0.0
                scored_papers.append(paper)

        # Sort by score (highest first)
        scored_papers.sort(key=lambda p: p.relevance_score, reverse=True)

        logger.info(f"✅ Scored and ranked {len(scored_papers)} papers")

        # Log top papers
        if scored_papers:
            logger.info("Top 3 papers:")
            for i, p in enumerate(scored_papers[:3], 1):
                logger.info(f"  {i}. [{p.relevance_score:.2f}] {p.title[:50]}...")

        return scored_papers

    def save_scores(self, papers: List[Paper]) -> int:
        """
        Save relevance scores to the database.

        Args:
            papers: List of Paper objects with relevance_score set

        Returns:
            Number of papers updated

        Example:
            curator = CuratorAgent()
            ranked = curator.score_papers(papers)
            curator.save_scores(ranked)
        """
        from datetime import datetime

        logger.info(f"Saving scores for {len(papers)} papers...")

        count = 0

        with get_db_session() as db:
            for paper in papers:
                # Find the paper in database
                db_paper = db.query(Paper).filter_by(arxiv_id=paper.arxiv_id).first()

                if db_paper:
                    db_paper.relevance_score = paper.relevance_score
                    db_paper.scored_at = datetime.utcnow()
                    # Store score breakdown (for future multi-signal scoring)
                    db_paper.score_components = {
                        "interest_match": paper.relevance_score,
                    }
                    count += 1

        logger.info(f"✅ Saved scores for {count} papers")
        return count

    def score_and_save(self, papers: List[Paper]) -> List[Paper]:
        """
        Score papers and save to database.

        Convenience method that does everything:
        1. Score each paper
        2. Sort by relevance
        3. Save scores to database
        4. Return sorted papers

        Args:
            papers: List of Paper objects

        Returns:
            List of papers sorted by relevance

        Example:
            curator = CuratorAgent()
            papers = db.query(Paper).all()
            ranked = curator.score_and_save(papers)
            print(f"Top paper: {ranked[0].title}")
        """
        # Score and sort
        scored_papers = self.score_papers(papers)

        # Save to database
        self.save_scores(scored_papers)

        return scored_papers

    def select_top_papers(
        self, papers: List[Paper], n: Optional[int] = None
    ) -> List[Paper]:
        """
        Select top N papers by relevance.

        Args:
            papers: List of Paper objects
            n: Number of papers to select (defaults to config setting)

        Returns:
            Top N papers sorted by relevance

        Example:
            curator = CuratorAgent()
            top_5 = curator.select_top_papers(papers, n=5)
        """
        n = n or settings.max_papers_per_digest

        # Score if not already scored
        if not all(p.relevance_score is not None for p in papers):
            papers = self.score_papers(papers)

        # Return top N
        top_papers = papers[:n]

        logger.info(f"Selected top {len(top_papers)} papers for digest")

        return top_papers


# ============================================================================
# Standalone function for LangGraph integration
# ============================================================================


def curate_papers_batch(
    papers: List[Paper], top_n: Optional[int] = None
) -> List[Paper]:
    """
    Score and select top papers.

    This is a standalone function for LangGraph nodes.

    Args:
        papers: List of explained Paper objects
        top_n: Number of top papers to return

    Returns:
        Top N papers sorted by relevance

    Example (in LangGraph):
        def curator_node(state: AgentState) -> AgentState:
            papers = state["explained_papers"]
            top_papers = curate_papers_batch(papers, top_n=5)
            state["final_papers"] = top_papers
            return state
    """
    curator = CuratorAgent()

    # Score and save
    ranked = curator.score_and_save(papers)

    # Select top N
    top_papers = curator.select_top_papers(ranked, n=top_n)

    return top_papers


if __name__ == "__main__":
    # Test the Curator agent
    print("Testing Curator Agent...")

    from src.database import get_db_session

    with get_db_session() as db:
        # Get papers that have been analyzed (have concepts)
        papers = db.query(Paper).filter(Paper.concepts.isnot(None)).all()

        if not papers:
            print("No papers with concepts found. Run:")
            print("1. python main.py --discover --days 1 --analyze")
        else:
            print(f"\nScoring {len(papers)} papers...")
            print(f"Research interests: {get_research_interests_list()}\n")

            # Create curator and score
            curator = CuratorAgent()
            ranked = curator.score_and_save(papers)

            # Display top 5
            print("TOP 5 PAPERS:")
            print("=" * 80)
            for i, paper in enumerate(ranked[:5], 1):
                print(f"\n{i}. [{paper.relevance_score:.2f}] {paper.title}")
                if paper.concepts:
                    print(f"   Concepts: {', '.join(paper.concepts[:5])}")
                if paper.key_insight:
                    print(f"   💡 {paper.key_insight[:100]}...")

            print("\n" + "=" * 80)
            print("✅ Curator test complete!")
