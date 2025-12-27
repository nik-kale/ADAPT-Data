"""Unit tests for streaming JSON writer."""

import json
import tempfile
from pathlib import Path

import pytest

from generator.core.streaming import (
    StreamingJSONLWriter,
    estimate_memory_usage,
)


class TestStreamingJSONLWriter:
    """Tests for StreamingJSONLWriter."""

    def test_write_single_record(self):
        """Test writing a single record."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.jsonl"
            
            with StreamingJSONLWriter(filepath, buffer_size=10) as writer:
                writer.write({"id": 1, "value": "test"})
            
            # Verify file contents
            with open(filepath, 'r') as f:
                lines = f.readlines()
            
            assert len(lines) == 1
            data = json.loads(lines[0])
            assert data == {"id": 1, "value": "test"}

    def test_write_multiple_records(self):
        """Test writing multiple records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.jsonl"
            
            with StreamingJSONLWriter(filepath, buffer_size=10) as writer:
                for i in range(100):
                    writer.write({"id": i, "value": i * 2})
            
            # Verify file contents
            with open(filepath, 'r') as f:
                lines = f.readlines()
            
            assert len(lines) == 100
            
            # Check first and last records
            first = json.loads(lines[0])
            assert first == {"id": 0, "value": 0}
            
            last = json.loads(lines[-1])
            assert last == {"id": 99, "value": 198}

    def test_buffering_behavior(self):
        """Test that buffering works correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.jsonl"
            
            writer = StreamingJSONLWriter(filepath, buffer_size=5)
            
            # Write 3 records - should not flush yet
            for i in range(3):
                writer.write({"id": i})
            
            assert len(writer.buffer) == 3
            assert writer.records_written == 0
            
            # Write 2 more - should trigger flush
            for i in range(3, 5):
                writer.write({"id": i})
            
            assert len(writer.buffer) == 0
            assert writer.records_written == 5
            
            writer.close()
            
            # Verify file contents
            with open(filepath, 'r') as f:
                lines = f.readlines()
            assert len(lines) == 5

    def test_manual_flush(self):
        """Test manual flush."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.jsonl"
            
            writer = StreamingJSONLWriter(filepath, buffer_size=100)
            
            # Write 10 records (buffer size is 100, so won't auto-flush)
            for i in range(10):
                writer.write({"id": i})
            
            assert len(writer.buffer) == 10
            assert writer.records_written == 0
            
            # Manual flush
            writer.flush()
            
            assert len(writer.buffer) == 0
            assert writer.records_written == 10
            
            writer.close()

    def test_context_manager(self):
        """Test context manager ensures proper closure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.jsonl"
            
            with StreamingJSONLWriter(filepath, buffer_size=10) as writer:
                for i in range(15):
                    writer.write({"id": i})
            
            # Writer should be closed and flushed
            assert writer.is_closed
            assert writer.records_written == 15
            
            # Verify file contents
            with open(filepath, 'r') as f:
                lines = f.readlines()
            assert len(lines) == 15

    def test_write_after_close_raises_error(self):
        """Test that writing after close raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.jsonl"
            
            writer = StreamingJSONLWriter(filepath)
            writer.close()
            
            with pytest.raises(ValueError, match="Cannot write to closed"):
                writer.write({"id": 1})

    def test_invalid_buffer_size(self):
        """Test that invalid buffer size raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.jsonl"
            
            with pytest.raises(ValueError, match="buffer_size must be positive"):
                StreamingJSONLWriter(filepath, buffer_size=0)
            
            with pytest.raises(ValueError, match="buffer_size must be positive"):
                StreamingJSONLWriter(filepath, buffer_size=-10)

    def test_special_characters_and_unicode(self):
        """Test writing records with special characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.jsonl"
            
            with StreamingJSONLWriter(filepath) as writer:
                writer.write({"text": "Hello 世界! 🌍"})
                writer.write({"special": "quotes \"test\" and\nnewlines"})
            
            # Verify file contents
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            assert len(lines) == 2
            data1 = json.loads(lines[0])
            assert data1["text"] == "Hello 世界! 🌍"
            
            data2 = json.loads(lines[1])
            assert "quotes" in data2["special"]


class TestEstimateMemoryUsage:
    """Tests for memory usage estimation."""

    def test_basic_estimation(self):
        """Test basic memory estimation."""
        result = estimate_memory_usage(
            num_records=1000,
            avg_record_size_bytes=500,
            buffer_size=1000
        )
        
        assert "total_dataset_size_mb" in result
        assert "streaming_memory_mb" in result
        assert "non_streaming_memory_mb" in result
        assert "memory_reduction_factor" in result
        assert "recommended_mode" in result
        
        # Verify streaming uses less memory
        assert result["streaming_memory_mb"] < result["non_streaming_memory_mb"]

    def test_large_dataset_recommendation(self):
        """Test that large datasets recommend streaming."""
        result = estimate_memory_usage(
            num_records=1_000_000,  # 1M records
            avg_record_size_bytes=500,
            buffer_size=1000
        )
        
        assert result["recommended_mode"] == "streaming"
        assert result["total_dataset_size_mb"] > 100

    def test_small_dataset_recommendation(self):
        """Test that small datasets recommend standard mode."""
        result = estimate_memory_usage(
            num_records=1000,
            avg_record_size_bytes=100,
            buffer_size=100
        )
        
        assert result["recommended_mode"] == "standard"
        assert result["total_dataset_size_mb"] < 100

    def test_memory_reduction_factor(self):
        """Test that memory reduction factor is calculated correctly."""
        result = estimate_memory_usage(
            num_records=10_000,
            avg_record_size_bytes=1000,
            buffer_size=100
        )
        
        # Reduction factor should be > 1 (streaming uses less)
        assert result["memory_reduction_factor"] > 1

