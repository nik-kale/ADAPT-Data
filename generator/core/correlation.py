"""Correlation ID propagation across telemetry types.

Real incident analysis leans on being able to join a log line, the metric it
moved, and the trace it belongs to. Generators use the helpers here to stamp a
shared correlation ID onto related records so downstream RCA systems have the
same joins available in synthetic data.
"""

import random
from dataclasses import dataclass
from typing import Any, Optional

from generator.core.utils import generate_id, generate_uuid

# Key used consistently across logs, metrics, traces and config deltas.
CORRELATION_KEY = "correlation_id"


@dataclass(frozen=True)
class CorrelationScope:
    """Identifiers shared by every record belonging to one logical event.

    Attributes:
        correlation_id: Joins records across telemetry types.
        trace_id: Distributed trace identifier for the event.
        request_id: Request identifier, as it would appear in an access log.
    """

    correlation_id: str
    trace_id: str
    request_id: str

    @classmethod
    def create(cls) -> "CorrelationScope":
        """Build a scope with freshly generated identifiers.

        Returns:
            A new correlation scope.
        """
        return cls(
            correlation_id=generate_uuid(),
            trace_id=generate_uuid(),
            request_id=generate_id(prefix="req-", length=12),
        )

    def stamp_log(self, log: dict[str, Any]) -> dict[str, Any]:
        """Attach correlation identifiers to a log record, in place.

        Args:
            log: Log record to stamp.

        Returns:
            The same log record, for chaining.
        """
        log[CORRELATION_KEY] = self.correlation_id
        log.setdefault("trace_id", self.trace_id)

        metadata = log.setdefault("metadata", {})
        if isinstance(metadata, dict):
            metadata.setdefault("request_id", self.request_id)

        return log

    def stamp_metric(self, metric: dict[str, Any]) -> dict[str, Any]:
        """Attach correlation identifiers to a metric record, in place.

        The ID goes into ``tags`` because the metric schema constrains tag
        values to strings and keeps top-level fields fixed.

        Args:
            metric: Metric record to stamp.

        Returns:
            The same metric record, for chaining.
        """
        tags = metric.setdefault("tags", {})
        if isinstance(tags, dict):
            tags[CORRELATION_KEY] = self.correlation_id

        return metric

    def stamp_trace(self, trace: dict[str, Any]) -> dict[str, Any]:
        """Attach correlation identifiers to a trace, in place.

        Every span inherits the correlation ID in its tags so a span found on
        its own still points back to the rest of the event.

        Args:
            trace: Trace record to stamp.

        Returns:
            The same trace record, for chaining.
        """
        trace[CORRELATION_KEY] = self.correlation_id

        for span in trace.get("spans", []):
            if not isinstance(span, dict):
                continue
            tags = span.setdefault("tags", {})
            if isinstance(tags, dict):
                tags[CORRELATION_KEY] = self.correlation_id

        return trace


class CorrelationGenerator:
    """Hands out correlation scopes at a configurable density.

    Not every event in a real system carries a usable correlation ID —
    sampling, dropped headers and legacy services all cut holes in the
    coverage. ``density`` reproduces that: it is the probability that any given
    event gets a scope at all.
    """

    def __init__(self, density: float = 1.0) -> None:
        """Initialize the generator.

        Args:
            density: Fraction of events that receive a correlation scope,
                from 0.0 (none) to 1.0 (all).

        Raises:
            ValueError: If density is outside [0.0, 1.0].
        """
        if not 0.0 <= density <= 1.0:
            raise ValueError(f"density must be between 0.0 and 1.0, got {density}")

        self.density = density
        self._scopes_created = 0

    @property
    def scopes_created(self) -> int:
        """Number of scopes handed out so far."""
        return self._scopes_created

    def new_scope(self) -> Optional[CorrelationScope]:
        """Create a scope, or return None for an uncorrelated event.

        Returns:
            A new scope with probability ``density``, otherwise None.
        """
        if self.density < 1.0 and random.random() >= self.density:
            return None

        self._scopes_created += 1
        return CorrelationScope.create()

    def new_scope_always(self) -> CorrelationScope:
        """Create a scope regardless of density.

        Use for events that must always be joinable, such as the records that
        carry the incident's root-cause signal.

        Returns:
            A new correlation scope.
        """
        self._scopes_created += 1
        return CorrelationScope.create()
