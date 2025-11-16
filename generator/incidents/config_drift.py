"""Configuration drift incident generator."""

import random
from datetime import datetime, timedelta
from typing import Any

from generator.core.base import BaseGenerator, IncidentContext
from generator.core.logging_config import get_logger
from generator.core.timeline import TimelineGenerator
from generator.core.utils import timestamp_to_iso, generate_uuid

logger = get_logger(__name__)


class ConfigDriftGenerator(BaseGenerator):
    """Generates a configuration drift incident.

    Simulates scenarios where configuration changes cause unexpected behavior,
    such as feature flag rollouts, resource limit changes, or connection pool adjustments.
    """

    def __init__(
        self,
        context: IncidentContext,
        affected_service: str = "payment-service",
        config_key: str = "max_concurrent_transactions",
        old_value: int = 100,
        new_value: int = 10
    ) -> None:
        """Initialize config drift generator.

        Args:
            context: Incident context
            affected_service: Service with config change
            config_key: Configuration key that changed
            old_value: Previous value
            new_value: New value causing issue
        """
        super().__init__(context)
        self.affected_service = affected_service
        self.config_key = config_key
        self.old_value = old_value
        self.new_value = new_value

        context.affected_services = [affected_service]
        context.root_cause = f"Configuration change: {config_key} reduced from {old_value} to {new_value}"

    def generate(self) -> dict[str, Any]:
        """Generate complete incident dataset."""
        logger.info(f"Generating config drift incident for {self.affected_service}...")

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
            "incident_type": "config_drift",
            "affected_service": self.affected_service,
            "config_key": self.config_key,
            "log_count": len(logs),
            "metric_count": len(metrics),
            "trace_count": len(traces)
        }

    def _generate_logs(self) -> list[dict[str, Any]]:
        """Generate log entries."""
        logs = []
        hosts = self._get_service_hosts(self.affected_service)

        current_time = self.context.start_time - timedelta(minutes=30)
        end_time = self.context.end_time + timedelta(minutes=30)

        while current_time < end_time:
            is_during_incident = self.context.is_during_incident(current_time)

            for host in hosts:
                if random.random() < 0.08:
                    if is_during_incident:
                        # Errors due to config limit
                        error_messages = [
                            "Transaction pool exhausted",
                            "Max concurrent transactions reached",
                            "Request queued - pool at capacity",
                            "Transaction timeout waiting for available slot"
                        ]
                        logs.append({
                            "timestamp": timestamp_to_iso(current_time),
                            "level": "WARN",
                            "service": self.affected_service,
                            "host": host,
                            "message": random.choice(error_messages),
                            "metadata": {
                                "current_pool_size": self.new_value,
                                "waiting_requests": random.randint(5, 50),
                                "request_id": generate_uuid()
                            }
                        })
                    else:
                        logs.append({
                            "timestamp": timestamp_to_iso(current_time),
                            "level": "INFO",
                            "service": self.affected_service,
                            "host": host,
                            "message": "Transaction completed successfully",
                            "metadata": {
                                "duration_ms": random.uniform(100, 300),
                                "request_id": generate_uuid()
                            }
                        })

            current_time += timedelta(seconds=1)

        return logs

    def _generate_metrics(self) -> list[dict[str, Any]]:
        """Generate metrics."""
        metrics = []
        hosts = self._get_service_hosts(self.affected_service)

        current_time = self.context.start_time - timedelta(minutes=30)
        end_time = self.context.end_time + timedelta(minutes=30)

        while current_time < end_time:
            is_during_incident = self.context.is_during_incident(current_time)

            for host in hosts:
                # Transaction pool metrics
                metrics.extend([
                    {
                        "timestamp": timestamp_to_iso(current_time),
                        "metric_name": "transaction_pool_size",
                        "value": self.new_value if is_during_incident else self.old_value,
                        "service": self.affected_service,
                        "metric_type": "gauge",
                        "unit": "transactions",
                        "host": host,
                        "tags": {},
                        "anomaly_injected": is_during_incident
                    },
                    {
                        "timestamp": timestamp_to_iso(current_time),
                        "metric_name": "transaction_pool_utilization",
                        "value": random.uniform(0.85, 1.0) if is_during_incident else random.uniform(0.3, 0.6),
                        "service": self.affected_service,
                        "metric_type": "gauge",
                        "unit": "ratio",
                        "host": host,
                        "tags": {},
                        "anomaly_injected": is_during_incident
                    },
                    {
                        "timestamp": timestamp_to_iso(current_time),
                        "metric_name": "transaction_queue_depth",
                        "value": random.randint(10, 50) if is_during_incident else random.randint(0, 5),
                        "service": self.affected_service,
                        "metric_type": "gauge",
                        "unit": "requests",
                        "host": host,
                        "tags": {},
                        "anomaly_injected": is_during_incident
                    },
                    {
                        "timestamp": timestamp_to_iso(current_time),
                        "metric_name": "http_request_duration_p95",
                        "value": random.uniform(800, 1500) if is_during_incident else random.uniform(150, 250),
                        "service": self.affected_service,
                        "metric_type": "gauge",
                        "unit": "ms",
                        "host": host,
                        "tags": {},
                        "anomaly_injected": is_during_incident
                    }
                ])

            current_time += timedelta(minutes=1)

        return metrics

    def _generate_traces(self) -> list[dict[str, Any]]:
        """Generate distributed traces."""
        traces = []
        current_time = self.context.start_time
        sample_count = 12

        for i in range(sample_count):
            trace_time = current_time + (self.context.duration / sample_count) * i
            is_during_incident = self.context.is_during_incident(trace_time)

            trace_id = generate_uuid()
            duration = random.uniform(800, 1500) if is_during_incident else random.uniform(150, 250)

            traces.append({
                "trace_id": trace_id,
                "timestamp": timestamp_to_iso(trace_time),
                "spans": [
                    {
                        "span_id": generate_uuid(),
                        "parent_span_id": None,
                        "service": "api-gateway",
                        "operation": "HTTP POST /api/payment",
                        "start_time": timestamp_to_iso(trace_time),
                        "duration_ms": round(duration + 20, 2),
                        "status": "OK",
                        "tags": {"http.method": "POST"}
                    },
                    {
                        "span_id": generate_uuid(),
                        "parent_span_id": trace_id,
                        "service": self.affected_service,
                        "operation": "processPayment",
                        "start_time": timestamp_to_iso(trace_time + timedelta(milliseconds=5)),
                        "duration_ms": round(duration, 2),
                        "status": "OK",
                        "tags": {
                            "pool_wait_ms": round(duration * 0.6, 2) if is_during_incident else 0
                        }
                    }
                ]
            })

        return traces

    def _generate_config_deltas(self) -> list[dict[str, Any]]:
        """Generate configuration changes."""
        config_change_time = self.context.start_time - timedelta(minutes=2)

        return [
            {
                "timestamp": timestamp_to_iso(config_change_time),
                "service": self.affected_service,
                "change_type": "config_update",
                "initiator": "ops-team",
                "changes": [
                    {
                        "key": self.config_key,
                        "old_value": self.old_value,
                        "new_value": self.new_value,
                        "category": "performance"
                    }
                ],
                "rollback_available": True
            }
        ]

    def _generate_timeline(self) -> dict[str, Any]:
        """Generate incident timeline."""
        timeline = TimelineGenerator(self.context)

        config_change_time = self.context.start_time - timedelta(minutes=2)
        timeline.add_config_change(
            config_change_time,
            self.affected_service,
            f"Changed {self.config_key} from {self.old_value} to {self.new_value}",
            "ops-team"
        )

        detection_time = self.context.start_time + timedelta(minutes=3)
        timeline.add_anomaly_detection(
            detection_time,
            self.affected_service,
            "transaction_queue_depth",
            threshold=10,
            actual_value=45
        )

        alert_time = self.context.start_time + timedelta(minutes=5)
        timeline.add_alert(
            alert_time,
            self.affected_service,
            "High transaction queue depth and latency",
            severity="warning"
        )

        mitigation_time = self.context.end_time - timedelta(minutes=2)
        timeline.add_mitigation(
            mitigation_time,
            self.affected_service,
            f"Reverted {self.config_key} back to {self.old_value}"
        )

        timeline.add_resolution(
            self.context.end_time,
            "Configuration rolled back, service performance normalized"
        )

        return timeline.generate()
