"""Core generator framework components."""

from generator.core.base import BaseGenerator, IncidentContext
from generator.core.correlation import CorrelationGenerator, CorrelationScope
from generator.core.streaming import StreamingJSONLWriter, stream_jsonl
from generator.core.timeline import TimelineGenerator
from generator.core.topology import (
    TopologyGenerator,
    TopologyValidationError,
    load_topology_file,
)
from generator.core.utils import generate_id, timestamp_to_iso, parse_duration

__all__ = [
    "BaseGenerator",
    "CorrelationGenerator",
    "CorrelationScope",
    "IncidentContext",
    "StreamingJSONLWriter",
    "TimelineGenerator",
    "TopologyGenerator",
    "TopologyValidationError",
    "generate_id",
    "load_topology_file",
    "parse_duration",
    "stream_jsonl",
    "timestamp_to_iso",
]
