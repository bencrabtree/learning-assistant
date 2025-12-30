"""
Curator Agent - Multi-Signal Paper Scoring and Ranking

Scores and ranks papers using multiple signals:
- Interest match (keyword matching against user interests + favorite concepts)
- Social proof (HackerNews engagement)
- Citation impact (Semantic Scholar data, age-adjusted)
- Breakthrough potential (Claude assessment)

Scoring weights:
- Interest match: 25%
- Social proof: 25%
- Citation score: 20%
- Breakthrough: 30%

Digest-worthy threshold:
- Breakthrough score >= 0.8 OR aggregate score >= 0.7

Seed Papers (Favorites):
- Concepts from favorite papers are extracted and used for interest matching
- Papers matching seed concepts get a bonus in interest scoring
- Favorites with ReadingProgress status='unread' are always included in digest
"""

from datetime import UTC, datetime, timedelta

from loguru import logger

from src.config import get_research_interests_list, settings
from src.database import get_db_session
from src.models.paper import Paper

# Scoring weights
WEIGHT_INTEREST = 0.25
WEIGHT_SOCIAL = 0.25
WEIGHT_CITATION = 0.20
WEIGHT_BREAKTHROUGH = 0.30

# Thresholds
DIGEST_WORTHY_AGGREGATE = 0.7
DIGEST_WORTHY_BREAKTHROUGH = 0.8

# Seed paper bonus weight
SEED_CONCEPT_BONUS = 0.3  # 30% bonus for matching seed concepts


def get_seed_concepts() -> list[str]:
    """
    Extract concepts from favorite (seed) papers.

    Returns a list of unique concepts from all papers marked as favorites.
    These concepts define what topics the user cares about most.
    """
    try:
        with get_db_session() as db:
            favorites = db.query(Paper).filter(Paper.is_favorite).all()

            if not favorites:
                return []

            # Collect all concepts from favorites
            seed_concepts = set()
            for paper in favorites:
                if paper.concepts:
                    for concept in paper.concepts:
                        # Normalize to lowercase for matching
                        seed_concepts.add(concept.lower())

            logger.debug(
                f"Loaded {len(seed_concepts)} seed concepts from {len(favorites)} favorites"
            )
            return list(seed_concepts)
    except Exception as e:
        # Database may not exist in test environments
        logger.debug(f"Could not load seed concepts (likely in test): {e}")
        return []


class CuratorAgent:
    """Agent that scores and ranks papers using multiple signals."""

    def __init__(self, interests: list[str] | None = None, use_seed_concepts: bool = True):
        """
        Initialize the Curator agent.

        Args:
            interests: User interests from config (defaults to RESEARCH_INTERESTS)
            use_seed_concepts: Whether to include concepts from favorite papers
        """
        self.interests = interests or get_research_interests_list()
        self.seed_concepts = get_seed_concepts() if use_seed_concepts else []
        if self.seed_concepts:
            logger.info(f"Using {len(self.seed_concepts)} seed concepts from favorites")

    def calculate_interest_score(self, paper: Paper) -> float:
        """
        Calculate interest match score based on concept overlap.

        Combines two signals:
        1. Match against user's configured RESEARCH_INTERESTS
        2. Match against concepts extracted from favorite (seed) papers

        Papers matching seed concepts get a bonus because they're similar
        to papers the user has explicitly marked as important.
        """
        if not paper.concepts:
            return 0.0

        paper_concepts = [c.lower() for c in paper.concepts]
        user_interests = [i.lower() for i in self.interests]

        # Score 1: Match against user interests (from config)
        interest_matches = 0
        for interest in user_interests:
            for concept in paper_concepts:
                if interest in concept or concept in interest:
                    interest_matches += 1
                    break

        interest_score = interest_matches / len(user_interests) if user_interests else 0.0

        # Score 2: Match against seed concepts (from favorites)
        seed_matches = 0
        if self.seed_concepts:
            for seed_concept in self.seed_concepts:
                for concept in paper_concepts:
                    if seed_concept in concept or concept in seed_concept:
                        seed_matches += 1
                        break

            seed_score = seed_matches / len(self.seed_concepts)
        else:
            seed_score = 0.0

        # Combine: interest score + bonus for matching seed concepts
        # Seed bonus rewards papers similar to what user explicitly liked
        combined = interest_score + (SEED_CONCEPT_BONUS * seed_score)

        return min(combined, 1.0)  # Cap at 1.0

    def calculate_social_score(self, paper: Paper) -> float:
        """Get combined social score from HN and Twitter signals.

        Uses pre-calculated social scores stored in score_components.
        Returns the maximum of HN and Twitter scores.
        """
        if not paper.score_components:
            return 0.0

        # Use pre-calculated scores from signal node
        hn_social = paper.score_components.get("hn_social_score", 0.0)
        twitter_social = paper.score_components.get("twitter_social_score", 0.0)

        # Return max score (trending on either platform counts)
        return max(hn_social, twitter_social)

    def calculate_citation_score(self, paper: Paper) -> float:
        """Calculate age-adjusted citation score."""
        now = datetime.now(UTC)
        paper_age = now - paper.published_date.replace(tzinfo=UTC)

        if paper_age < timedelta(days=7):
            return 0.5  # Neutral for new papers

        citations = getattr(paper, "citation_count", 0) or 0
        influential = getattr(paper, "influential_citation_count", 0) or 0

        months = max(1, paper_age.days / 30)
        citations_per_month = citations / months
        influential_per_month = influential / months

        score = 0.0
        if citations_per_month > 50:
            score += 0.5
        elif citations_per_month > 20:
            score += 0.3
        elif citations_per_month > 5:
            score += 0.15

        if influential_per_month > 10:
            score += 0.5
        elif influential_per_month > 5:
            score += 0.3
        elif influential_per_month > 1:
            score += 0.15

        return min(score, 1.0)

    def calculate_breakthrough_score(self, paper: Paper) -> float:
        """Get breakthrough score from assessment."""
        return getattr(paper, "breakthrough_score", 0.0) or 0.0

    def calculate_combined_score(self, paper: Paper) -> float:
        """Calculate weighted combined score from all signals."""
        interest = self.calculate_interest_score(paper)
        social = self.calculate_social_score(paper)
        citation = self.calculate_citation_score(paper)
        breakthrough = self.calculate_breakthrough_score(paper)

        return (
            WEIGHT_INTEREST * interest
            + WEIGHT_SOCIAL * social
            + WEIGHT_CITATION * citation
            + WEIGHT_BREAKTHROUGH * breakthrough
        )

    def is_digest_worthy(self, paper: Paper) -> bool:
        """Check if paper meets HIGH BAR for digest inclusion."""
        breakthrough = self.calculate_breakthrough_score(paper)
        if breakthrough >= DIGEST_WORTHY_BREAKTHROUGH:
            return True
        return self.calculate_combined_score(paper) >= DIGEST_WORTHY_AGGREGATE

    def score_paper(self, paper: Paper) -> float:
        """Score a single paper using all available signals."""
        return self.calculate_combined_score(paper)

    def score_papers(self, papers: list[Paper]) -> list[Paper]:
        """Score all papers and sort by relevance."""
        logger.info(f"Scoring {len(papers)} papers...")

        for paper in papers:
            try:
                paper.relevance_score = self.score_paper(paper)
            except Exception as e:
                logger.error(f"Failed to score {paper.arxiv_id}: {e}")
                paper.relevance_score = 0.0

        papers.sort(key=lambda p: p.relevance_score or 0, reverse=True)
        logger.info(f"Scored and ranked {len(papers)} papers")
        return papers

    def save_scores(self, papers: list[Paper]) -> int:
        """Save relevance scores to the database."""
        count = 0
        now = datetime.now(UTC)

        with get_db_session() as db:
            for paper in papers:
                db_paper = db.query(Paper).filter_by(arxiv_id=paper.arxiv_id).first()
                if db_paper:
                    db_paper.relevance_score = paper.relevance_score
                    db_paper.scored_at = now
                    count += 1

        logger.info(f"Saved scores for {count} papers")
        return count

    def score_and_save(self, papers: list[Paper]) -> list[Paper]:
        """Score papers and save to database."""
        scored = self.score_papers(papers)
        self.save_scores(scored)
        return scored

    def select_top_papers(self, papers: list[Paper], n: int | None = None) -> list[Paper]:
        """Select top N papers by relevance."""
        n = n or settings.max_papers_per_digest
        if not all(p.relevance_score is not None for p in papers):
            papers = self.score_papers(papers)
        return papers[:n]

    def get_digest_worthy(self, papers: list[Paper]) -> list[Paper]:
        """Filter papers to only digest-worthy ones."""
        worthy = [p for p in papers if self.is_digest_worthy(p)]
        logger.info(f"Found {len(worthy)}/{len(papers)} digest-worthy papers")
        return worthy


def curate_papers_batch(papers: list[Paper], top_n: int | None = None) -> list[Paper]:
    """Score and select top papers."""
    curator = CuratorAgent()
    ranked = curator.score_and_save(papers)
    return curator.select_top_papers(ranked, n=top_n)


def get_digest_worthy(papers: list[Paper]) -> list[Paper]:
    """Get only digest-worthy papers from a list."""
    curator = CuratorAgent()
    for paper in papers:
        if paper.relevance_score is None:
            paper.relevance_score = curator.score_paper(paper)
    return curator.get_digest_worthy(papers)


def get_unread_favorites() -> list[Paper]:
    """
    Get favorite papers that are still unread.

    These are seed papers that should always be included in email digests
    to ensure the user sees the papers they've explicitly marked as important.

    Returns:
        List of favorite papers with ReadingProgress status='unread' or no progress
    """
    from src.models.paper import ReadingProgress

    try:
        with get_db_session() as db:
            # Get favorites that are either:
            # 1. Have no ReadingProgress record (newly imported)
            # 2. Have ReadingProgress with status='unread'
            favorites = db.query(Paper).filter(Paper.is_favorite).all()

            unread = []
            for paper in favorites:
                progress = db.query(ReadingProgress).filter_by(paper_id=paper.arxiv_id).first()
                if not progress or progress.status == "unread":
                    unread.append(paper)

            logger.debug(f"Found {len(unread)}/{len(favorites)} unread favorites")
            return unread
    except Exception as e:
        # Database may not exist in test environments
        logger.debug(f"Could not load unread favorites (likely in test): {e}")
        return []
