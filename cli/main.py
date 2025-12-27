#!/usr/bin/env python3
"""Main CLI entry point for ADAPT-Data."""

import argparse
import sys
from pathlib import Path

from cli.generate import generate_incident
from cli.validate import validate_dataset
from generator.core.config import get_config
from generator.core.plugins import get_plugin_registry


def _main_impl() -> int:
    """Main CLI implementation."""
    # Load configuration early
    config = get_config()

    # Load plugins early
    plugin_registry = get_plugin_registry()

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
        default=config.generation.default_output_dir,
        help=f"Output directory (default: {config.generation.default_output_dir})"
    )
    gen_parser.add_argument(
        "--duration",
        default=config.generation.default_duration,
        help=f"Incident duration (default: {config.generation.default_duration})"
    )
    gen_parser.add_argument(
        "--severity",
        choices=["SEV1", "SEV2", "SEV3", "SEV4"],
        default=config.generation.default_severity,
        help=f"Incident severity (default: {config.generation.default_severity})"
    )
    gen_parser.add_argument(
        "--difficulty",
        choices=["beginner", "easy", "medium", "hard", "expert"],
        help="Challenge difficulty level (affects complexity, noise, correlations)"
    )
    gen_parser.add_argument(
        "--streaming",
        action="store_true",
        help="Enable streaming output for large datasets (reduces memory usage)"
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
        default=config.validation.strict_mode,
        help=f"Enable strict validation mode (default: {config.validation.strict_mode})"
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
        default=config.export.default_format,
        help=f"Export format: opentelemetry, prometheus, datadog, or plugin name (default: {config.export.default_format})"
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
        default=config.export.prometheus_port,
        help=f"HTTP port (default: {config.export.prometheus_port})"
    )
    serve_parser.add_argument(
        "--replay-speed",
        type=float,
        default=config.export.replay_speed,
        help=f"Replay speed multiplier (default: {config.export.replay_speed})"
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

    # List plugins command
    list_plugins_parser = subparsers.add_parser(
        "list-plugins",
        help="List available plugins"
    )

    args = parser.parse_args()

    if args.command == "generate":
        return generate_incident(
            scenario=args.scenario,
            output_dir=Path(args.output),
            duration=args.duration,
            severity=args.severity,
            difficulty=args.difficulty,
            streaming=args.streaming,
            global_config=config
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
        from generator.core.logging_config import get_logger
        logger = get_logger(__name__)

        dataset_dir = Path(args.dataset_dir)

        # Try built-in exporters first
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
        elif args.format == "datadog":
            from generator.exporters.datadog import DatadogExporter
            exporter = DatadogExporter(dataset_dir)
            # Export based on output filename
            if "metrics" in args.output:
                exporter.export_metrics(Path(args.output))
            elif "logs" in args.output:
                exporter.export_logs(Path(args.output))
            elif "traces" in args.output:
                exporter.export_traces(Path(args.output))
            else:
                # Export all to directory
                exporter.export_all(Path(args.output))
        else:
            # Try plugin exporters
            plugin_exporter = plugin_registry.get_exporter(args.format)
            if plugin_exporter:
                logger.info(f"Using plugin exporter: {args.format}")
                plugin_exporter.export(dataset_dir, Path(args.output))
            else:
                logger.error(f"Unknown export format: {args.format}")
                logger.info("Available formats: opentelemetry, prometheus, datadog, or custom plugin exporters")
                return 1
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
    elif args.command == "list-plugins":
        from generator.core.logging_config import get_logger
        logger = get_logger(__name__)

        plugins = plugin_registry.list_plugins()

        logger.info("=== ADAPT-Data Plugins ===")
        logger.info(f"\nGenerators ({len(plugins['generators'])}):")
        for name in plugins['generators']:
            gen = plugin_registry.get_generator(name)
            if gen:
                logger.info(f"  - {name} (v{gen.version}): {gen.description}")

        logger.info(f"\nExporters ({len(plugins['exporters'])}):")
        for name in plugins['exporters']:
            exp = plugin_registry.get_exporter(name)
            if exp:
                logger.info(f"  - {name} (v{exp.version}): {exp.description}")

        logger.info(f"\nAnalyzers ({len(plugins['analyzers'])}):")
        for name in plugins['analyzers']:
            ana = plugin_registry.get_analyzer(name)
            if ana:
                logger.info(f"  - {name} (v{ana.version}): {ana.description}")

        if not any(plugins.values()):
            logger.info("\nNo plugins found. Install plugins to ~/.adapt-data/plugins/")

        return 0
    else:
        parser.print_help()
        return 1


def main() -> int:
    """Main CLI entry point with error handling."""
    try:
        return _main_impl()
    except KeyboardInterrupt:
        from generator.core.logging_config import get_logger
        logger = get_logger(__name__)
        logger.info("\nOperation cancelled by user")
        return 130
    except Exception as e:
        from generator.core.logging_config import get_logger
        logger = get_logger(__name__)
        logger.error(f"Unexpected error: {e}", exc_info=True)
        logger.error("Please report this issue at: https://github.com/yourusername/ADAPT-Data/issues")
        return 1


if __name__ == "__main__":
    sys.exit(main())
