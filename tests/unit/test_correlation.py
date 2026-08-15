"""Tests for correlation ID propagation."""

import random

import pytest

from generator.core.correlation import (
    CORRELATION_KEY,
    CorrelationGenerator,
    CorrelationScope,
)


class TestCorrelationScope:
    """Test stamping records with correlation identifiers."""

    def test_create_generates_distinct_ids(self):
        """Each scope gets its own identifiers."""
        first, second = CorrelationScope.create(), CorrelationScope.create()

        assert first.correlation_id != second.correlation_id
        assert first.trace_id != second.trace_id
        assert first.request_id != second.request_id

    def test_stamp_log_sets_correlation_and_trace(self):
        """A log gains the correlation ID, trace ID and request ID."""
        scope = CorrelationScope.create()
        log = {"message": "hello"}

        scope.stamp_log(log)

        assert log[CORRELATION_KEY] == scope.correlation_id
        assert log["trace_id"] == scope.trace_id
        assert log["metadata"]["request_id"] == scope.request_id

    def test_stamp_log_preserves_existing_trace_id(self):
        """An explicit trace ID is not overwritten."""
        scope = CorrelationScope.create()
        log = {"message": "hello", "trace_id": "pre-existing"}

        scope.stamp_log(log)

        assert log["trace_id"] == "pre-existing"
        assert log[CORRELATION_KEY] == scope.correlation_id

    def test_stamp_log_preserves_existing_metadata(self):
        """Stamping merges into metadata rather than replacing it."""
        scope = CorrelationScope.create()
        log = {"message": "hello", "metadata": {"status_code": 200}}

        scope.stamp_log(log)

        assert log["metadata"]["status_code"] == 200
        assert log["metadata"]["request_id"] == scope.request_id

    def test_stamp_metric_writes_into_tags(self):
        """Metrics carry the ID in tags, where the schema allows it."""
        scope = CorrelationScope.create()
        metric = {"metric_name": "cpu", "value": 1.0}

        scope.stamp_metric(metric)

        assert metric["tags"][CORRELATION_KEY] == scope.correlation_id

    def test_stamp_metric_preserves_existing_tags(self):
        """Existing tags survive stamping."""
        scope = CorrelationScope.create()
        metric = {"metric_name": "cpu", "tags": {"endpoint": "/api"}}

        scope.stamp_metric(metric)

        assert metric["tags"]["endpoint"] == "/api"
        assert metric["tags"][CORRELATION_KEY] == scope.correlation_id

    def test_stamp_trace_covers_trace_and_every_span(self):
        """The ID reaches the trace and each of its spans."""
        scope = CorrelationScope.create()
        trace = {
            "trace_id": "t1",
            "spans": [
                {"span_id": "s1"},
                {"span_id": "s2", "tags": {"existing": "value"}},
            ],
        }

        scope.stamp_trace(trace)

        assert trace[CORRELATION_KEY] == scope.correlation_id
        for span in trace["spans"]:
            assert span["tags"][CORRELATION_KEY] == scope.correlation_id
        assert trace["spans"][1]["tags"]["existing"] == "value"

    def test_stamp_trace_handles_missing_spans(self):
        """A trace with no spans key does not raise."""
        scope = CorrelationScope.create()
        trace = {"trace_id": "t1"}

        scope.stamp_trace(trace)

        assert trace[CORRELATION_KEY] == scope.correlation_id

    def test_joins_records_across_telemetry_types(self):
        """One scope makes a log, metric and trace mutually joinable."""
        scope = CorrelationScope.create()
        log, metric = {"message": "m"}, {"metric_name": "cpu"}
        trace = {"trace_id": "t1", "spans": [{"span_id": "s1"}]}

        scope.stamp_log(log)
        scope.stamp_metric(metric)
        scope.stamp_trace(trace)

        assert log[CORRELATION_KEY] == metric["tags"][CORRELATION_KEY] == trace[CORRELATION_KEY]


class TestCorrelationGenerator:
    """Test density-controlled scope creation."""

    def test_full_density_always_returns_a_scope(self):
        """density=1.0 correlates every event."""
        generator = CorrelationGenerator(density=1.0)

        assert all(generator.new_scope() is not None for _ in range(50))

    def test_zero_density_never_returns_a_scope(self):
        """density=0.0 leaves every event uncorrelated."""
        generator = CorrelationGenerator(density=0.0)

        assert all(generator.new_scope() is None for _ in range(50))

    def test_partial_density_correlates_roughly_that_fraction(self):
        """density=0.5 correlates about half the events."""
        random.seed(42)
        generator = CorrelationGenerator(density=0.5)

        correlated = sum(generator.new_scope() is not None for _ in range(1000))

        assert 400 < correlated < 600

    def test_new_scope_always_ignores_density(self):
        """Records that must be joinable get a scope regardless of density."""
        generator = CorrelationGenerator(density=0.0)

        assert generator.new_scope_always() is not None

    def test_counts_scopes_created(self):
        """The counter tracks scopes actually handed out."""
        generator = CorrelationGenerator(density=1.0)
        for _ in range(7):
            generator.new_scope()

        assert generator.scopes_created == 7

    @pytest.mark.parametrize("density", [-0.1, 1.1, 2.0])
    def test_rejects_out_of_range_density(self, density):
        """Densities outside [0, 1] are rejected up front."""
        with pytest.raises(ValueError, match="density"):
            CorrelationGenerator(density=density)
