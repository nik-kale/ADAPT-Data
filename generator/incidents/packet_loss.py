"""Packet loss / network degradation incident generator."""

import random
from datetime import datetime, timedelta
from typing import Any

from generator.core.base import BaseGenerator, IncidentContext
from generator.core.timeline import TimelineGenerator
from generator.core.utils import timestamp_to_iso, generate_uuid


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

    def generate(self) -> dict[str, Any]:
        """Generate complete incident dataset."""
        print(f"Generating packet loss incident ({self.packet_loss_percent}% loss)...")

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
                                    "retry_count": random.randint(1, 3),
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
                                    "duration_ms": random.uniform(40, 80),
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
                    metrics.extend([
                        {
                            "timestamp": timestamp_to_iso(current_time),
                            "metric_name": "network_packet_loss_percent",
                            "value": random.uniform(
                                self.packet_loss_percent * 0.8,
                                self.packet_loss_percent * 1.2
                            ) if is_during_incident else random.uniform(0.0, 0.5),
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
                            "value": random.uniform(5, 15) if is_during_incident else random.uniform(0, 1),
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
                            "value": random.uniform(0.08, 0.15) if is_during_incident else random.uniform(0, 0.01),
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
                            "value": random.uniform(800, 2000) if is_during_incident else random.uniform(50, 100),
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
