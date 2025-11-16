"""Latency regression incident generator."""

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
    create_daily_pattern,
    NoisePattern
)
from generator.core.logging_config import get_logger
from generator.core.timeline import TimelineGenerator
from generator.core.utils import timestamp_to_iso, generate_uuid
from generator.anomalies.injectors import LatencyInjector

logger = get_logger(__name__)

# Distributions for realistic data generation
_ORDER_ID_DIST = UniformDistribution(min_val=1000, max_val=9999)
_ROWS_EXAMINED_DIST = LogNormalDistribution(mu=9, sigma=1)  # ~8K-100K rows


class LatencyRegressionGenerator(BaseGenerator):
    """Generates a latency regression incident scenario.

    Simulates a scenario where a service experiences increased latency,
    often due to a code change, database query regression, or resource contention.
    """

    def __init__(
        self,
        context: IncidentContext,
        affected_service: str = "order-service",
        baseline_latency_ms: float = 50.0,
        degraded_latency_ms: float = 500.0,
        error_threshold_ms: float = 1000.0
    ) -> None:
        """Initialize latency regression generator.

        Args:
            context: Incident context
            affected_service: Service experiencing latency
            baseline_latency_ms: Normal latency
            degraded_latency_ms: Degraded latency during incident
            error_threshold_ms: Latency at which requests timeout
        """
        super().__init__(context)
        self.affected_service = affected_service
        self.baseline_latency_ms = baseline_latency_ms
        self.degraded_latency_ms = degraded_latency_ms
        self.error_threshold_ms = error_threshold_ms

        # Apply difficulty configuration if available
        if hasattr(context, 'difficulty_config') and context.difficulty_config:
            diff_config = context.difficulty_config

            # Adjust noise level based on difficulty
            noise_level = diff_config.noise_level

            # Adjust complexity multipliers based on difficulty level
            if diff_config.level.value == 'beginner':
                # Reduce complexity for beginners
                self.baseline_latency_ms *= 0.7
                self.degraded_latency_ms *= 0.7
                self.error_threshold_ms *= 0.8
            elif diff_config.level.value == 'expert':
                # Increase complexity for experts
                self.baseline_latency_ms *= 1.3
                self.degraded_latency_ms *= 1.5
                self.error_threshold_ms *= 1.2

            # Store log and metric multipliers for generation
            self.log_volume_multiplier = diff_config.log_volume_multiplier
            self.metric_density_multiplier = diff_config.metric_density / 3.0  # Base is ~3 metrics/min

            logger.info(f"Applied {diff_config.level.value} difficulty adjustments: "
                       f"baseline_latency={self.baseline_latency_ms:.1f}ms, "
                       f"degraded_latency={self.degraded_latency_ms:.1f}ms, "
                       f"noise_level={noise_level:.2f}")
        else:
            noise_level = 0.05
            self.log_volume_multiplier = 1.0
            self.metric_density_multiplier = 1.0

        # Time-series patterns for realistic data
        self.request_rate_pattern = create_business_hours_pattern()
        self.latency_noise = NoisePattern(noise_level=noise_level)

        # Update context
        context.affected_services = [affected_service]
        context.root_cause = f"Latency regression in {affected_service} due to inefficient database query"

    def generate(self) -> dict[str, Any]:
        """Generate complete incident dataset.

        Returns:
            Summary of generated data
        """
        logger.info(f"Generating latency regression incident for {self.affected_service}...")

        # Generate components
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

        # Save files
        self.save_jsonl(logs, f"logs_{self.context.incident_id}.jsonl", "logs")
        self.save_jsonl(metrics, f"metrics_{self.context.incident_id}.jsonl", "metrics")
        self.save_jsonl(traces, f"traces_{self.context.incident_id}.jsonl", "traces")
        self.save_jsonl(config_deltas, f"config_{self.context.incident_id}.jsonl", "config_deltas")

        return {
            "incident_id": self.context.incident_id,
            "incident_type": "latency_regression",
            "affected_service": self.affected_service,
            "log_count": len(logs),
            "metric_count": len(metrics),
            "trace_count": len(traces),
            "config_change_count": len(config_deltas)
        }

    def _generate_logs(self) -> list[dict[str, Any]]:
        """Generate log entries."""
        logs = []
        hosts = self._get_service_hosts(self.affected_service)

        # Create latency injector
        injector = LatencyInjector(
            baseline_ms=self.baseline_latency_ms,
            anomaly_multiplier=self.degraded_latency_ms / self.baseline_latency_ms,
            spike_start=self.context.start_time,
            spike_duration=self.context.duration
        )

        # Generate logs over time using helper
        for current_time in self._iterate_time_window(step=timedelta(seconds=1)):
            # Request frequency: varies with business hours pattern
            for host in hosts:
                base_rate = 0.1 * self.log_volume_multiplier  # Base 10% of time slots, adjusted by difficulty
                request_rate = self.request_rate_pattern.apply(base_rate, current_time)
                if self._should_generate_log(request_rate):
                    latency = injector.get_latency(current_time)
                    is_error = latency > self.error_threshold_ms

                    order_id = int(_ORDER_ID_DIST.sample())
                    log_entry = {
                        "timestamp": timestamp_to_iso(current_time),
                        "level": "ERROR" if is_error else "INFO",
                        "service": self.affected_service,
                        "host": host,
                        "message": f"HTTP GET /api/orders/{order_id}",
                        "metadata": {
                            "endpoint": "/api/orders/{id}",
                            "method": "GET",
                            "status_code": 504 if is_error else 200,
                            "duration_ms": round(latency, 2),
                            "request_id": generate_uuid()
                        }
                    }

                    # Add slow query warnings during incident
                    if self.context.is_during_incident(current_time) and latency > 200:
                        rows_examined = int(_ROWS_EXAMINED_DIST.sample())
                        logs.append({
                            "timestamp": timestamp_to_iso(current_time),
                            "level": "WARN",
                            "service": self.affected_service,
                            "host": host,
                            "message": "Slow database query detected",
                            "metadata": {
                                "query": "SELECT * FROM orders WHERE user_id = ? AND status IN (...)",
                                "duration_ms": round(latency * 0.8, 2),
                                "rows_examined": max(10000, min(100000, rows_examined))
                            }
                        })

                    logs.append(log_entry)

        return logs

    def _generate_metrics(self) -> list[dict[str, Any]]:
        """Generate metrics."""
        metrics = []
        hosts = self._get_service_hosts(self.affected_service)

        # Create latency injector
        injector = LatencyInjector(
            baseline_ms=self.baseline_latency_ms,
            anomaly_multiplier=self.degraded_latency_ms / self.baseline_latency_ms,
            spike_start=self.context.start_time,
            spike_duration=self.context.duration
        )

        # Generate metrics over time using helper
        for current_time in self._iterate_time_window(step=timedelta(minutes=1)):
            for host in hosts:
                latency = injector.get_latency(current_time)
                is_anomaly = self.context.is_during_incident(current_time)

                # Latency metrics (p50, p95, p99)
                metrics.extend([
                    {
                        "timestamp": timestamp_to_iso(current_time),
                        "metric_name": "http_request_duration_p50",
                        "value": round(self.latency_noise.apply(latency * 0.7, current_time), 2),
                        "service": self.affected_service,
                        "metric_type": "gauge",
                        "unit": "ms",
                        "host": host,
                        "tags": {"endpoint": "/api/orders"},
                        "anomaly_injected": is_anomaly
                    },
                    {
                        "timestamp": timestamp_to_iso(current_time),
                        "metric_name": "http_request_duration_p95",
                        "value": round(self.latency_noise.apply(latency, current_time), 2),
                        "service": self.affected_service,
                        "metric_type": "gauge",
                        "unit": "ms",
                        "host": host,
                        "tags": {"endpoint": "/api/orders"},
                        "anomaly_injected": is_anomaly
                    },
                    {
                        "timestamp": timestamp_to_iso(current_time),
                        "metric_name": "http_request_duration_p99",
                        "value": round(self.latency_noise.apply(latency * 1.3, current_time), 2),
                        "service": self.affected_service,
                        "metric_type": "gauge",
                        "unit": "ms",
                        "host": host,
                        "tags": {"endpoint": "/api/orders"},
                        "anomaly_injected": is_anomaly
                    }
                ])

                # Database query time
                if is_anomaly:
                    metrics.append({
                        "timestamp": timestamp_to_iso(current_time),
                        "metric_name": "db_query_duration_ms",
                        "value": round(self.latency_noise.apply(latency * 0.8, current_time), 2),
                        "service": self.affected_service,
                        "metric_type": "gauge",
                        "unit": "ms",
                        "host": host,
                        "tags": {"query": "orders_by_user"},
                        "anomaly_injected": True
                    })

        return metrics

    def _generate_traces(self) -> list[dict[str, Any]]:
        """Generate distributed traces."""
        traces = []

        # Generate sample traces throughout the incident
        current_time = self.context.start_time
        sample_count = 20

        injector = LatencyInjector(
            baseline_ms=self.baseline_latency_ms,
            anomaly_multiplier=self.degraded_latency_ms / self.baseline_latency_ms,
            spike_start=self.context.start_time,
            spike_duration=self.context.duration
        )

        for i in range(sample_count):
            trace_time = current_time + (self.context.duration / sample_count) * i
            latency = injector.get_latency(trace_time)

            trace_id = generate_uuid()
            trace = {
                "trace_id": trace_id,
                "timestamp": timestamp_to_iso(trace_time),
                "spans": [
                    {
                        "span_id": generate_uuid(),
                        "parent_span_id": None,
                        "service": "api-gateway",
                        "operation": "HTTP GET /api/orders/123",
                        "start_time": timestamp_to_iso(trace_time),
                        "duration_ms": round(self.latency_noise.apply(latency + 10, trace_time), 2),
                        "status": "OK",
                        "tags": {"http.method": "GET", "http.path": "/api/orders/123"}
                    },
                    {
                        "span_id": generate_uuid(),
                        "parent_span_id": trace_id,
                        "service": self.affected_service,
                        "operation": "getOrder",
                        "start_time": timestamp_to_iso(trace_time + timedelta(milliseconds=2)),
                        "duration_ms": round(self.latency_noise.apply(latency, trace_time), 2),
                        "status": "OK" if latency < self.error_threshold_ms else "ERROR",
                        "tags": {"order_id": "123"}
                    },
                    {
                        "span_id": generate_uuid(),
                        "parent_span_id": trace_id,
                        "service": "postgres-primary",
                        "operation": "SELECT orders",
                        "start_time": timestamp_to_iso(trace_time + timedelta(milliseconds=5)),
                        "duration_ms": round(self.latency_noise.apply(latency * 0.85, trace_time), 2),
                        "status": "OK",
                        "tags": {"db.statement": "SELECT * FROM orders WHERE user_id = ?"}
                    }
                ]
            }

            traces.append(trace)

        return traces

    def _generate_config_deltas(self) -> list[dict[str, Any]]:
        """Generate configuration changes."""
        # Deployment that introduced the regression
        deployment_time = self.context.start_time - timedelta(minutes=5)

        return [
            {
                "timestamp": timestamp_to_iso(deployment_time),
                "service": self.affected_service,
                "change_type": "deployment",
                "initiator": "ci-cd-pipeline",
                "changes": [
                    {
                        "key": "version",
                        "old_value": "1.5.1",
                        "new_value": "1.5.2",
                        "category": "infrastructure"
                    }
                ],
                "rollback_available": True
            }
        ]

    def _generate_timeline(self) -> dict[str, Any]:
        """Generate incident timeline."""
        timeline = TimelineGenerator(self.context)

        # Deployment
        deployment_time = self.context.start_time - timedelta(minutes=5)
        timeline.add_deployment(
            deployment_time,
            self.affected_service,
            "1.5.1",
            "1.5.2"
        )

        # Anomaly detection
        detection_time = self.context.start_time + timedelta(minutes=2)
        timeline.add_anomaly_detection(
            detection_time,
            self.affected_service,
            "http_request_duration_p95",
            threshold=100.0,
            actual_value=self.degraded_latency_ms
        )

        # Alert
        alert_time = self.context.start_time + timedelta(minutes=3)
        timeline.add_alert(
            alert_time,
            self.affected_service,
            "High latency detected",
            severity="critical"
        )

        # Mitigation
        mitigation_time = self.context.end_time - timedelta(minutes=5)
        timeline.add_mitigation(
            mitigation_time,
            self.affected_service,
            "Rolled back to version 1.5.1"
        )

        # Resolution
        timeline.add_resolution(
            self.context.end_time,
            "Rollback completed, latency returned to normal"
        )

        return timeline.generate()
