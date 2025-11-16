#!/usr/bin/env python3
"""Example script showing how to generate incidents programmatically."""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from generator.core.base import IncidentContext
from generator.core.topology import TopologyGenerator
from generator.incidents.latency_regression import LatencyRegressionGenerator


def main():
    """Generate example latency regression incident."""
    print("ADAPT-Data Example: Generating Latency Regression Incident")
    print("=" * 60)

    # Create incident context
    output_dir = Path(__file__).parent / "outputs" / "sample_latency_incident"
    output_dir.mkdir(parents=True, exist_ok=True)

    context = IncidentContext(
        start_time=datetime.utcnow(),
        duration=timedelta(minutes=30),  # Short duration for demo
        severity="SEV3",
        output_dir=output_dir,
        affected_services=["order-service"],
        root_cause="Database query regression in order lookup"
    )

    print(f"\nIncident Configuration:")
    print(f"  ID: {context.incident_id}")
    print(f"  Duration: {context.duration}")
    print(f"  Severity: {context.severity}")
    print(f"  Output: {output_dir}")

    # Generate topology
    print("\nGenerating service topology...")
    topo_gen = TopologyGenerator(context)
    topology = topo_gen.generate()
    context.topology = topology
    print(f"  ✓ Generated {len(topology['services'])} services")
    print(f"  ✓ Generated {len(topology['dependencies'])} dependencies")

    # Create latency regression generator
    print("\nGenerating latency regression incident...")
    generator = LatencyRegressionGenerator(
        context,
        affected_service="order-service",
        baseline_latency_ms=50.0,
        degraded_latency_ms=400.0,
        error_threshold_ms=800.0
    )

    # Generate all data
    result = generator.generate()

    # Print summary
    print("\n" + "=" * 60)
    print("✓ Incident Generated Successfully!")
    print("=" * 60)
    print(f"\nSummary:")
    print(f"  Incident ID: {result['incident_id']}")
    print(f"  Type: {result['incident_type']}")
    print(f"  Affected Service: {result['affected_service']}")
    print(f"  Logs: {result['log_count']} entries")
    print(f"  Metrics: {result['metric_count']} data points")
    print(f"  Traces: {result['trace_count']} traces")
    print(f"  Config Changes: {result['config_change_count']}")

    print(f"\nOutput Location: {output_dir}")
    print("\nNext Steps:")
    print("  1. Validate: python -m cli.main validate", output_dir)
    print("  2. Explore: ls -R", output_dir)
    print("  3. Analyze: adapt-rca analyze --data", output_dir)


if __name__ == "__main__":
    main()
