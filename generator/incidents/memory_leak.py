"""Memory leak incident generator."""

import random
from datetime import datetime, timedelta
from typing import Any

from generator.core.base import BaseGenerator, IncidentContext
from generator.core.distributions import (
    UniformDistribution,
    LogNormalDistribution,
    CPU_DISTRIBUTION,
    MEMORY_DISTRIBUTION
)
from generator.core.patterns import (
    create_business_hours_pattern,
    NoisePattern
)
from generator.core.logging_config import get_logger
from generator.core.timeline import TimelineGenerator
from generator.core.utils import timestamp_to_iso, generate_uuid

logger = get_logger(__name__)

# Distributions for realistic data generation
_GC_PAUSE_DIST = LogNormalDistribution(mu=3, sigma=0.5)  # ~10-100ms


class MemoryLeakGenerator(BaseGenerator):
    """Generates a memory leak incident scenario.

    Simulates gradual memory exhaustion leading to OOM events, with correlated
    signals including increased GC pressure, reduced throughput, and eventual
    container restarts.
    """

    def __init__(
        self,
        context: IncidentContext,
        affected_service: str = "api-server",
        leak_rate_mb_per_min: float = 10.0,
        initial_memory_mb: float = 512.0,
        max_memory_mb: float = 2048.0,
        leak_pattern: str = "gradual"
    ) -> None:
        """Initialize memory leak generator.

        Args:
            context: Incident context
            affected_service: Service experiencing memory leak
            leak_rate_mb_per_min: Memory leak rate in MB/min
            initial_memory_mb: Initial memory usage
            max_memory_mb: Memory limit (triggers OOM)
            leak_pattern: "gradual" for slow leak, "rapid" for fast leak
        """
        super().__init__(context)
        self.affected_service = affected_service
        self.leak_rate_mb_per_min = leak_rate_mb_per_min
        self.initial_memory_mb = initial_memory_mb
        self.max_memory_mb = max_memory_mb
        self.leak_pattern = leak_pattern

        # Apply difficulty configuration if available
        if hasattr(context, 'difficulty_config') and context.difficulty_config:
            diff_config = context.difficulty_config
            noise_level = diff_config.noise_level

            # Adjust complexity based on difficulty
            if diff_config.level.value == 'beginner':
                # Make leak more obvious for beginners
                self.leak_rate_mb_per_min *= 1.5
                self.max_memory_mb *= 0.8
            elif diff_config.level.value == 'expert':
                # Slower, harder to detect leak for experts
                self.leak_rate_mb_per_min *= 0.5
                self.max_memory_mb *= 1.2

            self.log_volume_multiplier = diff_config.log_volume_multiplier
            self.metric_density_multiplier = diff_config.metric_density / 3.0

            logger.info(f"Applied {diff_config.level.value} difficulty adjustments: "
                       f"leak_rate={self.leak_rate_mb_per_min:.1f}MB/min, "
                       f"max_memory={self.max_memory_mb:.0f}MB, "
                       f"noise_level={noise_level:.2f}")
        else:
            noise_level = 0.05
            self.log_volume_multiplier = 1.0
            self.metric_density_multiplier = 1.0

        # Time-series patterns for realistic data
        self.request_rate_pattern = create_business_hours_pattern()
        self.memory_noise = NoisePattern(noise_level=noise_level)

        # Calculate when OOM will occur
        minutes_to_oom = (self.max_memory_mb - self.initial_memory_mb) / self.leak_rate_mb_per_min
        self.oom_time = context.start_time + timedelta(minutes=minutes_to_oom)

        # Update context
        context.affected_services = [affected_service]
        context.root_cause = f"Memory leak in {affected_service} causing gradual heap exhaustion and OOM events"

    def generate(self) -> dict[str, Any]:
        """Generate complete incident dataset.

        Returns:
            Summary of generated data
        """
        logger.info(f"Generating memory leak incident for {self.affected_service}...")
        logger.info(f"  Leak rate: {self.leak_rate_mb_per_min:.1f} MB/min")
        logger.info(f"  OOM expected at: {self.oom_time.isoformat()}")

        # Generate components
        logs = self._generate_logs()
        metrics = self._generate_metrics()
        traces = self._generate_traces()
        timeline = self._generate_timeline()

        logger.info(f"  Generated {len(logs)} log entries")
        logger.info(f"  Generated {len(metrics)} metric points")
        logger.info(f"  Generated {len(traces)} traces")
        logger.info(f"  Generated timeline with {len(timeline['events'])} events")

        # Save files
        self.save_jsonl(logs, f"logs_{self.context.incident_id}.jsonl", "logs")
        self.save_jsonl(metrics, f"metrics_{self.context.incident_id}.jsonl", "metrics")
        self.save_jsonl(traces, f"traces_{self.context.incident_id}.jsonl", "traces")
        self.save_json(timeline, f"timeline_{self.context.incident_id}.json", "timelines")

        return {
            "incident_id": self.context.incident_id,
            "incident_type": "memory_leak",
            "affected_service": self.affected_service,
            "log_count": len(logs),
            "metric_count": len(metrics),
            "trace_count": len(traces)
        }

    def _generate_logs(self) -> list[dict[str, Any]]:
        """Generate log entries."""
        logs = []
        hosts = self._get_service_hosts(self.affected_service)

        # Log sampling rate based on difficulty
        log_sample_rate = 0.05 * self.log_volume_multiplier

        for current_time in self._iterate_time_window(step=timedelta(minutes=1)):
            for host in hosts:
                # Baseline application logs
                if self._should_generate_log(log_sample_rate):
                    logs.append({
                        "timestamp": timestamp_to_iso(current_time),
                        "level": "INFO",
                        "service": self.affected_service,
                        "host": host,
                        "message": f"Processing request batch on {host}",
                        "request_id": generate_uuid()
                    })

                # Memory-related logs increase as we approach OOM
                memory_used_mb = self._calculate_memory_at_time(current_time)
                memory_pressure = memory_used_mb / self.max_memory_mb

                # GC logs (increase frequency as memory pressure grows)
                if self._should_generate_log(0.2 * memory_pressure):
                    gc_duration_ms = _GC_PAUSE_DIST.sample() * (1 + memory_pressure * 3)
                    logs.append({
                        "timestamp": timestamp_to_iso(current_time),
                        "level": "WARN" if gc_duration_ms > 100 else "INFO",
                        "service": self.affected_service,
                        "host": host,
                        "message": f"GC pause: {gc_duration_ms:.1f}ms (heap: {memory_used_mb:.0f}MB / {self.max_memory_mb:.0f}MB)",
                        "gc_pause_ms": gc_duration_ms,
                        "heap_usage_mb": memory_used_mb,
                        "heap_max_mb": self.max_memory_mb
                    })

                # Memory warnings as we approach limit
                if memory_pressure > 0.8 and self._should_generate_log(0.3):
                    logs.append({
                        "timestamp": timestamp_to_iso(current_time),
                        "level": "WARN",
                        "service": self.affected_service,
                        "host": host,
                        "message": f"High memory usage: {memory_pressure*100:.1f}% ({memory_used_mb:.0f}MB / {self.max_memory_mb:.0f}MB)",
                        "memory_usage_percent": memory_pressure * 100,
                        "heap_usage_mb": memory_used_mb
                    })

                # OOM killer events
                if current_time >= self.oom_time and current_time < self.oom_time + timedelta(minutes=5):
                    if self._should_generate_log(0.5):
                        logs.append({
                            "timestamp": timestamp_to_iso(current_time),
                            "level": "ERROR",
                            "service": self.affected_service,
                            "host": host,
                            "message": f"OutOfMemoryError: Java heap space - heap usage {memory_used_mb:.0f}MB exceeds limit {self.max_memory_mb:.0f}MB",
                            "error_type": "OutOfMemoryError",
                            "heap_usage_mb": memory_used_mb,
                            "heap_max_mb": self.max_memory_mb
                        })

                # Container restart logs
                restart_window_start = self.oom_time + timedelta(minutes=2)
                restart_window_end = restart_window_start + timedelta(minutes=3)
                if restart_window_start <= current_time < restart_window_end:
                    if self._should_generate_log(0.2):
                        logs.append({
                            "timestamp": timestamp_to_iso(current_time),
                            "level": "INFO",
                            "service": self.affected_service,
                            "host": host,
                            "message": f"Container {host} restarting due to OOM kill",
                            "restart_reason": "OOMKilled",
                            "exit_code": 137
                        })

        return sorted(logs, key=lambda x: x["timestamp"])

    def _generate_metrics(self) -> list[dict[str, Any]]:
        """Generate metric data points."""
        metrics = []
        hosts = self._get_service_hosts(self.affected_service)

        # Metric sampling interval based on difficulty
        metric_step = timedelta(seconds=60 / self.metric_density_multiplier)

        for current_time in self._iterate_time_window(step=metric_step):
            memory_used_mb = self._calculate_memory_at_time(current_time)
            memory_pressure = memory_used_mb / self.max_memory_mb

            for host in hosts:
                # Memory usage (gradually increasing)
                metrics.append({
                    "timestamp": timestamp_to_iso(current_time),
                    "metric_name": "memory_usage_mb",
                    "value": self.memory_noise.apply(memory_used_mb),
                    "service": self.affected_service,
                    "host": host,
                    "metric_type": "gauge",
                    "anomaly_injected": memory_pressure > 0.7
                })

                # Memory usage percentage
                metrics.append({
                    "timestamp": timestamp_to_iso(current_time),
                    "metric_name": "memory_usage_percent",
                    "value": self.memory_noise.apply(memory_pressure * 100),
                    "service": self.affected_service,
                    "host": host,
                    "metric_type": "gauge",
                    "anomaly_injected": memory_pressure > 0.7
                })

                # GC pause duration (increases with memory pressure)
                gc_pause_ms = _GC_PAUSE_DIST.sample() * (1 + memory_pressure * 5)
                metrics.append({
                    "timestamp": timestamp_to_iso(current_time),
                    "metric_name": "gc_pause_duration_ms",
                    "value": gc_pause_ms,
                    "service": self.affected_service,
                    "host": host,
                    "metric_type": "gauge",
                    "anomaly_injected": gc_pause_ms > 50
                })

                # GC collection frequency (increases with pressure)
                gc_rate = 5 + (memory_pressure * 45)  # 5-50 collections/min
                metrics.append({
                    "timestamp": timestamp_to_iso(current_time),
                    "metric_name": "gc_collection_count",
                    "value": gc_rate,
                    "service": self.affected_service,
                    "host": host,
                    "metric_type": "gauge",
                    "anomaly_injected": memory_pressure > 0.6
                })

                # Throughput degradation (decreases as GC pressure increases)
                baseline_throughput = 1000
                throughput = baseline_throughput * (1 - memory_pressure * 0.7)
                metrics.append({
                    "timestamp": timestamp_to_iso(current_time),
                    "metric_name": "requests_per_second",
                    "value": max(0, throughput),
                    "service": self.affected_service,
                    "host": host,
                    "metric_type": "gauge",
                    "anomaly_injected": memory_pressure > 0.5
                })

                # Container restart count
                if current_time >= self.oom_time:
                    restart_count = 1 + int((current_time - self.oom_time).total_seconds() / 600)
                    metrics.append({
                        "timestamp": timestamp_to_iso(current_time),
                        "metric_name": "container_restart_count",
                        "value": restart_count,
                        "service": self.affected_service,
                        "host": host,
                        "metric_type": "counter",
                        "anomaly_injected": True
                    })

        return sorted(metrics, key=lambda x: x["timestamp"])

    def _generate_traces(self) -> list[dict[str, Any]]:
        """Generate distributed trace data."""
        traces = []
        hosts = self._get_service_hosts(self.affected_service)

        # Generate trace every 5 minutes
        for current_time in self._iterate_time_window(step=timedelta(minutes=5)):
            memory_pressure = self._calculate_memory_at_time(current_time) / self.max_memory_mb

            # Higher memory pressure = slower traces
            base_duration_ms = 50
            duration_ms = base_duration_ms * (1 + memory_pressure * 10)

            host = random.choice(hosts)

            trace = {
                "trace_id": generate_uuid(),
                "timestamp": timestamp_to_iso(current_time),
                "duration_ms": duration_ms,
                "service": self.affected_service,
                "spans": [
                    {
                        "span_id": generate_uuid(),
                        "service": self.affected_service,
                        "operation": "process_request",
                        "start_time": timestamp_to_iso(current_time),
                        "duration_ms": duration_ms,
                        "host": host,
                        "tags": {
                            "http.method": "POST",
                            "http.status_code": 200 if memory_pressure < 0.95 else 503,
                            "memory_pressure": round(memory_pressure, 2)
                        }
                    }
                ]
            }

            traces.append(trace)

        return sorted(traces, key=lambda x: x["timestamp"])

    def _generate_timeline(self) -> dict[str, Any]:
        """Generate incident timeline."""
        timeline_gen = TimelineGenerator(self.context)

        # Add leak detection event
        detection_time = self.context.start_time + timedelta(
            minutes=(self.oom_time - self.context.start_time).total_seconds() / 60 * 0.7
        )
        timeline_gen.add_event(
            timestamp=detection_time,
            event_type="detection",
            description=f"High memory usage detected on {self.affected_service}",
            severity="warning"
        )

        # Add OOM event
        timeline_gen.add_event(
            timestamp=self.oom_time,
            event_type="failure",
            description=f"OutOfMemoryError triggered on {self.affected_service}",
            severity="critical"
        )

        # Add restart event
        restart_time = self.oom_time + timedelta(minutes=2)
        timeline_gen.add_event(
            timestamp=restart_time,
            event_type="mitigation",
            description=f"Container restart initiated for {self.affected_service}",
            severity="warning"
        )

        return timeline_gen.generate()

    def _calculate_memory_at_time(self, timestamp: datetime) -> float:
        """Calculate memory usage at a specific timestamp.

        Args:
            timestamp: Time to calculate memory for

        Returns:
            Memory usage in MB
        """
        if timestamp < self.context.start_time:
            return self.initial_memory_mb

        elapsed_minutes = (timestamp - self.context.start_time).total_seconds() / 60

        if self.leak_pattern == "gradual":
            # Linear memory growth
            memory_mb = self.initial_memory_mb + (self.leak_rate_mb_per_min * elapsed_minutes)
        else:  # rapid
            # Exponential memory growth
            growth_factor = 1.1 ** (elapsed_minutes / 10)
            memory_mb = self.initial_memory_mb * growth_factor

        # Cap at max memory
        return min(memory_mb, self.max_memory_mb)

