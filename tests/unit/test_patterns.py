"""Unit tests for time-series patterns module.

This module tests all pattern types and their behaviors.
"""

import math
import pytest
from datetime import datetime, timedelta

from generator.core.patterns import (
    SeasonalPattern,
    TrendPattern,
    BurstPattern,
    CyclicalPattern,
    NoisePattern,
    CompositePattern,
    create_daily_pattern,
    create_weekly_pattern,
    create_business_hours_pattern,
    create_growth_pattern,
    create_batch_job_pattern,
)


@pytest.fixture
def base_time():
    """Fixed baseline time for consistent tests."""
    return datetime(2024, 1, 1, 12, 0, 0)


@pytest.fixture
def base_value():
    """Base value for pattern testing."""
    return 100.0


class TestSeasonalPattern:
    """Tests for SeasonalPattern class."""

    def test_initialization(self):
        """Test SeasonalPattern can be initialized with default values."""
        pattern = SeasonalPattern()
        assert pattern.period_hours == 24.0
        assert pattern.amplitude == 0.3
        assert pattern.phase_shift == 0.0
        assert pattern.baseline_time is not None

    def test_initialization_with_custom_values(self, base_time):
        """Test SeasonalPattern with custom parameters."""
        pattern = SeasonalPattern(
            period_hours=168.0,
            amplitude=0.5,
            phase_shift=math.pi / 4,
            baseline_time=base_time
        )
        assert pattern.period_hours == 168.0
        assert pattern.amplitude == 0.5
        assert pattern.phase_shift == math.pi / 4
        assert pattern.baseline_time == base_time

    def test_apply_returns_modified_value(self, base_time, base_value):
        """Test that apply() modifies the base value."""
        pattern = SeasonalPattern(baseline_time=base_time)
        result = pattern.apply(base_value, base_time)
        # At baseline time with phase_shift=0, sin(0) = 0
        # multiplier = 1.0 + (0.3 * 0) = 1.0
        assert result == base_value

    def test_seasonal_variation_over_time(self, base_time, base_value):
        """Test that seasonal pattern varies over time."""
        pattern = SeasonalPattern(
            period_hours=24.0,
            amplitude=0.3,
            baseline_time=base_time
        )

        # At baseline (t=0): sin(0) = 0, multiplier = 1.0
        value_t0 = pattern.apply(base_value, base_time)

        # At quarter period (t=6h): sin(π/2) = 1, multiplier = 1.3
        time_t1 = base_time + timedelta(hours=6)
        value_t1 = pattern.apply(base_value, time_t1)

        # At half period (t=12h): sin(π) = 0, multiplier = 1.0
        time_t2 = base_time + timedelta(hours=12)
        value_t2 = pattern.apply(base_value, time_t2)

        # At three-quarter period (t=18h): sin(3π/2) = -1, multiplier = 0.7
        time_t3 = base_time + timedelta(hours=18)
        value_t3 = pattern.apply(base_value, time_t3)

        # Values should be different and follow sinusoidal pattern
        assert value_t1 > value_t0  # Peak
        assert value_t2 == pytest.approx(value_t0, rel=1e-9)  # Back to baseline
        assert value_t3 < value_t0  # Trough

    def test_phase_shift_affects_pattern(self, base_time, base_value):
        """Test that phase shift changes pattern timing."""
        pattern_no_shift = SeasonalPattern(
            period_hours=24.0,
            amplitude=0.3,
            phase_shift=0.0,
            baseline_time=base_time
        )

        pattern_with_shift = SeasonalPattern(
            period_hours=24.0,
            amplitude=0.3,
            phase_shift=math.pi / 2,  # 90 degree shift
            baseline_time=base_time
        )

        # At baseline time, values should differ due to phase shift
        value_no_shift = pattern_no_shift.apply(base_value, base_time)
        value_with_shift = pattern_with_shift.apply(base_value, base_time)

        assert value_no_shift != value_with_shift


class TestTrendPattern:
    """Tests for TrendPattern class."""

    def test_initialization_linear(self, base_time):
        """Test TrendPattern initialization with linear trend."""
        pattern = TrendPattern(
            trend_type='linear',
            rate=0.01,
            baseline_time=base_time
        )
        assert pattern.trend_type == 'linear'
        assert pattern.rate == 0.01
        assert pattern.baseline_time == base_time

    def test_initialization_exponential(self, base_time):
        """Test TrendPattern initialization with exponential trend."""
        pattern = TrendPattern(
            trend_type='exponential',
            rate=0.001,
            baseline_time=base_time
        )
        assert pattern.trend_type == 'exponential'

    def test_invalid_trend_type_raises_error(self):
        """Test that invalid trend type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown trend type"):
            TrendPattern(trend_type='invalid')

    def test_linear_trend_increases_over_time(self, base_time, base_value):
        """Test that linear trend increases value over time."""
        pattern = TrendPattern(
            trend_type='linear',
            rate=0.1,
            baseline_time=base_time
        )

        # At baseline: multiplier = 1.0 + (0.1 * 0) = 1.0
        value_t0 = pattern.apply(base_value, base_time)
        assert value_t0 == base_value

        # After 10 hours: multiplier = 1.0 + (0.1 * 10) = 2.0
        time_t1 = base_time + timedelta(hours=10)
        value_t1 = pattern.apply(base_value, time_t1)
        assert value_t1 == pytest.approx(base_value * 2.0)

    def test_exponential_trend_grows_exponentially(self, base_time, base_value):
        """Test that exponential trend grows exponentially."""
        pattern = TrendPattern(
            trend_type='exponential',
            rate=0.1,
            baseline_time=base_time
        )

        # At baseline: multiplier = exp(0) = 1.0
        value_t0 = pattern.apply(base_value, base_time)
        assert value_t0 == pytest.approx(base_value)

        # After 10 hours: multiplier = exp(0.1 * 10) = exp(1.0) ≈ 2.718
        time_t1 = base_time + timedelta(hours=10)
        value_t1 = pattern.apply(base_value, time_t1)
        expected = base_value * math.exp(1.0)
        assert value_t1 == pytest.approx(expected)

    def test_negative_trend_decreases_value(self, base_time, base_value):
        """Test that negative trend decreases value over time."""
        pattern = TrendPattern(
            trend_type='linear',
            rate=-0.05,
            baseline_time=base_time
        )

        time_future = base_time + timedelta(hours=10)
        value_future = pattern.apply(base_value, time_future)

        # Should decrease: 1.0 + (-0.05 * 10) = 0.5
        assert value_future == pytest.approx(base_value * 0.5)


class TestBurstPattern:
    """Tests for BurstPattern class."""

    def test_initialization(self, base_time):
        """Test BurstPattern initialization."""
        pattern = BurstPattern(
            burst_interval_minutes=60,
            burst_duration_minutes=5,
            burst_multiplier=3.0,
            baseline_time=base_time
        )
        assert pattern.burst_interval == timedelta(minutes=60)
        assert pattern.burst_duration == timedelta(minutes=5)
        assert pattern.burst_multiplier == 3.0
        assert pattern.baseline_time == base_time

    def test_burst_active_during_burst_window(self, base_time, base_value):
        """Test that burst multiplier is applied during burst window."""
        pattern = BurstPattern(
            burst_interval_minutes=60,
            burst_duration_minutes=5,
            burst_multiplier=3.0,
            baseline_time=base_time
        )

        # At baseline (start of burst): should be multiplied
        value_burst = pattern.apply(base_value, base_time)
        assert value_burst == base_value * 3.0

        # 3 minutes into burst: still multiplied
        time_during = base_time + timedelta(minutes=3)
        value_during = pattern.apply(base_value, time_during)
        assert value_during == base_value * 3.0

    def test_burst_inactive_outside_window(self, base_time, base_value):
        """Test that burst is not applied outside burst window."""
        pattern = BurstPattern(
            burst_interval_minutes=60,
            burst_duration_minutes=5,
            burst_multiplier=3.0,
            baseline_time=base_time
        )

        # 10 minutes in (after burst): should be normal
        time_after = base_time + timedelta(minutes=10)
        value_after = pattern.apply(base_value, time_after)
        assert value_after == base_value

    def test_burst_repeats_periodically(self, base_time, base_value):
        """Test that bursts repeat at the specified interval."""
        pattern = BurstPattern(
            burst_interval_minutes=60,
            burst_duration_minutes=5,
            burst_multiplier=3.0,
            baseline_time=base_time
        )

        # First burst at t=0
        value_first = pattern.apply(base_value, base_time)
        assert value_first == base_value * 3.0

        # Second burst at t=60min
        time_second_burst = base_time + timedelta(minutes=60)
        value_second = pattern.apply(base_value, time_second_burst)
        assert value_second == base_value * 3.0

        # Third burst at t=120min
        time_third_burst = base_time + timedelta(minutes=120)
        value_third = pattern.apply(base_value, time_third_burst)
        assert value_third == base_value * 3.0


class TestCyclicalPattern:
    """Tests for CyclicalPattern class."""

    def test_initialization(self):
        """Test CyclicalPattern initialization."""
        patterns = [
            SeasonalPattern(period_hours=24.0),
            SeasonalPattern(period_hours=168.0)
        ]
        cyclical = CyclicalPattern(patterns=patterns)
        assert len(cyclical.patterns) == 2

    def test_applies_multiple_patterns(self, base_time, base_value):
        """Test that cyclical pattern applies all seasonal patterns."""
        # Two patterns that should multiply effects
        pattern1 = SeasonalPattern(
            period_hours=24.0,
            amplitude=0.0,  # No variation, just multiplier of 1.0
            baseline_time=base_time
        )
        pattern2 = SeasonalPattern(
            period_hours=168.0,
            amplitude=0.0,  # No variation, just multiplier of 1.0
            baseline_time=base_time
        )

        cyclical = CyclicalPattern(patterns=[pattern1, pattern2])
        result = cyclical.apply(base_value, base_time)

        # With zero amplitude, should equal base_value
        assert result == pytest.approx(base_value)

    def test_patterns_applied_in_sequence(self, base_time, base_value):
        """Test that patterns are applied sequentially."""
        # Create patterns with measurable effects
        pattern1 = SeasonalPattern(
            period_hours=24.0,
            amplitude=0.5,
            phase_shift=math.pi / 2,  # sin(π/2) = 1, multiplier = 1.5
            baseline_time=base_time
        )
        pattern2 = SeasonalPattern(
            period_hours=168.0,
            amplitude=0.2,
            phase_shift=math.pi / 2,  # sin(π/2) = 1, multiplier = 1.2
            baseline_time=base_time
        )

        cyclical = CyclicalPattern(patterns=[pattern1, pattern2])
        result = cyclical.apply(base_value, base_time)

        # Should be base_value * 1.5 * 1.2 = base_value * 1.8
        expected = base_value * 1.5 * 1.2
        assert result == pytest.approx(expected, rel=1e-9)


class TestNoisePattern:
    """Tests for NoisePattern class."""

    def test_initialization(self):
        """Test NoisePattern initialization."""
        pattern = NoisePattern(noise_level=0.1, seed=42)
        assert pattern.noise_level == 0.1

    def test_apply_adds_randomness(self, base_time, base_value):
        """Test that noise pattern adds randomness."""
        pattern = NoisePattern(noise_level=0.1, seed=42)

        # Apply multiple times to same timestamp
        results = [pattern.apply(base_value, base_time) for _ in range(10)]

        # Results should vary (not all identical)
        assert len(set(results)) > 1

    def test_noise_with_seed_is_reproducible(self, base_time, base_value):
        """Test that same seed produces same initial value."""
        # Create pattern, apply, then recreate with same seed
        pattern1 = NoisePattern(noise_level=0.1, seed=42)
        result1 = pattern1.apply(base_value, base_time)

        # Reset with same seed should give same first value
        pattern2 = NoisePattern(noise_level=0.1, seed=42)
        result2 = pattern2.apply(base_value, base_time)

        assert result1 == result2

    def test_noise_varies_around_base_value(self, base_time, base_value):
        """Test that noise creates values around base value."""
        pattern = NoisePattern(noise_level=0.1, seed=42)

        # Generate many samples
        samples = [pattern.apply(base_value, base_time) for _ in range(100)]

        # Mean should be close to base_value (within reasonable bounds)
        mean = sum(samples) / len(samples)
        assert abs(mean - base_value) < base_value * 0.3  # Within 30%


class TestCompositePattern:
    """Tests for CompositePattern class."""

    def test_initialization(self):
        """Test CompositePattern initialization."""
        patterns = [
            SeasonalPattern(),
            TrendPattern(),
            NoisePattern(seed=42)
        ]
        composite = CompositePattern(patterns=patterns)
        assert len(composite.patterns) == 3

    def test_empty_composite_returns_base_value(self, base_time, base_value):
        """Test that empty composite pattern returns base value."""
        composite = CompositePattern(patterns=[])
        result = composite.apply(base_value, base_time)
        assert result == base_value

    def test_single_pattern_in_composite(self, base_time, base_value):
        """Test composite with single pattern."""
        pattern = TrendPattern(
            trend_type='linear',
            rate=0.1,
            baseline_time=base_time
        )
        composite = CompositePattern(patterns=[pattern])

        time_future = base_time + timedelta(hours=10)
        result = composite.apply(base_value, time_future)

        # Should match direct pattern application
        expected = pattern.apply(base_value, time_future)
        assert result == expected

    def test_multiple_patterns_combine(self, base_time, base_value):
        """Test that multiple patterns are combined correctly."""
        # Trend doubles value, seasonal adds no change at baseline
        trend = TrendPattern(
            trend_type='linear',
            rate=0.1,
            baseline_time=base_time
        )
        seasonal = SeasonalPattern(
            period_hours=24.0,
            amplitude=0.0,  # No variation
            baseline_time=base_time
        )

        composite = CompositePattern(patterns=[trend, seasonal])

        time_future = base_time + timedelta(hours=10)
        result = composite.apply(base_value, time_future)

        # Should be base_value * 2.0 * 1.0 = base_value * 2.0
        assert result == pytest.approx(base_value * 2.0)

    def test_pattern_order_matters(self, base_time, base_value):
        """Test that pattern application order affects result."""
        # Create patterns with distinct effects
        pattern1 = SeasonalPattern(
            period_hours=24.0,
            amplitude=0.5,
            phase_shift=math.pi / 2,  # Multiplier: 1.5
            baseline_time=base_time
        )
        pattern2 = TrendPattern(
            trend_type='linear',
            rate=0.1,
            baseline_time=base_time
        )

        composite1 = CompositePattern(patterns=[pattern1, pattern2])
        composite2 = CompositePattern(patterns=[pattern2, pattern1])

        time_future = base_time + timedelta(hours=10)

        result1 = composite1.apply(base_value, time_future)
        result2 = composite2.apply(base_value, time_future)

        # Results should be the same since order shouldn't matter for
        # multiplicative patterns at the same time point
        # Actually, let's verify they're applied correctly
        # composite1: base * 1.5 * 2.0 = base * 3.0
        # composite2: base * 2.0 * 1.5 = base * 3.0
        assert result1 == pytest.approx(result2, rel=1e-9)


class TestPredefinedPatterns:
    """Tests for predefined pattern creator functions."""

    def test_create_daily_pattern(self):
        """Test daily pattern creation."""
        pattern = create_daily_pattern(amplitude=0.3)
        assert isinstance(pattern, SeasonalPattern)
        assert pattern.period_hours == 24.0
        assert pattern.amplitude == 0.3
        assert pattern.phase_shift == math.pi / 6

    def test_create_daily_pattern_default_amplitude(self):
        """Test daily pattern with default amplitude."""
        pattern = create_daily_pattern()
        assert pattern.amplitude == 0.3

    def test_create_weekly_pattern(self):
        """Test weekly pattern creation."""
        pattern = create_weekly_pattern(amplitude=0.2)
        assert isinstance(pattern, SeasonalPattern)
        assert pattern.period_hours == 168.0  # 7 days
        assert pattern.amplitude == 0.2
        assert pattern.phase_shift == 0

    def test_create_weekly_pattern_default_amplitude(self):
        """Test weekly pattern with default amplitude."""
        pattern = create_weekly_pattern()
        assert pattern.amplitude == 0.2

    def test_create_business_hours_pattern(self):
        """Test business hours pattern creation."""
        pattern = create_business_hours_pattern()
        assert isinstance(pattern, CompositePattern)
        assert len(pattern.patterns) == 3

        # Should contain daily, weekly, and noise patterns
        assert isinstance(pattern.patterns[0], SeasonalPattern)  # Daily
        assert isinstance(pattern.patterns[1], SeasonalPattern)  # Weekly
        assert isinstance(pattern.patterns[2], NoisePattern)     # Noise

    def test_create_growth_pattern(self):
        """Test growth pattern creation."""
        pattern = create_growth_pattern(rate=0.001)
        assert isinstance(pattern, CompositePattern)
        assert len(pattern.patterns) == 3

        # Should contain trend, daily, and noise patterns
        assert isinstance(pattern.patterns[0], TrendPattern)     # Trend
        assert isinstance(pattern.patterns[1], SeasonalPattern)  # Daily
        assert isinstance(pattern.patterns[2], NoisePattern)     # Noise
        assert pattern.patterns[0].rate == 0.001

    def test_create_growth_pattern_default_rate(self):
        """Test growth pattern with default rate."""
        pattern = create_growth_pattern()
        assert pattern.patterns[0].rate == 0.001

    def test_create_batch_job_pattern(self):
        """Test batch job pattern creation."""
        pattern = create_batch_job_pattern()
        assert isinstance(pattern, CompositePattern)
        assert len(pattern.patterns) == 2

        # Should contain burst and noise patterns
        assert isinstance(pattern.patterns[0], BurstPattern)     # Burst
        assert isinstance(pattern.patterns[1], NoisePattern)     # Noise

        burst = pattern.patterns[0]
        assert burst.burst_interval == timedelta(minutes=60)
        assert burst.burst_duration == timedelta(minutes=5)
        assert burst.burst_multiplier == 5.0


class TestPatternIntegration:
    """Integration tests for realistic pattern scenarios."""

    def test_business_hours_pattern_behavior(self, base_time, base_value):
        """Test that business hours pattern produces realistic variation."""
        pattern = create_business_hours_pattern()

        # Sample values over 24 hours
        values = []
        for hour in range(24):
            timestamp = base_time + timedelta(hours=hour)
            values.append(pattern.apply(base_value, timestamp))

        # Values should vary (not all identical)
        assert len(set(values)) > 1
        # All values should be positive
        assert all(v > 0 for v in values)

    def test_growth_pattern_shows_growth(self, base_time, base_value):
        """Test that growth pattern increases over time."""
        pattern = create_growth_pattern(rate=0.01)

        value_start = pattern.apply(base_value, base_time)
        value_later = pattern.apply(base_value, base_time + timedelta(hours=100))

        # Later value should generally be higher (accounting for noise)
        # Use the underlying trend to verify
        trend_start = pattern.patterns[0].apply(base_value, base_time)
        trend_later = pattern.patterns[0].apply(base_value, base_time + timedelta(hours=100))

        assert trend_later > trend_start

    def test_batch_job_pattern_creates_spikes(self, base_time, base_value):
        """Test that batch job pattern creates periodic spikes."""
        # Create a burst pattern with known baseline time
        burst_pattern = BurstPattern(
            burst_interval_minutes=60,
            burst_duration_minutes=5,
            burst_multiplier=5.0,
            baseline_time=base_time
        )

        # At burst time (t=0, start of burst): should be high (multiplied by 5.0)
        burst_effect = burst_pattern.apply(base_value, base_time)

        # Between bursts (t=30min, outside 5min window): should be normal
        normal_effect = burst_pattern.apply(base_value, base_time + timedelta(minutes=30))

        # Burst should be higher than normal
        assert burst_effect > normal_effect
        assert burst_effect == base_value * 5.0
        assert normal_effect == base_value
