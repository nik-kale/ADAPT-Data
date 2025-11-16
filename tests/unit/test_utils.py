"""Unit tests for utility functions."""

from datetime import datetime, timedelta

import pytest

from generator.core.utils import (
    generate_id,
    generate_uuid,
    timestamp_to_iso,
    parse_duration,
    jitter,
    exponential_backoff,
    spike_pattern,
)


class TestIDGeneration:
    """Test ID generation utilities."""

    def test_generate_id_without_prefix(self):
        """Test ID generation without prefix."""
        id1 = generate_id()
        id2 = generate_id()

        assert len(id1) == 16
        assert len(id2) == 16
        assert id1 != id2  # Should be unique

    def test_generate_id_with_prefix(self):
        """Test ID generation with prefix."""
        id_val = generate_id(prefix="test-", length=8)

        assert id_val.startswith("test-")
        assert len(id_val) == 13  # 5 (prefix) + 8 (random)

    def test_generate_uuid_format(self):
        """Test UUID generation format."""
        uuid_val = generate_uuid()

        # Should be valid UUID format
        assert len(uuid_val) == 36
        assert uuid_val.count('-') == 4


class TestTimeUtilities:
    """Test time-related utilities."""

    def test_timestamp_to_iso(self):
        """Test ISO 8601 timestamp conversion."""
        dt = datetime(2025, 1, 15, 10, 30, 45, 123456)
        iso = timestamp_to_iso(dt)

        assert iso == "2025-01-15T10:30:45.123456Z"
        assert iso.endswith('Z')

    def test_parse_duration_seconds(self):
        """Test parsing seconds duration."""
        td = parse_duration("30s")
        assert td == timedelta(seconds=30)

    def test_parse_duration_minutes(self):
        """Test parsing minutes duration."""
        td = parse_duration("45m")
        assert td == timedelta(minutes=45)

    def test_parse_duration_hours(self):
        """Test parsing hours duration."""
        td = parse_duration("2h")
        assert td == timedelta(hours=2)

    def test_parse_duration_days(self):
        """Test parsing days duration."""
        td = parse_duration("3d")
        assert td == timedelta(days=3)

    def test_parse_duration_invalid_unit(self):
        """Test parsing with invalid unit."""
        with pytest.raises(ValueError):
            parse_duration("10x")


class TestJitterAndNoise:
    """Test jitter and noise functions."""

    def test_jitter_adds_variance(self):
        """Test that jitter adds variance to value."""
        base = 100.0
        results = [jitter(base, 0.1) for _ in range(100)]

        # Should have variance
        assert min(results) < base
        assert max(results) > base

        # Should be within bounds (90-110 for 10% jitter)
        assert all(85 <= r <= 115 for r in results)

    def test_jitter_zero_percent(self):
        """Test jitter with 0% variance."""
        base = 100.0
        result = jitter(base, 0.0)
        assert result == base

    def test_exponential_backoff_increases(self):
        """Test exponential backoff increases."""
        base = 1.0

        v0 = exponential_backoff(base, 0)
        v1 = exponential_backoff(base, 1)
        v2 = exponential_backoff(base, 2)
        v3 = exponential_backoff(base, 3)

        # Should generally increase (with jitter it might vary slightly)
        assert v0 < v1 < v2 < v3

    def test_exponential_backoff_respects_max(self):
        """Test exponential backoff respects max value."""
        base = 1.0
        max_val = 10.0

        # Even at high iterations, should not exceed max
        for i in range(20):
            val = exponential_backoff(base, i, max_value=max_val)
            assert val <= max_val * 1.3  # Allow for jitter


class TestSpikePattern:
    """Test spike pattern generation."""

    def test_spike_during_incident(self):
        """Test spike is elevated during incident."""
        baseline = 50.0
        multiplier = 10.0
        start = datetime(2025, 1, 15, 10, 0, 0)
        duration = timedelta(minutes=30)

        # During incident (middle)
        during = start + timedelta(minutes=15)
        value = spike_pattern(baseline, multiplier, during, start, duration)

        # Should be significantly elevated
        assert value > baseline * 5

    def test_spike_before_incident(self):
        """Test value is baseline before incident."""
        baseline = 50.0
        multiplier = 10.0
        start = datetime(2025, 1, 15, 10, 0, 0)
        duration = timedelta(minutes=30)

        # Before incident
        before = start - timedelta(minutes=10)
        value = spike_pattern(baseline, multiplier, before, start, duration)

        assert value == baseline

    def test_spike_after_incident(self):
        """Test value returns to baseline after incident."""
        baseline = 50.0
        multiplier = 10.0
        start = datetime(2025, 1, 15, 10, 0, 0)
        duration = timedelta(minutes=30)

        # After incident
        after = start + duration + timedelta(minutes=10)
        value = spike_pattern(baseline, multiplier, after, start, duration)

        assert value == baseline

    def test_spike_has_ramp_up(self):
        """Test spike has gradual ramp up at beginning."""
        baseline = 50.0
        multiplier = 10.0
        start = datetime(2025, 1, 15, 10, 0, 0)
        duration = timedelta(minutes=30)

        # Very early in incident (5% in)
        early = start + timedelta(seconds=90)  # 1.5 min = 5%
        value = spike_pattern(baseline, multiplier, early, start, duration)

        # Should be elevated but not full spike
        assert baseline < value < baseline * multiplier
