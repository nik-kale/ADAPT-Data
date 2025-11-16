"""Timeline generation for incidents."""

from datetime import datetime, timedelta
from typing import Any

from generator.core.base import BaseGenerator, IncidentContext
from generator.core.utils import timestamp_to_iso


class TimelineGenerator(BaseGenerator):
    """Generates incident timelines."""

    def __init__(self, context: IncidentContext) -> None:
        """Initialize timeline generator.

        Args:
            context: Incident context
        """
        super().__init__(context)
        self.events: list[dict[str, Any]] = []

    def add_event(
        self,
        timestamp: datetime,
        event_type: str,
        description: str,
        service: str = "",
        metadata: dict[str, Any] | None = None
    ) -> None:
        """Add an event to the timeline.

        Args:
            timestamp: When the event occurred
            event_type: Type of event
            description: Human-readable description
            service: Optional service name
            metadata: Optional additional metadata
        """
        event = {
            "timestamp": timestamp_to_iso(timestamp),
            "event_type": event_type,
            "description": description
        }

        if service:
            event["service"] = service

        if metadata:
            event["metadata"] = metadata

        self.events.append(event)

    def generate(self) -> dict[str, Any]:
        """Generate complete timeline.

        Returns:
            Timeline document
        """
        # Sort events by timestamp
        self.events.sort(key=lambda e: e["timestamp"])

        timeline = {
            "incident_id": self.context.incident_id,
            "title": self.context.root_cause or "Untitled Incident",
            "start_time": timestamp_to_iso(self.context.start_time),
            "end_time": timestamp_to_iso(self.context.end_time),
            "severity": self.context.severity,
            "affected_services": self.context.affected_services,
            "root_cause": self.context.root_cause,
            "events": self.events
        }

        # Save to file
        filename = f"timeline_{self.context.incident_id}.json"
        self.save_json(timeline, filename, "timelines")

        return timeline

    def add_anomaly_detection(
        self,
        timestamp: datetime,
        service: str,
        metric: str,
        threshold: float,
        actual_value: float
    ) -> None:
        """Add an anomaly detection event.

        Args:
            timestamp: When anomaly was detected
            service: Affected service
            metric: Metric name
            threshold: Threshold value
            actual_value: Actual observed value
        """
        self.add_event(
            timestamp=timestamp,
            event_type="anomaly_detected",
            description=f"Anomaly detected in {metric}",
            service=service,
            metadata={
                "metric": metric,
                "threshold": threshold,
                "actual_value": actual_value
            }
        )

    def add_alert(
        self,
        timestamp: datetime,
        service: str,
        alert_name: str,
        severity: str = "warning"
    ) -> None:
        """Add an alert event.

        Args:
            timestamp: When alert fired
            service: Affected service
            alert_name: Name of the alert
            severity: Alert severity
        """
        self.add_event(
            timestamp=timestamp,
            event_type="alert_fired",
            description=f"Alert: {alert_name}",
            service=service,
            metadata={
                "alert_name": alert_name,
                "severity": severity
            }
        )

    def add_config_change(
        self,
        timestamp: datetime,
        service: str,
        change_description: str,
        initiator: str = "automated"
    ) -> None:
        """Add a configuration change event.

        Args:
            timestamp: When change occurred
            service: Affected service
            change_description: Description of change
            initiator: Who/what initiated the change
        """
        self.add_event(
            timestamp=timestamp,
            event_type="config_change",
            description=change_description,
            service=service,
            metadata={"initiator": initiator}
        )

    def add_deployment(
        self,
        timestamp: datetime,
        service: str,
        old_version: str,
        new_version: str
    ) -> None:
        """Add a deployment event.

        Args:
            timestamp: When deployment occurred
            service: Service being deployed
            old_version: Previous version
            new_version: New version
        """
        self.add_event(
            timestamp=timestamp,
            event_type="deployment",
            description=f"Deployed {service} from {old_version} to {new_version}",
            service=service,
            metadata={
                "old_version": old_version,
                "new_version": new_version
            }
        )

    def add_mitigation(
        self,
        timestamp: datetime,
        service: str,
        action: str
    ) -> None:
        """Add a mitigation attempt event.

        Args:
            timestamp: When mitigation was attempted
            service: Service being mitigated
            action: Description of mitigation action
        """
        self.add_event(
            timestamp=timestamp,
            event_type="mitigation_attempted",
            description=action,
            service=service
        )

    def add_resolution(
        self,
        timestamp: datetime,
        description: str
    ) -> None:
        """Add incident resolution event.

        Args:
            timestamp: When incident was resolved
            description: How it was resolved
        """
        self.add_event(
            timestamp=timestamp,
            event_type="resolved",
            description=description
        )
