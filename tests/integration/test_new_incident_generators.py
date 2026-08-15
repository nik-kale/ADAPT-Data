"""Integration tests for the memory leak and deadlock generators."""

import json
from datetime import datetime, timedelta

import pytest

from generator.core.base import IncidentContext
from generator.core.topology import TopologyGenerator
from generator.incidents.deadlock import DeadlockGenerator
from generator.incidents.memory_leak import MemoryLeakGenerator


@pytest.fixture
def context(tmp_path):
    """Incident context with a generated topology."""
    ctx = IncidentContext(
        incident_id="test-incident",
        start_time=datetime(2025, 1, 15, 10, 0, 0),
        duration=timedelta(minutes=30),
        severity="SEV2",
        output_dir=tmp_path,
    )
    ctx.topology = TopologyGenerator(ctx).generate()
    return ctx


def read_jsonl(path):
    """Read a JSONL file into a list."""
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


class TestMemoryLeakGenerator:
    """Test the memory leak incident."""

    def test_generates_all_telemetry_types(self, context, tmp_path):
        """Logs, metrics, traces, config deltas and a timeline are produced."""
        result = MemoryLeakGenerator(context, affected_service="order-service").generate()

        assert result["incident_type"] == "memory_leak"
        assert result["log_count"] > 0
        assert result["metric_count"] > 0
        assert result["trace_count"] > 0

        for subdir in ("logs", "metrics", "traces", "config_deltas", "timelines"):
            assert list((tmp_path / subdir).glob("*")), f"{subdir} is empty"

    def test_memory_climbs_over_time(self, context, tmp_path):
        """The defining signal: heap grows steadily rather than spiking."""
        MemoryLeakGenerator(
            context,
            affected_service="order-service",
            initial_memory_mb=512.0,
            leak_rate_mb_per_min=20.0,
            max_memory_mb=4096.0,
            restart_on_oom=False,
        ).generate()

        metrics = read_jsonl(next((tmp_path / "metrics").glob("*.jsonl")))
        memory = [m for m in metrics if m["metric_name"] == "process_memory_usage_bytes"]
        memory.sort(key=lambda m: m["timestamp"])

        assert memory[-1]["value"] > memory[0]["value"]

    def test_memory_never_exceeds_limit(self, context, tmp_path):
        """Reported memory stays within the container limit."""
        max_memory_mb = 1024.0
        MemoryLeakGenerator(
            context,
            affected_service="order-service",
            initial_memory_mb=512.0,
            leak_rate_mb_per_min=100.0,
            max_memory_mb=max_memory_mb,
        ).generate()

        metrics = read_jsonl(next((tmp_path / "metrics").glob("*.jsonl")))
        memory = [m for m in metrics if m["metric_name"] == "process_memory_usage_bytes"]

        assert memory
        assert all(m["value"] <= max_memory_mb * 1024 * 1024 for m in memory)

    def test_gc_degrades_with_memory_pressure(self, context, tmp_path):
        """GC pause time rises as headroom shrinks."""
        MemoryLeakGenerator(
            context,
            affected_service="order-service",
            initial_memory_mb=512.0,
            leak_rate_mb_per_min=50.0,
            max_memory_mb=2048.0,
            restart_on_oom=False,
        ).generate()

        metrics = read_jsonl(next((tmp_path / "metrics").glob("*.jsonl")))
        pauses = [m for m in metrics if m["metric_name"] == "gc_pause_duration_ms"]
        pauses.sort(key=lambda m: m["timestamp"])

        assert pauses[-1]["value"] > pauses[0]["value"]

    def test_emits_oom_kill_when_limit_reached(self, context, tmp_path):
        """A fast leak produces an OOMKilled log."""
        MemoryLeakGenerator(
            context,
            affected_service="order-service",
            initial_memory_mb=512.0,
            leak_rate_mb_per_min=200.0,
            max_memory_mb=1024.0,
        ).generate()

        logs = read_jsonl(next((tmp_path / "logs").glob("*.jsonl")))

        assert any(log["metadata"].get("error_code") == "OOM_KILLED" for log in logs)

    def test_no_oom_when_leak_too_slow(self, context, tmp_path):
        """A leak that never reaches the limit produces no OOM kill."""
        MemoryLeakGenerator(
            context,
            affected_service="order-service",
            initial_memory_mb=512.0,
            leak_rate_mb_per_min=0.5,
            max_memory_mb=8192.0,
        ).generate()

        logs = read_jsonl(next((tmp_path / "logs").glob("*.jsonl")))

        assert not any(log["metadata"].get("error_code") == "OOM_KILLED" for log in logs)

    def test_logs_are_chronological(self, context, tmp_path):
        """Log timestamps are monotonic, as validation requires."""
        MemoryLeakGenerator(context, affected_service="order-service").generate()

        logs = read_jsonl(next((tmp_path / "logs").glob("*.jsonl")))
        timestamps = [log["timestamp"] for log in logs]

        assert timestamps == sorted(timestamps)

    def test_sets_root_cause_and_affected_services(self, context):
        """Context is updated for downstream consumers."""
        MemoryLeakGenerator(context, affected_service="order-service")

        assert context.affected_services == ["order-service"]
        assert "memory leak" in context.root_cause.lower()

    def test_rejects_limit_below_initial_memory(self, context):
        """A limit under the starting usage cannot leak."""
        with pytest.raises(ValueError, match="max_memory_mb"):
            MemoryLeakGenerator(context, initial_memory_mb=2048.0, max_memory_mb=512.0)

    def test_rejects_non_positive_leak_rate(self, context):
        """A zero leak rate would never produce an incident."""
        with pytest.raises(ValueError, match="leak_rate_mb_per_min"):
            MemoryLeakGenerator(context, leak_rate_mb_per_min=0)


class TestDeadlockGenerator:
    """Test the database deadlock incident."""

    def test_generates_all_telemetry_types(self, context, tmp_path):
        """Every telemetry type is produced."""
        result = DeadlockGenerator(context, affected_service="order-service").generate()

        assert result["incident_type"] == "deadlock"
        assert result["log_count"] > 0
        assert result["metric_count"] > 0

        for subdir in ("logs", "metrics", "traces", "config_deltas", "timelines"):
            assert list((tmp_path / subdir).glob("*")), f"{subdir} is empty"

    def test_emits_postgres_deadlock_code(self, context, tmp_path):
        """Postgres deadlocks report SQLSTATE 40P01."""
        DeadlockGenerator(
            context,
            affected_service="order-service",
            deadlock_frequency=1.0,
            dialect="postgres",
        ).generate()

        logs = read_jsonl(next((tmp_path / "logs").glob("*.jsonl")))

        assert any(log["metadata"].get("error_code") == "40P01" for log in logs)

    def test_emits_mysql_deadlock_code(self, context, tmp_path):
        """MySQL deadlocks report error 1213."""
        DeadlockGenerator(
            context,
            affected_service="order-service",
            deadlock_frequency=1.0,
            dialect="mysql",
        ).generate()

        logs = read_jsonl(next((tmp_path / "logs").glob("*.jsonl")))

        assert any(log["metadata"].get("error_code") == "1213" for log in logs)

    def test_logs_both_application_and_database_sides(self, context, tmp_path):
        """A deadlock is visible from the app and the database."""
        DeadlockGenerator(
            context,
            affected_service="order-service",
            database_service="postgres-primary",
            deadlock_frequency=1.0,
        ).generate()

        logs = read_jsonl(next((tmp_path / "logs").glob("*.jsonl")))
        services = {log["service"] for log in logs}

        assert {"order-service", "postgres-primary"} <= services

    def test_no_deadlocks_at_zero_frequency(self, context, tmp_path):
        """Frequency 0 produces clean traffic only."""
        DeadlockGenerator(
            context, affected_service="order-service", deadlock_frequency=0.0
        ).generate()

        logs = read_jsonl(next((tmp_path / "logs").glob("*.jsonl")))

        assert not any(log["metadata"].get("error_code") == "40P01" for log in logs)

    def test_deadlock_metrics_only_flagged_during_incident(self, context, tmp_path):
        """Baseline windows carry no injected anomalies."""
        DeadlockGenerator(
            context, affected_service="order-service", deadlock_frequency=0.5
        ).generate()

        metrics = read_jsonl(next((tmp_path / "metrics").glob("*.jsonl")))
        deadlock_metrics = [m for m in metrics if m["metric_name"] == "db_deadlocks_per_minute"]

        assert any(m["anomaly_injected"] for m in deadlock_metrics)
        assert any(not m["anomaly_injected"] for m in deadlock_metrics)

    def test_rejects_unsupported_dialect(self, context):
        """Only the supported dialects are accepted."""
        with pytest.raises(ValueError, match="dialect"):
            DeadlockGenerator(context, dialect="oracle")

    def test_rejects_single_table(self, context):
        """A lock cycle needs at least two tables."""
        with pytest.raises(ValueError, match="at least 2 tables"):
            DeadlockGenerator(context, affected_tables=["orders"])

    @pytest.mark.parametrize("frequency", [-0.1, 1.5])
    def test_rejects_out_of_range_frequency(self, context, frequency):
        """Frequency is a probability."""
        with pytest.raises(ValueError, match="deadlock_frequency"):
            DeadlockGenerator(context, deadlock_frequency=frequency)


class TestCorrelationInGeneratedData:
    """Correlation IDs must actually join records across telemetry types."""

    def test_correlation_ids_appear_across_types(self, context, tmp_path):
        """Logs, metrics and traces all carry correlation IDs."""
        MemoryLeakGenerator(
            context, affected_service="order-service", correlation_density=1.0
        ).generate()

        logs = read_jsonl(next((tmp_path / "logs").glob("*.jsonl")))
        metrics = read_jsonl(next((tmp_path / "metrics").glob("*.jsonl")))
        traces = read_jsonl(next((tmp_path / "traces").glob("*.jsonl")))

        assert any("correlation_id" in log for log in logs)
        assert any("correlation_id" in m.get("tags", {}) for m in metrics)
        assert any("correlation_id" in t for t in traces)

    def test_zero_density_disables_correlation(self, context, tmp_path):
        """density=0 leaves generated records uncorrelated."""
        MemoryLeakGenerator(
            context, affected_service="order-service", correlation_density=0.0
        ).generate()

        metrics = read_jsonl(next((tmp_path / "metrics").glob("*.jsonl")))

        assert not any("correlation_id" in m.get("tags", {}) for m in metrics)

    def test_spans_share_their_trace_correlation_id(self, context, tmp_path):
        """A span found alone still points back to its event."""
        DeadlockGenerator(
            context, affected_service="order-service", correlation_density=1.0
        ).generate()

        traces = read_jsonl(next((tmp_path / "traces").glob("*.jsonl")))
        trace = next(t for t in traces if "correlation_id" in t)

        assert all(
            span["tags"]["correlation_id"] == trace["correlation_id"] for span in trace["spans"]
        )
