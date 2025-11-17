"""Multi-region outage incident generator.

Simulates incidents spanning multiple geographic regions, including:
- Region-wide failures
- Cross-region cascade failures
- Network partitions between regions
- Data replication lag
"""

import random
from datetime import datetime, timedelta
from typing import Any

from generator.core.base import BaseGenerator, IncidentContext
from generator.core.utils import generate_uuid, timestamp_to_iso


class MultiRegionOutageGenerator(BaseGenerator):
    """Generate multi-region outage incidents."""

    def __init__(
        self,
        context: IncidentContext,
        affected_service: str = "api-gateway",
        primary_region: str = "us-east-1",
        secondary_regions: list[str] = None,
        cascade_delay_minutes: int = 5
    ):
        """Initialize multi-region outage generator.

        Args:
            context: Incident context
            affected_service: Service experiencing outage
            primary_region: Region where failure starts
            secondary_regions: Regions that cascade (default: us-west-2, eu-west-1)
            cascade_delay_minutes: Time between region failures
        """
        super().__init__(context)
        self.affected_service = affected_service
        self.primary_region = primary_region
        self.secondary_regions = secondary_regions or ["us-west-2", "eu-west-1"]
        self.cascade_delay = timedelta(minutes=cascade_delay_minutes)

        # Update context
        context.affected_services = [affected_service]
        context.root_cause = (
            f"Multi-region outage starting in {primary_region}, "
            f"cascading to {len(self.secondary_regions)} regions"
        )

    def generate(self) -> dict[str, Any]:
        """Generate multi-region outage data."""
        logs = self._generate_logs()
        metrics = self._generate_metrics()
        timeline = self._generate_timeline()

        self.save_jsonl(logs, f"logs_{self.context.incident_id}.jsonl", "logs")
        self.save_jsonl(metrics, f"metrics_{self.context.incident_id}.jsonl", "metrics")
        self.save_json(timeline, f"timeline_{self.context.incident_id}.json", "timelines")

        return {
            "incident_id": self.context.incident_id,
            "incident_type": "multi_region_outage",
            "affected_services": self.context.affected_services,
            "root_cause": self.context.root_cause,
            "regions": [self.primary_region] + self.secondary_regions
        }

    def _generate_logs(self) -> list[dict[str, Any]]:
        """Generate multi-region logs."""
        logs = []
        all_regions = [self.primary_region] + self.secondary_regions

        for current_time in self._iterate_time_window(step=timedelta(seconds=30)):
            for idx, region in enumerate(all_regions):
                # Calculate when this region starts failing
                region_failure_start = self.context.start_time + (self.cascade_delay * idx)
                is_failing = current_time >= region_failure_start and \
                            self.context.is_during_incident(current_time)

                host = f"{self.affected_service}-{region}-001"

                if is_failing and random.random() < 0.4:
                    logs.append({
                        "timestamp": timestamp_to_iso(current_time),
                        "level": "ERROR",
                        "service": self.affected_service,
                        "host": host,
                        "message": f"Region {region} experiencing service degradation",
                        "metadata": {
                            "region": region,
                            "availability_zone": f"{region}a",
                            "error_type": "region_failure"
                        }
                    })

        return logs

    def _generate_metrics(self) -> list[dict[str, Any]]:
        """Generate multi-region metrics."""
        metrics = []
        all_regions = [self.primary_region] + self.secondary_regions

        for current_time in self._iterate_time_window(step=timedelta(minutes=1)):
            for idx, region in enumerate(all_regions):
                region_failure_start = self.context.start_time + (self.cascade_delay * idx)
                is_failing = current_time >= region_failure_start and \
                            self.context.is_during_incident(current_time)

                # Availability metric
                if is_failing:
                    availability = random.uniform(0, 30)  # 0-30% availability
                else:
                    availability = random.uniform(98, 100)

                metrics.append({
                    "timestamp": timestamp_to_iso(current_time),
                    "metric_name": "region.availability",
                    "value": availability,
                    "unit": "percent",
                    "service": self.affected_service,
                    "host": f"{region}-monitor",
                    "tags": {"region": region},
                    "anomaly_injected": is_failing
                })

        return metrics

    def _generate_timeline(self) -> dict[str, Any]:
        """Generate multi-region timeline."""
        events = [{
            "timestamp": timestamp_to_iso(self.context.start_time),
            "event_type": "detection",
            "description": f"Primary region {self.primary_region} failure detected"
        }]

        for idx, region in enumerate(self.secondary_regions):
            cascade_time = self.context.start_time + (self.cascade_delay * (idx + 1))
            events.append({
                "timestamp": timestamp_to_iso(cascade_time),
                "event_type": "escalation",
                "description": f"Failure cascaded to region {region}"
            })

        return {
            "incident_id": self.context.incident_id,
            "start_time": timestamp_to_iso(self.context.start_time),
            "end_time": timestamp_to_iso(self.context.end_time),
            "severity": self.context.severity,
            "events": events
        }
