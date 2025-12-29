"""
Email Notification Service for Research Radar.

Sends email alerts when noteworthy papers are discovered.
Uses Gmail SMTP with app passwords for authentication.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from loguru import logger

from src.config import settings
from src.models.paper import Paper


class EmailNotifier:
    """Send email notifications for noteworthy papers."""

    def __init__(self):
        """Initialize the email notifier with settings."""
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.username = settings.smtp_username
        self.password = settings.smtp_password
        self.recipient = settings.recipient_email or settings.email_recipient

    def is_configured(self) -> bool:
        """Check if email is properly configured."""
        return all([self.username, self.password, self.recipient])

    def send_paper_alert(self, papers: list[Paper], reason: str = "noteworthy") -> bool:
        """
        Send an email alert about noteworthy papers.

        Args:
            papers: List of papers to include in the alert
            reason: Why these papers are noteworthy (e.g., "breakthrough", "trending")

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning("Email not configured - skipping notification")
            return False

        if not papers:
            logger.debug("No papers to notify about")
            return True

        try:
            msg = self._build_email(papers, reason)
            self._send_email(msg)
            logger.info(f"Sent alert for {len(papers)} papers to {self.recipient}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def _build_email(self, papers: list[Paper], reason: str) -> MIMEMultipart:
        """Build the email message with HTML content."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = self._build_subject(papers, reason)
        msg["From"] = self.username
        msg["To"] = self.recipient

        # Build HTML content
        html = self._build_html(papers, reason)
        text = self._build_plaintext(papers, reason)

        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        return msg

    def _build_subject(self, papers: list[Paper], reason: str) -> str:
        """Build email subject line."""
        count = len(papers)
        if reason == "breakthrough":
            emoji = "🚀"
            label = "Breakthrough"
        elif reason == "trending":
            emoji = "📈"
            label = "Trending"
        else:
            emoji = "📚"
            label = "Noteworthy"

        if count == 1:
            return f"{emoji} {label} Paper: {papers[0].title[:50]}..."
        return f"{emoji} {count} {label} Papers Found"

    def _build_html(self, papers: list[Paper], reason: str) -> str:
        """Build HTML email body."""
        papers_html = ""
        for i, paper in enumerate(papers, 1):
            scores = self._format_scores(paper)
            reasons = self._format_reasons(paper)

            # Build reasons section if we have reasons
            reasons_html = ""
            if reasons:
                reasons_html = f"""
                <div style="margin: 12px 0; padding: 10px; background: #f8f9fa; border-radius: 6px; font-size: 13px; color: #555;">
                    <strong>Why this paper?</strong> {reasons}
                </div>
                """

            papers_html += f"""
            <div style="margin-bottom: 24px; padding: 16px; border: 1px solid #e0e0e0; border-radius: 8px;">
                <h3 style="margin: 0 0 8px 0; color: #1a1a1a;">
                    {i}. {paper.title}
                </h3>
                <p style="margin: 0 0 8px 0; color: #666; font-size: 14px;">
                    {', '.join(paper.authors[:3])}{'...' if len(paper.authors) > 3 else ''}
                </p>
                <p style="margin: 0 0 12px 0; color: #444; font-size: 14px;">
                    {paper.eli5_summary or paper.abstract[:300]}{'...' if len(paper.abstract) > 300 else ''}
                </p>
                {reasons_html}
                <div style="font-size: 13px; color: #888;">
                    {scores}
                </div>
                <div style="margin-top: 12px;">
                    <a href="{paper.abstract_url}" style="color: #0066cc; text-decoration: none;">
                        View on arXiv →
                    </a>
                </div>
            </div>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h1 style="color: #1a1a1a; border-bottom: 2px solid #0066cc; padding-bottom: 12px;">
                Research Radar Alert
            </h1>
            <p style="color: #666; margin-bottom: 24px;">
                Found {len(papers)} {reason} paper{'s' if len(papers) > 1 else ''} you should check out:
            </p>
            {papers_html}
            <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 24px 0;">
            <p style="color: #888; font-size: 12px;">
                Sent by Research Radar |
                <a href="#" style="color: #0066cc;">Manage preferences</a>
            </p>
        </body>
        </html>
        """

    def _build_plaintext(self, papers: list[Paper], reason: str) -> str:
        """Build plaintext email body for clients that don't support HTML."""
        lines = [
            "Research Radar Alert",
            "====================",
            "",
            f"Found {len(papers)} {reason} paper{'s' if len(papers) > 1 else ''}:",
            "",
        ]

        for i, paper in enumerate(papers, 1):
            reasons = self._format_reasons(paper)
            paper_lines = [
                f"{i}. {paper.title}",
                f"   Authors: {', '.join(paper.authors[:3])}",
                f"   {self._format_scores(paper)}",
            ]
            if reasons:
                paper_lines.append(f"   Why this paper? {reasons}")
            paper_lines.extend([f"   Link: {paper.abstract_url}", ""])
            lines.extend(paper_lines)

        return "\n".join(lines)

    def _format_scores(self, paper: Paper) -> str:
        """Format paper scores for display with trending icons."""
        scores = []

        # Breakthrough score with icon
        if paper.breakthrough_score is not None:
            if paper.breakthrough_score >= 0.8:
                scores.append(f"🚀 Breakthrough: {paper.breakthrough_score:.0%}")
            else:
                scores.append(f"Breakthrough: {paper.breakthrough_score:.0%}")

        # Relevance score
        if paper.relevance_score is not None:
            scores.append(f"Relevance: {paper.relevance_score:.0%}")

        # HN score with trending icons
        if paper.score_components:
            hn_score = paper.score_components.get("hn_score", 0)
            hn_comments = paper.score_components.get("hn_comments", 0)
            if hn_score:
                if hn_score >= 100:
                    icon = "🔥"  # Hot/trending
                elif hn_score >= 50:
                    icon = "📈"  # Rising
                else:
                    icon = ""
                hn_text = f"{icon} HN: {hn_score} pts" if icon else f"HN: {hn_score} pts"
                if hn_comments:
                    hn_text += f" ({hn_comments} comments)"
                scores.append(hn_text.strip())

            # Twitter score if present
            twitter_score = paper.score_components.get("twitter_score", 0)
            if twitter_score:
                scores.append(f"Twitter: {twitter_score}")

        return " | ".join(scores) if scores else "New discovery"

    def _format_reasons(self, paper: Paper) -> str:
        """Generate 'Why this paper?' explanation."""
        reasons = []

        # Breakthrough potential
        if paper.breakthrough_score is not None and paper.breakthrough_score >= 0.8:
            reasons.append("High breakthrough potential")
        elif paper.breakthrough_score is not None and paper.breakthrough_score >= 0.6:
            reasons.append("Notable breakthrough potential")

        # High relevance
        if paper.relevance_score is not None and paper.relevance_score >= 0.8:
            reasons.append("Highly relevant to your interests")
        elif paper.relevance_score is not None and paper.relevance_score >= 0.6:
            reasons.append("Matches your interests")

        # Social signals
        if paper.score_components:
            hn_score = paper.score_components.get("hn_score", 0)
            if hn_score >= 100:
                reasons.append(f"Trending on HN ({hn_score} pts)")
            elif hn_score >= 50:
                reasons.append(f"Discussed on HN ({hn_score} pts)")

            twitter_score = paper.score_components.get("twitter_score", 0)
            if twitter_score >= 100:
                reasons.append(f"Viral on Twitter ({twitter_score})")

        # Interest match from score components
        if paper.score_components:
            interest_match = paper.score_components.get("interest_match", 0)
            if interest_match > 0.7:
                reasons.append("Strong match with your research areas")

        return " • ".join(reasons) if reasons else ""

    def _send_email(self, msg: MIMEMultipart) -> None:
        """Send the email via SMTP."""
        # Caller (send_paper_alert) already checks is_configured(), so these are set
        if self.username is None or self.password is None:
            raise ValueError("Email credentials not configured")
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)


def send_paper_notification(papers: list[Paper], reason: str = "noteworthy") -> bool:
    """
    Convenience function to send paper notifications.

    Args:
        papers: Papers to notify about
        reason: Why these are noteworthy

    Returns:
        True if sent successfully
    """
    notifier = EmailNotifier()
    return notifier.send_paper_alert(papers, reason)


def test_email_connection() -> bool:
    """
    Test that email is configured and can connect.

    Returns:
        True if connection successful
    """
    notifier = EmailNotifier()
    if not notifier.is_configured():
        logger.error("Email not configured")
        return False

    try:
        # is_configured() already verified these are set
        if notifier.username is None or notifier.password is None:
            raise ValueError("Email credentials not configured")
        with smtplib.SMTP(notifier.smtp_host, notifier.smtp_port) as server:
            server.starttls()
            server.login(notifier.username, notifier.password)
            logger.info("Email connection test successful!")
            return True
    except Exception as e:
        logger.error(f"Email connection test failed: {e}")
        return False
