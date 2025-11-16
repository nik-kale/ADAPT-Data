"""Generate incident command implementation."""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from generator.core.base import IncidentContext
from generator.core.topology import TopologyGenerator
from generator.core.utils import parse_duration
from generator.incidents.latency_regression import LatencyRegressionGenerator
from generator.incidents.auth_failure import AuthFailureGenerator
from generator.incidents.dependency_outage import DependencyOutageGenerator
from generator.incidents.config_drift import ConfigDriftGenerator
from generator.incidents.packet_loss import PacketLossGenerator
from generator.incidents.bursty_noise import BurstyNoiseGenerator


GENERATOR_MAP = {
    "latency_regression": LatencyRegressionGenerator,
    "auth_failure": AuthFailureGenerator,
    "dependency_outage": DependencyOutageGenerator,
    "config_drift": ConfigDriftGenerator,
    "packet_loss": PacketLossGenerator,
    "bursty_noise": BurstyNoiseGenerator,
}


def load_scenario(scenario_path: Path) -> dict[str, Any]:
    """Load scenario configuration from YAML file.

    Args:
        scenario_path: Path to scenario file

    Returns:
        Scenario configuration dictionary
    """
    with open(scenario_path, 'r') as f:
        return yaml.safe_load(f)


def find_scenario_file(scenario_name: str) -> Path | None:
    """Find scenario file by name.

    Args:
        scenario_name: Scenario name

    Returns:
        Path to scenario file or None
    """
    # Check scenarios directory
    scenarios_dir = Path(__file__).parent.parent / "scenarios"
    scenario_file = scenarios_dir / f"{scenario_name}.yaml"

    if scenario_file.exists():
        return scenario_file

    return None


def generate_incident(
    scenario: str,
    output_dir: Path,
    duration: str,
    severity: str
) -> int:
    """Generate incident dataset.

    Args:
        scenario: Scenario name or path
        output_dir: Output directory
        duration: Duration string (e.g., "1h")
        severity: Severity level

    Returns:
        Exit code
    """
    try:
        # Load scenario
        scenario_path = Path(scenario)
        if not scenario_path.exists():
            # Try to find in scenarios directory
            found_path = find_scenario_file(scenario)
            if found_path:
                scenario_path = found_path
            else:
                print(f"Error: Scenario not found: {scenario}")
                return 1

        print(f"Loading scenario: {scenario_path}")
        scenario_config = load_scenario(scenario_path)

        # Parse duration
        duration_td = parse_duration(duration)

        # Create incident context
        context = IncidentContext(
            start_time=datetime.utcnow(),
            duration=duration_td,
            severity=severity,
            output_dir=output_dir,
            scenario_config=scenario_config
        )

        # Generate topology
        print("Generating topology...")
        topo_gen = TopologyGenerator(context)
        topology = topo_gen.generate()
        context.topology = topology

        # Get generator type
        generator_type = scenario_config.get("type")
        if generator_type not in GENERATOR_MAP:
            print(f"Error: Unknown generator type: {generator_type}")
            print(f"Available types: {', '.join(GENERATOR_MAP.keys())}")
            return 1

        # Create generator
        generator_class = GENERATOR_MAP[generator_type]
        generator_params = scenario_config.get("parameters", {})
        generator = generator_class(context, **generator_params)

        # Generate incident
        print(f"\nGenerating {generator_type} incident...")
        result = generator.generate()

        print(f"\n✓ Successfully generated incident: {result['incident_id']}")
        print(f"  Output directory: {output_dir}")
        print(f"  Incident type: {result['incident_type']}")
        print(f"  Duration: {duration}")
        print(f"  Severity: {severity}")

        return 0

    except Exception as e:
        print(f"Error generating incident: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
