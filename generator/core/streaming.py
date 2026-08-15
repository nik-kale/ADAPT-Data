"""Streaming writers for large dataset generation.

The default generation path buffers every record in memory before writing it
out, which does not survive long incident windows at high sample rates. The
writers here keep memory flat by flushing to disk in fixed-size batches.
"""

import json
from pathlib import Path
from types import TracebackType
from typing import Any, Iterable, Iterator, Optional


class StreamingJSONLWriter:
    """Buffered JSON Lines writer with constant memory usage.

    Records are accumulated in a small in-memory buffer and flushed to disk
    whenever the buffer fills, so peak memory depends on ``buffer_size``
    rather than on the total number of records written.

    Usable as a context manager, which guarantees a final flush::

        with StreamingJSONLWriter(path) as writer:
            for record in records:
                writer.write(record)
    """

    def __init__(self, filepath: Path, buffer_size: int = 1000) -> None:
        """Initialize the writer.

        Args:
            filepath: Destination file. Parent directories are created and any
                existing file is truncated when the writer is opened.
            buffer_size: Number of records to hold before flushing to disk.

        Raises:
            ValueError: If buffer_size is not positive.
        """
        if buffer_size < 1:
            raise ValueError(f"buffer_size must be >= 1, got {buffer_size}")

        self.filepath = Path(filepath)
        self.buffer_size = buffer_size
        self._buffer: list[dict[str, Any]] = []
        self._records_written = 0
        self._handle: Optional[Any] = None

    @property
    def records_written(self) -> int:
        """Total number of records handed to this writer."""
        return self._records_written

    def open(self) -> "StreamingJSONLWriter":
        """Open the destination file for writing.

        Returns:
            This writer, for chaining.
        """
        if self._handle is None:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            self._handle = open(self.filepath, "w")
        return self

    def write(self, record: dict[str, Any]) -> None:
        """Buffer a single record, flushing when the buffer is full.

        Args:
            record: Record to serialize as one JSON line.
        """
        if self._handle is None:
            self.open()

        self._buffer.append(record)
        self._records_written += 1

        if len(self._buffer) >= self.buffer_size:
            self.flush()

    def write_all(self, records: Iterable[dict[str, Any]]) -> int:
        """Write every record from an iterable.

        Args:
            records: Records to write. Consumed lazily, so generators never
                need to be materialized in full.

        Returns:
            Number of records written by this call.
        """
        start = self._records_written
        for record in records:
            self.write(record)
        return self._records_written - start

    def flush(self) -> None:
        """Write any buffered records to disk and clear the buffer."""
        if not self._buffer:
            return

        if self._handle is None:
            self.open()

        assert self._handle is not None  # narrowed by open()
        for record in self._buffer:
            self._handle.write(json.dumps(record, default=str) + "\n")
        self._handle.flush()
        self._buffer.clear()

    def close(self) -> None:
        """Flush remaining records and close the file."""
        self.flush()
        if self._handle is not None:
            self._handle.close()
            self._handle = None

    def __enter__(self) -> "StreamingJSONLWriter":
        """Enter the context manager, opening the destination file."""
        return self.open()

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        """Flush and close on context exit, including on error."""
        self.close()


def stream_jsonl(filepath: Path) -> Iterator[dict[str, Any]]:
    """Read a JSON Lines file one record at a time.

    The counterpart to :class:`StreamingJSONLWriter` for the read path: large
    datasets can be consumed without loading the whole file into memory.

    Args:
        filepath: Path to the JSONL file.

    Yields:
        Each parsed record, skipping blank lines.
    """
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def estimate_record_count(
    duration_minutes: float,
    step_seconds: float,
    hosts: int = 1,
    series_per_sample: int = 1,
) -> int:
    """Estimate how many records a generation run will produce.

    Used to warn about very large datasets before generation starts.

    Args:
        duration_minutes: Length of the generation window in minutes.
        step_seconds: Seconds between samples.
        hosts: Number of hosts sampled at each step.
        series_per_sample: Records emitted per host per step.

    Returns:
        Estimated total record count.

    Raises:
        ValueError: If step_seconds is not positive.
    """
    if step_seconds <= 0:
        raise ValueError(f"step_seconds must be > 0, got {step_seconds}")

    steps = int((duration_minutes * 60) / step_seconds)
    return max(0, steps) * max(0, hosts) * max(0, series_per_sample)
