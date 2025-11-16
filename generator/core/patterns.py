"""Time-series patterns for realistic data generation.

This module provides seasonal, trend, and cyclical patterns that can be
applied to telemetry data for more realistic scenarios.
"""

import math
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional


class TimeSeriesPattern(ABC):
    """Base class for time-series patterns."""

    @abstractmethod
    def apply(self, base_value: float, timestamp: datetime) -> float:
        """Apply pattern to base value at given timestamp.

        Args:
            base_value: Base value to modify
            timestamp: Current timestamp

        Returns:
            Modified value with pattern applied
        """
        pass


class SeasonalPattern(TimeSeriesPattern):
    """Seasonal pattern with configurable period and amplitude.

    Examples:
        - Daily pattern: period=24h, peaks at certain hours
        - Weekly pattern: period=7d, weekday vs weekend differences
        - Monthly pattern: period=30d, month-end spikes
    """

    def __init__(
        self,
        period_hours: float = 24.0,
        amplitude: float = 0.3,
        phase_shift: float = 0.0,
        baseline_time: Optional[datetime] = None
    ) -> None:
        """Initialize seasonal pattern.

        Args:
            period_hours: Period length in hours (24 = daily, 168 = weekly)
            amplitude: Pattern amplitude as fraction of base value (0-1)
            phase_shift: Phase shift in radians
            baseline_time: Reference time for phase calculation
        """
        self.period_hours = period_hours
        self.amplitude = amplitude
        self.phase_shift = phase_shift
        self.baseline_time = baseline_time or datetime.utcnow()

    def apply(self, base_value: float, timestamp: datetime) -> float:
        """Apply seasonal pattern."""
        # Calculate time difference in hours
        hours_elapsed = (timestamp - self.baseline_time).total_seconds() / 3600

        # Calculate position in cycle (0 to 2π)
        cycle_position = (2 * math.pi * hours_elapsed / self.period_hours) + self.phase_shift

        # Apply sinusoidal pattern
        multiplier = 1.0 + (self.amplitude * math.sin(cycle_position))

        return base_value * multiplier


class TrendPattern(TimeSeriesPattern):
    """Linear or exponential trend over time.

    Examples:
        - Growing load: positive linear trend
        - Resource exhaustion: exponential growth
        - Capacity improvement: negative trend
    """

    def __init__(
        self,
        trend_type: str = "linear",
        rate: float = 0.01,
        baseline_time: Optional[datetime] = None
    ) -> None:
        """Initialize trend pattern.

        Args:
            trend_type: Type of trend ('linear' or 'exponential')
            rate: Rate of change per hour
            baseline_time: Reference time for trend calculation
        """
        if trend_type not in ['linear', 'exponential']:
            raise ValueError(f"Unknown trend type: {trend_type}")

        self.trend_type = trend_type
        self.rate = rate
        self.baseline_time = baseline_time or datetime.utcnow()

    def apply(self, base_value: float, timestamp: datetime) -> float:
        """Apply trend pattern."""
        # Calculate time difference in hours
        hours_elapsed = (timestamp - self.baseline_time).total_seconds() / 3600

        if self.trend_type == 'linear':
            # Linear trend: value = base * (1 + rate * time)
            multiplier = 1.0 + (self.rate * hours_elapsed)
        else:  # exponential
            # Exponential trend: value = base * exp(rate * time)
            multiplier = math.exp(self.rate * hours_elapsed)

        return base_value * multiplier


class CyclicalPattern(TimeSeriesPattern):
    """Multiple overlapping cycles (e.g., daily + weekly).

    Combines multiple seasonal patterns.
    """

    def __init__(self, patterns: list[SeasonalPattern]) -> None:
        """Initialize cyclical pattern.

        Args:
            patterns: List of seasonal patterns to combine
        """
        self.patterns = patterns

    def apply(self, base_value: float, timestamp: datetime) -> float:
        """Apply all cyclical patterns."""
        result = base_value
        for pattern in self.patterns:
            result = pattern.apply(result, timestamp)
        return result


class BurstPattern(TimeSeriesPattern):
    """Periodic bursts or spikes.

    Examples:
        - Scheduled jobs (e.g., every hour on the hour)
        - Batch processing windows
        - Traffic spikes
    """

    def __init__(
        self,
        burst_interval_minutes: int = 60,
        burst_duration_minutes: int = 5,
        burst_multiplier: float = 3.0,
        baseline_time: Optional[datetime] = None
    ) -> None:
        """Initialize burst pattern.

        Args:
            burst_interval_minutes: Time between bursts
            burst_duration_minutes: Duration of each burst
            burst_multiplier: Multiplier during burst
            baseline_time: Reference time
        """
        self.burst_interval = timedelta(minutes=burst_interval_minutes)
        self.burst_duration = timedelta(minutes=burst_duration_minutes)
        self.burst_multiplier = burst_multiplier
        self.baseline_time = baseline_time or datetime.utcnow()

    def apply(self, base_value: float, timestamp: datetime) -> float:
        """Apply burst pattern."""
        # Calculate position in burst cycle
        time_since_baseline = timestamp - self.baseline_time
        minutes_since_baseline = time_since_baseline.total_seconds() / 60

        # Calculate time within current interval
        interval_minutes = self.burst_interval.total_seconds() / 60
        position_in_interval = minutes_since_baseline % interval_minutes

        # Check if we're in a burst
        burst_duration_min = self.burst_duration.total_seconds() / 60
        if position_in_interval < burst_duration_min:
            return base_value * self.burst_multiplier

        return base_value


class NoisePattern(TimeSeriesPattern):
    """Random noise overlay.

    Adds realistic randomness to base values.
    """

    def __init__(self, noise_level: float = 0.1, seed: Optional[int] = None) -> None:
        """Initialize noise pattern.

        Args:
            noise_level: Noise amplitude as fraction of value (0-1)
            seed: Random seed for reproducibility
        """
        import random
        self.noise_level = noise_level
        if seed is not None:
            random.seed(seed)

    def apply(self, base_value: float, timestamp: datetime) -> float:
        """Apply noise pattern."""
        import random
        noise = random.gauss(0, self.noise_level)
        return base_value * (1.0 + noise)


class CompositePattern(TimeSeriesPattern):
    """Combines multiple patterns.

    Applies patterns in sequence to create complex, realistic behavior.
    """

    def __init__(self, patterns: list[TimeSeriesPattern]) -> None:
        """Initialize composite pattern.

        Args:
            patterns: List of patterns to apply in order
        """
        self.patterns = patterns

    def apply(self, base_value: float, timestamp: datetime) -> float:
        """Apply all patterns in sequence."""
        result = base_value
        for pattern in self.patterns:
            result = pattern.apply(result, timestamp)
        return result


# Predefined realistic patterns
def create_daily_pattern(amplitude: float = 0.3) -> SeasonalPattern:
    """Create daily pattern with peak at 2pm."""
    return SeasonalPattern(
        period_hours=24.0,
        amplitude=amplitude,
        phase_shift=math.pi / 6  # Peak at 14:00
    )


def create_weekly_pattern(amplitude: float = 0.2) -> SeasonalPattern:
    """Create weekly pattern with lower weekend traffic."""
    return SeasonalPattern(
        period_hours=168.0,  # 7 days
        amplitude=amplitude,
        phase_shift=0
    )


def create_business_hours_pattern() -> CompositePattern:
    """Create realistic business hours pattern.

    Combines:
    - Daily pattern (higher during day)
    - Weekly pattern (lower on weekends)
    - Noise
    """
    return CompositePattern([
        create_daily_pattern(amplitude=0.4),
        create_weekly_pattern(amplitude=0.3),
        NoisePattern(noise_level=0.05)
    ])


def create_growth_pattern(rate: float = 0.001) -> CompositePattern:
    """Create growing load pattern with daily variation."""
    return CompositePattern([
        TrendPattern(trend_type='linear', rate=rate),
        create_daily_pattern(amplitude=0.2),
        NoisePattern(noise_level=0.05)
    ])


def create_batch_job_pattern() -> CompositePattern:
    """Create pattern for hourly batch jobs."""
    return CompositePattern([
        BurstPattern(
            burst_interval_minutes=60,
            burst_duration_minutes=5,
            burst_multiplier=5.0
        ),
        NoisePattern(noise_level=0.1)
    ])
