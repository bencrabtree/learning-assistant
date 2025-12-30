"""
Email Notification Service for Research Radar.

Sends email alerts when noteworthy papers are discovered.
Uses Gmail SMTP with app passwords for authentication.

Seed Papers:
- Unread favorite papers are always included at the top of the digest
- These are papers the user has explicitly marked as important
- They appear in a special "📌 Seed Papers" section
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

    def send_paper_alert(
        self,
        papers: list[Paper],
        reason: str = "noteworthy",
        include_seed_papers: bool = True,
    ) -> bool:
        """
        Send an email alert about noteworthy papers.

        Args:
            papers: List of papers to include in the alert
            reason: Why these papers are noteworthy (e.g., "breakthrough", "trending")
            include_seed_papers: Whether to include unread favorites at the top

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.warning("Email not configured - skipping notification")
            return False

        # Get seed papers if requested
        seed_papers: list[Paper] = []
        if include_seed_papers:
            from src.agents.curator import get_unread_favorites

            seed_papers = get_unread_favorites()
            # Remove seed papers from main list to avoid duplicates
            seed_ids = {p.arxiv_id for p in seed_papers}
            papers = [p for p in papers if p.arxiv_id not in seed_ids]

        if not papers and not seed_papers:
            logger.debug("No papers to notify about")
            return True

        try:
            msg = self._build_email(papers, reason, seed_papers=seed_papers)
            self._send_email(msg)
            total = len(papers) + len(seed_papers)
            logger.info(
                f"Sent alert for {total} papers ({len(seed_papers)} seed, {len(papers)} discovered) to {self.recipient}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def _build_email(
        self,
        papers: list[Paper],
        reason: str,
        seed_papers: list[Paper] | None = None,
    ) -> MIMEMultipart:
        """Build the email message with HTML content."""
        msg = MIMEMultipart("alternative")
        all_papers = (seed_papers or []) + papers
        msg["Subject"] = self._build_subject(all_papers, reason, has_seed=bool(seed_papers))
        msg["From"] = self.username
        msg["To"] = self.recipient

        # Build HTML content
        html = self._build_html(papers, reason, seed_papers=seed_papers)
        text = self._build_plaintext(papers, reason, seed_papers=seed_papers)

        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        return msg

    def _build_subject(
        self,
        papers: list[Paper],
        reason: str,
        has_seed: bool = False,
    ) -> str:
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

        if has_seed:
            emoji = "📌"
            label = "Research Radar"

        if count == 1:
            return f"{emoji} {label} Paper: {papers[0].title[:50]}..."
        return f"{emoji} {count} {label} Papers Found"

    def _build_html(
        self,
        papers: list[Paper],
        reason: str,
        seed_papers: list[Paper] | None = None,
    ) -> str:
        """Build HTML email body."""
        feedback_url = settings.feedback_url

        # Build seed papers section (if any)
        seed_html = ""
        if seed_papers:
            seed_html = """
            <div style="margin-bottom: 32px;">
                <h2 style="color: #1a1a1a; font-size: 18px; margin-bottom: 16px; display: flex; align-items: center;">
                    📌 Your Seed Papers
                    <span style="font-size: 12px; font-weight: normal; color: #666; margin-left: 8px;">
                        (papers you marked as favorites)
                    </span>
                </h2>
            """
            for paper in seed_papers:
                scores = self._format_scores(paper)
                feedback_buttons = self._build_feedback_buttons(paper.arxiv_id, feedback_url)

                seed_html += f"""
                <div style="margin-bottom: 20px; padding: 16px; border: 2px solid #ffc107; border-radius: 8px; background: #fffef5;">
                    <h3 style="margin: 0 0 8px 0; color: #1a1a1a;">
                        {paper.title}
                    </h3>
                    <p style="margin: 0 0 8px 0; color: #666; font-size: 14px;">
                        {', '.join(paper.authors[:3])}{'...' if len(paper.authors) > 3 else ''}
                    </p>
                    <p style="margin: 0 0 12px 0; color: #444; font-size: 14px;">
                        {paper.eli5_summary or paper.abstract[:300]}{'...' if len(paper.abstract) > 300 else ''}
                    </p>
                    <div style="font-size: 13px; color: #888;">
                        {scores}
                    </div>
                    <div style="margin-top: 12px; display: flex; align-items: center; gap: 16px;">
                        <a href="{paper.abstract_url}" style="color: #0066cc; text-decoration: none;">
                            View on arXiv →
                        </a>
                        {feedback_buttons}
                    </div>
                </div>
                """
            seed_html += "</div>"

        # Build discovered papers section
        papers_html = ""
        if papers:
            papers_html = """
            <div style="margin-bottom: 32px;">
                <h2 style="color: #1a1a1a; font-size: 18px; margin-bottom: 16px;">
                    🔍 New Discoveries
                </h2>
            """
            for i, paper in enumerate(papers, 1):
                scores = self._format_scores(paper)
                reasons = self._format_reasons(paper)
                feedback_buttons = self._build_feedback_buttons(paper.arxiv_id, feedback_url)

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
                    <div style="margin-top: 12px; display: flex; align-items: center; gap: 16px;">
                        <a href="{paper.abstract_url}" style="color: #0066cc; text-decoration: none;">
                            View on arXiv →
                        </a>
                        {feedback_buttons}
                    </div>
                </div>
                """
            papers_html += "</div>"

        # Build intro text
        if seed_papers and papers:
            intro = f"Found {len(seed_papers)} seed paper{'s' if len(seed_papers) > 1 else ''} and {len(papers)} {reason} paper{'s' if len(papers) > 1 else ''} for you:"
        elif seed_papers:
            intro = f"Your {len(seed_papers)} seed paper{'s' if len(seed_papers) > 1 else ''} to review:"
        else:
            intro = f"Found {len(papers)} {reason} paper{'s' if len(papers) > 1 else ''} you should check out:"

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
                {intro}
            </p>
            {seed_html}
            {papers_html}
            <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 24px 0;">
            <p style="color: #888; font-size: 12px;">
                Sent by Research Radar |
                <a href="#" style="color: #0066cc;">Manage preferences</a>
            </p>
        </body>
        </html>
        """

    def _build_plaintext(
        self,
        papers: list[Paper],
        reason: str,
        seed_papers: list[Paper] | None = None,
    ) -> str:
        """Build plaintext email body for clients that don't support HTML."""
        lines = [
            "Research Radar Alert",
            "====================",
            "",
        ]

        # Seed papers section
        if seed_papers:
            lines.extend(
                [
                    "📌 YOUR SEED PAPERS",
                    "-" * 40,
                    "",
                ]
            )
            for i, paper in enumerate(seed_papers, 1):
                paper_lines = [
                    f"{i}. {paper.title}",
                    f"   Authors: {', '.join(paper.authors[:3])}",
                    f"   {self._format_scores(paper)}",
                    f"   Link: {paper.abstract_url}",
                    "",
                ]
                lines.extend(paper_lines)

        # Discovered papers section
        if papers:
            lines.extend(
                [
                    "🔍 NEW DISCOVERIES",
                    "-" * 40,
                    "",
                ]
            )
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

    def _build_feedback_buttons(self, arxiv_id: str, feedback_url: str | None) -> str:
        """Build HTML feedback buttons for a paper."""
        if not feedback_url:
            return ""

        button_style = (
            "display: inline-block; padding: 4px 8px; border-radius: 4px; "
            "text-decoration: none; font-size: 12px; margin-left: 4px;"
        )

        return f"""
        <span style="margin-left: auto; white-space: nowrap;">
            Rate:
            <a href="{feedback_url}/feedback/{arxiv_id}/good"
               style="{button_style} background: #d4edda; color: #155724;">
               👍 Good
            </a>
            <a href="{feedback_url}/feedback/{arxiv_id}/neutral"
               style="{button_style} background: #fff3cd; color: #856404;">
               😐 Neutral
            </a>
            <a href="{feedback_url}/feedback/{arxiv_id}/bad"
               style="{button_style} background: #f8d7da; color: #721c24;">
               👎 Bad
            </a>
        </span>
        """

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
