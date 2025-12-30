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

    # Bonus applied to papers the user has explicitly favorited
    FAVORITE_BOOST = 0.08  # +8% for favorites

    def __init__(self):
        """Initialize the assessor agent."""
        from src.config import settings

        self.client = get_claude_client()
        # Use Sonnet for better judgment on breakthrough potential
        self.model = settings.explainer_model

    def build_assessment_prompt(self, paper: Paper) -> str:
        """Build the prompt for breakthrough assessment."""
        return f"""Evaluate this paper's significance on a 0-1 scale. Be generous for genuinely important work.

PAPER: {paper.title}
ABSTRACT: {paper.abstract}
CLAIM: {paper.main_claim or 'Not analyzed'}
METHOD: {paper.methodology or 'Not analyzed'}
CONTRIBUTIONS: {paper.novel_contributions or 'Not analyzed'}

SCORING GUIDE (0-1):

NOVELTY - How new/original is this?
- 0.95+: Introduces new paradigm, technique, or architecture that others will build on (e.g., Transformers, RLHF, GRPO, Chain-of-Thought)
- 0.85+: Novel combination or significant extension of existing ideas with clear innovation
- 0.70+: Solid contribution with some novel elements
- 0.50+: Incremental improvement on known approaches
- <0.50: Derivative or rehashing existing work

IMPACT - Will this influence the field?
- 0.95+: Major model release (GPT-4, Claude, Llama, DeepSeek-R1, Qwen) or technique that will be widely adopted
- 0.85+: Will likely influence many follow-up papers and practitioners
- 0.70+: Will influence researchers in this subfield
- 0.50+: Useful but limited influence
- <0.50: Niche interest only

EVIDENCE - Quality of validation?
- 0.90+: Comprehensive benchmarks, ablations, and real-world validation
- 0.75+: Strong empirical results with good experimental design
- 0.60+: Adequate experiments supporting claims
- <0.60: Weak or missing evidence

SIGNIFICANCE - How important is the problem?
- 0.95+: Addresses fundamental challenge in AI (reasoning, safety, efficiency, generalization)
- 0.80+: Important practical problem with broad applications
- 0.60+: Useful problem in a specific domain
- <0.60: Minor or already-solved problem

NOTE: Major model releases and papers introducing widely-used techniques should score 0.90+ on impact.

JSON format:
{{
    "novelty_score": <float>,
    "impact_score": <float>,
    "evidence_score": <float>,
    "significance_score": <float>,
    "reasoning": "<2-3 sentences>",
    "key_strengths": ["<2 strengths>"],
    "key_weaknesses": ["<2 weaknesses>"],
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

            # Apply favorite boost if user has marked this paper as important
            if paper.is_favorite:
                breakthrough_score = min(1.0, breakthrough_score + self.FAVORITE_BOOST)
                logger.debug(
                    f"Applied favorite boost (+{self.FAVORITE_BOOST:.0%}) to {paper.arxiv_id}"
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
