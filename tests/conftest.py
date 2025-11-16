"""Pytest configuration and shared fixtures."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from generator.core.base import IncidentContext
from generator.core.topology import TopologyGenerator


@pytest.fixture
def temp_output_dir():
    """Create temporary output directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_context(temp_output_dir):
    """Create sample incident context."""
    return IncidentContext(
        incident_id="test-incident-001",
        start_time=datetime(2025, 1, 15, 10, 0, 0),
        duration=timedelta(hours=1),
        severity="SEV3",
        output_dir=temp_output_dir,
        affected_services=["test-service"],
        root_cause="Test root cause"
    )


@pytest.fixture
def sample_topology(sample_context):
    """Generate sample topology."""
    topo_gen = TopologyGenerator(sample_context)
    return topo_gen.generate()


@pytest.fixture
def load_schema():
    """Load JSON schema for validation."""
    def _load_schema(schema_name: str) -> dict[str, Any]:
        schema_path = Path(__file__).parent.parent / "schema" / schema_name
        with open(schema_path) as f:
            return json.load(f)
    return _load_schema


@pytest.fixture
def validate_against_schema(load_schema):
    """Validate data against schema."""
    import jsonschema

    def _validate(data: dict[str, Any], schema_name: str) -> bool:
        schema = load_schema(schema_name)
        try:
            jsonschema.validate(instance=data, schema=schema)
            return True
        except jsonschema.ValidationError:
            return False

    return _validate
