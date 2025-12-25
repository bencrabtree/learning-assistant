"""
Database models for papers and related entities.

This file defines our data schema using SQLAlchemy ORM (Object-Relational Mapping).

Key Concepts:
- ORM = Object-Relational Mapping: Write Python classes instead of SQL
- Each class = a database table
- Each instance = a row in that table
- SQLAlchemy handles all the SQL for us

Why ORM?
- Type safety (Python catches errors before they hit the database)
- Easier to work with (Python objects instead of raw SQL)
- Database-agnostic (can switch from SQLite to Postgres easily)
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# ============================================================================
# Base class for all models
# ============================================================================


class Base(DeclarativeBase):
    """
    Base class for all database models.

    SQLAlchemy will use this to set up the database mapping.
    All our models will inherit from this.
    """

    pass


# ============================================================================
# Paper Model - The core entity
# ============================================================================


class Paper(Base):
    """
    Represents a research paper from arXiv.

    This is the central entity in our system. Everything else relates to papers.

    Table Structure:
    - Primary data: arxiv_id, title, abstract, authors, etc.
    - Analysis data: What the Reader agent extracts
    - Explanation data: What the Explainer agent generates
    - Scoring data: How relevant this paper is to the user
    """

    __tablename__ = "papers"

    # ------------------------------------------------------------------------
    # Primary Key
    # ------------------------------------------------------------------------
    # Every table needs a unique identifier. We use arxiv_id (like "2312.12345")
    # because it's already unique and meaningful.

    arxiv_id: Mapped[str] = mapped_column(String(20), primary_key=True)

    # ------------------------------------------------------------------------
    # Core Metadata - From arXiv API
    # ------------------------------------------------------------------------

    title: Mapped[str] = mapped_column(Text, nullable=False)
    abstract: Mapped[str] = mapped_column(Text, nullable=False)

    # JSON field to store list of author names
    # Example: ["John Doe", "Jane Smith", "Bob Johnson"]
    authors: Mapped[list[str]] = mapped_column(JSON, nullable=False)

    # When the paper was published on arXiv
    published_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # ArXiv categories, e.g., ["cs.AI", "cs.LG"]
    categories: Mapped[list[str]] = mapped_column(JSON, nullable=False)

    # URLs to the paper
    pdf_url: Mapped[str] = mapped_column(String(200), nullable=False)
    abstract_url: Mapped[str] = mapped_column(String(200), nullable=False)

    # Tracking: when and how we discovered this paper
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Which source found it: "arxiv", "twitter", "hackernews", etc.
    discovered_by: Mapped[str] = mapped_column(String(50), nullable=False)

    # Optional: which AI lab published this (if any)
    # Example: "OpenAI", "Google DeepMind", "Anthropic"
    lab_published_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ------------------------------------------------------------------------
    # Analysis Fields - Populated by Reader Agent
    # ------------------------------------------------------------------------
    # These are filled in after we analyze the paper with Claude

    # What's the main claim or contribution?
    main_claim: Mapped[str | None] = mapped_column(Text, nullable=True)

    # What methods did they use?
    methodology: Mapped[str | None] = mapped_column(Text, nullable=True)

    # List of key results as strings
    key_results: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # What's novel about this work?
    novel_contributions: Mapped[str | None] = mapped_column(Text, nullable=True)

    # What are the limitations?
    limitations: Mapped[str | None] = mapped_column(Text, nullable=True)

    # List of technical concepts mentioned
    # Example: ["transformer architecture", "attention mechanism", "BERT"]
    concepts: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # When the analysis was done
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ------------------------------------------------------------------------
    # Explanation Fields - Populated by Explainer Agent
    # ------------------------------------------------------------------------
    # These make the paper accessible to learners

    # ELI5 (Explain Like I'm 5) summary for non-experts
    eli5_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # The one key insight to remember
    key_insight: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Questions to think about while reading
    # Example: ["How does this compare to GPT-4?", "Why use this architecture?"]
    learning_questions: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # What you should understand first
    # Example: ["attention mechanism", "transformer architecture"]
    prerequisites: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # Related concepts for further learning
    related_concepts: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # When the explanation was generated
    explained_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ------------------------------------------------------------------------
    # Citation Data - From Semantic Scholar API
    # ------------------------------------------------------------------------
    # Quick-access fields for latest citation metrics
    # (Historical data stored in Citation table for velocity calculations)

    # Total citation count (from Semantic Scholar)
    citation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Number of highly influential citations
    # (Semantic Scholar's proprietary metric for citation quality)
    influential_citation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # When we last fetched citation data
    citations_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ------------------------------------------------------------------------
    # Scoring Fields - Populated by Curator Agent
    # ------------------------------------------------------------------------
    # How relevant is this paper to the user?

    # Overall relevance score (0-1, higher = more relevant)
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Breakdown of score components (for debugging and transparency)
    # Example: {"interest_match": 0.85, "social_proof": 0.6, "citation_velocity": 0.3}
    score_components: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # When the score was calculated
    scored_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ------------------------------------------------------------------------
    # Relationships - Links to other tables
    # ------------------------------------------------------------------------
    # SQLAlchemy relationships let us easily access related data
    # Example: paper.citations will give us all Citation objects for this paper

    citations: Mapped[list["Citation"]] = relationship(
        "Citation",
        back_populates="paper",
        cascade="all, delete-orphan",  # If we delete a paper, delete its citations too
    )

    social_signals: Mapped[list["SocialSignal"]] = relationship(
        "SocialSignal", back_populates="paper", cascade="all, delete-orphan"
    )

    reading_progress: Mapped[Optional["ReadingProgress"]] = relationship(
        "ReadingProgress",
        back_populates="paper",
        uselist=False,  # One-to-one relationship
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """String representation for debugging"""
        return f"<Paper {self.arxiv_id}: {self.title[:50]}...>"


# Create indexes for common queries to speed up database lookups
# Indexes are like a book's index - they help find things faster
Index("idx_published_date", Paper.published_date)
Index("idx_relevance_score", Paper.relevance_score)
Index("idx_discovered_at", Paper.discovered_at)


# ============================================================================
# Citation Model - Track citation counts over time
# ============================================================================


class Citation(Base):
    """
    Citation metrics for a paper, tracked over time.

    We store multiple snapshots to calculate citation velocity
    (how fast the paper is gaining citations).

    Example:
    - Day 1: 10 citations
    - Day 7: 25 citations → velocity = 15 citations/week (trending!)
    """

    __tablename__ = "citations"

    # Primary key (auto-incrementing integer)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to papers table
    # This links each citation record to a specific paper
    paper_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey(
            "papers.arxiv_id", ondelete="CASCADE"
        ),  # If paper is deleted, delete citations too
        nullable=False,
    )

    # Citation metrics
    citation_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # When we measured this count
    measured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Derived metrics (calculated from historical data)
    citations_this_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    velocity_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Where we got this data from
    source: Mapped[str] = mapped_column(String(50), default="semantic_scholar", nullable=False)

    # Relationship back to the paper
    paper: Mapped["Paper"] = relationship("Paper", back_populates="citations")

    def __repr__(self) -> str:
        return f"<Citation {self.paper_id}: {self.citation_count} citations>"


# Index for looking up latest citation count for a paper
Index("idx_citation_paper_measured", Citation.paper_id, Citation.measured_at)


# ============================================================================
# SocialSignal Model - Twitter, HN, Reddit mentions
# ============================================================================


class SocialSignal(Base):
    """
    Social media signals about a paper.

    Tracks when a paper is discussed on Twitter, HackerNews, Reddit, etc.
    This helps us identify papers that are generating buzz.

    Example:
    - Geoffrey Hinton tweets about a paper → high signal
    - 500 points on HackerNews → high signal
    - Random retweet → low signal
    """

    __tablename__ = "social_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Link to the paper
    paper_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("papers.arxiv_id", ondelete="CASCADE"), nullable=False
    )

    # Where the signal came from
    # Values: "twitter", "hackernews", "reddit", etc.
    source: Mapped[str] = mapped_column(String(50), nullable=False)

    # URL to the tweet, HN thread, etc.
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)

    # Engagement metrics
    score: Mapped[int] = mapped_column(Integer, default=0)  # Likes, upvotes, etc.
    comments_count: Mapped[int] = mapped_column(Integer, default=0)

    # Text snippet or quote
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Who posted it (username or account name)
    author: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # When it was posted
    posted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # When we discovered it
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationship back to the paper
    paper: Mapped["Paper"] = relationship("Paper", back_populates="social_signals")

    def __repr__(self) -> str:
        return f"<SocialSignal {self.source} for {self.paper_id}>"


# Index for finding signals for a paper
Index("idx_social_paper_source", SocialSignal.paper_id, SocialSignal.source)


# ============================================================================
# ReadingProgress Model - Track user's reading journey
# ============================================================================


class ReadingProgress(Base):
    """
    Tracks which papers the user has read and their notes.

    This helps us:
    - Show reading history
    - Recommend papers based on what you've read
    - Track learning progress
    - Build knowledge graphs of your learning path
    """

    __tablename__ = "reading_progress"

    # Paper is the primary key (one progress record per paper)
    paper_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("papers.arxiv_id", ondelete="CASCADE"), primary_key=True
    )

    # Reading status
    # Values: "unread", "reading", "finished", "archived"
    status: Mapped[str] = mapped_column(String(20), default="unread", nullable=False)

    # Timestamps
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # User feedback
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5 stars
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # How long they spent reading (in minutes)
    time_spent_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationship back to the paper
    paper: Mapped["Paper"] = relationship("Paper", back_populates="reading_progress")

    def __repr__(self) -> str:
        return f"<ReadingProgress {self.paper_id}: {self.status}>"


# Index for finding papers by status
Index("idx_progress_status", ReadingProgress.status)
