"""GenAI/LLM latency incident generator.

Simulates incidents related to LLM API calls, including:
- High latency due to large context windows
- Token limit exhaustion
- Rate limiting
- Model overload
"""

import random
from datetime import datetime, timedelta
from typing import Any

from generator.core.base import BaseGenerator, IncidentContext
from generator.core.semantic_conventions import SemanticConventions
from generator.core.utils import generate_uuid, timestamp_to_iso


class GenAILatencyGenerator(BaseGenerator):
    """Generate GenAI/LLM latency incidents.

    Simulates realistic LLM-related performance issues with full
    GenAI semantic conventions support.
    """

    def __init__(
        self,
        context: IncidentContext,
        affected_service: str = "llm-gateway",
        model_name: str = "gpt-4",
        baseline_latency_ms: float = 2000.0,
        degraded_latency_ms: float = 15000.0,
        baseline_tokens: int = 500,
        context_window_size: int = 8192,
        rate_limit_rpm: int = 3000
    ):
        """Initialize GenAI latency incident generator.

        Args:
            context: Incident context
            affected_service: Service making LLM calls
            model_name: LLM model name (gpt-4, claude-3, etc.)
            baseline_latency_ms: Normal latency
            degraded_latency_ms: Degraded latency during incident
            baseline_tokens: Normal token count
            context_window_size: Model context window size
            rate_limit_rpm: Rate limit in requests per minute
        """
        super().__init__(context)
        self.affected_service = affected_service
        self.model_name = model_name
        self.baseline_latency_ms = baseline_latency_ms
        self.degraded_latency_ms = degraded_latency_ms
        self.baseline_tokens = baseline_tokens
        self.context_window_size = context_window_size
        self.rate_limit_rpm = rate_limit_rpm

        # Update context
        context.affected_services = [affected_service]
        context.root_cause = (
            f"LLM API performance degradation due to large context windows "
            f"and high token usage approaching model limits"
        )

    def generate(self) -> dict[str, Any]:
        """Generate GenAI incident data."""
        logs = self._generate_logs()
        metrics = self._generate_metrics()
        traces = self._generate_traces()
        timeline = self._generate_timeline()

        # Save all data
        self.save_jsonl(logs, f"logs_{self.context.incident_id}.jsonl", "logs")
        self.save_jsonl(metrics, f"metrics_{self.context.incident_id}.jsonl", "metrics")
        self.save_jsonl(traces, f"traces_{self.context.incident_id}.jsonl", "traces")
        self.save_json(timeline, f"timeline_{self.context.incident_id}.json", "timelines")

        return {
            "incident_id": self.context.incident_id,
            "incident_type": "genai_latency",
            "affected_services": self.context.affected_services,
            "root_cause": self.context.root_cause,
            "num_logs": len(logs),
            "num_metrics": len(metrics),
            "num_traces": len(traces)
        }

    def _generate_logs(self) -> list[dict[str, Any]]:
        """Generate LLM-related logs."""
        logs = []
        hosts = self._get_service_hosts(self.affected_service)

        for current_time in self._iterate_time_window(step=timedelta(seconds=10)):
            is_during = self.context.is_during_incident(current_time)
            host = random.choice(hosts)

            # Normal operational logs
            if random.random() < 0.3:
                logs.append({
                    "timestamp": timestamp_to_iso(current_time),
                    "level": "INFO",
                    "service": self.affected_service,
                    "host": host,
                    "message": f"Processing LLM request for model {self.model_name}",
                    "metadata": {
                        "model": self.model_name,
                        "request_id": generate_uuid()
                    }
                })

            # Warning logs during incident
            if is_during and random.random() < 0.4:
                warning_messages = [
                    f"High token usage detected: approaching context window limit ({self.context_window_size} tokens)",
                    f"LLM API latency above threshold: {int(self.degraded_latency_ms)}ms",
                    f"Rate limit approaching: {int(self.rate_limit_rpm * 0.9)} RPM",
                    "Token truncation occurred due to context window size",
                    "Prompt compression applied to fit context window"
                ]

                logs.append({
                    "timestamp": timestamp_to_iso(current_time),
                    "level": "WARN",
                    "service": self.affected_service,
                    "host": host,
                    "message": random.choice(warning_messages),
                    "metadata": {
                        "model": self.model_name,
                        "latency_ms": random.randint(10000, 20000)
                    }
                })

            # Error logs during severe incidents
            if is_during and random.random() < 0.2:
                error_messages = [
                    f"LLM API request failed: Context length exceeded ({self.context_window_size} tokens)",
                    f"LLM API rate limit exceeded: {self.rate_limit_rpm} RPM",
                    "LLM API timeout: request took longer than 30s",
                    "Token limit exhausted for current billing period"
                ]

                logs.append({
                    "timestamp": timestamp_to_iso(current_time),
                    "level": "ERROR",
                    "service": self.affected_service,
                    "host": host,
                    "message": random.choice(error_messages),
                    "metadata": {
                        "model": self.model_name,
                        "error_type": "context_length_exceeded"
                    }
                })

        return logs

    def _generate_metrics(self) -> list[dict[str, Any]]:
        """Generate GenAI metrics."""
        metrics = []
        hosts = self._get_service_hosts(self.affected_service)

        for current_time in self._iterate_time_window(step=timedelta(minutes=1)):
            is_during = self.context.is_during_incident(current_time)
            host = random.choice(hosts)

            # LLM request latency
            if is_during:
                latency = random.gauss(self.degraded_latency_ms, 2000)
            else:
                latency = random.gauss(self.baseline_latency_ms, 200)

            metrics.append({
                "timestamp": timestamp_to_iso(current_time),
                "metric_name": "genai.request.duration",
                "value": max(0, latency),
                "unit": "ms",
                "service": self.affected_service,
                "host": host,
                "tags": {
                    "model": self.model_name,
                    "operation": "completion"
                },
                "anomaly_injected": is_during
            })

            # Token usage
            if is_during:
                # Approaching context window limit
                input_tokens = random.randint(
                    int(self.context_window_size * 0.7),
                    int(self.context_window_size * 0.95)
                )
            else:
                input_tokens = random.randint(self.baseline_tokens, self.baseline_tokens * 2)

            output_tokens = random.randint(100, 500)

            metrics.extend([
                {
                    "timestamp": timestamp_to_iso(current_time),
                    "metric_name": "genai.token.usage.input",
                    "value": input_tokens,
                    "unit": "tokens",
                    "service": self.affected_service,
                    "host": host,
                    "tags": {"model": self.model_name},
                    "anomaly_injected": is_during
                },
                {
                    "timestamp": timestamp_to_iso(current_time),
                    "metric_name": "genai.token.usage.output",
                    "value": output_tokens,
                    "unit": "tokens",
                    "service": self.affected_service,
                    "host": host,
                    "tags": {"model": self.model_name},
                    "anomaly_injected": False
                },
                {
                    "timestamp": timestamp_to_iso(current_time),
                    "metric_name": "genai.token.usage.total",
                    "value": input_tokens + output_tokens,
                    "unit": "tokens",
                    "service": self.affected_service,
                    "host": host,
                    "tags": {"model": self.model_name},
                    "anomaly_injected": is_during
                }
            ])

            # Request rate
            if is_during:
                # Rate limiting kicking in
                request_rate = random.randint(
                    int(self.rate_limit_rpm * 0.8),
                    self.rate_limit_rpm
                )
            else:
                request_rate = random.randint(100, int(self.rate_limit_rpm * 0.5))

            metrics.append({
                "timestamp": timestamp_to_iso(current_time),
                "metric_name": "genai.request.rate",
                "value": request_rate,
                "unit": "requests/min",
                "service": self.affected_service,
                "host": host,
                "tags": {"model": self.model_name},
                "anomaly_injected": False
            })

            # Error rate
            if is_during:
                error_rate = random.uniform(10.0, 30.0)  # 10-30% errors
            else:
                error_rate = random.uniform(0.1, 1.0)  # <1% errors

            metrics.append({
                "timestamp": timestamp_to_iso(current_time),
                "metric_name": "genai.request.error_rate",
                "value": error_rate,
                "unit": "percent",
                "service": self.affected_service,
                "host": host,
                "tags": {"model": self.model_name},
                "anomaly_injected": is_during
            })

        return metrics

    def _generate_traces(self) -> list[dict[str, Any]]:
        """Generate GenAI request traces."""
        traces = []
        hosts = self._get_service_hosts(self.affected_service)

        for current_time in self._iterate_time_window(step=timedelta(seconds=30)):
            is_during = self.context.is_during_incident(current_time)
            host = random.choice(hosts)

            # Generate trace with GenAI semantic conventions
            trace_id = generate_uuid()

            # Request latency
            if is_during:
                total_duration_ms = random.gauss(self.degraded_latency_ms, 2000)
                input_tokens = random.randint(
                    int(self.context_window_size * 0.7),
                    int(self.context_window_size * 0.95)
                )
            else:
                total_duration_ms = random.gauss(self.baseline_latency_ms, 200)
                input_tokens = random.randint(self.baseline_tokens, self.baseline_tokens * 2)

            output_tokens = random.randint(100, 500)

            # Build spans with GenAI semantic conventions
            spans = [
                {
                    "span_id": generate_uuid(),
                    "parent_span_id": None,
                    "service": self.affected_service,
                    "operation": "llm.completion",
                    "start_time": timestamp_to_iso(current_time),
                    "duration_ms": total_duration_ms,
                    "status": "OK" if not is_during or random.random() > 0.3 else "ERROR",
                    "tags": {
                        **SemanticConventions.get_genai_span_attributes(
                            system="openai",
                            model=self.model_name,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            temperature=0.7,
                            max_tokens=4096
                        ),
                        "service.name": self.affected_service,
                        "host.name": host
                    }
                }
            ]

            traces.append({
                "trace_id": trace_id,
                "timestamp": timestamp_to_iso(current_time),
                "spans": spans,
                "service": self.affected_service
            })

        return traces

    def _generate_timeline(self) -> dict[str, Any]:
        """Generate incident timeline."""
        return {
            "incident_id": self.context.incident_id,
            "start_time": timestamp_to_iso(self.context.start_time),
            "end_time": timestamp_to_iso(self.context.end_time),
            "severity": self.context.severity,
            "events": [
                {
                    "timestamp": timestamp_to_iso(self.context.start_time - timedelta(minutes=10)),
                    "event_type": "normal",
                    "description": f"Normal LLM operations for {self.model_name}"
                },
                {
                    "timestamp": timestamp_to_iso(self.context.start_time),
                    "event_type": "detection",
                    "description": f"High latency detected for {self.model_name} API calls"
                },
                {
                    "timestamp": timestamp_to_iso(self.context.start_time + timedelta(minutes=5)),
                    "event_type": "analysis",
                    "description": "Token usage approaching context window limits"
                },
                {
                    "timestamp": timestamp_to_iso(self.context.start_time + timedelta(minutes=10)),
                    "event_type": "mitigation",
                    "description": "Enabled prompt compression and context truncation"
                },
                {
                    "timestamp": timestamp_to_iso(self.context.end_time),
                    "event_type": "resolution",
                    "description": "Latency returned to normal, context management optimized"
                }
            ]
        }
