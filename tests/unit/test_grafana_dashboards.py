"""Tests for Grafana dashboard generation."""

import json
import re
from pathlib import Path

import pytest

from generator.exporters.grafana import (
    DASHBOARD_SPECS,
    OVERVIEW_SPEC,
    GrafanaDashboardBuilder,
)

INCIDENTS_DIR = Path(__file__).parent.parent.parent / "generator" / "incidents"


@pytest.fixture
def builder():
    """Dashboard builder with the default datasource."""
    return GrafanaDashboardBuilder()


@pytest.fixture(scope="module")
def emitted_metrics():
    """Metric names found across the incident generators."""
    names = set()
    for source in INCIDENTS_DIR.glob("*.py"):
        names.update(re.findall(r'"metric_name":\s*"([a-z0-9_]+)"', source.read_text()))
    return names


class TestDashboardStructure:
    """Test the generated dashboard objects."""

    @pytest.mark.parametrize("spec", DASHBOARD_SPECS, ids=lambda s: s.slug)
    def test_dashboard_has_required_fields(self, builder, spec):
        """Grafana requires uid, title, schemaVersion and panels."""
        dashboard = builder.build(spec)

        assert dashboard["uid"]
        assert dashboard["title"]
        assert dashboard["schemaVersion"]
        assert dashboard["panels"]

    def test_panel_ids_are_unique(self, builder):
        """Duplicate panel IDs break Grafana rendering."""
        for spec in (*DASHBOARD_SPECS, OVERVIEW_SPEC):
            ids = [panel["id"] for panel in builder.build(spec)["panels"]]
            assert len(ids) == len(set(ids)), f"{spec.slug} has duplicate panel ids"

    def test_panels_query_the_configured_datasource(self):
        """Panels point at the datasource the builder was given."""
        dashboard = GrafanaDashboardBuilder(datasource_uid="my-prom").build(DASHBOARD_SPECS[0])

        for panel in dashboard["panels"]:
            assert panel["datasource"]["uid"] == "my-prom"
            for target in panel["targets"]:
                assert target["datasource"]["uid"] == "my-prom"

    def test_every_panel_has_targets(self, builder):
        """A panel with no query renders empty."""
        for spec in (*DASHBOARD_SPECS, OVERVIEW_SPEC):
            for panel in builder.build(spec)["panels"]:
                assert panel["targets"], f"{spec.slug}/{panel['title']} has no targets"

    def test_target_ref_ids_are_unique_per_panel(self, builder):
        """Grafana keys targets by refId within a panel."""
        for spec in (*DASHBOARD_SPECS, OVERVIEW_SPEC):
            for panel in builder.build(spec)["panels"]:
                ref_ids = [t["refId"] for t in panel["targets"]]
                assert len(ref_ids) == len(set(ref_ids))

    def test_dashboard_uids_are_unique(self, builder):
        """Colliding UIDs overwrite each other on import."""
        uids = [d["uid"] for d in builder.build_all().values()]

        assert len(uids) == len(set(uids))

    def test_service_template_variable_is_present(self, builder):
        """Dashboards can be narrowed to one service."""
        dashboard = builder.build(DASHBOARD_SPECS[0])
        names = [v["name"] for v in dashboard["templating"]["list"]]

        assert "service" in names

    def test_queries_reference_the_service_variable(self, builder):
        """The template variable is actually wired into the queries."""
        for panel in builder.build(DASHBOARD_SPECS[0])["panels"]:
            for target in panel["targets"]:
                assert "$service" in target["expr"]


class TestMetricCoverage:
    """Dashboards must reference metrics the generators really emit."""

    def test_generators_emit_metrics(self, emitted_metrics):
        """Guards the extraction itself."""
        assert len(emitted_metrics) > 10

    @pytest.mark.parametrize("spec", (*DASHBOARD_SPECS, OVERVIEW_SPEC), ids=lambda s: s.slug)
    def test_every_panel_metric_exists(self, spec, emitted_metrics):
        """A panel querying a nonexistent metric is silently empty in Grafana."""
        referenced = {metric for panel in spec.panels for metric in panel.metrics}
        missing = referenced - emitted_metrics

        assert not missing, f"{spec.slug} references unknown metrics: {sorted(missing)}"

    def test_new_incident_types_have_dashboards(self):
        """Memory leak and deadlock ship with dashboards."""
        slugs = {spec.slug for spec in DASHBOARD_SPECS}

        assert {"memory_leak", "deadlock"} <= slugs


class TestExport:
    """Test writing dashboards to disk."""

    def test_writes_one_file_per_dashboard(self, builder, tmp_path):
        """Every dashboard becomes a JSON file."""
        written = builder.export(tmp_path)

        assert len(written) == len(DASHBOARD_SPECS) + 1
        assert all(path.exists() for path in written)

    def test_written_files_are_valid_json(self, builder, tmp_path):
        """Grafana needs parseable JSON."""
        for path in builder.export(tmp_path):
            dashboard = json.loads(path.read_text())
            assert dashboard["panels"]

    def test_creates_missing_output_directory(self, builder, tmp_path):
        """The target directory is created on demand."""
        target = tmp_path / "nested" / "dashboards"
        builder.export(target)

        assert target.exists()

    def test_export_is_reproducible(self, builder, tmp_path):
        """Re-exporting produces identical bytes, so diffs stay clean."""
        first = tmp_path / "a"
        second = tmp_path / "b"
        builder.export(first)
        builder.export(second)

        for path in sorted(first.glob("*.json")):
            assert path.read_text() == (second / path.name).read_text()
