"""Unit tests for progress tracking system."""

from unittest.mock import Mock, patch, MagicMock

import pytest

from generator.core.progress import (
    ProgressTracker,
    get_progress_tracker,
    disable_progress,
    RICH_AVAILABLE,
)


class TestProgressTrackerInitialization:
    """Test ProgressTracker initialization."""

    def test_init_enabled_with_rich(self):
        """Test initialization when rich is available."""
        if not RICH_AVAILABLE:
            pytest.skip("Rich not available")

        tracker = ProgressTracker(enabled=True)

        assert tracker.enabled is True
        assert tracker.progress is not None
        assert tracker.console is not None

    def test_init_disabled(self):
        """Test initialization when disabled."""
        tracker = ProgressTracker(enabled=False)

        assert tracker.enabled is False

    def test_init_without_rich(self):
        """Test initialization when rich unavailable."""
        with patch("generator.core.progress.RICH_AVAILABLE", False):
            tracker = ProgressTracker(enabled=True)

            # Should be disabled even if requested
            assert tracker.enabled is False
            assert tracker.progress is None
            assert tracker.console is None


class TestProgressTrackerTrackContextManager:
    """Test track() context manager."""

    def test_track_context_manager_disabled(self):
        """Test track() when progress disabled."""
        tracker = ProgressTracker(enabled=False)

        with tracker.track("Test task", total=10) as task_id:
            # Should yield None when disabled
            assert task_id is None

    def test_track_context_manager_with_rich(self):
        """Test track() when rich available."""
        if not RICH_AVAILABLE:
            pytest.skip("Rich not available")

        tracker = ProgressTracker(enabled=True)

        with tracker.track("Test task", total=100) as task_id:
            # Should yield valid task ID
            assert task_id is not None
            assert isinstance(task_id, int)

    def test_track_context_manager_indeterminate(self):
        """Test track() with indeterminate progress (no total)."""
        if not RICH_AVAILABLE:
            pytest.skip("Rich not available")

        tracker = ProgressTracker(enabled=True)

        with tracker.track("Indeterminate task", total=None) as task_id:
            assert task_id is not None

    def test_track_completes_task_on_exit(self):
        """Test track() marks task complete on exit."""
        if not RICH_AVAILABLE:
            pytest.skip("Rich not available")

        tracker = ProgressTracker(enabled=True)

        with tracker.track("Test task", total=10) as task_id:
            pass  # Do nothing

        # After exiting, task should be completed
        # We can't directly test task completion without accessing internals,
        # but we verify no exceptions are raised

    def test_track_handles_exception(self):
        """Test track() handles exceptions properly."""
        if not RICH_AVAILABLE:
            pytest.skip("Rich not available")

        tracker = ProgressTracker(enabled=True)

        with pytest.raises(ValueError):
            with tracker.track("Test task", total=10) as task_id:
                raise ValueError("Test error")

        # Should still complete properly despite exception


class TestProgressTrackerUpdate:
    """Test update() method."""

    def test_update_when_disabled(self):
        """Test update() when progress disabled."""
        tracker = ProgressTracker(enabled=False)

        # Should not crash
        tracker.update(None, advance=1)
        tracker.update(None, advance=5, description="Updated")

    def test_update_with_none_task_id(self):
        """Test update() with None task_id."""
        if not RICH_AVAILABLE:
            pytest.skip("Rich not available")

        tracker = ProgressTracker(enabled=True)

        # Should not crash with None task_id
        tracker.update(None, advance=1)

    def test_update_advances_progress(self):
        """Test update() advances progress."""
        if not RICH_AVAILABLE:
            pytest.skip("Rich not available")

        tracker = ProgressTracker(enabled=True)

        with tracker.track("Test task", total=10) as task_id:
            # Should not crash
            tracker.update(task_id, advance=1)
            tracker.update(task_id, advance=2)

    def test_update_with_description(self):
        """Test update() with description change."""
        if not RICH_AVAILABLE:
            pytest.skip("Rich not available")

        tracker = ProgressTracker(enabled=True)

        with tracker.track("Test task", total=10) as task_id:
            tracker.update(task_id, advance=1, description="Step 1")
            tracker.update(task_id, advance=1, description="Step 2")


class TestProgressTrackerLog:
    """Test log() method."""

    def test_log_with_console(self):
        """Test log() when console available."""
        if not RICH_AVAILABLE:
            pytest.skip("Rich not available")

        tracker = ProgressTracker(enabled=True)

        # Should not crash
        tracker.log("Test message")
        tracker.log("Bold message", style="bold")

    def test_log_without_console(self):
        """Test log() when console unavailable."""
        tracker = ProgressTracker(enabled=False)

        # Should not crash, falls back to logging
        tracker.log("Test message")


class TestGracefulDegradation:
    """Test graceful degradation when rich unavailable."""

    def test_tracker_works_without_rich(self):
        """Test ProgressTracker works when rich unavailable."""
        with patch("generator.core.progress.RICH_AVAILABLE", False):
            tracker = ProgressTracker(enabled=True)

            # Should be disabled
            assert tracker.enabled is False

            # All operations should work without crashing
            with tracker.track("Test task", total=10) as task_id:
                assert task_id is None
                tracker.update(task_id, advance=1)

            tracker.log("Test message")

    def test_update_doesnt_crash_without_rich(self):
        """Test update() doesn't crash when rich unavailable."""
        with patch("generator.core.progress.RICH_AVAILABLE", False):
            tracker = ProgressTracker(enabled=True)

            # Should not crash
            tracker.update(None, advance=1)
            tracker.update(None, advance=1, description="Test")

    def test_log_doesnt_crash_without_rich(self):
        """Test log() doesn't crash when rich unavailable."""
        with patch("generator.core.progress.RICH_AVAILABLE", False):
            tracker = ProgressTracker(enabled=True)

            # Should not crash
            tracker.log("Test message")
            tracker.log("Test message", style="bold")


class TestGlobalProgressTracker:
    """Test global progress tracker functions."""

    def test_get_progress_tracker_singleton(self):
        """Test get_progress_tracker returns singleton."""
        # Reset global tracker
        import generator.core.progress
        generator.core.progress._tracker = None

        tracker1 = get_progress_tracker(enabled=True)
        tracker2 = get_progress_tracker(enabled=True)

        # Should be same instance
        assert tracker1 is tracker2

    def test_disable_progress(self):
        """Test disable_progress() function."""
        # Reset and create tracker
        import generator.core.progress
        generator.core.progress._tracker = None

        tracker = get_progress_tracker(enabled=True)
        initial_state = tracker.enabled

        disable_progress()

        # Should be disabled
        assert tracker.enabled is False

    def test_get_progress_tracker_respects_enabled_param(self):
        """Test get_progress_tracker respects enabled parameter."""
        # Reset global tracker
        import generator.core.progress
        generator.core.progress._tracker = None

        tracker = get_progress_tracker(enabled=False)

        assert tracker.enabled is False


class TestProgressTrackerEdgeCases:
    """Test edge cases and error handling."""

    def test_multiple_track_contexts_nested(self):
        """Test nested track() contexts."""
        if not RICH_AVAILABLE:
            pytest.skip("Rich not available")

        tracker = ProgressTracker(enabled=True)

        # Nested contexts should work
        with tracker.track("Outer task", total=10) as outer_id:
            with tracker.track("Inner task", total=5) as inner_id:
                assert outer_id != inner_id
                tracker.update(inner_id, advance=1)

            tracker.update(outer_id, advance=1)

    def test_track_with_zero_total(self):
        """Test track() with zero total."""
        if not RICH_AVAILABLE:
            pytest.skip("Rich not available")

        tracker = ProgressTracker(enabled=True)

        # Should handle zero total
        with tracker.track("Zero task", total=0) as task_id:
            assert task_id is not None

    def test_update_advance_zero(self):
        """Test update() with advance=0."""
        if not RICH_AVAILABLE:
            pytest.skip("Rich not available")

        tracker = ProgressTracker(enabled=True)

        with tracker.track("Test task", total=10) as task_id:
            # Should not crash
            tracker.update(task_id, advance=0)
