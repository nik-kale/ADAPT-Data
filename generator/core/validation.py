"""Input validation using Pydantic models.

This module provides validation for all user inputs, scenario configurations,
and parameters to ensure data integrity and security.
"""

from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, validator, root_validator


class LatencyRegressionConfig(BaseModel):
    """Configuration for latency regression incidents."""

    affected_service: str = Field(..., min_length=1, max_length=100)
    baseline_latency_ms: float = Field(..., gt=0, le=60000)
    degraded_latency_ms: float = Field(..., gt=0, le=300000)
    error_threshold_ms: Optional[float] = Field(None, gt=0, le=600000)

    @validator('degraded_latency_ms')
    def degraded_must_be_higher(cls, v: float, values: dict[str, Any]) -> float:
        """Ensure degraded latency is higher than baseline."""
        baseline = values.get('baseline_latency_ms')
        if baseline and v <= baseline:
            raise ValueError(
                f"degraded_latency_ms ({v}) must be greater than "
                f"baseline_latency_ms ({baseline})"
            )
        return v


class AuthFailureConfig(BaseModel):
    """Configuration for auth failure incidents."""

    affected_service: str = Field(..., min_length=1, max_length=100)
    baseline_error_rate: float = Field(0.001, ge=0.0, le=1.0)
    spike_error_rate: float = Field(..., ge=0.0, le=1.0)

    @validator('spike_error_rate')
    def spike_must_be_higher(cls, v: float, values: dict[str, Any]) -> float:
        """Ensure spike error rate is higher than baseline."""
        baseline = values.get('baseline_error_rate', 0.0)
        if v <= baseline:
            raise ValueError(
                f"spike_error_rate ({v}) must be greater than "
                f"baseline_error_rate ({baseline})"
            )
        return v


class DependencyOutageConfig(BaseModel):
    """Configuration for dependency outage incidents."""

    failed_service: str = Field(..., min_length=1, max_length=100)
    dependent_services: Optional[list[str]] = None

    @validator('dependent_services', each_item=True)
    def validate_service_names(cls, v: str) -> str:
        """Validate service names."""
        if len(v) < 1 or len(v) > 100:
            raise ValueError(f"Service name length must be 1-100 characters: {v}")
        return v


class ConfigDriftConfig(BaseModel):
    """Configuration for config drift incidents."""

    affected_service: str = Field(..., min_length=1, max_length=100)
    config_key: str = Field(..., min_length=1, max_length=200)
    old_value: Any
    new_value: Any

    @validator('new_value')
    def values_must_differ(cls, v: Any, values: dict[str, Any]) -> Any:
        """Ensure new value differs from old value."""
        old = values.get('old_value')
        if old is not None and v == old:
            raise ValueError("new_value must differ from old_value")
        return v


class PacketLossConfig(BaseModel):
    """Configuration for packet loss incidents."""

    affected_services: list[str] = Field(..., min_length=1, max_length=20)
    packet_loss_percent: float = Field(..., gt=0.0, le=100.0)


class BurstyNoiseConfig(BaseModel):
    """Configuration for bursty noise incidents."""

    affected_service: str = Field(..., min_length=1, max_length=100)
    burst_frequency_minutes: int = Field(5, gt=0, le=60)
    burst_duration_seconds: int = Field(30, gt=0, le=300)


class CascadeIncidentSpec(BaseModel):
    """Specification for a single incident in a cascade."""

    type: Literal[
        "latency_regression",
        "auth_failure",
        "dependency_outage",
        "config_drift",
        "packet_loss",
        "bursty_noise"
    ]
    service: str = Field(..., min_length=1, max_length=100)
    delay: str = Field("0m", pattern=r'^\d+[smhd]$')
    duration: str = Field("10m", pattern=r'^\d+[smhd]$')
    severity: Optional[Literal["SEV1", "SEV2", "SEV3", "SEV4"]] = None
    parameters: Optional[dict[str, Any]] = None


class CascadeConfig(BaseModel):
    """Configuration for cascade incidents."""

    cascade_config: list[CascadeIncidentSpec] = Field(..., min_length=2, max_length=10)


class ScenarioConfig(BaseModel):
    """Top-level scenario configuration."""

    type: Literal[
        "latency_regression",
        "auth_failure",
        "dependency_outage",
        "config_drift",
        "packet_loss",
        "bursty_noise",
        "cascade"
    ]
    description: str = Field(..., min_length=1, max_length=1000)
    parameters: dict[str, Any] = Field(default_factory=dict)
    metadata: Optional[dict[str, Any]] = None

    @validator('parameters')
    def validate_parameters(cls, v: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
        """Validate parameters based on incident type."""
        incident_type = values.get('type')

        if not incident_type:
            return v

        # Validate based on type
        try:
            if incident_type == "latency_regression":
                LatencyRegressionConfig(**v)
            elif incident_type == "auth_failure":
                AuthFailureConfig(**v)
            elif incident_type == "dependency_outage":
                DependencyOutageConfig(**v)
            elif incident_type == "config_drift":
                ConfigDriftConfig(**v)
            elif incident_type == "packet_loss":
                PacketLossConfig(**v)
            elif incident_type == "bursty_noise":
                BurstyNoiseConfig(**v)
            elif incident_type == "cascade":
                CascadeConfig(**v)
        except Exception as e:
            raise ValueError(f"Invalid parameters for {incident_type}: {e}")

        return v


class GenerationConfig(BaseModel):
    """Configuration for generation command."""

    scenario: str = Field(..., min_length=1, max_length=500)
    output_dir: Path
    duration: str = Field(..., pattern=r'^\d+[smhd]$')
    severity: Literal["SEV1", "SEV2", "SEV3", "SEV4"]

    @validator('scenario')
    def validate_scenario_path(cls, v: str) -> str:
        """Validate scenario path for security."""
        # Prevent path traversal
        if '..' in v or v.startswith('/'):
            raise ValueError("Invalid scenario path: path traversal not allowed")
        return v

    @validator('output_dir')
    def validate_output_dir(cls, v: Path) -> Path:
        """Validate output directory."""
        # Prevent absolute paths outside project
        if v.is_absolute():
            raise ValueError("Output directory must be relative path")
        return v


def validate_scenario_file(scenario_path: Path) -> ScenarioConfig:
    """Validate a scenario YAML file.

    Args:
        scenario_path: Path to scenario file

    Returns:
        Validated scenario configuration

    Raises:
        ValueError: If validation fails
    """
    import yaml

    if not scenario_path.exists():
        raise ValueError(f"Scenario file not found: {scenario_path}")

    if scenario_path.suffix not in ['.yaml', '.yml']:
        raise ValueError(f"Scenario file must be YAML: {scenario_path}")

    # Check file size (max 1MB)
    if scenario_path.stat().st_size > 1024 * 1024:
        raise ValueError("Scenario file too large (max 1MB)")

    with open(scenario_path) as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError("Scenario file must contain a dictionary")

    return ScenarioConfig(**data)
