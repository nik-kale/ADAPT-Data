"""Tests for the Datadog exporter."""

import json

import pytest

from generator.exporters.datadog import DatadogExporter


@pytest.fixture
def dataset(tmp_path):
    """Build a small dataset covering metrics, logs and traces."""
    for subdir in ("metrics", "logs", "traces"):
        (tmp_path / subdir).mkdir()

    metrics = [
        {
            "timestamp": "2025-01-15T10:00:00.000000Z",
            "metric_name": "cpu_usage_percent",
            "value": 40.0,
            "service": "api",
            "metric_type": "gauge",
            "unit": "percent",
            "host": "api-000",
            "tags": {"correlation_id": "corr-1", "endpoint": "/x"},
        },
        {
            "timestamp": "2025-01-15T10:01:00.000000Z",
            "metric_name": "cpu_usage_percent",
            "value": 55.0,
            "service": "api",
            "metric_type": "gauge",
            "unit": "percent",
            "host": "api-000",
            "tags": {"correlation_id": "corr-2", "endpoint": "/x"},
        },
        {
            "timestamp": "2025-01-15T10:00:00.000000Z",
            "metric_name": "requests_total",
            "value": 12,
            "service": "api",
            "metric_type": "counter",
            "host": "api-000",
            "tags": {},
        },
    ]
    (tmp_path / "metrics" / "m.jsonl").write_text("\n".join(json.dumps(m) for m in metrics) + "\n")

    logs = [
        {
            "timestamp": "2025-01-15T10:00:00.000000Z",
            "level": "ERROR",
            "service": "api",
            "host": "api-000",
            "message": "boom",
            "trace_id": "trace-abc",
            "correlation_id": "corr-1",
            "metadata": {"status_code": 500},
        },
        {
            "timestamp": "2025-01-15T10:00:05.000000Z",
            "level": "INFO",
            "service": "api",
            "host": "api-000",
            "message": "ok",
        },
    ]
    (tmp_path / "logs" / "l.jsonl").write_text("\n".join(json.dumps(x) for x in logs) + "\n")

    traces = [
        {
            "trace_id": "trace-abc",
            "timestamp": "2025-01-15T10:00:00.000000Z",
            "correlation_id": "corr-1",
            "spans": [
                {
                    "span_id": "span-1",
                    "parent_span_id": None,
                    "service": "api",
                    "operation": "GET /x",
                    "start_time": "2025-01-15T10:00:00.000000Z",
                    "duration_ms": 12.5,
                    "status": "OK",
                    "tags": {"http.method": "GET"},
                },
                {
                    "span_id": "span-2",
                    "parent_span_id": "span-1",
                    "service": "db",
                    "operation": "SELECT",
                    "start_time": "2025-01-15T10:00:00.005000Z",
                    "duration_ms": 5.0,
                    "status": "ERROR",
                },
            ],
        }
    ]
    (tmp_path / "traces" / "t.jsonl").write_text("\n".join(json.dumps(x) for x in traces) + "\n")

    return tmp_path


class TestExportMetrics:
    """Test the metrics payload."""

    def test_produces_series_payload(self, dataset, tmp_path):
        """Output matches Datadog's series envelope."""
        out = tmp_path / "dd_metrics.json"
        DatadogExporter(dataset).export_metrics(out)

        payload = json.loads(out.read_text())
        assert "series" in payload
        assert {s["metric"] for s in payload["series"]} == {
            "cpu_usage_percent",
            "requests_total",
        }

    def test_folds_samples_into_one_series(self, dataset, tmp_path):
        """Samples sharing name, service and tags become one multi-point series.

        Correlation IDs are per-event, so leaving them in metric tags would make
        every point its own series.
        """
        out = tmp_path / "dd_metrics.json"
        DatadogExporter(dataset).export_metrics(out)

        payload = json.loads(out.read_text())
        cpu = next(s for s in payload["series"] if s["metric"] == "cpu_usage_percent")

        assert len(cpu["points"]) == 2

    def test_drops_high_cardinality_tags(self, dataset, tmp_path):
        """Per-event IDs never reach metric tags."""
        out = tmp_path / "dd_metrics.json"
        DatadogExporter(dataset).export_metrics(out)

        payload = json.loads(out.read_text())
        all_tags = [tag for s in payload["series"] for tag in s["tags"]]

        assert not any(tag.startswith("correlation_id:") for tag in all_tags)
        assert "endpoint:/x" in all_tags

    def test_maps_metric_types(self, dataset, tmp_path):
        """Counters and gauges map to Datadog's type codes."""
        out = tmp_path / "dd_metrics.json"
        DatadogExporter(dataset).export_metrics(out)

        payload = json.loads(out.read_text())
        by_name = {s["metric"]: s for s in payload["series"]}

        assert by_name["cpu_usage_percent"]["type"] == 3  # gauge
        assert by_name["requests_total"]["type"] == 1  # count

    def test_applies_service_prefix(self, dataset, tmp_path):
        """The prefix keeps synthetic data separable from real telemetry."""
        out = tmp_path / "dd_metrics.json"
        DatadogExporter(dataset, service_prefix="synthetic.").export_metrics(out)

        payload = json.loads(out.read_text())
        assert all("service:synthetic.api" in s["tags"] for s in payload["series"])

    def test_raises_when_no_metrics_directory(self, tmp_path):
        """A missing directory is reported, not silently ignored."""
        with pytest.raises(ValueError, match="not found"):
            DatadogExporter(tmp_path).export_metrics(tmp_path / "out.json")


class TestExportLogs:
    """Test the logs payload."""

    def test_maps_levels_to_status(self, dataset, tmp_path):
        """ADAPT levels map onto Datadog log statuses."""
        out = tmp_path / "dd_logs.json"
        DatadogExporter(dataset).export_logs(out)

        entries = json.loads(out.read_text())
        assert {e["status"] for e in entries} == {"error", "info"}

    def test_uses_numeric_trace_ids_for_apm_join(self, dataset, tmp_path):
        """dd.trace_id must match the ID the trace export emits."""
        logs_out, traces_out = tmp_path / "l.json", tmp_path / "t.json"
        exporter = DatadogExporter(dataset)
        exporter.export_logs(logs_out)
        exporter.export_traces(traces_out)

        entry = next(e for e in json.loads(logs_out.read_text()) if "dd.trace_id" in e)
        span_trace_ids = {s["trace_id"] for t in json.loads(traces_out.read_text()) for s in t}

        assert int(entry["dd.trace_id"]) in span_trace_ids
        assert entry["adapt.trace_id"] == "trace-abc"

    def test_preserves_metadata_as_attributes(self, dataset, tmp_path):
        """Structured metadata survives as Datadog attributes."""
        out = tmp_path / "dd_logs.json"
        DatadogExporter(dataset).export_logs(out)

        entry = next(e for e in json.loads(out.read_text()) if e["message"] == "boom")
        assert entry["attributes"]["status_code"] == 500


class TestExportTraces:
    """Test the APM trace payload."""

    def test_groups_spans_per_trace(self, dataset, tmp_path):
        """Each trace becomes one list of spans."""
        out = tmp_path / "dd_traces.json"
        DatadogExporter(dataset).export_traces(out)

        payload = json.loads(out.read_text())
        assert len(payload) == 1
        assert len(payload[0]) == 2

    def test_ids_are_64_bit_integers(self, dataset, tmp_path):
        """Datadog requires unsigned 64-bit IDs."""
        out = tmp_path / "dd_traces.json"
        DatadogExporter(dataset).export_traces(out)

        for span in json.loads(out.read_text())[0]:
            assert isinstance(span["trace_id"], int)
            assert 0 <= span["trace_id"] < 2**64
            assert 0 <= span["span_id"] < 2**64

    def test_root_span_has_zero_parent(self, dataset, tmp_path):
        """A null parent maps to Datadog's 0 sentinel."""
        out = tmp_path / "dd_traces.json"
        DatadogExporter(dataset).export_traces(out)

        root = next(s for s in json.loads(out.read_text())[0] if s["name"] == "GET /x")
        assert root["parent_id"] == 0

    def test_child_span_points_at_parent(self, dataset, tmp_path):
        """Parent links are preserved through ID hashing."""
        out = tmp_path / "dd_traces.json"
        DatadogExporter(dataset).export_traces(out)

        spans = {s["name"]: s for s in json.loads(out.read_text())[0]}
        assert spans["SELECT"]["parent_id"] == spans["GET /x"]["span_id"]

    def test_marks_error_spans(self, dataset, tmp_path):
        """ERROR status becomes Datadog's error flag."""
        out = tmp_path / "dd_traces.json"
        DatadogExporter(dataset).export_traces(out)

        spans = {s["name"]: s for s in json.loads(out.read_text())[0]}
        assert spans["SELECT"]["error"] == 1
        assert spans["GET /x"]["error"] == 0

    def test_converts_duration_to_nanoseconds(self, dataset, tmp_path):
        """Durations are reported in nanoseconds."""
        out = tmp_path / "dd_traces.json"
        DatadogExporter(dataset).export_traces(out)

        spans = {s["name"]: s for s in json.loads(out.read_text())[0]}
        assert spans["GET /x"]["duration"] == int(12.5 * 1e6)

    def test_id_hashing_is_deterministic(self):
        """The same identifier always maps to the same Datadog ID."""
        assert DatadogExporter._to_dd_id("abc") == DatadogExporter._to_dd_id("abc")
        assert DatadogExporter._to_dd_id("abc") != DatadogExporter._to_dd_id("abd")


class TestExportAll:
    """Test the combined export."""

    def test_writes_three_payloads(self, dataset, tmp_path):
        """Metrics, logs and traces each get a file."""
        written = DatadogExporter(dataset).export_all(tmp_path / "dd")

        assert set(written) == {"metrics", "logs", "traces"}
        assert all(path.exists() for path in written.values())

    def test_continues_when_one_signal_is_missing(self, dataset, tmp_path):
        """A dataset without traces still exports metrics and logs."""
        for trace_file in (dataset / "traces").glob("*.jsonl"):
            trace_file.unlink()

        written = DatadogExporter(dataset).export_all(tmp_path / "dd")

        assert set(written) == {"metrics", "logs"}

    def test_raises_when_nothing_exportable(self, tmp_path):
        """An empty dataset directory is an error."""
        with pytest.raises(ValueError, match="No exportable data"):
            DatadogExporter(tmp_path).export_all(tmp_path / "dd")
