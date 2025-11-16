"""Prometheus format exporter and metrics server."""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from prometheus_client import Gauge, Counter, start_http_server, REGISTRY
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


class PrometheusExporter:
    """Export and serve metrics in Prometheus format.

    Can either export to Prometheus text format or serve metrics
    via HTTP endpoint for Prometheus to scrape.
    """

    def __init__(self, dataset_dir: Path) -> None:
        """Initialize exporter.

        Args:
            dataset_dir: Directory containing ADAPT-Data dataset
        """
        if not PROMETHEUS_AVAILABLE:
            raise ImportError(
                "prometheus_client is required for Prometheus export. "
                "Install with: pip install prometheus-client"
            )

        self.dataset_dir = dataset_dir
        self.metrics: dict[str, Any] = {}

    def serve(self, port: int = 9090, replay_speed: float = 1.0) -> None:
        """Serve metrics via HTTP for Prometheus scraping.

        Args:
            port: HTTP port to listen on
            replay_speed: Speed multiplier for replaying incident (1.0 = real-time)
        """
        print(f"Starting Prometheus metrics server on port {port}...")
        print(f"Replay speed: {replay_speed}x")
        print(f"Metrics endpoint: http://localhost:{port}/metrics")

        start_http_server(port)

        # Load metrics
        metrics_dir = self.dataset_dir / "metrics"
        if not metrics_dir.exists():
            raise ValueError(f"Metrics directory not found: {metrics_dir}")

        all_metrics = []
        for metric_file in metrics_dir.glob("*.jsonl"):
            with open(metric_file) as f:
                for line in f:
                    if line.strip():
                        all_metrics.append(json.loads(line))

        # Sort by timestamp
        all_metrics.sort(key=lambda m: m["timestamp"])

        if not all_metrics:
            print("No metrics found")
            return

        # Register metrics
        self._register_metrics(all_metrics)

        # Replay metrics
        print(f"\nReplaying {len(all_metrics)} metric points...")
        start_time = datetime.fromisoformat(all_metrics[0]["timestamp"].replace('Z', '+00:00'))

        for i, metric in enumerate(all_metrics):
            current_time = datetime.fromisoformat(metric["timestamp"].replace('Z', '+00:00'))
            elapsed = (current_time - start_time).total_seconds()

            # Sleep to match timeline
            if i > 0:
                time.sleep(elapsed / replay_speed)

            # Update metric
            self._update_metric(metric)

            if (i + 1) % 100 == 0:
                print(f"  Replayed {i + 1}/{len(all_metrics)} metrics")

        print("\n✓ Replay complete. Server will continue serving latest values.")
        print("Press Ctrl+C to stop.")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")

    def _register_metrics(self, metrics: list[dict[str, Any]]) -> None:
        """Register Prometheus metrics."""
        # Find unique metric names
        unique_metrics = {m["metric_name"] for m in metrics}

        for metric_name in unique_metrics:
            # Determine metric type from first occurrence
            sample = next(m for m in metrics if m["metric_name"] == metric_name)
            metric_type = sample.get("metric_type", "gauge")

            # Sanitize metric name for Prometheus
            prom_name = metric_name.replace("-", "_").replace(".", "_")

            if metric_type == "counter":
                self.metrics[metric_name] = Counter(
                    prom_name,
                    f"ADAPT-Data metric: {metric_name}",
                    ["service", "host"]
                )
            else:
                self.metrics[metric_name] = Gauge(
                    prom_name,
                    f"ADAPT-Data metric: {metric_name}",
                    ["service", "host"]
                )

    def _update_metric(self, metric: dict[str, Any]) -> None:
        """Update Prometheus metric with new value."""
        metric_name = metric["metric_name"]
        if metric_name not in self.metrics:
            return

        prom_metric = self.metrics[metric_name]
        labels = {
            "service": metric.get("service", "unknown"),
            "host": metric.get("host", "unknown")
        }

        value = metric.get("value", 0)

        if isinstance(prom_metric, Counter):
            # For counters, increment by value
            prom_metric.labels(**labels).inc(value)
        else:
            # For gauges, set to value
            prom_metric.labels(**labels).set(value)

    def export_text_format(self, output_path: Path) -> None:
        """Export metrics in Prometheus text format.

        Args:
            output_path: Where to write Prometheus text format metrics
        """
        metrics_dir = self.dataset_dir / "metrics"
        if not metrics_dir.exists():
            raise ValueError(f"Metrics directory not found: {metrics_dir}")

        lines = []

        # Group metrics by name
        metrics_by_name: dict[str, list[dict]] = {}

        for metric_file in metrics_dir.glob("*.jsonl"):
            with open(metric_file) as f:
                for line in f:
                    if not line.strip():
                        continue

                    metric = json.loads(line)
                    name = metric["metric_name"]

                    if name not in metrics_by_name:
                        metrics_by_name[name] = []

                    metrics_by_name[name].append(metric)

        # Write in Prometheus format
        for metric_name, points in metrics_by_name.items():
            # Sanitize name
            prom_name = metric_name.replace("-", "_").replace(".", "_")

            # Get type
            metric_type = points[0].get("metric_type", "gauge")

            # Write TYPE and HELP
            lines.append(f"# HELP {prom_name} ADAPT-Data metric: {metric_name}")
            lines.append(f"# TYPE {prom_name} {metric_type}")

            # Write data points (use latest value per label combination)
            latest_by_labels: dict[tuple, tuple[float, str]] = {}

            for point in points:
                service = point.get("service", "unknown")
                host = point.get("host", "unknown")
                labels_key = (service, host)

                timestamp = datetime.fromisoformat(point["timestamp"].replace('Z', '+00:00'))
                timestamp_ms = int(timestamp.timestamp() * 1000)

                latest_by_labels[labels_key] = (point["value"], timestamp_ms)

            # Write latest values
            for (service, host), (value, timestamp_ms) in latest_by_labels.items():
                labels = f'service="{service}",host="{host}"'
                lines.append(f"{prom_name}{{{labels}}} {value} {timestamp_ms}")

        with open(output_path, 'w') as f:
            f.write('\n'.join(lines) + '\n')

        print(f"Exported Prometheus text format to {output_path}")
