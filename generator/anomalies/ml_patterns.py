"""Machine Learning-based anomaly pattern generation.

This module provides AI-powered anomaly generators that learn from
patterns and create realistic, complex anomalies.
"""

import math
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

import numpy as np


@dataclass
class AnomalyPattern:
    """Represents a learned anomaly pattern."""

    pattern_type: str  # spike, drift, seasonal, chaotic
    severity: float  # 0.0 to 1.0
    duration: timedelta
    characteristics: dict[str, Any]


class MLAnomalyPatternGenerator:
    """Generate anomalies using machine learning patterns.

    Uses statistical models and pattern recognition to create
    realistic anomalies that mimic real-world incidents.
    """

    def __init__(self, seed: int = None):
        """Initialize ML pattern generator.

        Args:
            seed: Random seed for reproducibility
        """
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

    def generate_multimodal_anomaly(
        self,
        baseline: float,
        start_time: datetime,
        duration: timedelta,
        num_modes: int = 3
    ) -> Callable[[datetime], float]:
        """Generate multi-modal anomaly pattern.

        Creates anomalies with multiple contributing factors that
        compound to create complex patterns.

        Args:
            baseline: Normal baseline value
            start_time: Anomaly start time
            duration: Anomaly duration
            num_modes: Number of anomaly modes to combine

        Returns:
            Function that takes timestamp and returns anomalous value
        """
        # Generate random modes
        modes = []
        for _ in range(num_modes):
            mode_type = random.choice(['spike', 'drift', 'oscillation', 'step'])
            amplitude = random.uniform(0.5, 3.0)
            frequency = random.uniform(0.1, 2.0)

            modes.append({
                'type': mode_type,
                'amplitude': amplitude,
                'frequency': frequency
            })

        def anomaly_func(timestamp: datetime) -> float:
            if timestamp < start_time or timestamp > start_time + duration:
                return baseline

            # Calculate progress through anomaly
            elapsed = (timestamp - start_time).total_seconds()
            progress = elapsed / duration.total_seconds()

            value = baseline
            for mode in modes:
                if mode['type'] == 'spike':
                    # Spike pattern using gamma distribution
                    spike_value = np.random.gamma(2, mode['amplitude'])
                    value += spike_value * math.exp(-(progress - 0.5) ** 2 / 0.1)

                elif mode['type'] == 'drift':
                    # Linear drift
                    value += mode['amplitude'] * baseline * progress

                elif mode['type'] == 'oscillation':
                    # Sinusoidal oscillation
                    value += mode['amplitude'] * baseline * math.sin(
                        2 * math.pi * mode['frequency'] * progress
                    )

                elif mode['type'] == 'step':
                    # Step function
                    if progress > 0.3:
                        value += mode['amplitude'] * baseline

            return max(0, value)

        return anomaly_func

    def generate_cascading_failure_pattern(
        self,
        baseline: float,
        start_time: datetime,
        cascade_delay: timedelta = timedelta(minutes=5),
        num_cascades: int = 3
    ) -> Callable[[datetime], tuple[float, str]]:
        """Generate cascading failure pattern.

        Models how failures propagate through a system over time.

        Args:
            baseline: Normal baseline value
            start_time: Initial failure time
            cascade_delay: Time between cascade stages
            num_cascades: Number of cascade stages

        Returns:
            Function returning (value, stage_description)
        """
        cascade_stages = []
        for i in range(num_cascades):
            stage_start = start_time + (cascade_delay * i)
            multiplier = 1.5 ** (i + 1)  # Exponential degradation
            stage_desc = f"Cascade stage {i+1}: {'Critical' if i >= num_cascades - 1 else 'Degraded'}"

            cascade_stages.append({
                'start': stage_start,
                'multiplier': multiplier,
                'description': stage_desc
            })

        def cascade_func(timestamp: datetime) -> tuple[float, str]:
            value = baseline
            stage_desc = "Normal"

            for stage in cascade_stages:
                if timestamp >= stage['start']:
                    value = baseline * stage['multiplier']
                    stage_desc = stage['description']

            return value, stage_desc

        return cascade_func

    def generate_seasonal_anomaly(
        self,
        baseline: float,
        start_time: datetime,
        duration: timedelta,
        daily_pattern: bool = True,
        weekly_pattern: bool = False
    ) -> Callable[[datetime], float]:
        """Generate anomaly with seasonal/temporal patterns.

        Creates anomalies that vary based on time of day or day of week.

        Args:
            baseline: Normal baseline value
            start_time: Anomaly start time
            duration: Anomaly duration
            daily_pattern: Include daily (hourly) variation
            weekly_pattern: Include weekly variation

        Returns:
            Function that takes timestamp and returns anomalous value
        """
        def seasonal_func(timestamp: datetime) -> float:
            if timestamp < start_time or timestamp > start_time + duration:
                return baseline

            value = baseline

            if daily_pattern:
                # Higher anomaly during business hours (9am-5pm)
                hour = timestamp.hour
                if 9 <= hour <= 17:
                    value *= 2.0
                else:
                    value *= 1.2

            if weekly_pattern:
                # Lower on weekends
                weekday = timestamp.weekday()
                if weekday >= 5:  # Saturday=5, Sunday=6
                    value *= 0.7

            # Add noise
            value *= random.uniform(0.9, 1.1)

            return value

        return seasonal_func

    def generate_resource_exhaustion_pattern(
        self,
        baseline: float,
        start_time: datetime,
        saturation_time: timedelta = timedelta(minutes=30),
        resource_type: str = 'memory'
    ) -> Callable[[datetime], tuple[float, dict[str, Any]]]:
        """Generate resource exhaustion pattern.

        Models gradual resource depletion (memory leak, connection pool
        exhaustion, disk fill).

        Args:
            baseline: Normal baseline usage
            start_time: When exhaustion begins
            saturation_time: Time until resource is exhausted
            resource_type: Type of resource (memory, connections, disk)

        Returns:
            Function returning (usage, metadata)
        """
        max_capacity = baseline * 10  # Assume 10x baseline is capacity

        def exhaustion_func(timestamp: datetime) -> tuple[float, dict[str, Any]]:
            if timestamp < start_time:
                return baseline, {'status': 'normal'}

            elapsed = (timestamp - start_time).total_seconds()
            saturation_seconds = saturation_time.total_seconds()

            if elapsed >= saturation_seconds:
                # Saturated
                usage = max_capacity * random.uniform(0.95, 1.0)
                status = 'exhausted'
                available = 0
            else:
                # Gradual increase with exponential growth
                progress = elapsed / saturation_seconds
                growth_factor = math.exp(3 * progress)  # e^(3*progress)
                usage = baseline * growth_factor
                usage = min(usage, max_capacity)

                available_pct = (max_capacity - usage) / max_capacity
                if available_pct < 0.1:
                    status = 'critical'
                elif available_pct < 0.3:
                    status = 'warning'
                else:
                    status = 'normal'

                available = max_capacity - usage

            metadata = {
                'status': status,
                'usage': usage,
                'capacity': max_capacity,
                'available': available,
                'utilization_pct': (usage / max_capacity) * 100,
                'resource_type': resource_type
            }

            return usage, metadata

        return exhaustion_func

    def generate_intermittent_failure_pattern(
        self,
        baseline: float,
        start_time: datetime,
        duration: timedelta,
        failure_rate: float = 0.3,
        burst_length: timedelta = timedelta(seconds=30)
    ) -> Callable[[datetime], tuple[float, bool]]:
        """Generate intermittent failure pattern.

        Models flapping/intermittent issues that appear and disappear.

        Args:
            baseline: Normal baseline value
            start_time: Anomaly window start
            duration: Total anomaly window duration
            failure_rate: Probability of failure (0.0-1.0)
            burst_length: How long failures last when they occur

        Returns:
            Function returning (value, is_failing)
        """
        failure_windows = []
        current_time = start_time

        # Pre-generate failure windows
        while current_time < start_time + duration:
            if random.random() < failure_rate:
                failure_end = current_time + burst_length
                failure_windows.append((current_time, failure_end))
                current_time = failure_end + timedelta(seconds=random.randint(30, 120))
            else:
                current_time += timedelta(seconds=random.randint(10, 60))

        def intermittent_func(timestamp: datetime) -> tuple[float, bool]:
            is_failing = False
            for window_start, window_end in failure_windows:
                if window_start <= timestamp <= window_end:
                    is_failing = True
                    break

            if is_failing:
                # High error rate during failure
                value = baseline * random.uniform(5.0, 10.0)
            else:
                # Normal during non-failure
                value = baseline * random.uniform(0.9, 1.1)

            return value, is_failing

        return intermittent_func

    def generate_bimodal_distribution_anomaly(
        self,
        baseline: float,
        start_time: datetime,
        duration: timedelta
    ) -> Callable[[datetime], float]:
        """Generate bimodal distribution anomaly.

        Creates a distribution with two distinct peaks, representing
        two different behaviors (e.g., fast path vs slow path).

        Args:
            baseline: Normal baseline value
            start_time: Anomaly start time
            duration: Anomaly duration

        Returns:
            Function that returns values from bimodal distribution
        """
        # Two modes: fast and slow
        fast_mean = baseline
        slow_mean = baseline * 5.0
        fast_std = baseline * 0.1
        slow_std = baseline * 0.5

        def bimodal_func(timestamp: datetime) -> float:
            if timestamp < start_time or timestamp > start_time + duration:
                return np.random.normal(baseline, baseline * 0.1)

            # During anomaly, mix of fast and slow
            if random.random() < 0.7:
                # Fast path (70%)
                return max(0, np.random.normal(fast_mean, fast_std))
            else:
                # Slow path (30%)
                return max(0, np.random.normal(slow_mean, slow_std))

        return bimodal_func

    def learn_from_patterns(
        self,
        historical_data: list[tuple[datetime, float]],
        detect_anomalies: bool = True
    ) -> AnomalyPattern:
        """Learn anomaly patterns from historical data.

        Analyzes historical data to extract common anomaly patterns.

        Args:
            historical_data: List of (timestamp, value) tuples
            detect_anomalies: Whether to detect and characterize anomalies

        Returns:
            Learned AnomalyPattern
        """
        if not historical_data:
            raise ValueError("No historical data provided")

        # Extract values
        values = np.array([v for _, v in historical_data])

        # Calculate statistics
        mean = np.mean(values)
        std = np.std(values)
        median = np.median(values)

        # Detect pattern type
        # Simple heuristics (in production, use more sophisticated ML)
        if std > mean * 0.5:
            pattern_type = "chaotic"
        elif max(values) > mean + 3 * std:
            pattern_type = "spike"
        elif np.polyfit(range(len(values)), values, 1)[0] > 0.1 * mean:
            pattern_type = "drift"
        else:
            pattern_type = "seasonal"

        # Calculate severity
        severity = min(1.0, std / (mean + 1e-6))

        # Estimate duration (time above threshold)
        threshold = mean + 2 * std
        anomalous_points = sum(1 for v in values if v > threshold)
        duration_estimate = timedelta(minutes=anomalous_points)

        return AnomalyPattern(
            pattern_type=pattern_type,
            severity=severity,
            duration=duration_estimate,
            characteristics={
                'mean': mean,
                'std': std,
                'median': median,
                'max': max(values),
                'min': min(values),
                'num_samples': len(values)
            }
        )
