"""Anomaly injection functions for metrics and behavior."""

import random
from datetime import datetime, timedelta
from typing import Callable

from generator.core.utils import gaussian_noise, jitter, spike_pattern


class LatencyInjector:
    """Injects latency anomalies into metric streams."""

    def __init__(
        self,
        baseline_ms: float = 50.0,
        anomaly_multiplier: float = 10.0,
        spike_start: datetime | None = None,
        spike_duration: timedelta = timedelta(minutes=15)
    ) -> None:
        """Initialize latency injector.

        Args:
            baseline_ms: Normal latency in milliseconds
            anomaly_multiplier: Multiplier during anomaly
            spike_start: When to start spike
            spike_duration: How long spike lasts
        """
        self.baseline_ms = baseline_ms
        self.anomaly_multiplier = anomaly_multiplier
        self.spike_start = spike_start or datetime.utcnow()
        self.spike_duration = spike_duration

    def get_latency(self, timestamp: datetime) -> float:
        """Get latency value for timestamp.

        Args:
            timestamp: Current timestamp

        Returns:
            Latency in milliseconds
        """
        base_value = spike_pattern(
            baseline=self.baseline_ms,
            spike_multiplier=self.anomaly_multiplier,
            current_time=timestamp,
            spike_start=self.spike_start,
            spike_duration=self.spike_duration
        )

        # Add realistic noise
        noise = gaussian_noise(0, self.baseline_ms * 0.1)
        return max(0, base_value + noise)


class ErrorRateInjector:
    """Injects error rate spikes."""

    def __init__(
        self,
        baseline_error_rate: float = 0.001,  # 0.1%
        anomaly_error_rate: float = 0.15,     # 15%
        spike_start: datetime | None = None,
        spike_duration: timedelta = timedelta(minutes=20)
    ) -> None:
        """Initialize error rate injector.

        Args:
            baseline_error_rate: Normal error rate (0-1)
            anomaly_error_rate: Error rate during anomaly
            spike_start: When to start spike
            spike_duration: How long spike lasts
        """
        self.baseline_error_rate = baseline_error_rate
        self.anomaly_error_rate = anomaly_error_rate
        self.spike_start = spike_start or datetime.utcnow()
        self.spike_duration = spike_duration

    def should_error(self, timestamp: datetime) -> bool:
        """Determine if current request should error.

        Args:
            timestamp: Current timestamp

        Returns:
            True if request should error
        """
        spike_end = self.spike_start + self.spike_duration

        if self.spike_start <= timestamp <= spike_end:
            error_rate = self.anomaly_error_rate
        else:
            error_rate = self.baseline_error_rate

        return random.random() < error_rate

    def get_error_rate(self, timestamp: datetime) -> float:
        """Get error rate for timestamp.

        Args:
            timestamp: Current timestamp

        Returns:
            Error rate (0-1)
        """
        spike_end = self.spike_start + self.spike_duration

        if self.spike_start <= timestamp <= spike_end:
            # Gradual ramp
            progress = (timestamp - self.spike_start) / self.spike_duration
            if progress < 0.2:
                return self.baseline_error_rate + (
                    self.anomaly_error_rate - self.baseline_error_rate
                ) * (progress / 0.2)
            elif progress > 0.8:
                return self.baseline_error_rate + (
                    self.anomaly_error_rate - self.baseline_error_rate
                ) * ((1 - progress) / 0.2)
            else:
                return self.anomaly_error_rate

        return self.baseline_error_rate


class ThroughputInjector:
    """Injects throughput changes (drops or spikes)."""

    def __init__(
        self,
        baseline_rps: float = 100.0,
        anomaly_multiplier: float = 0.3,  # 30% of baseline (drop)
        spike_start: datetime | None = None,
        spike_duration: timedelta = timedelta(minutes=10)
    ) -> None:
        """Initialize throughput injector.

        Args:
            baseline_rps: Normal requests per second
            anomaly_multiplier: Multiplier during anomaly (< 1 for drop, > 1 for spike)
            spike_start: When to start change
            spike_duration: How long change lasts
        """
        self.baseline_rps = baseline_rps
        self.anomaly_multiplier = anomaly_multiplier
        self.spike_start = spike_start or datetime.utcnow()
        self.spike_duration = spike_duration

    def get_throughput(self, timestamp: datetime) -> float:
        """Get throughput for timestamp.

        Args:
            timestamp: Current timestamp

        Returns:
            Requests per second
        """
        value = spike_pattern(
            baseline=self.baseline_rps,
            spike_multiplier=self.anomaly_multiplier,
            current_time=timestamp,
            spike_start=self.spike_start,
            spike_duration=self.spike_duration
        )

        # Add noise
        return max(0, jitter(value, 0.15))


class MemoryLeakInjector:
    """Simulates a memory leak pattern."""

    def __init__(
        self,
        baseline_mb: float = 512.0,
        leak_rate_mb_per_min: float = 50.0,
        max_memory_mb: float = 4096.0,
        leak_start: datetime | None = None
    ) -> None:
        """Initialize memory leak injector.

        Args:
            baseline_mb: Normal memory usage in MB
            leak_rate_mb_per_min: Memory increase per minute
            max_memory_mb: Maximum memory before crash
            leak_start: When leak starts
        """
        self.baseline_mb = baseline_mb
        self.leak_rate_mb_per_min = leak_rate_mb_per_min
        self.max_memory_mb = max_memory_mb
        self.leak_start = leak_start or datetime.utcnow()

    def get_memory_usage(self, timestamp: datetime) -> float:
        """Get memory usage for timestamp.

        Args:
            timestamp: Current timestamp

        Returns:
            Memory usage in MB
        """
        if timestamp < self.leak_start:
            return jitter(self.baseline_mb, 0.05)

        # Calculate leaked amount
        elapsed_minutes = (timestamp - self.leak_start).total_seconds() / 60
        leaked = self.leak_rate_mb_per_min * elapsed_minutes

        # Cap at max
        memory = min(self.baseline_mb + leaked, self.max_memory_mb)

        return jitter(memory, 0.05)

    def has_crashed(self, timestamp: datetime) -> bool:
        """Check if process has crashed due to OOM.

        Args:
            timestamp: Current timestamp

        Returns:
            True if crashed
        """
        return self.get_memory_usage(timestamp) >= self.max_memory_mb


class CPUSpikeInjector:
    """Injects CPU usage spikes."""

    def __init__(
        self,
        baseline_percent: float = 25.0,
        spike_percent: float = 95.0,
        spike_start: datetime | None = None,
        spike_duration: timedelta = timedelta(minutes=5)
    ) -> None:
        """Initialize CPU spike injector.

        Args:
            baseline_percent: Normal CPU usage percentage
            spike_percent: CPU usage during spike
            spike_start: When spike starts
            spike_duration: How long spike lasts
        """
        self.baseline_percent = baseline_percent
        self.spike_percent = spike_percent
        self.spike_start = spike_start or datetime.utcnow()
        self.spike_duration = spike_duration

    def get_cpu_usage(self, timestamp: datetime) -> float:
        """Get CPU usage for timestamp.

        Args:
            timestamp: Current timestamp

        Returns:
            CPU usage percentage
        """
        multiplier = self.spike_percent / self.baseline_percent

        value = spike_pattern(
            baseline=self.baseline_percent,
            spike_multiplier=multiplier,
            current_time=timestamp,
            spike_start=self.spike_start,
            spike_duration=self.spike_duration
        )

        # Ensure within bounds
        return min(100.0, max(0.0, jitter(value, 0.1)))
