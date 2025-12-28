"""
Social signal trackers for discovering trending papers.

This module provides integrations with social platforms to identify
papers that are generating discussion and interest.
"""

from src.trackers.hackernews import HackerNewsTracker, fetch_hn_signals
from src.trackers.twitter import TwitterTracker, fetch_twitter_signals

__all__ = [
    "HackerNewsTracker",
    "TwitterTracker",
    "fetch_hn_signals",
    "fetch_twitter_signals",
]
