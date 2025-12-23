"""
Database connection and session management.

This module handles:
- Creating the database connection
- Managing database sessions
- Initializing the database schema

Key Concepts for SQLAlchemy:

1. Engine = The database connection pool
   - Creates connections to the database
   - Manages connection lifecycle
   - We create ONE engine for the whole app

2. Session = A workspace for database operations
   - Like a shopping cart - add changes, then commit them all at once
   - ALWAYS use in a context manager (with statement) to ensure cleanup
   - Create a NEW session for each request/operation

3. Transaction = A unit of work
   - All changes succeed together, or all fail together (atomicity)
   - Sessions handle this automatically with commit/rollback

Why this pattern?
- One engine = efficient connection pooling
- New session per operation = avoids conflicts
- Context manager = ensures cleanup even if errors happen
"""

from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from loguru import logger

from src.config import settings
from src.models.paper import Base


# ============================================================================
# Database Engine - Connection to the database
# ============================================================================

# Create the database engine
# This doesn't connect yet - it just sets up the connection pool
engine = create_engine(
    settings.database_url,
    # SQLite-specific settings for better performance
    connect_args=(
        {"check_same_thread": False}
        if settings.database_url.startswith("sqlite")
        else {}
    ),
    # Log all SQL queries (useful for debugging, disable in production)
    echo=settings.log_level == "DEBUG",
    # Connection pool settings
    pool_pre_ping=True,  # Check if connections are alive before using them
)


# SQLite-specific optimization: Enable foreign keys
# By default, SQLite doesn't enforce foreign key constraints
# We need to enable them for each connection
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """
    Enable foreign keys for SQLite connections.

    This is called automatically by SQLAlchemy whenever a new connection is created.
    It ensures that relationships between tables are enforced.

    Example:
    - If we try to create a Citation for a non-existent Paper, it will fail
    - If we delete a Paper, its Citations are automatically deleted (CASCADE)
    """
    if settings.database_url.startswith("sqlite"):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
        logger.debug("Enabled foreign key constraints for SQLite")


# ============================================================================
# Session Factory - Creates new database sessions
# ============================================================================

# SessionLocal is a factory that creates new Session objects
# Think of it like a session template - we call it to get a new session
SessionLocal = sessionmaker(
    bind=engine,  # Connect sessions to our engine
    autoflush=False,  # Don't automatically flush changes (we control when)
    autocommit=False,  # Don't automatically commit (we control when)
    expire_on_commit=False,  # Keep objects usable after commit
)


# ============================================================================
# Database Initialization
# ============================================================================


def init_db() -> None:
    """
    Initialize the database schema.

    This creates all tables defined in our models.

    How it works:
    1. Reads all model classes that inherit from Base
    2. Generates CREATE TABLE SQL for each one
    3. Creates indexes defined in the models
    4. Executes all SQL against the database

    Safe to call multiple times - won't recreate existing tables.

    Example:
        init_db()  # Creates papers, citations, social_signals, reading_progress tables
    """
    logger.info("Initializing database...")
    logger.info(f"Database URL: {settings.database_url}")

    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully!")

        # Log which tables were created
        table_names = Base.metadata.tables.keys()
        logger.info(f"Tables: {', '.join(table_names)}")

    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise


def drop_all_tables() -> None:
    """
    Drop all tables from the database.

    ⚠️  WARNING: This DELETES ALL DATA!

    Only use this for:
    - Development/testing
    - Resetting to a clean state
    - Fixing schema migration issues

    NEVER use in production!

    Example:
        drop_all_tables()  # 💥 All your data is gone!
        init_db()          # Start fresh
    """
    logger.warning("⚠️  Dropping all database tables...")
    try:
        Base.metadata.drop_all(bind=engine)
        logger.info("✅ All tables dropped")
    except Exception as e:
        logger.error(f"❌ Failed to drop tables: {e}")
        raise


# ============================================================================
# Session Management - Get database sessions
# ============================================================================


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.

    This is the CORRECT way to work with the database in this app.

    How to use:
        with get_db_session() as db:
            # Do database operations
            paper = db.query(Paper).filter_by(arxiv_id="2312.12345").first()
            print(paper.title)
            # Session is automatically closed when we exit the 'with' block

    What it does:
    1. Creates a new session
    2. Yields it to your code
    3. Commits changes if everything worked
    4. Rolls back changes if there was an error
    5. Always closes the session (cleanup)

    Why use a context manager?
    - Guarantees cleanup even if errors happen
    - Makes transaction boundaries clear
    - Prevents session leaks (memory leaks)

    Example - Reading data:
        with get_db_session() as db:
            papers = db.query(Paper).filter(Paper.relevance_score > 0.8).all()
            for paper in papers:
                print(paper.title)

    Example - Writing data:
        with get_db_session() as db:
            paper = Paper(
                arxiv_id="2312.12345",
                title="My Paper",
                abstract="This is cool",
                authors=["Alice", "Bob"],
                published_date=datetime.now(),
                categories=["cs.AI"],
                pdf_url="https://...",
                abstract_url="https://...",
                discovered_by="arxiv"
            )
            db.add(paper)
            db.commit()
            # Paper is now in the database!

    Example - Handling errors:
        with get_db_session() as db:
            try:
                paper = Paper(...)
                db.add(paper)
                db.commit()
            except IntegrityError:
                # Paper already exists (duplicate arxiv_id)
                logger.warning("Paper already in database")
                # Session is automatically rolled back

    """
    session = SessionLocal()
    try:
        yield session
        # If we get here without exceptions, commit the changes
        session.commit()
        logger.debug("Database session committed")
    except Exception as e:
        # If there was an error, undo all changes
        session.rollback()
        logger.error(f"Database session rolled back due to error: {e}")
        raise  # Re-raise the exception so caller knows it failed
    finally:
        # Always close the session to free resources
        session.close()
        logger.debug("Database session closed")


def get_db() -> Session:
    """
    Get a database session (without context manager).

    Use this when you need manual control over the session lifecycle.
    Most of the time, you should use get_db_session() instead.

    ⚠️  WARNING: You MUST close this session manually!

    Example:
        db = get_db()
        try:
            papers = db.query(Paper).all()
            db.commit()
        finally:
            db.close()  # Don't forget this!

    Better approach (use context manager):
        with get_db_session() as db:
            papers = db.query(Paper).all()
    """
    return SessionLocal()


# ============================================================================
# Helper Functions
# ============================================================================


def check_database_connection() -> bool:
    """
    Check if we can connect to the database.

    Returns:
        True if connection works, False otherwise

    Example:
        if not check_database_connection():
            print("Can't connect to database!")
            exit(1)
    """
    try:
        with get_db_session() as db:
            # Try a simple query
            db.execute(text("SELECT 1"))
        logger.info("✅ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


def get_database_stats() -> dict:
    """
    Get statistics about the database.

    Returns a dictionary with table counts.

    Example:
        stats = get_database_stats()
        print(f"Papers: {stats['papers']}")
        print(f"Citations: {stats['citations']}")
    """
    from src.models.paper import Paper, Citation, SocialSignal, ReadingProgress

    stats = {}

    try:
        with get_db_session() as db:
            stats["papers"] = db.query(Paper).count()
            stats["citations"] = db.query(Citation).count()
            stats["social_signals"] = db.query(SocialSignal).count()
            stats["reading_progress"] = db.query(ReadingProgress).count()

            # Additional useful stats
            stats["analyzed_papers"] = (
                db.query(Paper).filter(Paper.analyzed_at.isnot(None)).count()
            )
            stats["explained_papers"] = (
                db.query(Paper).filter(Paper.explained_at.isnot(None)).count()
            )
            stats["scored_papers"] = (
                db.query(Paper).filter(Paper.scored_at.isnot(None)).count()
            )

        logger.info(f"Database stats: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        return {}


if __name__ == "__main__":
    # Test database initialization
    print("Testing database setup...")

    # Initialize the database
    init_db()

    # Check connection
    if check_database_connection():
        print("✅ Database is ready!")

        # Show stats
        stats = get_database_stats()
        print(f"\nDatabase Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    else:
        print("❌ Database connection failed!")
