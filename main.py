#!/usr/bin/env python3
"""
Main CLI entry point for ArXiv Learning Assistant.

This is the command-line interface for the application.
It handles all user commands by calling LangGraph workflows.

Architecture:
- main.py = CLI layer (argument parsing, display)
- src/graph.py = Orchestration layer (LangGraph workflows)
- src/agents/* = Business logic layer (individual agents)

Example usage:
    python main.py --init-db                         # Initialize database
    python main.py --discover --days 1 --analyze     # Discover and analyze papers
    python main.py --list                            # List recent papers
    python main.py --stats                           # Show database statistics
"""

import argparse
import sys

from loguru import logger

from src.config import get_logs_dir, settings
from src.database import (
    check_database_connection,
    drop_all_tables,
    get_database_stats,
    get_db_session,
    init_db,
)
from src.graph import (
    run_analysis_pipeline,
    run_discovery_only_pipeline,
    run_full_pipeline,
)

# ============================================================================
# Logging Setup
# ============================================================================


def setup_logging():
    """
    Configure logging for the application.

    Loguru is a modern Python logging library with:
    - Colored output for readability
    - Automatic log rotation
    - Better formatting than stdlib logging
    - Easier to configure

    Logs go to:
    - Console (stdout) - for immediate feedback
    - File (logs/app.log) - for historical debugging
    """
    # Remove default handler
    logger.remove()

    # Add console handler with nice formatting
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=settings.log_level,
        colorize=True,
    )

    # Add file handler with rotation
    log_file = get_logs_dir() / "app.log"
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
        level=settings.log_level,
        rotation="10 MB",  # Rotate when file reaches 10MB
        retention="30 days",  # Keep logs for 30 days
        compression="zip",  # Compress old logs
    )

    logger.info("Logging initialized")


# ============================================================================
# Command Handlers
# ============================================================================


def handle_init_db(args):
    """
    Initialize the database schema.

    This creates all necessary tables. Safe to run multiple times.

    Example:
        python main.py --init-db
    """
    logger.info("Initializing database...")

    if args.reset:
        logger.warning("⚠️  Resetting database (all data will be lost)...")
        if args.yes or confirm_action("Are you sure you want to DELETE ALL DATA?"):
            drop_all_tables()
        else:
            logger.info("Cancelled")
            return

    init_db()

    if check_database_connection():
        stats = get_database_stats()
        logger.info("Database initialized successfully!")
        logger.info(f"Stats: {stats}")
    else:
        logger.error("Database connection failed!")
        sys.exit(1)


def handle_discover(args):
    """
    Discover new papers from arXiv.

    This always uses the LangGraph workflow for consistent execution.

    With --analyze: Run full pipeline (discovery + reader + explainer)
    Without --analyze: Run discovery only

    Example:
        python main.py --discover --days 1
        python main.py --discover --days 1 --analyze
    """
    logger.info(f"Discovering papers from the last {args.days} day(s)...")

    try:
        if args.analyze:
            # Use full LangGraph workflow (discovery + analysis + explanation)
            logger.info("Running full pipeline with LangGraph...")

            result = run_full_pipeline(
                days_back=args.days, max_papers=getattr(args, "max_papers", None)
            )

            # Show results
            stats = result.get("stats", {})
            logger.info("=" * 60)
            logger.info("PIPELINE RESULTS:")
            logger.info(f"  Discovered:    {stats.get('discovered_count', 0)} papers")
            logger.info(f"  Analyzed:      {stats.get('analyzed_count', 0)} papers")
            logger.info(f"  Explained:     {stats.get('explained_count', 0)} papers")
            logger.info(f"  HN signals:    {stats.get('hn_matched_count', 0)} matched")
            logger.info(f"  Twitter:       {stats.get('twitter_matched_count', 0)} matched")
            logger.info(f"  Breakthroughs: {stats.get('breakthrough_count', 0)} detected")
            logger.info(f"  Curated:       {stats.get('curated_count', 0)} ranked")
            logger.info("=" * 60)

            # Check for errors
            if result.get("errors"):
                logger.warning(f"Errors encountered: {result['errors']}")

        else:
            # Discovery only - uses LangGraph workflow for consistency
            result = run_discovery_only_pipeline(days_back=args.days)

            # Show results
            stats = result.get("stats", {})
            count = stats.get("discovered_count", 0)
            logger.info(f"✅ Discovered {count} papers")
            logger.info("Use --analyze flag to run full analysis pipeline")

            # Check for errors
            if result.get("errors"):
                logger.warning(f"Errors encountered: {result['errors']}")

    except Exception as e:
        logger.error(f"❌ Discovery failed: {e}")
        if settings.log_level == "DEBUG":
            logger.exception("Full traceback:")
        sys.exit(1)


def handle_analyze(args):
    """
    Analyze papers with Claude using LangGraph workflow.

    This runs the analysis workflow which:
    1. Loads unanalyzed papers from database
    2. Reader agent - Extract structured information
    3. Explainer agent - Generate learning-friendly explanations

    This command analyzes papers that are already in the database
    (discovered but not yet analyzed).

    Example:
        python main.py --analyze
    """
    logger.info("Analyzing unanalyzed papers with Claude...")

    try:
        # Use LangGraph workflow for analysis
        result = run_analysis_pipeline()

        # Show results
        stats = result.get("stats", {})
        logger.info("=" * 60)
        logger.info("ANALYSIS RESULTS:")
        logger.info(f"  Analyzed:  {stats.get('analyzed_count', 0)} papers")
        logger.info(f"  Explained: {stats.get('explained_count', 0)} papers")
        logger.info("=" * 60)

        # Check for errors
        if result.get("errors"):
            logger.warning(f"Errors encountered: {result['errors']}")

        # Helpful message if no papers found
        if stats.get("discovered_count", 0) == 0:
            logger.info("No unanalyzed papers found")
            logger.info("Run: python main.py --discover --days 1")

    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        if settings.log_level == "DEBUG":
            logger.exception("Full traceback:")
        sys.exit(1)


def handle_list(args):
    """
    List recent papers from the database.

    Shows the most recently discovered or analyzed papers
    to help understand what's currently in the system.

    Example:
        python main.py --list
        python main.py --list --limit 20
        python main.py --list --format json
    """
    logger.info("Listing recent papers...")

    if not check_database_connection():
        logger.error("Cannot connect to database!")
        sys.exit(1)

    # Get limit from args (default to 10)
    limit = getattr(args, "limit", 10)
    output_format = getattr(args, "format", "text")

    with get_db_session() as db:
        from src.models.paper import Paper

        papers = db.query(Paper).order_by(Paper.discovered_at.desc()).limit(limit).all()

        if not papers:
            if output_format == "json":
                import json

                print(json.dumps({"papers": [], "total": 0}, indent=2))
            else:
                print("\nNo papers found in database.")
                print("Run: python main.py --discover --days 1\n")
            return

        # JSON output
        if output_format == "json":
            import json

            papers_data = []
            for paper in papers:
                papers_data.append(
                    {
                        "arxiv_id": paper.arxiv_id,
                        "title": paper.title,
                        "published_date": paper.published_date.isoformat(),
                        "discovered_at": paper.discovered_at.isoformat(),
                        "analyzed": paper.analyzed_at is not None,
                        "analyzed_at": (
                            paper.analyzed_at.isoformat() if paper.analyzed_at else None
                        ),
                        "explained": paper.explained_at is not None,
                        "explained_at": (
                            paper.explained_at.isoformat() if paper.explained_at else None
                        ),
                        "relevance_score": paper.relevance_score,
                        "authors": paper.authors,
                        "categories": paper.categories,
                        "pdf_url": paper.pdf_url,
                    }
                )

            output = {"papers": papers_data, "total": db.query(Paper).count(), "limit": limit}
            print(json.dumps(output, indent=2))
            return

        # Text output
        print("\n" + "=" * 80)
        print(f"RECENT PAPERS (showing {len(papers)} of {db.query(Paper).count()} total)")
        print("=" * 80)

        for i, paper in enumerate(papers, 1):
            status = []
            if paper.analyzed_at:
                status.append("✓ Analyzed")
            if paper.explained_at:
                status.append("✓ Explained")
            if paper.scored_at:
                status.append(f"✓ Scored ({paper.relevance_score:.2f})")

            status_str = " | ".join(status) if status else "Not processed"

            print(f"\n{i}. {paper.title}")
            print(f"   ArXiv: {paper.arxiv_id} | Published: {paper.published_date.date()}")
            print(f"   Status: {status_str}")

        print("\n" + "=" * 80 + "\n")


def handle_show(args):
    """
    Show detailed view of a specific paper including analysis and explanation.

    Example:
        python main.py --show 2512.18878v1
        python main.py --show 2512.18878v1 --format json
    """
    arxiv_id = args.show
    output_format = getattr(args, "format", "text")

    logger.info(f"Fetching details for paper: {arxiv_id}")

    if not check_database_connection():
        logger.error("Cannot connect to database!")
        sys.exit(1)

    with get_db_session() as db:
        from src.models.paper import Paper

        paper = db.query(Paper).filter_by(arxiv_id=arxiv_id).first()

        if not paper:
            print(f"\nPaper not found: {arxiv_id}")
            print("Run: python main.py --list\n")
            sys.exit(1)

        # JSON output
        if output_format == "json":
            import json

            paper_data = {
                "arxiv_id": paper.arxiv_id,
                "title": paper.title,
                "abstract": paper.abstract,
                "authors": paper.authors,
                "published_date": paper.published_date.isoformat(),
                "categories": paper.categories,
                "pdf_url": paper.pdf_url,
                "abstract_url": paper.abstract_url,
                "discovered_at": paper.discovered_at.isoformat(),
                "analysis": (
                    {
                        "main_claim": paper.main_claim,
                        "methodology": paper.methodology,
                        "key_results": paper.key_results,
                        "novel_contributions": paper.novel_contributions,
                        "limitations": paper.limitations,
                        "concepts": paper.concepts,
                        "analyzed_at": (
                            paper.analyzed_at.isoformat() if paper.analyzed_at else None
                        ),
                    }
                    if paper.analyzed_at
                    else None
                ),
                "explanation": (
                    {
                        "eli5_summary": paper.eli5_summary,
                        "key_insight": paper.key_insight,
                        "learning_questions": paper.learning_questions,
                        "prerequisites": paper.prerequisites,
                        "related_concepts": paper.related_concepts,
                        "explained_at": (
                            paper.explained_at.isoformat() if paper.explained_at else None
                        ),
                    }
                    if paper.explained_at
                    else None
                ),
                "relevance_score": paper.relevance_score,
                "scored_at": paper.scored_at.isoformat() if paper.scored_at else None,
                "breakthrough_score": paper.breakthrough_score,
                "assessed_at": paper.assessed_at.isoformat() if paper.assessed_at else None,
            }

            print(json.dumps(paper_data, indent=2))
            return

        # Text output
        print("\n" + "=" * 100)
        print(f"PAPER DETAILS: {paper.arxiv_id}")
        print("=" * 100)

        print(f"\nTitle: {paper.title}")
        print(f"Authors: {paper.authors}")
        print(f"Published: {paper.published_date.date()}")
        print(f"Categories: {paper.categories}")
        print(f"PDF: {paper.pdf_url}")
        print(f"\nAbstract:\n{paper.abstract}")

        if paper.analyzed_at:
            print("\n" + "-" * 100)
            print("ANALYSIS (by Claude Haiku)")
            print("-" * 100)
            print(f"\nMain Claim:\n{paper.main_claim}")
            print(f"\nMethodology:\n{paper.methodology}")
            print(f"\nKey Results:\n{paper.key_results}")
            print(f"\nNovel Contributions:\n{paper.novel_contributions}")
            print(f"\nLimitations:\n{paper.limitations}")
            print(f"\nConcepts: {paper.concepts}")
            print(f"\nAnalyzed at: {paper.analyzed_at}")

        if paper.explained_at:
            print("\n" + "-" * 100)
            print("EXPLANATION (by Claude Sonnet)")
            print("-" * 100)
            print(f"\nELI5 Summary:\n{paper.eli5_summary}")
            print(f"\nKey Insight:\n{paper.key_insight}")
            print(f"\nLearning Questions:\n{paper.learning_questions}")
            print(f"\nPrerequisites: {paper.prerequisites}")
            print(f"\nRelated Concepts: {paper.related_concepts}")
            print(f"\nExplained at: {paper.explained_at}")

        if paper.breakthrough_score is not None or paper.relevance_score is not None:
            print("\n" + "-" * 100)
            print("SCORING")
            print("-" * 100)
            if paper.breakthrough_score is not None:
                print(
                    f"Breakthrough Score: {paper.breakthrough_score:.2f} (assessed at: {paper.assessed_at})"
                )
            if paper.relevance_score is not None:
                print(
                    f"Relevance Score:    {paper.relevance_score:.2f} (scored at: {paper.scored_at})"
                )

        print("\n" + "=" * 100 + "\n")


def handle_explore(args):
    """
    Launch interactive TUI for exploring papers.

    Navigate with arrow keys, press Enter to view details,
    and use keyboard shortcuts for actions.

    Example:
        python main.py --explore
    """
    logger.info("Launching paper explorer...")

    from src.tui import run_paper_explorer

    try:
        run_paper_explorer()
    except KeyboardInterrupt:
        logger.info("Explorer closed by user")
    except Exception as e:
        logger.error(f"Explorer failed: {e}")
        if settings.log_level == "DEBUG":
            logger.exception("Full traceback:")
        sys.exit(1)


def handle_stats(args):
    """
    Show database statistics.

    Example:
        python main.py --stats
    """
    logger.info("Fetching database statistics...")

    if not check_database_connection():
        logger.error("Cannot connect to database!")
        sys.exit(1)

    stats = get_database_stats()

    print("\n" + "=" * 50)
    print("DATABASE STATISTICS")
    print("=" * 50)
    print(f"Total Papers:        {stats.get('papers', 0)}")
    print(f"Analyzed Papers:     {stats.get('analyzed_papers', 0)}")
    print(f"Explained Papers:    {stats.get('explained_papers', 0)}")
    print(f"Scored Papers:       {stats.get('scored_papers', 0)}")
    print(f"Citations:           {stats.get('citations', 0)}")
    print(f"Social Signals:      {stats.get('social_signals', 0)}")
    print(f"Reading Progress:    {stats.get('reading_progress', 0)}")
    print("=" * 50 + "\n")


# ============================================================================
# Radar Command Handlers
# ============================================================================


def handle_radar(args):
    """
    Start the Research Radar daemon.

    Runs continuously in the foreground, scanning for noteworthy papers
    and sending email notifications when found.

    Example:
        python main.py --radar
    """
    from src.radar import run_radar

    logger.info("Starting Research Radar daemon...")
    run_radar()


def handle_radar_once(args):
    """
    Run a single radar scan (for testing).

    Example:
        python main.py --radar-once
    """
    from src.radar import run_radar_once

    logger.info("Running single radar scan...")
    results = run_radar_once()

    logger.info("=" * 60)
    logger.info("RADAR SCAN RESULTS:")
    logger.info(f"  New papers:        {results.get('new_papers', 0)}")
    logger.info(f"  Rising papers:     {results.get('rising_papers', 0)}")
    logger.info(f"  Noteworthy:        {results.get('noteworthy_papers', 0)}")
    logger.info(f"  Notifications:     {results.get('notifications_sent', 0)}")
    logger.info("=" * 60)

    if results.get("errors"):
        logger.warning(f"Errors: {results['errors']}")


def handle_digest(args):
    """
    Send an email digest of top unread papers.

    This command surfaces the best papers from your database:
    1. Your seed papers (favorites) - always included if unread
    2. Top unread papers by relevance score
    3. Recently hot papers (high social engagement)

    Examples:
        python main.py --digest              # Send digest email
        python main.py --digest --preview    # Preview without sending
        python main.py --digest --top 10     # Include top 10 papers
    """
    from src.agents.curator import get_unread_favorites
    from src.database import get_db_session
    from src.models.paper import Paper, ReadingProgress
    from src.services.email_notifier import EmailNotifier

    preview = getattr(args, "preview", False)
    top_n = getattr(args, "top", 5)

    logger.info("Building email digest...")

    # 1. Get unread seed papers (favorites)
    seed_papers = get_unread_favorites()
    seed_ids = {p.arxiv_id for p in seed_papers}
    logger.info(f"Found {len(seed_papers)} unread seed papers")

    # 2. Get top unread papers by relevance score (excluding seeds)
    with get_db_session() as db:
        # Get papers that are either:
        # - Not in ReadingProgress (never seen)
        # - In ReadingProgress with status='unread'
        all_papers = (
            db.query(Paper)
            .filter(
                Paper.relevance_score.isnot(None),
                Paper.arxiv_id.notin_(seed_ids),  # Exclude seeds
            )
            .order_by(Paper.relevance_score.desc())
            .limit(top_n * 3)  # Get more than needed to filter
            .all()
        )

        # Filter to unread only
        top_papers = []
        for paper in all_papers:
            progress = db.query(ReadingProgress).filter_by(paper_id=paper.arxiv_id).first()
            if not progress or progress.status == "unread":
                top_papers.append(paper)
                if len(top_papers) >= top_n:
                    break

    logger.info(f"Found {len(top_papers)} top unread papers")

    # 3. Preview or send
    if preview:
        print("\n" + "=" * 60)
        print("📧 DIGEST PREVIEW")
        print("=" * 60)

        if seed_papers:
            print("\n📌 YOUR SEED PAPERS:")
            print("-" * 40)
            for p in seed_papers:
                score = f"{p.relevance_score:.0%}" if p.relevance_score else "N/A"
                bt = f"{p.breakthrough_score:.0%}" if p.breakthrough_score else "N/A"
                print(f"  • {p.title[:60]}...")
                print(f"    Score: {score} | Breakthrough: {bt}")
                print()

        if top_papers:
            print("\n🔍 TOP UNREAD PAPERS:")
            print("-" * 40)
            for i, p in enumerate(top_papers, 1):
                score = f"{p.relevance_score:.0%}" if p.relevance_score else "N/A"
                bt = f"{p.breakthrough_score:.0%}" if p.breakthrough_score else "N/A"
                print(f"  {i}. {p.title[:60]}...")
                print(f"     Score: {score} | Breakthrough: {bt}")
                print()

        total = len(seed_papers) + len(top_papers)
        print(f"Total: {total} papers would be sent")
        print("=" * 60)
        print("Run without --preview to send email")

    else:
        # Send the digest
        notifier = EmailNotifier()
        if not notifier.is_configured():
            logger.error("Email not configured. Check SMTP settings in .env")
            sys.exit(1)

        # send_paper_alert now handles seed papers automatically
        success = notifier.send_paper_alert(
            papers=top_papers,
            reason="digest",
            include_seed_papers=True,
        )

        if success:
            total = len(seed_papers) + len(top_papers)
            logger.info(
                f"✅ Digest sent! {total} papers ({len(seed_papers)} seed, {len(top_papers)} top)"
            )
        else:
            logger.error("❌ Failed to send digest")
            sys.exit(1)


def handle_test_email(args):
    """
    Test email configuration by sending a test message.

    Example:
        python main.py --test-email
    """
    from src.services.email_notifier import test_email_connection

    logger.info("Testing email configuration...")
    if test_email_connection():
        logger.info("Email test successful! Check your inbox.")
    else:
        logger.error("Email test failed. Check your SMTP settings in .env")
        sys.exit(1)


def handle_feedback_server(args):
    """
    Start the feedback server for collecting email feedback.

    Example:
        python main.py --feedback-server
    """
    from src.services.feedback_server import run_feedback_server

    port = getattr(args, "feedback_port", None)
    run_feedback_server(port=port)


# ============================================================================
# Favorites/Personalization Command Handlers
# ============================================================================


def handle_like(args):
    """
    Mark a paper as a favorite/seed paper for personalization.

    Example:
        python main.py --like 2312.12345
    """
    from datetime import UTC, datetime

    from src.models.paper import Paper

    arxiv_id = args.like
    logger.info(f"Marking paper as favorite: {arxiv_id}")

    if not check_database_connection():
        logger.error("Cannot connect to database!")
        sys.exit(1)

    with get_db_session() as db:
        paper = db.query(Paper).filter_by(arxiv_id=arxiv_id).first()

        if not paper:
            logger.error(f"Paper not found: {arxiv_id}")
            logger.info("Use --list to see available papers, or --discover to find new ones")
            sys.exit(1)

        if paper.is_favorite:
            logger.info(f"Paper is already a favorite: {paper.title}")
            return

        paper.is_favorite = True
        paper.favorited_at = datetime.now(UTC)

    logger.info(f"Marked as favorite: {paper.title[:60]}...")
    print(f"\n⭐ Added to favorites: {paper.title}")
    print(f"   ArXiv ID: {arxiv_id}")
    print("   Use --favorites to see all your seed papers\n")


def handle_unlike(args):
    """
    Remove a paper from favorites.

    Example:
        python main.py --unlike 2312.12345
    """
    from src.models.paper import Paper

    arxiv_id = args.unlike
    logger.info(f"Removing paper from favorites: {arxiv_id}")

    if not check_database_connection():
        logger.error("Cannot connect to database!")
        sys.exit(1)

    with get_db_session() as db:
        paper = db.query(Paper).filter_by(arxiv_id=arxiv_id).first()

        if not paper:
            logger.error(f"Paper not found: {arxiv_id}")
            sys.exit(1)

        if not paper.is_favorite:
            logger.info(f"Paper is not a favorite: {paper.title}")
            return

        paper.is_favorite = False
        paper.favorited_at = None

    logger.info(f"Removed from favorites: {paper.title[:60]}...")
    print(f"\n✓ Removed from favorites: {paper.title}\n")


def handle_favorites(args):
    """
    List all favorite/seed papers.

    Example:
        python main.py --favorites
    """
    from src.models.paper import Paper

    logger.info("Listing favorite papers...")

    if not check_database_connection():
        logger.error("Cannot connect to database!")
        sys.exit(1)

    with get_db_session() as db:
        favorites = (
            db.query(Paper).filter_by(is_favorite=True).order_by(Paper.favorited_at.desc()).all()
        )

        if not favorites:
            print("\n⭐ No favorite papers yet.")
            print("Use --like <arxiv_id> to mark papers you like")
            print("These seed papers will help personalize recommendations\n")
            return

        print("\n" + "=" * 80)
        print(f"⭐ FAVORITE PAPERS ({len(favorites)} total)")
        print("=" * 80)

        for i, paper in enumerate(favorites, 1):
            favorited_date = paper.favorited_at.strftime("%Y-%m-%d") if paper.favorited_at else "?"
            print(f"\n{i}. {paper.title}")
            print(f"   ArXiv: {paper.arxiv_id} | Favorited: {favorited_date}")
            if paper.categories:
                print(f"   Categories: {', '.join(paper.categories[:3])}")

        print("\n" + "=" * 80)
        print("These papers help personalize your recommendations.")
        print("Use --unlike <arxiv_id> to remove a paper from favorites.\n")


def handle_discover_hn(args):
    """
    Discover papers trending on HackerNews.

    This is a "social-first" discovery approach - finds papers that
    the tech community is actively discussing.

    Example:
        python main.py --discover-hn
        python main.py --discover-hn --days 14 --min-hn-score 50
    """
    from src.agents.discovery import discover_papers_from_hn

    days_back = args.days
    min_score = args.min_hn_score

    logger.info(f"Discovering papers from HackerNews (days={days_back}, min_score={min_score})...")

    try:
        papers = discover_papers_from_hn(days_back=days_back, min_score=min_score)

        if not papers:
            logger.warning("No papers found from HackerNews")
            return

        # Display results
        print("\n" + "=" * 80)
        print(f"HACKERNEWS DISCOVERY RESULTS ({len(papers)} papers)")
        print("=" * 80)

        for i, paper in enumerate(papers, 1):
            hn_score = paper.score_components.get("hn_score", 0) if paper.score_components else 0
            hn_comments = (
                paper.score_components.get("hn_comments", 0) if paper.score_components else 0
            )

            print(f"\n{i}. {paper.title[:70]}...")
            print(f"   ArXiv: {paper.arxiv_id} | HN: {hn_score} pts, {hn_comments} comments")

        print("\n" + "=" * 80)
        logger.info(f"✅ Discovered {len(papers)} papers from HackerNews")

    except Exception as e:
        logger.error(f"❌ HN Discovery failed: {e}")
        if settings.log_level == "DEBUG":
            logger.exception("Full traceback:")
        sys.exit(1)


def handle_import(args):
    """
    Import specific papers by arXiv ID.

    This allows you to manually add papers you know you want to read.
    You can mark them as favorites and/or unread.

    Example:
        python main.py --import 2501.12948 2412.19437 --favorite --unread
        python main.py --import 2501.12948 --favorite
    """
    from src.agents.discovery import import_papers_by_ids

    arxiv_ids = args.import_ids
    mark_favorite = args.favorite
    mark_unread = args.unread

    logger.info(f"Importing {len(arxiv_ids)} papers by ID...")

    if not check_database_connection():
        logger.error("Cannot connect to database!")
        sys.exit(1)

    try:
        papers = import_papers_by_ids(
            arxiv_ids=arxiv_ids,
            mark_favorite=mark_favorite,
            mark_unread=mark_unread,
        )

        if not papers:
            logger.warning("No papers were imported")
            return

        # Display results
        print("\n" + "=" * 80)
        print(f"IMPORT RESULTS ({len(papers)} papers)")
        print("=" * 80)

        for i, paper in enumerate(papers, 1):
            status = []
            if paper.is_favorite:
                status.append("⭐ Favorite")
            if mark_unread:
                status.append("📖 Unread")

            status_str = " | ".join(status) if status else ""

            print(f"\n{i}. {paper.title[:70]}...")
            print(f"   ArXiv: {paper.arxiv_id}")
            if status_str:
                print(f"   Status: {status_str}")

        print("\n" + "=" * 80)
        logger.info(f"✅ Imported {len(papers)} papers")

        # If user wants to analyze them, suggest the command
        if args.analyze:
            logger.info("Running analysis on imported papers...")
            # Re-use the handle_analyze logic but only for these papers
            from src.graph import run_analysis_pipeline

            result = run_analysis_pipeline()
            stats = result.get("stats", {})
            logger.info(f"✅ Analyzed {stats.get('analyzed_count', 0)} papers")
        else:
            print("\nUse --analyze flag to analyze these papers immediately")
            print("Or run: python main.py --analyze\n")

    except Exception as e:
        logger.error(f"❌ Import failed: {e}")
        if settings.log_level == "DEBUG":
            logger.exception("Full traceback:")
        sys.exit(1)


# ============================================================================
# Utilities
# ============================================================================


def confirm_action(message: str) -> bool:
    """
    Ask user for confirmation.

    Args:
        message: The question to ask

    Returns:
        True if user confirmed, False otherwise

    Example:
        if confirm_action("Delete all data?"):
            drop_all_tables()
    """
    response = input(f"{message} [y/N]: ").strip().lower()
    return response in ("y", "yes")


# ============================================================================
# Main CLI
# ============================================================================


def main():
    """
    Main entry point for the CLI.

    Parses command-line arguments and dispatches to the appropriate handler.
    """
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="ArXiv Learning Assistant - Your AI research companion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # First-time setup
  python main.py --init-db

  # Core workflow - discover and analyze papers
  python main.py --discover --days 1 --analyze --max-papers 5

  # Just discover (don't analyze yet)
  python main.py --discover --days 3

  # Analyze previously discovered papers
  python main.py --analyze

  # View current state
  python main.py --stats                           # Database statistics
  python main.py --list                            # Recent papers (default: 10)
  python main.py --list --limit 20                 # Show 20 recent papers
  python main.py --show 2512.18878v1               # View detailed analysis of a paper

  # Interactive exploration (recommended!)
  python main.py --explore                         # Browse papers interactively with arrow keys

  # Export data as JSON
  python main.py --list --format json              # Export list as JSON
  python main.py --show 2512.18878v1 --format json # Export paper details as JSON

  # Personalization - mark favorite papers as seeds
  python main.py --like 2312.12345                 # Mark paper as favorite
  python main.py --unlike 2312.12345               # Remove from favorites
  python main.py --favorites                       # List all favorite papers

  # Reset everything
  python main.py --init-db --reset --yes

  # Social-first discovery (papers trending on HackerNews)
  python main.py --discover-hn                        # Discover papers from HN (default: 7 days, min 10 pts)
  python main.py --discover-hn --days 14 --min-hn-score 50  # More days, higher threshold
        """,
    )

    # ==================== SETUP COMMANDS ====================
    setup_group = parser.add_argument_group("Setup", "Database initialization and management")
    setup_group.add_argument(
        "--init-db", action="store_true", help="Initialize or update database schema"
    )
    setup_group.add_argument(
        "--reset", action="store_true", help="Reset database (WARNING: deletes all data)"
    )
    setup_group.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompts")

    # ==================== PIPELINE COMMANDS ====================
    pipeline_group = parser.add_argument_group("Pipeline", "Run discovery and analysis workflows")
    pipeline_group.add_argument(
        "--discover", action="store_true", help="Discover new papers from arXiv"
    )
    pipeline_group.add_argument(
        "--analyze", action="store_true", help="Analyze papers with Claude AI"
    )

    # ==================== PIPELINE PARAMETERS ====================
    params_group = parser.add_argument_group("Parameters", "Control pipeline behavior")
    params_group.add_argument(
        "--days", type=int, default=1, help="How many days back to search (default: 1)"
    )
    params_group.add_argument(
        "--max-papers",
        type=int,
        default=None,
        help="Maximum papers to process per run (useful for testing)",
    )

    # ==================== REPORTING COMMANDS ====================
    report_group = parser.add_argument_group("Reporting", "View current state and statistics")
    report_group.add_argument("--stats", action="store_true", help="Show database statistics")
    report_group.add_argument(
        "--list", action="store_true", help="List recent papers from database"
    )
    report_group.add_argument(
        "--show", type=str, metavar="ARXIV_ID", help="Show detailed view of a specific paper"
    )
    report_group.add_argument(
        "--explore",
        action="store_true",
        help="Launch interactive TUI for browsing papers (arrow keys, Enter to view)",
    )
    report_group.add_argument(
        "--limit", type=int, default=10, help="Number of papers to show with --list (default: 10)"
    )
    report_group.add_argument(
        "--format",
        type=str,
        choices=["text", "json"],
        default="text",
        help="Output format for --list, --stats, or --show (default: text)",
    )

    # ==================== RADAR COMMANDS ====================
    radar_group = parser.add_argument_group(
        "Research Radar", "Background monitoring and notifications"
    )
    radar_group.add_argument(
        "--radar",
        action="store_true",
        help="Start the Research Radar daemon (runs in foreground)",
    )
    radar_group.add_argument(
        "--radar-once",
        action="store_true",
        help="Run a single radar scan (for testing)",
    )
    radar_group.add_argument(
        "--digest",
        action="store_true",
        help="Send email digest of top unread papers from database",
    )
    radar_group.add_argument(
        "--preview",
        action="store_true",
        help="Preview digest without sending email (use with --digest)",
    )
    radar_group.add_argument(
        "--top",
        type=int,
        default=5,
        metavar="N",
        help="Number of top papers to include in digest (default: 5)",
    )
    radar_group.add_argument(
        "--test-email",
        action="store_true",
        help="Test email configuration",
    )
    radar_group.add_argument(
        "--feedback-server",
        action="store_true",
        help="Start the feedback server for collecting email ratings",
    )
    radar_group.add_argument(
        "--feedback-port",
        type=int,
        default=None,
        help="Port for feedback server (default: 8080)",
    )

    # ==================== PERSONALIZATION COMMANDS ====================
    pref_group = parser.add_argument_group(
        "Personalization", "Mark favorite papers as seeds for recommendations"
    )
    pref_group.add_argument(
        "--like",
        type=str,
        metavar="ARXIV_ID",
        help="Mark a paper as a favorite/seed paper for personalization",
    )
    pref_group.add_argument(
        "--unlike",
        type=str,
        metavar="ARXIV_ID",
        help="Remove a paper from favorites",
    )
    pref_group.add_argument(
        "--favorites",
        action="store_true",
        help="List all favorite/seed papers",
    )

    # ==================== SOCIAL DISCOVERY ====================
    social_group = parser.add_argument_group(
        "Social Discovery", "Discover papers from social platforms"
    )
    social_group.add_argument(
        "--discover-hn",
        action="store_true",
        help="Discover papers trending on HackerNews",
    )
    social_group.add_argument(
        "--min-hn-score",
        type=int,
        default=10,
        help="Minimum HN score for --discover-hn (default: 10)",
    )

    # ==================== MANUAL IMPORT ====================
    import_group = parser.add_argument_group("Manual Import", "Import specific papers by arXiv ID")
    import_group.add_argument(
        "--import",
        dest="import_ids",
        type=str,
        nargs="+",
        metavar="ARXIV_ID",
        help="Import specific papers by arXiv ID (e.g., --import 2501.12948 2412.19437)",
    )
    import_group.add_argument(
        "--favorite",
        action="store_true",
        help="Mark imported papers as favorites (use with --import)",
    )
    import_group.add_argument(
        "--unread",
        action="store_true",
        help="Mark imported papers as unread (use with --import)",
    )

    # ==================== OTHER OPTIONS ====================
    other_group = parser.add_argument_group("Other")
    other_group.add_argument("--debug", action="store_true", help="Enable debug logging")

    # Parse arguments
    args = parser.parse_args()

    # Override log level if --debug is set
    if args.debug:
        settings.log_level = "DEBUG"

    # Setup logging
    setup_logging()

    logger.info("ArXiv Learning Assistant starting...")
    logger.debug(f"Command-line args: {args}")

    # Dispatch to appropriate handler
    try:
        if args.init_db:
            handle_init_db(args)
        elif args.discover:
            handle_discover(args)
        elif args.analyze:
            handle_analyze(args)
        elif args.show:
            handle_show(args)
        elif args.explore:
            handle_explore(args)
        elif args.list:
            handle_list(args)
        elif args.stats:
            handle_stats(args)
        elif args.radar:
            handle_radar(args)
        elif args.radar_once:
            handle_radar_once(args)
        elif args.digest:
            handle_digest(args)
        elif args.test_email:
            handle_test_email(args)
        elif args.like:
            handle_like(args)
        elif args.unlike:
            handle_unlike(args)
        elif args.favorites:
            handle_favorites(args)
        elif args.feedback_server:
            handle_feedback_server(args)
        elif args.discover_hn:
            handle_discover_hn(args)
        elif args.import_ids:
            handle_import(args)
        else:
            # No command specified, show help
            parser.print_help()
            sys.exit(0)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if settings.log_level == "DEBUG":
            logger.exception("Full traceback:")
        sys.exit(1)

    logger.info("Done!")


if __name__ == "__main__":
    main()
