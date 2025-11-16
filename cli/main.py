#!/usr/bin/env python3
"""Main CLI entry point for ADAPT-Data."""

import argparse
import sys
from pathlib import Path

from cli.generate import generate_incident
from cli.validate import validate_dataset


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="ADAPT-Data: Synthetic Telemetry & Incident Dataset Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Generate command
    gen_parser = subparsers.add_parser(
        "generate",
        help="Generate incident dataset"
    )
    gen_parser.add_argument(
        "--scenario",
        required=True,
        help="Scenario name or path to scenario YAML file"
    )
    gen_parser.add_argument(
        "--output",
        default="./output",
        help="Output directory (default: ./output)"
    )
    gen_parser.add_argument(
        "--duration",
        default="1h",
        help="Incident duration (e.g., 30m, 1h, 2h)"
    )
    gen_parser.add_argument(
        "--severity",
        choices=["SEV1", "SEV2", "SEV3", "SEV4"],
        default="SEV3",
        help="Incident severity"
    )

    # Validate command
    val_parser = subparsers.add_parser(
        "validate",
        help="Validate generated dataset against schemas"
    )
    val_parser.add_argument(
        "dataset_dir",
        help="Directory containing generated dataset"
    )
    val_parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict validation mode"
    )

    # List scenarios command
    list_parser = subparsers.add_parser(
        "list-scenarios",
        help="List available scenarios"
    )

    args = parser.parse_args()

    if args.command == "generate":
        return generate_incident(
            scenario=args.scenario,
            output_dir=Path(args.output),
            duration=args.duration,
            severity=args.severity
        )
    elif args.command == "validate":
        return validate_dataset(
            dataset_dir=Path(args.dataset_dir),
            strict=args.strict
        )
    elif args.command == "list-scenarios":
        from cli.scenarios import list_scenarios
        list_scenarios()
        return 0
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
