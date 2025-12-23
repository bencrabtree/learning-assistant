"""
Explainer Agent - Learning-Friendly Explanations

This agent takes technical paper analysis and creates learning-friendly explanations.

Key Concepts:
- ELI5 = Explain Like I'm 5 (simple explanations for complex topics)
- Learning-oriented = Focused on helping people understand, not just summarize
- Pedagogical prompting = Designing prompts that encourage teaching

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

from typing import Dict, Any, List, Optional
from loguru import logger

from src.models.paper import Paper
from src.services.claude_client import get_claude_client
from src.config import settings
from src.database import get_db_session


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
                f"Paper {paper.arxiv_id} hasn't been analyzed yet. "
                "Run Reader agent first."
            )

        # Format concepts as a readable list
        concepts_str = ", ".join(paper.concepts) if paper.concepts else "Not specified"

        prompt = f"""Create a learning-friendly explanation of this research paper.

PAPER DETAILS:
Title: {paper.title}
Categories: {', '.join(paper.categories)}

TECHNICAL ANALYSIS (from Reader Agent):
Main Claim: {paper.main_claim}
Methodology: {paper.methodology}
Key Results: {', '.join(paper.key_results) if paper.key_results else 'Not specified'}
Novel Contributions: {paper.novel_contributions}
Technical Concepts: {concepts_str}

YOUR TASK:
Help someone learn from this paper by providing:

{{
  "eli5_summary": "A simple 2-3 sentence explanation that anyone could understand. Use analogies or examples. Avoid jargon. Start with 'Imagine...' or 'Think of it like...' if helpful.",

  "key_insight": "The ONE most important thing to remember about this paper (1 sentence). What's the big breakthrough or main idea?",

  "learning_questions": [
    "3-5 thought-provoking questions someone should think about while reading this paper",
    "Questions should help connect to prior knowledge or explore implications",
    "Examples: 'How does this compare to X?', 'Why is this better than Y?', 'What problems does this solve?'"
  ],

  "prerequisites": [
    "2-4 concepts or topics someone should understand BEFORE reading this paper",
    "Be specific: not just 'machine learning' but 'how attention mechanisms work'",
    "Order from most fundamental to more advanced"
  ],

  "related_concepts": [
    "3-5 related topics to explore AFTER understanding this paper",
    "These should be natural next steps for learning",
    "Examples: related papers, techniques, applications, extensions"
  ]
}}

IMPORTANT:
- Write for curious learners, not experts
- Be encouraging and accessible
- Focus on understanding, not just facts
- Make connections to things people might already know
- Spark curiosity!
"""

        return prompt

    def explain_paper(self, paper: Paper) -> Dict[str, Any]:
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
                    if field in ["learning_questions", "prerequisites", "related_concepts"]:
                        explanation[field] = []
                    else:
                        explanation[field] = "Not available"

            logger.info(f"✅ Explanation complete for {paper.arxiv_id}")
            logger.debug(f"Generated {len(explanation['learning_questions'])} learning questions")

            return explanation

        except Exception as e:
            logger.error(f"❌ Failed to explain paper {paper.arxiv_id}: {e}")
            raise

    def explain_papers(self, papers: List[Paper]) -> List[Dict[str, Any]]:
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
                results.append({
                    "arxiv_id": paper.arxiv_id,
                    "explanation": explanation,
                })
            except Exception as e:
                logger.error(f"Failed to explain {paper.arxiv_id}: {e}")
                failed += 1
                continue

        logger.info(
            f"✅ Explained {len(results)} papers "
            f"({skipped} skipped, {failed} failed)"
        )
        return results

    def save_explanation(self, arxiv_id: str, explanation: Dict[str, Any]) -> None:
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

    def explain_and_save(self, papers: List[Paper]) -> int:
        """
        Explain papers and save results to database.

        This is the convenience method that does everything:
        1. Explain each paper
        2. Save results to database
        3. Return count of successful explanations

        Args:
            papers: List of Paper objects (must be analyzed)

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
        logger.info(f"Explaining and saving {len(papers)} papers...")

        success_count = 0
        skipped = 0

        for i, paper in enumerate(papers, 1):
            logger.info(f"Progress: {i}/{len(papers)} - {paper.title[:40]}...")

            # Skip if not analyzed
            if not paper.analyzed_at:
                logger.warning(f"Skipping {paper.arxiv_id} - not analyzed yet")
                skipped += 1
                continue

            try:
                # Explain the paper
                explanation = self.explain_paper(paper)

                # Save to database
                self.save_explanation(paper.arxiv_id, explanation)

                success_count += 1

            except Exception as e:
                logger.error(f"Failed to process {paper.arxiv_id}: {e}")
                continue

        logger.info(
            f"✅ Successfully explained {success_count}/{len(papers)} papers "
            f"({skipped} skipped)"
        )
        return success_count


# ============================================================================
# Standalone function for LangGraph integration
# ============================================================================

def explain_papers_batch(papers: List[Paper]) -> List[Paper]:
    """
    Batch explain papers and return updated Paper objects.

    This is a standalone function for LangGraph nodes.

    Args:
        papers: List of analyzed Paper objects

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
    explainer.explain_and_save(papers)

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
        paper = db.query(Paper).filter(
            Paper.analyzed_at.isnot(None),
            Paper.explained_at.is_(None)
        ).first()

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

            print(f"\n❓ Learning Questions:")
            for i, q in enumerate(explanation['learning_questions'], 1):
                print(f"  {i}. {q}")

            print(f"\n📖 Prerequisites:")
            for i, prereq in enumerate(explanation['prerequisites'], 1):
                print(f"  {i}. {prereq}")

            print(f"\n🔗 Related Concepts:")
            for i, concept in enumerate(explanation['related_concepts'], 1):
                print(f"  {i}. {concept}")

            print("=" * 80)

            # Save to database
            explainer.save_explanation(paper.arxiv_id, explanation)
            print("\n✅ Explanation saved to database!")
