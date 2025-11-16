"""Correlation analysis for generated datasets.

This module provides correlation analysis to help understand
relationships between metrics, logs, and traces in generated datasets.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from generator.core.logging_config import get_logger

logger = get_logger(__name__)


def analyze_correlations(dataset_dir: Path) -> dict[str, Any]:
    """Analyze correlations in a dataset.

    Args:
        dataset_dir: Path to dataset directory

    Returns:
        Correlation analysis results
    """
    logger.info(f"Analyzing correlations in {dataset_dir}")

    results = {
        "metric_correlations": {},
        "temporal_correlations": {},
        "service_correlations": {},
        "anomaly_correlations": {},
    }

    # Load metrics
    metrics_data = _load_metrics(dataset_dir)
    if metrics_data:
        results["metric_correlations"] = _analyze_metric_correlations(metrics_data)
        results["temporal_correlations"] = _analyze_temporal_patterns(metrics_data)

    # Load logs
    logs_data = _load_logs(dataset_dir)
    if logs_data:
        results["service_correlations"] = _analyze_service_correlations(logs_data)
        results["anomaly_correlations"] = _analyze_anomaly_correlations(logs_data, metrics_data)

    return results


def _load_metrics(dataset_dir: Path) -> list[dict[str, Any]]:
    """Load all metrics from dataset."""
    metrics = []
    metrics_dir = dataset_dir / "metrics"

    if not metrics_dir.exists():
        return metrics

    for metric_file in metrics_dir.glob("*.jsonl"):
        try:
            with open(metric_file) as f:
                for line in f:
                    if line.strip():
                        metrics.append(json.loads(line))
        except Exception as e:
            logger.error(f"Error loading {metric_file}: {e}")

    return metrics


def _load_logs(dataset_dir: Path) -> list[dict[str, Any]]:
    """Load all logs from dataset."""
    logs = []
    logs_dir = dataset_dir / "logs"

    if not logs_dir.exists():
        return logs

    for log_file in logs_dir.glob("*.jsonl"):
        try:
            with open(log_file) as f:
                for line in f:
                    if line.strip():
                        logs.append(json.loads(line))
        except Exception as e:
            logger.error(f"Error loading {log_file}: {e}")

    return logs


def _analyze_metric_correlations(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze correlations between different metrics."""
    # Group metrics by name and service
    metric_groups: dict[tuple[str, str], list[float]] = {}

    for metric in metrics:
        key = (metric.get("metric_name", "unknown"), metric.get("service", "unknown"))
        if key not in metric_groups:
            metric_groups[key] = []
        metric_groups[key].append(metric.get("value", 0))

    # Calculate correlations between metric pairs
    correlations = []
    metric_names = list(metric_groups.keys())

    for i, metric1 in enumerate(metric_names):
        for metric2 in metric_names[i + 1:]:
            values1 = np.array(metric_groups[metric1])
            values2 = np.array(metric_groups[metric2])

            # Align lengths
            min_len = min(len(values1), len(values2))
            if min_len < 2:
                continue

            values1 = values1[:min_len]
            values2 = values2[:min_len]

            # Calculate Pearson correlation
            try:
                correlation = np.corrcoef(values1, values2)[0, 1]

                if abs(correlation) > 0.3:  # Only report significant correlations
                    correlations.append({
                        "metric1": f"{metric1[0]} ({metric1[1]})",
                        "metric2": f"{metric2[0]} ({metric2[1]})",
                        "correlation": float(correlation),
                        "strength": _correlation_strength(correlation)
                    })
            except Exception as e:
                logger.debug(f"Error calculating correlation: {e}")

    # Sort by absolute correlation
    correlations.sort(key=lambda x: abs(x["correlation"]), reverse=True)

    return {
        "top_correlations": correlations[:10],
        "total_pairs_analyzed": len(metric_names) * (len(metric_names) - 1) // 2,
        "significant_correlations": len(correlations)
    }


def _correlation_strength(correlation: float) -> str:
    """Determine correlation strength."""
    abs_corr = abs(correlation)
    if abs_corr >= 0.8:
        return "very strong"
    elif abs_corr >= 0.6:
        return "strong"
    elif abs_corr >= 0.4:
        return "moderate"
    else:
        return "weak"


def _analyze_temporal_patterns(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze temporal patterns in metrics."""
    if not metrics:
        return {}

    # Group by metric name
    by_metric: dict[str, list[tuple[datetime, float]]] = {}

    for metric in metrics:
        name = metric.get("metric_name", "unknown")
        try:
            timestamp = datetime.fromisoformat(metric["timestamp"].replace('Z', '+00:00'))
            value = metric.get("value", 0)
            if name not in by_metric:
                by_metric[name] = []
            by_metric[name].append((timestamp, value))
        except Exception:
            continue

    patterns = []
    for metric_name, data in by_metric.items():
        if len(data) < 10:
            continue

        # Sort by time
        data.sort(key=lambda x: x[0])
        values = [v for _, v in data]

        # Check for trend
        time_indices = np.arange(len(values))
        correlation = np.corrcoef(time_indices, values)[0, 1]

        if abs(correlation) > 0.5:
            trend = "increasing" if correlation > 0 else "decreasing"
            patterns.append({
                "metric": metric_name,
                "pattern": "trend",
                "direction": trend,
                "strength": abs(correlation)
            })

    return {
        "patterns_detected": patterns,
        "metrics_analyzed": len(by_metric)
    }


def _analyze_service_correlations(logs: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze correlations between services based on logs."""
    # Count errors per service
    service_errors: dict[str, int] = {}
    service_total: dict[str, int] = {}

    for log in logs:
        service = log.get("service", "unknown")
        level = log.get("level", "INFO")

        service_total[service] = service_total.get(service, 0) + 1
        if level in ["ERROR", "CRITICAL"]:
            service_errors[service] = service_errors.get(service, 0) + 1

    # Calculate error rates
    error_rates = []
    for service in service_total:
        rate = service_errors.get(service, 0) / service_total[service]
        error_rates.append({
            "service": service,
            "error_rate": rate,
            "total_logs": service_total[service],
            "errors": service_errors.get(service, 0)
        })

    error_rates.sort(key=lambda x: x["error_rate"], reverse=True)

    return {
        "service_error_rates": error_rates,
        "services_analyzed": len(service_total)
    }


def _analyze_anomaly_correlations(
    logs: list[dict[str, Any]],
    metrics: list[dict[str, Any]]
) -> dict[str, Any]:
    """Analyze correlations between log anomalies and metric anomalies."""
    # Find time windows with errors
    error_windows = set()
    for log in logs:
        if log.get("level") in ["ERROR", "CRITICAL"]:
            try:
                timestamp = datetime.fromisoformat(log["timestamp"].replace('Z', '+00:00'))
                # Round to minute
                window = timestamp.replace(second=0, microsecond=0)
                error_windows.add(window)
            except Exception:
                continue

    # Find metrics with anomalies in same windows
    anomalous_metrics = []
    for metric in metrics:
        try:
            timestamp = datetime.fromisoformat(metric["timestamp"].replace('Z', '+00:00'))
            window = timestamp.replace(second=0, microsecond=0)

            if window in error_windows:
                anomalous_metrics.append({
                    "metric": metric.get("metric_name", "unknown"),
                    "service": metric.get("service", "unknown"),
                    "value": metric.get("value", 0),
                    "timestamp": metric["timestamp"]
                })
        except Exception:
            continue

    return {
        "error_windows": len(error_windows),
        "correlated_metric_anomalies": len(anomalous_metrics),
        "correlation_rate": len(anomalous_metrics) / len(error_windows) if error_windows else 0
    }


def print_correlation_report(results: dict[str, Any]) -> None:
    """Print correlation analysis report.

    Args:
        results: Correlation analysis results
    """
    logger.info("\n" + "=" * 70)
    logger.info("CORRELATION ANALYSIS REPORT")
    logger.info("=" * 70)

    # Metric correlations
    if "metric_correlations" in results:
        mc = results["metric_correlations"]
        logger.info(f"\n📊 METRIC CORRELATIONS:")
        logger.info(f"  Pairs Analyzed: {mc.get('total_pairs_analyzed', 0)}")
        logger.info(f"  Significant Correlations: {mc.get('significant_correlations', 0)}")

        if mc.get("top_correlations"):
            logger.info(f"\n  Top Correlations:")
            for corr in mc["top_correlations"][:5]:
                sign = "+" if corr["correlation"] > 0 else ""
                logger.info(f"    {corr['metric1']} ↔ {corr['metric2']}")
                logger.info(f"      Correlation: {sign}{corr['correlation']:.3f} ({corr['strength']})")

    # Temporal patterns
    if "temporal_correlations" in results:
        tc = results["temporal_correlations"]
        logger.info(f"\n📈 TEMPORAL PATTERNS:")
        logger.info(f"  Metrics Analyzed: {tc.get('metrics_analyzed', 0)}")

        if tc.get("patterns_detected"):
            logger.info(f"  Patterns Detected:")
            for pattern in tc["patterns_detected"][:5]:
                logger.info(f"    {pattern['metric']}: {pattern['direction']} trend "
                      f"(strength: {pattern['strength']:.2f})")

    # Service correlations
    if "service_correlations" in results:
        sc = results["service_correlations"]
        logger.info(f"\n🔧 SERVICE ERROR RATES:")

        if sc.get("service_error_rates"):
            for svc in sc["service_error_rates"][:5]:
                logger.info(f"    {svc['service']}: {svc['error_rate']:.1%} "
                      f"({svc['errors']}/{svc['total_logs']} logs)")

    # Anomaly correlations
    if "anomaly_correlations" in results:
        ac = results["anomaly_correlations"]
        logger.info(f"\n⚠️  ANOMALY CORRELATIONS:")
        logger.info(f"  Error Windows: {ac.get('error_windows', 0)}")
        logger.info(f"  Correlated Metric Anomalies: {ac.get('correlated_metric_anomalies', 0)}")
        logger.info(f"  Correlation Rate: {ac.get('correlation_rate', 0):.1%}")

    logger.info("\n" + "=" * 70 + "\n")
