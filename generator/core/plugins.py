"""Plugin system for extending ADAPT-Data functionality.

This module provides a simple plugin framework for extending ADAPT-Data
with custom generators, exporters, and analyzers.
"""

import importlib
import inspect
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional, Type

from generator.core.logging_config import get_logger

logger = get_logger(__name__)


class Plugin(ABC):
    """Base class for all plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version."""
        pass

    @property
    def description(self) -> str:
        """Plugin description."""
        return ""

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the plugin.

        Called when plugin is loaded.
        """
        pass


class GeneratorPlugin(Plugin):
    """Plugin for custom incident generators."""

    @abstractmethod
    def generate(self, context: Any, **kwargs) -> dict[str, Any]:
        """Generate incident data.

        Args:
            context: Incident context
            **kwargs: Generator-specific parameters

        Returns:
            Generation result
        """
        pass


class ExporterPlugin(Plugin):
    """Plugin for custom exporters."""

    @abstractmethod
    def export(self, dataset_dir: Path, output_path: Path, **kwargs) -> None:
        """Export dataset to custom format.

        Args:
            dataset_dir: Dataset directory
            output_path: Output file path
            **kwargs: Exporter-specific parameters
        """
        pass


class AnalyzerPlugin(Plugin):
    """Plugin for custom analyzers."""

    @abstractmethod
    def analyze(self, dataset_dir: Path) -> dict[str, Any]:
        """Analyze dataset.

        Args:
            dataset_dir: Dataset directory

        Returns:
            Analysis results
        """
        pass


class PluginRegistry:
    """Registry for managing plugins."""

    def __init__(self) -> None:
        """Initialize plugin registry."""
        self.generators: dict[str, Type[GeneratorPlugin]] = {}
        self.exporters: dict[str, Type[ExporterPlugin]] = {}
        self.analyzers: dict[str, Type[AnalyzerPlugin]] = {}
        self._initialized_plugins: dict[str, Plugin] = {}

    def register_generator(self, plugin_class: Type[GeneratorPlugin]) -> None:
        """Register a generator plugin.

        Args:
            plugin_class: Plugin class to register
        """
        # Instantiate to get name
        instance = plugin_class()
        name = instance.name

        if name in self.generators:
            logger.warning(f"Generator plugin '{name}' already registered. Overwriting.")

        self.generators[name] = plugin_class
        logger.info(f"Registered generator plugin: {name} v{instance.version}")

    def register_exporter(self, plugin_class: Type[ExporterPlugin]) -> None:
        """Register an exporter plugin.

        Args:
            plugin_class: Plugin class to register
        """
        instance = plugin_class()
        name = instance.name

        if name in self.exporters:
            logger.warning(f"Exporter plugin '{name}' already registered. Overwriting.")

        self.exporters[name] = plugin_class
        logger.info(f"Registered exporter plugin: {name} v{instance.version}")

    def register_analyzer(self, plugin_class: Type[AnalyzerPlugin]) -> None:
        """Register an analyzer plugin.

        Args:
            plugin_class: Plugin class to register
        """
        instance = plugin_class()
        name = instance.name

        if name in self.analyzers:
            logger.warning(f"Analyzer plugin '{name}' already registered. Overwriting.")

        self.analyzers[name] = plugin_class
        logger.info(f"Registered analyzer plugin: {name} v{instance.version}")

    def get_generator(self, name: str) -> Optional[GeneratorPlugin]:
        """Get generator plugin by name.

        Args:
            name: Plugin name

        Returns:
            Plugin instance or None
        """
        if name not in self.generators:
            return None

        # Return cached instance or create new one
        if name not in self._initialized_plugins:
            plugin = self.generators[name]()
            plugin.initialize()
            self._initialized_plugins[name] = plugin

        return self._initialized_plugins[name]  # type: ignore

    def get_exporter(self, name: str) -> Optional[ExporterPlugin]:
        """Get exporter plugin by name."""
        if name not in self.exporters:
            return None

        if name not in self._initialized_plugins:
            plugin = self.exporters[name]()
            plugin.initialize()
            self._initialized_plugins[name] = plugin

        return self._initialized_plugins[name]  # type: ignore

    def get_analyzer(self, name: str) -> Optional[AnalyzerPlugin]:
        """Get analyzer plugin by name."""
        if name not in self.analyzers:
            return None

        if name not in self._initialized_plugins:
            plugin = self.analyzers[name]()
            plugin.initialize()
            self._initialized_plugins[name] = plugin

        return self._initialized_plugins[name]  # type: ignore

    def list_plugins(self) -> dict[str, list[str]]:
        """List all registered plugins.

        Returns:
            Dictionary of plugin types and names
        """
        return {
            "generators": list(self.generators.keys()),
            "exporters": list(self.exporters.keys()),
            "analyzers": list(self.analyzers.keys()),
        }

    def load_from_directory(self, plugin_dir: Path) -> None:
        """Load plugins from a directory.

        Args:
            plugin_dir: Directory containing plugin modules
        """
        if not plugin_dir.exists():
            logger.warning(f"Plugin directory not found: {plugin_dir}")
            return

        logger.info(f"Loading plugins from: {plugin_dir}")

        for plugin_file in plugin_dir.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue

            try:
                # Import module
                module_name = plugin_file.stem
                spec = importlib.util.spec_from_file_location(module_name, plugin_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # Find plugin classes
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if issubclass(obj, GeneratorPlugin) and obj != GeneratorPlugin:
                            self.register_generator(obj)
                        elif issubclass(obj, ExporterPlugin) and obj != ExporterPlugin:
                            self.register_exporter(obj)
                        elif issubclass(obj, AnalyzerPlugin) and obj != AnalyzerPlugin:
                            self.register_analyzer(obj)

            except Exception as e:
                logger.error(f"Error loading plugin {plugin_file}: {e}")


# Global plugin registry
_registry: Optional[PluginRegistry] = None


def get_plugin_registry() -> PluginRegistry:
    """Get global plugin registry.

    Returns:
        Plugin registry instance
    """
    global _registry
    if _registry is None:
        _registry = PluginRegistry()

        # Auto-load plugins from default directory
        plugin_dir = Path.home() / ".adapt-data" / "plugins"
        if plugin_dir.exists():
            _registry.load_from_directory(plugin_dir)

    return _registry
