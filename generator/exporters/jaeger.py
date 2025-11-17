"""Jaeger format exporter."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from generator.core.logging_config import get_logger

logger = get_logger(__name__)


class JaegerExporter:
    """Export ADAPT-Data traces to Jaeger format.

    Converts generated traces to Jaeger JSON format for integration
    with Jaeger UI and backends.

    Reference: https://www.jaegertracing.io/docs/1.35/apis/#json-over-http
    """

    def __init__(self, dataset_dir: Path) -> None:
        """Initialize exporter.

        Args:
            dataset_dir: Directory containing ADAPT-Data dataset
        """
        self.dataset_dir = dataset_dir

    def export_traces(self, output_path: Path) -> None:
        """Export traces in Jaeger JSON format.

        Args:
            output_path: Where to write Jaeger traces

        Raises:
            ValueError: If traces directory not found or no traces to export
            IOError: If file operations fail
        """
        traces_dir = self.dataset_dir / "traces"
        if not traces_dir.exists():
            logger.error(f"Traces directory not found: {traces_dir}")
            raise ValueError(f"Traces directory not found: {traces_dir}")

        jaeger_batches = []

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
                            batch = self._convert_trace_to_jaeger(trace)
                            jaeger_batches.append(batch)
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

        if not jaeger_batches:
            logger.error("No valid traces found to export")
            raise ValueError("No valid traces found to export")

        # Write Jaeger format
        jaeger_output = {
            "data": jaeger_batches
        }

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                json.dump(jaeger_output, f, indent=2)
        except IOError as e:
            logger.error(f"Error writing to {output_path}: {e}")
            raise

        logger.info(f"Exported {len(jaeger_batches)} trace batches to {output_path}")
        if errors > 0:
            logger.warning(f"Encountered {errors} errors during export")

    def _convert_trace_to_jaeger(self, trace: dict[str, Any]) -> dict[str, Any]:
        """Convert ADAPT trace to Jaeger format.

        Args:
            trace: ADAPT trace object

        Returns:
            Jaeger-formatted batch
        """
        # Extract service name from first span
        service_name = "unknown"
        if trace.get("spans") and len(trace["spans"]) > 0:
            service_name = trace["spans"][0].get("service", "unknown")

        # Convert spans
        jaeger_spans = []
        for span in trace.get("spans", []):
            jaeger_span = self._convert_span_to_jaeger(trace["trace_id"], span)
            jaeger_spans.append(jaeger_span)

        return {
            "traceID": self._format_trace_id(trace["trace_id"]),
            "spans": jaeger_spans,
            "processes": {
                "p1": {
                    "serviceName": service_name,
                    "tags": []
                }
            }
        }

    def _convert_span_to_jaeger(
        self,
        trace_id: str,
        span: dict[str, Any]
    ) -> dict[str, Any]:
        """Convert ADAPT span to Jaeger span.

        Args:
            trace_id: Trace ID
            span: ADAPT span object

        Returns:
            Jaeger-formatted span
        """
        # Parse timestamp
        start_time = datetime.fromisoformat(span["start_time"].replace('Z', '+00:00'))
        start_time_us = int(start_time.timestamp() * 1e6)
        duration_us = int(span["duration_ms"] * 1000)

        # Convert tags to Jaeger format
        tags = []
        for key, value in span.get("tags", {}).items():
            tag_type = "string"
            if isinstance(value, bool):
                tag_type = "bool"
            elif isinstance(value, int):
                tag_type = "int64"
            elif isinstance(value, float):
                tag_type = "float64"

            tags.append({
                "key": key,
                "type": tag_type,
                "value": value
            })

        # Add standard tags
        tags.append({
            "key": "span.kind",
            "type": "string",
            "value": span.get("kind", "internal")
        })

        return {
            "traceID": self._format_trace_id(trace_id),
            "spanID": self._format_span_id(span["span_id"]),
            "operationName": span.get("operation", "unknown"),
            "references": self._get_references(span),
            "startTime": start_time_us,
            "duration": duration_us,
            "tags": tags,
            "logs": [],
            "processID": "p1",
            "warnings": None
        }

    def _get_references(self, span: dict[str, Any]) -> list[dict[str, Any]]:
        """Get span references (parent relationship).

        Args:
            span: ADAPT span object

        Returns:
            List of Jaeger references
        """
        refs = []
        parent_span_id = span.get("parent_span_id")

        if parent_span_id:
            refs.append({
                "refType": "CHILD_OF",
                "traceID": self._format_span_id(parent_span_id),
                "spanID": self._format_span_id(parent_span_id)
            })

        return refs

    def _format_trace_id(self, trace_id: str) -> str:
        """Format trace ID for Jaeger (32 hex chars).

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
        """Format span ID for Jaeger (16 hex chars).

        Args:
            span_id: ADAPT span ID

        Returns:
            Formatted span ID
        """
        # Remove dashes and ensure 16 chars
        formatted = span_id.replace("-", "")[:16]
        # Pad if needed
        return formatted.ljust(16, "0")
