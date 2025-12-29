"""
Feedback Recording Service.

Records user feedback on papers for personalization.
Supports ratings from email, CLI, or TUI.
"""

from loguru import logger

from src.database import get_db_session
from src.models.paper import Paper, ReadingProgress

# Rating mappings for different sources
RATING_MAP = {
    "good": 5,
    "neutral": 3,
    "bad": 1,
}


def record_feedback(
    arxiv_id: str,
    rating: int | str,
    source: str = "email",
) -> dict:
    """
    Record user feedback on a paper.

    Args:
        arxiv_id: The arXiv ID of the paper
        rating: Rating value (1-5) or string ("good", "neutral", "bad")
        source: Where feedback came from ("email", "cli", "tui")

    Returns:
        dict with status and message
    """
    # Convert string ratings to integers
    if isinstance(rating, str):
        rating_str = rating.lower()
        if rating_str in RATING_MAP:
            rating = RATING_MAP[rating_str]
        else:
            return {
                "success": False,
                "message": f"Invalid rating: {rating}. Use: good, neutral, bad",
            }

    # Validate rating range
    if not 1 <= rating <= 5:
        return {
            "success": False,
            "message": f"Rating must be 1-5, got: {rating}",
        }

    try:
        with get_db_session() as db:
            # Check if paper exists
            paper = db.query(Paper).filter_by(arxiv_id=arxiv_id).first()
            if not paper:
                return {
                    "success": False,
                    "message": f"Paper not found: {arxiv_id}",
                }

            # Get or create reading progress
            progress = db.query(ReadingProgress).filter_by(paper_id=arxiv_id).first()
            if not progress:
                progress = ReadingProgress(paper_id=arxiv_id, status="unread")
                db.add(progress)

            # Update rating
            progress.rating = rating
            # Note: feedback_source will be added in a future PR when schema is updated

            logger.info(f"Recorded feedback for {arxiv_id}: rating={rating}, source={source}")

            return {
                "success": True,
                "message": f"Thanks for your feedback on '{paper.title[:50]}...'",
                "paper_title": paper.title,
                "rating": rating,
            }

    except Exception as e:
        logger.error(f"Failed to record feedback: {e}")
        return {
            "success": False,
            "message": f"Error recording feedback: {e!s}",
        }


def get_paper_feedback(arxiv_id: str) -> dict | None:
    """
    Get existing feedback for a paper.

    Args:
        arxiv_id: The arXiv ID of the paper

    Returns:
        dict with rating info, or None if no feedback
    """
    try:
        with get_db_session() as db:
            progress = db.query(ReadingProgress).filter_by(paper_id=arxiv_id).first()
            if progress and progress.rating:
                return {
                    "rating": progress.rating,
                    # Note: source will be added in a future PR when schema is updated
                }
            return None
    except Exception as e:
        logger.error(f"Failed to get feedback: {e}")
        return None


def get_feedback_stats() -> dict:
    """
    Get statistics on collected feedback.

    Returns:
        dict with feedback statistics
    """
    try:
        with get_db_session() as db:
            total = db.query(ReadingProgress).filter(ReadingProgress.rating.isnot(None)).count()
            good = db.query(ReadingProgress).filter(ReadingProgress.rating >= 4).count()
            neutral = db.query(ReadingProgress).filter(ReadingProgress.rating == 3).count()
            bad = db.query(ReadingProgress).filter(ReadingProgress.rating <= 2).count()

            return {
                "total_feedback": total,
                "good": good,
                "neutral": neutral,
                "bad": bad,
            }
    except Exception as e:
        logger.error(f"Failed to get feedback stats: {e}")
        return {"total_feedback": 0, "good": 0, "neutral": 0, "bad": 0}
