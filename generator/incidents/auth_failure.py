"""Authentication failure spike incident generator."""

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
    create_daily_pattern,
    NoisePattern
)
from generator.core.logging_config import get_logger
from generator.core.timeline import TimelineGenerator
from generator.core.utils import timestamp_to_iso, generate_uuid
from generator.anomalies.injectors import ErrorRateInjector

logger = get_logger(__name__)

# Distributions for realistic data generation
_USER_ID_DIST = UniformDistribution(min_val=1000, max_val=999999)
_SUCCESS_DURATION_DIST = LogNormalDistribution(mu=3, sigma=0.4)  # ~10-50ms
_AUTH_REQUESTS_DIST = UniformDistribution(min_val=90, max_val=110)
_REDIS_ERROR_DIST = UniformDistribution(min_val=10, max_val=30)
_REDIS_CONN_DIST = UniformDistribution(min_val=5, max_val=15)


class AuthFailureGenerator(BaseGenerator):
    """Generates an authentication failure spike incident.

    Simulates scenarios like:
    - Database connection pool exhaustion
    - Redis cache unavailability
    - Token validation service overload
    """

    def __init__(
        self,
        context: IncidentContext,
        affected_service: str = "auth-service",
        baseline_error_rate: float = 0.001,
        spike_error_rate: float = 0.25
    ) -> None:
        """Initialize auth failure generator.

        Args:
            context: Incident context
            affected_service: Service experiencing auth failures
            baseline_error_rate: Normal error rate
            spike_error_rate: Error rate during incident
        """
        super().__init__(context)
        self.affected_service = affected_service
        self.baseline_error_rate = baseline_error_rate
        self.spike_error_rate = spike_error_rate

        # Time-series patterns for realistic data
        self.auth_rate_pattern = create_daily_pattern(amplitude=0.3)
        self.metric_noise = NoisePattern(noise_level=0.05)

        context.affected_services = [affected_service, "api-gateway"]
        context.root_cause = f"Redis cache connection failures causing {affected_service} auth failures"

    def generate(self) -> dict[str, Any]:
        """Generate complete incident dataset."""
        logger.info(f"Generating auth failure spike incident for {self.affected_service}...")

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
            "incident_type": "auth_failure_spike",
            "affected_service": self.affected_service,
            "log_count": len(logs),
            "metric_count": len(metrics),
            "trace_count": len(traces)
        }

    def _generate_logs(self) -> list[dict[str, Any]]:
        """Generate log entries."""
        logs = []
        hosts = self._get_service_hosts(self.affected_service)

        injector = ErrorRateInjector(
            baseline_error_rate=self.baseline_error_rate,
            anomaly_error_rate=self.spike_error_rate,
            spike_start=self.context.start_time,
            spike_duration=self.context.duration
        )

        current_time = self.context.start_time - timedelta(minutes=30)
        end_time = self.context.end_time + timedelta(minutes=30)

        while current_time < end_time:
            for host in hosts:
                if random.random() < 0.15:  # Auth requests
                    should_error = injector.should_error(current_time)

                    if should_error:
                        # Error log
                        error_messages = [
                            "Failed to connect to Redis cache",
                            "Connection pool exhausted",
                            "Timeout waiting for cache response",
                            "Redis connection refused",
                            "Unable to validate auth token"
                        ]
                        user_id = int(_USER_ID_DIST.sample())
                        logs.append({
                            "timestamp": timestamp_to_iso(current_time),
                            "level": "ERROR",
                            "service": self.affected_service,
                            "host": host,
                            "message": random.choice(error_messages),
                            "metadata": {
                                "error_code": "CACHE_UNAVAILABLE",
                                "user_id": f"user_{user_id}",
                                "request_id": generate_uuid()
                            }
                        })
                    else:
                        # Success log
                        user_id = int(_USER_ID_DIST.sample())
                        duration_ms = max(10, min(50, _SUCCESS_DURATION_DIST.sample()))
                        logs.append({
                            "timestamp": timestamp_to_iso(current_time),
                            "level": "INFO",
                            "service": self.affected_service,
                            "host": host,
                            "message": "User authenticated successfully",
                            "metadata": {
                                "user_id": f"user_{user_id}",
                                "duration_ms": round(duration_ms, 2),
                                "request_id": generate_uuid()
                            }
                        })

            current_time += timedelta(seconds=1)

        return logs

    def _generate_metrics(self) -> list[dict[str, Any]]:
        """Generate metrics."""
        metrics = []
        hosts = self._get_service_hosts(self.affected_service)

        injector = ErrorRateInjector(
            baseline_error_rate=self.baseline_error_rate,
            anomaly_error_rate=self.spike_error_rate,
            spike_start=self.context.start_time,
            spike_duration=self.context.duration
        )

        current_time = self.context.start_time - timedelta(minutes=30)
        end_time = self.context.end_time + timedelta(minutes=30)

        while current_time < end_time:
            for host in hosts:
                error_rate = injector.get_error_rate(current_time)
                is_anomaly = self.context.is_during_incident(current_time)

                # Auth metrics
                base_auth_requests = _AUTH_REQUESTS_DIST.sample()
                auth_requests = int(self.auth_rate_pattern.apply(base_auth_requests, current_time))

                base_error_rate = error_rate
                error_rate_with_noise = self.metric_noise.apply(base_error_rate, current_time)

                metrics.extend([
                    {
                        "timestamp": timestamp_to_iso(current_time),
                        "metric_name": "auth_requests_total",
                        "value": auth_requests,
                        "service": self.affected_service,
                        "metric_type": "counter",
                        "unit": "requests",
                        "host": host,
                        "tags": {},
                        "anomaly_injected": False
                    },
                    {
                        "timestamp": timestamp_to_iso(current_time),
                        "metric_name": "auth_error_rate",
                        "value": round(error_rate_with_noise, 4),
                        "service": self.affected_service,
                        "metric_type": "gauge",
                        "unit": "ratio",
                        "host": host,
                        "tags": {},
                        "anomaly_injected": is_anomaly
                    }
                ])

                # Redis connection metrics
                if is_anomaly:
                    base_redis_errors = _REDIS_ERROR_DIST.sample()
                    redis_errors = int(self.metric_noise.apply(base_redis_errors, current_time))

                    base_redis_conns = _REDIS_CONN_DIST.sample()
                    redis_conns = int(self.metric_noise.apply(base_redis_conns, current_time))

                    metrics.extend([
                        {
                            "timestamp": timestamp_to_iso(current_time),
                            "metric_name": "redis_connection_errors",
                            "value": redis_errors,
                            "service": "redis-cache",
                            "metric_type": "counter",
                            "unit": "errors",
                            "host": "redis-cache-000",
                            "tags": {},
                            "anomaly_injected": True
                        },
                        {
                            "timestamp": timestamp_to_iso(current_time),
                            "metric_name": "redis_active_connections",
                            "value": redis_conns,
                            "service": "redis-cache",
                            "metric_type": "gauge",
                            "unit": "connections",
                            "host": "redis-cache-000",
                            "tags": {},
                            "anomaly_injected": True
                        }
                    ])

            current_time += timedelta(minutes=1)

        return metrics

    def _generate_traces(self) -> list[dict[str, Any]]:
        """Generate distributed traces."""
        traces = []
        current_time = self.context.start_time
        sample_count = 15

        injector = ErrorRateInjector(
            baseline_error_rate=self.baseline_error_rate,
            anomaly_error_rate=self.spike_error_rate,
            spike_start=self.context.start_time,
            spike_duration=self.context.duration
        )

        for i in range(sample_count):
            trace_time = current_time + (self.context.duration / sample_count) * i
            should_error = injector.should_error(trace_time)

            trace_id = generate_uuid()
            spans = [
                {
                    "span_id": generate_uuid(),
                    "parent_span_id": None,
                    "service": "api-gateway",
                    "operation": "HTTP POST /api/auth/login",
                    "start_time": timestamp_to_iso(trace_time),
                    "duration_ms": 250 if should_error else 35,
                    "status": "ERROR" if should_error else "OK",
                    "tags": {"http.method": "POST", "http.path": "/api/auth/login"}
                },
                {
                    "span_id": generate_uuid(),
                    "parent_span_id": trace_id,
                    "service": self.affected_service,
                    "operation": "validateCredentials",
                    "start_time": timestamp_to_iso(trace_time + timedelta(milliseconds=2)),
                    "duration_ms": 240 if should_error else 30,
                    "status": "ERROR" if should_error else "OK",
                    "tags": {}
                }
            ]

            if should_error:
                spans.append({
                    "span_id": generate_uuid(),
                    "parent_span_id": trace_id,
                    "service": "redis-cache",
                    "operation": "GET auth:token:{id}",
                    "start_time": timestamp_to_iso(trace_time + timedelta(milliseconds=5)),
                    "duration_ms": 230,
                    "status": "TIMEOUT",
                    "tags": {"error": "connection_timeout"}
                })

            traces.append({"trace_id": trace_id, "timestamp": timestamp_to_iso(trace_time), "spans": spans})

        return traces

    def _generate_config_deltas(self) -> list[dict[str, Any]]:
        """Generate configuration changes."""
        # Redis scaling change that triggered the issue
        change_time = self.context.start_time - timedelta(minutes=10)

        return [
            {
                "timestamp": timestamp_to_iso(change_time),
                "service": "redis-cache",
                "change_type": "scaling",
                "initiator": "auto-scaler",
                "changes": [
                    {
                        "key": "max_connections",
                        "old_value": 1000,
                        "new_value": 500,
                        "category": "performance"
                    }
                ],
                "rollback_available": True
            }
        ]

    def _generate_timeline(self) -> dict[str, Any]:
        """Generate incident timeline."""
        timeline = TimelineGenerator(self.context)

        change_time = self.context.start_time - timedelta(minutes=10)
        timeline.add_config_change(
            change_time,
            "redis-cache",
            "Reduced max_connections from 1000 to 500",
            "auto-scaler"
        )

        detection_time = self.context.start_time + timedelta(minutes=1)
        timeline.add_anomaly_detection(
            detection_time,
            self.affected_service,
            "auth_error_rate",
            threshold=0.01,
            actual_value=self.spike_error_rate
        )

        alert_time = self.context.start_time + timedelta(minutes=2)
        timeline.add_alert(
            alert_time,
            self.affected_service,
            "High authentication failure rate",
            severity="critical"
        )

        mitigation_time = self.context.end_time - timedelta(minutes=3)
        timeline.add_mitigation(
            mitigation_time,
            "redis-cache",
            "Increased max_connections back to 1000"
        )

        timeline.add_resolution(
            self.context.end_time,
            "Redis connection limit restored, auth success rate normalized"
        )

        return timeline.generate()
