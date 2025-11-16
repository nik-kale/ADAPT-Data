"""Dataset statistics and profiling tools."""

import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np


def analyze_dataset(dataset_dir: Path) -> dict[str, Any]:
    """Analyze dataset and generate statistics.

    Args:
        dataset_dir: Directory containing dataset

    Returns:
        Dictionary of statistics
    """
    stats: dict[str, Any] = {
        "dataset_path": str(dataset_dir),
        "analysis_time": datetime.utcnow().isoformat(),
        "logs": {},
        "metrics": {},
        "traces": {},
        "timeline": {},
    }

    # Analyze logs
    logs_dir = dataset_dir / "logs"
    if logs_dir.exists():
        stats["logs"] = _analyze_logs(logs_dir)

    # Analyze metrics
    metrics_dir = dataset_dir / "metrics"
    if metrics_dir.exists():
        stats["metrics"] = _analyze_metrics(metrics_dir)

    # Analyze traces
    traces_dir = dataset_dir / "traces"
    if traces_dir.exists():
        stats["traces"] = _analyze_traces(traces_dir)

    # Analyze timeline
    timelines_dir = dataset_dir / "timelines"
    if timelines_dir.exists():
        stats["timeline"] = _analyze_timeline(timelines_dir)

    return stats


def _analyze_logs(logs_dir: Path) -> dict[str, Any]:
    """Analyze log files."""
    total_logs = 0
    level_counts = Counter()
    service_counts = Counter()
    timestamps = []

    for log_file in logs_dir.glob("*.jsonl"):
        with open(log_file) as f:
            for line in f:
                if not line.strip():
                    continue

                log_entry = json.loads(line)
                total_logs += 1

                level_counts[log_entry.get("level", "UNKNOWN")] += 1
                service_counts[log_entry.get("service", "unknown")] += 1

                ts_str = log_entry.get("timestamp")
                if ts_str:
                    timestamps.append(ts_str)

    return {
        "total_count": total_logs,
        "level_distribution": dict(level_counts),
        "service_distribution": dict(service_counts),
        "top_services": service_counts.most_common(5),
        "time_range": {
            "start": min(timestamps) if timestamps else None,
            "end": max(timestamps) if timestamps else None,
        }
    }


def _analyze_metrics(metrics_dir: Path) -> dict[str, Any]:
    """Analyze metric files."""
    total_metrics = 0
    metric_names = Counter()
    anomalous_count = 0
    values_by_metric: dict[str, list[float]] = defaultdict(list)

    for metric_file in metrics_dir.glob("*.jsonl"):
        with open(metric_file) as f:
            for line in f:
                if not line.strip():
                    continue

                metric = json.loads(line)
                total_metrics += 1

                name = metric.get("metric_name", "unknown")
                metric_names[name] += 1

                if metric.get("anomaly_injected"):
                    anomalous_count += 1

                value = metric.get("value")
                if value is not None:
                    values_by_metric[name].append(float(value))

    # Calculate statistics for each metric
    metric_stats = {}
    for name, values in values_by_metric.items():
        if values:
            metric_stats[name] = {
                "count": len(values),
                "mean": float(np.mean(values)),
                "median": float(np.median(values)),
                "std": float(np.std(values)),
                "min": float(np.min(values)),
                "max": float(np.max(values)),
                "p95": float(np.percentile(values, 95)),
                "p99": float(np.percentile(values, 99)),
            }

    return {
        "total_count": total_metrics,
        "unique_metrics": len(metric_names),
        "anomalous_count": anomalous_count,
        "anomalous_percentage": (anomalous_count / total_metrics * 100) if total_metrics > 0 else 0,
        "metric_distribution": dict(metric_names.most_common(10)),
        "metric_statistics": metric_stats,
    }


def _analyze_traces(traces_dir: Path) -> dict[str, Any]:
    """Analyze trace files."""
    total_traces = 0
    total_spans = 0
    status_counts = Counter()
    service_counts = Counter()
    durations = []

    for trace_file in traces_dir.glob("*.jsonl"):
        with open(trace_file) as f:
            for line in f:
                if not line.strip():
                    continue

                trace = json.loads(line)
                total_traces += 1

                for span in trace.get("spans", []):
                    total_spans += 1
                    status_counts[span.get("status", "UNKNOWN")] += 1
                    service_counts[span.get("service", "unknown")] += 1

                    duration = span.get("duration_ms")
                    if duration is not None:
                        durations.append(float(duration))

    duration_stats = {}
    if durations:
        duration_stats = {
            "mean": float(np.mean(durations)),
            "median": float(np.median(durations)),
            "p95": float(np.percentile(durations, 95)),
            "p99": float(np.percentile(durations, 99)),
            "max": float(np.max(durations)),
        }

    return {
        "total_traces": total_traces,
        "total_spans": total_spans,
        "avg_spans_per_trace": total_spans / total_traces if total_traces > 0 else 0,
        "status_distribution": dict(status_counts),
        "service_distribution": dict(service_counts.most_common(10)),
        "duration_stats_ms": duration_stats,
    }


def _analyze_timeline(timelines_dir: Path) -> dict[str, Any]:
    """Analyze timeline files."""
    timeline_files = list(timelines_dir.glob("*.json"))

    if not timeline_files:
        return {}

    # Load first timeline
    with open(timeline_files[0]) as f:
        timeline = json.load(f)

    event_types = Counter(e.get("event_type") for e in timeline.get("events", []))

    return {
        "incident_id": timeline.get("incident_id"),
        "severity": timeline.get("severity"),
        "affected_services": timeline.get("affected_services", []),
        "root_cause": timeline.get("root_cause"),
        "total_events": len(timeline.get("events", [])),
        "event_type_distribution": dict(event_types),
        "time_range": {
            "start": timeline.get("start_time"),
            "end": timeline.get("end_time"),
        }
    }


def print_stats(stats: dict[str, Any]) -> None:
    """Print statistics in human-readable format."""
    print("\n" + "=" * 70)
    print("DATASET STATISTICS")
    print("=" * 70)

    # Logs
    if stats.get("logs"):
        print("\n📝 LOGS:")
        logs = stats["logs"]
        print(f"  Total Entries: {logs['total_count']:,}")
        print(f"  Log Levels:")
        for level, count in sorted(logs['level_distribution'].items()):
            pct = count / logs['total_count'] * 100
            print(f"    {level}: {count:,} ({pct:.1f}%)")

    # Metrics
    if stats.get("metrics"):
        print("\n📊 METRICS:")
        metrics = stats["metrics"]
        print(f"  Total Data Points: {metrics['total_count']:,}")
        print(f"  Unique Metrics: {metrics['unique_metrics']}")
        print(f"  Anomalous Points: {metrics['anomalous_count']:,} ({metrics['anomalous_percentage']:.1f}%)")

    # Traces
    if stats.get("traces"):
        print("\n🔍 TRACES:")
        traces = stats["traces"]
        print(f"  Total Traces: {traces['total_traces']:,}")
        print(f"  Total Spans: {traces['total_spans']:,}")
        print(f"  Avg Spans/Trace: {traces['avg_spans_per_trace']:.1f}")

        if traces.get("duration_stats_ms"):
            dur = traces["duration_stats_ms"]
            print(f"  Duration Stats (ms):")
            print(f"    Mean: {dur['mean']:.2f}")
            print(f"    p95: {dur['p95']:.2f}")
            print(f"    p99: {dur['p99']:.2f}")

    # Timeline
    if stats.get("timeline"):
        print("\n📅 TIMELINE:")
        timeline = stats["timeline"]
        print(f"  Incident ID: {timeline.get('incident_id')}")
        print(f"  Severity: {timeline.get('severity')}")
        print(f"  Root Cause: {timeline.get('root_cause')}")
        print(f"  Total Events: {timeline.get('total_events')}")

    print("\n" + "=" * 70 + "\n")


def export_stats(stats: dict[str, Any], output_path: Path) -> None:
    """Export statistics to JSON file."""
    with open(output_path, 'w') as f:
        json.dump(stats, f, indent=2, default=str)

    print(f"Statistics exported to: {output_path}")
