"""
Assessor Agent - Breakthrough Detection

Uses Claude Sonnet to evaluate papers for breakthrough potential.
Applies a HIGH BAR - only truly groundbreaking papers should score high.

Scoring dimensions:
- Novelty (0-1): How new/original is the approach?
- Impact (0-1): Potential to change the field?
- Evidence (0-1): Quality of experimental validation?
- Significance (0-1): Importance of the problem being solved?

Breakthrough score = weighted combination of dimensions.
A paper is "breakthrough" if score >= 0.8
"""

from datetime import UTC, datetime
from typing import Any

from loguru import logger

from src.database import get_db_session
from src.models.paper import Paper
from src.services.claude_client import get_claude_client


class AssessorAgent:
    """Agent that assesses papers for breakthrough potential."""

    # Weights for combining scores
    WEIGHT_NOVELTY = 0.30
    WEIGHT_IMPACT = 0.30
    WEIGHT_EVIDENCE = 0.20
    WEIGHT_SIGNIFICANCE = 0.20

    # Threshold for breakthrough classification
    BREAKTHROUGH_THRESHOLD = 0.8

    def __init__(self):
        """Initialize the assessor agent."""
        from src.config import settings

        self.client = get_claude_client()
        self.model = settings.explainer_model  # Use Sonnet for quality

    def build_assessment_prompt(self, paper: Paper) -> str:
        """Build the prompt for breakthrough assessment."""
        return f"""You are an expert research assessor. Evaluate this paper for BREAKTHROUGH potential.

Apply a VERY HIGH BAR. Most papers are incremental - true breakthroughs are rare (maybe 1-2% of papers).

PAPER INFORMATION:
- ArXiv ID: {paper.arxiv_id}
- Title: {paper.title}
- Abstract: {paper.abstract}
- Main Claim: {paper.main_claim or 'Not analyzed'}
- Methodology: {paper.methodology or 'Not analyzed'}
- Novel Contributions: {paper.novel_contributions or 'Not analyzed'}
- Key Results: {paper.key_results or 'Not analyzed'}

SCORING CRITERIA (0.0 to 1.0 scale):

NOVELTY - How original is this work?
- 0.9-1.0: Introduces fundamentally new paradigm/approach
- 0.7-0.8: Significant novel contribution, new combination of ideas
- 0.5-0.6: Moderate novelty, incremental improvement
- 0.0-0.4: Mostly derivative, minor variations

IMPACT - Potential to change the field?
- 0.9-1.0: Could reshape entire research directions
- 0.7-0.8: Likely to influence many future papers
- 0.5-0.6: Useful contribution with moderate influence
- 0.0-0.4: Limited impact, niche application

EVIDENCE - Quality of validation?
- 0.9-1.0: Rigorous experiments, strong baselines, clear improvements
- 0.7-0.8: Good experiments, reasonable comparisons
- 0.5-0.6: Adequate validation, some gaps
- 0.0-0.4: Weak evidence, missing baselines

SIGNIFICANCE - Importance of the problem?
- 0.9-1.0: Addresses fundamental challenge in the field
- 0.7-0.8: Important practical or theoretical problem
- 0.5-0.6: Useful but not critical problem
- 0.0-0.4: Minor or already-solved problem

Respond in JSON format:
{{
    "novelty_score": <float 0-1>,
    "impact_score": <float 0-1>,
    "evidence_score": <float 0-1>,
    "significance_score": <float 0-1>,
    "reasoning": "<2-3 sentence explanation>",
    "key_strengths": ["<strength 1>", "<strength 2>"],
    "key_weaknesses": ["<weakness 1>", "<weakness 2>"],
    "read_priority": "<immediate|soon|when_free|skip>"
}}"""

    def assess_paper(self, paper: Paper) -> dict[str, Any]:
        """
        Assess a paper for breakthrough potential.

        Args:
            paper: Paper to assess

        Returns:
            Assessment dict with scores and metadata
        """
        prompt = self.build_assessment_prompt(paper)

        try:
            response = self.client.chat_json(
                prompt=prompt,
                model=self.model,
                system="You are an expert research assessor. Be rigorous and apply high standards.",
            )

            # Normalize scores to 0-1 range
            for key in ["novelty_score", "impact_score", "evidence_score", "significance_score"]:
                if key in response:
                    response[key] = max(0.0, min(1.0, float(response.get(key, 0.5))))

            # Calculate breakthrough score
            breakthrough_score = (
                self.WEIGHT_NOVELTY * response.get("novelty_score", 0.5)
                + self.WEIGHT_IMPACT * response.get("impact_score", 0.5)
                + self.WEIGHT_EVIDENCE * response.get("evidence_score", 0.5)
                + self.WEIGHT_SIGNIFICANCE * response.get("significance_score", 0.5)
            )
            response["breakthrough_score"] = breakthrough_score
            response["is_breakthrough"] = breakthrough_score >= self.BREAKTHROUGH_THRESHOLD

            # Ensure required fields exist
            response.setdefault("key_strengths", [])
            response.setdefault("key_weaknesses", [])
            response.setdefault("reasoning", "")
            response.setdefault("read_priority", "when_free")
            response.setdefault("confidence", 0.7)

            return response

        except Exception as e:
            logger.error(f"Assessment failed for {paper.arxiv_id}: {e}")
            return {
                "novelty_score": 0.5,
                "impact_score": 0.5,
                "evidence_score": 0.5,
                "significance_score": 0.5,
                "breakthrough_score": 0.5,
                "is_breakthrough": False,
                "reasoning": f"Assessment failed: {e}",
                "key_strengths": [],
                "key_weaknesses": [],
                "read_priority": "when_free",
                "confidence": 0.0,
            }

    def assess_and_save(self, paper: Paper) -> dict[str, Any]:
        """
        Assess a paper and save the results to the database.

        Args:
            paper: Paper to assess

        Returns:
            Assessment dict
        """
        assessment = self.assess_paper(paper)

        with get_db_session() as db:
            db_paper = db.query(Paper).filter_by(arxiv_id=paper.arxiv_id).first()
            if db_paper:
                db_paper.breakthrough_score = assessment["breakthrough_score"]
                db_paper.assessed_at = datetime.now(UTC)
                logger.debug(
                    f"Saved assessment for {paper.arxiv_id}: "
                    f"breakthrough={assessment['breakthrough_score']:.2f}"
                )

        return assessment

    def get_breakthroughs(self, papers: list[Paper]) -> list[Paper]:
        """
        Filter papers to only those with breakthrough potential.

        Args:
            papers: List of papers to filter

        Returns:
            List of breakthrough papers (score >= 0.8)
        """
        breakthroughs = []
        for paper in papers:
            assessment = self.assess_and_save(paper)
            if assessment["is_breakthrough"]:
                breakthroughs.append(paper)
                logger.info(
                    f"BREAKTHROUGH detected: {paper.title[:50]}... "
                    f"(score: {assessment['breakthrough_score']:.2f})"
                )
        return breakthroughs


def assess_papers_batch(papers: list[Paper]) -> tuple[list[Paper], list[dict[str, Any]]]:
    """
    Assess a batch of papers.

    Args:
        papers: List of papers to assess

    Returns:
        Tuple of (papers, assessments)
    """
    if not papers:
        return [], []

    agent = AssessorAgent()
    assessments = []

    total = len(papers)
    for i, paper in enumerate(papers, 1):
        logger.info(f"[{i}/{total}] Assessing: {paper.title[:50]}...")
        assessment = agent.assess_and_save(paper)
        assessment["arxiv_id"] = paper.arxiv_id
        assessments.append(assessment)

        # Log breakthrough status immediately
        if assessment.get("is_breakthrough"):
            logger.info(f"  🚀 BREAKTHROUGH! Score: {assessment['breakthrough_score']:.0%}")
        else:
            logger.debug(f"  Score: {assessment['breakthrough_score']:.0%}")

    logger.info(
        f"Assessed {len(papers)} papers, "
        f"{sum(1 for a in assessments if a['is_breakthrough'])} breakthroughs"
    )
    return papers, assessments


def get_breakthrough_papers(papers: list[Paper]) -> list[Paper]:
    """
    Get only breakthrough papers from a list.

    Args:
        papers: List of papers to filter

    Returns:
        List of papers with breakthrough potential
    """
    agent = AssessorAgent()
    return agent.get_breakthroughs(papers)
