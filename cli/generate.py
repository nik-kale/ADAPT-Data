"""Generate incident command implementation."""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from generator.core.base import IncidentContext
from generator.core.logging_config import get_logger
from generator.core.topology import TopologyGenerator
from generator.core.utils import parse_duration
from generator.core.validation import validate_scenario_file, GenerationConfig
from generator.incidents.latency_regression import LatencyRegressionGenerator
from generator.incidents.auth_failure import AuthFailureGenerator
from generator.incidents.dependency_outage import DependencyOutageGenerator
from generator.incidents.config_drift import ConfigDriftGenerator
from generator.incidents.packet_loss import PacketLossGenerator
from generator.incidents.bursty_noise import BurstyNoiseGenerator
from generator.incidents.cascade import CascadeGenerator

logger = get_logger(__name__)


GENERATOR_MAP = {
    "latency_regression": LatencyRegressionGenerator,
    "auth_failure": AuthFailureGenerator,
    "dependency_outage": DependencyOutageGenerator,
    "config_drift": ConfigDriftGenerator,
    "packet_loss": PacketLossGenerator,
    "bursty_noise": BurstyNoiseGenerator,
    "cascade": CascadeGenerator,
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
        # Validate generation configuration first
        try:
            config = GenerationConfig(
                scenario=scenario,
                output_dir=output_dir,
                duration=duration,
                severity=severity
            )
        except ValidationError as e:
            logger.error(f"Invalid configuration: {e}")
            return 1

        # Load scenario
        scenario_path = Path(scenario)
        if not scenario_path.exists():
            # Try to find in scenarios directory
            found_path = find_scenario_file(scenario)
            if found_path:
                scenario_path = found_path
            else:
                logger.error(f"Scenario not found: {scenario}")
                return 1

        logger.info(f"Loading scenario: {scenario_path}")

        # Validate scenario file (security + schema validation)
        try:
            scenario_config_validated = validate_scenario_file(scenario_path)
            scenario_config = scenario_config_validated.model_dump()
        except ValidationError as e:
            logger.error(f"Invalid scenario file: {e}")
            return 1
        except ValueError as e:
            logger.error(f"Scenario validation error: {e}")
            return 1

        # Parse duration
        duration_td = parse_duration(duration)

        # Create output directory with security checks
        try:
            # Ensure output_dir is created safely
            output_dir_abs = output_dir.resolve()
            output_dir_abs.mkdir(parents=True, exist_ok=True)
        except (OSError, RuntimeError) as e:
            logger.error(f"Cannot create output directory {output_dir}: {e}")
            return 1

        # Create incident context
        context = IncidentContext(
            start_time=datetime.utcnow(),
            duration=duration_td,
            severity=severity,
            output_dir=output_dir_abs,
            scenario_config=scenario_config
        )

        # Generate topology
        logger.info("Generating topology...")
        topo_gen = TopologyGenerator(context)
        topology = topo_gen.generate()
        context.topology = topology

        # Get generator type
        generator_type = scenario_config.get("type")
        if generator_type not in GENERATOR_MAP:
            logger.error(f"Unknown generator type: {generator_type}")
            logger.info(f"Available types: {', '.join(GENERATOR_MAP.keys())}")
            return 1

        # Create generator
        generator_class = GENERATOR_MAP[generator_type]
        generator_params = scenario_config.get("parameters", {})

        try:
            generator = generator_class(context, **generator_params)
        except (TypeError, ValueError) as e:
            logger.error(f"Error creating generator: {e}")
            return 1

        # Generate incident
        logger.info(f"Generating {generator_type} incident...")
        result = generator.generate()

        logger.info(f"✓ Successfully generated incident: {result['incident_id']}")
        logger.info(f"  Output directory: {output_dir}")
        logger.info(f"  Incident type: {result['incident_type']}")
        logger.info(f"  Duration: {duration}")
        logger.info(f"  Severity: {severity}")

        return 0

    except Exception as e:
        logger.error(f"Error generating incident: {e}", exc_info=True)
        return 1
