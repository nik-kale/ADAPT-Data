"""Integration tests for incident generators."""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from generator.core.base import IncidentContext
from generator.core.topology import TopologyGenerator
from generator.incidents.latency_regression import LatencyRegressionGenerator
from generator.incidents.auth_failure import AuthFailureGenerator
from generator.incidents.dependency_outage import DependencyOutageGenerator


class TestLatencyRegressionGenerator:
    """Test latency regression incident generation."""

    def test_generates_all_data_types(self, temp_output_dir):
        """Test that all data types are generated."""
        context = IncidentContext(
            start_time=datetime.utcnow(),
            duration=timedelta(minutes=30),
            severity="SEV3",
            output_dir=temp_output_dir
        )

        # Generate topology
        topo_gen = TopologyGenerator(context)
        context.topology = topo_gen.generate()

        # Generate incident
        generator = LatencyRegressionGenerator(
            context,
            affected_service="order-service",
            baseline_latency_ms=50.0,
            degraded_latency_ms=400.0
        )
        result = generator.generate()

        # Check all files exist
        assert (temp_output_dir / "logs").exists()
        assert (temp_output_dir / "metrics").exists()
        assert (temp_output_dir / "traces").exists()
        assert (temp_output_dir / "config_deltas").exists()
        assert (temp_output_dir / "timelines").exists()
        assert (temp_output_dir / "topology").exists()

        # Check result summary
        assert result["incident_type"] == "latency_regression"
        assert result["log_count"] > 0
        assert result["metric_count"] > 0
        assert result["trace_count"] > 0

    def test_logs_conform_to_schema(self, temp_output_dir, load_schema):
        """Test that generated logs conform to schema."""
        import jsonschema

        context = IncidentContext(
            start_time=datetime.utcnow(),
            duration=timedelta(minutes=10),
            severity="SEV3",
            output_dir=temp_output_dir
        )

        topo_gen = TopologyGenerator(context)
        context.topology = topo_gen.generate()

        generator = LatencyRegressionGenerator(context)
        generator.generate()

        # Load schema
        schema = load_schema("log_schema.json")

        # Validate logs
        log_files = list((temp_output_dir / "logs").glob("*.jsonl"))
        assert len(log_files) > 0

        with open(log_files[0]) as f:
            for line in f:
                log_entry = json.loads(line)
                jsonschema.validate(instance=log_entry, schema=schema)

    def test_metrics_conform_to_schema(self, temp_output_dir, load_schema):
        """Test that generated metrics conform to schema."""
        import jsonschema

        context = IncidentContext(
            start_time=datetime.utcnow(),
            duration=timedelta(minutes=10),
            severity="SEV3",
            output_dir=temp_output_dir
        )

        topo_gen = TopologyGenerator(context)
        context.topology = topo_gen.generate()

        generator = LatencyRegressionGenerator(context)
        generator.generate()

        schema = load_schema("metric_schema.json")

        metric_files = list((temp_output_dir / "metrics").glob("*.jsonl"))
        assert len(metric_files) > 0

        with open(metric_files[0]) as f:
            for line in f:
                metric = json.loads(line)
                jsonschema.validate(instance=metric, schema=schema)

    def test_timeline_has_chronological_events(self, temp_output_dir):
        """Test that timeline events are in chronological order."""
        context = IncidentContext(
            start_time=datetime.utcnow(),
            duration=timedelta(minutes=30),
            severity="SEV3",
            output_dir=temp_output_dir
        )

        topo_gen = TopologyGenerator(context)
        context.topology = topo_gen.generate()

        generator = LatencyRegressionGenerator(context)
        generator.generate()

        # Load timeline
        timeline_files = list((temp_output_dir / "timelines").glob("*.json"))
        assert len(timeline_files) > 0

        with open(timeline_files[0]) as f:
            timeline = json.load(f)

        # Check events are chronological
        events = timeline["events"]
        timestamps = [e["timestamp"] for e in events]

        assert timestamps == sorted(timestamps)


class TestAuthFailureGenerator:
    """Test auth failure incident generation."""

    def test_generates_auth_errors(self, temp_output_dir):
        """Test that auth errors are generated."""
        context = IncidentContext(
            start_time=datetime.utcnow(),
            duration=timedelta(minutes=20),
            severity="SEV2",
            output_dir=temp_output_dir
        )

        topo_gen = TopologyGenerator(context)
        context.topology = topo_gen.generate()

        generator = AuthFailureGenerator(context)
        result = generator.generate()

        assert result["incident_type"] == "auth_failure_spike"
        assert result["log_count"] > 0

    def test_error_rate_metric_present(self, temp_output_dir):
        """Test that error rate metrics are generated."""
        context = IncidentContext(
            start_time=datetime.utcnow(),
            duration=timedelta(minutes=10),
            severity="SEV2",
            output_dir=temp_output_dir
        )

        topo_gen = TopologyGenerator(context)
        context.topology = topo_gen.generate()

        generator = AuthFailureGenerator(context)
        generator.generate()

        # Check for error rate metrics
        metric_files = list((temp_output_dir / "metrics").glob("*.jsonl"))

        error_rate_found = False
        with open(metric_files[0]) as f:
            for line in f:
                metric = json.loads(line)
                if metric["metric_name"] == "auth_error_rate":
                    error_rate_found = True
                    break

        assert error_rate_found


class TestDependencyOutageGenerator:
    """Test dependency outage incident generation."""

    def test_affects_multiple_services(self, temp_output_dir):
        """Test that multiple services are affected."""
        context = IncidentContext(
            start_time=datetime.utcnow(),
            duration=timedelta(minutes=30),
            severity="SEV1",
            output_dir=temp_output_dir
        )

        topo_gen = TopologyGenerator(context)
        context.topology = topo_gen.generate()

        generator = DependencyOutageGenerator(
            context,
            failed_service="postgres-primary",
            dependent_services=["user-service", "order-service"]
        )
        result = generator.generate()

        assert result["incident_type"] == "dependency_outage"
        assert result["failed_service"] == "postgres-primary"
        assert len(result["affected_services"]) == 2

    def test_generates_timeout_traces(self, temp_output_dir):
        """Test that timeout traces are generated."""
        context = IncidentContext(
            start_time=datetime.utcnow(),
            duration=timedelta(minutes=15),
            severity="SEV1",
            output_dir=temp_output_dir
        )

        topo_gen = TopologyGenerator(context)
        context.topology = topo_gen.generate()

        generator = DependencyOutageGenerator(context)
        generator.generate()

        # Check for timeout status in traces
        trace_files = list((temp_output_dir / "traces").glob("*.jsonl"))

        timeout_found = False
        with open(trace_files[0]) as f:
            for line in f:
                trace = json.loads(line)
                for span in trace["spans"]:
                    if span.get("status") == "TIMEOUT":
                        timeout_found = True
                        break

        assert timeout_found


class TestGeneratorDataQuality:
    """Test data quality across all generators."""

    @pytest.mark.parametrize("generator_class,params", [
        (LatencyRegressionGenerator, {}),
        (AuthFailureGenerator, {}),
        (DependencyOutageGenerator, {}),
    ])
    def test_no_missing_timestamps(self, temp_output_dir, generator_class, params):
        """Test that all generated data has timestamps."""
        context = IncidentContext(
            start_time=datetime.utcnow(),
            duration=timedelta(minutes=10),
            severity="SEV3",
            output_dir=temp_output_dir
        )

        topo_gen = TopologyGenerator(context)
        context.topology = topo_gen.generate()

        generator = generator_class(context, **params)
        generator.generate()

        # Check logs
        log_files = list((temp_output_dir / "logs").glob("*.jsonl"))
        with open(log_files[0]) as f:
            for line in f:
                log_entry = json.loads(line)
                assert "timestamp" in log_entry
                assert log_entry["timestamp"]  # Not empty

    @pytest.mark.parametrize("generator_class,params", [
        (LatencyRegressionGenerator, {}),
        (AuthFailureGenerator, {}),
    ])
    def test_metrics_have_anomaly_flag(self, temp_output_dir, generator_class, params):
        """Test that metrics have anomaly_injected flag."""
        context = IncidentContext(
            start_time=datetime.utcnow(),
            duration=timedelta(minutes=10),
            severity="SEV3",
            output_dir=temp_output_dir
        )

        topo_gen = TopologyGenerator(context)
        context.topology = topo_gen.generate()

        generator = generator_class(context, **params)
        generator.generate()

        # Check metrics have anomaly flag
        metric_files = list((temp_output_dir / "metrics").glob("*.jsonl"))

        has_true = False
        has_false = False

        with open(metric_files[0]) as f:
            for line in f:
                metric = json.loads(line)
                if "anomaly_injected" in metric:
                    if metric["anomaly_injected"]:
                        has_true = True
                    else:
                        has_false = True

        # Should have both true and false (before/during/after incident)
        assert has_true
        assert has_false
