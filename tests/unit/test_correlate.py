"""Unit tests for correlation analysis module."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pytest

from cli.correlate import (
    analyze_correlations,
    print_correlation_report,
    _load_metrics,
    _load_logs,
    _analyze_metric_correlations,
    _correlation_strength,
    _analyze_temporal_patterns,
    _analyze_service_correlations,
    _analyze_anomaly_correlations,
)


class TestDataLoading:
    """Test data loading functions."""

    def test_load_metrics_empty_directory(self, tmp_path):
        """Test loading metrics from empty directory."""
        # Create empty metrics directory
        metrics_dir = tmp_path / "metrics"
        metrics_dir.mkdir()

        result = _load_metrics(tmp_path)

        assert result == []

    def test_load_metrics_no_directory(self, tmp_path):
        """Test loading metrics when directory doesn't exist."""
        result = _load_metrics(tmp_path)

        assert result == []

    def test_load_metrics_single_file(self, tmp_path):
        """Test loading metrics from single JSONL file."""
        metrics_dir = tmp_path / "metrics"
        metrics_dir.mkdir()

        # Create sample metrics file
        metrics_file = metrics_dir / "cpu_usage.jsonl"
        metrics_data = [
            {
                "metric_name": "cpu_usage",
                "service": "api-server",
                "value": 45.5,
                "timestamp": "2025-01-15T10:00:00Z"
            },
            {
                "metric_name": "cpu_usage",
                "service": "api-server",
                "value": 52.3,
                "timestamp": "2025-01-15T10:01:00Z"
            }
        ]

        with open(metrics_file, 'w') as f:
            for metric in metrics_data:
                f.write(json.dumps(metric) + '\n')

        result = _load_metrics(tmp_path)

        assert len(result) == 2
        assert result[0]["metric_name"] == "cpu_usage"
        assert result[0]["value"] == 45.5

    def test_load_metrics_multiple_files(self, tmp_path):
        """Test loading metrics from multiple JSONL files."""
        metrics_dir = tmp_path / "metrics"
        metrics_dir.mkdir()

        # Create multiple metrics files
        for i, metric_name in enumerate(["cpu_usage", "memory_usage"]):
            metrics_file = metrics_dir / f"{metric_name}.jsonl"
            with open(metrics_file, 'w') as f:
                for j in range(3):
                    metric = {
                        "metric_name": metric_name,
                        "service": "api-server",
                        "value": 50.0 + i + j,
                        "timestamp": f"2025-01-15T10:0{j}:00Z"
                    }
                    f.write(json.dumps(metric) + '\n')

        result = _load_metrics(tmp_path)

        assert len(result) == 6  # 2 files × 3 metrics each

    def test_load_metrics_with_empty_lines(self, tmp_path):
        """Test loading metrics file with empty lines."""
        metrics_dir = tmp_path / "metrics"
        metrics_dir.mkdir()

        metrics_file = metrics_dir / "cpu_usage.jsonl"
        with open(metrics_file, 'w') as f:
            f.write(json.dumps({"metric_name": "cpu_usage", "value": 50.0}) + '\n')
            f.write('\n')  # Empty line
            f.write('   \n')  # Whitespace line
            f.write(json.dumps({"metric_name": "cpu_usage", "value": 60.0}) + '\n')

        result = _load_metrics(tmp_path)

        assert len(result) == 2

    def test_load_metrics_with_malformed_json(self, tmp_path):
        """Test loading metrics with malformed JSON (should skip)."""
        metrics_dir = tmp_path / "metrics"
        metrics_dir.mkdir()

        # Create two separate files - one valid, one invalid
        valid_file = metrics_dir / "cpu_usage.jsonl"
        with open(valid_file, 'w') as f:
            f.write(json.dumps({"metric_name": "cpu_usage", "value": 50.0}) + '\n')

        invalid_file = metrics_dir / "invalid.jsonl"
        with open(invalid_file, 'w') as f:
            f.write('invalid json line\n')

        result = _load_metrics(tmp_path)

        # Should load valid file, skip invalid file entirely
        assert len(result) == 1
        assert result[0]["value"] == 50.0

    def test_load_logs_empty_directory(self, tmp_path):
        """Test loading logs from empty directory."""
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()

        result = _load_logs(tmp_path)

        assert result == []

    def test_load_logs_no_directory(self, tmp_path):
        """Test loading logs when directory doesn't exist."""
        result = _load_logs(tmp_path)

        assert result == []

    def test_load_logs_single_file(self, tmp_path):
        """Test loading logs from single JSONL file."""
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()

        logs_file = logs_dir / "api-server.jsonl"
        logs_data = [
            {
                "service": "api-server",
                "level": "INFO",
                "message": "Request processed",
                "timestamp": "2025-01-15T10:00:00Z"
            },
            {
                "service": "api-server",
                "level": "ERROR",
                "message": "Connection failed",
                "timestamp": "2025-01-15T10:01:00Z"
            }
        ]

        with open(logs_file, 'w') as f:
            for log in logs_data:
                f.write(json.dumps(log) + '\n')

        result = _load_logs(tmp_path)

        assert len(result) == 2
        assert result[0]["level"] == "INFO"
        assert result[1]["level"] == "ERROR"


class TestMetricCorrelations:
    """Test metric correlation analysis."""

    def test_analyze_metric_correlations_empty_list(self):
        """Test correlation analysis with empty metrics list."""
        result = _analyze_metric_correlations([])

        assert result["total_pairs_analyzed"] == 0
        assert result["significant_correlations"] == 0
        assert result["top_correlations"] == []

    def test_analyze_metric_correlations_single_metric(self):
        """Test correlation analysis with single metric type."""
        metrics = [
            {"metric_name": "cpu_usage", "service": "api", "value": 50.0},
            {"metric_name": "cpu_usage", "service": "api", "value": 55.0},
            {"metric_name": "cpu_usage", "service": "api", "value": 60.0},
        ]

        result = _analyze_metric_correlations(metrics)

        # Can't correlate with itself
        assert result["total_pairs_analyzed"] == 0
        assert result["significant_correlations"] == 0

    def test_analyze_metric_correlations_perfect_positive(self):
        """Test correlation analysis with perfectly correlated metrics."""
        metrics = []
        # Create perfectly correlated metrics
        for i in range(10):
            metrics.append({
                "metric_name": "cpu_usage",
                "service": "api",
                "value": float(i * 10)
            })
            metrics.append({
                "metric_name": "memory_usage",
                "service": "api",
                "value": float(i * 10)  # Same values
            })

        result = _analyze_metric_correlations(metrics)

        assert result["total_pairs_analyzed"] == 1
        assert result["significant_correlations"] == 1
        assert len(result["top_correlations"]) == 1

        # Check correlation is close to 1.0
        corr = result["top_correlations"][0]
        assert corr["correlation"] > 0.99
        assert corr["strength"] == "very strong"
        assert "cpu_usage" in corr["metric1"]
        assert "memory_usage" in corr["metric2"]

    def test_analyze_metric_correlations_perfect_negative(self):
        """Test correlation analysis with negatively correlated metrics."""
        metrics = []
        # Create negatively correlated metrics
        for i in range(10):
            metrics.append({
                "metric_name": "cpu_usage",
                "service": "api",
                "value": float(i * 10)
            })
            metrics.append({
                "metric_name": "idle_time",
                "service": "api",
                "value": float(100 - i * 10)  # Inverse relationship
            })

        result = _analyze_metric_correlations(metrics)

        assert result["significant_correlations"] >= 1
        corr = result["top_correlations"][0]
        assert corr["correlation"] < -0.9
        assert corr["strength"] == "very strong"

    def test_analyze_metric_correlations_weak_correlation(self):
        """Test correlation analysis filters out weak correlations."""
        np.random.seed(42)
        metrics = []

        # Create metrics with weak correlation (random noise)
        for i in range(20):
            metrics.append({
                "metric_name": "metric1",
                "service": "api",
                "value": float(np.random.random() * 100)
            })
            metrics.append({
                "metric_name": "metric2",
                "service": "api",
                "value": float(np.random.random() * 100)
            })

        result = _analyze_metric_correlations(metrics)

        # Weak correlations should be filtered out (threshold is 0.3)
        # Random data should not produce significant correlations
        assert result["significant_correlations"] <= 1

    def test_analyze_metric_correlations_multiple_services(self):
        """Test correlation analysis with metrics from different services."""
        metrics = []
        for i in range(10):
            metrics.append({
                "metric_name": "cpu_usage",
                "service": "api",
                "value": float(i * 10)
            })
            metrics.append({
                "metric_name": "cpu_usage",
                "service": "db",
                "value": float(i * 10)
            })

        result = _analyze_metric_correlations(metrics)

        # Different services should be treated as different metric groups
        assert result["total_pairs_analyzed"] == 1
        corr = result["top_correlations"][0]
        assert "api" in corr["metric1"]
        assert "db" in corr["metric2"]

    def test_analyze_metric_correlations_insufficient_data(self):
        """Test correlation analysis with insufficient data points."""
        metrics = [
            {"metric_name": "cpu_usage", "service": "api", "value": 50.0},
            {"metric_name": "memory_usage", "service": "api", "value": 70.0},
        ]

        result = _analyze_metric_correlations(metrics)

        # Need at least 2 points for correlation
        assert result["significant_correlations"] == 0

    def test_correlation_strength_classification(self):
        """Test correlation strength classification."""
        assert _correlation_strength(0.95) == "very strong"
        assert _correlation_strength(-0.85) == "very strong"
        assert _correlation_strength(0.70) == "strong"
        assert _correlation_strength(-0.65) == "strong"
        assert _correlation_strength(0.50) == "moderate"
        assert _correlation_strength(-0.45) == "moderate"
        assert _correlation_strength(0.35) == "weak"
        assert _correlation_strength(-0.31) == "weak"
        assert _correlation_strength(0.0) == "weak"


class TestTemporalPatterns:
    """Test temporal pattern analysis."""

    def test_analyze_temporal_patterns_empty_list(self):
        """Test temporal pattern analysis with empty metrics list."""
        result = _analyze_temporal_patterns([])

        assert result == {}

    def test_analyze_temporal_patterns_insufficient_data(self):
        """Test temporal patterns with insufficient data points."""
        base_time = datetime(2025, 1, 15, 10, 0, 0)
        metrics = [
            {
                "metric_name": "cpu_usage",
                "value": 50.0,
                "timestamp": base_time.isoformat() + "Z"
            },
            {
                "metric_name": "cpu_usage",
                "value": 55.0,
                "timestamp": (base_time + timedelta(minutes=1)).isoformat() + "Z"
            }
        ]

        result = _analyze_temporal_patterns(metrics)

        # Need at least 10 points to detect patterns
        assert result["patterns_detected"] == []
        assert result["metrics_analyzed"] == 1

    def test_analyze_temporal_patterns_increasing_trend(self):
        """Test detection of increasing trend."""
        base_time = datetime(2025, 1, 15, 10, 0, 0)
        metrics = []

        # Create increasing trend
        for i in range(15):
            metrics.append({
                "metric_name": "cpu_usage",
                "value": 50.0 + i * 5.0,  # Steady increase
                "timestamp": (base_time + timedelta(minutes=i)).isoformat() + "Z"
            })

        result = _analyze_temporal_patterns(metrics)

        assert result["metrics_analyzed"] == 1
        assert len(result["patterns_detected"]) == 1

        pattern = result["patterns_detected"][0]
        assert pattern["metric"] == "cpu_usage"
        assert pattern["pattern"] == "trend"
        assert pattern["direction"] == "increasing"
        assert pattern["strength"] > 0.5

    def test_analyze_temporal_patterns_decreasing_trend(self):
        """Test detection of decreasing trend."""
        base_time = datetime(2025, 1, 15, 10, 0, 0)
        metrics = []

        # Create decreasing trend
        for i in range(15):
            metrics.append({
                "metric_name": "error_rate",
                "value": 100.0 - i * 5.0,  # Steady decrease
                "timestamp": (base_time + timedelta(minutes=i)).isoformat() + "Z"
            })

        result = _analyze_temporal_patterns(metrics)

        pattern = result["patterns_detected"][0]
        assert pattern["direction"] == "decreasing"
        assert pattern["strength"] > 0.5

    def test_analyze_temporal_patterns_no_trend(self):
        """Test that stable metrics don't show trends."""
        base_time = datetime(2025, 1, 15, 10, 0, 0)
        metrics = []

        # Create stable metric (small random variations)
        np.random.seed(42)
        for i in range(15):
            metrics.append({
                "metric_name": "stable_metric",
                "value": 50.0 + np.random.random() * 2.0,  # Small variations
                "timestamp": (base_time + timedelta(minutes=i)).isoformat() + "Z"
            })

        result = _analyze_temporal_patterns(metrics)

        # Should not detect strong trend in stable data
        assert len(result["patterns_detected"]) == 0

    def test_analyze_temporal_patterns_multiple_metrics(self):
        """Test temporal pattern analysis with multiple metrics."""
        base_time = datetime(2025, 1, 15, 10, 0, 0)
        metrics = []

        # Metric 1: increasing trend
        for i in range(15):
            metrics.append({
                "metric_name": "cpu_usage",
                "value": 50.0 + i * 5.0,
                "timestamp": (base_time + timedelta(minutes=i)).isoformat() + "Z"
            })

        # Metric 2: decreasing trend
        for i in range(15):
            metrics.append({
                "metric_name": "available_memory",
                "value": 100.0 - i * 4.0,
                "timestamp": (base_time + timedelta(minutes=i)).isoformat() + "Z"
            })

        result = _analyze_temporal_patterns(metrics)

        assert result["metrics_analyzed"] == 2
        assert len(result["patterns_detected"]) == 2

    def test_analyze_temporal_patterns_invalid_timestamps(self):
        """Test temporal patterns with invalid timestamps."""
        metrics = [
            {"metric_name": "cpu_usage", "value": 50.0, "timestamp": "invalid"},
            {"metric_name": "cpu_usage", "value": 55.0, "timestamp": "also invalid"}
        ]

        result = _analyze_temporal_patterns(metrics)

        # Should handle invalid timestamps gracefully - skips all invalid data
        assert result["metrics_analyzed"] == 0 or result["patterns_detected"] == []


class TestServiceCorrelations:
    """Test service correlation analysis."""

    def test_analyze_service_correlations_empty_list(self):
        """Test service correlation with empty logs list."""
        result = _analyze_service_correlations([])

        assert result["services_analyzed"] == 0
        assert result["service_error_rates"] == []

    def test_analyze_service_correlations_single_service(self):
        """Test service correlation with single service."""
        logs = [
            {"service": "api-server", "level": "INFO"},
            {"service": "api-server", "level": "INFO"},
            {"service": "api-server", "level": "ERROR"},
            {"service": "api-server", "level": "INFO"},
        ]

        result = _analyze_service_correlations(logs)

        assert result["services_analyzed"] == 1
        assert len(result["service_error_rates"]) == 1

        service = result["service_error_rates"][0]
        assert service["service"] == "api-server"
        assert service["error_rate"] == 0.25  # 1/4
        assert service["total_logs"] == 4
        assert service["errors"] == 1

    def test_analyze_service_correlations_multiple_services(self):
        """Test service correlation with multiple services."""
        logs = [
            {"service": "api-server", "level": "INFO"},
            {"service": "api-server", "level": "ERROR"},
            {"service": "db-server", "level": "INFO"},
            {"service": "db-server", "level": "ERROR"},
            {"service": "db-server", "level": "CRITICAL"},
            {"service": "cache", "level": "INFO"},
        ]

        result = _analyze_service_correlations(logs)

        assert result["services_analyzed"] == 3
        assert len(result["service_error_rates"]) == 3

        # Should be sorted by error rate (descending)
        assert result["service_error_rates"][0]["error_rate"] >= \
               result["service_error_rates"][1]["error_rate"]

    def test_analyze_service_correlations_critical_errors(self):
        """Test that CRITICAL logs are counted as errors."""
        logs = [
            {"service": "api-server", "level": "INFO"},
            {"service": "api-server", "level": "CRITICAL"},
        ]

        result = _analyze_service_correlations(logs)

        service = result["service_error_rates"][0]
        assert service["errors"] == 1
        assert service["error_rate"] == 0.5

    def test_analyze_service_correlations_no_errors(self):
        """Test service with no errors."""
        logs = [
            {"service": "api-server", "level": "INFO"},
            {"service": "api-server", "level": "INFO"},
            {"service": "api-server", "level": "DEBUG"},
        ]

        result = _analyze_service_correlations(logs)

        service = result["service_error_rates"][0]
        assert service["errors"] == 0
        assert service["error_rate"] == 0.0

    def test_analyze_service_correlations_sorting(self):
        """Test that services are sorted by error rate."""
        logs = [
            {"service": "low-error", "level": "INFO"},
            {"service": "low-error", "level": "INFO"},
            {"service": "low-error", "level": "ERROR"},
            {"service": "high-error", "level": "ERROR"},
            {"service": "high-error", "level": "ERROR"},
        ]

        result = _analyze_service_correlations(logs)

        # high-error should be first (100% error rate)
        assert result["service_error_rates"][0]["service"] == "high-error"
        assert result["service_error_rates"][0]["error_rate"] == 1.0

        # low-error should be second (33% error rate)
        assert result["service_error_rates"][1]["service"] == "low-error"
        assert result["service_error_rates"][1]["error_rate"] == pytest.approx(0.333, 0.01)


class TestAnomalyCorrelations:
    """Test anomaly correlation analysis."""

    def test_analyze_anomaly_correlations_empty_data(self):
        """Test anomaly correlation with empty data."""
        result = _analyze_anomaly_correlations([], [])

        assert result["error_windows"] == 0
        assert result["correlated_metric_anomalies"] == 0
        assert result["correlation_rate"] == 0

    def test_analyze_anomaly_correlations_no_errors(self):
        """Test anomaly correlation with no errors."""
        base_time = datetime(2025, 1, 15, 10, 0, 0)
        logs = [
            {"level": "INFO", "timestamp": base_time.isoformat() + "Z"},
            {"level": "DEBUG", "timestamp": (base_time + timedelta(minutes=1)).isoformat() + "Z"},
        ]
        metrics = [
            {
                "metric_name": "cpu_usage",
                "value": 50.0,
                "timestamp": base_time.isoformat() + "Z"
            }
        ]

        result = _analyze_anomaly_correlations(logs, metrics)

        assert result["error_windows"] == 0
        assert result["correlated_metric_anomalies"] == 0

    def test_analyze_anomaly_correlations_correlated(self):
        """Test anomaly correlation with correlated errors and metrics."""
        base_time = datetime(2025, 1, 15, 10, 0, 0)

        # Error at 10:00
        logs = [
            {"level": "ERROR", "timestamp": base_time.isoformat() + "Z"},
        ]

        # Metric anomaly in same minute
        metrics = [
            {
                "metric_name": "cpu_usage",
                "service": "api",
                "value": 95.0,
                "timestamp": (base_time + timedelta(seconds=30)).isoformat() + "Z"
            }
        ]

        result = _analyze_anomaly_correlations(logs, metrics)

        assert result["error_windows"] == 1
        assert result["correlated_metric_anomalies"] == 1
        assert result["correlation_rate"] == 1.0

    def test_analyze_anomaly_correlations_uncorrelated(self):
        """Test anomaly correlation with uncorrelated errors and metrics."""
        base_time = datetime(2025, 1, 15, 10, 0, 0)

        # Error at 10:00
        logs = [
            {"level": "ERROR", "timestamp": base_time.isoformat() + "Z"},
        ]

        # Metric in different time window (10:05)
        metrics = [
            {
                "metric_name": "cpu_usage",
                "service": "api",
                "value": 50.0,
                "timestamp": (base_time + timedelta(minutes=5)).isoformat() + "Z"
            }
        ]

        result = _analyze_anomaly_correlations(logs, metrics)

        assert result["error_windows"] == 1
        assert result["correlated_metric_anomalies"] == 0
        assert result["correlation_rate"] == 0.0

    def test_analyze_anomaly_correlations_multiple_windows(self):
        """Test anomaly correlation with multiple error windows."""
        base_time = datetime(2025, 1, 15, 10, 0, 0)

        logs = [
            {"level": "ERROR", "timestamp": base_time.isoformat() + "Z"},
            {"level": "CRITICAL", "timestamp": (base_time + timedelta(minutes=5)).isoformat() + "Z"},
            {"level": "ERROR", "timestamp": (base_time + timedelta(minutes=10)).isoformat() + "Z"},
        ]

        metrics = [
            # Correlated with first error
            {
                "metric_name": "cpu_usage",
                "service": "api",
                "value": 95.0,
                "timestamp": base_time.isoformat() + "Z"
            },
            # Correlated with second error
            {
                "metric_name": "memory_usage",
                "service": "api",
                "value": 85.0,
                "timestamp": (base_time + timedelta(minutes=5)).isoformat() + "Z"
            },
            # Not correlated (different window)
            {
                "metric_name": "disk_usage",
                "service": "api",
                "value": 75.0,
                "timestamp": (base_time + timedelta(minutes=15)).isoformat() + "Z"
            },
        ]

        result = _analyze_anomaly_correlations(logs, metrics)

        assert result["error_windows"] == 3
        assert result["correlated_metric_anomalies"] == 2
        assert result["correlation_rate"] == pytest.approx(0.666, 0.01)

    def test_analyze_anomaly_correlations_invalid_timestamps(self):
        """Test anomaly correlation with invalid timestamps."""
        logs = [
            {"level": "ERROR", "timestamp": "invalid"},
        ]
        metrics = [
            {"metric_name": "cpu_usage", "value": 50.0, "timestamp": "invalid"}
        ]

        result = _analyze_anomaly_correlations(logs, metrics)

        # Should handle gracefully
        assert result["error_windows"] == 0
        assert result["correlated_metric_anomalies"] == 0


class TestAnalyzeCorrelations:
    """Test main analyze_correlations function."""

    def test_analyze_correlations_empty_dataset(self, tmp_path):
        """Test analysis with empty dataset directory."""
        result = analyze_correlations(tmp_path)

        assert "metric_correlations" in result
        assert "temporal_correlations" in result
        assert "service_correlations" in result
        assert "anomaly_correlations" in result

    def test_analyze_correlations_metrics_only(self, tmp_path):
        """Test analysis with metrics only."""
        metrics_dir = tmp_path / "metrics"
        metrics_dir.mkdir()

        metrics_file = metrics_dir / "cpu_usage.jsonl"
        base_time = datetime(2025, 1, 15, 10, 0, 0)

        with open(metrics_file, 'w') as f:
            for i in range(15):
                metric = {
                    "metric_name": "cpu_usage",
                    "service": "api",
                    "value": 50.0 + i * 2.0,
                    "timestamp": (base_time + timedelta(minutes=i)).isoformat() + "Z"
                }
                f.write(json.dumps(metric) + '\n')

        result = analyze_correlations(tmp_path)

        # Should have metric and temporal correlations
        assert result["metric_correlations"] != {}
        assert result["temporal_correlations"] != {}
        # But not service or anomaly correlations
        assert result["service_correlations"] == {}
        assert result["anomaly_correlations"] == {}

    def test_analyze_correlations_logs_only(self, tmp_path):
        """Test analysis with logs only."""
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()

        logs_file = logs_dir / "api-server.jsonl"
        with open(logs_file, 'w') as f:
            for level in ["INFO", "INFO", "ERROR", "INFO"]:
                log = {
                    "service": "api-server",
                    "level": level,
                    "message": "Test message",
                    "timestamp": "2025-01-15T10:00:00Z"
                }
                f.write(json.dumps(log) + '\n')

        result = analyze_correlations(tmp_path)

        # Should have service correlations
        assert result["service_correlations"] != {}
        # But not metric correlations
        assert result["metric_correlations"] == {}
        assert result["temporal_correlations"] == {}

    def test_analyze_correlations_full_dataset(self, tmp_path):
        """Test analysis with complete dataset."""
        # Create metrics
        metrics_dir = tmp_path / "metrics"
        metrics_dir.mkdir()

        base_time = datetime(2025, 1, 15, 10, 0, 0)
        metrics_file = metrics_dir / "cpu_usage.jsonl"

        with open(metrics_file, 'w') as f:
            for i in range(15):
                metric = {
                    "metric_name": "cpu_usage",
                    "service": "api",
                    "value": 50.0 + i * 2.0,
                    "timestamp": (base_time + timedelta(minutes=i)).isoformat() + "Z"
                }
                f.write(json.dumps(metric) + '\n')

        # Create logs
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()

        logs_file = logs_dir / "api-server.jsonl"
        with open(logs_file, 'w') as f:
            for i, level in enumerate(["INFO", "ERROR", "INFO", "INFO"]):
                log = {
                    "service": "api-server",
                    "level": level,
                    "message": "Test message",
                    "timestamp": (base_time + timedelta(minutes=i)).isoformat() + "Z"
                }
                f.write(json.dumps(log) + '\n')

        result = analyze_correlations(tmp_path)

        # Should have all types of correlations
        assert result["metric_correlations"] != {}
        assert result["temporal_correlations"] != {}
        assert result["service_correlations"] != {}
        assert result["anomaly_correlations"] != {}


class TestPrintCorrelationReport:
    """Test correlation report printing."""

    def test_print_correlation_report_empty(self):
        """Test printing report with empty results."""
        results = {
            "metric_correlations": {},
            "temporal_correlations": {},
            "service_correlations": {},
            "anomaly_correlations": {},
        }

        # Should not raise an exception
        print_correlation_report(results)

    def test_print_correlation_report_with_metric_correlations(self):
        """Test printing report with metric correlations."""
        results = {
            "metric_correlations": {
                "total_pairs_analyzed": 10,
                "significant_correlations": 3,
                "top_correlations": [
                    {
                        "metric1": "cpu_usage (api)",
                        "metric2": "memory_usage (api)",
                        "correlation": 0.85,
                        "strength": "very strong"
                    }
                ]
            },
            "temporal_correlations": {},
            "service_correlations": {},
            "anomaly_correlations": {},
        }

        # Should not raise an exception
        print_correlation_report(results)

    def test_print_correlation_report_with_temporal_patterns(self):
        """Test printing report with temporal patterns."""
        results = {
            "metric_correlations": {},
            "temporal_correlations": {
                "metrics_analyzed": 5,
                "patterns_detected": [
                    {
                        "metric": "cpu_usage",
                        "pattern": "trend",
                        "direction": "increasing",
                        "strength": 0.92
                    }
                ]
            },
            "service_correlations": {},
            "anomaly_correlations": {},
        }

        # Should not raise an exception
        print_correlation_report(results)

    def test_print_correlation_report_with_service_errors(self):
        """Test printing report with service error rates."""
        results = {
            "metric_correlations": {},
            "temporal_correlations": {},
            "service_correlations": {
                "services_analyzed": 3,
                "service_error_rates": [
                    {
                        "service": "api-server",
                        "error_rate": 0.15,
                        "errors": 15,
                        "total_logs": 100
                    }
                ]
            },
            "anomaly_correlations": {},
        }

        # Should not raise an exception
        print_correlation_report(results)

    def test_print_correlation_report_with_anomalies(self):
        """Test printing report with anomaly correlations."""
        results = {
            "metric_correlations": {},
            "temporal_correlations": {},
            "service_correlations": {},
            "anomaly_correlations": {
                "error_windows": 10,
                "correlated_metric_anomalies": 8,
                "correlation_rate": 0.8
            },
        }

        # Should not raise an exception
        print_correlation_report(results)

    def test_print_correlation_report_complete(self):
        """Test printing complete report with all sections."""
        results = {
            "metric_correlations": {
                "total_pairs_analyzed": 10,
                "significant_correlations": 3,
                "top_correlations": [
                    {
                        "metric1": "cpu_usage (api)",
                        "metric2": "memory_usage (api)",
                        "correlation": 0.85,
                        "strength": "very strong"
                    },
                    {
                        "metric1": "request_rate (api)",
                        "metric2": "error_rate (api)",
                        "correlation": -0.65,
                        "strength": "strong"
                    }
                ]
            },
            "temporal_correlations": {
                "metrics_analyzed": 5,
                "patterns_detected": [
                    {
                        "metric": "cpu_usage",
                        "pattern": "trend",
                        "direction": "increasing",
                        "strength": 0.92
                    }
                ]
            },
            "service_correlations": {
                "services_analyzed": 3,
                "service_error_rates": [
                    {
                        "service": "api-server",
                        "error_rate": 0.15,
                        "errors": 15,
                        "total_logs": 100
                    }
                ]
            },
            "anomaly_correlations": {
                "error_windows": 10,
                "correlated_metric_anomalies": 8,
                "correlation_rate": 0.8
            },
        }

        # Should not raise an exception
        print_correlation_report(results)

    @patch('cli.correlate.logger')
    def test_print_correlation_report_logging(self, mock_logger):
        """Test that report uses logger correctly."""
        results = {
            "metric_correlations": {
                "total_pairs_analyzed": 10,
                "significant_correlations": 3,
                "top_correlations": []
            },
            "temporal_correlations": {},
            "service_correlations": {},
            "anomaly_correlations": {},
        }

        print_correlation_report(results)

        # Verify logger.info was called
        assert mock_logger.info.called
        assert mock_logger.info.call_count > 0
