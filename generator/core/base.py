"""Base classes for incident generators."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from generator.core.utils import generate_uuid, timestamp_to_iso


@dataclass
class IncidentContext:
    """Context for an incident generation session.

    Attributes:
        incident_id: Unique incident identifier
        start_time: When the incident starts
        end_time: When the incident ends
        duration: Incident duration
        severity: Incident severity (SEV1-SEV4)
        affected_services: List of affected service names
        root_cause: Root cause description
        output_dir: Directory to write output files
        topology: System topology definition
        scenario_config: Additional scenario configuration
    """

    incident_id: str = field(default_factory=lambda: generate_uuid())
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration: timedelta = field(default=timedelta(hours=1))
    severity: str = "SEV3"
    affected_services: list[str] = field(default_factory=list)
    root_cause: str = ""
    output_dir: Path = field(default=Path("./output"))
    topology: dict[str, Any] = field(default_factory=dict)
    scenario_config: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize computed fields."""
        if self.end_time is None:
            self.end_time = self.start_time + self.duration

        # Ensure output directories exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "logs").mkdir(exist_ok=True)
        (self.output_dir / "metrics").mkdir(exist_ok=True)
        (self.output_dir / "traces").mkdir(exist_ok=True)
        (self.output_dir / "config_deltas").mkdir(exist_ok=True)
        (self.output_dir / "timelines").mkdir(exist_ok=True)
        (self.output_dir / "topology").mkdir(exist_ok=True)

    def is_during_incident(self, timestamp: datetime) -> bool:
        """Check if a timestamp falls during the incident.

        Args:
            timestamp: Timestamp to check

        Returns:
            True if timestamp is during incident
        """
        return self.start_time <= timestamp <= self.end_time

    def get_incident_progress(self, timestamp: datetime) -> float:
        """Get progress through incident (0.0 to 1.0).

        Args:
            timestamp: Current timestamp

        Returns:
            Progress ratio (0.0 at start, 1.0 at end)
        """
        if timestamp < self.start_time:
            return 0.0
        if timestamp > self.end_time:
            return 1.0

        elapsed = timestamp - self.start_time
        return elapsed / self.duration


class BaseGenerator(ABC):
    """Base class for all data generators.

    Subclasses must implement the generate() method to produce
    their specific type of telemetry data.
    """

    def __init__(self, context: IncidentContext) -> None:
        """Initialize generator with incident context.

        Args:
            context: Incident context
        """
        self.context = context

    @abstractmethod
    def generate(self) -> dict[str, Any]:
        """Generate data for this component.

        Returns:
            Dictionary containing generated data
        """
        pass

    def save_json(self, data: Any, filename: str, subdir: str = "") -> Path:
        """Save data as JSON file.

        Args:
            data: Data to save
            filename: Output filename
            subdir: Optional subdirectory within output_dir

        Returns:
            Path to saved file
        """
        import json

        output_path = self.context.output_dir
        if subdir:
            output_path = output_path / subdir
            output_path.mkdir(parents=True, exist_ok=True)

        filepath = output_path / filename
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        return filepath

    def save_jsonl(self, records: list[dict[str, Any]], filename: str, subdir: str = "") -> Path:
        """Save records as JSON Lines file.

        Args:
            records: List of records to save
            filename: Output filename
            subdir: Optional subdirectory

        Returns:
            Path to saved file
        """
        import json

        output_path = self.context.output_dir
        if subdir:
            output_path = output_path / subdir
            output_path.mkdir(parents=True, exist_ok=True)

        filepath = output_path / filename
        with open(filepath, 'w') as f:
            for record in records:
                f.write(json.dumps(record, default=str) + '\n')

        return filepath

    def _get_service_hosts(self, service_name: str) -> list[str]:
        """Get list of host identifiers for a service.

        Args:
            service_name: Service name

        Returns:
            List of host identifiers
        """
        # Find service in topology
        services = self.context.topology.get('services', [])
        for service in services:
            if service['name'] == service_name:
                instances = service.get('instances', 1)
                return [f"{service_name}-{i:03d}" for i in range(instances)]

        # Default if not found
        return [f"{service_name}-000"]
