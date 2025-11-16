"""Scenario management utilities."""

from pathlib import Path

import yaml


def list_scenarios() -> None:
    """List all available scenarios."""
    scenarios_dir = Path(__file__).parent.parent / "scenarios"

    if not scenarios_dir.exists():
        print("No scenarios directory found")
        return

    print("Available scenarios:\n")

    for scenario_file in sorted(scenarios_dir.glob("*.yaml")):
        try:
            with open(scenario_file, 'r') as f:
                config = yaml.safe_load(f)

            name = scenario_file.stem
            desc = config.get("description", "No description")
            incident_type = config.get("type", "unknown")

            print(f"  {name}")
            print(f"    Type: {incident_type}")
            print(f"    Description: {desc}")
            print()

        except Exception as e:
            print(f"  {scenario_file.stem} (error loading: {e})")
            print()
