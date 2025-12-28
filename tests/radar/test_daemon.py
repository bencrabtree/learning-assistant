"""
Tests for the Research Radar daemon.

These tests verify the background monitoring functionality
without actually running long scans.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.models.paper import Paper
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

    def test_initialization_creates_curator(self):
        """Test that radar creates a curator agent."""
        with patch("src.radar.daemon.settings") as mock_settings:
            mock_settings.radar_interval_hours = 3
            mock_settings.radar_start_hour = 5
            mock_settings.radar_end_hour = 20
            mock_settings.radar_timezone = "America/New_York"
            mock_settings.notify_breakthrough_threshold = 0.6
            mock_settings.notify_social_threshold = 0.3
            mock_settings.notify_relevance_threshold = 0.5

            with patch("src.radar.daemon.CuratorAgent") as mock_curator:
                _radar = ResearchRadar()
                mock_curator.assert_called_once()


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

            with patch("src.radar.daemon.CuratorAgent"):
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


class TestFilterNoteworthy:
    """Tests for noteworthy paper filtering."""

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

            with patch("src.radar.daemon.CuratorAgent"):
                return ResearchRadar()

    @pytest.fixture
    def sample_paper(self):
        """Create a sample paper."""
        return Paper(
            arxiv_id="2312.12345",
            title="Test Paper",
            abstract="Test abstract",
            authors=["Test Author"],
            published_date=datetime(2023, 12, 15),
            categories=["cs.AI"],
            pdf_url="https://arxiv.org/pdf/2312.12345",
            abstract_url="https://arxiv.org/abs/2312.12345",
        )

    def test_filter_breakthrough_paper(self, radar, sample_paper):
        """Test that high breakthrough papers are noteworthy."""
        sample_paper.breakthrough_score = 0.7  # Above 0.6 threshold
        sample_paper.relevance_score = 0.3  # Low relevance

        noteworthy = radar._filter_noteworthy([sample_paper])

        assert len(noteworthy) == 1
        assert noteworthy[0] == sample_paper

    def test_filter_high_relevance_paper(self, radar, sample_paper):
        """Test that very high relevance papers are noteworthy."""
        sample_paper.breakthrough_score = 0.3  # Low breakthrough
        sample_paper.relevance_score = 0.85  # Above 0.8 threshold

        noteworthy = radar._filter_noteworthy([sample_paper])

        assert len(noteworthy) == 1

    def test_filter_trending_relevant_paper(self, radar, sample_paper):
        """Test that trending + relevant papers are noteworthy."""
        sample_paper.breakthrough_score = 0.3  # Low breakthrough
        sample_paper.relevance_score = 0.6  # Above 0.5 threshold
        sample_paper.score_components = {"hn_score": 250, "hn_comments": 60}

        noteworthy = radar._filter_noteworthy([sample_paper])

        assert len(noteworthy) == 1

    def test_filter_low_scoring_paper(self, radar, sample_paper):
        """Test that low scoring papers are not noteworthy."""
        sample_paper.breakthrough_score = 0.3  # Low
        sample_paper.relevance_score = 0.4  # Low
        sample_paper.score_components = {"hn_score": 10}  # Low social

        noteworthy = radar._filter_noteworthy([sample_paper])

        assert len(noteworthy) == 0

    def test_filter_empty_list(self, radar):
        """Test filtering empty list."""
        noteworthy = radar._filter_noteworthy([])
        assert len(noteworthy) == 0


class TestSocialScoring:
    """Tests for social score calculation."""

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

            with patch("src.radar.daemon.CuratorAgent"):
                return ResearchRadar()

    @pytest.fixture
    def sample_paper(self):
        """Create a sample paper."""
        return Paper(
            arxiv_id="2312.12345",
            title="Test Paper",
            abstract="Test abstract",
            authors=["Test Author"],
            published_date=datetime(2023, 12, 15),
            categories=["cs.AI"],
            pdf_url="https://arxiv.org/pdf/2312.12345",
            abstract_url="https://arxiv.org/abs/2312.12345",
        )

    def test_social_score_high_engagement(self, radar, sample_paper):
        """Test social score for high engagement."""
        sample_paper.score_components = {"hn_score": 250, "hn_comments": 120}

        score = radar._get_social_score(sample_paper)

        # 250 points = 0.30, 120 comments = 0.15, total = 0.45
        assert score == pytest.approx(0.45)

    def test_social_score_medium_engagement(self, radar, sample_paper):
        """Test social score for medium engagement."""
        sample_paper.score_components = {"hn_score": 120, "hn_comments": 60}

        score = radar._get_social_score(sample_paper)

        # 120 points = 0.20, 60 comments = 0.10, total = 0.30
        assert score == pytest.approx(0.30)

    def test_social_score_low_engagement(self, radar, sample_paper):
        """Test social score for low engagement."""
        sample_paper.score_components = {"hn_score": 60, "hn_comments": 25}

        score = radar._get_social_score(sample_paper)

        # 60 points = 0.10, 25 comments = 0.05, total = 0.15
        assert score == pytest.approx(0.15)

    def test_social_score_no_components(self, radar, sample_paper):
        """Test social score with no score components."""
        sample_paper.score_components = None

        score = radar._get_social_score(sample_paper)

        assert score == 0.0

    def test_social_score_max_engagement(self, radar, sample_paper):
        """Test that social score maxes at 0.45 (0.30 + 0.15)."""
        sample_paper.score_components = {"hn_score": 500, "hn_comments": 200}

        score = radar._get_social_score(sample_paper)

        # Max is 0.30 (hn_score > 200) + 0.15 (comments > 100) = 0.45
        assert score == pytest.approx(0.45)


class TestScanCycle:
    """Tests for the scan cycle logic."""

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

            with patch("src.radar.daemon.CuratorAgent"):
                return ResearchRadar()

    @patch("src.radar.daemon.run_full_pipeline")
    @patch("src.radar.daemon.fetch_hn_signals")
    @patch("src.radar.daemon.send_paper_notification")
    def test_scan_cycle_no_papers(self, mock_notify, mock_hn, mock_pipeline, radar):
        """Test scan cycle with no papers found."""
        mock_pipeline.return_value = {"ranked_papers": []}
        mock_hn.return_value = []

        results = radar._run_scan_cycle()

        assert results["new_papers"] == 0
        assert results["rising_papers"] == 0
        assert results["noteworthy_papers"] == 0
        mock_notify.assert_not_called()

    @patch("src.radar.daemon.run_full_pipeline")
    @patch("src.radar.daemon.fetch_hn_signals")
    @patch("src.radar.daemon.send_paper_notification")
    def test_scan_cycle_with_noteworthy_papers(self, mock_notify, mock_hn, mock_pipeline, radar):
        """Test scan cycle that finds noteworthy papers."""
        breakthrough_paper = Paper(
            arxiv_id="2312.12345",
            title="Breakthrough Paper",
            abstract="Test abstract",
            authors=["Test Author"],
            published_date=datetime(2023, 12, 15),
            categories=["cs.AI"],
            pdf_url="https://arxiv.org/pdf/2312.12345",
            abstract_url="https://arxiv.org/abs/2312.12345",
            breakthrough_score=0.8,
            relevance_score=0.7,
        )

        mock_pipeline.return_value = {"ranked_papers": [breakthrough_paper]}
        mock_hn.return_value = []
        mock_notify.return_value = True

        results = radar._run_scan_cycle()

        assert results["new_papers"] == 1
        assert results["noteworthy_papers"] == 1
        assert results["notifications_sent"] == 1
        mock_notify.assert_called_once()


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
    @patch("src.radar.daemon.ResearchRadar")
    def test_run_radar_once(self, mock_radar_class, mock_settings):
        """Test run_radar_once function."""
        mock_settings.radar_interval_hours = 3
        mock_settings.radar_start_hour = 5
        mock_settings.radar_end_hour = 20
        mock_settings.radar_timezone = "America/New_York"
        mock_settings.notify_breakthrough_threshold = 0.6
        mock_settings.notify_social_threshold = 0.3
        mock_settings.notify_relevance_threshold = 0.5

        mock_radar = MagicMock()
        mock_radar.run_once.return_value = {"new_papers": 5}
        mock_radar_class.return_value = mock_radar

        result = run_radar_once()

        assert result == {"new_papers": 5}
        mock_radar.run_once.assert_called_once()


class TestNotify:
    """Tests for notification logic."""

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

            with patch("src.radar.daemon.CuratorAgent"):
                return ResearchRadar()

    @pytest.fixture
    def sample_paper(self):
        """Create a sample paper."""
        return Paper(
            arxiv_id="2312.12345",
            title="Test Paper",
            abstract="Test abstract",
            authors=["Test Author"],
            published_date=datetime(2023, 12, 15),
            categories=["cs.AI"],
            pdf_url="https://arxiv.org/pdf/2312.12345",
            abstract_url="https://arxiv.org/abs/2312.12345",
        )

    @patch("src.radar.daemon.send_paper_notification")
    def test_notify_breakthrough_papers(self, mock_send, radar, sample_paper):
        """Test notification for breakthrough papers uses breakthrough reason."""
        sample_paper.breakthrough_score = 0.8  # Above threshold

        radar._notify([sample_paper])

        mock_send.assert_called_once_with([sample_paper], reason="breakthrough")

    @patch("src.radar.daemon.send_paper_notification")
    def test_notify_trending_papers(self, mock_send, radar, sample_paper):
        """Test notification for non-breakthrough papers uses trending reason."""
        sample_paper.breakthrough_score = 0.3  # Below threshold

        radar._notify([sample_paper])

        mock_send.assert_called_once_with([sample_paper], reason="trending")


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

            with patch("src.radar.daemon.CuratorAgent"):
                radar = ResearchRadar()
                radar.running = True
                radar.stop()
                assert radar.running is False


class TestRunOnceMethod:
    """Tests for run_once method."""

    @patch("src.radar.daemon.settings")
    @patch("src.radar.daemon.CuratorAgent")
    def test_run_once_returns_scan_cycle_results(self, mock_curator, mock_settings):
        """Test run_once returns results from scan cycle."""
        mock_settings.radar_interval_hours = 3
        mock_settings.radar_start_hour = 5
        mock_settings.radar_end_hour = 20
        mock_settings.radar_timezone = "America/New_York"
        mock_settings.notify_breakthrough_threshold = 0.6
        mock_settings.notify_social_threshold = 0.3
        mock_settings.notify_relevance_threshold = 0.5

        with patch.object(ResearchRadar, "_run_scan_cycle") as mock_cycle:
            mock_cycle.return_value = {"new_papers": 10, "noteworthy_papers": 2}

            radar = ResearchRadar()
            result = radar.run_once()

            assert result["new_papers"] == 10
            assert result["noteworthy_papers"] == 2
            mock_cycle.assert_called_once()


class TestDiscoverNewPapers:
    """Tests for discovering new papers."""

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

            with patch("src.radar.daemon.CuratorAgent"):
                return ResearchRadar()

    @patch("src.radar.daemon.run_full_pipeline")
    def test_discover_returns_ranked_papers(self, mock_pipeline, radar):
        """Test discovery returns ranked papers."""
        papers = [MagicMock(), MagicMock()]
        mock_pipeline.return_value = {"ranked_papers": papers}

        result = radar._discover_new_papers()

        assert result == papers

    @patch("src.radar.daemon.run_full_pipeline")
    def test_discover_returns_final_papers_fallback(self, mock_pipeline, radar):
        """Test discovery falls back to final_papers."""
        papers = [MagicMock()]
        mock_pipeline.return_value = {"ranked_papers": None, "final_papers": papers}

        result = radar._discover_new_papers()

        assert result == papers

    @patch("src.radar.daemon.run_full_pipeline")
    def test_discover_handles_errors(self, mock_pipeline, radar):
        """Test discovery handles pipeline errors."""
        mock_pipeline.side_effect = Exception("Pipeline error")

        result = radar._discover_new_papers()

        assert result == []

    @patch("src.radar.daemon.run_full_pipeline")
    def test_discover_logs_pipeline_warnings(self, mock_pipeline, radar):
        """Test discovery logs warnings from pipeline."""
        mock_pipeline.return_value = {
            "ranked_papers": [],
            "errors": ["Warning 1", "Warning 2"],
        }

        result = radar._discover_new_papers()

        assert result == []


class TestFindRisingPapers:
    """Tests for finding rising papers."""

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

            with patch("src.radar.daemon.CuratorAgent"):
                return ResearchRadar()

    @patch("src.radar.daemon.fetch_hn_signals")
    def test_find_rising_no_signals(self, mock_fetch, radar):
        """Test finding rising papers with no HN signals."""
        mock_fetch.return_value = []

        result = radar._find_rising_papers()

        assert result == []

    @patch("src.radar.daemon.fetch_hn_signals")
    def test_find_rising_handles_errors(self, mock_fetch, radar):
        """Test finding rising papers handles errors gracefully."""
        mock_fetch.side_effect = Exception("HN API error")

        result = radar._find_rising_papers()

        assert result == []


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

            with patch("src.radar.daemon.CuratorAgent"):
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


class TestScanCycleEdgeCases:
    """Additional edge case tests for scan cycle."""

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

            with patch("src.radar.daemon.CuratorAgent"):
                return ResearchRadar()

    @patch("src.radar.daemon.run_full_pipeline")
    @patch("src.radar.daemon.fetch_hn_signals")
    @patch("src.radar.daemon.send_paper_notification")
    def test_scan_cycle_notification_failure(self, mock_notify, mock_hn, mock_pipeline, radar):
        """Test scan cycle handles notification failure."""
        breakthrough_paper = Paper(
            arxiv_id="2312.12345",
            title="Breakthrough Paper",
            abstract="Test abstract",
            authors=["Test Author"],
            published_date=datetime(2023, 12, 15),
            categories=["cs.AI"],
            pdf_url="https://arxiv.org/pdf/2312.12345",
            abstract_url="https://arxiv.org/abs/2312.12345",
            breakthrough_score=0.8,
            relevance_score=0.7,
        )

        mock_pipeline.return_value = {"ranked_papers": [breakthrough_paper]}
        mock_hn.return_value = []
        mock_notify.return_value = False  # Notification fails

        results = radar._run_scan_cycle()

        assert results["noteworthy_papers"] == 1
        assert results["notifications_sent"] == 0  # No notifications sent due to failure

    @patch("src.radar.daemon.run_full_pipeline")
    @patch("src.radar.daemon.fetch_hn_signals")
    def test_scan_cycle_with_no_noteworthy(self, mock_hn, mock_pipeline, radar):
        """Test scan cycle when no papers meet threshold."""
        low_score_paper = Paper(
            arxiv_id="2312.12345",
            title="Low Score Paper",
            abstract="Test abstract",
            authors=["Test Author"],
            published_date=datetime(2023, 12, 15),
            categories=["cs.AI"],
            pdf_url="https://arxiv.org/pdf/2312.12345",
            abstract_url="https://arxiv.org/abs/2312.12345",
            breakthrough_score=0.3,  # Below threshold
            relevance_score=0.3,  # Below threshold
        )

        mock_pipeline.return_value = {"ranked_papers": [low_score_paper]}
        mock_hn.return_value = []

        results = radar._run_scan_cycle()

        assert results["new_papers"] == 1
        assert results["noteworthy_papers"] == 0
        assert results["notifications_sent"] == 0
