"""Unit tests for configuration system."""

import os
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest
import yaml

from generator.core.config import (
    AdaptDataConfig,
    LoggingConfig,
    GenerationConfig,
    ValidationConfig,
    ExportConfig,
    AdvancedConfig,
    load_config,
    find_config_file,
    _apply_env_overrides,
    create_default_config_file,
)


class TestConfigModels:
    """Test configuration model classes."""

    def test_logging_config_defaults(self):
        """Test LoggingConfig has correct defaults."""
        config = LoggingConfig()

        assert config.level == "INFO"
        assert config.enable_colors is True
        assert config.log_file is None

    def test_generation_config_defaults(self):
        """Test GenerationConfig has correct defaults."""
        config = GenerationConfig()

        assert config.default_duration == "1h"
        assert config.default_severity == "SEV3"
        assert config.default_output_dir == "./output"
        assert config.enable_progress is True
        assert config.parallel_generation is False
        assert config.random_seed is None

    def test_validation_config_defaults(self):
        """Test ValidationConfig has correct defaults."""
        config = ValidationConfig()

        assert config.strict_mode is False
        assert config.max_scenario_size_mb == 1
        assert config.validate_on_generation is True

    def test_export_config_defaults(self):
        """Test ExportConfig has correct defaults."""
        config = ExportConfig()

        assert config.default_format == "opentelemetry"
        assert config.prometheus_port == 9090
        assert config.replay_speed == 1.0

    def test_advanced_config_defaults(self):
        """Test AdvancedConfig has correct defaults."""
        config = AdvancedConfig()

        assert config.enable_distributions is True
        assert config.enable_patterns is True
        assert config.enable_correlation is True
        assert config.noise_level == 0.1

    def test_adapt_data_config_defaults(self):
        """Test AdaptDataConfig has correct defaults."""
        config = AdaptDataConfig()

        assert isinstance(config.logging, LoggingConfig)
        assert isinstance(config.generation, GenerationConfig)
        assert isinstance(config.validation, ValidationConfig)
        assert isinstance(config.export, ExportConfig)
        assert isinstance(config.advanced, AdvancedConfig)


class TestConfigLoading:
    """Test configuration loading from dict."""

    def test_load_config_from_dict(self):
        """Test loading config from dictionary."""
        config_dict = {
            "logging": {"level": "DEBUG"},
            "generation": {"default_severity": "SEV1"},
            "validation": {"strict_mode": True},
        }

        config = AdaptDataConfig(**config_dict)

        assert config.logging.level == "DEBUG"
        assert config.generation.default_severity == "SEV1"
        assert config.validation.strict_mode is True

    def test_load_config_partial_dict(self):
        """Test loading config with partial dictionary (uses defaults)."""
        config_dict = {"logging": {"level": "WARNING"}}

        config = AdaptDataConfig(**config_dict)

        # Custom value
        assert config.logging.level == "WARNING"

        # Default values still present
        assert config.generation.default_duration == "1h"
        assert config.validation.strict_mode is False

    def test_load_config_empty_dict(self):
        """Test loading config with empty dictionary (all defaults)."""
        config = AdaptDataConfig(**{})

        assert config.logging.level == "INFO"
        assert config.generation.enable_progress is True

    def test_config_allows_extra_fields(self):
        """Test config allows extra fields (future compatibility)."""
        config_dict = {"custom_field": "custom_value", "another": 123}

        # Should not raise error
        config = AdaptDataConfig(**config_dict)
        assert config.logging.level == "INFO"  # Defaults still work


class TestEnvironmentVariableOverrides:
    """Test environment variable overrides."""

    def test_env_override_log_level(self):
        """Test ADAPT_LOG_LEVEL environment variable."""
        config = AdaptDataConfig()

        with patch.dict(os.environ, {"ADAPT_LOG_LEVEL": "debug"}):
            _apply_env_overrides(config)

        assert config.logging.level == "DEBUG"

    def test_env_override_enable_progress_true(self):
        """Test ADAPT_ENABLE_PROGRESS=true."""
        config = AdaptDataConfig()

        with patch.dict(os.environ, {"ADAPT_ENABLE_PROGRESS": "true"}):
            _apply_env_overrides(config)

        assert config.generation.enable_progress is True

    def test_env_override_enable_progress_false(self):
        """Test ADAPT_ENABLE_PROGRESS=false."""
        config = AdaptDataConfig()

        with patch.dict(os.environ, {"ADAPT_ENABLE_PROGRESS": "false"}):
            _apply_env_overrides(config)

        assert config.generation.enable_progress is False

    def test_env_override_output_dir(self):
        """Test ADAPT_OUTPUT_DIR environment variable."""
        config = AdaptDataConfig()

        with patch.dict(os.environ, {"ADAPT_OUTPUT_DIR": "/custom/path"}):
            _apply_env_overrides(config)

        assert config.generation.default_output_dir == "/custom/path"

    def test_env_override_random_seed(self):
        """Test ADAPT_RANDOM_SEED environment variable."""
        config = AdaptDataConfig()

        with patch.dict(os.environ, {"ADAPT_RANDOM_SEED": "42"}):
            _apply_env_overrides(config)

        assert config.generation.random_seed == 42

    def test_env_override_invalid_seed_ignored(self):
        """Test invalid ADAPT_RANDOM_SEED is ignored."""
        config = AdaptDataConfig()
        config.generation.random_seed = None

        with patch.dict(os.environ, {"ADAPT_RANDOM_SEED": "not-a-number"}):
            _apply_env_overrides(config)

        # Should remain None (invalid value ignored)
        assert config.generation.random_seed is None

    def test_env_override_multiple_vars(self):
        """Test multiple environment variables together."""
        config = AdaptDataConfig()

        env_vars = {
            "ADAPT_LOG_LEVEL": "warning",
            "ADAPT_OUTPUT_DIR": "/tmp/output",
            "ADAPT_RANDOM_SEED": "123",
        }

        with patch.dict(os.environ, env_vars):
            _apply_env_overrides(config)

        assert config.logging.level == "WARNING"
        assert config.generation.default_output_dir == "/tmp/output"
        assert config.generation.random_seed == 123


class TestConfigFileDiscovery:
    """Test configuration file discovery (mocked filesystem)."""

    def test_find_config_in_current_dir(self):
        """Test finding .adapt-data.yaml in current directory."""
        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = Path("/fake/project")

            with patch("pathlib.Path.exists") as mock_exists:
                # First check succeeds (current dir)
                mock_exists.return_value = True

                result = find_config_file()

                assert result == Path("/fake/project/.adapt-data.yaml")

    def test_find_config_alternate_extension(self):
        """Test finding .adapt-data.yml (alternate extension)."""
        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = Path("/fake/project")

            with patch("pathlib.Path.exists") as mock_exists:

                def exists_side_effect():
                    # .yaml doesn't exist, but .yml does
                    return True  # Simplified: just return True for .yml

                # First check .yaml (False), then .yml (True)
                mock_exists.side_effect = [False, True]

                result = find_config_file()

                assert result == Path("/fake/project/.adapt-data.yml")

    def test_find_config_in_parent_dir(self):
        """Test finding config in parent directory."""
        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = Path("/fake/project/subdir")

            with patch("pathlib.Path.exists") as mock_exists:
                # First two checks fail (subdir), then parent succeeds
                # Check order: subdir/.adapt-data.yaml, subdir/.adapt-data.yml, parent/.adapt-data.yaml
                mock_exists.side_effect = [False, False, True]

                result = find_config_file()

                # Should find it in parent
                assert result is not None
                assert result == Path("/fake/project/.adapt-data.yaml")

    def test_find_config_in_home_dir(self):
        """Test finding config in home directory."""
        with patch("pathlib.Path.cwd") as mock_cwd:
            # Start from a path close to root to avoid too many checks
            mock_cwd.return_value = Path("/fake")

            with patch("pathlib.Path.home") as mock_home:
                mock_home.return_value = Path("/fake/home")

                with patch("pathlib.Path.exists") as mock_exists:
                    # Check current (/fake): .yaml, .yml - False, False
                    # Check parent (/): .yaml, .yml - False, False (then break as reached root)
                    # Check home: .yaml - True
                    mock_exists.side_effect = [False, False, False, False, True]

                    result = find_config_file()

                    assert result == Path("/fake/home/.adapt-data.yaml")

    def test_find_config_not_found(self):
        """Test when no config file exists."""
        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = Path("/fake/project")

            with patch("pathlib.Path.exists") as mock_exists:
                mock_exists.return_value = False

                result = find_config_file()

                assert result is None


class TestLoadConfig:
    """Test load_config function."""

    def test_load_config_uses_defaults_when_no_file(self):
        """Test load_config returns defaults when no file found."""
        with patch("generator.core.config.find_config_file") as mock_find:
            mock_find.return_value = None

            # Force reload to bypass caching
            import generator.core.config
            generator.core.config._config = None

            config = load_config()

            assert config.logging.level == "INFO"
            assert config.generation.enable_progress is True

    def test_load_config_from_file(self):
        """Test load_config reads from file."""
        config_data = {"logging": {"level": "DEBUG"}, "generation": {"random_seed": 42}}

        yaml_content = yaml.dump(config_data)

        # Clear any environment variable overrides
        with patch.dict(os.environ, {}, clear=True):
            config_file = Path("/fake/config.yaml")

            with patch("builtins.open", mock_open(read_data=yaml_content)):
                with patch("pathlib.Path.exists", return_value=True):
                    # Force reload
                    import generator.core.config
                    generator.core.config._config = None

                    # Pass config_path directly to avoid find_config_file
                    config = load_config(config_path=config_file)

                    assert config.logging.level == "DEBUG"
                    assert config.generation.random_seed == 42


class TestCreateDefaultConfigFile:
    """Test creating default config file."""

    def test_create_default_config_file(self):
        """Test creating a default config file."""
        output_path = Path("/fake/config.yaml")

        with patch("builtins.open", mock_open()) as mock_file:
            create_default_config_file(output_path)

            # Verify file was opened for writing
            mock_file.assert_called_once_with(output_path, 'w')

            # Verify yaml.dump was called
            handle = mock_file()
            assert handle.write.called
