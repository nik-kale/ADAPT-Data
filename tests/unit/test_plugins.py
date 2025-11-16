"""Unit tests for plugin system."""

from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch, MagicMock

import pytest

from generator.core.plugins import (
    Plugin,
    GeneratorPlugin,
    ExporterPlugin,
    AnalyzerPlugin,
    PluginRegistry,
    get_plugin_registry,
)


# Test plugin implementations
class TestGeneratorPluginImpl(GeneratorPlugin):
    """Test generator plugin."""

    @property
    def name(self) -> str:
        return "test-generator"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Test generator plugin"

    def initialize(self) -> None:
        self.initialized = True

    def generate(self, context: Any, **kwargs) -> dict[str, Any]:
        return {"status": "generated", "context": context}


class TestExporterPluginImpl(ExporterPlugin):
    """Test exporter plugin."""

    @property
    def name(self) -> str:
        return "test-exporter"

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self) -> None:
        self.initialized = True

    def export(self, dataset_dir: Path, output_path: Path, **kwargs) -> None:
        pass


class TestAnalyzerPluginImpl(AnalyzerPlugin):
    """Test analyzer plugin."""

    @property
    def name(self) -> str:
        return "test-analyzer"

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self) -> None:
        self.initialized = True

    def analyze(self, dataset_dir: Path) -> dict[str, Any]:
        return {"status": "analyzed"}


class TestPluginBaseClasses:
    """Test plugin base classes exist and work."""

    def test_plugin_base_class_exists(self):
        """Test Plugin base class exists."""
        assert Plugin is not None

    def test_generator_plugin_base_exists(self):
        """Test GeneratorPlugin base class exists."""
        assert GeneratorPlugin is not None
        assert issubclass(GeneratorPlugin, Plugin)

    def test_exporter_plugin_base_exists(self):
        """Test ExporterPlugin base class exists."""
        assert ExporterPlugin is not None
        assert issubclass(ExporterPlugin, Plugin)

    def test_analyzer_plugin_base_exists(self):
        """Test AnalyzerPlugin base class exists."""
        assert AnalyzerPlugin is not None
        assert issubclass(AnalyzerPlugin, Plugin)

    def test_plugin_has_required_properties(self):
        """Test Plugin base requires name and version."""
        plugin = TestGeneratorPluginImpl()

        assert hasattr(plugin, "name")
        assert hasattr(plugin, "version")
        assert hasattr(plugin, "description")
        assert hasattr(plugin, "initialize")

    def test_generator_plugin_has_generate_method(self):
        """Test GeneratorPlugin has generate method."""
        plugin = TestGeneratorPluginImpl()

        assert hasattr(plugin, "generate")
        result = plugin.generate(context={"test": "data"})
        assert "status" in result

    def test_exporter_plugin_has_export_method(self):
        """Test ExporterPlugin has export method."""
        plugin = TestExporterPluginImpl()

        assert hasattr(plugin, "export")
        # Should not crash
        plugin.export(Path("/fake"), Path("/fake/out"))

    def test_analyzer_plugin_has_analyze_method(self):
        """Test AnalyzerPlugin has analyze method."""
        plugin = TestAnalyzerPluginImpl()

        assert hasattr(plugin, "analyze")
        result = plugin.analyze(Path("/fake"))
        assert "status" in result


class TestPluginRegistry:
    """Test PluginRegistry functionality."""

    def test_registry_initialization(self):
        """Test PluginRegistry initializes correctly."""
        registry = PluginRegistry()

        assert isinstance(registry.generators, dict)
        assert isinstance(registry.exporters, dict)
        assert isinstance(registry.analyzers, dict)
        assert len(registry.generators) == 0
        assert len(registry.exporters) == 0
        assert len(registry.analyzers) == 0


class TestPluginRegistration:
    """Test plugin registration."""

    def test_register_generator(self):
        """Test registering a generator plugin."""
        registry = PluginRegistry()

        registry.register_generator(TestGeneratorPluginImpl)

        assert "test-generator" in registry.generators
        assert registry.generators["test-generator"] == TestGeneratorPluginImpl

    def test_register_exporter(self):
        """Test registering an exporter plugin."""
        registry = PluginRegistry()

        registry.register_exporter(TestExporterPluginImpl)

        assert "test-exporter" in registry.exporters
        assert registry.exporters["test-exporter"] == TestExporterPluginImpl

    def test_register_analyzer(self):
        """Test registering an analyzer plugin."""
        registry = PluginRegistry()

        registry.register_analyzer(TestAnalyzerPluginImpl)

        assert "test-analyzer" in registry.analyzers
        assert registry.analyzers["test-analyzer"] == TestAnalyzerPluginImpl

    def test_register_duplicate_plugin_overwrites(self):
        """Test registering duplicate plugin overwrites."""
        registry = PluginRegistry()

        registry.register_generator(TestGeneratorPluginImpl)
        registry.register_generator(TestGeneratorPluginImpl)

        # Should still have only one entry
        assert len(registry.generators) == 1

    def test_register_multiple_plugins(self):
        """Test registering multiple different plugins."""
        registry = PluginRegistry()

        registry.register_generator(TestGeneratorPluginImpl)
        registry.register_exporter(TestExporterPluginImpl)
        registry.register_analyzer(TestAnalyzerPluginImpl)

        assert len(registry.generators) == 1
        assert len(registry.exporters) == 1
        assert len(registry.analyzers) == 1


class TestGettingPluginsByName:
    """Test getting plugins by name."""

    def test_get_generator_by_name(self):
        """Test getting generator plugin by name."""
        registry = PluginRegistry()
        registry.register_generator(TestGeneratorPluginImpl)

        plugin = registry.get_generator("test-generator")

        assert plugin is not None
        assert isinstance(plugin, TestGeneratorPluginImpl)
        assert plugin.name == "test-generator"

    def test_get_exporter_by_name(self):
        """Test getting exporter plugin by name."""
        registry = PluginRegistry()
        registry.register_exporter(TestExporterPluginImpl)

        plugin = registry.get_exporter("test-exporter")

        assert plugin is not None
        assert isinstance(plugin, TestExporterPluginImpl)

    def test_get_analyzer_by_name(self):
        """Test getting analyzer plugin by name."""
        registry = PluginRegistry()
        registry.register_analyzer(TestAnalyzerPluginImpl)

        plugin = registry.get_analyzer("test-analyzer")

        assert plugin is not None
        assert isinstance(plugin, TestAnalyzerPluginImpl)

    def test_get_nonexistent_generator_returns_none(self):
        """Test getting non-existent generator returns None."""
        registry = PluginRegistry()

        plugin = registry.get_generator("nonexistent")

        assert plugin is None

    def test_get_nonexistent_exporter_returns_none(self):
        """Test getting non-existent exporter returns None."""
        registry = PluginRegistry()

        plugin = registry.get_exporter("nonexistent")

        assert plugin is None

    def test_get_nonexistent_analyzer_returns_none(self):
        """Test getting non-existent analyzer returns None."""
        registry = PluginRegistry()

        plugin = registry.get_analyzer("nonexistent")

        assert plugin is None

    def test_get_plugin_initializes_once(self):
        """Test getting plugin initializes it once."""
        registry = PluginRegistry()
        registry.register_generator(TestGeneratorPluginImpl)

        plugin1 = registry.get_generator("test-generator")
        plugin2 = registry.get_generator("test-generator")

        # Should return same instance
        assert plugin1 is plugin2
        assert hasattr(plugin1, "initialized")
        assert plugin1.initialized is True


class TestListPlugins:
    """Test list_plugins() functionality."""

    def test_list_plugins_empty_registry(self):
        """Test list_plugins() with empty registry."""
        registry = PluginRegistry()

        plugins = registry.list_plugins()

        assert plugins == {
            "generators": [],
            "exporters": [],
            "analyzers": [],
        }

    def test_list_plugins_with_registered_plugins(self):
        """Test list_plugins() with registered plugins."""
        registry = PluginRegistry()

        registry.register_generator(TestGeneratorPluginImpl)
        registry.register_exporter(TestExporterPluginImpl)
        registry.register_analyzer(TestAnalyzerPluginImpl)

        plugins = registry.list_plugins()

        assert plugins == {
            "generators": ["test-generator"],
            "exporters": ["test-exporter"],
            "analyzers": ["test-analyzer"],
        }

    def test_list_plugins_returns_copy(self):
        """Test list_plugins() returns data structure."""
        registry = PluginRegistry()
        registry.register_generator(TestGeneratorPluginImpl)

        plugins = registry.list_plugins()

        # Modifying returned list shouldn't affect registry
        plugins["generators"].append("fake-plugin")
        plugins2 = registry.list_plugins()

        assert "fake-plugin" not in plugins2["generators"]


class TestPluginLoading:
    """Test loading plugins from directory."""

    def test_load_from_nonexistent_directory(self):
        """Test loading from non-existent directory."""
        registry = PluginRegistry()

        # Should not crash
        registry.load_from_directory(Path("/nonexistent/path"))

    def test_load_from_directory_mock(self):
        """Test loading plugins from directory (mocked)."""
        registry = PluginRegistry()

        mock_dir = Path("/fake/plugins")

        with patch.object(Path, "exists", return_value=True):
            with patch.object(Path, "glob", return_value=[]):
                # Should not crash with empty directory
                registry.load_from_directory(mock_dir)


class TestGlobalPluginRegistry:
    """Test global plugin registry function."""

    def test_get_plugin_registry_returns_instance(self):
        """Test get_plugin_registry() returns registry."""
        # Reset global registry
        import generator.core.plugins
        generator.core.plugins._registry = None

        registry = get_plugin_registry()

        assert isinstance(registry, PluginRegistry)

    def test_get_plugin_registry_singleton(self):
        """Test get_plugin_registry() returns singleton."""
        # Reset global registry
        import generator.core.plugins
        generator.core.plugins._registry = None

        registry1 = get_plugin_registry()
        registry2 = get_plugin_registry()

        assert registry1 is registry2

    def test_get_plugin_registry_auto_loads(self):
        """Test get_plugin_registry() auto-loads from default directory."""
        # Reset global registry
        import generator.core.plugins
        generator.core.plugins._registry = None

        with patch.object(Path, "exists", return_value=False):
            registry = get_plugin_registry()

            # Should create registry even if directory doesn't exist
            assert isinstance(registry, PluginRegistry)


class TestPluginEdgeCases:
    """Test edge cases and error handling."""

    def test_plugin_with_empty_name(self):
        """Test plugin with empty name."""

        class EmptyNamePlugin(GeneratorPlugin):
            @property
            def name(self) -> str:
                return ""

            @property
            def version(self) -> str:
                return "1.0.0"

            def initialize(self) -> None:
                pass

            def generate(self, context: Any, **kwargs) -> dict[str, Any]:
                return {}

        registry = PluginRegistry()
        registry.register_generator(EmptyNamePlugin)

        # Should register with empty name
        assert "" in registry.generators

    def test_plugin_initialization_called_on_get(self):
        """Test plugin initialize() is called when getting plugin."""
        registry = PluginRegistry()
        registry.register_generator(TestGeneratorPluginImpl)

        plugin = registry.get_generator("test-generator")

        # Should have been initialized
        assert hasattr(plugin, "initialized")
        assert plugin.initialized is True
