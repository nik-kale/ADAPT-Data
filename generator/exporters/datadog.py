"""Datadog format exporter for metrics, logs, and traces."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from generator.core.logging_config import get_logger

logger = get_logger(__name__)


class DatadogExporter:
    """Export ADAPT-Data to Datadog format.

    Supports exporting metrics, logs, and traces in Datadog API format.
    Can write to JSON files for manual import or optionally submit directly
    to Datadog API.
    """

    def __init__(self, dataset_dir: Path, api_key: Optional[str] = None) -> None:
        """Initialize exporter.

        Args:
            dataset_dir: Directory containing ADAPT-Data dataset
            api_key: Optional Datadog API key for direct submission
        """
        self.dataset_dir = dataset_dir
        self.api_key = api_key

        if api_key:
            logger.info("Datadog API key provided - direct submission enabled")

    def export_metrics(self, output_path: Path) -> None:
        """Export metrics in Datadog series format.

        Converts ADAPT-Data metrics to Datadog's JSON series format:
        {
          "series": [
            {
              "metric": "metric_name",
              "points": [[timestamp, value]],
              "type": "gauge" or "count",
              "tags": ["tag1:value1", "tag2:value2"]
            }
          ]
        }

        Args:
            output_path: Path to output JSON file

        Raises:
            FileNotFoundError: If metrics directory doesn't exist
            ValueError: If no metrics found
        """
        logger.info("Exporting metrics to Datadog format...")

        metrics_dir = self.dataset_dir / "metrics"
        if not metrics_dir.exists():
            raise FileNotFoundError(f"Metrics directory not found: {metrics_dir}")

        metric_files = list(metrics_dir.glob("*.jsonl"))
        if not metric_files:
            raise ValueError(f"No metric files found in {metrics_dir}")

        # Group metrics by name
        metrics_by_name: dict[str, list[tuple[int, float, list[str]]]] = {}

        for metric_file in metric_files:
            logger.debug(f"Reading metrics from {metric_file.name}...")
            with open(metric_file) as f:
                for line in f:
                    if not line.strip():
                        continue

                    metric = json.loads(line)
                    metric_name = metric.get('metric_name')
                    value = metric.get('value')
                    timestamp = metric.get('timestamp')

                    if not all([metric_name, value is not None, timestamp]):
                        logger.warning(f"Skipping incomplete metric: {metric}")
                        continue

                    # Convert ISO timestamp to Unix epoch
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    unix_timestamp = int(dt.timestamp())

                    # Build tags from metric metadata
                    tags = []
                    if 'service' in metric:
                        tags.append(f"service:{metric['service']}")
                    if 'host' in metric:
                        tags.append(f"host:{metric['host']}")
                    if 'metric_type' in metric:
                        tags.append(f"type:{metric['metric_type']}")
                    if 'anomaly_injected' in metric and metric['anomaly_injected']:
                        tags.append("anomaly:true")

                    # Group by metric name
                    if metric_name not in metrics_by_name:
                        metrics_by_name[metric_name] = []

                    metrics_by_name[metric_name].append((unix_timestamp, float(value), tags))

        # Convert to Datadog series format
        series = []
        for metric_name, points_data in metrics_by_name.items():
            # Sort by timestamp
            points_data.sort(key=lambda x: x[0])

            # Aggregate tags (use tags from first point)
            tags = points_data[0][2] if points_data else []

            # Format points as [timestamp, value]
            points = [[ts, val] for ts, val, _ in points_data]

            # Determine metric type (default to gauge)
            metric_type = "gauge"
            for tag in tags:
                if tag.startswith("type:"):
                    type_val = tag.split(":", 1)[1]
                    if type_val in ["counter", "count"]:
                        metric_type = "count"

            series.append({
                "metric": metric_name,
                "points": points,
                "type": metric_type,
                "tags": tags
            })

        datadog_payload = {
            "series": series
        }

        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(datadog_payload, f, indent=2)

        logger.info(f"✓ Exported {len(series)} metric series to {output_path}")
        logger.info(f"  Total data points: {sum(len(s['points']) for s in series)}")

    def export_logs(self, output_path: Path) -> None:
        """Export logs in Datadog logs format.

        Converts ADAPT-Data logs to Datadog's JSON logs format.

        Args:
            output_path: Path to output JSON file

        Raises:
            FileNotFoundError: If logs directory doesn't exist
            ValueError: If no logs found
        """
        logger.info("Exporting logs to Datadog format...")

        logs_dir = self.dataset_dir / "logs"
        if not logs_dir.exists():
            raise FileNotFoundError(f"Logs directory not found: {logs_dir}")

        log_files = list(logs_dir.glob("*.jsonl"))
        if not log_files:
            raise ValueError(f"No log files found in {logs_dir}")

        datadog_logs = []

        for log_file in log_files:
            logger.debug(f"Reading logs from {log_file.name}...")
            with open(log_file) as f:
                for line in f:
                    if not line.strip():
                        continue

                    log = json.loads(line)

                    # Convert to Datadog log format
                    timestamp = log.get('timestamp')
                    if not timestamp:
                        logger.warning(f"Skipping log without timestamp: {log}")
                        continue

                    # Convert ISO timestamp to milliseconds since epoch
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    timestamp_ms = int(dt.timestamp() * 1000)

                    # Map log level to Datadog severity
                    level = log.get('level', 'INFO').upper()
                    status_map = {
                        'DEBUG': 'debug',
                        'INFO': 'info',
                        'WARN': 'warn',
                        'WARNING': 'warn',
                        'ERROR': 'error',
                        'FATAL': 'critical',
                        'CRITICAL': 'critical'
                    }
                    status = status_map.get(level, 'info')

                    # Build Datadog log entry
                    dd_log = {
                        "timestamp": timestamp_ms,
                        "status": status,
                        "message": log.get('message', ''),
                        "service": log.get('service', 'unknown'),
                        "ddsource": "adapt-data",
                        "ddtags": f"env:synthetic,source:adapt-data"
                    }

                    # Add host if available
                    if 'host' in log:
                        dd_log["host"] = log['host']

                    # Add additional attributes
                    attributes = {}
                    for key, value in log.items():
                        if key not in ['timestamp', 'level', 'message', 'service', 'host']:
                            attributes[key] = value

                    if attributes:
                        dd_log["attributes"] = attributes

                    datadog_logs.append(dd_log)

        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(datadog_logs, f, indent=2)

        logger.info(f"✓ Exported {len(datadog_logs)} log entries to {output_path}")

    def export_traces(self, output_path: Path) -> None:
        """Export traces in Datadog APM format.

        Converts ADAPT-Data traces to Datadog's trace format.

        Args:
            output_path: Path to output JSON file

        Raises:
            FileNotFoundError: If traces directory doesn't exist
            ValueError: If no traces found
        """
        logger.info("Exporting traces to Datadog format...")

        traces_dir = self.dataset_dir / "traces"
        if not traces_dir.exists():
            raise FileNotFoundError(f"Traces directory not found: {traces_dir}")

        trace_files = list(traces_dir.glob("*.jsonl"))
        if not trace_files:
            raise ValueError(f"No trace files found in {traces_dir}")

        datadog_traces = []

        for trace_file in trace_files:
            logger.debug(f"Reading traces from {trace_file.name}...")
            with open(trace_file) as f:
                for line in f:
                    if not line.strip():
                        continue

                    trace = json.loads(line)

                    trace_id = trace.get('trace_id')
                    spans = trace.get('spans', [])

                    if not trace_id or not spans:
                        logger.warning(f"Skipping invalid trace: {trace}")
                        continue

                    # Convert each span to Datadog format
                    dd_spans = []
                    for span in spans:
                        span_id = span.get('span_id')
                        service = span.get('service', 'unknown')
                        operation = span.get('operation', 'unknown')
                        start_time = span.get('start_time')
                        duration_ms = span.get('duration_ms', 0)

                        if not all([span_id, start_time]):
                            logger.warning(f"Skipping incomplete span: {span}")
                            continue

                        # Convert timestamps
                        dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        start_ns = int(dt.timestamp() * 1_000_000_000)
                        duration_ns = int(duration_ms * 1_000_000)

                        # Build Datadog span
                        dd_span = {
                            "trace_id": int(trace_id.replace('-', ''), 16) % (2**64),  # Convert UUID to int
                            "span_id": int(span_id.replace('-', ''), 16) % (2**64),
                            "name": operation,
                            "resource": span.get('resource', operation),
                            "service": service,
                            "type": "web",
                            "start": start_ns,
                            "duration": duration_ns,
                            "meta": {
                                "source": "adapt-data",
                                "env": "synthetic"
                            }
                        }

                        # Add parent span if present
                        if 'parent_span_id' in span:
                            dd_span["parent_id"] = int(span['parent_span_id'].replace('-', ''), 16) % (2**64)

                        # Add error flag if present
                        if span.get('error'):
                            dd_span["error"] = 1
                            dd_span["meta"]["error.message"] = str(span.get('error'))

                        # Add tags
                        if 'tags' in span:
                            dd_span["meta"].update({
                                str(k): str(v) for k, v in span['tags'].items()
                            })

                        # Add metrics (numeric values)
                        metrics = {}
                        if 'host' in span:
                            dd_span["meta"]["host"] = span['host']

                        if metrics:
                            dd_span["metrics"] = metrics

                        dd_spans.append(dd_span)

                    if dd_spans:
                        datadog_traces.append(dd_spans)

        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(datadog_traces, f, indent=2)

        logger.info(f"✓ Exported {len(datadog_traces)} traces to {output_path}")
        logger.info(f"  Total spans: {sum(len(t) for t in datadog_traces)}")

    def export_all(self, output_dir: Path) -> None:
        """Export all telemetry types to Datadog format.

        Args:
            output_dir: Directory to write exported files
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Exporting all telemetry to {output_dir}...")

        try:
            self.export_metrics(output_dir / "datadog_metrics.json")
        except (FileNotFoundError, ValueError) as e:
            logger.warning(f"Skipping metrics export: {e}")

        try:
            self.export_logs(output_dir / "datadog_logs.json")
        except (FileNotFoundError, ValueError) as e:
            logger.warning(f"Skipping logs export: {e}")

        try:
            self.export_traces(output_dir / "datadog_traces.json")
        except (FileNotFoundError, ValueError) as e:
            logger.warning(f"Skipping traces export: {e}")

        logger.info("✓ Export complete")

