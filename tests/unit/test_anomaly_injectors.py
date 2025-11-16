"""Unit tests for anomaly injectors."""

from datetime import datetime, timedelta

import pytest

from generator.anomalies.injectors import (
    LatencyInjector,
    ErrorRateInjector,
    ThroughputInjector,
    MemoryLeakInjector,
    CPUSpikeInjector,
)


class TestLatencyInjector:
    """Test latency anomaly injection."""

    def test_latency_baseline_before_spike(self):
        """Test latency is near baseline before spike."""
        spike_start = datetime(2025, 1, 15, 10, 0, 0)
        injector = LatencyInjector(
            baseline_ms=50.0,
            anomaly_multiplier=10.0,
            spike_start=spike_start,
            spike_duration=timedelta(minutes=30)
        )

        before = spike_start - timedelta(minutes=5)
        latency = injector.get_latency(before)

        # Should be near baseline (within reasonable noise)
        assert 30 < latency < 70

    def test_latency_elevated_during_spike(self):
        """Test latency is elevated during spike."""
        spike_start = datetime(2025, 1, 15, 10, 0, 0)
        injector = LatencyInjector(
            baseline_ms=50.0,
            anomaly_multiplier=10.0,
            spike_start=spike_start,
            spike_duration=timedelta(minutes=30)
        )

        during = spike_start + timedelta(minutes=15)
        latency = injector.get_latency(during)

        # Should be significantly elevated
        assert latency > 300

    def test_latency_returns_to_baseline(self):
        """Test latency returns to baseline after spike."""
        spike_start = datetime(2025, 1, 15, 10, 0, 0)
        injector = LatencyInjector(
            baseline_ms=50.0,
            anomaly_multiplier=10.0,
            spike_start=spike_start,
            spike_duration=timedelta(minutes=30)
        )

        after = spike_start + timedelta(hours=1)
        latency = injector.get_latency(after)

        assert 30 < latency < 70


class TestErrorRateInjector:
    """Test error rate anomaly injection."""

    def test_error_rate_baseline(self):
        """Test error rate is low at baseline."""
        spike_start = datetime(2025, 1, 15, 10, 0, 0)
        injector = ErrorRateInjector(
            baseline_error_rate=0.001,
            anomaly_error_rate=0.25,
            spike_start=spike_start,
            spike_duration=timedelta(minutes=20)
        )

        before = spike_start - timedelta(minutes=5)
        rate = injector.get_error_rate(before)

        assert rate < 0.01

    def test_error_rate_elevated_during_spike(self):
        """Test error rate is elevated during spike."""
        spike_start = datetime(2025, 1, 15, 10, 0, 0)
        injector = ErrorRateInjector(
            baseline_error_rate=0.001,
            anomaly_error_rate=0.25,
            spike_start=spike_start,
            spike_duration=timedelta(minutes=20)
        )

        during = spike_start + timedelta(minutes=10)
        rate = injector.get_error_rate(during)

        assert rate > 0.1

    def test_should_error_probability(self):
        """Test should_error respects probability."""
        spike_start = datetime(2025, 1, 15, 10, 0, 0)
        injector = ErrorRateInjector(
            baseline_error_rate=0.0,
            anomaly_error_rate=1.0,  # Always error during spike
            spike_start=spike_start,
            spike_duration=timedelta(minutes=20)
        )

        during = spike_start + timedelta(minutes=10)

        # Should always error
        errors = sum(1 for _ in range(100) if injector.should_error(during))
        assert errors == 100


class TestMemoryLeakInjector:
    """Test memory leak injection."""

    def test_memory_baseline_before_leak(self):
        """Test memory is at baseline before leak."""
        leak_start = datetime(2025, 1, 15, 10, 0, 0)
        injector = MemoryLeakInjector(
            baseline_mb=512.0,
            leak_rate_mb_per_min=50.0,
            max_memory_mb=4096.0,
            leak_start=leak_start
        )

        before = leak_start - timedelta(minutes=5)
        memory = injector.get_memory_usage(before)

        assert 480 < memory < 550

    def test_memory_increases_during_leak(self):
        """Test memory increases during leak."""
        leak_start = datetime(2025, 1, 15, 10, 0, 0)
        injector = MemoryLeakInjector(
            baseline_mb=512.0,
            leak_rate_mb_per_min=50.0,
            max_memory_mb=4096.0,
            leak_start=leak_start
        )

        # 10 minutes into leak: 512 + (50 * 10) = 1012 MB
        during = leak_start + timedelta(minutes=10)
        memory = injector.get_memory_usage(during)

        assert 900 < memory < 1100

    def test_memory_respects_max(self):
        """Test memory doesn't exceed maximum."""
        leak_start = datetime(2025, 1, 15, 10, 0, 0)
        injector = MemoryLeakInjector(
            baseline_mb=512.0,
            leak_rate_mb_per_min=50.0,
            max_memory_mb=2048.0,
            leak_start=leak_start
        )

        # Way past max: 100 minutes would be 5512 MB without cap
        way_past = leak_start + timedelta(minutes=100)
        memory = injector.get_memory_usage(way_past)

        assert memory <= 2048.0

    def test_has_crashed_when_at_max(self):
        """Test crash detection when at max memory."""
        leak_start = datetime(2025, 1, 15, 10, 0, 0)
        injector = MemoryLeakInjector(
            baseline_mb=512.0,
            leak_rate_mb_per_min=100.0,
            max_memory_mb=1024.0,
            leak_start=leak_start
        )

        # After 10 minutes: 512 + 1000 = 1512 (capped at 1024)
        crash_time = leak_start + timedelta(minutes=10)

        assert injector.has_crashed(crash_time)


class TestCPUSpikeInjector:
    """Test CPU spike injection."""

    def test_cpu_baseline(self):
        """Test CPU is at baseline before spike."""
        spike_start = datetime(2025, 1, 15, 10, 0, 0)
        injector = CPUSpikeInjector(
            baseline_percent=25.0,
            spike_percent=95.0,
            spike_start=spike_start,
            spike_duration=timedelta(minutes=5)
        )

        before = spike_start - timedelta(minutes=2)
        cpu = injector.get_cpu_usage(before)

        assert 15 < cpu < 35

    def test_cpu_elevated_during_spike(self):
        """Test CPU is elevated during spike."""
        spike_start = datetime(2025, 1, 15, 10, 0, 0)
        injector = CPUSpikeInjector(
            baseline_percent=25.0,
            spike_percent=95.0,
            spike_start=spike_start,
            spike_duration=timedelta(minutes=5)
        )

        during = spike_start + timedelta(minutes=2.5)
        cpu = injector.get_cpu_usage(during)

        assert cpu > 80

    def test_cpu_never_exceeds_100(self):
        """Test CPU never exceeds 100%."""
        spike_start = datetime(2025, 1, 15, 10, 0, 0)
        injector = CPUSpikeInjector(
            baseline_percent=50.0,
            spike_percent=99.0,
            spike_start=spike_start,
            spike_duration=timedelta(minutes=5)
        )

        # Check many points
        for i in range(100):
            t = spike_start + timedelta(seconds=i * 3)
            cpu = injector.get_cpu_usage(t)
            assert 0 <= cpu <= 100
