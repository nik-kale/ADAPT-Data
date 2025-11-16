"""Prometheus format exporter and metrics server."""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from generator.core.logging_config import get_logger

try:
    from prometheus_client import Gauge, Counter, start_http_server, REGISTRY
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

logger = get_logger(__name__)


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

        Raises:
            ValueError: If metrics directory not found or no metrics to serve
            IOError: If file operations fail
        """
        logger.info(f"Starting Prometheus metrics server on port {port}...")
        logger.info(f"Replay speed: {replay_speed}x")
        logger.info(f"Metrics endpoint: http://localhost:{port}/metrics")

        try:
            start_http_server(port)
        except OSError as e:
            logger.error(f"Failed to start HTTP server on port {port}: {e}")
            raise

        # Load metrics
        metrics_dir = self.dataset_dir / "metrics"
        if not metrics_dir.exists():
            logger.error(f"Metrics directory not found: {metrics_dir}")
            raise ValueError(f"Metrics directory not found: {metrics_dir}")

        all_metrics = []
        errors = 0

        metric_files = list(metrics_dir.glob("*.jsonl"))
        if not metric_files:
            logger.error(f"No metric files found in {metrics_dir}")
            raise ValueError(f"No metric files found in {metrics_dir}")

        logger.info(f"Loading {len(metric_files)} metric files...")

        for metric_file in metric_files:
            try:
                with open(metric_file) as f:
                    for line_num, line in enumerate(f, 1):
                        if not line.strip():
                            continue
                        try:
                            all_metrics.append(json.loads(line))
                        except json.JSONDecodeError as e:
                            logger.error(f"JSON decode error in {metric_file}:{line_num}: {e}")
                            errors += 1
            except IOError as e:
                logger.error(f"Error reading {metric_file}: {e}")
                errors += 1

        if not all_metrics:
            logger.error("No valid metrics found")
            raise ValueError("No valid metrics found")

        # Sort by timestamp
        try:
            all_metrics.sort(key=lambda m: m.get("timestamp", ""))
        except Exception as e:
            logger.error(f"Error sorting metrics: {e}")
            raise

        # Register metrics
        logger.info(f"Registering metrics...")
        try:
            self._register_metrics(all_metrics)
        except Exception as e:
            logger.error(f"Error registering metrics: {e}")
            raise

        # Replay metrics
        logger.info(f"Replaying {len(all_metrics)} metric points...")
        try:
            start_time = datetime.fromisoformat(all_metrics[0]["timestamp"].replace('Z', '+00:00'))

            for i, metric in enumerate(all_metrics):
                try:
                    current_time = datetime.fromisoformat(metric["timestamp"].replace('Z', '+00:00'))
                    elapsed = (current_time - start_time).total_seconds()

                    # Sleep to match timeline
                    if i > 0:
                        time.sleep(elapsed / replay_speed)

                    # Update metric
                    self._update_metric(metric)

                    if (i + 1) % 100 == 0:
                        logger.info(f"  Replayed {i + 1}/{len(all_metrics)} metrics")
                except Exception as e:
                    logger.error(f"Error replaying metric {i}: {e}")
                    errors += 1

        except Exception as e:
            logger.error(f"Error during replay: {e}")
            raise

        logger.info("Replay complete. Server will continue serving latest values.")
        logger.info("Press Ctrl+C to stop.")

        if errors > 0:
            logger.warning(f"Encountered {errors} errors during replay")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")

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

        Raises:
            ValueError: If metrics directory not found or no metrics to export
            IOError: If file operations fail
        """
        metrics_dir = self.dataset_dir / "metrics"
        if not metrics_dir.exists():
            logger.error(f"Metrics directory not found: {metrics_dir}")
            raise ValueError(f"Metrics directory not found: {metrics_dir}")

        lines = []

        # Group metrics by name
        metrics_by_name: dict[str, list[dict]] = {}

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
                            name = metric.get("metric_name", "unknown")

                            if name not in metrics_by_name:
                                metrics_by_name[name] = []

                            metrics_by_name[name].append(metric)
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

        # Write in Prometheus format
        logger.info(f"Converting {len(metrics_by_name)} metric series to Prometheus format...")
        for metric_name, points in metrics_by_name.items():
            try:
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
                    try:
                        service = point.get("service", "unknown")
                        host = point.get("host", "unknown")
                        labels_key = (service, host)

                        timestamp = datetime.fromisoformat(point["timestamp"].replace('Z', '+00:00'))
                        timestamp_ms = int(timestamp.timestamp() * 1000)

                        latest_by_labels[labels_key] = (point["value"], timestamp_ms)
                    except Exception as e:
                        logger.error(f"Error processing point in {metric_name}: {e}")
                        errors += 1

                # Write latest values
                for (service, host), (value, timestamp_ms) in latest_by_labels.items():
                    labels = f'service="{service}",host="{host}"'
                    lines.append(f"{prom_name}{{{labels}}} {value} {timestamp_ms}")

            except Exception as e:
                logger.error(f"Error converting metric {metric_name}: {e}")
                errors += 1

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write('\n'.join(lines) + '\n')
        except IOError as e:
            logger.error(f"Error writing to {output_path}: {e}")
            raise

        logger.info(f"Exported Prometheus text format to {output_path}")
        if errors > 0:
            logger.warning(f"Encountered {errors} errors during export")
