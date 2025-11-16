"""Multi-incident cascade generator."""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from generator.core.base import BaseGenerator, IncidentContext
from generator.core.logging_config import get_logger
from generator.core.timeline import TimelineGenerator
from generator.incidents.latency_regression import LatencyRegressionGenerator
from generator.incidents.auth_failure import AuthFailureGenerator
from generator.incidents.dependency_outage import DependencyOutageGenerator

logger = get_logger(__name__)


class CascadeGenerator(BaseGenerator):
    """Generates multi-incident cascades where incidents trigger each other.

    This simulates realistic scenarios where one failure cascades into others,
    such as:
    - Deployment → Latency → Database overload → Auth failures
    - Config change → Memory leak → Service crash → Dependency outage
    """

    def __init__(
        self,
        context: IncidentContext,
        cascade_config: list[dict[str, Any]]
    ) -> None:
        """Initialize cascade generator.

        Args:
            context: Incident context
            cascade_config: List of incident specifications in order
        """
        super().__init__(context)
        self.cascade_config = cascade_config

        # Collect all affected services
        all_services = set()
        for incident_spec in cascade_config:
            service = incident_spec.get("service")
            if service:
                all_services.add(service)

        context.affected_services = list(all_services)
        context.root_cause = self._build_root_cause_description()

    def _build_root_cause_description(self) -> str:
        """Build description of cascade."""
        if not self.cascade_config:
            return "Multi-incident cascade"

        first = self.cascade_config[0]
        last = self.cascade_config[-1]

        return (
            f"Cascade failure: {first.get('type', 'incident')} in "
            f"{first.get('service', 'unknown')} led to "
            f"{last.get('type', 'incident')} affecting multiple services"
        )

    def generate(self) -> dict[str, Any]:
        """Generate cascading incident data."""
        logger.info(f"Generating cascade with {len(self.cascade_config)} incidents...")

        all_logs = []
        all_metrics = []
        all_traces = []
        all_config_deltas = []

        timeline = TimelineGenerator(self.context)

        current_time = self.context.start_time

        for i, incident_spec in enumerate(self.cascade_config):
            logger.info(f"  Generating incident {i+1}/{len(self.cascade_config)}: {incident_spec['type']}")

            # Calculate timing
            delay_str = incident_spec.get("delay", "0m")
            delay = self._parse_duration(delay_str)
            incident_start = current_time + delay

            duration_str = incident_spec.get("duration", "10m")
            incident_duration = self._parse_duration(duration_str)

            # Create unique sub-directory for this incident to avoid overwrites
            sub_output_dir = self.context.output_dir / f"sub_incident_{i+1}"
            sub_output_dir.mkdir(parents=True, exist_ok=True)

            # Create sub-context for this incident
            sub_context = IncidentContext(
                incident_id=f"{self.context.incident_id}-{i+1}",
                start_time=incident_start,
                duration=incident_duration,
                severity=incident_spec.get("severity", self.context.severity),
                output_dir=sub_output_dir,
                topology=self.context.topology,
                scenario_config=self.context.scenario_config
            )

            # Generate based on type
            incident_type = incident_spec["type"]
            service = incident_spec.get("service", "unknown-service")

            if incident_type == "latency_regression":
                generator = LatencyRegressionGenerator(
                    sub_context,
                    affected_service=service,
                    baseline_latency_ms=incident_spec.get("baseline_latency", 50.0),
                    degraded_latency_ms=incident_spec.get("degraded_latency", 500.0)
                )
            elif incident_type == "auth_failure":
                generator = AuthFailureGenerator(
                    sub_context,
                    affected_service=service
                )
            elif incident_type == "dependency_outage":
                generator = DependencyOutageGenerator(
                    sub_context,
                    failed_service=service
                )
            else:
                # Fallback to latency
                logger.warning(f"Unknown incident type '{incident_type}', using latency_regression")
                generator = LatencyRegressionGenerator(sub_context, affected_service=service)

            # Generate incident data
            result = generator.generate()

            # Collect generated data from sub-incident
            logs = self._read_jsonl_files(sub_output_dir / "logs")
            metrics = self._read_jsonl_files(sub_output_dir / "metrics")
            traces = self._read_jsonl_files(sub_output_dir / "traces")
            config_deltas = self._read_jsonl_files(sub_output_dir / "config_deltas")

            all_logs.extend(logs)
            all_metrics.extend(metrics)
            all_traces.extend(traces)
            all_config_deltas.extend(config_deltas)

            logger.info(f"  Collected {len(logs)} logs, {len(metrics)} metrics, {len(traces)} traces")

            # Add to timeline
            timeline.add_event(
                incident_start,
                "other",
                f"Incident {i+1} started: {incident_type} in {service}",
                service=service,
                metadata={"incident_type": incident_type, "triggered_by": incident_spec.get("trigger")}
            )

            # Update current time for next incident
            current_time = incident_start + incident_duration

        # Write merged data to main output directory
        logger.info(f"Writing merged data: {len(all_logs)} logs, {len(all_metrics)} metrics, {len(all_traces)} traces")

        if all_logs:
            self.save_jsonl(all_logs, "cascade_logs.jsonl", "logs")
        if all_metrics:
            self.save_jsonl(all_metrics, "cascade_metrics.jsonl", "metrics")
        if all_traces:
            self.save_jsonl(all_traces, "cascade_traces.jsonl", "traces")
        if all_config_deltas:
            self.save_jsonl(all_config_deltas, "cascade_config_deltas.jsonl", "config_deltas")

        # Generate combined timeline
        timeline_result = timeline.generate()

        logger.info(f"Generated cascade with {len(timeline_result['events'])} timeline events")

        return {
            "incident_id": self.context.incident_id,
            "incident_type": "cascade",
            "num_incidents": len(self.cascade_config),
            "cascade_duration": str(self.context.duration),
            "affected_services": len(self.context.affected_services),
            "total_logs": len(all_logs),
            "total_metrics": len(all_metrics),
            "total_traces": len(all_traces)
        }

    def _read_jsonl_files(self, directory: Path) -> list[dict[str, Any]]:
        """Read all JSONL files from a directory.

        Args:
            directory: Directory containing JSONL files

        Returns:
            List of all JSON objects from all files
        """
        data = []

        if not directory.exists():
            return data

        for jsonl_file in directory.glob("*.jsonl"):
            try:
                with open(jsonl_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            data.append(json.loads(line))
            except Exception as e:
                logger.error(f"Error reading {jsonl_file}: {e}")

        return data

    def _parse_duration(self, duration_str: str) -> timedelta:
        """Parse duration string like '5m', '2h'."""
        from generator.core.utils import parse_duration
        return parse_duration(duration_str)
