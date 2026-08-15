"""Generate incident command implementation."""

import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import numpy as np
import yaml
from pydantic import ValidationError

from generator.core.base import IncidentContext
from generator.core.config import AdaptDataConfig
from generator.core.difficulty import DifficultyLevel, get_difficulty_config
from generator.core.logging_config import get_logger
from generator.core.progress import get_progress_tracker
from generator.core.topology import (
    TopologyGenerator,
    TopologyValidationError,
    find_topology_file,
)
from generator.core.utils import parse_duration
from generator.core.validation import validate_scenario_file, GenerationConfig
from generator.incidents.latency_regression import LatencyRegressionGenerator
from generator.incidents.auth_failure import AuthFailureGenerator
from generator.incidents.dependency_outage import DependencyOutageGenerator
from generator.incidents.config_drift import ConfigDriftGenerator
from generator.incidents.packet_loss import PacketLossGenerator
from generator.incidents.bursty_noise import BurstyNoiseGenerator
from generator.incidents.memory_leak import MemoryLeakGenerator
from generator.incidents.deadlock import DeadlockGenerator
from generator.incidents.cascade import CascadeGenerator

logger = get_logger(__name__)


GENERATOR_MAP = {
    "latency_regression": LatencyRegressionGenerator,
    "auth_failure": AuthFailureGenerator,
    "dependency_outage": DependencyOutageGenerator,
    "config_drift": ConfigDriftGenerator,
    "packet_loss": PacketLossGenerator,
    "bursty_noise": BurstyNoiseGenerator,
    "memory_leak": MemoryLeakGenerator,
    "deadlock": DeadlockGenerator,
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
    severity: str,
    difficulty: Optional[str] = None,
    global_config: Optional[AdaptDataConfig] = None,
    topology: Optional[str] = None
) -> int:
    """Generate incident dataset.

    Args:
        scenario: Scenario name or path
        output_dir: Output directory
        duration: Duration string (e.g., "1h")
        severity: Severity level
        difficulty: Difficulty level (beginner, easy, medium, hard, expert)
        global_config: Global ADAPT-Data configuration
        topology: Topology name or path. Overrides any topology named by the
            scenario; falls back to the built-in default when neither is set.

    Returns:
        Exit code
    """
    try:
        # Initialize progress tracker
        enable_progress = global_config.generation.enable_progress if global_config else True
        tracker = get_progress_tracker(enabled=enable_progress)

        # Apply random seed if configured
        if global_config and global_config.generation.random_seed is not None:
            seed = global_config.generation.random_seed
            random.seed(seed)
            np.random.seed(seed)
            logger.info(f"Using random seed: {seed}")

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
        with tracker.track("Loading scenario", total=1):
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

                # Check if parent directory exists and is writable
                if not output_dir_abs.parent.exists():
                    logger.error(f"Parent directory does not exist: {output_dir_abs.parent}")
                    logger.error("Please create the parent directory first or choose a different output location")
                    return 1

                if not os.access(output_dir_abs.parent, os.W_OK):
                    logger.error(f"No write permission for parent directory: {output_dir_abs.parent}")
                    logger.error("Please check directory permissions or choose a different output location")
                    return 1

                # Create directory
                output_dir_abs.mkdir(parents=True, exist_ok=True)

                # Verify we can actually write to it
                if not os.access(output_dir_abs, os.W_OK):
                    logger.error(f"Cannot write to output directory: {output_dir_abs}")
                    logger.error("Please check directory permissions")
                    return 1

                # Check available disk space (at least 100MB recommended)
                import shutil
                stat = shutil.disk_usage(output_dir_abs)
                free_mb = stat.free / (1024 * 1024)
                if free_mb < 100:
                    logger.warning(f"Low disk space: {free_mb:.1f}MB available")
                    logger.warning("Dataset generation may fail if disk space runs out")
                elif free_mb < 10:
                    logger.error(f"Insufficient disk space: {free_mb:.1f}MB available")
                    logger.error("At least 100MB of free space is recommended")
                    return 1

            except (OSError, RuntimeError) as e:
                logger.error(f"Cannot create output directory {output_dir}: {e}")
                logger.error("Common causes: insufficient permissions, invalid path, or disk full")
                return 1

            # Create incident context
            context = IncidentContext(
                start_time=datetime.utcnow(),
                duration=duration_td,
                severity=severity,
                output_dir=output_dir_abs,
                scenario_config=scenario_config
            )

            # Apply difficulty configuration if provided
            if difficulty:
                difficulty_level = DifficultyLevel.from_string(difficulty)
                difficulty_config = get_difficulty_config(difficulty_level)

                logger.info(f"Applying difficulty level: {difficulty}")
                logger.info(f"  Services: {difficulty_config.num_services}")
                logger.info(f"  Noise level: {difficulty_config.noise_level}")
                logger.info(f"  Correlation strength: {difficulty_config.correlation_strength}")

                # Store difficulty config in context for generators to use
                context.difficulty_config = difficulty_config

        # Generate topology
        with tracker.track("Generating topology", total=1):
            # An explicit --topology beats the scenario's own choice.
            topology_ref = topology or scenario_config.get("topology")

            if topology_ref:
                topology_path = find_topology_file(topology_ref)
                if topology_path is None:
                    logger.error(f"Topology not found: {topology_ref}")
                    logger.info(
                        "Provide a path to a YAML file, or a name from the topology/ directory"
                    )
                    return 1

                try:
                    topo_gen = TopologyGenerator.from_yaml(context, topology_path)
                except TopologyValidationError as e:
                    logger.error(f"Invalid topology {topology_path}: {e}")
                    return 1
            else:
                topo_gen = TopologyGenerator(context)

            context.topology = topo_gen.generate()

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
        with tracker.track(f"Generating {generator_type} incident", total=1):
            result = generator.generate()

        # Validate output if configured
        if global_config and global_config.validation.validate_on_generation:
            with tracker.track("Validating output data", total=1):
                logger.info("Running output validation...")
                validation_results = generator.validate_output()

                # Log summary
                summary = validation_results["summary"]
                if summary["validation_passed"]:
                    logger.info(f"✓ Validation passed: {summary['files_validated']} files validated")
                else:
                    logger.warning(f"⚠ Validation found {summary['total_errors']} errors")

                # Log errors
                if validation_results["errors"]:
                    logger.error("Validation errors:")
                    for error in validation_results["errors"]:
                        logger.error(f"  - {error}")

                # Log warnings (only first 5 to avoid spam)
                if validation_results["warnings"]:
                    logger.warning(f"Validation warnings ({len(validation_results['warnings'])} total):")
                    for warning in validation_results["warnings"][:5]:
                        logger.warning(f"  - {warning}")
                    if len(validation_results["warnings"]) > 5:
                        logger.warning(f"  ... and {len(validation_results['warnings']) - 5} more")

                # Log info (only first 3)
                if global_config.logging.level == "DEBUG" and validation_results["info"]:
                    logger.debug(f"Validation info ({len(validation_results['info'])} total):")
                    for info in validation_results["info"][:3]:
                        logger.debug(f"  - {info}")

                # Save validation report
                validation_report_path = output_dir_abs / "validation_report.json"
                import json
                with open(validation_report_path, 'w') as f:
                    json.dump(validation_results, f, indent=2)
                logger.info(f"  Validation report saved to: {validation_report_path}")

        logger.info(f"✓ Successfully generated incident: {result['incident_id']}")
        logger.info(f"  Output directory: {output_dir}")
        logger.info(f"  Incident type: {result['incident_type']}")
        logger.info(f"  Duration: {duration}")
        logger.info(f"  Severity: {severity}")
        if difficulty:
            logger.info(f"  Difficulty: {difficulty}")

        return 0

    except Exception as e:
        logger.error(f"Error generating incident: {e}", exc_info=True)
        return 1
