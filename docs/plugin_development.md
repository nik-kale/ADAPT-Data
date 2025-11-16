# Plugin Development Guide

This guide explains how to develop custom plugins for ADAPT-Data to extend its functionality with new incident generators, exporters, and analyzers.

## Table of Contents

- [Overview](#overview)
- [Plugin Types](#plugin-types)
- [Quick Start](#quick-start)
- [Generator Plugins](#generator-plugins)
- [Exporter Plugins](#exporter-plugins)
- [Analyzer Plugins](#analyzer-plugins)
- [Testing Plugins](#testing-plugins)
- [Publishing Plugins](#publishing-plugins)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

ADAPT-Data's plugin system allows you to extend its core functionality without modifying the codebase. Plugins are Python modules that implement specific interfaces and are automatically discovered from the `~/.adapt-data/plugins/` directory.

### Why Create Plugins?

- **Custom Incident Types**: Simulate organization-specific failure scenarios
- **Export Formats**: Export data to proprietary or specialized formats
- **Analysis Tools**: Add custom analysis and correlation algorithms
- **Reusability**: Share plugins across teams and projects

### Plugin Architecture

```
ADAPT-Data
    ↓
PluginRegistry (auto-discovers plugins)
    ↓
~/.adapt-data/plugins/
    ├── my_generator.py (GeneratorPlugin)
    ├── my_exporter.py (ExporterPlugin)
    └── my_analyzer.py (AnalyzerPlugin)
```

## Plugin Types

ADAPT-Data supports three types of plugins:

| Type | Purpose | Used In |
|------|---------|---------|
| **GeneratorPlugin** | Create custom incident scenarios | Scenario files (`type: your_plugin_name`) |
| **ExporterPlugin** | Export data to custom formats | CLI (`--format your_plugin_name`) |
| **AnalyzerPlugin** | Analyze and process datasets | Programmatic usage |

## Quick Start

### 1. Create Plugin Directory

```bash
mkdir -p ~/.adapt-data/plugins
cd ~/.adapt-data/plugins
```

### 2. Copy Example Plugin

```bash
# Copy from examples
cp /path/to/ADAPT-Data/examples/plugins/example_custom_generator.py my_plugin.py
```

### 3. Edit Plugin

```python
# my_plugin.py
from generator.core.plugins import GeneratorPlugin

class MyGeneratorPlugin(GeneratorPlugin):
    name = "my_incident_type"
    version = "1.0.0"
    description = "My custom incident generator"
    generator_class = MyCustomGenerator

plugin = MyGeneratorPlugin()
```

### 4. Verify Installation

```bash
adapt-data list-plugins
# Should show your plugin
```

## Generator Plugins

Generator plugins create custom incident scenarios by generating telemetry data (logs, metrics, traces).

### Interface

```python
from generator.core.base import BaseGenerator, IncidentContext
from generator.core.plugins import GeneratorPlugin

class MyCustomGenerator(BaseGenerator):
    """Your custom generator implementation."""

    def __init__(self, context: IncidentContext, **params):
        """Initialize generator with context and custom parameters.

        Args:
            context: Incident context (timing, severity, output dir)
            **params: Custom parameters from scenario file
        """
        super().__init__(context)
        # Store custom parameters
        self.my_param = params.get('my_param', 'default_value')

    def generate(self) -> dict:
        """Generate telemetry data.

        Returns:
            Summary dict with counts and incident details
        """
        logs = self._generate_logs()
        metrics = self._generate_metrics()
        traces = self._generate_traces()

        # Save data
        self.save_jsonl(logs, f"logs_{self.context.incident_id}.jsonl", "logs")
        self.save_jsonl(metrics, f"metrics_{self.context.incident_id}.jsonl", "metrics")
        self.save_jsonl(traces, f"traces_{self.context.incident_id}.jsonl", "traces")

        return {
            "incident_id": self.context.incident_id,
            "incident_type": "my_custom_type",
            "log_count": len(logs),
            "metric_count": len(metrics),
            "trace_count": len(traces)
        }

    def _generate_logs(self) -> list[dict]:
        """Generate log entries."""
        # Your implementation
        pass

    def _generate_metrics(self) -> list[dict]:
        """Generate metrics."""
        # Your implementation
        pass

    def _generate_traces(self) -> list[dict]:
        """Generate distributed traces."""
        # Your implementation
        pass
```

### Available Helpers

BaseGenerator provides helpful methods:

```python
# Get hosts for a service
hosts = self._get_service_hosts("my-service")

# Check if time is during incident
if self.context.is_during_incident(current_time):
    # Inject anomaly

# Access topology
services = self.context.topology.services

# Save data
self.save_jsonl(data, "filename.jsonl", "subdirectory")
```

### Using Distributions and Patterns

Make your data realistic:

```python
from generator.core.distributions import (
    UniformDistribution,
    LogNormalDistribution,
    LATENCY_DISTRIBUTION
)
from generator.core.patterns import (
    create_business_hours_pattern,
    NoisePattern
)

class MyGenerator(BaseGenerator):
    def __init__(self, context, **params):
        super().__init__(context)

        # Create distributions
        self.latency_dist = LogNormalDistribution(mu=3.5, sigma=0.5)
        self.error_dist = UniformDistribution(min_val=0, max_val=100)

        # Create patterns
        self.request_pattern = create_business_hours_pattern()
        self.noise = NoisePattern(noise_level=0.05)

    def _generate_metrics(self):
        metrics = []
        for current_time in self._time_iterator():
            # Sample from distribution
            latency = self.latency_dist.sample()

            # Apply pattern
            latency_with_pattern = self.noise.apply(latency, current_time)

            metrics.append({
                "timestamp": timestamp_to_iso(current_time),
                "metric_name": "latency_ms",
                "value": latency_with_pattern,
                # ...
            })
        return metrics
```

### Creating Scenario Files

Use your generator in scenario files:

```yaml
# scenarios/my_scenario.yaml
type: my_incident_type  # Matches plugin name
description: "My custom incident scenario"

parameters:
  my_param: "custom_value"
  affected_service: "my-service"
  # Any parameters your generator accepts

topology:
  services:
    - name: my-service
      type: web
      replicas: 3
```

### Example: Disk Full Generator

```python
"""Disk full incident generator plugin."""

from datetime import datetime, timedelta
from generator.core.base import BaseGenerator, IncidentContext
from generator.core.distributions import UniformDistribution
from generator.core.logging_config import get_logger
from generator.core.plugins import GeneratorPlugin
from generator.core.utils import timestamp_to_iso

logger = get_logger(__name__)

class DiskFullGenerator(BaseGenerator):
    """Simulates gradual disk space exhaustion."""

    def __init__(
        self,
        context: IncidentContext,
        affected_service: str = "storage-service",
        initial_usage_percent: float = 60.0,
        fill_rate_percent_per_hour: float = 10.0,
        full_threshold_percent: float = 95.0
    ):
        super().__init__(context)
        self.affected_service = affected_service
        self.initial_usage = initial_usage_percent
        self.fill_rate = fill_rate_percent_per_hour
        self.threshold = full_threshold_percent

        # Distributions
        self.jitter = UniformDistribution(min_val=-1.0, max_val=1.0)

    def generate(self) -> dict:
        logs = self._generate_logs()
        metrics = self._generate_metrics()

        self.save_jsonl(logs, f"logs_{self.context.incident_id}.jsonl", "logs")
        self.save_jsonl(metrics, f"metrics_{self.context.incident_id}.jsonl", "metrics")

        return {
            "incident_id": self.context.incident_id,
            "incident_type": "disk_full",
            "affected_service": self.affected_service,
            "log_count": len(logs),
            "metric_count": len(metrics)
        }

    def _generate_logs(self):
        logs = []
        hosts = self._get_service_hosts(self.affected_service)

        current_time = self.context.start_time - timedelta(hours=1)
        end_time = self.context.end_time + timedelta(hours=1)

        while current_time < end_time:
            hours_elapsed = (current_time - self.context.start_time).total_seconds() / 3600
            usage = min(100, self.initial_usage + (self.fill_rate * hours_elapsed))

            for host in hosts:
                if usage > self.threshold:
                    logs.append({
                        "timestamp": timestamp_to_iso(current_time),
                        "level": "ERROR",
                        "service": self.affected_service,
                        "host": host,
                        "message": f"Disk space critical: {int(usage)}% used",
                        "metadata": {
                            "disk_usage_percent": int(usage),
                            "error_type": "DiskFullError"
                        }
                    })

            current_time += timedelta(minutes=1)

        return logs

    def _generate_metrics(self):
        metrics = []
        hosts = self._get_service_hosts(self.affected_service)

        current_time = self.context.start_time - timedelta(hours=1)
        end_time = self.context.end_time + timedelta(hours=1)

        while current_time < end_time:
            hours_elapsed = (current_time - self.context.start_time).total_seconds() / 3600
            base_usage = min(100, self.initial_usage + (self.fill_rate * hours_elapsed))

            for host in hosts:
                usage_with_jitter = base_usage + self.jitter.sample()
                usage_with_jitter = max(0, min(100, usage_with_jitter))

                metrics.append({
                    "timestamp": timestamp_to_iso(current_time),
                    "metric_name": "disk_usage_percent",
                    "value": round(usage_with_jitter, 2),
                    "service": self.affected_service,
                    "metric_type": "gauge",
                    "unit": "percent",
                    "host": host,
                    "anomaly_injected": self.context.is_during_incident(current_time)
                })

            current_time += timedelta(minutes=1)

        return metrics

class DiskFullGeneratorPlugin(GeneratorPlugin):
    name = "disk_full"
    version = "1.0.0"
    description = "Simulates gradual disk space exhaustion leading to service failure"
    generator_class = DiskFullGenerator

plugin = DiskFullGeneratorPlugin()
```

## Exporter Plugins

Exporter plugins convert generated telemetry data to custom formats.

### Interface

```python
from pathlib import Path
from generator.core.plugins import ExporterPlugin

class MyExporter:
    """Your custom exporter implementation."""

    def __init__(self, dataset_dir: Path):
        """Initialize with dataset directory.

        Args:
            dataset_dir: Path to generated dataset
        """
        self.dataset_dir = dataset_dir

    def export(self, output_path: Path) -> None:
        """Export dataset to custom format.

        Args:
            output_path: Where to save exported data
        """
        # Load data from dataset_dir
        # Transform to your format
        # Save to output_path
        pass

class MyExporterPlugin(ExporterPlugin):
    name = "my_format"
    version = "1.0.0"
    description = "Exports to my custom format"
    exporter_class = MyExporter

plugin = MyExporterPlugin()
```

### Example: JSON Exporter

```python
"""JSON exporter plugin - combines all telemetry into single JSON."""

import json
from pathlib import Path
from generator.core.logging_config import get_logger
from generator.core.plugins import ExporterPlugin

logger = get_logger(__name__)

class JSONExporter:
    """Exports all telemetry to a single JSON file."""

    def __init__(self, dataset_dir: Path):
        self.dataset_dir = dataset_dir

    def export(self, output_path: Path):
        """Export to combined JSON format."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Load all data
        data = {
            "logs": self._load_logs(),
            "metrics": self._load_metrics(),
            "traces": self._load_traces(),
            "topology": self._load_topology(),
            "timeline": self._load_timeline()
        }

        # Save as JSON
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Exported to JSON: {output_path}")

    def _load_logs(self):
        logs = []
        for log_file in self.dataset_dir.glob("logs/*.jsonl"):
            with open(log_file) as f:
                for line in f:
                    logs.append(json.loads(line))
        return logs

    def _load_metrics(self):
        metrics = []
        for metric_file in self.dataset_dir.glob("metrics/*.jsonl"):
            with open(metric_file) as f:
                for line in f:
                    metrics.append(json.loads(line))
        return metrics

    def _load_traces(self):
        traces = []
        for trace_file in self.dataset_dir.glob("traces/*.jsonl"):
            with open(trace_file) as f:
                for line in f:
                    traces.append(json.loads(line))
        return traces

    def _load_topology(self):
        topology_file = self.dataset_dir / "topology.json"
        if topology_file.exists():
            with open(topology_file) as f:
                return json.load(f)
        return None

    def _load_timeline(self):
        timeline_file = self.dataset_dir / "timeline.json"
        if timeline_file.exists():
            with open(timeline_file) as f:
                return json.load(f)
        return None

class JSONExporterPlugin(ExporterPlugin):
    name = "json"
    version = "1.0.0"
    description = "Exports all telemetry to a single JSON file"
    exporter_class = JSONExporter

plugin = JSONExporterPlugin()
```

Usage:
```bash
adapt-data export ./output --format json --output combined.json
```

## Analyzer Plugins

Analyzer plugins process and analyze generated datasets.

### Interface

```python
from pathlib import Path
from typing import Any
from generator.core.plugins import AnalyzerPlugin

class MyAnalyzer:
    """Your custom analyzer implementation."""

    def __init__(self, dataset_dir: Path):
        """Initialize with dataset directory.

        Args:
            dataset_dir: Path to dataset to analyze
        """
        self.dataset_dir = dataset_dir

    def analyze(self) -> dict[str, Any]:
        """Analyze dataset.

        Returns:
            Analysis results dictionary
        """
        # Perform analysis
        # Return results
        return {}

class MyAnalyzerPlugin(AnalyzerPlugin):
    name = "my_analyzer"
    version = "1.0.0"
    description = "My custom analysis tool"
    analyzer_class = MyAnalyzer

plugin = MyAnalyzerPlugin()
```

### Example: Error Rate Analyzer

```python
"""Error rate analyzer plugin."""

import json
from collections import defaultdict
from pathlib import Path
from generator.core.logging_config import get_logger
from generator.core.plugins import AnalyzerPlugin

logger = get_logger(__name__)

class ErrorRateAnalyzer:
    """Analyzes error rates across services and time."""

    def __init__(self, dataset_dir: Path):
        self.dataset_dir = dataset_dir

    def analyze(self):
        """Perform error rate analysis."""
        results = {
            "errors_by_service": self._analyze_by_service(),
            "errors_over_time": self._analyze_over_time(),
            "top_error_messages": self._get_top_errors()
        }

        logger.info("Error rate analysis complete")
        return results

    def _analyze_by_service(self):
        errors = defaultdict(lambda: {"total": 0, "errors": 0})

        for log_file in self.dataset_dir.glob("logs/*.jsonl"):
            with open(log_file) as f:
                for line in f:
                    log = json.loads(line)
                    service = log.get('service', 'unknown')
                    errors[service]["total"] += 1
                    if log.get('level') in ['ERROR', 'FATAL']:
                        errors[service]["errors"] += 1

        # Calculate error rates
        for service in errors:
            total = errors[service]["total"]
            error_count = errors[service]["errors"]
            errors[service]["error_rate"] = (error_count / total * 100) if total > 0 else 0

        return dict(errors)

    def _analyze_over_time(self):
        # Group errors by 5-minute buckets
        buckets = defaultdict(int)

        for log_file in self.dataset_dir.glob("logs/*.jsonl"):
            with open(log_file) as f:
                for line in f:
                    log = json.loads(line)
                    if log.get('level') in ['ERROR', 'FATAL']:
                        # Round timestamp to 5-min bucket
                        timestamp = log['timestamp'][:16]  # YYYY-MM-DDTHH:MM
                        buckets[timestamp] += 1

        return dict(sorted(buckets.items()))

    def _get_top_errors(self, top_n=10):
        message_counts = defaultdict(int)

        for log_file in self.dataset_dir.glob("logs/*.jsonl"):
            with open(log_file) as f:
                for line in f:
                    log = json.loads(line)
                    if log.get('level') in ['ERROR', 'FATAL']:
                        message = log.get('message', 'Unknown error')
                        message_counts[message] += 1

        # Sort by count
        top_errors = sorted(
            message_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]

        return [{"message": msg, "count": count} for msg, count in top_errors]

class ErrorRateAnalyzerPlugin(AnalyzerPlugin):
    name = "error_rate_analyzer"
    version = "1.0.0"
    description = "Analyzes error rates across services and time"
    analyzer_class = ErrorRateAnalyzer

plugin = ErrorRateAnalyzerPlugin()
```

Usage:
```python
from pathlib import Path
from generator.core.plugins import get_plugin_registry

registry = get_plugin_registry()
analyzer = registry.get_analyzer("error_rate_analyzer")

if analyzer:
    instance = analyzer.analyzer_class(Path("./output"))
    results = instance.analyze()
    print(results)
```

## Testing Plugins

### Unit Tests

```python
# tests/test_my_plugin.py
import pytest
from pathlib import Path
from datetime import datetime, timedelta
from generator.core.base import IncidentContext
from my_plugin import MyCustomGenerator

def test_generator_creates_logs():
    """Test that generator creates logs."""
    context = IncidentContext(
        start_time=datetime.utcnow(),
        duration=timedelta(hours=1),
        severity="SEV3",
        output_dir=Path("/tmp/test"),
        scenario_config={}
    )

    generator = MyCustomGenerator(context, my_param="test")
    result = generator.generate()

    assert result["log_count"] > 0
    assert result["incident_type"] == "my_custom_type"

def test_generator_respects_parameters():
    """Test that generator uses custom parameters."""
    context = IncidentContext(
        start_time=datetime.utcnow(),
        duration=timedelta(hours=1),
        severity="SEV3",
        output_dir=Path("/tmp/test"),
        scenario_config={}
    )

    generator = MyCustomGenerator(context, my_param="custom_value")
    assert generator.my_param == "custom_value"
```

### Integration Tests

```python
def test_plugin_discovery():
    """Test that plugin is discovered."""
    from generator.core.plugins import get_plugin_registry

    registry = get_plugin_registry()
    plugins = registry.list_plugins()

    assert "my_incident_type" in plugins['generators']

def test_end_to_end_workflow(tmp_path):
    """Test complete workflow with plugin."""
    from cli.generate import generate_incident

    # Create scenario
    scenario = tmp_path / "scenario.yaml"
    scenario.write_text("""
    type: my_incident_type
    description: Test scenario
    parameters:
      my_param: test_value
    """)

    # Generate
    output = tmp_path / "output"
    result = generate_incident(
        scenario=str(scenario),
        output_dir=output,
        duration="1h",
        severity="SEV3"
    )

    assert result == 0
    assert (output / "logs").exists()
```

## Publishing Plugins

### Package Structure

```
my-adapt-plugin/
├── README.md
├── setup.py
├── my_plugin.py
└── tests/
    └── test_my_plugin.py
```

### setup.py

```python
from setuptools import setup

setup(
    name="adapt-data-my-plugin",
    version="1.0.0",
    description="My ADAPT-Data plugin",
    author="Your Name",
    py_modules=["my_plugin"],
    install_requires=[
        "adapt-data>=0.4.0",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "Programming Language :: Python :: 3.9",
    ],
)
```

### Installation Instructions

```bash
# Install from PyPI
pip install adapt-data-my-plugin

# Copy plugin to ADAPT-Data plugins directory
cp $(python -c "import my_plugin; print(my_plugin.__file__)") ~/.adapt-data/plugins/
```

## Best Practices

### Code Quality

1. **Follow PEP 8**: Use consistent Python style
2. **Type Hints**: Add type annotations for better IDE support
3. **Docstrings**: Document all classes and methods
4. **Error Handling**: Use try/except blocks and log errors
5. **Logging**: Use `logger` instead of `print()`

### Data Generation

1. **Use Distributions**: Realistic data with probability distributions
2. **Apply Patterns**: Time-series patterns for temporal realism
3. **Validate Output**: Check data quality before saving
4. **Performance**: Optimize for large datasets (use generators, batch operations)
5. **Reproducibility**: Support random seeds for testing

### Plugin Design

1. **Single Responsibility**: One plugin, one purpose
2. **Configurable**: Accept parameters for flexibility
3. **Documented**: Clear README with examples
4. **Tested**: Unit and integration tests
5. **Versioned**: Semantic versioning (MAJOR.MINOR.PATCH)

### Common Patterns

```python
# Pattern 1: Time iteration
for current_time in self._iterate_time_window():
    # Generate data for this timestamp

# Pattern 2: Host iteration
for host in self._get_service_hosts(service_name):
    # Generate data for this host

# Pattern 3: Conditional anomaly injection
if self.context.is_during_incident(current_time):
    # Inject anomaly
else:
    # Generate baseline data

# Pattern 4: Using distributions
value = self.distribution.sample()
value_with_pattern = self.pattern.apply(value, current_time)

# Pattern 5: Saving data
self.save_jsonl(data, f"type_{self.context.incident_id}.jsonl", "subdirectory")
```

## Troubleshooting

### Plugin Not Discovered

**Problem**: `adapt-data list-plugins` doesn't show your plugin

**Solutions**:
1. Check plugin is in `~/.adapt-data/plugins/`
2. Verify plugin exports `plugin` variable
3. Check for syntax errors: `python ~/.adapt-data/plugins/my_plugin.py`
4. Ensure plugin name doesn't conflict with built-ins

### Import Errors

**Problem**: `ModuleNotFoundError` when loading plugin

**Solutions**:
1. Install ADAPT-Data: `pip install -e .` (from repo root)
2. Check Python path includes ADAPT-Data
3. Install plugin dependencies
4. Use absolute imports in plugin

### Plugin Crashes

**Problem**: Plugin raises exception during execution

**Solutions**:
1. Add try/except blocks around risky operations
2. Validate input parameters in `__init__`
3. Use logging for debugging: `logger.debug(f"Value: {value}")`
4. Test with small datasets first
5. Check file permissions for output directory

### Data Quality Issues

**Problem**: Generated data doesn't look realistic

**Solutions**:
1. Use distributions instead of `random.randint()`
2. Apply time-series patterns for temporal variation
3. Add noise for natural variance
4. Study real-world data for realistic ranges
5. Use difficulty configs for appropriate complexity

### Performance Issues

**Problem**: Plugin is slow for large datasets

**Solutions**:
1. Use generators instead of lists where possible
2. Batch file I/O operations
3. Profile code to find bottlenecks
4. Consider parallel processing
5. Optimize hot loops

## Additional Resources

- [ADAPT-Data Architecture](architecture.md)
- [API Reference](api_reference.md)
- [Example Plugins](../examples/plugins/)
- [Built-in Generators](../generator/incidents/)
- [Core Modules](../generator/core/)

## Community

- **GitHub**: Submit issues and pull requests
- **Examples**: Share your plugins in examples directory
- **Discussions**: Join community discussions

## License

Plugins inherit the ADAPT-Data license unless otherwise specified. See LICENSE file for details.

---

**Happy Plugin Development!** 🚀

If you create a useful plugin, consider contributing it back to the ADAPT-Data project!
