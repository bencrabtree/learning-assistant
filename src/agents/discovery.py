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

from datetime import UTC, datetime, timedelta

import arxiv
from loguru import logger
from sqlalchemy.exc import IntegrityError

from src.config import get_arxiv_categories_list, settings
from src.database import get_db_session
from src.models.paper import Paper


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

    def __init__(self, categories: list[str] | None = None, max_results: int = 1000):
        """
        Initialize the Discovery agent.

        Args:
            categories: List of arXiv categories to search (defaults to config)
            max_results: Maximum number of papers to fetch from API
        """
        self.categories = categories or get_arxiv_categories_list()
        self.max_results = max_results
        logger.debug(
            f"DiscoveryAgent initialized with categories={self.categories}, max_results={max_results}"
        )

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

    def fetch_papers(self, days_back: int = 1) -> list[dict]:
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
        logger.info(
            f"Fetching papers from arXiv (categories={self.categories}, days_back={days_back})"
        )

        # Calculate date cutoff
        # We only want papers published after this date
        # Use timezone-aware datetime (UTC) to match arXiv API results
        cutoff_date = datetime.now(UTC) - timedelta(days=days_back)
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

    def save_papers(self, papers: list[dict]) -> int:
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
                # Force immediate flush to catch IntegrityError during the loop
                try:
                    db.add(paper)
                    db.flush()  # Force immediate insert to catch IntegrityError now
                    new_papers_count += 1
                    logger.debug(f"Added paper: {paper.title[:50]}...")
                except IntegrityError:
                    db.rollback()
                    logger.warning(f"Paper {arxiv_id} already exists (race condition), skipping")

            # Commit happens automatically when we exit the with block
            # All papers are inserted in a single transaction

        logger.info(f"✅ Saved {new_papers_count} new papers to database")
        return new_papers_count

    def discover_papers(self, days_back: int | None = None) -> list[Paper]:
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

        logger.info(
            f"Starting paper discovery (days_back={days_back}, categories={self.categories})"
        )

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
    days_back: int | None = None,
    categories: list[str] | None = None,
) -> list[Paper]:
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


def build_arxiv_query(categories: list[str], days_back: int = 1) -> str:
    """
    Build an arXiv API query string.

    DEPRECATED: Use DiscoveryAgent.build_query() instead.
    This function is kept for backward compatibility.
    """
    agent = DiscoveryAgent(categories=categories)
    return agent.build_query()


def fetch_papers_from_arxiv(
    categories: list[str], days_back: int = 1, max_results: int = 1000
) -> list[dict]:
    """
    Fetch papers from arXiv API.

    DEPRECATED: Use DiscoveryAgent.fetch_papers() instead.
    This function is kept for backward compatibility.
    """
    agent = DiscoveryAgent(categories=categories, max_results=max_results)
    return agent.fetch_papers(days_back=days_back)


def save_papers_to_db(papers: list[dict]) -> int:
    """
    Save papers to the database.

    DEPRECATED: Use DiscoveryAgent.save_papers() instead.
    This function is kept for backward compatibility.
    """
    agent = DiscoveryAgent()
    return agent.save_papers(papers)


def discover_papers_from_hn(
    days_back: int = 7,
    min_score: int = 10,
) -> list[Paper]:
    """
    Discover papers trending on HackerNews.

    This is a "social-first" discovery approach - instead of browsing arXiv
    categories, we find papers that the tech community is already discussing.

    Flow:
    1. Fetch HN posts mentioning arXiv (via HackerNews tracker)
    2. Filter by minimum score
    3. Extract arXiv IDs not already in database
    4. Fetch metadata from arXiv API for new papers
    5. Save with discovered_by="hackernews"
    6. Store HN signals in score_components

    Args:
        days_back: How many days back to search HN (default: 7)
        min_score: Minimum HN score to include (default: 10)

    Returns:
        List of Paper objects discovered from HN

    Example:
        # Find papers trending on HN in the last week
        papers = discover_papers_from_hn(days_back=7, min_score=10)
    """
    from src.trackers.hackernews import fetch_hn_signals

    logger.info(
        f"Discovering papers from HackerNews (days_back={days_back}, min_score={min_score})"
    )

    # Step 1: Get HN posts mentioning arXiv
    hn_papers = fetch_hn_signals(days_back=days_back)
    logger.info(f"Found {len(hn_papers)} arXiv papers mentioned on HN")

    # Step 2: Filter by minimum score
    hn_papers = [p for p in hn_papers if p.get("score", 0) >= min_score]
    logger.info(f"After min_score filter: {len(hn_papers)} papers")

    if not hn_papers:
        logger.warning("No papers meet the minimum score threshold")
        return []

    # Step 3: Find papers not already in database
    arxiv_ids = [p["arxiv_id"] for p in hn_papers]

    with get_db_session() as db:
        existing_ids = {
            p.arxiv_id for p in db.query(Paper.arxiv_id).filter(Paper.arxiv_id.in_(arxiv_ids)).all()
        }

    new_arxiv_ids = [aid for aid in arxiv_ids if aid not in existing_ids]
    logger.info(
        f"New papers to fetch: {len(new_arxiv_ids)} (skipping {len(existing_ids)} existing)"
    )

    # Build mapping of arxiv_id -> HN data for later
    hn_data_map = {p["arxiv_id"]: p for p in hn_papers}

    # Step 4: Fetch metadata from arXiv API for new papers
    new_papers_count = 0
    discovered_papers = []
    all_arxiv_ids = set()  # Track all actual arxiv_ids (with versions)

    if new_arxiv_ids:
        try:
            # Query arXiv API for the specific papers
            search = arxiv.Search(id_list=new_arxiv_ids)

            with get_db_session() as db:
                for result in search.results():
                    arxiv_id = result.entry_id.split("/")[-1]
                    # Strip version suffix for HN data lookup (e.g., "1902.01989v2" -> "1902.01989")
                    arxiv_id_base = arxiv_id.split("v")[0] if "v" in arxiv_id else arxiv_id
                    hn_data = hn_data_map.get(arxiv_id_base, {})

                    # Build score_components with HN signals
                    score_components = {
                        "hn_score": hn_data.get("score", 0),
                        "hn_comments": hn_data.get("comments_count", 0),
                        "hn_posts": len(hn_data.get("posts", [])),
                        "social_score": hn_data.get("social_score", 0),
                    }

                    paper = Paper(
                        arxiv_id=arxiv_id,
                        title=result.title.strip(),
                        abstract=result.summary.strip(),
                        authors=[author.name for author in result.authors],
                        published_date=result.published,
                        categories=result.categories,
                        pdf_url=result.pdf_url,
                        abstract_url=result.entry_id,
                        discovered_by="hackernews",
                        score_components=score_components,
                    )

                    try:
                        db.add(paper)
                        db.flush()  # Force immediate insert to catch IntegrityError now
                        new_papers_count += 1
                        all_arxiv_ids.add(arxiv_id)
                        logger.debug(
                            f"Added from HN: {paper.title[:50]}... "
                            f"(HN score: {hn_data.get('score', 0)})"
                        )
                    except IntegrityError:
                        db.rollback()
                        logger.debug(f"Paper {arxiv_id} already exists, skipping")
                        # Add to existing_ids so it gets updated below
                        existing_ids.add(arxiv_id)
                        all_arxiv_ids.add(arxiv_id)

        except Exception as e:
            logger.error(f"Failed to fetch arXiv metadata: {e}")
            raise

    # Step 5: Update existing papers with HN signals
    updated_count = 0
    if existing_ids:
        with get_db_session() as db:
            for arxiv_id in existing_ids:
                paper = db.query(Paper).filter_by(arxiv_id=arxiv_id).first()
                if paper:
                    # Strip version suffix for HN data lookup
                    arxiv_id_base = arxiv_id.split("v")[0] if "v" in arxiv_id else arxiv_id
                    hn_data = hn_data_map.get(arxiv_id_base, {})

                    # Update or create score_components
                    components = paper.score_components or {}
                    components.update(
                        {
                            "hn_score": hn_data.get("score", 0),
                            "hn_comments": hn_data.get("comments_count", 0),
                            "hn_posts": len(hn_data.get("posts", [])),
                            "social_score": hn_data.get("social_score", 0),
                        }
                    )
                    paper.score_components = components
                    updated_count += 1

    # Step 6: Return all matching papers (new + existing with HN signals)
    with get_db_session() as db:
        if all_arxiv_ids:
            discovered_papers = db.query(Paper).filter(Paper.arxiv_id.in_(all_arxiv_ids)).all()
        else:
            discovered_papers = []

    logger.info(
        f"✅ HN Discovery complete! "
        f"{new_papers_count} new papers, {updated_count} updated with HN signals"
    )
    return discovered_papers


def import_papers_by_ids(
    arxiv_ids: list[str],
    discovered_by: str = "manual",
    mark_favorite: bool = False,
    mark_unread: bool = False,
) -> list[Paper]:
    """
    Import specific papers by their arXiv IDs.

    This is useful for manually adding papers you know you want to read,
    or for importing seed papers for personalization.

    Flow:
    1. Filter out papers that already exist
    2. Fetch metadata from arXiv API
    3. Save to database with specified flags
    4. Optionally mark as favorites
    5. Optionally mark as unread (create ReadingProgress)

    Args:
        arxiv_ids: List of arXiv IDs to import (e.g., ["2501.12948", "2412.19437"])
        discovered_by: Source label (default: "manual")
        mark_favorite: Whether to mark papers as favorites (default: False)
        mark_unread: Whether to create ReadingProgress with status="unread" (default: False)

    Returns:
        List of Paper objects that were imported or already existed

    Example:
        # Import papers and mark as favorites
        papers = import_papers_by_ids(
            arxiv_ids=["2501.12948", "2412.19437"],
            mark_favorite=True,
            mark_unread=True
        )
    """
    from datetime import UTC, datetime

    from src.models.paper import ReadingProgress

    logger.info(
        f"Importing {len(arxiv_ids)} papers by ID (mark_favorite={mark_favorite}, mark_unread={mark_unread})"
    )

    if not arxiv_ids:
        logger.warning("No arXiv IDs provided")
        return []

    # Step 1: Check which papers already exist
    with get_db_session() as db:
        existing = db.query(Paper).filter(Paper.arxiv_id.in_(arxiv_ids)).all()
        existing_ids = {p.arxiv_id for p in existing}

    new_ids = [aid for aid in arxiv_ids if aid not in existing_ids]
    logger.info(f"Papers to fetch: {len(new_ids)} new, {len(existing_ids)} already exist")

    # Step 2: Fetch metadata from arXiv API for new papers
    imported_papers = []

    if new_ids:
        try:
            search = arxiv.Search(id_list=new_ids)

            with get_db_session() as db:
                for result in search.results():
                    arxiv_id = result.entry_id.split("/")[-1]

                    paper = Paper(
                        arxiv_id=arxiv_id,
                        title=result.title.strip(),
                        abstract=result.summary.strip(),
                        authors=[author.name for author in result.authors],
                        published_date=result.published,
                        categories=result.categories,
                        pdf_url=result.pdf_url,
                        abstract_url=result.entry_id,
                        discovered_by=discovered_by,
                        is_favorite=mark_favorite,
                        favorited_at=datetime.now(UTC) if mark_favorite else None,
                    )

                    try:
                        db.add(paper)
                        db.flush()
                        imported_papers.append(paper)
                        logger.debug(f"Imported: {paper.title[:50]}...")
                    except IntegrityError:
                        db.rollback()
                        logger.debug(f"Paper {arxiv_id} already exists (race condition)")
                        # Add to existing_ids so we update it below
                        existing_ids.add(arxiv_id)

        except Exception as e:
            logger.error(f"Failed to fetch papers from arXiv: {e}")
            raise

    # Step 3: Update existing papers if needed (mark_favorite, etc.)
    if existing_ids and (mark_favorite or mark_unread):
        with get_db_session() as db:
            for arxiv_id in existing_ids:
                paper = db.query(Paper).filter_by(arxiv_id=arxiv_id).first()
                if paper and mark_favorite and not paper.is_favorite:
                    paper.is_favorite = True
                    paper.favorited_at = datetime.now(UTC)
                    logger.debug(f"Marked as favorite: {paper.title[:50]}...")

    # Step 4: Create ReadingProgress records if mark_unread
    if mark_unread:
        with get_db_session() as db:
            all_ids = list(existing_ids) + [p.arxiv_id for p in imported_papers]
            for arxiv_id in all_ids:
                # Check if ReadingProgress already exists
                existing_progress = db.query(ReadingProgress).filter_by(paper_id=arxiv_id).first()

                if not existing_progress:
                    progress = ReadingProgress(
                        paper_id=arxiv_id,
                        status="unread",
                    )
                    db.add(progress)
                    logger.debug(f"Created ReadingProgress for {arxiv_id}")

    # Step 5: Return all papers (new + existing)
    # Note: arXiv API returns IDs with version suffixes (e.g., "2501.12948v1")
    # but user may provide base IDs (e.g., "2501.12948"), so we need to handle both
    with get_db_session() as db:
        # Build a LIKE query for each arxiv_id to match with or without version suffix
        from sqlalchemy import or_

        filters = []
        for arxiv_id in arxiv_ids:
            # Match exact ID or ID with version suffix
            filters.append(Paper.arxiv_id == arxiv_id)
            filters.append(Paper.arxiv_id.like(f"{arxiv_id}v%"))

        all_papers = db.query(Paper).filter(or_(*filters)).all()

    logger.info(
        f"✅ Import complete! {len(imported_papers)} new papers, {len(existing_ids)} already existed"
    )
    return all_papers


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
