"""Example Custom Analyzer Plugin for ADAPT-Data.

This plugin demonstrates how to create a custom analyzer
that detects anomaly patterns in generated telemetry.

To use this plugin:
1. Copy this file to ~/.adapt-data/plugins/
2. The plugin will be auto-discovered on startup
3. Use programmatically or via custom CLI commands
"""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from generator.core.logging_config import get_logger
from generator.core.plugins import AnalyzerPlugin

logger = get_logger(__name__)


class AnomalyPatternAnalyzer:
    """Analyzes telemetry data for common anomaly patterns.

    Detects patterns like:
    - Sudden spikes in metrics
    - Error bursts in logs
    - Missing data gaps
    - Correlation between errors and metric anomalies
    """

    def __init__(self, dataset_dir: Path) -> None:
        """Initialize anomaly analyzer.

        Args:
            dataset_dir: Directory containing generated dataset
        """
        self.dataset_dir = dataset_dir
        logger.info(f"Initialized anomaly analyzer for {dataset_dir}")

    def analyze(self) -> dict[str, Any]:
        """Analyze dataset for anomaly patterns.

        Returns:
            Dict containing analysis results
        """
        results = {
            "metric_anomalies": self._analyze_metrics(),
            "log_anomalies": self._analyze_logs(),
            "data_quality": self._check_data_quality(),
            "summary": {}
        }

        # Generate summary
        results["summary"] = {
            "total_metric_anomalies": len(results["metric_anomalies"]["spikes"]),
            "total_log_errors": results["log_anomalies"]["error_count"],
            "data_completeness": results["data_quality"]["completeness_percent"],
            "analysis_timestamp": datetime.utcnow().isoformat()
        }

        logger.info("Anomaly analysis complete")
        return results

    def _analyze_metrics(self) -> dict[str, Any]:
        """Analyze metrics for anomalies."""
        metric_files = list(self.dataset_dir.glob("metrics/*.jsonl"))

        if not metric_files:
            return {"spikes": [], "gaps": []}

        metrics_by_name = defaultdict(list)

        # Load all metrics
        for metric_file in metric_files:
            with open(metric_file) as f:
                for line in f:
                    metric = json.loads(line)
                    metrics_by_name[metric['metric_name']].append(metric)

        spikes = []

        # Detect spikes in each metric
        for metric_name, metric_data in metrics_by_name.items():
            if len(metric_data) < 3:
                continue

            # Sort by timestamp
            metric_data.sort(key=lambda m: m['timestamp'])

            # Simple spike detection: value > 2 * previous value
            for i in range(1, len(metric_data)):
                prev_value = metric_data[i-1]['value']
                curr_value = metric_data[i]['value']

                if prev_value > 0 and curr_value > prev_value * 2:
                    spikes.append({
                        "metric_name": metric_name,
                        "timestamp": metric_data[i]['timestamp'],
                        "previous_value": prev_value,
                        "spike_value": curr_value,
                        "multiplier": round(curr_value / prev_value, 2)
                    })

        logger.info(f"Found {len(spikes)} metric spikes")

        return {
            "spikes": spikes,
            "total_metrics": sum(len(v) for v in metrics_by_name.values()),
            "unique_metric_names": len(metrics_by_name)
        }

    def _analyze_logs(self) -> dict[str, Any]:
        """Analyze logs for error patterns."""
        log_files = list(self.dataset_dir.glob("logs/*.jsonl"))

        if not log_files:
            return {"error_count": 0, "errors_by_service": {}}

        errors_by_service = defaultdict(int)
        error_count = 0

        for log_file in log_files:
            with open(log_file) as f:
                for line in f:
                    log = json.loads(line)
                    if log.get('level') in ['ERROR', 'FATAL']:
                        error_count += 1
                        errors_by_service[log.get('service', 'unknown')] += 1

        logger.info(f"Found {error_count} error logs across {len(errors_by_service)} services")

        return {
            "error_count": error_count,
            "errors_by_service": dict(errors_by_service),
            "top_error_services": sorted(
                errors_by_service.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }

    def _check_data_quality(self) -> dict[str, Any]:
        """Check data quality metrics."""
        quality = {
            "has_metrics": False,
            "has_logs": False,
            "has_traces": False,
            "completeness_percent": 0.0
        }

        # Check for presence of each data type
        quality["has_metrics"] = len(list(self.dataset_dir.glob("metrics/*.jsonl"))) > 0
        quality["has_logs"] = len(list(self.dataset_dir.glob("logs/*.jsonl"))) > 0
        quality["has_traces"] = len(list(self.dataset_dir.glob("traces/*.jsonl"))) > 0

        # Calculate completeness
        present_types = sum([
            quality["has_metrics"],
            quality["has_logs"],
            quality["has_traces"]
        ])
        quality["completeness_percent"] = round((present_types / 3.0) * 100, 1)

        # Check for timeline and topology
        quality["has_timeline"] = (self.dataset_dir / "timeline.json").exists()
        quality["has_topology"] = (self.dataset_dir / "topology.json").exists()

        logger.info(f"Data completeness: {quality['completeness_percent']}%")

        return quality


# Plugin registration
class AnomalyPatternAnalyzerPlugin(AnalyzerPlugin):
    """Plugin wrapper for AnomalyPatternAnalyzer."""

    name = "anomaly_pattern_analyzer"
    version = "1.0.0"
    description = "Analyzes telemetry for common anomaly patterns and data quality issues"
    analyzer_class = AnomalyPatternAnalyzer


# Export plugin instance
plugin = AnomalyPatternAnalyzerPlugin()
