"""Streaming output writers for large-scale data generation.

This module provides memory-efficient streaming writers that enable
generation of datasets with millions of records without memory exhaustion.
Records are written to disk incrementally as they're generated, maintaining
constant memory usage regardless of dataset size.
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class StreamingJSONLWriter:
    """Memory-efficient JSONL writer with buffered I/O.

    Writes JSON Lines records directly to disk with configurable buffering.
    Records are accumulated in memory until buffer size is reached, then
    flushed to disk, keeping memory usage bounded.

    Example:
        ```python
        writer = StreamingJSONLWriter("output/metrics.jsonl", buffer_size=1000)
        for i in range(1_000_000):
            writer.write({"id": i, "value": i * 2})
        writer.close()  # Final flush
        ```

    Attributes:
        filepath: Output file path
        buffer_size: Number of records to buffer before flushing
        records_written: Total count of records written
        is_closed: Whether writer has been closed
    """

    def __init__(
        self,
        filepath: Path,
        buffer_size: int = 1000,
        mode: str = 'w'
    ) -> None:
        """Initialize streaming writer.

        Args:
            filepath: Path to output JSONL file
            buffer_size: Records to buffer before flush (default: 1000)
            mode: File mode ('w' for write, 'a' for append)

        Raises:
            ValueError: If buffer_size is not positive
        """
        if buffer_size <= 0:
            raise ValueError(f"buffer_size must be positive, got {buffer_size}")

        self.filepath = Path(filepath)
        self.buffer_size = buffer_size
        self.buffer: list[dict[str, Any]] = []
        self.records_written = 0
        self.is_closed = False
        self._file_handle: Optional[Any] = None

        # Ensure parent directory exists
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

        # Open file handle
        self._file_handle = open(self.filepath, mode, buffering=8192)
        logger.debug(f"Opened streaming writer to {self.filepath} with buffer size {buffer_size}")

    def write(self, record: dict[str, Any]) -> None:
        """Write a single record to the buffer.

        Record will be flushed to disk when buffer reaches buffer_size.

        Args:
            record: Dictionary to write as JSON Line

        Raises:
            ValueError: If writer is closed
            TypeError: If record is not serializable
        """
        if self.is_closed:
            raise ValueError("Cannot write to closed StreamingJSONLWriter")

        self.buffer.append(record)
        if len(self.buffer) >= self.buffer_size:
            self.flush()

    def flush(self) -> None:
        """Flush buffered records to disk.

        Writes all buffered records as JSON Lines and clears buffer.
        Can be called manually to force immediate write.

        Raises:
            ValueError: If writer is closed
        """
        if self.is_closed:
            raise ValueError("Cannot flush closed StreamingJSONLWriter")

        if not self.buffer:
            return

        if self._file_handle is None:
            raise RuntimeError("File handle is not initialized")

        for record in self.buffer:
            json_line = json.dumps(record, default=str) + '\n'
            self._file_handle.write(json_line)

        self.records_written += len(self.buffer)
        logger.debug(f"Flushed {len(self.buffer)} records to {self.filepath} (total: {self.records_written})")
        self.buffer.clear()

    def close(self) -> None:
        """Close the writer and flush remaining records.

        Ensures all buffered records are written to disk and file handle
        is properly closed. Safe to call multiple times.
        """
        if self.is_closed:
            return

        # Flush remaining buffer
        if self.buffer:
            self.flush()

        # Close file handle
        if self._file_handle is not None:
            self._file_handle.close()
            self._file_handle = None

        self.is_closed = True
        logger.info(f"Closed streaming writer. Total records written: {self.records_written}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures writer is closed."""
        self.close()

    def __del__(self):
        """Destructor - ensures file handle is closed."""
        if not self.is_closed:
            try:
                self.close()
            except Exception as e:
                logger.warning(f"Error closing StreamingJSONLWriter in destructor: {e}")


def estimate_memory_usage(
    num_records: int,
    avg_record_size_bytes: int = 500,
    buffer_size: int = 1000
) -> dict[str, Any]:
    """Estimate memory usage for streaming vs non-streaming generation.

    Args:
        num_records: Total number of records to generate
        avg_record_size_bytes: Average size per record in bytes
        buffer_size: Buffer size for streaming writer

    Returns:
        Dictionary with memory estimates:
        {
            "total_dataset_size_mb": float,
            "streaming_memory_mb": float,
            "non_streaming_memory_mb": float,
            "memory_reduction_factor": float,
            "recommended_mode": str
        }
    """
    total_size_bytes = num_records * avg_record_size_bytes
    total_size_mb = total_size_bytes / (1024 * 1024)

    # Streaming uses only buffer + overhead
    streaming_mb = (buffer_size * avg_record_size_bytes) / (1024 * 1024)
    streaming_mb += 10  # Add overhead for generator state, etc.

    # Non-streaming holds entire dataset in memory
    non_streaming_mb = total_size_mb + 10

    reduction = non_streaming_mb / streaming_mb if streaming_mb > 0 else 1.0

    # Recommend streaming if dataset > 100MB
    recommended = "streaming" if total_size_mb > 100 else "standard"

    return {
        "total_dataset_size_mb": round(total_size_mb, 2),
        "streaming_memory_mb": round(streaming_mb, 2),
        "non_streaming_memory_mb": round(non_streaming_mb, 2),
        "memory_reduction_factor": round(reduction, 2),
        "recommended_mode": recommended,
        "num_records": num_records,
        "buffer_size": buffer_size
    }

