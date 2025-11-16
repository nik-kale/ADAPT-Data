#!/usr/bin/env python3
"""Example script to test output validation functionality.

This script demonstrates:
1. Generating a simple incident
2. Running validation on the output
3. Displaying validation results
"""

from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from generator.core.base import IncidentContext
from generator.incidents.latency_regression import LatencyRegressionGenerator
from generator.core.logging_config import get_logger

logger = get_logger(__name__)


def main():
    """Run validation test."""
    logger.info("=" * 60)
    logger.info("ADAPT-Data Output Validation Test")
    logger.info("=" * 60)

    # Create temporary output directory
    with TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "test_output"

        # Create incident context
        context = IncidentContext(
            start_time=datetime.utcnow(),
            duration=timedelta(minutes=30),
            severity="SEV3",
            output_dir=output_dir,
            topology={
                "services": [
                    {"name": "order-service", "instances": 2},
                    {"name": "api-gateway", "instances": 1}
                ]
            }
        )

        # Create and run generator
        logger.info("\n1. Generating latency regression incident...")
        generator = LatencyRegressionGenerator(
            context=context,
            affected_service="order-service",
            baseline_latency_ms=50.0,
            degraded_latency_ms=500.0
        )

        result = generator.generate()
        logger.info(f"   ✓ Generated incident: {result['incident_id']}")
        logger.info(f"   - Metrics: {result['metric_count']}")
        logger.info(f"   - Logs: {result['log_count']}")
        logger.info(f"   - Traces: {result['trace_count']}")

        # Run validation
        logger.info("\n2. Running output validation...")
        validation_results = generator.validate_output()

        # Display results
        logger.info("\n3. Validation Results:")
        logger.info("-" * 60)

        summary = validation_results["summary"]
        logger.info(f"Files validated: {summary['files_validated']}")
        logger.info(f"Total errors: {summary['total_errors']}")
        logger.info(f"Total warnings: {summary['total_warnings']}")
        logger.info(f"Validation passed: {'✓ YES' if summary['validation_passed'] else '✗ NO'}")

        # Show errors
        if validation_results["errors"]:
            logger.error("\nErrors found:")
            for error in validation_results["errors"]:
                logger.error(f"  - {error}")
        else:
            logger.info("\n✓ No errors found!")

        # Show warnings (first 5)
        if validation_results["warnings"]:
            logger.warning(f"\nWarnings ({len(validation_results['warnings'])} total):")
            for warning in validation_results["warnings"][:5]:
                logger.warning(f"  - {warning}")
            if len(validation_results["warnings"]) > 5:
                logger.warning(f"  ... and {len(validation_results['warnings']) - 5} more")

        # Show info messages (first 5)
        if validation_results["info"]:
            logger.info(f"\nInfo messages ({len(validation_results['info'])} total):")
            for info in validation_results["info"][:5]:
                logger.info(f"  - {info}")
            if len(validation_results["info"]) > 5:
                logger.info(f"  ... and {len(validation_results['info']) - 5} more")

        logger.info("\n" + "=" * 60)
        logger.info("Validation test complete!")
        logger.info("=" * 60)


if __name__ == "__main__":
    main()
