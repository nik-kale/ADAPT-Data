"""Progress indicators for ADAPT-Data operations.

This module provides progress tracking using the rich library for
better user experience during long-running operations.
"""

from contextlib import contextmanager
from typing import Optional

try:
    from rich.progress import (
        Progress,
        SpinnerColumn,
        TextColumn,
        BarColumn,
        TaskProgressColumn,
        TimeRemainingColumn,
        TimeElapsedColumn,
    )
    from rich.console import Console
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from generator.core.logging_config import get_logger

logger = get_logger(__name__)


class ProgressTracker:
    """Tracks progress of generation operations.

    Falls back to logging if rich is not available.
    """

    def __init__(self, enabled: bool = True) -> None:
        """Initialize progress tracker.

        Args:
            enabled: Whether to show progress (auto-disabled if rich unavailable)
        """
        self.enabled = enabled and RICH_AVAILABLE
        self.progress: Optional[Progress] = None
        self.console: Optional[Console] = None

        if self.enabled:
            self.console = Console()
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
                console=self.console,
            )

    @contextmanager
    def track(self, description: str, total: Optional[int] = None):
        """Context manager for tracking a task.

        Args:
            description: Task description
            total: Total number of steps (None for indeterminate)

        Yields:
            Task ID for updating progress
        """
        if not self.enabled or self.progress is None:
            # Fallback to logging
            logger.info(f"Starting: {description}")
            yield None
            logger.info(f"Completed: {description}")
            return

        with self.progress:
            task_id = self.progress.add_task(description, total=total)
            try:
                yield task_id
            finally:
                if not self.progress.tasks[task_id].finished:
                    self.progress.update(task_id, completed=total or 1)

    def update(self, task_id: Optional[int], advance: int = 1, description: Optional[str] = None) -> None:
        """Update task progress.

        Args:
            task_id: Task ID (from track context manager)
            advance: Number of steps to advance
            description: Optional new description
        """
        if not self.enabled or task_id is None or self.progress is None:
            if description:
                logger.debug(description)
            return

        kwargs = {"advance": advance}
        if description:
            kwargs["description"] = description

        self.progress.update(task_id, **kwargs)

    def log(self, message: str, style: str = "bold") -> None:
        """Log a message to console.

        Args:
            message: Message to log
            style: Rich style to apply
        """
        if self.console:
            self.console.print(message, style=style)
        else:
            logger.info(message)


# Global progress tracker instance
_tracker: Optional[ProgressTracker] = None


def get_progress_tracker(enabled: bool = True) -> ProgressTracker:
    """Get global progress tracker instance.

    Args:
        enabled: Whether progress should be enabled

    Returns:
        Progress tracker instance
    """
    global _tracker
    if _tracker is None:
        _tracker = ProgressTracker(enabled=enabled)
    return _tracker


def disable_progress() -> None:
    """Disable progress tracking globally."""
    global _tracker
    if _tracker is not None:
        _tracker.enabled = False
