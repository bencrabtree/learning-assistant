"""
Research Radar Daemon - Background paper monitoring system.

This daemon runs continuously, scanning for noteworthy papers and
sending notifications when something important is discovered.

Key features:
- Runs on a configurable schedule (e.g., every 3 hours, 5am-8pm EST)
- Scans both new papers AND rising/trending older papers
- Uses an agentic loop: discover → assess → decide → notify (or continue)
- Only notifies when papers meet threshold criteria
"""

import signal
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from loguru import logger

from src.agents.assessor import assess_papers_batch
from src.agents.curator import CuratorAgent
from src.config import settings
from src.database import get_db_session
from src.graph import run_full_pipeline
from src.models.paper import Paper
from src.services.email_notifier import send_paper_notification
from src.trackers.hackernews import fetch_hn_signals


class ResearchRadar:
    """
    Background research monitoring daemon.

    Implements an agentic loop that continuously searches for
    noteworthy papers and notifies the user when found.
    """

    def __init__(self):
        """Initialize the radar with settings."""
        self.interval_hours = settings.radar_interval_hours
        self.start_hour = settings.radar_start_hour
        self.end_hour = settings.radar_end_hour
        self.timezone = ZoneInfo(settings.radar_timezone)

        # Notification thresholds (aggressive = lower values)
        self.breakthrough_threshold = settings.notify_breakthrough_threshold
        self.social_threshold = settings.notify_social_threshold
        self.relevance_threshold = settings.notify_relevance_threshold

        self.running = False
        self.curator = CuratorAgent()

    def start(self) -> None:
        """Start the radar daemon."""
        logger.info("🔬 Research Radar starting...")
        logger.info(
            f"Schedule: Every {self.interval_hours}h, {self.start_hour}:00-{self.end_hour}:00 {settings.radar_timezone}"
        )
        logger.info(
            f"Thresholds: breakthrough>{self.breakthrough_threshold}, social>{self.social_threshold}, relevance>{self.relevance_threshold}"
        )

        self.running = True
        self._setup_signal_handlers()

        while self.running:
            try:
                if self._is_within_schedule():
                    self._run_scan_cycle()
                else:
                    next_window = self._time_until_next_window()
                    logger.info(f"Outside schedule window. Next scan in {next_window:.1f}h")

                # Sleep until next cycle
                sleep_seconds = self.interval_hours * 3600
                logger.info(f"Sleeping for {self.interval_hours}h until next scan...")
                self._interruptible_sleep(sleep_seconds)

            except KeyboardInterrupt:
                logger.info("Radar stopped by user")
                break
            except Exception as e:
                logger.error(f"Radar error: {e}")
                logger.exception("Full traceback:")
                # Sleep briefly before retrying
                time.sleep(60)

        logger.info("Research Radar stopped")

    def stop(self) -> None:
        """Stop the radar daemon gracefully."""
        logger.info("Stopping Research Radar...")
        self.running = False

    def run_once(self) -> dict:
        """
        Run a single scan cycle (useful for testing).

        Returns:
            Dict with scan results
        """
        return self._run_scan_cycle()

    def _run_scan_cycle(self) -> dict:
        """
        Execute one full scan cycle.

        This is the core agentic loop:
        1. Discover new papers (last 1-2 days)
        2. Find rising papers (older but trending)
        3. Assess all for breakthrough potential
        4. Score and rank by relevance
        5. Filter to noteworthy papers
        6. Notify if any found

        Returns:
            Dict with cycle results
        """
        logger.info("=" * 60)
        logger.info("🔍 Starting scan cycle...")
        cycle_start = datetime.now(self.timezone)

        results = {
            "timestamp": cycle_start.isoformat(),
            "new_papers": 0,
            "rising_papers": 0,
            "noteworthy_papers": 0,
            "notifications_sent": 0,
            "errors": [],
        }

        try:
            # Step 1: Discover new papers (last 2 days)
            logger.info("Step 1: Discovering new papers...")
            new_papers = self._discover_new_papers()
            results["new_papers"] = len(new_papers)
            logger.info(f"Found {len(new_papers)} new papers")

            # Step 2: Find rising/trending older papers
            logger.info("Step 2: Scanning for rising papers...")
            rising_papers = self._find_rising_papers()
            results["rising_papers"] = len(rising_papers)
            logger.info(f"Found {len(rising_papers)} rising papers")

            # Combine all candidates
            all_candidates = new_papers + rising_papers

            if not all_candidates:
                logger.info("No candidates found this cycle")
                return results

            # Step 3: Filter to noteworthy papers
            logger.info("Step 3: Filtering to noteworthy papers...")
            noteworthy = self._filter_noteworthy(all_candidates)
            results["noteworthy_papers"] = len(noteworthy)

            if noteworthy:
                logger.info(f"🎯 Found {len(noteworthy)} noteworthy papers!")

                # Step 4: Send notifications
                logger.info("Step 4: Sending notifications...")
                if self._notify(noteworthy):
                    results["notifications_sent"] = len(noteworthy)
                    logger.info(f"✅ Sent notification for {len(noteworthy)} papers")
                else:
                    logger.warning("Failed to send notification")
            else:
                logger.info("No papers met notification threshold this cycle")

        except Exception as e:
            logger.error(f"Scan cycle error: {e}")
            results["errors"].append(str(e))

        duration = (datetime.now(self.timezone) - cycle_start).total_seconds()
        logger.info(f"Scan cycle complete in {duration:.1f}s")
        logger.info("=" * 60)

        return results

    def _discover_new_papers(self) -> list[Paper]:
        """
        Discover new papers from the last 1-2 days.

        Uses the full pipeline but limits to recent papers.
        """
        try:
            result = run_full_pipeline(days_back=2, max_papers=20)

            if result.get("errors"):
                for error in result["errors"]:
                    logger.warning(f"Pipeline warning: {error}")

            return result.get("ranked_papers", []) or result.get("final_papers", []) or []

        except Exception as e:
            logger.error(f"Discovery failed: {e}")
            return []

    def _find_rising_papers(self) -> list[Paper]:
        """
        Find older papers that are gaining traction.

        Scans social signals for papers from the last 30 days
        that are currently being discussed.
        """
        try:
            # Get HN signals from last 7 days (captures rising old papers)
            hn_signals = fetch_hn_signals(days_back=7)

            if not hn_signals:
                return []

            # Find papers that are older but trending now
            rising = []
            with get_db_session() as db:
                for hn_signal in hn_signals:
                    arxiv_id = hn_signal.get("arxiv_id")
                    if not arxiv_id:
                        continue

                    # Check if we have this paper
                    paper = db.query(Paper).filter_by(arxiv_id=arxiv_id).first()

                    if paper:
                        # Update social signals
                        if paper.score_components is None:
                            paper.score_components = {}
                        paper.score_components["hn_score"] = hn_signal.get("score", 0)
                        paper.score_components["hn_comments"] = hn_signal.get("comments_count", 0)

                        # Check if it's "rising" (older than 3 days but getting attention)
                        age_days = (datetime.now() - paper.published_date.replace(tzinfo=None)).days
                        if age_days > 3 and hn_signal.get("score", 0) > 50:
                            rising.append(paper)

                db.commit()

            # Assess rising papers if not already assessed
            if rising:
                unassessed = [p for p in rising if p.breakthrough_score is None]
                if unassessed:
                    assess_papers_batch(unassessed)

                # Score them
                self.curator.score_papers(rising)

            return rising

        except Exception as e:
            logger.error(f"Rising paper scan failed: {e}")
            return []

    def _filter_noteworthy(self, papers: list[Paper]) -> list[Paper]:
        """
        Filter papers to only those worth notifying about.

        A paper is noteworthy if ANY of:
        - Breakthrough score > threshold
        - Social score > threshold AND relevance > threshold
        - Relevance score very high (> 0.8)
        """
        noteworthy = []

        for paper in papers:
            reasons = []

            # Check breakthrough
            if paper.breakthrough_score and paper.breakthrough_score >= self.breakthrough_threshold:
                reasons.append(f"breakthrough={paper.breakthrough_score:.0%}")

            # Check social proof + relevance combo
            social_score = self._get_social_score(paper)
            if (
                social_score >= self.social_threshold
                and paper.relevance_score
                and paper.relevance_score >= self.relevance_threshold
            ):
                reasons.append(
                    f"trending+relevant (social={social_score:.0%}, rel={paper.relevance_score:.0%})"
                )

            # Check very high relevance
            if paper.relevance_score and paper.relevance_score >= 0.8:
                reasons.append(f"high_relevance={paper.relevance_score:.0%}")

            if reasons:
                logger.info(f"📌 Noteworthy: {paper.title[:50]}... ({', '.join(reasons)})")
                noteworthy.append(paper)

        return noteworthy

    def _get_social_score(self, paper: Paper) -> float:
        """Calculate social score from paper's score components."""
        if not paper.score_components:
            return 0.0

        hn_score = paper.score_components.get("hn_score", 0)
        hn_comments = paper.score_components.get("hn_comments", 0)

        # Simple scoring rubric
        score = 0.0
        if hn_score > 200:
            score += 0.30
        elif hn_score > 100:
            score += 0.20
        elif hn_score > 50:
            score += 0.10

        if hn_comments > 100:
            score += 0.15
        elif hn_comments > 50:
            score += 0.10
        elif hn_comments > 20:
            score += 0.05

        return min(score, 0.5)  # Cap at 0.5

    def _notify(self, papers: list[Paper]) -> bool:
        """Send notification for noteworthy papers."""
        # Determine primary reason for notification
        breakthroughs = [
            p
            for p in papers
            if p.breakthrough_score and p.breakthrough_score >= self.breakthrough_threshold
        ]
        if breakthroughs:
            return send_paper_notification(papers, reason="breakthrough")
        return send_paper_notification(papers, reason="trending")

    def _is_within_schedule(self) -> bool:
        """Check if current time is within the scheduled window."""
        now = datetime.now(self.timezone)
        return self.start_hour <= now.hour < self.end_hour

    def _time_until_next_window(self) -> float:
        """Calculate hours until next schedule window opens."""
        now = datetime.now(self.timezone)

        if now.hour >= self.end_hour:
            # Window closed for today, next is tomorrow
            hours_until_midnight = 24 - now.hour
            return hours_until_midnight + self.start_hour
        elif now.hour < self.start_hour:
            # Before today's window
            return self.start_hour - now.hour
        else:
            # Within window
            return 0

    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""

        def handle_signal(signum, frame):
            logger.info(f"Received signal {signum}")
            self.stop()

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

    def _interruptible_sleep(self, seconds: float) -> None:
        """Sleep that can be interrupted by stop()."""
        interval = 10  # Check every 10 seconds
        elapsed = 0
        while elapsed < seconds and self.running:
            time.sleep(min(interval, seconds - elapsed))
            elapsed += interval


def run_radar() -> None:
    """Start the Research Radar daemon."""
    if not settings.radar_enabled:
        logger.error("Research Radar is not enabled. Set RADAR_ENABLED=true in .env")
        sys.exit(1)

    radar = ResearchRadar()
    radar.start()


def run_radar_once() -> dict:
    """Run a single radar scan (for testing)."""
    radar = ResearchRadar()
    return radar.run_once()
