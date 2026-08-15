"""Datadog format exporter.

Converts generated telemetry into the payload shapes Datadog's intake APIs
accept, so datasets can be replayed into a Datadog account or fed to tooling
that already speaks that format.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from generator.core.logging_config import get_logger

logger = get_logger(__name__)

# Datadog metric type codes used by the v2 series intake.
_DD_TYPE_UNSPECIFIED = 0
_DD_TYPE_COUNT = 1
_DD_TYPE_GAUGE = 3

_METRIC_TYPE_MAP = {
    "counter": _DD_TYPE_COUNT,
    "gauge": _DD_TYPE_GAUGE,
    "histogram": _DD_TYPE_GAUGE,
    "summary": _DD_TYPE_GAUGE,
}

# Tags whose values are unbounded. Datadog bills and limits metrics by series
# cardinality, and a per-event ID would make every point its own series, so
# these are dropped from metric tags. They are preserved on logs and traces,
# where high cardinality is expected and joins actually happen.
_HIGH_CARDINALITY_TAGS = frozenset({"correlation_id", "request_id", "trace_id", "span_id"})

# Datadog log status values; ADAPT levels map onto these.
_LEVEL_STATUS_MAP = {
    "DEBUG": "debug",
    "INFO": "info",
    "WARN": "warn",
    "WARNING": "warn",
    "ERROR": "error",
    "FATAL": "critical",
    "CRITICAL": "critical",
}


class DatadogExporter:
    """Export ADAPT-Data datasets to Datadog-compatible JSON payloads.

    Produces three artifacts, matching Datadog's separate intakes:

    - **Metrics** — ``{"series": [...]}`` for the metrics API
    - **Logs** — a JSON array for the logs intake
    - **Traces** — nested span arrays for the APM trace intake
    """

    def __init__(self, dataset_dir: Path, service_prefix: str = "") -> None:
        """Initialize exporter.

        Args:
            dataset_dir: Directory containing an ADAPT-Data dataset
            service_prefix: Optional prefix applied to every service name, to
                keep synthetic data separable from real telemetry
        """
        self.dataset_dir = Path(dataset_dir)
        self.service_prefix = service_prefix

    def _service_name(self, service: str) -> str:
        """Apply the configured prefix to a service name.

        Args:
            service: Raw service name

        Returns:
            Prefixed service name
        """
        return f"{self.service_prefix}{service}" if self.service_prefix else service

    def _iter_records(self, subdir: str) -> Iterator[tuple[Path, int, dict[str, Any]]]:
        """Iterate records across every JSONL file in a dataset subdirectory.

        Args:
            subdir: Dataset subdirectory ('metrics', 'logs' or 'traces')

        Yields:
            Tuples of (file path, 1-based line number, parsed record)

        Raises:
            ValueError: If the subdirectory is missing or holds no JSONL files
        """
        source_dir = self.dataset_dir / subdir
        if not source_dir.exists():
            raise ValueError(f"{subdir.capitalize()} directory not found: {source_dir}")

        files = sorted(source_dir.glob("*.jsonl"))
        if not files:
            raise ValueError(f"No {subdir} files found in {source_dir}")

        logger.info(f"Processing {len(files)} {subdir} files...")

        for path in files:
            try:
                with open(path) as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            yield path, line_num, json.loads(line)
                        except json.JSONDecodeError as e:
                            logger.error(f"JSON decode error in {path}:{line_num}: {e}")
            except IOError as e:
                logger.error(f"Error reading {path}: {e}")

    @staticmethod
    def _to_unix_seconds(iso_time: str) -> int:
        """Convert an ISO 8601 timestamp to whole Unix seconds.

        Args:
            iso_time: ISO 8601 timestamp

        Returns:
            Unix timestamp in seconds
        """
        dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
        return int(dt.timestamp())

    @staticmethod
    def _to_unix_nanos(iso_time: str) -> int:
        """Convert an ISO 8601 timestamp to Unix nanoseconds.

        Args:
            iso_time: ISO 8601 timestamp

        Returns:
            Unix timestamp in nanoseconds
        """
        dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
        return int(dt.timestamp() * 1e9)

    @staticmethod
    def _format_tags(record: dict[str, Any], drop_high_cardinality: bool = False) -> list[str]:
        """Render a record's tags in Datadog's ``key:value`` form.

        Args:
            record: Record carrying optional 'tags', 'host' and 'region' fields
            drop_high_cardinality: Omit per-event IDs. Set for metrics, where
                unbounded tag values would explode series cardinality.

        Returns:
            Sorted list of tag strings
        """
        tags: list[str] = []

        raw_tags = record.get("tags")
        if isinstance(raw_tags, dict):
            tags.extend(
                f"{key}:{value}"
                for key, value in raw_tags.items()
                if not (drop_high_cardinality and key in _HIGH_CARDINALITY_TAGS)
            )

        for field in ("host", "region"):
            if value := record.get(field):
                tags.append(f"{field}:{value}")

        if record.get("anomaly_injected"):
            tags.append("anomaly_injected:true")

        return sorted(tags)

    def _write_json(self, payload: Any, output_path: Path, description: str) -> None:
        """Write a payload to disk as formatted JSON.

        Args:
            payload: Serializable payload
            output_path: Destination file
            description: What is being written, for the log line

        Raises:
            IOError: If the file cannot be written
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                json.dump(payload, f, indent=2, default=str)
        except IOError as e:
            logger.error(f"Error writing to {output_path}: {e}")
            raise

        logger.info(f"Exported {description} to {output_path}")

    def export_metrics(self, output_path: Path) -> None:
        """Export metrics as a Datadog series payload.

        Samples sharing a metric name, service and tag set are folded into one
        series with multiple points, which is how the intake expects them.

        Args:
            output_path: Where to write the payload

        Raises:
            ValueError: If no metrics are available to export
        """
        series: dict[tuple[str, str, str], dict[str, Any]] = {}

        for _, _, metric in self._iter_records("metrics"):
            name = metric.get("metric_name")
            timestamp = metric.get("timestamp")
            if not name or timestamp is None or "value" not in metric:
                continue

            service = self._service_name(metric.get("service", "unknown"))
            tags = self._format_tags(metric, drop_high_cardinality=True)
            tags.append(f"service:{service}")

            key = (name, service, ",".join(sorted(tags)))

            if key not in series:
                series[key] = {
                    "metric": name,
                    "type": _METRIC_TYPE_MAP.get(
                        metric.get("metric_type", "gauge"), _DD_TYPE_UNSPECIFIED
                    ),
                    "points": [],
                    "tags": sorted(tags),
                    "resources": [{"name": service, "type": "service"}],
                }

            if unit := metric.get("unit"):
                series[key]["unit"] = unit

            try:
                series[key]["points"].append(
                    {
                        "timestamp": self._to_unix_seconds(timestamp),
                        "value": float(metric["value"]),
                    }
                )
            except (ValueError, TypeError) as e:
                logger.error(f"Skipping metric point for {name}: {e}")

        if not series:
            raise ValueError("No valid metrics found to export")

        payload = {"series": list(series.values())}
        point_count = sum(len(s["points"]) for s in series.values())
        self._write_json(
            payload, output_path, f"{len(series)} metric series ({point_count} points)"
        )

    def export_logs(self, output_path: Path) -> None:
        """Export logs as a Datadog logs intake payload.

        Args:
            output_path: Where to write the payload

        Raises:
            ValueError: If no logs are available to export
        """
        entries: list[dict[str, Any]] = []

        for _, _, log in self._iter_records("logs"):
            message = log.get("message")
            if not message:
                continue

            service = self._service_name(log.get("service", "unknown"))
            level = str(log.get("level", "INFO")).upper()

            entry: dict[str, Any] = {
                "ddsource": "adapt-data",
                "ddtags": ",".join(self._format_tags(log)),
                "hostname": log.get("host", "unknown"),
                "message": message,
                "service": service,
                "status": _LEVEL_STATUS_MAP.get(level, "info"),
            }

            if timestamp := log.get("timestamp"):
                # Datadog expects milliseconds for the reserved timestamp attribute.
                entry["timestamp"] = self._to_unix_nanos(timestamp) // 1_000_000

            # dd.trace_id / dd.span_id must be the same 64-bit IDs the APM
            # export emits, or Datadog cannot join logs to traces.
            for field in ("trace_id", "span_id"):
                if value := log.get(field):
                    entry[f"dd.{field}"] = str(self._to_dd_id(value))
                    entry[f"adapt.{field}"] = value

            if correlation_id := log.get("correlation_id"):
                entry["correlation_id"] = correlation_id

            if isinstance(log.get("metadata"), dict):
                entry["attributes"] = log["metadata"]

            entries.append(entry)

        if not entries:
            raise ValueError("No valid logs found to export")

        self._write_json(entries, output_path, f"{len(entries)} log entries")

    def export_traces(self, output_path: Path) -> None:
        """Export traces as a Datadog APM trace payload.

        Datadog identifies traces and spans with 64-bit unsigned integers, so
        the UUID-based IDs in the dataset are hashed down to that range. The
        original UUID is preserved as a span tag.

        Args:
            output_path: Where to write the payload

        Raises:
            ValueError: If no traces are available to export
        """
        payload: list[list[dict[str, Any]]] = []

        for _, _, trace in self._iter_records("traces"):
            spans = trace.get("spans")
            trace_id = trace.get("trace_id")
            if not trace_id or not isinstance(spans, list) or not spans:
                continue

            dd_trace_id = self._to_dd_id(trace_id)
            dd_spans: list[dict[str, Any]] = []

            for span in spans:
                if not isinstance(span, dict):
                    continue

                required = ("span_id", "service", "operation", "start_time", "duration_ms")
                if any(field not in span for field in required):
                    logger.error(f"Skipping span missing required fields in trace {trace_id}")
                    continue

                service = self._service_name(span["service"])
                parent_id = span.get("parent_span_id")

                meta = {str(key): str(value) for key, value in (span.get("tags") or {}).items()}
                meta["adapt.trace_id"] = trace_id
                meta["adapt.span_id"] = str(span["span_id"])
                if correlation_id := trace.get("correlation_id"):
                    meta["correlation_id"] = correlation_id

                try:
                    dd_span = {
                        "trace_id": dd_trace_id,
                        "span_id": self._to_dd_id(span["span_id"]),
                        "parent_id": self._to_dd_id(parent_id) if parent_id else 0,
                        "name": span["operation"],
                        "resource": span["operation"],
                        "service": service,
                        "type": "web",
                        "start": self._to_unix_nanos(span["start_time"]),
                        "duration": int(float(span["duration_ms"]) * 1e6),
                        "error": 1 if span.get("status") in ("ERROR", "TIMEOUT") else 0,
                        "meta": meta,
                    }
                except (ValueError, TypeError) as e:
                    logger.error(f"Skipping malformed span in trace {trace_id}: {e}")
                    continue

                dd_spans.append(dd_span)

            if dd_spans:
                payload.append(dd_spans)

        if not payload:
            raise ValueError("No valid traces found to export")

        span_count = sum(len(spans) for spans in payload)
        self._write_json(payload, output_path, f"{len(payload)} traces ({span_count} spans)")

    @staticmethod
    def _to_dd_id(identifier: str) -> int:
        """Hash an ADAPT identifier into Datadog's 64-bit ID space.

        Args:
            identifier: Source identifier, typically a UUID

        Returns:
            Stable unsigned 64-bit integer for the same input
        """
        # Deterministic across processes, unlike hash(), which is salted.
        digest = 0
        for char in str(identifier):
            digest = (digest * 31 + ord(char)) & 0xFFFFFFFFFFFFFFFF
        return digest

    def export_all(self, output_dir: Path) -> dict[str, Path]:
        """Export metrics, logs and traces into one directory.

        Each artifact is attempted independently, so a dataset missing traces
        still yields metrics and logs.

        Args:
            output_dir: Directory to write the three payloads into

        Returns:
            Mapping of artifact name to the file written

        Raises:
            ValueError: If nothing could be exported at all
        """
        output_dir = Path(output_dir)
        written: dict[str, Path] = {}

        exports = (
            ("metrics", self.export_metrics, "datadog_metrics.json"),
            ("logs", self.export_logs, "datadog_logs.json"),
            ("traces", self.export_traces, "datadog_traces.json"),
        )

        for name, export_fn, filename in exports:
            target = output_dir / filename
            try:
                export_fn(target)
                written[name] = target
            except ValueError as e:
                logger.warning(f"Skipping {name} export: {e}")

        if not written:
            raise ValueError(f"No exportable data found in {self.dataset_dir}")

        return written
