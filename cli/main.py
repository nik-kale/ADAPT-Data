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

    # Stats command
    stats_parser = subparsers.add_parser(
        "stats",
        help="Analyze dataset statistics"
    )
    stats_parser.add_argument(
        "dataset_dir",
        help="Directory containing dataset"
    )
    stats_parser.add_argument(
        "--output",
        help="Export stats to JSON file"
    )

    # Wizard command
    wizard_parser = subparsers.add_parser(
        "wizard",
        help="Interactive scenario configuration wizard"
    )

    # Export command
    export_parser = subparsers.add_parser(
        "export",
        help="Export dataset to other formats"
    )
    export_parser.add_argument(
        "dataset_dir",
        help="Directory containing dataset"
    )
    export_parser.add_argument(
        "--format",
        choices=["opentelemetry", "prometheus"],
        required=True,
        help="Export format"
    )
    export_parser.add_argument(
        "--output",
        required=True,
        help="Output file path"
    )

    # Serve command (for Prometheus)
    serve_parser = subparsers.add_parser(
        "serve",
        help="Serve metrics via HTTP (Prometheus)"
    )
    serve_parser.add_argument(
        "dataset_dir",
        help="Directory containing dataset"
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=9090,
        help="HTTP port (default: 9090)"
    )
    serve_parser.add_argument(
        "--replay-speed",
        type=float,
        default=1.0,
        help="Replay speed multiplier (default: 1.0)"
    )

    # Version command
    version_parser = subparsers.add_parser(
        "version",
        help="Show version information"
    )

    # Doctor command
    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Run health checks"
    )
    doctor_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show verbose output"
    )

    # Clean command
    clean_parser = subparsers.add_parser(
        "clean",
        help="Clean generated files"
    )
    clean_parser.add_argument(
        "path",
        help="Directory to clean"
    )
    clean_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted"
    )
    clean_parser.add_argument(
        "--force",
        action="store_true",
        help="Don't ask for confirmation"
    )

    # Info command
    info_parser = subparsers.add_parser(
        "info",
        help="Show dataset information"
    )
    info_parser.add_argument(
        "dataset_dir",
        help="Dataset directory"
    )

    # Correlate command
    correlate_parser = subparsers.add_parser(
        "correlate",
        help="Analyze correlations in dataset"
    )
    correlate_parser.add_argument(
        "dataset_dir",
        help="Dataset directory"
    )
    correlate_parser.add_argument(
        "--output",
        help="Export results to JSON file"
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
    elif args.command == "stats":
        from cli.stats import analyze_dataset, print_stats, export_stats
        stats = analyze_dataset(Path(args.dataset_dir))
        print_stats(stats)
        if args.output:
            export_stats(stats, Path(args.output))
        return 0
    elif args.command == "wizard":
        from cli.wizard import run_wizard
        run_wizard()
        return 0
    elif args.command == "export":
        dataset_dir = Path(args.dataset_dir)
        if args.format == "opentelemetry":
            from generator.exporters.opentelemetry import OpenTelemetryExporter
            exporter = OpenTelemetryExporter(dataset_dir)
            if "trace" in args.output:
                exporter.export_traces(Path(args.output))
            else:
                exporter.export_metrics(Path(args.output))
        elif args.format == "prometheus":
            from generator.exporters.prometheus import PrometheusExporter
            exporter = PrometheusExporter(dataset_dir)
            exporter.export_text_format(Path(args.output))
        return 0
    elif args.command == "serve":
        from generator.exporters.prometheus import PrometheusExporter
        exporter = PrometheusExporter(Path(args.dataset_dir))
        exporter.serve(port=args.port, replay_speed=args.replay_speed)
        return 0
    elif args.command == "version":
        from cli.utils import print_version
        print_version()
        return 0
    elif args.command == "doctor":
        from cli.utils import doctor
        return doctor(verbose=args.verbose)
    elif args.command == "clean":
        from cli.utils import clean
        return clean(Path(args.path), dry_run=args.dry_run, force=args.force)
    elif args.command == "info":
        from cli.utils import info
        return info(Path(args.dataset_dir))
    elif args.command == "correlate":
        from cli.correlate import analyze_correlations, print_correlation_report
        import json
        results = analyze_correlations(Path(args.dataset_dir))
        print_correlation_report(results)
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"Results exported to: {args.output}")
        return 0
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
