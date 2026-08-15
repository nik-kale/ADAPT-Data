"""Tests for streaming JSONL writers."""

import json

import pytest

from generator.core.streaming import (
    StreamingJSONLWriter,
    estimate_record_count,
    stream_jsonl,
)


class TestStreamingJSONLWriter:
    """Test buffered JSONL writing."""

    def test_writes_all_records(self, tmp_path):
        """Every record reaches disk, one JSON object per line."""
        target = tmp_path / "out.jsonl"

        with StreamingJSONLWriter(target) as writer:
            for i in range(250):
                writer.write({"index": i})

        lines = target.read_text().strip().split("\n")
        assert len(lines) == 250
        assert json.loads(lines[0]) == {"index": 0}
        assert json.loads(lines[-1]) == {"index": 249}

    def test_flushes_when_buffer_fills(self, tmp_path):
        """Records land on disk before close once the buffer is full."""
        target = tmp_path / "out.jsonl"
        writer = StreamingJSONLWriter(target, buffer_size=10)

        for i in range(10):
            writer.write({"index": i})

        # Buffer hit its limit and flushed without an explicit close.
        assert len(target.read_text().strip().split("\n")) == 10
        writer.close()

    def test_buffer_holds_records_until_full(self, tmp_path):
        """Nothing is written while the buffer is still filling."""
        target = tmp_path / "out.jsonl"
        writer = StreamingJSONLWriter(target, buffer_size=100)

        for i in range(5):
            writer.write({"index": i})

        assert target.read_text() == ""

        writer.close()
        assert len(target.read_text().strip().split("\n")) == 5

    def test_close_flushes_partial_buffer(self, tmp_path):
        """A partly-filled buffer is still written on close."""
        target = tmp_path / "out.jsonl"
        writer = StreamingJSONLWriter(target, buffer_size=1000)
        writer.write({"only": True})
        writer.close()

        assert json.loads(target.read_text().strip()) == {"only": True}

    def test_context_manager_flushes_on_exception(self, tmp_path):
        """Buffered records survive an error inside the context block."""
        target = tmp_path / "out.jsonl"

        with pytest.raises(RuntimeError):
            with StreamingJSONLWriter(target, buffer_size=1000) as writer:
                writer.write({"index": 0})
                raise RuntimeError("boom")

        assert json.loads(target.read_text().strip()) == {"index": 0}

    def test_write_all_consumes_generator_lazily(self, tmp_path):
        """A generator can be written without being materialized."""
        target = tmp_path / "out.jsonl"

        def records():
            for i in range(500):
                yield {"index": i}

        with StreamingJSONLWriter(target, buffer_size=50) as writer:
            written = writer.write_all(records())

        assert written == 500
        assert len(target.read_text().strip().split("\n")) == 500

    def test_records_written_counter(self, tmp_path):
        """The counter tracks every record handed to the writer."""
        target = tmp_path / "out.jsonl"

        with StreamingJSONLWriter(target, buffer_size=10) as writer:
            for i in range(37):
                writer.write({"index": i})
            assert writer.records_written == 37

    def test_creates_parent_directories(self, tmp_path):
        """Missing parent directories are created."""
        target = tmp_path / "nested" / "deeper" / "out.jsonl"

        with StreamingJSONLWriter(target) as writer:
            writer.write({"ok": True})

        assert target.exists()

    def test_truncates_existing_file(self, tmp_path):
        """Opening replaces prior content rather than appending."""
        target = tmp_path / "out.jsonl"
        target.write_text('{"stale": true}\n')

        with StreamingJSONLWriter(target) as writer:
            writer.write({"fresh": True})

        assert json.loads(target.read_text().strip()) == {"fresh": True}

    def test_serializes_non_json_types(self, tmp_path):
        """Values json cannot encode natively fall back to str()."""
        from datetime import datetime

        target = tmp_path / "out.jsonl"
        with StreamingJSONLWriter(target) as writer:
            writer.write({"when": datetime(2025, 1, 15, 10, 0, 0)})

        assert json.loads(target.read_text().strip())["when"] == "2025-01-15 10:00:00"

    def test_rejects_invalid_buffer_size(self, tmp_path):
        """A non-positive buffer size is rejected up front."""
        with pytest.raises(ValueError, match="buffer_size"):
            StreamingJSONLWriter(tmp_path / "out.jsonl", buffer_size=0)


class TestStreamJsonl:
    """Test the streaming read path."""

    def test_reads_records(self, tmp_path):
        """Records round-trip through write and read."""
        target = tmp_path / "out.jsonl"
        with StreamingJSONLWriter(target) as writer:
            writer.write_all({"index": i} for i in range(20))

        assert [r["index"] for r in stream_jsonl(target)] == list(range(20))

    def test_skips_blank_lines(self, tmp_path):
        """Blank lines are ignored rather than raising."""
        target = tmp_path / "out.jsonl"
        target.write_text('{"a": 1}\n\n\n{"a": 2}\n')

        assert [r["a"] for r in stream_jsonl(target)] == [1, 2]


class TestEstimateRecordCount:
    """Test dataset size estimation."""

    def test_basic_estimate(self):
        """60 minutes at one sample per minute is 60 records."""
        assert estimate_record_count(60, step_seconds=60) == 60

    def test_scales_with_hosts_and_series(self):
        """Hosts and series per sample multiply the total."""
        assert estimate_record_count(60, step_seconds=60, hosts=3, series_per_sample=5) == 900

    def test_rejects_non_positive_step(self):
        """A zero step would divide by zero, so it is rejected."""
        with pytest.raises(ValueError, match="step_seconds"):
            estimate_record_count(60, step_seconds=0)
