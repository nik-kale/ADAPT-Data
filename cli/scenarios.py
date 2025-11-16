"""Scenario management utilities."""

from pathlib import Path

import yaml

from generator.core.logging_config import get_logger

logger = get_logger(__name__)


def list_scenarios() -> None:
    """List all available scenarios."""
    scenarios_dir = Path(__file__).parent.parent / "scenarios"

    if not scenarios_dir.exists():
        logger.error("No scenarios directory found")
        return

    logger.info("Available scenarios:\n")

    for scenario_file in sorted(scenarios_dir.glob("*.yaml")):
        try:
            with open(scenario_file, 'r') as f:
                config = yaml.safe_load(f)

            name = scenario_file.stem
            desc = config.get("description", "No description")
            incident_type = config.get("type", "unknown")

            logger.info(f"  {name}")
            logger.info(f"    Type: {incident_type}")
            logger.info(f"    Description: {desc}")
            logger.info("")

        except Exception as e:
            logger.error(f"  {scenario_file.stem} (error loading: {e})")
            logger.info("")
