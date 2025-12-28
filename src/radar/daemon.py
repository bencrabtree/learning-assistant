"""
Research Radar Daemon - Background paper monitoring system.

This daemon runs continuously, invoking the agentic radar workflow
to scan for noteworthy papers and send notifications.

Key features:
- Runs on a configurable schedule (e.g., every 3 hours, 5am-8pm EST)
- Uses LangGraph agentic workflow with 8 specialized agents
- Iterative search with multiple expansion strategies
- Only notifies when papers meet threshold criteria

The heavy lifting is done by the agentic radar workflow in graph.py.
This daemon just handles scheduling and lifecycle management.
"""

import signal
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from loguru import logger

from src.config import settings
from src.graph import run_radar_workflow


class ResearchRadar:
    """
    Background research monitoring daemon.

    This is a thin wrapper that:
    1. Manages the daemon lifecycle (start/stop)
    2. Handles scheduling (when to run)
    3. Invokes the agentic radar workflow

    The actual paper discovery, assessment, and notification
    is handled by the LangGraph workflow in graph.py.
    """

    def __init__(self):
        """Initialize the radar with settings."""
        self.interval_hours = settings.radar_interval_hours
        self.start_hour = settings.radar_start_hour
        self.end_hour = settings.radar_end_hour
        self.timezone = ZoneInfo(settings.radar_timezone)

        # Notification thresholds (passed to workflow)
        self.breakthrough_threshold = settings.notify_breakthrough_threshold
        self.social_threshold = settings.notify_social_threshold
        self.relevance_threshold = settings.notify_relevance_threshold

        self.running = False

    def start(self) -> None:
        """Start the radar daemon."""
        logger.info("🔬 Research Radar starting...")
        logger.info(
            f"Schedule: Every {self.interval_hours}h, "
            f"{self.start_hour}:00-{self.end_hour}:00 {settings.radar_timezone}"
        )
        logger.info(
            f"Thresholds: breakthrough>{self.breakthrough_threshold}, "
            f"social>{self.social_threshold}, relevance>{self.relevance_threshold}"
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
            Dict with scan results from the workflow
        """
        return self._run_scan_cycle()

    def _run_scan_cycle(self) -> dict:
        """
        Execute one full scan cycle using the agentic workflow.

        This invokes the LangGraph radar workflow which:
        1. StrategyAgent - Selects search strategy
        2. ScannerAgent - Discovers papers
        3. FilterAgent - Removes duplicates
        4. AssessorAgent - Evaluates breakthrough potential
        5. CuratorAgent - Scores and ranks
        6. DecisionAgent - Routes to notify/expand/done
        7. NotifierAgent - Sends notification (if noteworthy found)
        8. LogAgent - Logs results (if nothing found)

        Returns:
            Dict with cycle results
        """
        logger.info("=" * 60)
        logger.info("🔍 Starting agentic scan cycle...")
        cycle_start = datetime.now(self.timezone)

        try:
            # Run the agentic radar workflow
            result = run_radar_workflow(
                max_iterations=3,
                breakthrough_threshold=self.breakthrough_threshold,
                relevance_threshold=self.relevance_threshold,
                social_threshold=self.social_threshold,
            )

            # Convert workflow state to results dict
            results = {
                "timestamp": cycle_start.isoformat(),
                "iterations": result.get("iterations", 0),
                "strategies_tried": result.get("strategies_tried", []),
                "papers_scanned": len(result.get("papers_seen", [])),
                "noteworthy_papers": len(result.get("noteworthy_papers", [])),
                "notification_sent": result.get("notification_sent", False),
                "errors": result.get("errors", []),
            }

            duration = (datetime.now(self.timezone) - cycle_start).total_seconds()
            logger.info(f"Scan cycle complete in {duration:.1f}s")
            logger.info(f"Results: {results}")
            logger.info("=" * 60)

            return results

        except Exception as e:
            logger.error(f"Scan cycle error: {e}")
            logger.exception("Full traceback:")
            return {
                "timestamp": cycle_start.isoformat(),
                "iterations": 0,
                "strategies_tried": [],
                "papers_scanned": 0,
                "noteworthy_papers": 0,
                "notification_sent": False,
                "errors": [str(e)],
            }

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
