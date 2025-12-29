"""
NotifierAgent - Sends notification for noteworthy papers.

This agent sends email notifications when noteworthy papers are found.
"""

from loguru import logger

from src.agents.radar.state import RadarState
from src.services.email_notifier import send_paper_notification


def notifier_agent_node(state: RadarState) -> RadarState:
    """
    NotifierAgent: Sends notification for noteworthy papers.

    Sends an email notification with the noteworthy papers,
    indicating whether they were found due to breakthrough
    potential or trending status.

    Args:
        state: Current radar workflow state

    Returns:
        Updated state with notification_sent status
    """
    logger.info(
        """
╔╗╔╔═╗╔╦╗╦╔═╗╦ ╦
║║║║ ║ ║ ║╠╣ ╚╦╝
╝╚╝╚═╝ ╩ ╩╚   ╩  AGENT
    """
    )
    logger.info("📧 Sending notification...")

    noteworthy = state.get("noteworthy_papers", [])

    if not noteworthy:
        logger.warning("No papers to notify about")
        state["notification_sent"] = False
        return state

    try:
        # Determine notification reason
        breakthroughs = [
            p
            for p in noteworthy
            if p.breakthrough_score
            and p.breakthrough_score >= state.get("breakthrough_threshold", 0.6)
        ]
        reason = "breakthrough" if breakthroughs else "trending"

        success = send_paper_notification(noteworthy, reason=reason)
        state["notification_sent"] = success

        if success:
            logger.info(f"✅ Notification sent for {len(noteworthy)} papers")
        else:
            logger.warning("Failed to send notification")

    except Exception as e:
        logger.error(f"❌ NotifierAgent failed: {e}")
        state["notification_sent"] = False
        if "errors" not in state or state["errors"] is None:
            state["errors"] = []
        state["errors"].append(f"Notifier error: {e!s}")

    return state
