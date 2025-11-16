"""Dependency outage incident generator."""

import random
from datetime import datetime, timedelta
from typing import Any

from generator.core.base import BaseGenerator, IncidentContext
from generator.core.distributions import (
    UniformDistribution,
    ExponentialDistribution,
    LogNormalDistribution
)
from generator.core.patterns import (
    create_daily_pattern,
    NoisePattern
)
from generator.core.logging_config import get_logger
from generator.core.timeline import TimelineGenerator
from generator.core.utils import timestamp_to_iso, generate_uuid

logger = get_logger(__name__)

# Distributions for realistic data generation
_RETRY_COUNT_DIST = UniformDistribution(min_val=1, max_val=10)
_NORMAL_DURATION_DIST = UniformDistribution(min_val=20, max_val=60)  # Normal request duration in ms
_CONNECTION_POOL_DIST = UniformDistribution(min_val=10, max_val=50)  # Active connections
_HTTP_REQUESTS_DIST = UniformDistribution(min_val=80, max_val=120)  # Requests per interval


class DependencyOutageGenerator(BaseGenerator):
    """Generates a dependency outage incident.

    Simulates scenarios where a critical dependency (database, cache, external API)
    becomes unavailable, causing cascading failures.
    """

    def __init__(
        self,
        context: IncidentContext,
        failed_service: str = "postgres-primary",
        dependent_services: list[str] | None = None
    ) -> None:
        """Initialize dependency outage generator.

        Args:
            context: Incident context
            failed_service: Service that went down
            dependent_services: Services that depend on failed service
        """
        super().__init__(context)
        self.failed_service = failed_service
        self.dependent_services = dependent_services or [
            "user-service",
            "order-service",
            "payment-service"
        ]

        context.affected_services = [failed_service] + self.dependent_services
        context.root_cause = f"Complete outage of {failed_service} causing cascading failures"

        # Time-series patterns for realistic data
        self.request_pattern = create_daily_pattern(amplitude=0.25)
        self.connection_pattern = create_daily_pattern(amplitude=0.20)
        self.metric_noise = NoisePattern(noise_level=0.05)

    def generate(self) -> dict[str, Any]:
        """Generate complete incident dataset."""
        logger.info(f"Generating dependency outage incident: {self.failed_service} failure...")

        logs = self._generate_logs()
        metrics = self._generate_metrics()
        traces = self._generate_traces()
        config_deltas = self._generate_config_deltas()
        timeline = self._generate_timeline()

        logger.info(f"  Generated {len(logs)} log entries")
        logger.info(f"  Generated {len(metrics)} metric points")
        logger.info(f"  Generated {len(traces)} traces")

        self.save_jsonl(logs, f"logs_{self.context.incident_id}.jsonl", "logs")
        self.save_jsonl(metrics, f"metrics_{self.context.incident_id}.jsonl", "metrics")
        self.save_jsonl(traces, f"traces_{self.context.incident_id}.jsonl", "traces")
        self.save_jsonl(config_deltas, f"config_{self.context.incident_id}.jsonl", "config_deltas")

        return {
            "incident_id": self.context.incident_id,
            "incident_type": "dependency_outage",
            "failed_service": self.failed_service,
            "affected_services": self.dependent_services,
            "log_count": len(logs),
            "metric_count": len(metrics),
            "trace_count": len(traces)
        }

    def _generate_logs(self) -> list[dict[str, Any]]:
        """Generate log entries."""
        logs = []

        current_time = self.context.start_time - timedelta(minutes=30)
        end_time = self.context.end_time + timedelta(minutes=30)

        while current_time < end_time:
            is_during_outage = self.context.is_during_incident(current_time)

            # Logs from failed service
            if is_during_outage:
                logs.append({
                    "timestamp": timestamp_to_iso(current_time),
                    "level": "FATAL",
                    "service": self.failed_service,
                    "host": f"{self.failed_service}-000",
                    "message": "Database connection lost - attempting reconnection",
                    "metadata": {
                        "error": "connection_refused",
                        "retry_attempt": int(_RETRY_COUNT_DIST.sample())
                    }
                })

            # Logs from dependent services
            for service in self.dependent_services:
                hosts = self._get_service_hosts(service)
                for host in hosts:
                    if random.random() < 0.05:
                        if is_during_outage:
                            error_messages = [
                                f"Failed to connect to {self.failed_service}",
                                "Database operation failed",
                                "Connection timeout",
                                "Max retry attempts exceeded"
                            ]
                            logs.append({
                                "timestamp": timestamp_to_iso(current_time),
                                "level": "ERROR",
                                "service": service,
                                "host": host,
                                "message": random.choice(error_messages),
                                "metadata": {
                                    "dependency": self.failed_service,
                                    "error_code": "DEPENDENCY_UNAVAILABLE",
                                    "request_id": generate_uuid()
                                }
                            })
                        else:
                            logs.append({
                                "timestamp": timestamp_to_iso(current_time),
                                "level": "INFO",
                                "service": service,
                                "host": host,
                                "message": "Request processed successfully",
                                "metadata": {
                                    "duration_ms": round(_NORMAL_DURATION_DIST.sample(), 2),
                                    "request_id": generate_uuid()
                                }
                            })

            current_time += timedelta(seconds=1)

        return logs

    def _generate_metrics(self) -> list[dict[str, Any]]:
        """Generate metrics."""
        metrics = []

        current_time = self.context.start_time - timedelta(minutes=30)
        end_time = self.context.end_time + timedelta(minutes=30)

        while current_time < end_time:
            is_during_outage = self.context.is_during_incident(current_time)

            # Failed service metrics
            metrics.extend([
                {
                    "timestamp": timestamp_to_iso(current_time),
                    "metric_name": "service_available",
                    "value": 0.0 if is_during_outage else 1.0,
                    "service": self.failed_service,
                    "metric_type": "gauge",
                    "unit": "bool",
                    "host": f"{self.failed_service}-000",
                    "tags": {},
                    "anomaly_injected": is_during_outage
                },
                {
                    "timestamp": timestamp_to_iso(current_time),
                    "metric_name": "connection_pool_active",
                    "value": 0 if is_during_outage else int(self.connection_pattern.apply(_CONNECTION_POOL_DIST.sample(), current_time)),
                    "service": self.failed_service,
                    "metric_type": "gauge",
                    "unit": "connections",
                    "host": f"{self.failed_service}-000",
                    "tags": {},
                    "anomaly_injected": is_during_outage
                }
            ])

            # Dependent service metrics
            for service in self.dependent_services:
                for host in self._get_service_hosts(service):
                    metrics.extend([
                        {
                            "timestamp": timestamp_to_iso(current_time),
                            "metric_name": "http_requests_total",
                            "value": int(self.request_pattern.apply(_HTTP_REQUESTS_DIST.sample(), current_time)),
                            "service": service,
                            "metric_type": "counter",
                            "unit": "requests",
                            "host": host,
                            "tags": {},
                            "anomaly_injected": False
                        },
                        {
                            "timestamp": timestamp_to_iso(current_time),
                            "metric_name": "http_error_rate",
                            "value": 0.95 if is_during_outage else self.metric_noise.apply(0.001, current_time),
                            "service": service,
                            "metric_type": "gauge",
                            "unit": "ratio",
                            "host": host,
                            "tags": {},
                            "anomaly_injected": is_during_outage
                        }
                    ])

            current_time += timedelta(minutes=1)

        return metrics

    def _generate_traces(self) -> list[dict[str, Any]]:
        """Generate distributed traces."""
        traces = []
        current_time = self.context.start_time
        sample_count = 10

        for i in range(sample_count):
            trace_time = current_time + (self.context.duration / sample_count) * i
            is_during_outage = self.context.is_during_incident(trace_time)

            trace_id = generate_uuid()
            service = random.choice(self.dependent_services)

            spans = [
                {
                    "span_id": generate_uuid(),
                    "parent_span_id": None,
                    "service": "api-gateway",
                    "operation": "HTTP GET /api/resource",
                    "start_time": timestamp_to_iso(trace_time),
                    "duration_ms": 5020 if is_during_outage else 45,
                    "status": "ERROR" if is_during_outage else "OK",
                    "tags": {"http.method": "GET"}
                },
                {
                    "span_id": generate_uuid(),
                    "parent_span_id": trace_id,
                    "service": service,
                    "operation": "processRequest",
                    "start_time": timestamp_to_iso(trace_time + timedelta(milliseconds=2)),
                    "duration_ms": 5015 if is_during_outage else 40,
                    "status": "ERROR" if is_during_outage else "OK",
                    "tags": {}
                },
                {
                    "span_id": generate_uuid(),
                    "parent_span_id": trace_id,
                    "service": self.failed_service,
                    "operation": "query",
                    "start_time": timestamp_to_iso(trace_time + timedelta(milliseconds=5)),
                    "duration_ms": 5000 if is_during_outage else 30,
                    "status": "TIMEOUT" if is_during_outage else "OK",
                    "tags": {"error": "connection_timeout"} if is_during_outage else {}
                }
            ]

            traces.append({"trace_id": trace_id, "timestamp": timestamp_to_iso(trace_time), "spans": spans})

        return traces

    def _generate_config_deltas(self) -> list[dict[str, Any]]:
        """Generate configuration changes."""
        return []  # No config changes for this incident type

    def _generate_timeline(self) -> dict[str, Any]:
        """Generate incident timeline."""
        timeline = TimelineGenerator(self.context)

        timeline.add_event(
            self.context.start_time,
            "other",
            f"{self.failed_service} became unavailable",
            service=self.failed_service
        )

        detection_time = self.context.start_time + timedelta(seconds=30)
        timeline.add_anomaly_detection(
            detection_time,
            self.failed_service,
            "service_available",
            threshold=1.0,
            actual_value=0.0
        )

        for service in self.dependent_services:
            alert_time = self.context.start_time + timedelta(minutes=1)
            timeline.add_alert(
                alert_time,
                service,
                f"High error rate due to {self.failed_service} unavailability",
                severity="critical"
            )

        mitigation_time = self.context.end_time - timedelta(minutes=2)
        timeline.add_mitigation(
            mitigation_time,
            self.failed_service,
            f"Restarted {self.failed_service} instances"
        )

        timeline.add_resolution(
            self.context.end_time,
            f"{self.failed_service} restored, dependent services recovered"
        )

        return timeline.generate()
