"""
Explainer Agent - Learning-Friendly Explanations

This agent takes technical paper analysis and creates learning-friendly explanations.

Key Concepts:
- ELI5 = Explain Like I'm 5 (simple explanations for complex topics)
- Learning-oriented = Focused on helping people understand, not just summarize
- Pedagogical prompting = Designing prompts that encourage teaching
- Parallel processing = Multiple API calls concurrently for speed

Difference from Reader Agent:
- Reader = Extract technical info (for researchers)
- Explainer = Simplify for learning (for students/learners)
- Reader uses Haiku (fast/cheap), Explainer uses Sonnet (better quality)

What the Explainer Agent does:
1. Takes analyzed paper data (from Reader Agent)
2. Uses Claude Sonnet to generate:
   - ELI5 summary (simple explanation)
   - Key insight (one thing to remember)
   - Learning questions (to think about while reading)
   - Prerequisites (what to learn first)
   - Related concepts (for further study)
3. Saves to database

Example:
    explainer = ExplainerAgent()
    explanation = explainer.explain_paper(paper)
    print(explanation["eli5_summary"])
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from loguru import logger

from src.config import settings
from src.database import get_db_session
from src.models.paper import Paper
from src.services.claude_client import get_claude_client


class ExplainerAgent:
    """
    Agent that creates learning-friendly explanations of research papers.

    This agent uses Claude Sonnet (better at creative explanations) to:
    - Simplify complex concepts
    - Identify key insights
    - Generate learning questions
    - Map out prerequisites
    - Suggest related topics

    The goal is to make papers accessible to learners, not just experts.
    """

    def __init__(self):
        """Initialize the Explainer agent."""
        self.client = get_claude_client()
        self.model = settings.explainer_model
        logger.debug(f"ExplainerAgent initialized with model={self.model}")

    def build_explanation_prompt(self, paper: Paper) -> str:
        """
        Build the prompt for explaining a paper.

        Prompt engineering for explanations:
        - Ask for simple language (avoid jargon)
        - Request analogies or examples
        - Focus on "why this matters"
        - Generate questions to guide learning
        - Identify what to learn first

        Args:
            paper: Paper object with analysis already done

        Returns:
            Formatted prompt string

        Example output:
            {
              "eli5_summary": "Imagine if...",
              "key_insight": "The big idea is...",
              "learning_questions": ["Why...", "How..."],
              "prerequisites": ["You should understand..."],
              "related_concepts": ["This connects to..."]
            }
        """
        # Check if paper has been analyzed
        if not paper.main_claim:
            raise ValueError(
                f"Paper {paper.arxiv_id} hasn't been analyzed yet. " "Run Reader agent first."
            )

        # Format concepts as a readable list
        concepts_str = ", ".join(paper.concepts) if paper.concepts else "Not specified"

        prompt = f"""Explain this paper for learners.

PAPER: {paper.title}
CLAIM: {paper.main_claim}
METHOD: {paper.methodology}
RESULTS: {', '.join(paper.key_results) if paper.key_results else 'Not specified'}
CONTRIBUTIONS: {paper.novel_contributions}
CONCEPTS: {concepts_str}

Return JSON:
{{
  "eli5_summary": "2-3 sentence simple explanation. Use analogies, avoid jargon.",
  "key_insight": "The ONE most important takeaway (1 sentence).",
  "learning_questions": ["3-5 thought-provoking questions to guide understanding"],
  "prerequisites": ["2-4 specific concepts to learn first (e.g., 'how attention works')"],
  "related_concepts": ["3-5 related topics for further study"]
}}

Write for learners. Be clear, encouraging, and spark curiosity.
"""

        return prompt

    def explain_paper(self, paper: Paper) -> dict[str, Any]:
        """
        Create a learning-friendly explanation for a paper.

        This is the main method of the Explainer agent.

        Flow:
        1. Check that paper has been analyzed (Reader agent ran first)
        2. Build prompt with technical analysis
        3. Call Claude Sonnet in JSON mode
        4. Parse and validate response
        5. Return structured explanation

        Args:
            paper: Paper object (must have analysis fields populated)

        Returns:
            Dictionary with explanation results

        Raises:
            ValueError: If paper hasn't been analyzed yet

        Example:
            explainer = ExplainerAgent()
            paper = db.query(Paper).filter_by(analyzed_at!=None).first()
            explanation = explainer.explain_paper(paper)
            print(explanation["eli5_summary"])
        """
        logger.info(f"Explaining paper: {paper.title[:50]}...")

        # Validate that paper has been analyzed
        if not paper.analyzed_at:
            raise ValueError(
                f"Paper {paper.arxiv_id} must be analyzed before explaining. "
                "Run ReaderAgent first."
            )

        try:
            # Build the prompt
            prompt = self.build_explanation_prompt(paper)

            # Call Claude Sonnet in JSON mode
            # Sonnet is better at creative, nuanced explanations
            explanation = self.client.chat_json(
                prompt=prompt,
                model=self.model,
                temperature=0.7,  # Higher temperature = more creative explanations
            )

            # Validate expected fields
            expected_fields = [
                "eli5_summary",
                "key_insight",
                "learning_questions",
                "prerequisites",
                "related_concepts",
            ]

            missing_fields = [f for f in expected_fields if f not in explanation]
            if missing_fields:
                logger.warning(f"Missing fields in explanation: {missing_fields}")
                # Fill in missing fields with defaults
                for field in missing_fields:
                    if field in [
                        "learning_questions",
                        "prerequisites",
                        "related_concepts",
                    ]:
                        explanation[field] = []
                    else:
                        explanation[field] = "Not available"

            logger.info(f"✅ Explanation complete for {paper.arxiv_id}")
            logger.debug(f"Generated {len(explanation['learning_questions'])} learning questions")

            return explanation

        except Exception as e:
            logger.error(f"❌ Failed to explain paper {paper.arxiv_id}: {e}")
            raise

    def explain_papers(self, papers: list[Paper]) -> list[dict[str, Any]]:
        """
        Explain multiple papers.

        Processes papers sequentially. Each paper must have been analyzed first.

        Args:
            papers: List of Paper objects (all must be analyzed)

        Returns:
            List of explanation dictionaries

        Example:
            explainer = ExplainerAgent()
            papers = db.query(Paper).filter(Paper.analyzed_at != None).all()
            explanations = explainer.explain_papers(papers)
        """
        logger.info(f"Explaining {len(papers)} papers...")

        results = []
        failed = 0
        skipped = 0

        for i, paper in enumerate(papers, 1):
            logger.info(f"Progress: {i}/{len(papers)}")

            # Skip if not analyzed
            if not paper.analyzed_at:
                logger.warning(f"Skipping {paper.arxiv_id} - not analyzed yet")
                skipped += 1
                continue

            try:
                explanation = self.explain_paper(paper)
                results.append(
                    {
                        "arxiv_id": paper.arxiv_id,
                        "explanation": explanation,
                    }
                )
            except Exception as e:
                logger.error(f"Failed to explain {paper.arxiv_id}: {e}")
                failed += 1
                continue

        logger.info(f"✅ Explained {len(results)} papers " f"({skipped} skipped, {failed} failed)")
        return results

    def save_explanation(self, arxiv_id: str, explanation: dict[str, Any]) -> None:
        """
        Save explanation results to the database.

        Updates the Paper object with learning-friendly content.

        Args:
            arxiv_id: The paper's arXiv ID
            explanation: Explanation dictionary from explain_paper()

        Example:
            explainer = ExplainerAgent()
            explanation = explainer.explain_paper(paper)
            explainer.save_explanation(paper.arxiv_id, explanation)
        """
        from datetime import datetime

        logger.debug(f"Saving explanation for {arxiv_id}...")

        with get_db_session() as db:
            # Find the paper
            paper = db.query(Paper).filter_by(arxiv_id=arxiv_id).first()

            if not paper:
                logger.error(f"Paper {arxiv_id} not found in database!")
                raise ValueError(f"Paper {arxiv_id} not found")

            # Update the paper with explanation results
            paper.eli5_summary = explanation.get("eli5_summary")
            paper.key_insight = explanation.get("key_insight")
            paper.learning_questions = explanation.get("learning_questions")
            paper.prerequisites = explanation.get("prerequisites")
            paper.related_concepts = explanation.get("related_concepts")
            paper.explained_at = datetime.utcnow()

            # Commit happens automatically when we exit the with block
            logger.debug(f"✅ Saved explanation for {arxiv_id}")

    def _explain_single(self, paper: Paper) -> tuple[str, dict[str, Any] | None, bool]:
        """
        Explain a single paper and return result tuple.

        Helper method for parallel processing.

        Args:
            paper: Paper to explain

        Returns:
            Tuple of (arxiv_id, explanation_dict or None, was_skipped)
        """
        # Skip if not analyzed
        if not paper.analyzed_at:
            logger.warning(f"Skipping {paper.arxiv_id} - not analyzed yet")
            return (paper.arxiv_id, None, True)

        try:
            explanation = self.explain_paper(paper)
            return (paper.arxiv_id, explanation, False)
        except Exception as e:
            logger.error(f"Failed to explain {paper.arxiv_id}: {e}")
            return (paper.arxiv_id, None, False)

    def explain_and_save(self, papers: list[Paper], max_workers: int = 3) -> int:
        """
        Explain papers in parallel and save results to database.

        Uses ThreadPoolExecutor to process multiple papers concurrently.
        Each paper's prompt is moderate (~2-3K tokens), so we limit
        concurrency to avoid rate limits.

        Args:
            papers: List of Paper objects (must be analyzed)
            max_workers: Maximum concurrent API calls (default: 3, reduced to avoid rate limits)

        Returns:
            Number of successfully explained papers

        Example:
            explainer = ExplainerAgent()
            papers = db.query(Paper).filter(
                Paper.analyzed_at != None,
                Paper.explained_at == None
            ).all()
            count = explainer.explain_and_save(papers)
            print(f"Explained {count} papers")
        """
        if not papers:
            return 0

        logger.info(f"Explaining {len(papers)} papers with {max_workers} parallel workers...")

        success_count = 0
        skipped = 0
        results: list[tuple[str, dict[str, Any]]] = []

        # Sequential processing when max_workers=1 (avoids SQLite threading issues)
        if max_workers == 1:
            for i, paper in enumerate(papers, 1):
                logger.info(f"Progress: {i}/{len(papers)} - {paper.title[:40]}...")
                arxiv_id, explanation, was_skipped = self._explain_single(paper)
                if was_skipped:
                    skipped += 1
                elif explanation:
                    results.append((arxiv_id, explanation))
        else:
            # Process papers in parallel with staggered submission to avoid rate limits
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {}
                for i, paper in enumerate(papers):
                    # Submit tasks with a small delay to avoid initial burst
                    if i > 0:
                        time.sleep(0.5)  # 500ms delay between submissions
                    futures[executor.submit(self._explain_single, paper)] = paper

                for i, future in enumerate(as_completed(futures), 1):
                    paper = futures[future]
                    logger.info(f"Progress: {i}/{len(papers)} - {paper.title[:40]}...")

                    arxiv_id, explanation, was_skipped = future.result()
                    if was_skipped:
                        skipped += 1
                    elif explanation:
                        results.append((arxiv_id, explanation))

        # Save results to database (sequential to avoid conflicts)
        for arxiv_id, explanation in results:
            try:
                self.save_explanation(arxiv_id, explanation)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to save {arxiv_id}: {e}")

        logger.info(
            f"✅ Successfully explained {success_count}/{len(papers)} papers "
            f"({skipped} skipped)"
        )
        return success_count


# ============================================================================
# Standalone function for LangGraph integration
# ============================================================================


def explain_papers_batch(papers: list[Paper], max_workers: int = 3) -> list[Paper]:
    """
    Batch explain papers and return updated Paper objects.

    This is a standalone function for LangGraph nodes.

    Args:
        papers: List of analyzed Paper objects
        max_workers: Maximum concurrent API calls (default: 3, reduced to avoid rate limits)

    Returns:
        List of Paper objects with explanation fields populated

    Example (in LangGraph):
        def explainer_node(state: AgentState) -> AgentState:
            papers = state["analyzed_papers"]
            explained = explain_papers_batch(papers)
            state["explained_papers"] = explained
            return state
    """
    explainer = ExplainerAgent()
    explainer.explain_and_save(papers, max_workers=max_workers)

    # Reload papers from database to get updated data
    with get_db_session() as db:
        arxiv_ids = [p.arxiv_id for p in papers]
        updated_papers = db.query(Paper).filter(Paper.arxiv_id.in_(arxiv_ids)).all()

    return updated_papers


if __name__ == "__main__":
    # Test the Explainer agent
    print("Testing Explainer Agent...")

    with get_db_session() as db:
        # Get a paper that has been analyzed but not explained
        paper = (
            db.query(Paper)
            .filter(Paper.analyzed_at.isnot(None), Paper.explained_at.is_(None))
            .first()
        )

        if not paper:
            print("No analyzed papers found. First run:")
            print("1. python main.py --discover --days 1")
            print("2. python src/agents/reader.py")
        else:
            print(f"\nExplaining: {paper.title}\n")

            # Create explainer and explain
            explainer = ExplainerAgent()
            explanation = explainer.explain_paper(paper)

            # Display results
            print("EXPLANATION RESULTS:")
            print("=" * 80)
            print(f"\n📚 ELI5 Summary:\n{explanation['eli5_summary']}")
            print(f"\n💡 Key Insight:\n{explanation['key_insight']}")

            print("\n❓ Learning Questions:")
            for i, q in enumerate(explanation["learning_questions"], 1):
                print(f"  {i}. {q}")

            print("\n📖 Prerequisites:")
            for i, prereq in enumerate(explanation["prerequisites"], 1):
                print(f"  {i}. {prereq}")

            print("\n🔗 Related Concepts:")
            for i, concept in enumerate(explanation["related_concepts"], 1):
                print(f"  {i}. {concept}")

            print("=" * 80)

            # Save to database
            explainer.save_explanation(paper.arxiv_id, explanation)
            print("\n✅ Explanation saved to database!")
