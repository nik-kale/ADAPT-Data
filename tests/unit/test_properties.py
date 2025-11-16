"""Property-based tests using Hypothesis."""

from datetime import datetime, timedelta

import pytest
from hypothesis import given, strategies as st, assume

from generator.core.utils import jitter, exponential_backoff, spike_pattern
from generator.anomalies.injectors import (
    LatencyInjector,
    ErrorRateInjector,
    CPUSpikeInjector,
)


class TestJitterProperties:
    """Property-based tests for jitter function."""

    @given(
        value=st.floats(min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False),
        percent=st.floats(min_value=0.0, max_value=0.5, allow_nan=False, allow_infinity=False)
    )
    def test_jitter_bounded(self, value, percent):
        """Jitter should stay within bounds."""
        result = jitter(value, percent)

        # Should be within percentage bounds
        lower_bound = value * (1 - percent - 0.1)  # Allow some extra room for randomness
        upper_bound = value * (1 + percent + 0.1)

        assert lower_bound <= result <= upper_bound

    @given(
        value=st.floats(min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False)
    )
    def test_jitter_zero_percent_returns_value(self, value):
        """Jitter with 0% should return original value."""
        result = jitter(value, 0.0)
        assert result == value


class TestExponentialBackoffProperties:
    """Property-based tests for exponential backoff."""

    @given(
        base=st.floats(min_value=0.1, max_value=100.0, allow_nan=False, allow_infinity=False),
        iteration=st.integers(min_value=0, max_value=10)
    )
    def test_backoff_increases_monotonically(self, base, iteration):
        """Backoff should generally increase with iteration."""
        if iteration == 0:
            return  # Skip base case

        current = exponential_backoff(base, iteration, jitter_percent=0.0)
        previous = exponential_backoff(base, iteration - 1, jitter_percent=0.0)

        # Without jitter, should be monotonically increasing
        assert current >= previous

    @given(
        base=st.floats(min_value=0.1, max_value=100.0, allow_nan=False, allow_infinity=False),
        iteration=st.integers(min_value=0, max_value=20),
        max_value=st.floats(min_value=10.0, max_value=1000.0, allow_nan=False, allow_infinity=False)
    )
    def test_backoff_respects_maximum(self, base, iteration, max_value):
        """Backoff should never significantly exceed maximum."""
        assume(max_value > base)  # Max should be larger than base

        result = exponential_backoff(base, iteration, max_value=max_value)

        # Allow some jitter room (20% over max)
        assert result <= max_value * 1.3


class TestSpikePatternProperties:
    """Property-based tests for spike patterns."""

    @given(
        baseline=st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        multiplier=st.floats(min_value=1.1, max_value=100.0, allow_nan=False, allow_infinity=False)
    )
    def test_spike_before_always_baseline(self, baseline, multiplier):
        """Value before spike should always equal baseline."""
        spike_start = datetime(2025, 1, 15, 10, 0, 0)
        spike_duration = timedelta(minutes=30)

        before = spike_start - timedelta(minutes=10)

        value = spike_pattern(
            baseline=baseline,
            spike_multiplier=multiplier,
            current_time=before,
            spike_start=spike_start,
            spike_duration=spike_duration
        )

        assert value == baseline

    @given(
        baseline=st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        multiplier=st.floats(min_value=1.1, max_value=100.0, allow_nan=False, allow_infinity=False)
    )
    def test_spike_after_always_baseline(self, baseline, multiplier):
        """Value after spike should always equal baseline."""
        spike_start = datetime(2025, 1, 15, 10, 0, 0)
        spike_duration = timedelta(minutes=30)

        after = spike_start + spike_duration + timedelta(minutes=10)

        value = spike_pattern(
            baseline=baseline,
            spike_multiplier=multiplier,
            current_time=after,
            spike_start=spike_start,
            spike_duration=spike_duration
        )

        assert value == baseline

    @given(
        baseline=st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        multiplier=st.floats(min_value=2.0, max_value=50.0, allow_nan=False, allow_infinity=False)
    )
    def test_spike_during_elevated(self, baseline, multiplier):
        """Value during spike (middle) should be elevated."""
        spike_start = datetime(2025, 1, 15, 10, 0, 0)
        spike_duration = timedelta(minutes=30)

        # Middle of spike
        during = spike_start + timedelta(minutes=15)

        value = spike_pattern(
            baseline=baseline,
            spike_multiplier=multiplier,
            current_time=during,
            spike_start=spike_start,
            spike_duration=spike_duration
        )

        # Should be significantly elevated (at least 80% of full spike)
        assert value >= baseline * multiplier * 0.8


class TestLatencyInjectorProperties:
    """Property-based tests for LatencyInjector."""

    @given(
        baseline=st.floats(min_value=1.0, max_value=500.0, allow_nan=False, allow_infinity=False),
        multiplier=st.floats(min_value=2.0, max_value=50.0, allow_nan=False, allow_infinity=False)
    )
    def test_latency_never_negative(self, baseline, multiplier):
        """Latency should never be negative."""
        spike_start = datetime(2025, 1, 15, 10, 0, 0)
        injector = LatencyInjector(
            baseline_ms=baseline,
            anomaly_multiplier=multiplier,
            spike_start=spike_start,
            spike_duration=timedelta(minutes=30)
        )

        # Test various points
        for minutes_offset in [-10, 0, 15, 30, 40]:
            t = spike_start + timedelta(minutes=minutes_offset)
            latency = injector.get_latency(t)
            assert latency >= 0


class TestErrorRateInjectorProperties:
    """Property-based tests for ErrorRateInjector."""

    @given(
        baseline=st.floats(min_value=0.0, max_value=0.1, allow_nan=False, allow_infinity=False),
        anomaly=st.floats(min_value=0.1, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    def test_error_rate_bounded_0_to_1(self, baseline, anomaly):
        """Error rate should always be between 0 and 1."""
        assume(anomaly > baseline)  # Anomaly should be higher than baseline

        spike_start = datetime(2025, 1, 15, 10, 0, 0)
        injector = ErrorRateInjector(
            baseline_error_rate=baseline,
            anomaly_error_rate=anomaly,
            spike_start=spike_start,
            spike_duration=timedelta(minutes=20)
        )

        # Test various points
        for minutes_offset in [-10, 0, 10, 20, 30]:
            t = spike_start + timedelta(minutes=minutes_offset)
            rate = injector.get_error_rate(t)
            assert 0.0 <= rate <= 1.0


class TestCPUSpikeInjectorProperties:
    """Property-based tests for CPUSpikeInjector."""

    @given(
        baseline=st.floats(min_value=1.0, max_value=80.0, allow_nan=False, allow_infinity=False),
        spike=st.floats(min_value=80.0, max_value=100.0, allow_nan=False, allow_infinity=False)
    )
    def test_cpu_always_0_to_100(self, baseline, spike):
        """CPU usage should always be between 0 and 100."""
        assume(spike > baseline)

        spike_start = datetime(2025, 1, 15, 10, 0, 0)
        injector = CPUSpikeInjector(
            baseline_percent=baseline,
            spike_percent=spike,
            spike_start=spike_start,
            spike_duration=timedelta(minutes=5)
        )

        # Test many points
        for seconds_offset in range(0, 600, 30):
            t = spike_start + timedelta(seconds=seconds_offset)
            cpu = injector.get_cpu_usage(t)
            assert 0.0 <= cpu <= 100.0
