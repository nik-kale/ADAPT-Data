"""Packet loss / network degradation incident generator."""

import random
from datetime import datetime, timedelta
from typing import Any

from generator.core.base import BaseGenerator, IncidentContext
from generator.core.distributions import (
    UniformDistribution,
    NormalDistribution,
    ExponentialDistribution
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
_PACKET_SIZE_DIST = UniformDistribution(min_val=64, max_val=1500)  # Bytes
_JITTER_DIST = NormalDistribution(mean=0, std=5)  # ms
_RTT_DIST = UniformDistribution(min_val=10, max_val=50)  # Round-trip time
_RETRY_COUNT_DIST = UniformDistribution(min_val=1, max_val=3)  # Retry attempts
_DURATION_MS_DIST = UniformDistribution(min_val=40, max_val=80)  # Successful request duration
_RETRANSMIT_RATE_NORMAL_DIST = UniformDistribution(min_val=0, max_val=1)  # Normal retransmit rate
_RETRANSMIT_RATE_INCIDENT_DIST = UniformDistribution(min_val=5, max_val=15)  # Incident retransmit rate
_TIMEOUT_RATE_NORMAL_DIST = UniformDistribution(min_val=0, max_val=0.01)  # Normal timeout rate
_TIMEOUT_RATE_INCIDENT_DIST = UniformDistribution(min_val=0.08, max_val=0.15)  # Incident timeout rate
_LATENCY_NORMAL_DIST = UniformDistribution(min_val=50, max_val=100)  # Normal latency p95
_LATENCY_INCIDENT_DIST = UniformDistribution(min_val=800, max_val=2000)  # Incident latency p95


class PacketLossGenerator(BaseGenerator):
    """Generates a packet loss / network degradation incident.

    Simulates network issues between services or regions,
    causing timeouts, retries, and intermittent failures.
    """

    def __init__(
        self,
        context: IncidentContext,
        affected_services: list[str] | None = None,
        packet_loss_percent: float = 15.0
    ) -> None:
        """Initialize packet loss generator.

        Args:
            context: Incident context
            affected_services: Services affected by network issues
            packet_loss_percent: Percentage of packets lost
        """
        super().__init__(context)
        self.affected_services = affected_services or ["order-service", "inventory-service"]
        self.packet_loss_percent = packet_loss_percent

        context.affected_services = self.affected_services
        context.root_cause = f"Network degradation causing {packet_loss_percent}% packet loss between services"

        # Time-series patterns for realistic data
        self.network_noise = NoisePattern(noise_level=0.12)
        self.retransmit_noise = NoisePattern(noise_level=0.10)
        self.latency_noise = NoisePattern(noise_level=0.15)

    def generate(self) -> dict[str, Any]:
        """Generate complete incident dataset."""
        logger.info(f"Generating packet loss incident ({self.packet_loss_percent}% loss)...")

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
            "incident_type": "packet_loss",
            "packet_loss_percent": self.packet_loss_percent,
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
            is_during_incident = self.context.is_during_incident(current_time)

            for service in self.affected_services:
                hosts = self._get_service_hosts(service)
                for host in hosts:
                    if random.random() < 0.06:
                        if is_during_incident and random.random() < (self.packet_loss_percent / 100):
                            # Network errors
                            error_messages = [
                                "Connection timeout to downstream service",
                                "Network I/O error during service call",
                                "Retry attempt failed - connection reset",
                                "Read timeout on HTTP request"
                            ]
                            logs.append({
                                "timestamp": timestamp_to_iso(current_time),
                                "level": "ERROR",
                                "service": service,
                                "host": host,
                                "message": random.choice(error_messages),
                                "metadata": {
                                    "error_code": "NETWORK_TIMEOUT",
                                    "retry_count": int(_RETRY_COUNT_DIST.sample()),
                                    "request_id": generate_uuid()
                                }
                            })
                        else:
                            logs.append({
                                "timestamp": timestamp_to_iso(current_time),
                                "level": "INFO",
                                "service": service,
                                "host": host,
                                "message": "Request completed successfully",
                                "metadata": {
                                    "duration_ms": _DURATION_MS_DIST.sample(),
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
            is_during_incident = self.context.is_during_incident(current_time)

            for service in self.affected_services:
                hosts = self._get_service_hosts(service)
                for host in hosts:
                    # Network metrics
                    packet_loss_dist_incident = UniformDistribution(
                        min_val=self.packet_loss_percent * 0.8,
                        max_val=self.packet_loss_percent * 1.2
                    )
                    packet_loss_dist_normal = UniformDistribution(min_val=0.0, max_val=0.5)

                    metrics.extend([
                        {
                            "timestamp": timestamp_to_iso(current_time),
                            "metric_name": "network_packet_loss_percent",
                            "value": self.network_noise.apply(packet_loss_dist_incident.sample(), current_time) if is_during_incident else self.network_noise.apply(packet_loss_dist_normal.sample(), current_time),
                            "service": service,
                            "metric_type": "gauge",
                            "unit": "percent",
                            "host": host,
                            "tags": {},
                            "anomaly_injected": is_during_incident
                        },
                        {
                            "timestamp": timestamp_to_iso(current_time),
                            "metric_name": "network_retransmit_rate",
                            "value": self.retransmit_noise.apply(_RETRANSMIT_RATE_INCIDENT_DIST.sample(), current_time) if is_during_incident else self.retransmit_noise.apply(_RETRANSMIT_RATE_NORMAL_DIST.sample(), current_time),
                            "service": service,
                            "metric_type": "gauge",
                            "unit": "percent",
                            "host": host,
                            "tags": {},
                            "anomaly_injected": is_during_incident
                        },
                        {
                            "timestamp": timestamp_to_iso(current_time),
                            "metric_name": "http_request_timeout_rate",
                            "value": _TIMEOUT_RATE_INCIDENT_DIST.sample() if is_during_incident else _TIMEOUT_RATE_NORMAL_DIST.sample(),
                            "service": service,
                            "metric_type": "gauge",
                            "unit": "ratio",
                            "host": host,
                            "tags": {},
                            "anomaly_injected": is_during_incident
                        },
                        {
                            "timestamp": timestamp_to_iso(current_time),
                            "metric_name": "http_request_duration_p95",
                            "value": self.latency_noise.apply(_LATENCY_INCIDENT_DIST.sample(), current_time) if is_during_incident else self.latency_noise.apply(_LATENCY_NORMAL_DIST.sample(), current_time),
                            "service": service,
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
        sample_count = 15

        for i in range(sample_count):
            trace_time = current_time + (self.context.duration / sample_count) * i
            is_during_incident = self.context.is_during_incident(trace_time)
            has_timeout = is_during_incident and random.random() < (self.packet_loss_percent / 100)

            trace_id = generate_uuid()
            service1 = self.affected_services[0]
            service2 = self.affected_services[1] if len(self.affected_services) > 1 else "postgres-primary"

            spans = [
                {
                    "span_id": generate_uuid(),
                    "parent_span_id": None,
                    "service": "api-gateway",
                    "operation": "HTTP GET /api/order/{id}",
                    "start_time": timestamp_to_iso(trace_time),
                    "duration_ms": 3050 if has_timeout else 90,
                    "status": "ERROR" if has_timeout else "OK",
                    "tags": {"http.method": "GET"}
                },
                {
                    "span_id": generate_uuid(),
                    "parent_span_id": trace_id,
                    "service": service1,
                    "operation": "getOrderDetails",
                    "start_time": timestamp_to_iso(trace_time + timedelta(milliseconds=5)),
                    "duration_ms": 3040 if has_timeout else 80,
                    "status": "ERROR" if has_timeout else "OK",
                    "tags": {}
                },
                {
                    "span_id": generate_uuid(),
                    "parent_span_id": trace_id,
                    "service": service2,
                    "operation": "checkInventory",
                    "start_time": timestamp_to_iso(trace_time + timedelta(milliseconds=10)),
                    "duration_ms": 3000 if has_timeout else 65,
                    "status": "TIMEOUT" if has_timeout else "OK",
                    "tags": {"error": "read_timeout"} if has_timeout else {}
                }
            ]

            traces.append({
                "trace_id": trace_id,
                "timestamp": timestamp_to_iso(trace_time),
                "spans": spans
            })

        return traces

    def _generate_config_deltas(self) -> list[dict[str, Any]]:
        """Generate configuration changes."""
        return []  # Network issues typically don't involve config changes

    def _generate_timeline(self) -> dict[str, Any]:
        """Generate incident timeline."""
        timeline = TimelineGenerator(self.context)

        timeline.add_event(
            self.context.start_time,
            "other",
            f"Network degradation detected: {self.packet_loss_percent}% packet loss",
            service=self.affected_services[0]
        )

        detection_time = self.context.start_time + timedelta(minutes=1)
        timeline.add_anomaly_detection(
            detection_time,
            self.affected_services[0],
            "network_packet_loss_percent",
            threshold=1.0,
            actual_value=self.packet_loss_percent
        )

        alert_time = self.context.start_time + timedelta(minutes=2)
        timeline.add_alert(
            alert_time,
            self.affected_services[0],
            "High network packet loss and timeout rate",
            severity="critical"
        )

        mitigation_time = self.context.end_time - timedelta(minutes=3)
        timeline.add_mitigation(
            mitigation_time,
            "network",
            "Network team investigating routing tables and firewall rules"
        )

        timeline.add_resolution(
            self.context.end_time,
            "Network issue resolved by infrastructure team"
        )

        return timeline.generate()
