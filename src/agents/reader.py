"""
Reader Agent - Structured Paper Analysis

This agent reads research papers and extracts structured information.

Key Concepts:
- Structured extraction = Getting specific fields from unstructured text
- JSON mode = Claude returns data in a predictable format
- Prompt engineering = Designing prompts to get good results

What the Reader Agent does:
1. Takes a paper (title, abstract, authors)
2. Uses Claude to extract:
   - Main claim/contribution
   - Methodology
   - Key results
   - Novel contributions
   - Limitations
   - Technical concepts
3. Saves analysis to database

Why separate Reader and Explainer?
- Reader = Technical analysis (for ML researchers)
- Explainer = Simplified explanation (for learners)
- Different prompts, different Claude models (Haiku vs Sonnet)
- Separation of concerns = easier to maintain

Example:
    reader = ReaderAgent()
    analysis = reader.analyze_paper(paper)
    # analysis contains structured data about the paper
"""

from typing import Dict, Any, List
from loguru import logger

from src.models.paper import Paper
from src.services.claude_client import get_claude_client
from src.config import settings
from src.database import get_db_session


class ReaderAgent:
    """
    Agent that reads papers and extracts structured information.

    This agent uses Claude Haiku (fast, cheap, good at extraction) to:
    - Identify the main claim
    - Understand the methodology
    - Extract key results
    - Identify technical concepts
    - Note limitations

    The output is structured JSON that we save to the database.
    """

    def __init__(self):
        """Initialize the Reader agent."""
        self.client = get_claude_client()
        self.model = settings.reader_model
        logger.debug(f"ReaderAgent initialized with model={self.model}")

    def build_analysis_prompt(self, paper: Paper) -> str:
        """
        Build the prompt for analyzing a paper.

        Prompt engineering tips:
        - Be specific about what you want
        - Provide the output format (JSON schema)
        - Give context (this is a research paper)
        - Request concise answers (abstracts are already summaries)

        Args:
            paper: Paper object with title, abstract, authors

        Returns:
            Formatted prompt string

        Example output:
            {
              "main_claim": "...",
              "methodology": "...",
              "key_results": ["...", "..."],
              "novel_contributions": "...",
              "limitations": "...",
              "concepts": ["...", "..."]
            }
        """
        # Format authors as a readable string
        authors_str = ", ".join(paper.authors[:3])  # First 3 authors
        if len(paper.authors) > 3:
            authors_str += " et al."

        prompt = f"""Analyze this research paper and extract structured information.

PAPER DETAILS:
Title: {paper.title}
Authors: {authors_str}
Published: {paper.published_date.strftime('%Y-%m-%d')}
Categories: {', '.join(paper.categories)}

ABSTRACT:
{paper.abstract}

TASK:
Extract the following information in JSON format:

{{
  "main_claim": "The primary contribution or claim of the paper (1-2 sentences)",
  "methodology": "What methods/techniques they used (1-2 sentences)",
  "key_results": ["List of 2-4 key findings or results"],
  "novel_contributions": "What's new or different about this work (1-2 sentences)",
  "limitations": "Acknowledged limitations or potential weaknesses (1-2 sentences, or 'Not mentioned' if none)",
  "concepts": ["List of 3-7 important technical concepts or terms used"]
}}

IMPORTANT:
- Be concise and technical (this is for ML researchers)
- Extract information, don't add interpretation
- Use the paper's own terminology
- If something isn't in the abstract, say "Not available in abstract"
"""

        return prompt

    def analyze_paper(self, paper: Paper) -> Dict[str, Any]:
        """
        Analyze a single paper with Claude.

        This is the main method of the Reader agent.

        Flow:
        1. Build prompt with paper details
        2. Call Claude in JSON mode
        3. Parse response
        4. Validate fields
        5. Return structured data

        Args:
            paper: Paper object to analyze

        Returns:
            Dictionary with analysis results

        Example:
            reader = ReaderAgent()
            paper = db.query(Paper).first()
            analysis = reader.analyze_paper(paper)
            print(analysis["main_claim"])
        """
        logger.info(f"Analyzing paper: {paper.title[:50]}...")

        try:
            # Build the prompt
            prompt = self.build_analysis_prompt(paper)

            # Call Claude in JSON mode
            # This will return a dictionary with our requested fields
            analysis = self.client.chat_json(
                prompt=prompt,
                model=self.model,
                temperature=0.3,  # Low temperature = more focused/consistent
            )

            # Validate that we got all expected fields
            expected_fields = [
                "main_claim",
                "methodology",
                "key_results",
                "novel_contributions",
                "limitations",
                "concepts",
            ]

            missing_fields = [f for f in expected_fields if f not in analysis]
            if missing_fields:
                logger.warning(f"Missing fields in analysis: {missing_fields}")
                # Fill in missing fields with defaults
                for field in missing_fields:
                    if field in ["key_results", "concepts"]:
                        analysis[field] = []
                    else:
                        analysis[field] = "Not available"

            logger.info(f"✅ Analysis complete for {paper.arxiv_id}")
            logger.debug(f"Extracted {len(analysis['concepts'])} concepts")

            return analysis

        except Exception as e:
            logger.error(f"❌ Failed to analyze paper {paper.arxiv_id}: {e}")
            raise

    def analyze_papers(self, papers: List[Paper]) -> List[Dict[str, Any]]:
        """
        Analyze multiple papers.

        This processes papers one by one. In the future, we could:
        - Batch them for efficiency
        - Run them in parallel
        - Add retry logic for failures

        Args:
            papers: List of Paper objects

        Returns:
            List of analysis dictionaries

        Example:
            reader = ReaderAgent()
            papers = db.query(Paper).limit(10).all()
            analyses = reader.analyze_papers(papers)
        """
        logger.info(f"Analyzing {len(papers)} papers...")

        results = []
        failed = 0

        for i, paper in enumerate(papers, 1):
            logger.info(f"Progress: {i}/{len(papers)}")

            try:
                analysis = self.analyze_paper(paper)
                results.append(
                    {
                        "arxiv_id": paper.arxiv_id,
                        "analysis": analysis,
                    }
                )
            except Exception as e:
                logger.error(f"Failed to analyze {paper.arxiv_id}: {e}")
                failed += 1
                continue

        logger.info(f"✅ Analyzed {len(results)} papers ({failed} failed)")
        return results

    def save_analysis(self, arxiv_id: str, analysis: Dict[str, Any]) -> None:
        """
        Save analysis results to the database.

        This updates the Paper object with the extracted information.

        Args:
            arxiv_id: The paper's arXiv ID
            analysis: Analysis dictionary from analyze_paper()

        Example:
            reader = ReaderAgent()
            analysis = reader.analyze_paper(paper)
            reader.save_analysis(paper.arxiv_id, analysis)
        """
        from datetime import datetime

        logger.debug(f"Saving analysis for {arxiv_id}...")

        with get_db_session() as db:
            # Find the paper
            paper = db.query(Paper).filter_by(arxiv_id=arxiv_id).first()

            if not paper:
                logger.error(f"Paper {arxiv_id} not found in database!")
                raise ValueError(f"Paper {arxiv_id} not found")

            # Update the paper with analysis results
            paper.main_claim = analysis.get("main_claim")
            paper.methodology = analysis.get("methodology")
            paper.key_results = analysis.get("key_results")
            paper.novel_contributions = analysis.get("novel_contributions")
            paper.limitations = analysis.get("limitations")
            paper.concepts = analysis.get("concepts")
            paper.analyzed_at = datetime.utcnow()

            # Commit happens automatically when we exit the with block
            logger.debug(f"✅ Saved analysis for {arxiv_id}")

    def analyze_and_save(self, papers: List[Paper]) -> int:
        """
        Analyze papers and save results to database.

        This is the convenience method that does everything:
        1. Analyze each paper
        2. Save results to database
        3. Return count of successful analyses

        Args:
            papers: List of Paper objects

        Returns:
            Number of successfully analyzed papers

        Example:
            reader = ReaderAgent()
            papers = db.query(Paper).filter_by(analyzed_at=None).all()
            count = reader.analyze_and_save(papers)
            print(f"Analyzed {count} papers")
        """
        logger.info(f"Analyzing and saving {len(papers)} papers...")

        success_count = 0

        for i, paper in enumerate(papers, 1):
            logger.info(f"Progress: {i}/{len(papers)} - {paper.title[:40]}...")

            try:
                # Analyze the paper
                analysis = self.analyze_paper(paper)

                # Save to database
                self.save_analysis(paper.arxiv_id, analysis)

                success_count += 1

            except Exception as e:
                logger.error(f"Failed to process {paper.arxiv_id}: {e}")
                continue

        logger.info(f"✅ Successfully analyzed {success_count}/{len(papers)} papers")
        return success_count


# ============================================================================
# Standalone function for LangGraph integration
# ============================================================================


def analyze_papers_batch(papers: List[Paper]) -> List[Paper]:
    """
    Batch analyze papers and return updated Paper objects.

    This is a standalone function that can be used in LangGraph nodes.

    LangGraph nodes should be functions that:
    - Take state as input
    - Do work
    - Return updated state

    This function does the "do work" part for the Reader agent.

    Args:
        papers: List of Paper objects to analyze

    Returns:
        List of Paper objects with analysis fields populated

    Example (in LangGraph):
        def reader_node(state: AgentState) -> AgentState:
            papers = state["papers"]
            analyzed = analyze_papers_batch(papers)
            state["analyzed_papers"] = analyzed
            return state
    """
    reader = ReaderAgent()
    reader.analyze_and_save(papers)

    # Reload papers from database to get updated data
    with get_db_session() as db:
        arxiv_ids = [p.arxiv_id for p in papers]
        updated_papers = db.query(Paper).filter(Paper.arxiv_id.in_(arxiv_ids)).all()

    return updated_papers


if __name__ == "__main__":
    # Test the Reader agent
    print("Testing Reader Agent...")

    # You need papers in the database to test this
    # First run: python main.py --discover --days 1

    with get_db_session() as db:
        # Get a paper that hasn't been analyzed yet
        paper = db.query(Paper).filter(Paper.analyzed_at.is_(None)).first()

        if not paper:
            print("No unanalyzed papers found. Run: python main.py --discover --days 1")
        else:
            print(f"\nAnalyzing: {paper.title}\n")

            # Create reader and analyze
            reader = ReaderAgent()
            analysis = reader.analyze_paper(paper)

            # Display results
            print("ANALYSIS RESULTS:")
            print("=" * 80)
            print(f"\nMain Claim:\n{analysis['main_claim']}")
            print(f"\nMethodology:\n{analysis['methodology']}")
            print(f"\nKey Results:")
            for i, result in enumerate(analysis["key_results"], 1):
                print(f"  {i}. {result}")
            print(f"\nNovel Contributions:\n{analysis['novel_contributions']}")
            print(f"\nLimitations:\n{analysis['limitations']}")
            print(f"\nConcepts: {', '.join(analysis['concepts'])}")
            print("=" * 80)

            # Save to database
            reader.save_analysis(paper.arxiv_id, analysis)
            print("\n✅ Analysis saved to database!")
