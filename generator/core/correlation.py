"""Correlation ID utilities for telemetry correlation.

This module provides utilities for generating and propagating correlation IDs
across logs, metrics, and traces to enable cross-signal correlation in RCA systems.
"""

import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from generator.core.utils import generate_uuid


@dataclass
class CorrelatedEvent:
    """Represents a correlated event with shared correlation ID.

    Attributes:
        correlation_id: Unique identifier for this correlated event
        timestamp: Event timestamp
        service: Service generating the event
        operation: Operation or endpoint being executed
        request_id: Optional request-level identifier (can be same as correlation_id)
        parent_id: Optional parent correlation ID for nested calls
        attributes: Additional event attributes
    """

    correlation_id: str = field(default_factory=generate_uuid)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    service: str = "unknown"
    operation: str = "unknown"
    request_id: Optional[str] = None
    parent_id: Optional[str] = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize derived fields."""
        if self.request_id is None:
            self.request_id = self.correlation_id

    def to_log_context(self) -> dict[str, Any]:
        """Convert to log context dictionary.

        Returns:
            Dictionary with correlation fields for log entries
        """
        context = {
            "correlation_id": self.correlation_id,
            "request_id": self.request_id,
            "service": self.service,
            "operation": self.operation
        }

        if self.parent_id:
            context["parent_id"] = self.parent_id

        return context

    def to_metric_tags(self) -> dict[str, str]:
        """Convert to metric tags dictionary.

        Returns:
            Dictionary with correlation fields for metric tags
        """
        tags = {
            "correlation_id": self.correlation_id,
            "service": self.service,
            "operation": self.operation
        }

        return tags

    def to_trace_attributes(self) -> dict[str, Any]:
        """Convert to trace attributes dictionary.

        Returns:
            Dictionary with correlation fields for trace spans
        """
        attributes = {
            "correlation_id": self.correlation_id,
            "request_id": self.request_id,
            "http.route": self.operation
        }

        if self.parent_id:
            attributes["parent_correlation_id"] = self.parent_id

        # Add custom attributes
        attributes.update(self.attributes)

        return attributes


class CorrelationManager:
    """Manages correlation ID generation and event correlation.

    Provides utilities for creating correlated events with configurable
    correlation density to simulate real-world correlation patterns.
    """

    def __init__(self, correlation_density: float = 0.8) -> None:
        """Initialize correlation manager.

        Args:
            correlation_density: Probability (0.0-1.0) that events will be correlated.
                                Lower values simulate more independent events.
                                Higher values create tighter correlation.
        """
        self.correlation_density = max(0.0, min(1.0, correlation_density))
        self._active_correlations: dict[str, CorrelatedEvent] = {}

    def create_event(
        self,
        timestamp: datetime,
        service: str,
        operation: str,
        **attributes
    ) -> CorrelatedEvent:
        """Create a new correlated event.

        Args:
            timestamp: Event timestamp
            service: Service name
            operation: Operation or endpoint name
            **attributes: Additional event attributes

        Returns:
            New CorrelatedEvent instance
        """
        event = CorrelatedEvent(
            timestamp=timestamp,
            service=service,
            operation=operation,
            attributes=attributes
        )

        # Store for potential reuse based on correlation density
        if random.random() < self.correlation_density:
            self._active_correlations[event.correlation_id] = event

        return event

    def create_child_event(
        self,
        parent_event: CorrelatedEvent,
        service: str,
        operation: str,
        timestamp: Optional[datetime] = None,
        **attributes
    ) -> CorrelatedEvent:
        """Create a child event linked to a parent.

        Args:
            parent_event: Parent correlated event
            service: Child service name
            operation: Child operation name
            timestamp: Optional timestamp (defaults to parent timestamp)
            **attributes: Additional event attributes

        Returns:
            New CorrelatedEvent with parent linkage
        """
        child = CorrelatedEvent(
            timestamp=timestamp or parent_event.timestamp,
            service=service,
            operation=operation,
            request_id=parent_event.request_id,
            parent_id=parent_event.correlation_id,
            attributes=attributes
        )

        return child

    def should_correlate(self) -> bool:
        """Determine if current event should be correlated.

        Uses correlation_density to randomly decide if events should
        share correlation IDs.

        Returns:
            True if events should be correlated
        """
        return random.random() < self.correlation_density

    def get_correlation_stats(self) -> dict[str, Any]:
        """Get statistics about correlation generation.

        Returns:
            Dictionary with correlation statistics
        """
        return {
            "correlation_density": self.correlation_density,
            "active_correlations": len(self._active_correlations),
            "correlation_ids": list(self._active_correlations.keys())
        }

    def clear_correlations(self) -> None:
        """Clear all active correlations."""
        self._active_correlations.clear()


def generate_request_chain(
    services: list[str],
    operations: list[str],
    timestamp: datetime,
    correlation_manager: Optional[CorrelationManager] = None
) -> list[CorrelatedEvent]:
    """Generate a chain of correlated events across services.

    Simulates a request propagating through multiple services with
    parent-child relationships.

    Args:
        services: List of service names in call chain
        operations: List of operation names for each service
        timestamp: Starting timestamp
        correlation_manager: Optional correlation manager (creates new if None)

    Returns:
        List of CorrelatedEvent instances forming a chain

    Example:
        ```python
        chain = generate_request_chain(
            services=["api-gateway", "user-service", "postgres-primary"],
            operations=["GET /users", "get_user", "SELECT"],
            timestamp=datetime.utcnow()
        )
        # chain[0] is parent, chain[1] is child of chain[0], etc.
        ```
    """
    if not services or not operations:
        return []

    if len(services) != len(operations):
        raise ValueError("services and operations must have same length")

    manager = correlation_manager or CorrelationManager()

    # Create root event
    events = [manager.create_event(timestamp, services[0], operations[0])]

    # Create child events
    for i in range(1, len(services)):
        child = manager.create_child_event(
            parent_event=events[-1],
            service=services[i],
            operation=operations[i],
            timestamp=timestamp
        )
        events.append(child)

    return events

