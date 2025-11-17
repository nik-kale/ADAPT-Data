"""Zipkin format exporter."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from generator.core.logging_config import get_logger

logger = get_logger(__name__)


class ZipkinExporter:
    """Export ADAPT-Data traces to Zipkin format.

    Converts generated traces to Zipkin JSON format for integration
    with Zipkin UI and backends.

    Reference: https://zipkin.io/zipkin-api/
    """

    def __init__(self, dataset_dir: Path) -> None:
        """Initialize exporter.

        Args:
            dataset_dir: Directory containing ADAPT-Data dataset
        """
        self.dataset_dir = dataset_dir

    def export_traces(self, output_path: Path) -> None:
        """Export traces in Zipkin JSON format.

        Args:
            output_path: Where to write Zipkin traces

        Raises:
            ValueError: If traces directory not found or no traces to export
            IOError: If file operations fail
        """
        traces_dir = self.dataset_dir / "traces"
        if not traces_dir.exists():
            logger.error(f"Traces directory not found: {traces_dir}")
            raise ValueError(f"Traces directory not found: {traces_dir}")

        zipkin_spans = []

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
                            spans = self._convert_trace_to_zipkin(trace)
                            zipkin_spans.extend(spans)
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

        if not zipkin_spans:
            logger.error("No valid traces found to export")
            raise ValueError("No valid traces found to export")

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(zipkin_spans, f, indent=2)
        except IOError as e:
            logger.error(f"Error writing to {output_path}: {e}")
            raise

        logger.info(f"Exported {len(zipkin_spans)} spans to {output_path}")
        if errors > 0:
            logger.warning(f"Encountered {errors} errors during export")

    def _convert_trace_to_zipkin(self, trace: dict[str, Any]) -> list[dict[str, Any]]:
        """Convert ADAPT trace to Zipkin spans.

        Args:
            trace: ADAPT trace object

        Returns:
            List of Zipkin-formatted spans
        """
        zipkin_spans = []

        for span in trace.get("spans", []):
            zipkin_span = self._convert_span_to_zipkin(trace["trace_id"], span)
            zipkin_spans.append(zipkin_span)

        return zipkin_spans

    def _convert_span_to_zipkin(
        self,
        trace_id: str,
        span: dict[str, Any]
    ) -> dict[str, Any]:
        """Convert ADAPT span to Zipkin span.

        Args:
            trace_id: Trace ID
            span: ADAPT span object

        Returns:
            Zipkin-formatted span
        """
        # Parse timestamp
        start_time = datetime.fromisoformat(span["start_time"].replace('Z', '+00:00'))
        timestamp_us = int(start_time.timestamp() * 1e6)
        duration_us = int(span["duration_ms"] * 1000)

        # Build Zipkin span
        zipkin_span = {
            "traceId": self._format_trace_id(trace_id),
            "id": self._format_span_id(span["span_id"]),
            "name": span.get("operation", "unknown"),
            "timestamp": timestamp_us,
            "duration": duration_us,
            "kind": self._get_span_kind(span),
            "localEndpoint": {
                "serviceName": span.get("service", "unknown"),
                "ipv4": span.get("host", "127.0.0.1")
            },
            "tags": {}
        }

        # Add parent span ID if present
        if span.get("parent_span_id"):
            zipkin_span["parentId"] = self._format_span_id(span["parent_span_id"])

        # Add tags
        for key, value in span.get("tags", {}).items():
            zipkin_span["tags"][key] = str(value)

        # Add status
        status = span.get("status", "OK")
        if status != "OK":
            zipkin_span["tags"]["error"] = "true"
            zipkin_span["tags"]["otel.status_code"] = status

        return zipkin_span

    def _get_span_kind(self, span: dict[str, Any]) -> str:
        """Get Zipkin span kind.

        Args:
            span: ADAPT span object

        Returns:
            Zipkin span kind (CLIENT, SERVER, PRODUCER, CONSUMER, or None)
        """
        operation = span.get("operation", "").lower()

        if "http" in operation or "get" in operation or "post" in operation:
            return "CLIENT"
        elif "receive" in operation or "consume" in operation:
            return "CONSUMER"
        elif "send" in operation or "publish" in operation:
            return "PRODUCER"
        elif "handle" in operation or "serve" in operation:
            return "SERVER"

        return "CLIENT"  # Default

    def _format_trace_id(self, trace_id: str) -> str:
        """Format trace ID for Zipkin (32 hex chars).

        Args:
            trace_id: ADAPT trace ID

        Returns:
            Formatted trace ID
        """
        # Remove dashes and ensure 32 chars
        formatted = trace_id.replace("-", "")[:32]
        # Pad if needed
        return formatted.ljust(32, "0")

    def _format_span_id(self, span_id: str) -> str:
        """Format span ID for Zipkin (16 hex chars).

        Args:
            span_id: ADAPT span ID

        Returns:
            Formatted span ID
        """
        # Remove dashes and ensure 16 chars
        formatted = span_id.replace("-", "")[:16]
        # Pad if needed
        return formatted.ljust(16, "0")
