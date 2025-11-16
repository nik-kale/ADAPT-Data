"""Configuration drift incident generator."""

import random
from datetime import datetime, timedelta
from typing import Any

from generator.core.base import BaseGenerator, IncidentContext
from generator.core.distributions import (
    UniformDistribution,
    NormalDistribution
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
_POOL_UTILIZATION_INCIDENT = UniformDistribution(min_val=0.85, max_val=1.0)
_POOL_UTILIZATION_NORMAL = UniformDistribution(min_val=0.3, max_val=0.6)
_QUEUE_DEPTH_INCIDENT = UniformDistribution(min_val=10, max_val=50)
_QUEUE_DEPTH_NORMAL = UniformDistribution(min_val=0, max_val=5)
_REQUEST_DURATION_INCIDENT = UniformDistribution(min_val=800, max_val=1500)
_REQUEST_DURATION_NORMAL = UniformDistribution(min_val=150, max_val=250)
_TRANSACTION_DURATION = UniformDistribution(min_val=100, max_val=300)
_WAITING_REQUESTS = UniformDistribution(min_val=5, max_val=50)


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

        # Apply difficulty configuration if available
        if hasattr(context, 'difficulty_config') and context.difficulty_config:
            diff_config = context.difficulty_config

            # Adjust noise level based on difficulty
            base_noise = diff_config.noise_level

            # Adjust config values based on difficulty level
            if diff_config.level.value == 'beginner':
                # Make the change more obvious for beginners
                ratio = self.new_value / self.old_value
                self.new_value = int(self.old_value * (ratio * 0.7))  # More dramatic change
            elif diff_config.level.value == 'expert':
                # Make the change more subtle for experts
                ratio = self.new_value / self.old_value
                self.new_value = int(self.old_value * (ratio * 1.3))  # More subtle change

            # Store log and metric multipliers for generation
            self.log_volume_multiplier = diff_config.log_volume_multiplier
            self.metric_density_multiplier = diff_config.metric_density / 3.0  # Base is ~3 metrics/min

            logger.info(f"Applied {diff_config.level.value} difficulty adjustments: "
                       f"config_change={self.old_value}->{self.new_value}, "
                       f"noise_level={base_noise:.2f}")
        else:
            base_noise = 0.1
            self.log_volume_multiplier = 1.0
            self.metric_density_multiplier = 1.0

        context.affected_services = [affected_service]
        context.root_cause = f"Configuration change: {config_key} reduced from {old_value} to {new_value}"

        # Time-series patterns for realistic data
        self.utilization_noise = NoisePattern(noise_level=base_noise * 0.8)
        self.queue_noise = NoisePattern(noise_level=base_noise * 1.5)
        self.latency_noise = NoisePattern(noise_level=base_noise)

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

        for current_time in self._iterate_time_window(step=timedelta(seconds=1)):
            is_during_incident = self.context.is_during_incident(current_time)

            for host in hosts:
                if self._should_generate_log(0.08 * self.log_volume_multiplier):  # Adjusted by difficulty
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
                                "waiting_requests": int(_WAITING_REQUESTS.sample()),
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
                                "duration_ms": _TRANSACTION_DURATION.sample(),
                                "request_id": generate_uuid()
                            }
                        })

        return logs

    def _generate_metrics(self) -> list[dict[str, Any]]:
        """Generate metrics."""
        metrics = []
        hosts = self._get_service_hosts(self.affected_service)

        for current_time in self._iterate_time_window(step=timedelta(minutes=1)):
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
                        "value": self.utilization_noise.apply(_POOL_UTILIZATION_INCIDENT.sample(), current_time) if is_during_incident else self.utilization_noise.apply(_POOL_UTILIZATION_NORMAL.sample(), current_time),
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
                        "value": int(self.queue_noise.apply(_QUEUE_DEPTH_INCIDENT.sample(), current_time)) if is_during_incident else int(self.queue_noise.apply(_QUEUE_DEPTH_NORMAL.sample(), current_time)),
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
                        "value": self.latency_noise.apply(_REQUEST_DURATION_INCIDENT.sample(), current_time) if is_during_incident else self.latency_noise.apply(_REQUEST_DURATION_NORMAL.sample(), current_time),
                        "service": self.affected_service,
                        "metric_type": "gauge",
                        "unit": "ms",
                        "host": host,
                        "tags": {},
                        "anomaly_injected": is_during_incident
                    }
                ])

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
            duration = _REQUEST_DURATION_INCIDENT.sample() if is_during_incident else _REQUEST_DURATION_NORMAL.sample()

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
