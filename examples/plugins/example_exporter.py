"""Example Custom Exporter Plugin for ADAPT-Data.

This plugin demonstrates how to create a custom exporter
that exports telemetry data to CSV format.

To use this plugin:
1. Copy this file to ~/.adapt-data/plugins/
2. The plugin will be auto-discovered on startup
3. Use with: adapt-data export dataset_dir --format csv --output metrics.csv
"""

import csv
import json
from pathlib import Path
from typing import Any

from generator.core.logging_config import get_logger
from generator.core.plugins import ExporterPlugin

logger = get_logger(__name__)


class CSVExporter:
    """Exports ADAPT-Data telemetry to CSV format.

    Exports metrics, logs, and traces to separate CSV files
    for easy analysis in spreadsheet applications.
    """

    def __init__(self, dataset_dir: Path) -> None:
        """Initialize CSV exporter.

        Args:
            dataset_dir: Directory containing generated dataset
        """
        self.dataset_dir = dataset_dir
        logger.info(f"Initialized CSV exporter for {dataset_dir}")

    def export(self, output_path: Path) -> None:
        """Export dataset to CSV format.

        Args:
            output_path: Base path for CSV files (will create multiple files)
        """
        output_dir = output_path.parent if output_path.is_file() else output_path
        output_dir.mkdir(parents=True, exist_ok=True)

        base_name = output_path.stem if output_path.is_file() else "export"

        # Export each data type
        self._export_metrics(output_dir / f"{base_name}_metrics.csv")
        self._export_logs(output_dir / f"{base_name}_logs.csv")
        self._export_traces(output_dir / f"{base_name}_traces.csv")

        logger.info(f"CSV export complete: {output_dir}")

    def _export_metrics(self, output_path: Path) -> None:
        """Export metrics to CSV."""
        metric_files = list(self.dataset_dir.glob("metrics/*.jsonl"))

        if not metric_files:
            logger.warning("No metric files found")
            return

        metrics = []
        for metric_file in metric_files:
            with open(metric_file) as f:
                for line in f:
                    metrics.append(json.loads(line))

        if not metrics:
            return

        # Define CSV columns
        columns = [
            "timestamp",
            "metric_name",
            "value",
            "service",
            "host",
            "metric_type",
            "unit",
            "tags",
            "anomaly_injected"
        ]

        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
            writer.writeheader()

            for metric in metrics:
                # Flatten tags dict to string
                if 'tags' in metric and isinstance(metric['tags'], dict):
                    metric['tags'] = json.dumps(metric['tags'])
                writer.writerow(metric)

        logger.info(f"Exported {len(metrics)} metrics to {output_path}")

    def _export_logs(self, output_path: Path) -> None:
        """Export logs to CSV."""
        log_files = list(self.dataset_dir.glob("logs/*.jsonl"))

        if not log_files:
            logger.warning("No log files found")
            return

        logs = []
        for log_file in log_files:
            with open(log_file) as f:
                for line in f:
                    logs.append(json.loads(line))

        if not logs:
            return

        columns = [
            "timestamp",
            "level",
            "service",
            "host",
            "message",
            "metadata"
        ]

        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
            writer.writeheader()

            for log in logs:
                # Flatten metadata to string
                if 'metadata' in log and isinstance(log['metadata'], dict):
                    log['metadata'] = json.dumps(log['metadata'])
                writer.writerow(log)

        logger.info(f"Exported {len(logs)} logs to {output_path}")

    def _export_traces(self, output_path: Path) -> None:
        """Export traces to CSV (flattened spans)."""
        trace_files = list(self.dataset_dir.glob("traces/*.jsonl"))

        if not trace_files:
            logger.warning("No trace files found")
            return

        spans = []
        for trace_file in trace_files:
            with open(trace_file) as f:
                for line in f:
                    trace = json.loads(line)
                    # Flatten trace spans into individual rows
                    for span in trace.get('spans', []):
                        span['trace_id'] = trace['trace_id']
                        span['trace_timestamp'] = trace['timestamp']
                        spans.append(span)

        if not spans:
            return

        columns = [
            "trace_id",
            "trace_timestamp",
            "span_id",
            "parent_span_id",
            "service",
            "operation",
            "start_time",
            "duration_ms",
            "status",
            "tags"
        ]

        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
            writer.writeheader()

            for span in spans:
                # Flatten tags to string
                if 'tags' in span and isinstance(span['tags'], dict):
                    span['tags'] = json.dumps(span['tags'])
                writer.writerow(span)

        logger.info(f"Exported {len(spans)} spans to {output_path}")


# Plugin registration
class CSVExporterPlugin(ExporterPlugin):
    """Plugin wrapper for CSVExporter."""

    name = "csv"
    version = "1.0.0"
    description = "Exports telemetry data to CSV format for spreadsheet analysis"
    exporter_class = CSVExporter


# Export plugin instance
plugin = CSVExporterPlugin()
