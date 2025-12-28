"""
Semantic Scholar API Client for citation data.

Fetches citation counts and influential citation counts for papers
to help assess their academic impact.
"""

import time
from typing import Any

import requests
from loguru import logger

from src.config import settings
from src.database import get_db_session
from src.models.paper import Paper


class SemanticScholarClient:
    """Client for Semantic Scholar API."""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self):
        """Initialize the client with optional API key."""
        self.api_key = settings.semantic_scholar_api_key
        self.headers = {}
        if self.api_key:
            self.headers["x-api-key"] = self.api_key

    def _make_request(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """Make a request to the Semantic Scholar API."""
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            if response.status_code == 200:
                return response.json()
            if response.status_code == 404:
                logger.debug(f"Paper not found: {endpoint}")
                return None
            if response.status_code == 429:
                logger.warning("Rate limited by Semantic Scholar API")
                time.sleep(5)
                return None
            logger.warning(f"Semantic Scholar API error: {response.status_code}")
            return None
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None

    def get_citation_counts(self, arxiv_id: str) -> dict[str, Any] | None:
        """
        Get citation counts for a paper by arXiv ID.

        Args:
            arxiv_id: The arXiv identifier (e.g., "2312.12345")

        Returns:
            Dict with citation_count and influential_citation_count, or None
        """
        endpoint = f"paper/arXiv:{arxiv_id}"
        params = {"fields": "citationCount,influentialCitationCount,title"}

        result = self._make_request(endpoint, params)
        if result:
            return {
                "citation_count": result.get("citationCount") or 0,
                "influential_citation_count": result.get("influentialCitationCount") or 0,
                "paper_id": result.get("paperId"),
            }
        return None

    def update_paper_citations(self, paper: Paper) -> bool:
        """
        Update a paper's citation counts in the database.

        Args:
            paper: Paper object to update

        Returns:
            True if successfully updated, False otherwise
        """
        counts = self.get_citation_counts(paper.arxiv_id)
        if counts is None:
            return False

        with get_db_session() as db:
            db_paper = db.query(Paper).filter_by(arxiv_id=paper.arxiv_id).first()
            if db_paper:
                db_paper.citation_count = counts["citation_count"]
                db_paper.influential_citation_count = counts["influential_citation_count"]
                logger.debug(
                    f"Updated citations for {paper.arxiv_id}: "
                    f"{counts['citation_count']} citations"
                )
                return True
        return False


def fetch_citations_for_papers(papers: list[Paper]) -> int:
    """
    Fetch citation counts for a list of papers.

    Args:
        papers: List of Paper objects to fetch citations for

    Returns:
        Number of papers successfully updated
    """
    if not papers:
        return 0

    client = SemanticScholarClient()
    updated = 0

    for paper in papers:
        if client.update_paper_citations(paper):
            updated += 1
        # Rate limiting - be nice to the API
        time.sleep(0.5)

    logger.info(f"Updated citations for {updated}/{len(papers)} papers")
    return updated
