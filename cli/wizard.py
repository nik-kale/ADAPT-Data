"""Interactive configuration wizard."""

import sys
from pathlib import Path
from typing import Any

import yaml


def run_wizard() -> dict[str, Any]:
    """Run interactive wizard to create scenario configuration.

    Returns:
        Scenario configuration dictionary
    """
    print("=" * 70)
    print("ADAPT-Data Configuration Wizard")
    print("=" * 70)
    print("\nThis wizard will help you create a custom incident scenario.\n")

    config: dict[str, Any] = {}

    # Choose incident type
    print("Available incident types:")
    types = [
        ("latency_regression", "Performance degradation from slow queries/code"),
        ("auth_failure", "Authentication service failures"),
        ("dependency_outage", "Critical dependency becomes unavailable"),
        ("config_drift", "Configuration change causes issues"),
        ("packet_loss", "Network degradation between services"),
        ("bursty_noise", "Intermittent resource contention"),
    ]

    for i, (name, desc) in enumerate(types, 1):
        print(f"  {i}. {name}: {desc}")

    while True:
        choice = input("\nSelect incident type (1-6): ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(types):
                config["type"] = types[idx][0]
                break
        except ValueError:
            pass
        print("Invalid choice. Please enter a number 1-6.")

    # Get description
    config["description"] = input("\nIncident description: ").strip() or "Custom incident scenario"

    # Type-specific parameters
    config["parameters"] = {}

    if config["type"] == "latency_regression":
        print("\n--- Latency Regression Parameters ---")
        config["parameters"]["affected_service"] = input("Affected service (default: order-service): ").strip() or "order-service"
        config["parameters"]["baseline_latency_ms"] = float(input("Baseline latency in ms (default: 50): ") or "50")
        config["parameters"]["degraded_latency_ms"] = float(input("Degraded latency in ms (default: 500): ") or "500")

    elif config["type"] == "auth_failure":
        print("\n--- Auth Failure Parameters ---")
        config["parameters"]["affected_service"] = input("Affected service (default: auth-service): ").strip() or "auth-service"
        config["parameters"]["spike_error_rate"] = float(input("Error rate during spike 0-1 (default: 0.25): ") or "0.25")

    elif config["type"] == "dependency_outage":
        print("\n--- Dependency Outage Parameters ---")
        config["parameters"]["failed_service"] = input("Failed service (default: postgres-primary): ").strip() or "postgres-primary"

    elif config["type"] == "config_drift":
        print("\n--- Config Drift Parameters ---")
        config["parameters"]["affected_service"] = input("Affected service (default: payment-service): ").strip() or "payment-service"
        config["parameters"]["config_key"] = input("Config key changed: ").strip() or "max_connections"
        config["parameters"]["old_value"] = int(input("Old value: ") or "100")
        config["parameters"]["new_value"] = int(input("New value: ") or "10")

    elif config["type"] == "packet_loss":
        print("\n--- Packet Loss Parameters ---")
        config["parameters"]["packet_loss_percent"] = float(input("Packet loss percentage (default: 15): ") or "15")

    elif config["type"] == "bursty_noise":
        print("\n--- Bursty Noise Parameters ---")
        config["parameters"]["affected_service"] = input("Affected service (default: user-service): ").strip() or "user-service"

    # Metadata
    print("\n--- Additional Configuration ---")

    difficulty = input("Difficulty level (easy/medium/hard, default: medium): ").strip() or "medium"

    config["metadata"] = {
        "category": _get_category(config["type"]),
        "difficulty": difficulty,
        "common_causes": ["Cause 1", "Cause 2"],
        "detection_signals": ["Signal 1", "Signal 2"],
        "mitigation_strategies": ["Strategy 1", "Strategy 2"],
    }

    # Save location
    print("\n--- Save Scenario ---")
    scenario_name = input("Scenario name (e.g., my_custom_incident): ").strip()
    if not scenario_name:
        scenario_name = f"custom_{config['type']}"

    output_path = Path("scenarios") / f"{scenario_name}.yaml"

    # Confirm
    print(f"\nScenario will be saved to: {output_path}")
    print("\nConfiguration:")
    print(yaml.dump(config, default_flow_style=False))

    confirm = input("\nSave this configuration? (y/n): ").strip().lower()

    if confirm == 'y':
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)

        print(f"\n✓ Scenario saved to: {output_path}")
        print(f"\nTo generate this incident:")
        print(f"  python -m cli.main generate --scenario {scenario_name} --output ./output")

        return config
    else:
        print("\nConfiguration not saved.")
        return {}


def _get_category(incident_type: str) -> str:
    """Get category for incident type."""
    categories = {
        "latency_regression": "performance",
        "auth_failure": "availability",
        "dependency_outage": "availability",
        "config_drift": "configuration",
        "packet_loss": "network",
        "bursty_noise": "resource_contention",
    }
    return categories.get(incident_type, "other")


if __name__ == "__main__":
    run_wizard()
