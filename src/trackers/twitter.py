"""
Twitter Tracker for social signals.

Uses the Twitter API v2 to find arXiv papers that have been tweeted
by AI labs and researchers, providing social proof signals.
"""

import re
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar

import requests
from loguru import logger


class TwitterTracker:
    """Tracker for Twitter discussions of arXiv papers."""

    API_BASE: ClassVar[str] = "https://api.twitter.com/2"

    # Default AI lab accounts to monitor
    DEFAULT_LAB_ACCOUNTS: ClassVar[list[str]] = [
        "AnthropicAI",
        "OpenAI",
        "GoogleDeepMind",
        "GoogleAI",
        "MetaAI",
        "xaboratory",  # xAI
        "nvidia",
        "MistralAI",
        "AIatMeta",
    ]

    def __init__(self, bearer_token: str | None = None):
        """
        Initialize the Twitter tracker.

        Args:
            bearer_token: Twitter API v2 bearer token. If not provided,
                         will try to load from config.
        """
        from src.config import settings

        self.bearer_token = bearer_token or settings.twitter_bearer_token
        self.session = requests.Session()

        if self.bearer_token:
            self.session.headers.update({"Authorization": f"Bearer {self.bearer_token}"})

        # Load lab accounts from config or use defaults
        lab_accounts_str = settings.lab_twitter_accounts
        if lab_accounts_str:
            self.lab_accounts = [a.strip() for a in lab_accounts_str.split(",")]
        else:
            self.lab_accounts = self.DEFAULT_LAB_ACCOUNTS

    def _is_configured(self) -> bool:
        """Check if Twitter API is configured."""
        return self.bearer_token is not None

    def _make_request(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """
        Make a request to the Twitter API.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            API response dict or None on error
        """
        if not self._is_configured():
            logger.debug("Twitter API not configured (no bearer token)")
            return None

        url = f"{self.API_BASE}/{endpoint}"

        try:
            response = self.session.get(url, params=params, timeout=30)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                logger.warning("Twitter API authentication failed")
            elif response.status_code == 429:
                logger.warning("Twitter API rate limit exceeded")
            else:
                logger.warning(f"Twitter API error: {response.status_code}")

            return None

        except requests.RequestException as e:
            logger.error(f"Twitter request failed: {e}")
            return None

    def _extract_arxiv_id(self, text: str) -> str | None:
        """
        Extract arXiv ID from tweet text.

        Args:
            text: Tweet text content

        Returns:
            arXiv ID if found, None otherwise
        """
        # Pattern for arXiv IDs (e.g., 2312.12345, 1901.00001v2)
        pattern = r"(\d{4}\.\d{4,5}(?:v\d+)?)"

        # Check for arXiv URL or ID in text
        if "arxiv.org" in text.lower() or "arxiv:" in text.lower():
            match = re.search(pattern, text)
            if match:
                # Remove version suffix for consistency
                arxiv_id = match.group(1)
                return re.sub(r"v\d+$", "", arxiv_id)

        return None

    def _extract_arxiv_urls(self, text: str) -> list[str]:
        """
        Extract all arXiv IDs from tweet text.

        Args:
            text: Tweet text content

        Returns:
            List of arXiv IDs found
        """
        arxiv_ids = []

        # Pattern for arXiv URLs
        url_pattern = r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})"
        for match in re.finditer(url_pattern, text, re.IGNORECASE):
            arxiv_id = re.sub(r"v\d+$", "", match.group(1))
            if arxiv_id not in arxiv_ids:
                arxiv_ids.append(arxiv_id)

        # Pattern for bare arXiv IDs after "arxiv:" prefix
        bare_pattern = r"arxiv[:\s]+(\d{4}\.\d{4,5})"
        for match in re.finditer(bare_pattern, text, re.IGNORECASE):
            arxiv_id = re.sub(r"v\d+$", "", match.group(1))
            if arxiv_id not in arxiv_ids:
                arxiv_ids.append(arxiv_id)

        return arxiv_ids

    def calculate_social_score(self, tweet_data: dict[str, Any]) -> float:
        """
        Calculate a social score based on tweet engagement.

        Scoring rubric:
        - Likes > 1000: 0.25
        - Likes > 500: 0.20
        - Likes > 100: 0.15
        - Likes > 50: 0.10
        - Retweets > 500: 0.15
        - Retweets > 100: 0.10
        - Retweets > 50: 0.05
        - Quote tweets > 50: 0.05
        - From verified lab account: 0.10 bonus

        Args:
            tweet_data: Dict with engagement metrics

        Returns:
            Social score between 0.0 and 0.5
        """
        likes = tweet_data.get("likes", 0)
        retweets = tweet_data.get("retweets", 0)
        quotes = tweet_data.get("quote_count", 0)
        is_lab_account = tweet_data.get("is_lab_account", False)

        social_score = 0.0

        # Like-based scoring
        if likes > 1000:
            social_score += 0.25
        elif likes > 500:
            social_score += 0.20
        elif likes > 100:
            social_score += 0.15
        elif likes > 50:
            social_score += 0.10

        # Retweet-based scoring
        if retweets > 500:
            social_score += 0.15
        elif retweets > 100:
            social_score += 0.10
        elif retweets > 50:
            social_score += 0.05

        # Quote tweet scoring
        if quotes > 50:
            social_score += 0.05

        # Lab account bonus
        if is_lab_account:
            social_score += 0.10

        return min(social_score, 0.5)

    def search_arxiv_tweets(self, days_back: int = 7) -> list[dict[str, Any]]:
        """
        Search for tweets containing arXiv links.

        Args:
            days_back: How many days back to search

        Returns:
            List of dicts with arxiv_id and Twitter engagement data
        """
        if not self._is_configured():
            logger.info("Twitter tracker not configured - skipping")
            return []

        # Build search query for arXiv papers
        query = "arxiv.org -is:retweet"

        # Calculate start time
        start_time = datetime.now(UTC) - timedelta(days=days_back)
        start_time_str = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")

        params = {
            "query": query,
            "max_results": 100,
            "start_time": start_time_str,
            "tweet.fields": "created_at,public_metrics,author_id",
            "expansions": "author_id",
            "user.fields": "username,verified",
        }

        result = self._make_request("tweets/search/recent", params)
        if not result or "data" not in result:
            return []

        # Build user lookup
        users = {}
        for user in result.get("includes", {}).get("users", []):
            users[user["id"]] = {
                "username": user.get("username", ""),
                "verified": user.get("verified", False),
            }

        # Process tweets
        papers: dict[str, dict[str, Any]] = {}

        for tweet in result.get("data", []):
            text = tweet.get("text", "")
            arxiv_ids = self._extract_arxiv_urls(text)

            if not arxiv_ids:
                continue

            metrics = tweet.get("public_metrics", {})
            author_id = tweet.get("author_id", "")
            author = users.get(author_id, {})
            username = author.get("username", "")
            is_lab = username.lower() in [a.lower() for a in self.lab_accounts]

            for arxiv_id in arxiv_ids:
                tweet_data = {
                    "tweet_id": tweet.get("id"),
                    "likes": metrics.get("like_count", 0),
                    "retweets": metrics.get("retweet_count", 0),
                    "replies": metrics.get("reply_count", 0),
                    "quote_count": metrics.get("quote_count", 0),
                    "author": username,
                    "is_lab_account": is_lab,
                    "created_at": tweet.get("created_at"),
                }

                # Aggregate scores for duplicate papers
                if arxiv_id in papers:
                    papers[arxiv_id]["likes"] += tweet_data["likes"]
                    papers[arxiv_id]["retweets"] += tweet_data["retweets"]
                    papers[arxiv_id]["replies"] += tweet_data["replies"]
                    papers[arxiv_id]["tweets"].append(tweet_data)
                    if is_lab:
                        papers[arxiv_id]["is_lab_account"] = True
                else:
                    papers[arxiv_id] = {
                        "arxiv_id": arxiv_id,
                        "source": "twitter",
                        "likes": tweet_data["likes"],
                        "retweets": tweet_data["retweets"],
                        "replies": tweet_data["replies"],
                        "is_lab_account": is_lab,
                        "tweets": [tweet_data],
                    }

        return list(papers.values())

    def get_lab_tweets(self, days_back: int = 7) -> list[dict[str, Any]]:
        """
        Get tweets from AI lab accounts that mention arXiv papers.

        Args:
            days_back: How many days back to search

        Returns:
            List of papers mentioned by lab accounts
        """
        if not self._is_configured():
            logger.info("Twitter tracker not configured - skipping")
            return []

        all_papers: dict[str, dict[str, Any]] = {}

        for account in self.lab_accounts:
            # Build query for specific account
            query = f"from:{account} arxiv.org -is:retweet"

            start_time = datetime.now(UTC) - timedelta(days=days_back)
            start_time_str = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")

            params = {
                "query": query,
                "max_results": 100,
                "start_time": start_time_str,
                "tweet.fields": "created_at,public_metrics",
            }

            result = self._make_request("tweets/search/recent", params)
            if not result or "data" not in result:
                continue

            for tweet in result.get("data", []):
                text = tweet.get("text", "")
                arxiv_ids = self._extract_arxiv_urls(text)

                for arxiv_id in arxiv_ids:
                    metrics = tweet.get("public_metrics", {})

                    if arxiv_id in all_papers:
                        all_papers[arxiv_id]["likes"] += metrics.get("like_count", 0)
                        all_papers[arxiv_id]["retweets"] += metrics.get("retweet_count", 0)
                        all_papers[arxiv_id]["lab_accounts"].add(account)
                    else:
                        all_papers[arxiv_id] = {
                            "arxiv_id": arxiv_id,
                            "source": "twitter",
                            "likes": metrics.get("like_count", 0),
                            "retweets": metrics.get("retweet_count", 0),
                            "replies": metrics.get("reply_count", 0),
                            "is_lab_account": True,
                            "lab_accounts": {account},
                        }

        # Convert sets to lists for JSON serialization
        for paper in all_papers.values():
            if "lab_accounts" in paper:
                paper["lab_accounts"] = list(paper["lab_accounts"])

        return list(all_papers.values())


def fetch_twitter_signals(days_back: int = 7) -> list[dict[str, Any]]:
    """
    Fetch Twitter signals for recent arXiv papers.

    Args:
        days_back: How many days back to search

    Returns:
        List of papers with Twitter engagement data
    """
    tracker = TwitterTracker()

    if not tracker._is_configured():
        logger.info("Twitter API not configured - returning empty signals")
        return []

    # Get general arXiv tweets
    papers = tracker.search_arxiv_tweets(days_back=days_back)

    # Calculate social scores
    for paper in papers:
        paper["social_score"] = tracker.calculate_social_score(paper)

    # Sort by social score
    papers.sort(key=lambda x: x["social_score"], reverse=True)

    logger.info(f"Found {len(papers)} arXiv papers on Twitter from last {days_back} days")
    return papers
