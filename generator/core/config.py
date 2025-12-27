"""Configuration file system for ADAPT-Data.

This module provides a centralized configuration system that loads
settings from .adapt-data.yaml files in the project directory.
"""

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field

from generator.core.logging_config import get_logger

logger = get_logger(__name__)


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(default="INFO", description="Log level")
    enable_colors: bool = Field(default=True, description="Enable colored output")
    log_file: Optional[str] = Field(default=None, description="Log file path")
    log_format: str = Field(default="text", description="Log format (text or json)")


class GenerationConfig(BaseModel):
    """Default generation settings."""

    default_duration: str = Field(default="1h", description="Default incident duration")
    default_severity: str = Field(default="SEV3", description="Default severity level")
    default_output_dir: str = Field(default="./output", description="Default output directory")
    enable_progress: bool = Field(default=True, description="Show progress indicators")
    parallel_generation: bool = Field(default=False, description="Enable parallel generation")
    random_seed: Optional[int] = Field(default=None, description="Random seed for reproducibility")


class ValidationConfig(BaseModel):
    """Validation settings."""

    strict_mode: bool = Field(default=False, description="Enable strict validation")
    max_scenario_size_mb: int = Field(default=1, description="Max scenario file size in MB")
    validate_on_generation: bool = Field(default=True, description="Validate output after generation")


class ExportConfig(BaseModel):
    """Export settings."""

    default_format: str = Field(default="opentelemetry", description="Default export format")
    prometheus_port: int = Field(default=9090, description="Default Prometheus port")
    replay_speed: float = Field(default=1.0, description="Default replay speed")


class AdvancedConfig(BaseModel):
    """Advanced settings."""

    enable_distributions: bool = Field(default=True, description="Use parameterized distributions")
    enable_patterns: bool = Field(default=True, description="Apply time-series patterns")
    enable_correlation: bool = Field(default=True, description="Generate correlated anomalies")
    noise_level: float = Field(default=0.1, ge=0.0, le=1.0, description="Base noise level")


class AdaptDataConfig(BaseModel):
    """Main ADAPT-Data configuration."""

    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)
    advanced: AdvancedConfig = Field(default_factory=AdvancedConfig)

    class Config:
        """Pydantic configuration."""

        extra = "allow"  # Allow additional fields


# Global configuration instance
_config: Optional[AdaptDataConfig] = None


def find_config_file() -> Optional[Path]:
    """Find .adapt-data.yaml configuration file.

    Searches in:
    1. Current directory
    2. Parent directories (up to root)
    3. Home directory

    Returns:
        Path to config file or None if not found
    """
    # Check current directory and parents
    current = Path.cwd()
    for _ in range(10):  # Limit depth
        config_path = current / ".adapt-data.yaml"
        if config_path.exists():
            return config_path

        # Check alternate name
        config_path_alt = current / ".adapt-data.yml"
        if config_path_alt.exists():
            return config_path_alt

        # Move to parent
        if current.parent == current:  # Reached root
            break
        current = current.parent

    # Check home directory
    home_config = Path.home() / ".adapt-data.yaml"
    if home_config.exists():
        return home_config

    home_config_alt = Path.home() / ".adapt-data.yml"
    if home_config_alt.exists():
        return home_config_alt

    return None


def load_config(config_path: Optional[Path] = None, force_reload: bool = False) -> AdaptDataConfig:
    """Load configuration from file or use defaults.

    Args:
        config_path: Optional path to config file (auto-detected if None)
        force_reload: Force reload even if already loaded

    Returns:
        Configuration object
    """
    global _config

    if _config is not None and not force_reload:
        return _config

    # Find config file
    if config_path is None:
        config_path = find_config_file()

    # Load from file if found
    if config_path and config_path.exists():
        logger.info(f"Loading configuration from: {config_path}")
        try:
            with open(config_path) as f:
                config_data = yaml.safe_load(f)

            if config_data is None:
                config_data = {}

            _config = AdaptDataConfig(**config_data)
            logger.debug(f"Configuration loaded successfully")
        except Exception as e:
            logger.warning(f"Error loading config file: {e}. Using defaults.")
            _config = AdaptDataConfig()
    else:
        logger.debug("No configuration file found. Using defaults.")
        _config = AdaptDataConfig()

    # Apply environment variable overrides
    _apply_env_overrides(_config)

    return _config


def _apply_env_overrides(config: AdaptDataConfig) -> None:
    """Apply environment variable overrides to configuration.

    Environment variables:
        ADAPT_LOG_LEVEL: Override logging level
        ADAPT_ENABLE_PROGRESS: Enable/disable progress indicators
        ADAPT_OUTPUT_DIR: Default output directory
        ADAPT_RANDOM_SEED: Random seed for reproducibility
    """
    # Logging level
    if log_level := os.getenv("ADAPT_LOG_LEVEL"):
        config.logging.level = log_level.upper()
        logger.debug(f"Override log level from env: {config.logging.level}")

    # Progress indicators
    if enable_progress := os.getenv("ADAPT_ENABLE_PROGRESS"):
        config.generation.enable_progress = enable_progress.lower() in ["true", "1", "yes"]
        logger.debug(f"Override progress from env: {config.generation.enable_progress}")

    # Output directory
    if output_dir := os.getenv("ADAPT_OUTPUT_DIR"):
        config.generation.default_output_dir = output_dir
        logger.debug(f"Override output dir from env: {config.generation.default_output_dir}")

    # Random seed
    if seed := os.getenv("ADAPT_RANDOM_SEED"):
        try:
            config.generation.random_seed = int(seed)
            logger.debug(f"Override random seed from env: {config.generation.random_seed}")
        except ValueError:
            logger.warning(f"Invalid ADAPT_RANDOM_SEED value: {seed}")


def get_config() -> AdaptDataConfig:
    """Get global configuration instance.

    Returns:
        Configuration object (loads if not already loaded)
    """
    return load_config()


def create_default_config_file(path: Path) -> None:
    """Create a default configuration file.

    Args:
        path: Path where to create the config file
    """
    default_config = AdaptDataConfig()

    config_dict = {
        "# ADAPT-Data Configuration File": None,
        "# This file customizes ADAPT-Data behavior": None,
        "": None,
        "logging": {
            "level": default_config.logging.level,
            "enable_colors": default_config.logging.enable_colors,
            "# log_file": "adapt-data.log  # Uncomment to enable file logging",
        },
        "generation": {
            "default_duration": default_config.generation.default_duration,
            "default_severity": default_config.generation.default_severity,
            "default_output_dir": default_config.generation.default_output_dir,
            "enable_progress": default_config.generation.enable_progress,
            "parallel_generation": default_config.generation.parallel_generation,
            "# random_seed": "42  # Uncomment for reproducible generation",
        },
        "validation": {
            "strict_mode": default_config.validation.strict_mode,
            "max_scenario_size_mb": default_config.validation.max_scenario_size_mb,
            "validate_on_generation": default_config.validation.validate_on_generation,
        },
        "export": {
            "default_format": default_config.export.default_format,
            "prometheus_port": default_config.export.prometheus_port,
            "replay_speed": default_config.export.replay_speed,
        },
        "advanced": {
            "enable_distributions": default_config.advanced.enable_distributions,
            "enable_patterns": default_config.advanced.enable_patterns,
            "enable_correlation": default_config.advanced.enable_correlation,
            "noise_level": default_config.advanced.noise_level,
        },
    }

    with open(path, 'w') as f:
        yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)

    logger.info(f"Created default configuration file: {path}")
