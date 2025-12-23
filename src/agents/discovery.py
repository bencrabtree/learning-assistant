"""
ArXiv Discovery Agent

This agent searches arXiv for recent papers in AI/ML categories.

Key Concepts:
- Discovery = Finding new papers
- arXiv API = Free API for querying research papers
- Categories = cs.AI, cs.LG, cs.CL, cs.CV (AI, ML, NLP, Vision)
- Date filtering = Only get papers from last N days

How it works:
1. Build a query string (categories + date range)
2. Call arXiv API
3. Parse results into Paper objects
4. Save to database
5. Return list of papers

Example:
    agent = DiscoveryAgent()
    papers = agent.discover_papers(days_back=1)
    # Returns papers from the last 24 hours
"""

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import arxiv
from loguru import logger

from src.config import settings, get_arxiv_categories_list
from src.models.paper import Paper
from src.database import get_db_session


class DiscoveryAgent:
    """
    Agent that discovers new papers from arXiv.

    This agent uses the arXiv API to:
    - Search for papers in specified categories
    - Filter by publication date
    - Extract paper metadata
    - Save to database

    Follows the same class-based pattern as ReaderAgent, ExplainerAgent, and CuratorAgent.
    """

    def __init__(
        self,
        categories: Optional[List[str]] = None,
        max_results: int = 1000
    ):
        """
        Initialize the Discovery agent.

        Args:
            categories: List of arXiv categories to search (defaults to config)
            max_results: Maximum number of papers to fetch from API
        """
        self.categories = categories or get_arxiv_categories_list()
        self.max_results = max_results
        logger.debug(f"DiscoveryAgent initialized with categories={self.categories}, max_results={max_results}")

    def build_query(self) -> str:
        """
        Build an arXiv API query string.

        ArXiv query syntax:
        - cat:cs.AI = Papers in the cs.AI category
        - OR = Combine multiple categories
        - submittedDate:[start TO end] = Date range filter

        Returns:
            Query string for arXiv API

        Example:
            agent = DiscoveryAgent(categories=["cs.AI", "cs.LG"])
            query = agent.build_query()
            # Returns: "(cat:cs.AI OR cat:cs.LG)"
        """
        # Build category query
        # Example: "cat:cs.AI OR cat:cs.LG OR cat:cs.CL"
        category_queries = [f"cat:{cat}" for cat in self.categories]
        query = "(" + " OR ".join(category_queries) + ")"

        logger.debug(f"Built arXiv query: {query}")
        return query

    def fetch_papers(self, days_back: int = 1) -> List[Dict]:
        """
        Fetch papers from arXiv API.

        This is the core discovery method. It:
        1. Builds a query
        2. Calls arXiv API
        3. Filters by date
        4. Converts results to dictionaries

        Args:
            days_back: How many days back to look

        Returns:
            List of paper dictionaries with metadata

        Example:
            agent = DiscoveryAgent()
            papers = agent.fetch_papers(days_back=1)
            for paper in papers:
                print(paper["title"])
        """
        logger.info(f"Fetching papers from arXiv (categories={self.categories}, days_back={days_back})")

        # Calculate date cutoff
        # We only want papers published after this date
        # Use timezone-aware datetime (UTC) to match arXiv API results
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        logger.debug(f"Cutoff date: {cutoff_date}")

        # Build query
        query = self.build_query()

        try:
            # Create arXiv search client
            # The arxiv library provides a nice Python wrapper around the API
            search = arxiv.Search(
                query=query,
                max_results=self.max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate,  # Newest first
                sort_order=arxiv.SortOrder.Descending,
            )

            papers = []

            # Iterate through results
            # Note: The arXiv API returns a generator, not a list
            # This is memory-efficient for large result sets
            for result in search.results():
                # Check if paper is recent enough
                # result.published is a datetime object
                if result.published < cutoff_date:
                    # Papers are sorted by date, so we can stop here
                    logger.debug(f"Reached papers older than cutoff ({result.published}), stopping")
                    break

                # Extract metadata
                # The arxiv library provides a Result object with all the fields we need
                paper_data = {
                    "arxiv_id": result.entry_id.split("/")[-1],  # Extract ID from URL
                    "title": result.title.strip(),
                    "abstract": result.summary.strip(),
                    "authors": [author.name for author in result.authors],
                    "published_date": result.published,
                    "categories": result.categories,
                    "pdf_url": result.pdf_url,
                    "abstract_url": result.entry_id,
                    "discovered_by": "arxiv",
                }

                papers.append(paper_data)

                logger.debug(f"Found: {paper_data['title'][:50]}...")

            logger.info(f"✅ Fetched {len(papers)} papers from arXiv")
            return papers

        except Exception as e:
            logger.error(f"❌ ArXiv API call failed: {e}")
            raise

    def save_papers(self, papers: List[Dict]) -> int:
        """
        Save papers to the database.

        This handles:
        - Creating Paper objects from dictionaries
        - Checking for duplicates (same arxiv_id)
        - Inserting new papers only

        Args:
            papers: List of paper dictionaries

        Returns:
            Number of new papers saved

        Example:
            agent = DiscoveryAgent()
            papers = agent.fetch_papers()
            num_saved = agent.save_papers(papers)
            print(f"Saved {num_saved} new papers")
        """
        logger.info(f"Saving {len(papers)} papers to database...")

        new_papers_count = 0

        with get_db_session() as db:
            for paper_data in papers:
                arxiv_id = paper_data["arxiv_id"]

                # Check if paper already exists
                # We query by arxiv_id (the primary key)
                existing = db.query(Paper).filter_by(arxiv_id=arxiv_id).first()

                if existing:
                    logger.debug(f"Paper {arxiv_id} already exists, skipping")
                    continue

                # Create new Paper object
                # **paper_data unpacks the dictionary as keyword arguments
                # This is equivalent to:
                # Paper(arxiv_id="...", title="...", abstract="...", ...)
                paper = Paper(**paper_data)

                # Add to session
                # This stages the paper for insertion
                # The actual INSERT happens when we commit (automatically at end of with block)
                db.add(paper)
                new_papers_count += 1

                logger.debug(f"Added paper: {paper.title[:50]}...")

            # Commit happens automatically when we exit the with block
            # All papers are inserted in a single transaction

        logger.info(f"✅ Saved {new_papers_count} new papers to database")
        return new_papers_count

    def discover_papers(self, days_back: Optional[int] = None) -> List[Paper]:
        """
        Main entry point for paper discovery.

        This is the main method you call to find and save new papers.

        High-level flow:
        1. Fetch papers from arXiv
        2. Save to database
        3. Return Paper objects

        Args:
            days_back: How many days back to search (defaults to config setting)

        Returns:
            List of Paper objects that were discovered

        Example:
            # Find papers from last 2 days
            agent = DiscoveryAgent()
            papers = agent.discover_papers(days_back=2)

            # Use defaults from config
            papers = agent.discover_papers()
        """
        # Use config defaults if not specified
        days_back = days_back or settings.discovery_days_back

        logger.info(f"Starting paper discovery (days_back={days_back}, categories={self.categories})")

        try:
            # Step 1: Fetch from arXiv
            paper_dicts = self.fetch_papers(days_back=days_back)

            if not paper_dicts:
                logger.warning("No papers found!")
                return []

            # Step 2: Save to database
            num_saved = self.save_papers(paper_dicts)

            # Step 3: Load and return Paper objects
            # We query the database to get the full ORM objects
            # This ensures we have the latest data (in case papers were updated)
            with get_db_session() as db:
                # Get all papers discovered in this session
                # We could optimize this by only getting papers with matching arxiv_ids
                # But for now, this is simple and works
                arxiv_ids = [p["arxiv_id"] for p in paper_dicts]
                papers = db.query(Paper).filter(Paper.arxiv_id.in_(arxiv_ids)).all()

            logger.info(f"✅ Discovery complete! Found {len(papers)} papers ({num_saved} new)")
            return papers

        except Exception as e:
            logger.error(f"❌ Paper discovery failed: {e}")
            raise


# ============================================================================
# Standalone functions for backward compatibility and LangGraph integration
# ============================================================================

def discover_papers(
    days_back: Optional[int] = None,
    categories: Optional[List[str]] = None,
) -> List[Paper]:
    """
    Main entry point for paper discovery.

    This is a convenience function that wraps DiscoveryAgent.
    Provided for backward compatibility and LangGraph integration.

    High-level flow:
    1. Fetch papers from arXiv
    2. Save to database
    3. Return Paper objects

    Args:
        days_back: How many days back to search (defaults to config setting)
        categories: Which categories to search (defaults to config setting)

    Returns:
        List of Paper objects that were discovered

    Example:
        # Find papers from last 2 days
        papers = discover_papers(days_back=2)

        # Find papers in specific categories
        papers = discover_papers(categories=["cs.AI", "cs.CL"])

        # Use defaults from config
        papers = discover_papers()
    """
    agent = DiscoveryAgent(categories=categories)
    return agent.discover_papers(days_back=days_back)


# Deprecated: Legacy functions for backward compatibility
# These are wrappers around DiscoveryAgent methods

def build_arxiv_query(categories: List[str], days_back: int = 1) -> str:
    """
    Build an arXiv API query string.

    DEPRECATED: Use DiscoveryAgent.build_query() instead.
    This function is kept for backward compatibility.
    """
    agent = DiscoveryAgent(categories=categories)
    return agent.build_query()


def fetch_papers_from_arxiv(
    categories: List[str],
    days_back: int = 1,
    max_results: int = 1000
) -> List[Dict]:
    """
    Fetch papers from arXiv API.

    DEPRECATED: Use DiscoveryAgent.fetch_papers() instead.
    This function is kept for backward compatibility.
    """
    agent = DiscoveryAgent(categories=categories, max_results=max_results)
    return agent.fetch_papers(days_back=days_back)


def save_papers_to_db(papers: List[Dict]) -> int:
    """
    Save papers to the database.

    DEPRECATED: Use DiscoveryAgent.save_papers() instead.
    This function is kept for backward compatibility.
    """
    agent = DiscoveryAgent()
    return agent.save_papers(papers)


if __name__ == "__main__":
    # Test the discovery agent
    print("Testing arXiv Discovery Agent...")
    print("=" * 80)

    # Test class-based approach
    print("\n1. Testing DiscoveryAgent class:")
    agent = DiscoveryAgent()
    papers = agent.discover_papers(days_back=1)

    print(f"\n✅ Found {len(papers)} papers")

    if papers:
        print("\nFirst paper:")
        paper = papers[0]
        print(f"  Title: {paper.title}")
        print(f"  Authors: {', '.join(paper.authors)}")
        print(f"  Published: {paper.published_date}")
        print(f"  Categories: {', '.join(paper.categories)}")
        print(f"  URL: {paper.pdf_url}")

    # Test backward-compatible function
    print("\n2. Testing discover_papers() function (backward compatibility):")
    papers2 = discover_papers(days_back=1)
    print(f"✅ Function returned {len(papers2)} papers")

    print("\n✅ Discovery agent test complete!")
