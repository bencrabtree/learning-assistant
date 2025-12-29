"""
HackerNews Tracker for social signals.

Uses the Algolia HN Search API to find arXiv papers that have been
discussed on HackerNews, providing social proof signals.
"""

import re
from datetime import datetime, timedelta
from typing import Any

import requests
from loguru import logger


class HackerNewsTracker:
    """Tracker for HackerNews discussions of arXiv papers."""

    ALGOLIA_API = "https://hn.algolia.com/api/v1"

    def __init__(self):
        """Initialize the tracker."""
        self.session = requests.Session()

    def _search_algolia(
        self, query: str, tags: str = "story", num_results: int = 100
    ) -> dict[str, Any] | None:
        """
        Search HN using Algolia API.

        Args:
            query: Search query
            tags: Filter tags (story, comment, etc.)
            num_results: Maximum results to return

        Returns:
            API response dict or None on error
        """
        url = f"{self.ALGOLIA_API}/search"
        params = {"query": query, "tags": tags, "hitsPerPage": num_results}

        try:
            response = self.session.get(url, params=params, timeout=30)
            if response.status_code == 200:
                return response.json()
            logger.warning(f"Algolia API error: {response.status_code}")
            return None
        except requests.RequestException as e:
            logger.error(f"Algolia request failed: {e}")
            return None

    def _extract_arxiv_id(self, text: str | None, url: str | None) -> str | None:
        """
        Extract arXiv ID from text or URL.

        Args:
            text: Text content to search
            url: URL to parse

        Returns:
            arXiv ID if found, None otherwise
        """
        # Pattern for arXiv IDs (e.g., 2312.12345, 1901.00001v2)
        pattern = r"(\d{4}\.\d{4,5}(?:v\d+)?)"

        # Check URL first
        if url and "arxiv.org" in url:
            match = re.search(pattern, url)
            if match:
                # Remove version suffix for consistency
                arxiv_id = match.group(1)
                return re.sub(r"v\d+$", "", arxiv_id)

        # Check text content
        if text and "arxiv.org" in text.lower():
            match = re.search(pattern, text)
            if match:
                arxiv_id = match.group(1)
                return re.sub(r"v\d+$", "", arxiv_id)

        return None

    def calculate_social_score(self, hn_data: dict[str, Any]) -> float:
        """
        Calculate a social score based on HN engagement.

        Scoring rubric:
        - Score > 200: 0.30
        - Score > 100: 0.20
        - Score > 50: 0.10
        - Comments > 100: 0.15
        - Comments > 50: 0.10
        - Comments > 20: 0.05

        Args:
            hn_data: Dict with score and comments_count

        Returns:
            Social score between 0.0 and 0.5
        """
        score = hn_data.get("score", 0)
        comments = hn_data.get("comments_count", 0)

        social_score = 0.0

        # Score-based component
        if score > 200:
            social_score += 0.30
        elif score > 100:
            social_score += 0.20
        elif score > 50:
            social_score += 0.10

        # Comments-based component
        if comments > 100:
            social_score += 0.15
        elif comments > 50:
            social_score += 0.10
        elif comments > 20:
            social_score += 0.05

        return min(social_score, 0.5)

    def search_arxiv_papers(self, days_back: int = 7) -> list[dict[str, Any]]:
        """
        Search for arXiv papers mentioned on HN.

        Args:
            days_back: How many days back to search

        Returns:
            List of dicts with arxiv_id and HN engagement data
        """
        # Use search_by_date endpoint with date filter for recent results
        cutoff = datetime.now() - timedelta(days=days_back)
        cutoff_timestamp = int(cutoff.timestamp())

        url = f"{self.ALGOLIA_API}/search_by_date"
        params = {
            "query": "arxiv.org",
            "tags": "story",
            "numericFilters": f"created_at_i>{cutoff_timestamp}",
            "hitsPerPage": 200,
        }

        try:
            response = self.session.get(url, params=params, timeout=30)
            if response.status_code != 200:
                logger.warning(f"Algolia API error: {response.status_code}")
                return []
            result = response.json()
        except requests.RequestException as e:
            logger.error(f"Algolia request failed: {e}")
            return []

        papers = {}

        for hit in result.get("hits", []):
            created_at = hit.get("created_at_i", 0)

            # Extract arXiv ID
            url = hit.get("url", "")
            title = hit.get("title", "")
            arxiv_id = self._extract_arxiv_id(title, url)

            if not arxiv_id:
                continue

            # Aggregate scores for duplicate posts
            if arxiv_id in papers:
                papers[arxiv_id]["score"] += hit.get("points", 0)
                papers[arxiv_id]["comments_count"] += hit.get("num_comments", 0)
                papers[arxiv_id]["posts"].append(hit.get("objectID"))
            else:
                papers[arxiv_id] = {
                    "arxiv_id": arxiv_id,
                    "score": hit.get("points", 0),
                    "comments_count": hit.get("num_comments", 0),
                    "hn_title": title,
                    "posts": [hit.get("objectID")],
                    "first_posted": datetime.fromtimestamp(created_at),
                }

        return list(papers.values())

    def get_paper_signals(self, arxiv_id: str) -> dict[str, Any] | None:
        """
        Get HN signals for a specific paper.

        Args:
            arxiv_id: The arXiv identifier

        Returns:
            Dict with HN engagement data or None
        """
        result = self._search_algolia(arxiv_id, tags="story", num_results=20)
        if not result or not result.get("hits"):
            return None

        total_score = 0
        total_comments = 0
        posts = []

        for hit in result.get("hits", []):
            # Verify this is actually about this paper
            url = hit.get("url", "")
            title = hit.get("title", "")
            extracted_id = self._extract_arxiv_id(title, url)

            if extracted_id == arxiv_id:
                total_score += hit.get("points", 0)
                total_comments += hit.get("num_comments", 0)
                posts.append(
                    {
                        "id": hit.get("objectID"),
                        "title": title,
                        "score": hit.get("points", 0),
                        "comments": hit.get("num_comments", 0),
                    }
                )

        if not posts:
            return None

        return {
            "arxiv_id": arxiv_id,
            "score": total_score,
            "comments_count": total_comments,
            "num_posts": len(posts),
            "posts": posts,
        }


def fetch_hn_signals(days_back: int = 7) -> list[dict[str, Any]]:
    """
    Fetch HN signals for recent arXiv papers.

    Args:
        days_back: How many days back to search

    Returns:
        List of papers with HN engagement data
    """
    tracker = HackerNewsTracker()
    papers = tracker.search_arxiv_papers(days_back=days_back)

    # Calculate social scores
    for paper in papers:
        paper["social_score"] = tracker.calculate_social_score(paper)

    # Sort by social score
    papers.sort(key=lambda x: x["social_score"], reverse=True)

    logger.info(f"Found {len(papers)} arXiv papers on HN from last {days_back} days")
    return papers
