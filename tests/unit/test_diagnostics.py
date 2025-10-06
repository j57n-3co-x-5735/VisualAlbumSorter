"""Tests for visualalbumsorter.utils.diagnostics."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

# Add project root for direct imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from visualalbumsorter.utils.diagnostics import DiagnosticsTracker, PhotoStats, ProcessingEvent


class TestPhotoStats:
    def test_completion_percentage_defaults_and_progress(self):
        stats = PhotoStats()
        assert stats.get_completion_percentage() == 100.0

        stats.total_in_library = 100
        stats.previously_processed = 20
        stats.processed_this_session = 30
        assert stats.get_completion_percentage() == 50.0

        stats.previously_processed = 80
        stats.processed_this_session = 30
        assert stats.get_completion_percentage() == pytest.approx(110.0)

    def test_average_processing_time(self):
        stats = PhotoStats()
        assert stats.get_average_processing_time() == 0.0

        stats.processing_times = [1.0, 2.0, 5.0]
        assert stats.get_average_processing_time() == pytest.approx(8.0 / 3)

    def test_session_summary_strings(self):
        stats = PhotoStats(
            total_in_library=200,
            previously_processed=50,
            to_process=150,
            processed_this_session=20,
            matched_this_session=5,
            errors_this_session=1,
            skipped_this_session=2,
            processing_times=[1.5, 2.0]
        )

        summary = stats.get_session_summary()
        assert summary["photos_in_library"] == 200
        assert summary["previously_processed"] == 50
        assert summary["processed_this_session"] == 20
        assert summary["completion_percentage"] == "35.0%"
        assert summary["average_time_per_photo"].endswith("s")


class TestProcessingEvent:
    def test_optional_fields_default_to_none_or_empty(self):
        event = ProcessingEvent(event_type="error", timestamp=datetime.now())
        assert event.photo_uuid is None
        assert event.batch_number is None
        assert event.details == {}


class TestDiagnosticsTracker:
    @pytest.fixture
    def tracker(self, tmp_path):
        config = MagicMock()
        config.storage.temp_dir = tmp_path
        config.task.name = "Test Task"
        return DiagnosticsTracker(config)

    def test_initial_state(self, tracker, tmp_path):
        assert tracker.start_time is None
        assert tracker.events == []
        assert tracker.log_dir.exists()
        assert tracker.diagnostic_file.parent == tracker.log_dir

    def test_start_processing_records_event(self, tracker):
        tracker.start_processing(40, {"a", "b"})
        assert tracker.stats.total_in_library == 40
        assert tracker.stats.previously_processed == 2
        assert tracker.events[0].details == {
            "total_photos": 40,
            "previously_processed": 2,
            "to_process": 38,
        }

    def test_record_photo_processed_updates_stats(self, tracker):
        tracker.start_processing(10, set())
        tracker.record_photo_processed("uuid", "yes", 1.2, batch_num=1)

        assert tracker.stats.processed_this_session == 1
        assert tracker.stats.matched_this_session == 1
        assert tracker.stats.processing_times == [1.2]
        assert tracker.events[-1].event_type == "photo_processed"

    def test_record_batch_complete_uses_batch_number(self, tracker):
        tracker.start_processing(5, set())
        tracker.record_batch_complete(2, 5, ["u1", "u2"])

        event = tracker.events[-1]
        assert event.batch_number == 2
        assert event.details["batch_size"] == 5
        assert event.details["matches_in_batch"] == 2

    def test_snapshot_contains_stats_and_events(self, tracker):
        tracker.start_processing(5, set())
        tracker.record_photo_processed("uuid", "no", 0.5, 1)
        tracker._save_diagnostic_snapshot()

        data = json.loads(tracker.diagnostic_file.read_text())
        assert "stats" in data
        assert "events" in data
        assert data["events"][0]["event_type"] == "start"

    def test_get_current_status_reports_progress(self, tracker):
        tracker.start_processing(100, set())
        tracker.stats.processed_this_session = 10

        status = tracker.get_current_status()
        assert status["is_processing"] is True
        assert status["current_stats"]["processed_this_session"] == 10
        assert status["session_progress"].endswith("%")

    def test_log_progress_emits_logger_messages(self, tracker):
        tracker.start_processing(20, set())
        with patch("visualalbumsorter.utils.diagnostics.logger.info") as mock_info:
            tracker._log_progress()
        assert mock_info.called

    def test_generate_final_report_logs_summary(self, tracker):
        tracker.start_processing(10, {"u"})
        tracker.stats.processed_this_session = 3
        tracker.end_time = tracker.start_time + timedelta(seconds=10)

        with patch("visualalbumsorter.utils.diagnostics.logger.info") as mock_info:
            tracker._generate_final_report()
        assert mock_info.called

    def test_error_recovery_propagates_filesystem_errors(self, tmp_path):
        config = MagicMock()
        config.storage.temp_dir = tmp_path
        config.task.name = "Test"

        with patch("pathlib.Path.mkdir", side_effect=PermissionError("RO")):
            with pytest.raises(PermissionError):
                DiagnosticsTracker(config)
