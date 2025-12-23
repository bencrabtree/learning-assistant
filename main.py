#!/usr/bin/env python3
"""
Main CLI entry point for ArXiv Learning Assistant.

This is the command-line interface for the application.
It handles all user commands and orchestrates the agents.

Example usage:
    python main.py --init-db                    # Initialize database
    python main.py --discover --days 1          # Find papers from last day
    python main.py --digest                     # Generate and send email digest
    python main.py --stats                      # Show database statistics
"""

import argparse
import sys
from loguru import logger

from src.config import settings, get_logs_dir
from src.database import (
    init_db,
    check_database_connection,
    get_database_stats,
    drop_all_tables,
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

    This will:
    1. Query arXiv API for recent papers
    2. Save them to the database
    3. Optionally trigger analysis with LangGraph workflow

    Example:
        python main.py --discover --days 1
        python main.py --discover --days 1 --analyze
    """
    logger.info(f"Discovering papers from the last {args.days} day(s)...")

    try:
        if args.analyze:
            # Use full LangGraph workflow (discovery + analysis + explanation)
            logger.info("Running full pipeline with LangGraph...")
            from src.graph import run_full_pipeline

            result = run_full_pipeline(
                days_back=args.days,
                max_papers=getattr(args, 'max_papers', None)
            )

            # Show results
            stats = result.get("stats", {})
            logger.info("=" * 60)
            logger.info("PIPELINE RESULTS:")
            logger.info(f"  Discovered: {stats.get('discovered_count', 0)} papers")
            logger.info(f"  Analyzed:   {stats.get('analyzed_count', 0)} papers")
            logger.info(f"  Explained:  {stats.get('explained_count', 0)} papers")
            logger.info("=" * 60)

            # Check for errors
            if result.get("errors"):
                logger.warning(f"Errors encountered: {result['errors']}")

        else:
            # Just discovery (no analysis)
            from src.agents.discovery import discover_papers

            papers = discover_papers(days_back=args.days)
            logger.info(f"✅ Discovered {len(papers)} papers")
            logger.info("Use --analyze flag to run analysis pipeline")

    except Exception as e:
        logger.error(f"❌ Discovery failed: {e}")
        if settings.log_level == "DEBUG":
            logger.exception("Full traceback:")
        sys.exit(1)


def handle_analyze(args):
    """
    Analyze papers with Claude.

    This runs:
    1. Reader agent - Extract structured information
    2. Explainer agent - Generate learning-friendly explanations

    This command analyzes papers that are already in the database
    (discovered but not yet analyzed).

    Example:
        python main.py --analyze
    """
    logger.info("Analyzing unanalyzed papers with Claude...")

    from src.models.paper import Paper
    from src.database import get_db_session
    from src.agents.reader import ReaderAgent
    from src.agents.explainer import ExplainerAgent

    try:
        # Find papers that haven't been analyzed
        with get_db_session() as db:
            unanalyzed = db.query(Paper).filter(Paper.analyzed_at.is_(None)).all()

        if not unanalyzed:
            logger.info("No unanalyzed papers found")
            logger.info("Run: python main.py --discover --days 1")
            return

        logger.info(f"Found {len(unanalyzed)} papers to analyze")

        # Step 1: Analyze with Reader agent
        logger.info("Step 1/2: Running Reader agent...")
        reader = ReaderAgent()
        reader_count = reader.analyze_and_save(unanalyzed)

        # Step 2: Explain with Explainer agent
        logger.info("Step 2/2: Running Explainer agent...")
        with get_db_session() as db:
            analyzed = db.query(Paper).filter(
                Paper.analyzed_at.isnot(None),
                Paper.explained_at.is_(None)
            ).all()

        explainer = ExplainerAgent()
        explainer_count = explainer.explain_and_save(analyzed)

        # Show results
        logger.info("=" * 60)
        logger.info("ANALYSIS RESULTS:")
        logger.info(f"  Analyzed:  {reader_count} papers")
        logger.info(f"  Explained: {explainer_count} papers")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        if settings.log_level == "DEBUG":
            logger.exception("Full traceback:")
        sys.exit(1)


def handle_digest(args):
    """
    Generate and send email digest.

    This will:
    1. Load papers from database
    2. Score them for relevance
    3. Select top N papers
    4. Generate HTML email
    5. Send via SMTP

    Example:
        python main.py --digest
    """
    logger.info("Generating email digest...")

    # TODO: Implement digest pipeline
    # This will be built in Week 1, Day 4-5
    logger.warning("Digest not yet implemented (coming in Day 4)")


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
    return response in ('y', 'yes')


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

  # Daily workflow
  python main.py --discover --days 1 --analyze
  python main.py --digest

  # Check status
  python main.py --stats

  # Reset everything
  python main.py --init-db --reset
        """
    )

    # Database commands
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Initialize database schema"
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset database (WARNING: deletes all data)"
    )

    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompts"
    )

    # Discovery commands
    parser.add_argument(
        "--discover",
        action="store_true",
        help="Discover new papers from arXiv"
    )

    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="How many days back to search (default: 1)"
    )

    parser.add_argument(
        "--max-papers",
        type=int,
        default=None,
        help="Maximum number of papers to process (for testing)"
    )

    # Analysis commands
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Analyze papers with Claude"
    )

    # Digest commands
    parser.add_argument(
        "--digest",
        action="store_true",
        help="Generate and send email digest"
    )

    # Stats commands
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show database statistics"
    )

    # Logging
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

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
        elif args.digest:
            handle_digest(args)
        elif args.stats:
            handle_stats(args)
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
