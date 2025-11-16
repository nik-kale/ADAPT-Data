"""Bursty noise incident generator."""

import random
from datetime import datetime, timedelta
from typing import Any

from generator.core.base import BaseGenerator, IncidentContext
from generator.core.timeline import TimelineGenerator
from generator.core.utils import timestamp_to_iso, generate_uuid, gaussian_noise


class BurstyNoiseGenerator(BaseGenerator):
    """Generates a bursty noise / noisy neighbor incident.

    Simulates scenarios where resource contention or external factors
    cause intermittent performance degradation with high variance.
    """

    def __init__(
        self,
        context: IncidentContext,
        affected_service: str = "user-service",
        burst_frequency_minutes: int = 5,
        burst_duration_seconds: int = 30
    ) -> None:
        """Initialize bursty noise generator.

        Args:
            context: Incident context
            affected_service: Service experiencing noise
            burst_frequency_minutes: How often bursts occur
            burst_duration_seconds: How long each burst lasts
        """
        super().__init__(context)
        self.affected_service = affected_service
        self.burst_frequency_minutes = burst_frequency_minutes
        self.burst_duration_seconds = burst_duration_seconds

        context.affected_services = [affected_service]
        context.root_cause = f"Resource contention from noisy neighbor causing intermittent performance bursts in {affected_service}"

    def generate(self) -> dict[str, Any]:
        """Generate complete incident dataset."""
        print(f"Generating bursty noise incident for {self.affected_service}...")

        logs = self._generate_logs()
        metrics = self._generate_metrics()
        traces = self._generate_traces()
        config_deltas = self._generate_config_deltas()
        timeline = self._generate_timeline()

        print(f"  Generated {len(logs)} log entries")
        print(f"  Generated {len(metrics)} metric points")
        print(f"  Generated {len(traces)} traces")

        self.save_jsonl(logs, f"logs_{self.context.incident_id}.jsonl", "logs")
        self.save_jsonl(metrics, f"metrics_{self.context.incident_id}.jsonl", "metrics")
        self.save_jsonl(traces, f"traces_{self.context.incident_id}.jsonl", "traces")
        self.save_jsonl(config_deltas, f"config_{self.context.incident_id}.jsonl", "config_deltas")

        return {
            "incident_id": self.context.incident_id,
            "incident_type": "bursty_noise",
            "affected_service": self.affected_service,
            "log_count": len(logs),
            "metric_count": len(metrics),
            "trace_count": len(traces)
        }

    def _is_in_burst(self, timestamp: datetime) -> bool:
        """Check if timestamp falls within a burst period."""
        if not self.context.is_during_incident(timestamp):
            return False

        # Calculate burst windows
        elapsed_seconds = (timestamp - self.context.start_time).total_seconds()
        cycle_seconds = self.burst_frequency_minutes * 60
        position_in_cycle = elapsed_seconds % cycle_seconds

        return position_in_cycle < self.burst_duration_seconds

    def _generate_logs(self) -> list[dict[str, Any]]:
        """Generate log entries."""
        logs = []
        hosts = self._get_service_hosts(self.affected_service)

        current_time = self.context.start_time - timedelta(minutes=30)
        end_time = self.context.end_time + timedelta(minutes=30)

        while current_time < end_time:
            in_burst = self._is_in_burst(current_time)

            for host in hosts:
                if random.random() < 0.1:
                    if in_burst:
                        # High CPU / resource contention messages
                        messages = [
                            "High CPU usage detected",
                            "Thread pool saturation warning",
                            "GC pressure - long pause detected",
                            "Slow request processing due to resource contention"
                        ]
                        logs.append({
                            "timestamp": timestamp_to_iso(current_time),
                            "level": "WARN",
                            "service": self.affected_service,
                            "host": host,
                            "message": random.choice(messages),
                            "metadata": {
                                "cpu_percent": random.uniform(85, 99),
                                "gc_pause_ms": random.uniform(500, 2000),
                                "request_id": generate_uuid()
                            }
                        })
                    else:
                        logs.append({
                            "timestamp": timestamp_to_iso(current_time),
                            "level": "INFO",
                            "service": self.affected_service,
                            "host": host,
                            "message": "Request processed",
                            "metadata": {
                                "duration_ms": random.uniform(20, 60),
                                "request_id": generate_uuid()
                            }
                        })

            current_time += timedelta(seconds=1)

        return logs

    def _generate_metrics(self) -> list[dict[str, Any]]:
        """Generate metrics with bursty pattern."""
        metrics = []
        hosts = self._get_service_hosts(self.affected_service)

        current_time = self.context.start_time - timedelta(minutes=30)
        end_time = self.context.end_time + timedelta(minutes=30)

        while current_time < end_time:
            in_burst = self._is_in_burst(current_time)

            for host in hosts:
                # Base values with noise
                base_cpu = 25.0 if not in_burst else 92.0
                base_latency = 50.0 if not in_burst else 450.0
                base_memory = 512.0 if not in_burst else 850.0

                # Add significant noise
                cpu = max(0, min(100, base_cpu + gaussian_noise(0, 8)))
                latency = max(0, base_latency + gaussian_noise(0, base_latency * 0.3))
                memory = max(0, base_memory + gaussian_noise(0, base_memory * 0.1))

                metrics.extend([
                    {
                        "timestamp": timestamp_to_iso(current_time),
                        "metric_name": "cpu_usage_percent",
                        "value": round(cpu, 2),
                        "service": self.affected_service,
                        "metric_type": "gauge",
                        "unit": "percent",
                        "host": host,
                        "tags": {},
                        "anomaly_injected": in_burst
                    },
                    {
                        "timestamp": timestamp_to_iso(current_time),
                        "metric_name": "http_request_duration_p95",
                        "value": round(latency, 2),
                        "service": self.affected_service,
                        "metric_type": "gauge",
                        "unit": "ms",
                        "host": host,
                        "tags": {},
                        "anomaly_injected": in_burst
                    },
                    {
                        "timestamp": timestamp_to_iso(current_time),
                        "metric_name": "memory_usage_mb",
                        "value": round(memory, 2),
                        "service": self.affected_service,
                        "metric_type": "gauge",
                        "unit": "MB",
                        "host": host,
                        "tags": {},
                        "anomaly_injected": in_burst
                    },
                    {
                        "timestamp": timestamp_to_iso(current_time),
                        "metric_name": "gc_pause_duration_ms",
                        "value": round(random.uniform(800, 2000) if in_burst else random.uniform(5, 50), 2),
                        "service": self.affected_service,
                        "metric_type": "gauge",
                        "unit": "ms",
                        "host": host,
                        "tags": {},
                        "anomaly_injected": in_burst
                    }
                ])

            current_time += timedelta(minutes=1)

        return metrics

    def _generate_traces(self) -> list[dict[str, Any]]:
        """Generate distributed traces."""
        traces = []
        current_time = self.context.start_time
        sample_count = 20

        for i in range(sample_count):
            trace_time = current_time + (self.context.duration / sample_count) * i
            in_burst = self._is_in_burst(trace_time)

            base_duration = 450 if in_burst else 50
            duration = base_duration + gaussian_noise(0, base_duration * 0.2)

            trace_id = generate_uuid()
            traces.append({
                "trace_id": trace_id,
                "timestamp": timestamp_to_iso(trace_time),
                "spans": [
                    {
                        "span_id": generate_uuid(),
                        "parent_span_id": None,
                        "service": "api-gateway",
                        "operation": "HTTP GET /api/users/{id}",
                        "start_time": timestamp_to_iso(trace_time),
                        "duration_ms": round(duration + 15, 2),
                        "status": "OK",
                        "tags": {"http.method": "GET"}
                    },
                    {
                        "span_id": generate_uuid(),
                        "parent_span_id": trace_id,
                        "service": self.affected_service,
                        "operation": "getUser",
                        "start_time": timestamp_to_iso(trace_time + timedelta(milliseconds=3)),
                        "duration_ms": round(duration, 2),
                        "status": "OK",
                        "tags": {"cpu_throttled": in_burst}
                    }
                ]
            })

        return traces

    def _generate_config_deltas(self) -> list[dict[str, Any]]:
        """Generate configuration changes."""
        # Deployment of new noisy workload
        change_time = self.context.start_time - timedelta(minutes=15)

        return [
            {
                "timestamp": timestamp_to_iso(change_time),
                "service": "batch-processor",  # noisy neighbor
                "change_type": "deployment",
                "initiator": "ci-cd-pipeline",
                "changes": [
                    {
                        "key": "batch_size",
                        "old_value": 100,
                        "new_value": 10000,
                        "category": "performance"
                    }
                ],
                "rollback_available": True
            }
        ]

    def _generate_timeline(self) -> dict[str, Any]:
        """Generate incident timeline."""
        timeline = TimelineGenerator(self.context)

        change_time = self.context.start_time - timedelta(minutes=15)
        timeline.add_deployment(
            change_time,
            "batch-processor",
            "1.0.0",
            "1.1.0"
        )

        detection_time = self.context.start_time + timedelta(minutes=5)
        timeline.add_anomaly_detection(
            detection_time,
            self.affected_service,
            "cpu_usage_percent",
            threshold=70.0,
            actual_value=92.0
        )

        alert_time = self.context.start_time + timedelta(minutes=7)
        timeline.add_alert(
            alert_time,
            self.affected_service,
            "Intermittent CPU spikes and latency variance",
            severity="warning"
        )

        mitigation_time = self.context.end_time - timedelta(minutes=5)
        timeline.add_mitigation(
            mitigation_time,
            "batch-processor",
            "Reduced batch size and added resource limits"
        )

        timeline.add_resolution(
            self.context.end_time,
            "Noisy neighbor mitigated, performance stabilized"
        )

        return timeline.generate()
