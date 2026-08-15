"""Base classes for incident generators."""

import json
import math
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

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

    def stream_jsonl(
        self,
        records: Iterable[dict[str, Any]],
        filename: str,
        subdir: str = "",
        buffer_size: int = 1000
    ) -> tuple[Path, int]:
        """Write records to a JSON Lines file without buffering them all.

        The streaming counterpart to :meth:`save_jsonl`. Because ``records`` is
        consumed lazily, a generator can produce millions of entries at flat
        memory cost.

        Args:
            records: Records to write. Consumed lazily.
            filename: Output filename
            subdir: Optional subdirectory
            buffer_size: Records held in memory between disk flushes

        Returns:
            Tuple of (path to saved file, number of records written)
        """
        from generator.core.streaming import StreamingJSONLWriter

        output_path = self.context.output_dir
        if subdir:
            output_path = output_path / subdir

        filepath = output_path / filename

        with StreamingJSONLWriter(filepath, buffer_size=buffer_size) as writer:
            count = writer.write_all(records)

        return filepath, count

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

    def _iterate_time_window(
        self,
        start_offset_minutes: int = -30,
        end_offset_minutes: int = 30,
        step: timedelta = timedelta(seconds=1)
    ):
        """Iterate over time window for data generation.

        Args:
            start_offset_minutes: Minutes before incident start (negative value)
            end_offset_minutes: Minutes after incident end (positive value)
            step: Time step between iterations

        Yields:
            datetime: Current timestamp in the iteration
        """
        current_time = self.context.start_time + timedelta(minutes=start_offset_minutes)
        end_time = self.context.end_time + timedelta(minutes=end_offset_minutes)
        while current_time < end_time:
            yield current_time
            current_time += step

    def _generate_time_series_metrics(
        self,
        metric_builders: list[Callable],
        step: timedelta = timedelta(minutes=1)
    ) -> list[dict]:
        """Generate time-series metrics using builder functions.

        Args:
            metric_builders: List of functions that take (timestamp, host) and return a metric dict or None
            step: Time step between metric samples

        Returns:
            List of generated metrics
        """
        metrics = []
        hosts = self._get_service_hosts(self.affected_service)

        for current_time in self._iterate_time_window(step=step):
            for host in hosts:
                for builder in metric_builders:
                    metric = builder(current_time, host)
                    if metric:
                        metrics.append(metric)
        return metrics

    def _should_generate_log(self, probability: float = 0.1) -> bool:
        """Determine if a log should be generated based on probability.

        Args:
            probability: Probability threshold (0.0 to 1.0)

        Returns:
            True if a log should be generated
        """
        return random.random() < probability

    def validate_output(self) -> dict[str, Any]:
        """Validate generated output data quality.

        Performs comprehensive quality checks on all generated telemetry data
        including metrics, logs, and traces. Validation checks include:
        - Timestamp format and consistency
        - Required field presence
        - Value ranges and validity
        - Service consistency
        - Anomaly presence during incident window

        Returns:
            Validation results dict with issues found:
            {
                "errors": [],      # Critical issues that break data integrity
                "warnings": [],    # Issues that may affect analysis quality
                "info": [],        # Informational messages about data
                "summary": {       # Overall validation summary
                    "total_errors": int,
                    "total_warnings": int,
                    "files_validated": int,
                    "validation_passed": bool
                }
            }
        """
        issues = {
            "errors": [],
            "warnings": [],
            "info": []
        }

        # Check each data type
        self._validate_metrics(issues)
        self._validate_logs(issues)
        self._validate_traces(issues)

        # Add summary
        issues["summary"] = {
            "total_errors": len(issues["errors"]),
            "total_warnings": len(issues["warnings"]),
            "files_validated": self._count_output_files(),
            "validation_passed": len(issues["errors"]) == 0
        }

        return issues

    def _count_output_files(self) -> int:
        """Count total number of output files generated."""
        count = 0
        for subdir in ["logs", "metrics", "traces", "config_deltas", "timelines"]:
            dir_path = self.context.output_dir / subdir
            if dir_path.exists():
                count += len(list(dir_path.glob("*.jsonl"))) + len(list(dir_path.glob("*.json")))
        return count

    def _validate_metrics(self, issues: dict[str, list[str]]) -> None:
        """Validate metrics data.

        Args:
            issues: Issues dictionary to append validation results
        """
        metrics_dir = self.context.output_dir / "metrics"
        if not metrics_dir.exists():
            issues["warnings"].append("No metrics directory found")
            return

        metrics_files = list(metrics_dir.glob("*.jsonl"))
        if not metrics_files:
            issues["warnings"].append("No metrics files found")
            return

        for metrics_file in metrics_files:
            try:
                metrics = self._load_jsonl(metrics_file)
                issues["info"].append(f"Validating {len(metrics)} metrics from {metrics_file.name}")

                # Track timestamps for monotonic check
                timestamps_by_service = {}
                anomaly_count = 0
                baseline_count = 0

                for idx, metric in enumerate(metrics):
                    # Required fields validation
                    required_fields = ["timestamp", "metric_name", "value", "service"]
                    missing_fields = [f for f in required_fields if f not in metric]
                    if missing_fields:
                        issues["errors"].append(
                            f"Metric at index {idx} in {metrics_file.name} missing required fields: {missing_fields}"
                        )
                        continue

                    # Timestamp validation
                    try:
                        ts = self._parse_timestamp(metric["timestamp"])

                        # Check if timestamp is within reasonable range
                        # (30 minutes before incident start to 30 minutes after incident end)
                        min_time = self.context.start_time - timedelta(minutes=30)
                        max_time = self.context.end_time + timedelta(minutes=30)
                        if not (min_time <= ts <= max_time):
                            issues["warnings"].append(
                                f"Metric timestamp {metric['timestamp']} in {metrics_file.name} "
                                f"outside expected range ({min_time} to {max_time})"
                            )

                        # Track for monotonic check
                        service = metric["service"]
                        if service not in timestamps_by_service:
                            timestamps_by_service[service] = []
                        timestamps_by_service[service].append((idx, ts, metric["timestamp"]))

                    except (ValueError, KeyError) as e:
                        issues["errors"].append(
                            f"Invalid timestamp format in metric at index {idx} "
                            f"in {metrics_file.name}: {e}"
                        )

                    # Value validation
                    value = metric["value"]
                    if not isinstance(value, (int, float)):
                        issues["errors"].append(
                            f"Metric value at index {idx} in {metrics_file.name} "
                            f"is not numeric: {type(value).__name__}"
                        )
                    elif math.isnan(value):
                        issues["errors"].append(
                            f"Metric value at index {idx} in {metrics_file.name} is NaN"
                        )
                    elif math.isinf(value):
                        issues["errors"].append(
                            f"Metric value at index {idx} in {metrics_file.name} is Inf"
                        )
                    elif value < 0 and metric.get("metric_type") != "gauge":
                        issues["warnings"].append(
                            f"Metric value at index {idx} in {metrics_file.name} "
                            f"is negative for non-gauge metric"
                        )

                    # Service consistency
                    if service not in self._get_all_services():
                        issues["warnings"].append(
                            f"Metric at index {idx} references unknown service: {service}"
                        )

                    # Count anomalies
                    if metric.get("anomaly_injected"):
                        anomaly_count += 1
                    else:
                        baseline_count += 1

                # Check monotonic timestamps per service
                for service, timestamps in timestamps_by_service.items():
                    for i in range(1, len(timestamps)):
                        idx_prev, ts_prev, str_prev = timestamps[i-1]
                        idx_curr, ts_curr, str_curr = timestamps[i]
                        if ts_curr < ts_prev:
                            issues["errors"].append(
                                f"Non-monotonic timestamps in {metrics_file.name} for service {service}: "
                                f"index {idx_prev} ({str_prev}) > index {idx_curr} ({str_curr})"
                            )

                # Check anomaly presence
                if anomaly_count == 0:
                    issues["warnings"].append(
                        f"No anomalies detected in {metrics_file.name} - "
                        "incident window may not have anomalous data"
                    )
                elif baseline_count == 0:
                    issues["warnings"].append(
                        f"No baseline data in {metrics_file.name} - "
                        "all metrics are anomalous"
                    )
                else:
                    issues["info"].append(
                        f"Metrics in {metrics_file.name}: {anomaly_count} anomalous, "
                        f"{baseline_count} baseline"
                    )

            except Exception as e:
                issues["errors"].append(f"Failed to validate metrics file {metrics_file.name}: {e}")

    def _validate_logs(self, issues: dict[str, list[str]]) -> None:
        """Validate logs data.

        Args:
            issues: Issues dictionary to append validation results
        """
        logs_dir = self.context.output_dir / "logs"
        if not logs_dir.exists():
            issues["warnings"].append("No logs directory found")
            return

        log_files = list(logs_dir.glob("*.jsonl"))
        if not log_files:
            issues["warnings"].append("No log files found")
            return

        valid_log_levels = {"DEBUG", "INFO", "WARN", "WARNING", "ERROR", "FATAL", "CRITICAL"}

        for log_file in log_files:
            try:
                logs = self._load_jsonl(log_file)
                issues["info"].append(f"Validating {len(logs)} log entries from {log_file.name}")

                timestamps = []
                level_counts = {}

                for idx, log in enumerate(logs):
                    # Required fields validation
                    required_fields = ["timestamp", "level", "service", "message"]
                    missing_fields = [f for f in required_fields if f not in log]
                    if missing_fields:
                        issues["errors"].append(
                            f"Log at index {idx} in {log_file.name} missing required fields: {missing_fields}"
                        )
                        continue

                    # Timestamp validation
                    try:
                        ts = self._parse_timestamp(log["timestamp"])
                        timestamps.append((idx, ts, log["timestamp"]))

                        # Check if timestamp is within reasonable range
                        min_time = self.context.start_time - timedelta(minutes=30)
                        max_time = self.context.end_time + timedelta(minutes=30)
                        if not (min_time <= ts <= max_time):
                            issues["warnings"].append(
                                f"Log timestamp {log['timestamp']} in {log_file.name} "
                                f"outside expected range ({min_time} to {max_time})"
                            )

                    except (ValueError, KeyError) as e:
                        issues["errors"].append(
                            f"Invalid timestamp format in log at index {idx} "
                            f"in {log_file.name}: {e}"
                        )

                    # Log level validation
                    level = log["level"].upper()
                    if level not in valid_log_levels:
                        issues["errors"].append(
                            f"Invalid log level '{log['level']}' at index {idx} in {log_file.name}. "
                            f"Must be one of: {valid_log_levels}"
                        )
                    else:
                        level_counts[level] = level_counts.get(level, 0) + 1

                    # Service consistency
                    service = log["service"]
                    if service not in self._get_all_services():
                        issues["warnings"].append(
                            f"Log at index {idx} references unknown service: {service}"
                        )

                    # Message validation
                    if not log["message"] or not isinstance(log["message"], str):
                        issues["warnings"].append(
                            f"Log at index {idx} in {log_file.name} has empty or invalid message"
                        )

                # Check monotonic timestamps
                for i in range(1, len(timestamps)):
                    idx_prev, ts_prev, str_prev = timestamps[i-1]
                    idx_curr, ts_curr, str_curr = timestamps[i]
                    if ts_curr < ts_prev:
                        issues["warnings"].append(
                            f"Non-monotonic timestamps in {log_file.name}: "
                            f"index {idx_prev} ({str_prev}) > index {idx_curr} ({str_curr})"
                        )

                # Log level distribution info
                if level_counts:
                    issues["info"].append(
                        f"Log levels in {log_file.name}: {dict(sorted(level_counts.items()))}"
                    )

                # Check for error/warning presence during incident
                error_warning_count = level_counts.get("ERROR", 0) + level_counts.get("WARN", 0) + level_counts.get("WARNING", 0)
                if error_warning_count == 0:
                    issues["warnings"].append(
                        f"No ERROR or WARN logs in {log_file.name} - "
                        "incident may not have problematic log entries"
                    )

            except Exception as e:
                issues["errors"].append(f"Failed to validate log file {log_file.name}: {e}")

    def _validate_traces(self, issues: dict[str, list[str]]) -> None:
        """Validate traces data.

        Args:
            issues: Issues dictionary to append validation results
        """
        traces_dir = self.context.output_dir / "traces"
        if not traces_dir.exists():
            issues["info"].append("No traces directory found (traces are optional)")
            return

        trace_files = list(traces_dir.glob("*.jsonl"))
        if not trace_files:
            issues["info"].append("No trace files found (traces are optional)")
            return

        for trace_file in trace_files:
            try:
                traces = self._load_jsonl(trace_file)
                issues["info"].append(f"Validating {len(traces)} traces from {trace_file.name}")

                for idx, trace in enumerate(traces):
                    # Required fields validation
                    if "trace_id" not in trace:
                        issues["errors"].append(
                            f"Trace at index {idx} in {trace_file.name} missing trace_id"
                        )
                        continue

                    if "timestamp" not in trace:
                        issues["errors"].append(
                            f"Trace at index {idx} in {trace_file.name} missing timestamp"
                        )
                        continue

                    # Timestamp validation
                    try:
                        ts = self._parse_timestamp(trace["timestamp"])

                        # Check if timestamp is within reasonable range
                        min_time = self.context.start_time - timedelta(minutes=30)
                        max_time = self.context.end_time + timedelta(minutes=30)
                        if not (min_time <= ts <= max_time):
                            issues["warnings"].append(
                                f"Trace timestamp {trace['timestamp']} in {trace_file.name} "
                                f"outside expected range ({min_time} to {max_time})"
                            )

                    except (ValueError, KeyError) as e:
                        issues["errors"].append(
                            f"Invalid timestamp format in trace at index {idx} "
                            f"in {trace_file.name}: {e}"
                        )

                    # Spans validation
                    if "spans" not in trace or not isinstance(trace["spans"], list):
                        issues["errors"].append(
                            f"Trace at index {idx} in {trace_file.name} missing or invalid spans"
                        )
                        continue

                    if len(trace["spans"]) == 0:
                        issues["warnings"].append(
                            f"Trace at index {idx} in {trace_file.name} has no spans"
                        )

                    for span_idx, span in enumerate(trace["spans"]):
                        # Required span fields
                        required_span_fields = ["span_id", "service", "operation", "start_time", "duration_ms"]
                        missing_span_fields = [f for f in required_span_fields if f not in span]
                        if missing_span_fields:
                            issues["errors"].append(
                                f"Span {span_idx} in trace {idx} in {trace_file.name} "
                                f"missing required fields: {missing_span_fields}"
                            )
                            continue

                        # Duration validation
                        duration = span["duration_ms"]
                        if not isinstance(duration, (int, float)):
                            issues["errors"].append(
                                f"Span {span_idx} in trace {idx} in {trace_file.name} "
                                f"has non-numeric duration: {type(duration).__name__}"
                            )
                        elif duration < 0:
                            issues["errors"].append(
                                f"Span {span_idx} in trace {idx} in {trace_file.name} "
                                f"has negative duration: {duration}"
                            )
                        elif math.isnan(duration) or math.isinf(duration):
                            issues["errors"].append(
                                f"Span {span_idx} in trace {idx} in {trace_file.name} "
                                f"has invalid duration: {duration}"
                            )

                        # Service consistency
                        service = span["service"]
                        if service not in self._get_all_services():
                            issues["warnings"].append(
                                f"Span {span_idx} in trace {idx} references unknown service: {service}"
                            )

            except Exception as e:
                issues["errors"].append(f"Failed to validate trace file {trace_file.name}: {e}")

    def _load_jsonl(self, filepath: Path) -> list[dict[str, Any]]:
        """Load JSONL file into list of dictionaries.

        Args:
            filepath: Path to JSONL file

        Returns:
            List of parsed JSON objects
        """
        records = []
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse ISO 8601 timestamp string.

        Args:
            timestamp_str: ISO format timestamp string

        Returns:
            Parsed datetime object

        Raises:
            ValueError: If timestamp format is invalid
        """
        # Expected format: YYYY-MM-DDTHH:MM:SS.fffffZ
        try:
            # Remove the 'Z' suffix and parse
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str[:-1]

            # Parse with microseconds
            if '.' in timestamp_str:
                dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%f")
            else:
                dt = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S")

            return dt
        except ValueError as e:
            raise ValueError(f"Invalid ISO 8601 timestamp format: {timestamp_str}") from e

    def _get_all_services(self) -> set[str]:
        """Get set of all known services from topology.

        Returns:
            Set of service names
        """
        services = set()

        # Add services from topology
        for service in self.context.topology.get('services', []):
            services.add(service['name'])

        # Add affected services from context
        for service in self.context.affected_services:
            services.add(service)

        # Always allow some common infrastructure services
        services.update([
            'api-gateway',
            'postgres-primary',
            'postgres-replica',
            'redis-cache',
            'kafka-broker',
            'load-balancer'
        ])

        return services
