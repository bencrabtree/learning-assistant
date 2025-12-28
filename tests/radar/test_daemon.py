"""
Tests for the Research Radar daemon.

These tests verify the daemon scheduling and lifecycle management.
The actual workflow logic is tested in tests/test_graph.py.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.radar.daemon import ResearchRadar, run_radar, run_radar_once


class TestResearchRadarInit:
    """Tests for ResearchRadar initialization."""

    def test_initialization_loads_settings(self):
        """Test that radar loads settings correctly."""
        with patch("src.radar.daemon.settings") as mock_settings:
            mock_settings.radar_interval_hours = 3
            mock_settings.radar_start_hour = 5
            mock_settings.radar_end_hour = 20
            mock_settings.radar_timezone = "America/New_York"
            mock_settings.notify_breakthrough_threshold = 0.6
            mock_settings.notify_social_threshold = 0.3
            mock_settings.notify_relevance_threshold = 0.5

            radar = ResearchRadar()

            assert radar.interval_hours == 3
            assert radar.start_hour == 5
            assert radar.end_hour == 20
            assert radar.breakthrough_threshold == 0.6
            assert radar.social_threshold == 0.3
            assert radar.relevance_threshold == 0.5
            assert radar.running is False


class TestScheduleLogic:
    """Tests for schedule-related logic."""

    @pytest.fixture
    def radar(self):
        """Create a radar instance for testing."""
        with patch("src.radar.daemon.settings") as mock_settings:
            mock_settings.radar_interval_hours = 3
            mock_settings.radar_start_hour = 5
            mock_settings.radar_end_hour = 20
            mock_settings.radar_timezone = "America/New_York"
            mock_settings.notify_breakthrough_threshold = 0.6
            mock_settings.notify_social_threshold = 0.3
            mock_settings.notify_relevance_threshold = 0.5

            return ResearchRadar()

    def test_is_within_schedule_during_window(self, radar):
        """Test schedule check during active window."""
        # Mock current time to 10am EST (within 5am-8pm window)
        mock_now = datetime(2024, 1, 15, 10, 0, 0, tzinfo=radar.timezone)
        with patch("src.radar.daemon.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_now

            assert radar._is_within_schedule() is True

    def test_is_within_schedule_before_window(self, radar):
        """Test schedule check before active window."""
        # Mock current time to 3am EST (before 5am window)
        mock_now = datetime(2024, 1, 15, 3, 0, 0, tzinfo=radar.timezone)
        with patch("src.radar.daemon.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_now

            assert radar._is_within_schedule() is False

    def test_is_within_schedule_after_window(self, radar):
        """Test schedule check after active window."""
        # Mock current time to 10pm EST (after 8pm window)
        mock_now = datetime(2024, 1, 15, 22, 0, 0, tzinfo=radar.timezone)
        with patch("src.radar.daemon.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_now

            assert radar._is_within_schedule() is False

    def test_time_until_next_window_after_end(self, radar):
        """Test time calculation when after end hour."""
        # Mock current time to 10pm EST
        mock_now = datetime(2024, 1, 15, 22, 0, 0, tzinfo=radar.timezone)
        with patch("src.radar.daemon.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_now

            hours = radar._time_until_next_window()
            # 10pm to midnight = 2h, midnight to 5am = 5h, total = 7h
            assert hours == 7

    def test_time_until_next_window_before_start(self, radar):
        """Test time calculation when before start hour."""
        # Mock current time to 3am EST
        mock_now = datetime(2024, 1, 15, 3, 0, 0, tzinfo=radar.timezone)
        with patch("src.radar.daemon.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_now

            hours = radar._time_until_next_window()
            # 3am to 5am = 2h
            assert hours == 2

    def test_time_until_next_window_within(self, radar):
        """Test time calculation when within window."""
        # Mock current time to 10am EST (within window)
        mock_now = datetime(2024, 1, 15, 10, 0, 0, tzinfo=radar.timezone)
        with patch("src.radar.daemon.datetime") as mock_datetime:
            mock_datetime.now.return_value = mock_now

            hours = radar._time_until_next_window()
            assert hours == 0


class TestScanCycle:
    """Tests for the scan cycle."""

    @pytest.fixture
    def radar(self):
        """Create a radar instance for testing."""
        with patch("src.radar.daemon.settings") as mock_settings:
            mock_settings.radar_interval_hours = 3
            mock_settings.radar_start_hour = 5
            mock_settings.radar_end_hour = 20
            mock_settings.radar_timezone = "America/New_York"
            mock_settings.notify_breakthrough_threshold = 0.6
            mock_settings.notify_social_threshold = 0.3
            mock_settings.notify_relevance_threshold = 0.5

            return ResearchRadar()

    @patch("src.radar.daemon.run_radar_workflow")
    def test_run_scan_cycle_success(self, mock_workflow, radar):
        """Test successful scan cycle."""
        mock_workflow.return_value = {
            "iterations": 2,
            "strategies_tried": ["recent_2_days", "recent_7_days"],
            "papers_seen": ["paper1", "paper2", "paper3"],
            "noteworthy_papers": [MagicMock()],
            "notification_sent": True,
            "errors": [],
        }

        result = radar._run_scan_cycle()

        assert result["iterations"] == 2
        assert result["papers_scanned"] == 3
        assert result["noteworthy_papers"] == 1
        assert result["notification_sent"] is True
        assert len(result["errors"]) == 0
        mock_workflow.assert_called_once()

    @patch("src.radar.daemon.run_radar_workflow")
    def test_run_scan_cycle_no_papers(self, mock_workflow, radar):
        """Test scan cycle with no noteworthy papers."""
        mock_workflow.return_value = {
            "iterations": 3,
            "strategies_tried": ["recent_2_days", "recent_7_days", "recent_14_days"],
            "papers_seen": ["paper1", "paper2"],
            "noteworthy_papers": [],
            "notification_sent": False,
            "errors": [],
        }

        result = radar._run_scan_cycle()

        assert result["noteworthy_papers"] == 0
        assert result["notification_sent"] is False

    @patch("src.radar.daemon.run_radar_workflow")
    def test_run_scan_cycle_with_errors(self, mock_workflow, radar):
        """Test scan cycle handles workflow errors."""
        mock_workflow.return_value = {
            "iterations": 1,
            "strategies_tried": ["recent_2_days"],
            "papers_seen": [],
            "noteworthy_papers": [],
            "notification_sent": False,
            "errors": ["Scanner error: API failed"],
        }

        result = radar._run_scan_cycle()

        assert len(result["errors"]) == 1
        assert "Scanner error" in result["errors"][0]

    @patch("src.radar.daemon.run_radar_workflow")
    def test_run_scan_cycle_exception(self, mock_workflow, radar):
        """Test scan cycle handles exceptions."""
        mock_workflow.side_effect = Exception("Workflow crashed")

        result = radar._run_scan_cycle()

        assert result["iterations"] == 0
        assert "Workflow crashed" in result["errors"][0]

    @patch("src.radar.daemon.run_radar_workflow")
    def test_run_scan_cycle_passes_thresholds(self, mock_workflow, radar):
        """Test that scan cycle passes thresholds to workflow."""
        mock_workflow.return_value = {
            "iterations": 1,
            "strategies_tried": [],
            "papers_seen": [],
            "noteworthy_papers": [],
            "notification_sent": False,
            "errors": [],
        }

        radar._run_scan_cycle()

        mock_workflow.assert_called_once_with(
            max_iterations=3,
            breakthrough_threshold=0.6,
            relevance_threshold=0.5,
            social_threshold=0.3,
        )


class TestStopMethod:
    """Tests for the stop method."""

    def test_stop_sets_running_false(self):
        """Test that stop() sets running to False."""
        with patch("src.radar.daemon.settings") as mock_settings:
            mock_settings.radar_interval_hours = 3
            mock_settings.radar_start_hour = 5
            mock_settings.radar_end_hour = 20
            mock_settings.radar_timezone = "America/New_York"
            mock_settings.notify_breakthrough_threshold = 0.6
            mock_settings.notify_social_threshold = 0.3
            mock_settings.notify_relevance_threshold = 0.5

            radar = ResearchRadar()
            radar.running = True
            radar.stop()
            assert radar.running is False


class TestRunOnceMethod:
    """Tests for run_once method."""

    @patch("src.radar.daemon.settings")
    @patch("src.radar.daemon.run_radar_workflow")
    def test_run_once_returns_results(self, mock_workflow, mock_settings):
        """Test run_once returns workflow results."""
        mock_settings.radar_interval_hours = 3
        mock_settings.radar_start_hour = 5
        mock_settings.radar_end_hour = 20
        mock_settings.radar_timezone = "America/New_York"
        mock_settings.notify_breakthrough_threshold = 0.6
        mock_settings.notify_social_threshold = 0.3
        mock_settings.notify_relevance_threshold = 0.5

        mock_workflow.return_value = {
            "iterations": 1,
            "strategies_tried": ["recent_2_days"],
            "papers_seen": ["paper1"],
            "noteworthy_papers": [],
            "notification_sent": False,
            "errors": [],
        }

        radar = ResearchRadar()
        result = radar.run_once()

        assert "iterations" in result
        assert "papers_scanned" in result


class TestInterruptibleSleep:
    """Tests for interruptible sleep."""

    @pytest.fixture
    def radar(self):
        """Create a radar instance for testing."""
        with patch("src.radar.daemon.settings") as mock_settings:
            mock_settings.radar_interval_hours = 3
            mock_settings.radar_start_hour = 5
            mock_settings.radar_end_hour = 20
            mock_settings.radar_timezone = "America/New_York"
            mock_settings.notify_breakthrough_threshold = 0.6
            mock_settings.notify_social_threshold = 0.3
            mock_settings.notify_relevance_threshold = 0.5

            return ResearchRadar()

    @patch("src.radar.daemon.time.sleep")
    def test_interruptible_sleep_completes(self, mock_sleep, radar):
        """Test interruptible sleep completes when running."""
        radar.running = True

        radar._interruptible_sleep(5)  # 5 seconds

        # Should sleep once (5 < 10 interval)
        mock_sleep.assert_called()

    @patch("src.radar.daemon.time.sleep")
    def test_interruptible_sleep_stops_when_not_running(self, mock_sleep, radar):
        """Test interruptible sleep stops when running is False."""
        radar.running = False

        radar._interruptible_sleep(30)

        # Should not sleep at all when not running
        mock_sleep.assert_not_called()


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    @patch("src.radar.daemon.settings")
    @patch("src.radar.daemon.ResearchRadar")
    def test_run_radar_when_disabled(self, mock_radar_class, mock_settings):
        """Test run_radar exits when disabled."""
        mock_settings.radar_enabled = False

        with pytest.raises(SystemExit) as exc_info:
            run_radar()

        assert exc_info.value.code == 1

    @patch("src.radar.daemon.settings")
    @patch("src.radar.daemon.ResearchRadar")
    def test_run_radar_when_enabled(self, mock_radar_class, mock_settings):
        """Test run_radar starts when enabled."""
        mock_settings.radar_enabled = True
        mock_radar = MagicMock()
        mock_radar_class.return_value = mock_radar

        run_radar()

        mock_radar.start.assert_called_once()

    @patch("src.radar.daemon.settings")
    @patch("src.radar.daemon.run_radar_workflow")
    def test_run_radar_once(self, mock_workflow, mock_settings):
        """Test run_radar_once function."""
        mock_settings.radar_interval_hours = 3
        mock_settings.radar_start_hour = 5
        mock_settings.radar_end_hour = 20
        mock_settings.radar_timezone = "America/New_York"
        mock_settings.notify_breakthrough_threshold = 0.6
        mock_settings.notify_social_threshold = 0.3
        mock_settings.notify_relevance_threshold = 0.5

        mock_workflow.return_value = {
            "iterations": 1,
            "strategies_tried": [],
            "papers_seen": [],
            "noteworthy_papers": [],
            "notification_sent": False,
            "errors": [],
        }

        result = run_radar_once()

        assert "iterations" in result
        mock_workflow.assert_called_once()
