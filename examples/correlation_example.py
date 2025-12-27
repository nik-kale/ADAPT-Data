"""Example demonstrating correlation ID usage in ADAPT-Data.

This example shows how correlation IDs propagate across logs, metrics,
and traces to enable cross-signal correlation in RCA systems.
"""

from datetime import datetime, timedelta
from pathlib import Path

from generator.core.base import IncidentContext
from generator.core.correlation import (
    CorrelationManager,
    CorrelatedEvent,
    generate_request_chain
)
from generator.core.utils import timestamp_to_iso


def example_basic_correlation():
    """Example: Basic correlation ID generation."""
    print("=== Basic Correlation Example ===\n")

    # Create correlation manager
    manager = CorrelationManager(correlation_density=0.8)

    # Create correlated event
    event = manager.create_event(
        timestamp=datetime.utcnow(),
        service="api-gateway",
        operation="GET /users/123"
    )

    print(f"Correlation ID: {event.correlation_id}")
    print(f"Request ID: {event.request_id}")

    # Use in log
    log = {
        "timestamp": timestamp_to_iso(event.timestamp),
        "level": "INFO",
        "message": "Processing user request"
    }
    log.update(event.to_log_context())
    print(f"\nLog with correlation: {log}")

    # Use in metric
    metric = {
        "timestamp": timestamp_to_iso(event.timestamp),
        "metric_name": "http_request_duration_ms",
        "value": 45.2,
        "tags": {}
    }
    metric["tags"].update(event.to_metric_tags())
    print(f"\nMetric with correlation: {metric}")

    # Use in trace
    trace = {
        "trace_id": event.correlation_id,
        "timestamp": timestamp_to_iso(event.timestamp),
        "spans": [{
            "span_id": "span-001",
            "attributes": event.to_trace_attributes()
        }]
    }
    print(f"\nTrace with correlation: {trace}")


def example_request_chain():
    """Example: Multi-service request chain with parent-child relationships."""
    print("\n\n=== Request Chain Example ===\n")

    # Simulate a request flowing through multiple services
    services = ["api-gateway", "user-service", "postgres-primary"]
    operations = ["GET /users/123", "get_user", "SELECT FROM users"]

    chain = generate_request_chain(
        services=services,
        operations=operations,
        timestamp=datetime.utcnow()
    )

    print(f"Generated {len(chain)} correlated events:\n")

    for i, event in enumerate(chain):
        print(f"Event {i + 1}:")
        print(f"  Service: {event.service}")
        print(f"  Operation: {event.operation}")
        print(f"  Correlation ID: {event.correlation_id}")
        print(f"  Request ID: {event.request_id}")
        if event.parent_id:
            print(f"  Parent ID: {event.parent_id}")
        print()

    # Verify correlation
    print("Verification:")
    print(f"  Same request_id: {len(set(e.request_id for e in chain)) == 1}")
    print(f"  Parent-child linkage: {chain[1].parent_id == chain[0].correlation_id}")


def example_correlation_density():
    """Example: Controlling correlation density."""
    print("\n\n=== Correlation Density Example ===\n")

    # High correlation (80% of events correlated)
    high_density = CorrelationManager(correlation_density=0.8)

    # Low correlation (20% of events correlated)
    low_density = CorrelationManager(correlation_density=0.2)

    # Generate events and count correlations
    high_correlated = sum(
        1 for _ in range(100)
        if high_density.should_correlate()
    )

    low_correlated = sum(
        1 for _ in range(100)
        if low_density.should_correlate()
    )

    print(f"High density (0.8): {high_correlated}% events correlated")
    print(f"Low density (0.2): {low_correlated}% events correlated")

    print("\nUse cases:")
    print("  - High density (0.8-1.0): Microservices with strong RPC chains")
    print("  - Medium density (0.5-0.7): Mixed synchronous/asynchronous systems")
    print("  - Low density (0.2-0.4): Event-driven architectures with loose coupling")


def example_custom_correlation():
    """Example: Using correlation in custom generator."""
    print("\n\n=== Custom Generator Example ===\n")

    # Simulated incident context
    context = IncidentContext(
        output_dir=Path("./output"),
        correlation_density=0.9  # High correlation for this scenario
    )

    manager = CorrelationManager(correlation_density=context.correlation_density)

    # Generate correlated telemetry for same event
    timestamp = datetime.utcnow()
    event = manager.create_event(
        timestamp=timestamp,
        service="payment-service",
        operation="process_payment"
    )

    # Log entry
    log = {
        "timestamp": timestamp_to_iso(timestamp),
        "level": "INFO",
        "service": "payment-service",
        "message": "Payment processing started",
        **event.to_log_context()
    }

    # Metric
    metric = {
        "timestamp": timestamp_to_iso(timestamp),
        "metric_name": "payment_processing_duration_ms",
        "value": 125.5,
        "service": "payment-service",
        "tags": event.to_metric_tags()
    }

    # Trace span
    span = {
        "span_id": "span-payment-001",
        "service": "payment-service",
        "operation": "process_payment",
        "start_time": timestamp_to_iso(timestamp),
        "duration_ms": 125.5,
        "attributes": event.to_trace_attributes()
    }

    print("All telemetry shares correlation_id:", event.correlation_id)
    print(f"\nLog correlation_id: {log['correlation_id']}")
    print(f"Metric correlation_id: {metric['tags']['correlation_id']}")
    print(f"Span correlation_id: {span['attributes']['correlation_id']}")

    print("\nRCA systems can now:")
    print("  1. Query logs by correlation_id to get full request context")
    print("  2. Find related metrics using same correlation_id")
    print("  3. Link traces to logs and metrics for complete picture")


if __name__ == "__main__":
    example_basic_correlation()
    example_request_chain()
    example_correlation_density()
    example_custom_correlation()

    print("\n\n=== Summary ===")
    print("Correlation IDs enable:")
    print("  ✓ Cross-signal correlation (logs ↔ metrics ↔ traces)")
    print("  ✓ Request chain tracking across services")
    print("  ✓ Parent-child relationship modeling")
    print("  ✓ Configurable correlation density")
    print("  ✓ RCA-friendly data relationships")

