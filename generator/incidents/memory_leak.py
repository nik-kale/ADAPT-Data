"""Memory leak incident generator."""

from datetime import datetime, timedelta
from typing import Any, Optional

from generator.anomalies.injectors import MemoryLeakInjector
from generator.core.base import BaseGenerator, IncidentContext
from generator.core.correlation import CorrelationGenerator
from generator.core.logging_config import get_logger
from generator.core.patterns import NoisePattern, create_business_hours_pattern
from generator.core.timeline import TimelineGenerator
from generator.core.utils import generate_uuid, jitter, timestamp_to_iso

logger = get_logger(__name__)

# Heap pressure drives garbage collection: as headroom shrinks, collections get
# both longer and more frequent. These shape that relationship.
_GC_PAUSE_BASELINE_MS = 8.0
_GC_PAUSE_MAX_MULTIPLIER = 25.0
_GC_BASELINE_PER_MINUTE = 2.0
_GC_MAX_PER_MINUTE = 40.0


class MemoryLeakGenerator(BaseGenerator):
    """Generates a memory leak incident scenario.

    Simulates a service leaking heap over time until it hits its container
    memory limit and is OOM-killed. The distinguishing signal is the shape:
    memory climbs steadily rather than spiking, garbage collection degrades
    alongside it, and throughput falls away as the process spends more of its
    time collecting instead of serving.
    """

    def __init__(
        self,
        context: IncidentContext,
        affected_service: str = "order-service",
        initial_memory_mb: float = 512.0,
        leak_rate_mb_per_min: float = 10.0,
        max_memory_mb: float = 2048.0,
        restart_on_oom: bool = True,
        correlation_density: float = 0.8,
    ) -> None:
        """Initialize memory leak generator.

        Args:
            context: Incident context
            affected_service: Service leaking memory
            initial_memory_mb: Steady-state memory before the leak begins
            leak_rate_mb_per_min: Megabytes leaked per minute
            max_memory_mb: Container memory limit; reaching it triggers an OOM kill
            restart_on_oom: Whether the process restarts (and memory resets) after OOM
            correlation_density: Fraction of records carrying a correlation ID

        Raises:
            ValueError: If the memory limit is not above the initial usage, or
                the leak rate is not positive
        """
        super().__init__(context)

        if max_memory_mb <= initial_memory_mb:
            raise ValueError(
                f"max_memory_mb ({max_memory_mb}) must be greater than "
                f"initial_memory_mb ({initial_memory_mb})"
            )
        if leak_rate_mb_per_min <= 0:
            raise ValueError(f"leak_rate_mb_per_min must be positive, got {leak_rate_mb_per_min}")

        self.affected_service = affected_service
        self.initial_memory_mb = initial_memory_mb
        self.leak_rate_mb_per_min = leak_rate_mb_per_min
        self.max_memory_mb = max_memory_mb
        self.restart_on_oom = restart_on_oom

        # Apply difficulty configuration if available
        if getattr(context, "difficulty_config", None):
            diff_config = context.difficulty_config
            noise_level = diff_config.noise_level

            if diff_config.level.value == "beginner":
                # Leak fast and obviously: the signal should be hard to miss.
                self.leak_rate_mb_per_min *= 2.0
            elif diff_config.level.value == "expert":
                # A slow leak that may not reach the limit inside the window.
                self.leak_rate_mb_per_min *= 0.5

            self.log_volume_multiplier = diff_config.log_volume_multiplier
            logger.info(
                f"Applied {diff_config.level.value} difficulty adjustments: "
                f"leak_rate={self.leak_rate_mb_per_min:.1f}MB/min, "
                f"noise_level={noise_level:.2f}"
            )
        else:
            noise_level = 0.05
            self.log_volume_multiplier = 1.0

        self.noise = NoisePattern(noise_level=noise_level)
        self.request_rate_pattern = create_business_hours_pattern()
        self.correlation = CorrelationGenerator(density=correlation_density)

        self.injector = MemoryLeakInjector(
            baseline_mb=self.initial_memory_mb,
            leak_rate_mb_per_min=self.leak_rate_mb_per_min,
            max_memory_mb=self.max_memory_mb,
            leak_start=context.start_time,
        )

        # Update context
        context.affected_services = [affected_service]
        context.root_cause = (
            f"Memory leak in {affected_service}: unbounded cache growth retains "
            f"objects across requests, exhausting the {max_memory_mb:.0f}MB heap limit"
        )

    def _oom_time(self) -> Optional[datetime]:
        """Return when the leak first reaches the memory limit.

        Returns:
            Timestamp of the OOM kill, or None if the limit is never reached
            inside the generation window.
        """
        minutes_to_oom = (self.max_memory_mb - self.initial_memory_mb) / self.leak_rate_mb_per_min
        oom_time = self.context.start_time + timedelta(minutes=minutes_to_oom)

        return oom_time if oom_time <= self.context.end_time else None

    def _memory_pressure(self, timestamp: datetime) -> float:
        """Fraction of the memory limit currently consumed, from 0.0 to 1.0.

        Args:
            timestamp: Current timestamp

        Returns:
            Heap utilisation ratio, clamped to [0.0, 1.0]
        """
        projected = self.injector.get_projected_memory_usage(timestamp)
        return max(0.0, min(1.0, projected / self.max_memory_mb))

    def generate(self) -> dict[str, Any]:
        """Generate complete incident dataset.

        Returns:
            Summary of generated data
        """
        logger.info(f"Generating memory leak incident for {self.affected_service}...")

        logs = self._generate_logs()
        metrics = self._generate_metrics()
        traces = self._generate_traces()
        config_deltas = self._generate_config_deltas()
        timeline = self._generate_timeline()

        logger.info(f"  Generated {len(logs)} log entries")
        logger.info(f"  Generated {len(metrics)} metric points")
        logger.info(f"  Generated {len(traces)} traces")
        logger.info(f"  Generated {len(config_deltas)} config changes")
        logger.info(f"  Generated timeline with {len(timeline['events'])} events")

        self.save_jsonl(logs, f"logs_{self.context.incident_id}.jsonl", "logs")
        self.save_jsonl(metrics, f"metrics_{self.context.incident_id}.jsonl", "metrics")
        self.save_jsonl(traces, f"traces_{self.context.incident_id}.jsonl", "traces")
        self.save_jsonl(config_deltas, f"config_{self.context.incident_id}.jsonl", "config_deltas")

        return {
            "incident_id": self.context.incident_id,
            "incident_type": "memory_leak",
            "affected_service": self.affected_service,
            "log_count": len(logs),
            "metric_count": len(metrics),
            "trace_count": len(traces),
            "config_change_count": len(config_deltas),
        }

    def _generate_logs(self) -> list[dict[str, Any]]:
        """Generate log entries."""
        logs = []
        hosts = self._get_service_hosts(self.affected_service)
        oom_time = self._oom_time()

        for current_time in self._iterate_time_window(step=timedelta(seconds=10)):
            pressure = self._memory_pressure(current_time)

            for host in hosts:
                base_rate = 0.3 * self.log_volume_multiplier
                request_rate = self.request_rate_pattern.apply(base_rate, current_time)

                if self._should_generate_log(request_rate):
                    scope = self.correlation.new_scope()

                    log_entry = {
                        "timestamp": timestamp_to_iso(current_time),
                        "level": "INFO",
                        "service": self.affected_service,
                        "host": host,
                        "message": "HTTP POST /api/orders",
                        "metadata": {
                            "endpoint": "/api/orders",
                            "method": "POST",
                            "status_code": 200,
                            "duration_ms": round(jitter(45.0 * (1 + pressure * 2), 0.2), 2),
                        },
                    }
                    if scope:
                        scope.stamp_log(log_entry)
                    logs.append(log_entry)

                # Heap warnings begin once the process is meaningfully squeezed.
                if pressure > 0.75 and self._should_generate_log(0.15 * (pressure - 0.75) * 4):
                    scope = self.correlation.new_scope()
                    heap_log = {
                        "timestamp": timestamp_to_iso(current_time),
                        "level": "WARN",
                        "service": self.affected_service,
                        "host": host,
                        "message": "Heap usage above threshold, GC pressure increasing",
                        "metadata": {
                            "heap_used_mb": round(self.injector.get_memory_usage(current_time), 1),
                            "heap_max_mb": self.max_memory_mb,
                            "heap_utilization_percent": round(pressure * 100, 1),
                            "error_code": "HEAP_PRESSURE",
                        },
                    }
                    if scope:
                        scope.stamp_log(heap_log)
                    logs.append(heap_log)

                # Allocation failures appear only in the final stretch.
                if pressure > 0.95 and self._should_generate_log(0.2):
                    scope = self.correlation.new_scope()
                    alloc_log = {
                        "timestamp": timestamp_to_iso(current_time),
                        "level": "ERROR",
                        "service": self.affected_service,
                        "host": host,
                        "message": "Allocation failed: unable to reserve memory for request buffer",
                        "metadata": {
                            "heap_used_mb": round(self.injector.get_memory_usage(current_time), 1),
                            "heap_max_mb": self.max_memory_mb,
                            "status_code": 503,
                            "error_code": "OUT_OF_MEMORY",
                        },
                    }
                    if scope:
                        scope.stamp_log(alloc_log)
                    logs.append(alloc_log)

        # OOM kill and restart are single, decisive events.
        if oom_time:
            for host in hosts:
                logs.append(
                    {
                        "timestamp": timestamp_to_iso(oom_time),
                        "level": "FATAL",
                        "service": self.affected_service,
                        "host": host,
                        "message": (
                            f"Container killed: memory limit of "
                            f"{self.max_memory_mb:.0f}MB exceeded (OOMKilled)"
                        ),
                        "metadata": {
                            "heap_max_mb": self.max_memory_mb,
                            "error_code": "OOM_KILLED",
                            "exit_code": 137,
                        },
                    }
                )

                if self.restart_on_oom:
                    logs.append(
                        {
                            "timestamp": timestamp_to_iso(oom_time + timedelta(seconds=20)),
                            "level": "INFO",
                            "service": self.affected_service,
                            "host": host,
                            "message": "Container restarted, heap reset to baseline",
                            "metadata": {
                                "heap_used_mb": round(self.initial_memory_mb, 1),
                                "restart_count": 1,
                            },
                        }
                    )

        logs.sort(key=lambda entry: entry["timestamp"])
        return logs

    def _generate_metrics(self) -> list[dict[str, Any]]:
        """Generate metrics."""
        metrics = []
        hosts = self._get_service_hosts(self.affected_service)
        oom_time = self._oom_time()

        for current_time in self._iterate_time_window(step=timedelta(minutes=1)):
            is_anomaly = self.context.is_during_incident(current_time)
            pressure = self._memory_pressure(current_time)

            for host in hosts:
                memory_mb = self.injector.get_memory_usage(current_time)

                # Memory resets to baseline after the OOM restart.
                if oom_time and self.restart_on_oom and current_time > oom_time:
                    minutes_since = (current_time - oom_time).total_seconds() / 60
                    memory_mb = min(
                        self.initial_memory_mb + self.leak_rate_mb_per_min * minutes_since,
                        self.max_memory_mb,
                    )
                    pressure = memory_mb / self.max_memory_mb

                gc_pause = _GC_PAUSE_BASELINE_MS * (
                    1 + (_GC_PAUSE_MAX_MULTIPLIER - 1) * (pressure**3)
                )
                gc_rate = _GC_BASELINE_PER_MINUTE + (
                    _GC_MAX_PER_MINUTE - _GC_BASELINE_PER_MINUTE
                ) * (pressure**2)

                scope = self.correlation.new_scope()
                sample = [
                    {
                        "timestamp": timestamp_to_iso(current_time),
                        "metric_name": "process_memory_usage_bytes",
                        "value": round(memory_mb * 1024 * 1024, 0),
                        "service": self.affected_service,
                        "metric_type": "gauge",
                        "unit": "bytes",
                        "host": host,
                        "tags": {"limit_mb": str(int(self.max_memory_mb))},
                        "anomaly_injected": is_anomaly,
                    },
                    {
                        "timestamp": timestamp_to_iso(current_time),
                        "metric_name": "process_memory_utilization_percent",
                        "value": round(pressure * 100, 2),
                        "service": self.affected_service,
                        "metric_type": "gauge",
                        "unit": "percent",
                        "host": host,
                        "tags": {},
                        "anomaly_injected": is_anomaly,
                    },
                    {
                        "timestamp": timestamp_to_iso(current_time),
                        "metric_name": "gc_pause_duration_ms",
                        "value": round(self.noise.apply(gc_pause, current_time), 2),
                        "service": self.affected_service,
                        "metric_type": "gauge",
                        "unit": "ms",
                        "host": host,
                        "tags": {"collector": "g1"},
                        "anomaly_injected": is_anomaly,
                    },
                    {
                        "timestamp": timestamp_to_iso(current_time),
                        "metric_name": "gc_collections_per_minute",
                        "value": round(self.noise.apply(gc_rate, current_time), 2),
                        "service": self.affected_service,
                        "metric_type": "gauge",
                        "unit": "collections",
                        "host": host,
                        "tags": {"collector": "g1"},
                        "anomaly_injected": is_anomaly,
                    },
                    {
                        # Throughput falls as GC eats an increasing share of CPU.
                        "timestamp": timestamp_to_iso(current_time),
                        "metric_name": "http_requests_per_second",
                        "value": round(
                            self.noise.apply(120.0 * (1 - 0.6 * pressure**2), current_time), 2
                        ),
                        "service": self.affected_service,
                        "metric_type": "gauge",
                        "unit": "requests",
                        "host": host,
                        "tags": {"endpoint": "/api/orders"},
                        "anomaly_injected": is_anomaly,
                    },
                ]

                if scope:
                    for metric in sample:
                        scope.stamp_metric(metric)

                metrics.extend(sample)

                if oom_time and current_time >= oom_time:
                    metrics.append(
                        {
                            "timestamp": timestamp_to_iso(current_time),
                            "metric_name": "container_restarts_total",
                            "value": 1,
                            "service": self.affected_service,
                            "metric_type": "counter",
                            "unit": "restarts",
                            "host": host,
                            "tags": {"reason": "OOMKilled"},
                            "anomaly_injected": True,
                        }
                    )

        return metrics

    def _generate_traces(self) -> list[dict[str, Any]]:
        """Generate distributed traces."""
        traces = []
        sample_count = 20

        for i in range(sample_count):
            trace_time = self.context.start_time + (self.context.duration / sample_count) * i
            pressure = self._memory_pressure(trace_time)

            # GC pauses land inside request handling, inflating tail latency.
            gc_penalty = _GC_PAUSE_BASELINE_MS * (
                1 + (_GC_PAUSE_MAX_MULTIPLIER - 1) * (pressure**3)
            )
            handler_duration = jitter(45.0 + gc_penalty, 0.2)
            failed = pressure > 0.95

            trace_id = generate_uuid()
            trace = {
                "trace_id": trace_id,
                "timestamp": timestamp_to_iso(trace_time),
                "spans": [
                    {
                        "span_id": generate_uuid(),
                        "parent_span_id": None,
                        "service": "api-gateway",
                        "operation": "HTTP POST /api/orders",
                        "start_time": timestamp_to_iso(trace_time),
                        "duration_ms": round(handler_duration + 8, 2),
                        "status": "ERROR" if failed else "OK",
                        "tags": {"http.method": "POST", "http.path": "/api/orders"},
                    },
                    {
                        "span_id": generate_uuid(),
                        "parent_span_id": trace_id,
                        "service": self.affected_service,
                        "operation": "createOrder",
                        "start_time": timestamp_to_iso(trace_time + timedelta(milliseconds=3)),
                        "duration_ms": round(handler_duration, 2),
                        "status": "ERROR" if failed else "OK",
                        "tags": {
                            "heap_utilization_percent": round(pressure * 100, 1),
                            "gc_pause_ms": round(gc_penalty, 2),
                        },
                    },
                    {
                        "span_id": generate_uuid(),
                        "parent_span_id": trace_id,
                        "service": "postgres-primary",
                        "operation": "INSERT orders",
                        "start_time": timestamp_to_iso(trace_time + timedelta(milliseconds=6)),
                        "duration_ms": round(jitter(12.0, 0.3), 2),
                        "status": "OK",
                        "tags": {"db.statement": "INSERT INTO orders (...) VALUES (...)"},
                    },
                ],
            }

            scope = self.correlation.new_scope()
            if scope:
                scope.stamp_trace(trace)

            traces.append(trace)

        return traces

    def _generate_config_deltas(self) -> list[dict[str, Any]]:
        """Generate configuration changes."""
        # The release that introduced the leak.
        deployment_time = self.context.start_time - timedelta(minutes=8)

        return [
            {
                "timestamp": timestamp_to_iso(deployment_time),
                "service": self.affected_service,
                "change_type": "deployment",
                "initiator": "ci-cd-pipeline",
                "changes": [
                    {
                        "key": "version",
                        "old_value": "2.4.0",
                        "new_value": "2.5.0",
                        "category": "infrastructure",
                    },
                    {
                        "key": "cache.entry_ttl_seconds",
                        "old_value": "300",
                        "new_value": "0",
                        "category": "performance",
                    },
                ],
                "rollback_available": True,
            }
        ]

    def _generate_timeline(self) -> dict[str, Any]:
        """Generate incident timeline."""
        timeline = TimelineGenerator(self.context)
        oom_time = self._oom_time()

        deployment_time = self.context.start_time - timedelta(minutes=8)
        timeline.add_deployment(deployment_time, self.affected_service, "2.4.0", "2.5.0")

        detection_time = self.context.start_time + timedelta(minutes=5)
        timeline.add_anomaly_detection(
            detection_time,
            self.affected_service,
            "process_memory_utilization_percent",
            threshold=80.0,
            actual_value=85.0,
        )

        timeline.add_alert(
            self.context.start_time + timedelta(minutes=6),
            self.affected_service,
            "Memory utilization trending toward limit",
            severity="warning",
        )

        if oom_time:
            timeline.add_alert(
                oom_time,
                self.affected_service,
                f"Container OOMKilled at {self.max_memory_mb:.0f}MB limit",
                severity="critical",
            )

        mitigation_time = self.context.end_time - timedelta(minutes=5)
        timeline.add_mitigation(
            mitigation_time,
            self.affected_service,
            "Rolled back to 2.4.0, restoring cache entry TTL",
        )

        timeline.add_resolution(
            self.context.end_time,
            "Rollback completed, heap usage stable at baseline",
        )

        return timeline.generate()
