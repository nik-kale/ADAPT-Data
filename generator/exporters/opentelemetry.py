"""OpenTelemetry format exporter."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from generator.core.logging_config import get_logger

logger = get_logger(__name__)


class OpenTelemetryExporter:
    """Export ADAPT-Data to OpenTelemetry format.

    Converts generated telemetry to OTLP-compatible format for
    integration with OpenTelemetry collectors and backends.
    """

    def __init__(self, dataset_dir: Path) -> None:
        """Initialize exporter.

        Args:
            dataset_dir: Directory containing ADAPT-Data dataset
        """
        self.dataset_dir = dataset_dir

    def export_traces(self, output_path: Path) -> None:
        """Export traces in OTLP format.

        Args:
            output_path: Where to write OTLP traces

        Raises:
            ValueError: If traces directory not found or no traces to export
            IOError: If file operations fail
        """
        traces_dir = self.dataset_dir / "traces"
        if not traces_dir.exists():
            logger.error(f"Traces directory not found: {traces_dir}")
            raise ValueError(f"Traces directory not found: {traces_dir}")

        otlp_traces = {
            "resourceSpans": []
        }

        trace_files = list(traces_dir.glob("*.jsonl"))
        if not trace_files:
            logger.warning(f"No trace files found in {traces_dir}")
            raise ValueError(f"No trace files found in {traces_dir}")

        logger.info(f"Processing {len(trace_files)} trace files...")

        errors = 0
        for trace_file in trace_files:
            try:
                with open(trace_file) as f:
                    for line_num, line in enumerate(f, 1):
                        if not line.strip():
                            continue

                        try:
                            trace = json.loads(line)
                            resource_span = self._convert_trace_to_otlp(trace)
                            otlp_traces["resourceSpans"].append(resource_span)
                        except json.JSONDecodeError as e:
                            logger.error(f"JSON decode error in {trace_file}:{line_num}: {e}")
                            errors += 1
                        except KeyError as e:
                            logger.error(f"Missing required field in {trace_file}:{line_num}: {e}")
                            errors += 1
                        except Exception as e:
                            logger.error(f"Error processing trace in {trace_file}:{line_num}: {e}")
                            errors += 1
            except IOError as e:
                logger.error(f"Error reading {trace_file}: {e}")
                errors += 1

        if not otlp_traces["resourceSpans"]:
            logger.error("No valid traces found to export")
            raise ValueError("No valid traces found to export")

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(otlp_traces, f, indent=2)
        except IOError as e:
            logger.error(f"Error writing to {output_path}: {e}")
            raise

        logger.info(f"Exported {len(otlp_traces['resourceSpans'])} traces to {output_path}")
        if errors > 0:
            logger.warning(f"Encountered {errors} errors during export")

    def _convert_trace_to_otlp(self, trace: dict[str, Any]) -> dict[str, Any]:
        """Convert ADAPT trace to OTLP format.

        Args:
            trace: ADAPT trace object

        Returns:
            OTLP-formatted resource span
        """
        scope_spans = []

        for span in trace.get("spans", []):
            otlp_span = {
                "traceId": trace["trace_id"],
                "spanId": span["span_id"],
                "parentSpanId": span.get("parent_span_id") or "",
                "name": span.get("operation", "unknown"),
                "kind": self._get_span_kind(span),
                "startTimeUnixNano": self._iso_to_nano(span["start_time"]),
                "endTimeUnixNano": self._iso_to_nano(span["start_time"]) + int(span["duration_ms"] * 1e6),
                "status": {
                    "code": 1 if span.get("status") == "OK" else 2
                },
                "attributes": self._convert_tags_to_attributes(span.get("tags", {}))
            }

            scope_spans.append(otlp_span)

        return {
            "resource": {
                "attributes": []
            },
            "scopeSpans": [{
                "scope": {"name": "adapt-data"},
                "spans": scope_spans
            }]
        }

    def _get_span_kind(self, span: dict[str, Any]) -> int:
        """Get OTLP span kind.

        Args:
            span: ADAPT span

        Returns:
            OTLP span kind code
        """
        operation = span.get("operation", "").lower()
        if "http" in operation or "get" in operation or "post" in operation:
            return 3  # CLIENT
        return 0  # UNSPECIFIED

    def _iso_to_nano(self, iso_time: str) -> int:
        """Convert ISO timestamp to nanoseconds.

        Args:
            iso_time: ISO 8601 timestamp

        Returns:
            Unix timestamp in nanoseconds
        """
        dt = datetime.fromisoformat(iso_time.replace('Z', '+00:00'))
        return int(dt.timestamp() * 1e9)

    def _convert_tags_to_attributes(self, tags: dict[str, Any]) -> list[dict[str, Any]]:
        """Convert tags to OTLP attributes.

        Args:
            tags: Tag dictionary

        Returns:
            List of OTLP attributes
        """
        attributes = []
        for key, value in tags.items():
            if value is None:
                continue

            attr = {"key": key}

            if isinstance(value, bool):
                attr["value"] = {"boolValue": value}
            elif isinstance(value, int):
                attr["value"] = {"intValue": value}
            elif isinstance(value, float):
                attr["value"] = {"doubleValue": value}
            else:
                attr["value"] = {"stringValue": str(value)}

            attributes.append(attr)

        return attributes

    def export_metrics(self, output_path: Path) -> None:
        """Export metrics in OTLP format.

        Args:
            output_path: Where to write OTLP metrics

        Raises:
            ValueError: If metrics directory not found or no metrics to export
            IOError: If file operations fail
        """
        metrics_dir = self.dataset_dir / "metrics"
        if not metrics_dir.exists():
            logger.error(f"Metrics directory not found: {metrics_dir}")
            raise ValueError(f"Metrics directory not found: {metrics_dir}")

        otlp_metrics = {
            "resourceMetrics": []
        }

        # Group metrics by name and service
        metrics_by_name: dict[tuple[str, str], list[dict]] = {}

        metric_files = list(metrics_dir.glob("*.jsonl"))
        if not metric_files:
            logger.warning(f"No metric files found in {metrics_dir}")
            raise ValueError(f"No metric files found in {metrics_dir}")

        logger.info(f"Processing {len(metric_files)} metric files...")

        errors = 0
        for metric_file in metric_files:
            try:
                with open(metric_file) as f:
                    for line_num, line in enumerate(f, 1):
                        if not line.strip():
                            continue

                        try:
                            metric = json.loads(line)
                            key = (metric.get("metric_name", "unknown"), metric.get("service", "unknown"))

                            if key not in metrics_by_name:
                                metrics_by_name[key] = []

                            metrics_by_name[key].append(metric)
                        except json.JSONDecodeError as e:
                            logger.error(f"JSON decode error in {metric_file}:{line_num}: {e}")
                            errors += 1
                        except Exception as e:
                            logger.error(f"Error processing metric in {metric_file}:{line_num}: {e}")
                            errors += 1
            except IOError as e:
                logger.error(f"Error reading {metric_file}: {e}")
                errors += 1

        if not metrics_by_name:
            logger.error("No valid metrics found to export")
            raise ValueError("No valid metrics found to export")

        # Convert to OTLP
        logger.info(f"Converting {len(metrics_by_name)} metric series to OTLP...")
        for (metric_name, service), points in metrics_by_name.items():
            try:
                resource_metric = self._convert_metrics_to_otlp(metric_name, service, points)
                otlp_metrics["resourceMetrics"].append(resource_metric)
            except Exception as e:
                logger.error(f"Error converting metric {metric_name} for {service}: {e}")
                errors += 1

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(otlp_metrics, f, indent=2)
        except IOError as e:
            logger.error(f"Error writing to {output_path}: {e}")
            raise

        logger.info(f"Exported {len(otlp_metrics['resourceMetrics'])} metric series to {output_path}")
        if errors > 0:
            logger.warning(f"Encountered {errors} errors during export")

    def _convert_metrics_to_otlp(
        self,
        metric_name: str,
        service: str,
        points: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Convert ADAPT metrics to OTLP format."""
        data_points = []

        for point in points:
            data_point = {
                "timeUnixNano": self._iso_to_nano(point["timestamp"]),
                "asDouble": float(point["value"]),
                "attributes": []
            }
            data_points.append(data_point)

        metric_type = points[0].get("metric_type", "gauge")

        metric_data = {
            "name": metric_name,
            "unit": points[0].get("unit", ""),
        }

        if metric_type == "gauge":
            metric_data["gauge"] = {"dataPoints": data_points}
        else:
            metric_data["sum"] = {
                "dataPoints": data_points,
                "aggregationTemporality": 2,  # CUMULATIVE
                "isMonotonic": metric_type == "counter"
            }

        return {
            "resource": {
                "attributes": [
                    {"key": "service.name", "value": {"stringValue": service}}
                ]
            },
            "scopeMetrics": [{
                "scope": {"name": "adapt-data"},
                "metrics": [metric_data]
            }]
        }
