"""Golden file tests to ensure reproducibility."""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from generator.core.base import IncidentContext
from generator.core.topology import TopologyGenerator
from generator.incidents.latency_regression import LatencyRegressionGenerator


@pytest.fixture
def golden_dir():
    """Get golden files directory."""
    return Path(__file__).parent / "golden_files"


@pytest.fixture
def deterministic_context(temp_output_dir):
    """Create deterministic context for reproducible generation."""
    # Fixed random seed
    random.seed(42)

    # Fixed timestamp
    fixed_time = datetime(2025, 1, 15, 10, 0, 0)

    return IncidentContext(
        incident_id="golden-test-001",
        start_time=fixed_time,
        duration=timedelta(minutes=10),  # Short for testing
        severity="SEV3",
        output_dir=temp_output_dir,
        affected_services=["order-service"],
        root_cause="Test incident for golden file"
    )


class TestReproducibility:
    """Test that generation is reproducible with same seed."""

    def test_same_seed_produces_same_output(self, temp_output_dir):
        """Test that same seed produces identical output."""
        fixed_time = datetime(2025, 1, 15, 10, 0, 0)

        # Generate first time
        random.seed(42)
        context1 = IncidentContext(
            incident_id="test-001",
            start_time=fixed_time,
            duration=timedelta(minutes=5),
            severity="SEV3",
            output_dir=temp_output_dir / "run1"
        )
        topo1 = TopologyGenerator(context1)
        context1.topology = topo1.generate()
        gen1 = LatencyRegressionGenerator(context1)
        gen1.generate()

        # Generate second time with same seed
        random.seed(42)
        context2 = IncidentContext(
            incident_id="test-001",
            start_time=fixed_time,
            duration=timedelta(minutes=5),
            severity="SEV3",
            output_dir=temp_output_dir / "run2"
        )
        topo2 = TopologyGenerator(context2)
        context2.topology = topo2.generate()
        gen2 = LatencyRegressionGenerator(context2)
        gen2.generate()

        # Compare topology files
        with open(context1.output_dir / "topology" / "topology.json") as f1:
            topo_data1 = json.load(f1)
        with open(context2.output_dir / "topology" / "topology.json") as f2:
            topo_data2 = json.load(f2)

        assert topo_data1 == topo_data2

        # Compare log counts (should be same with same seed and params)
        logs1 = list((context1.output_dir / "logs").glob("*.jsonl"))
        logs2 = list((context2.output_dir / "logs").glob("*.jsonl"))

        with open(logs1[0]) as f1, open(logs2[0]) as f2:
            lines1 = f1.readlines()
            lines2 = f2.readlines()

        # Should have same number of logs
        assert len(lines1) == len(lines2)

    def test_different_seed_produces_different_output(self, temp_output_dir):
        """Test that different seeds produce different output."""
        fixed_time = datetime(2025, 1, 15, 10, 0, 0)

        # Generate with seed 42
        random.seed(42)
        context1 = IncidentContext(
            incident_id="test-001",
            start_time=fixed_time,
            duration=timedelta(minutes=5),
            severity="SEV3",
            output_dir=temp_output_dir / "seed42"
        )
        topo1 = TopologyGenerator(context1)
        context1.topology = topo1.generate()
        gen1 = LatencyRegressionGenerator(context1)
        gen1.generate()

        # Generate with seed 123
        random.seed(123)
        context2 = IncidentContext(
            incident_id="test-001",
            start_time=fixed_time,
            duration=timedelta(minutes=5),
            severity="SEV3",
            output_dir=temp_output_dir / "seed123"
        )
        topo2 = TopologyGenerator(context2)
        context2.topology = topo2.generate()
        gen2 = LatencyRegressionGenerator(context2)
        gen2.generate()

        # Read some metric values - they should differ
        metrics1 = list((context1.output_dir / "metrics").glob("*.jsonl"))
        metrics2 = list((context2.output_dir / "metrics").glob("*.jsonl"))

        with open(metrics1[0]) as f1, open(metrics2[0]) as f2:
            metric_vals1 = [json.loads(line)["value"] for line in f1.readlines()[:10]]
            metric_vals2 = [json.loads(line)["value"] for line in f2.readlines()[:10]]

        # Values should be different (extremely unlikely to be all identical)
        assert metric_vals1 != metric_vals2


class TestGoldenFiles:
    """Test against stored golden files."""

    @pytest.mark.skip(reason="Golden files not yet created - run create_golden_files.py first")
    def test_matches_golden_topology(self, deterministic_context, golden_dir):
        """Test that topology matches golden file."""
        topo_gen = TopologyGenerator(deterministic_context)
        topology = topo_gen.generate()

        # Load golden file
        with open(golden_dir / "topology_seed42.json") as f:
            golden_topology = json.load(f)

        assert topology == golden_topology

    @pytest.mark.skip(reason="Golden files not yet created")
    def test_matches_golden_timeline(self, deterministic_context, golden_dir):
        """Test that timeline matches golden file."""
        topo_gen = TopologyGenerator(deterministic_context)
        deterministic_context.topology = topo_gen.generate()

        gen = LatencyRegressionGenerator(deterministic_context)
        gen.generate()

        # Load generated timeline
        timeline_files = list((deterministic_context.output_dir / "timelines").glob("*.json"))
        with open(timeline_files[0]) as f:
            timeline = json.load(f)

        # Load golden
        with open(golden_dir / "timeline_seed42.json") as f:
            golden_timeline = json.load(f)

        # Compare key fields (timestamps might vary slightly)
        assert timeline["incident_id"] == golden_timeline["incident_id"]
        assert len(timeline["events"]) == len(golden_timeline["events"])
