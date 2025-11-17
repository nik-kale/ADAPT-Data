"""SLO breach incident generator.

Simulates Service Level Objective violations including:
- Error budget exhaustion
- Latency SLO violations
- Availability SLO misses
- Custom SLI/SLO definitions
"""

import random
from datetime import datetime, timedelta
from typing import Any

from generator.core.base import BaseGenerator, IncidentContext
from generator.core.utils import generate_uuid, timestamp_to_iso


class SLOBreachGenerator(BaseGenerator):
    """Generate SLO breach incidents."""

    def __init__(
        self,
        context: IncidentContext,
        affected_service: str = "payment-service",
        slo_type: str = "availability",  # availability, latency, error_rate
        slo_target: float = 99.9,  # 99.9% for availability, 200ms for latency
        error_budget_hours: float = 7.3,  # Monthly error budget
        breach_severity: float = 1.5  # Multiplier for breach severity
    ):
        """Initialize SLO breach generator.

        Args:
            context: Incident context
            affected_service: Service with SLO breach
            slo_type: Type of SLO (availability, latency, error_rate)
            slo_target: SLO target value
            error_budget_hours: Error budget in hours
            breach_severity: How severe the breach is (1.0 = at limit, >1.0 = exceeded)
        """
        super().__init__(context)
        self.affected_service = affected_service
        self.slo_type = slo_type
        self.slo_target = slo_target
        self.error_budget_hours = error_budget_hours
        self.breach_severity = breach_severity

        context.affected_services = [affected_service]
        context.root_cause = (
            f"SLO breach: {slo_type} fell below {slo_target}% target, "
            f"error budget exhausted"
        )

    def generate(self) -> dict[str, Any]:
        """Generate SLO breach incident data."""
        logs = self._generate_logs()
        metrics = self._generate_metrics()
        timeline = self._generate_timeline()
        slo_report = self._generate_slo_report()

        self.save_jsonl(logs, f"logs_{self.context.incident_id}.jsonl", "logs")
        self.save_jsonl(metrics, f"metrics_{self.context.incident_id}.jsonl", "metrics")
        self.save_json(timeline, f"timeline_{self.context.incident_id}.json", "timelines")
        self.save_json(slo_report, f"slo_report_{self.context.incident_id}.json", "timelines")

        return {
            "incident_id": self.context.incident_id,
            "incident_type": "slo_breach",
            "slo_type": self.slo_type,
            "affected_services": self.context.affected_services,
            "error_budget_consumed_pct": self._calculate_error_budget_consumed()
        }

    def _generate_logs(self) -> list[dict[str, Any]]:
        """Generate SLO-related logs."""
        logs = []
        hosts = self._get_service_hosts(self.affected_service)

        for current_time in self._iterate_time_window(step=timedelta(minutes=1)):
            is_during = self.context.is_during_incident(current_time)
            host = random.choice(hosts)

            # SLO alert logs
            if is_during and random.random() < 0.2:
                logs.append({
                    "timestamp": timestamp_to_iso(current_time),
                    "level": "ERROR",
                    "service": "slo-monitor",
                    "host": "monitoring-001",
                    "message": f"SLO breach detected for {self.affected_service}: "
                              f"{self.slo_type} below target",
                    "metadata": {
                        "service": self.affected_service,
                        "slo_type": self.slo_type,
                        "target": self.slo_target,
                        "current": self.slo_target / self.breach_severity
                    }
                })

            # Error budget warnings
            if is_during and random.random() < 0.15:
                error_budget_remaining = max(0, 100 - self._calculate_error_budget_consumed())
                logs.append({
                    "timestamp": timestamp_to_iso(current_time),
                    "level": "WARN",
                    "service": "slo-monitor",
                    "host": "monitoring-001",
                    "message": f"Error budget consumption: {error_budget_remaining:.1f}% remaining",
                    "metadata": {
                        "service": self.affected_service,
                        "error_budget_remaining_pct": error_budget_remaining
                    }
                })

        return logs

    def _generate_metrics(self) -> list[dict[str, Any]]:
        """Generate SLO metrics."""
        metrics = []
        hosts = self._get_service_hosts(self.affected_service)

        for current_time in self._iterate_time_window(step=timedelta(minutes=1)):
            is_during = self.context.is_during_incident(current_time)
            host = random.choice(hosts)

            # Generate SLO-specific metrics
            if self.slo_type == "availability":
                if is_during:
                    availability = random.uniform(
                        self.slo_target / self.breach_severity,
                        self.slo_target * 0.98
                    )
                else:
                    availability = random.uniform(self.slo_target, 100.0)

                metrics.append({
                    "timestamp": timestamp_to_iso(current_time),
                    "metric_name": "slo.availability",
                    "value": availability,
                    "unit": "percent",
                    "service": self.affected_service,
                    "host": host,
                    "tags": {"slo_target": str(self.slo_target)},
                    "anomaly_injected": is_during
                })

            elif self.slo_type == "latency":
                if is_during:
                    latency = random.gauss(
                        self.slo_target * self.breach_severity,
                        self.slo_target * 0.2
                    )
                else:
                    latency = random.gauss(
                        self.slo_target * 0.7,
                        self.slo_target * 0.1
                    )

                metrics.append({
                    "timestamp": timestamp_to_iso(current_time),
                    "metric_name": "slo.latency.p99",
                    "value": max(0, latency),
                    "unit": "ms",
                    "service": self.affected_service,
                    "host": host,
                    "tags": {"slo_target": str(self.slo_target)},
                    "anomaly_injected": is_during
                })

            # Error budget consumption
            budget_consumed = self._calculate_error_budget_consumed(current_time)
            metrics.append({
                "timestamp": timestamp_to_iso(current_time),
                "metric_name": "slo.error_budget.consumed",
                "value": budget_consumed,
                "unit": "percent",
                "service": self.affected_service,
                "host": "monitoring-001",
                "tags": {},
                "anomaly_injected": False
            })

        return metrics

    def _calculate_error_budget_consumed(
        self,
        current_time: datetime = None
    ) -> float:
        """Calculate error budget consumed."""
        if current_time is None:
            current_time = self.context.end_time

        if current_time < self.context.start_time:
            return 0.0

        # Calculate how much of incident window has passed
        incident_duration = self.context.end_time - self.context.start_time
        elapsed = min(current_time, self.context.end_time) - self.context.start_time

        progress = elapsed.total_seconds() / incident_duration.total_seconds()

        # Error budget consumption accelerates during incident
        budget_consumed = min(100.0, progress * self.breach_severity * 100)

        return budget_consumed

    def _generate_timeline(self) -> dict[str, Any]:
        """Generate SLO breach timeline."""
        return {
            "incident_id": self.context.incident_id,
            "start_time": timestamp_to_iso(self.context.start_time),
            "end_time": timestamp_to_iso(self.context.end_time),
            "severity": self.context.severity,
            "events": [
                {
                    "timestamp": timestamp_to_iso(self.context.start_time - timedelta(minutes=30)),
                    "event_type": "normal",
                    "description": f"SLO compliance: {self.slo_type} at {self.slo_target}%"
                },
                {
                    "timestamp": timestamp_to_iso(self.context.start_time),
                    "event_type": "detection",
                    "description": f"SLO breach detected: {self.slo_type} below target"
                },
                {
                    "timestamp": timestamp_to_iso(self.context.start_time + timedelta(minutes=10)),
                    "event_type": "escalation",
                    "description": "Error budget 50% consumed, incident escalated"
                },
                {
                    "timestamp": timestamp_to_iso(self.context.start_time + timedelta(minutes=20)),
                    "event_type": "critical",
                    "description": "Error budget exhausted, SLO compliance at risk"
                },
                {
                    "timestamp": timestamp_to_iso(self.context.end_time),
                    "event_type": "resolution",
                    "description": f"Service recovered, SLO compliance restored"
                }
            ]
        }

    def _generate_slo_report(self) -> dict[str, Any]:
        """Generate detailed SLO report."""
        return {
            "report_id": generate_uuid(),
            "incident_id": self.context.incident_id,
            "service": self.affected_service,
            "slo_definition": {
                "type": self.slo_type,
                "target": self.slo_target,
                "measurement_window": "30 days",
                "error_budget_hours": self.error_budget_hours
            },
            "breach_summary": {
                "breach_start": timestamp_to_iso(self.context.start_time),
                "breach_end": timestamp_to_iso(self.context.end_time),
                "breach_duration_minutes": (self.context.end_time - self.context.start_time).total_seconds() / 60,
                "severity": self.breach_severity
            },
            "error_budget_analysis": {
                "monthly_budget_hours": self.error_budget_hours,
                "consumed_hours": (self.context.end_time - self.context.start_time).total_seconds() / 3600 * self.breach_severity,
                "consumed_percent": self._calculate_error_budget_consumed(),
                "remaining_hours": max(0, self.error_budget_hours - ((self.context.end_time - self.context.start_time).total_seconds() / 3600 * self.breach_severity))
            },
            "recommendations": [
                "Review incident postmortem and implement preventive measures",
                "Consider adjusting SLO targets based on user impact",
                "Implement proactive monitoring for early SLO degradation detection",
                "Review error budget policy and burn rate alerting"
            ]
        }
