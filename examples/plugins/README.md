# ADAPT-Data Plugin Examples

This directory contains example plugins demonstrating how to extend ADAPT-Data with custom functionality.

## Available Examples

### 1. Custom Generator: Memory Leak (`example_custom_generator.py`)

Simulates a memory leak incident with gradual OOM progression.

**Features:**
- Generates realistic memory growth over time
- Produces warning logs as memory fills
- Simulates OutOfMemoryError when threshold exceeded
- Includes GC pause metrics

**Usage:**

1. Install the plugin:
```bash
cp example_custom_generator.py ~/.adapt-data/plugins/
```

2. Create a scenario file (`scenarios/memory_leak_test.yaml`):
```yaml
type: memory_leak
description: "Memory leak in user service"
parameters:
  affected_service: "user-service"
  initial_memory_mb: 512
  leak_rate_mb_per_min: 10
  oom_threshold_mb: 2048
```

3. Generate the incident:
```bash
adapt-data generate --scenario memory_leak_test --duration 2h
```

### 2. Custom Exporter: CSV (`example_exporter.py`)

Exports telemetry data to CSV format for spreadsheet analysis.

**Features:**
- Exports metrics, logs, and traces to separate CSV files
- Flattens JSON structures for easy analysis
- Compatible with Excel, Google Sheets, pandas

**Usage:**

1. Install the plugin:
```bash
cp example_exporter.py ~/.adapt-data/plugins/
```

2. Export a dataset:
```bash
adapt-data export ./output --format csv --output analysis/data.csv
```

This creates:
- `analysis/data_metrics.csv` - All metrics
- `analysis/data_logs.csv` - All logs
- `analysis/data_traces.csv` - All trace spans (flattened)

### 3. Custom Analyzer: Anomaly Pattern (`example_analyzer.py`)

Analyzes datasets for common anomaly patterns and data quality issues.

**Features:**
- Detects metric spikes (2x+ increases)
- Counts errors by service
- Checks data completeness
- Validates data quality

**Usage:**

1. Install the plugin:
```bash
cp example_analyzer.py ~/.adapt-data/plugins/
```

2. Use programmatically:
```python
from pathlib import Path
from generator.core.plugins import get_plugin_registry

registry = get_plugin_registry()
analyzer_plugin = registry.get_analyzer("anomaly_pattern_analyzer")

if analyzer_plugin:
    analyzer = analyzer_plugin.analyzer_class(Path("./output"))
    results = analyzer.analyze()

    print(f"Found {results['summary']['total_metric_anomalies']} metric spikes")
    print(f"Found {results['summary']['total_log_errors']} error logs")
    print(f"Data completeness: {results['summary']['data_completeness']}%")
```

## Creating Your Own Plugins

### Plugin Types

ADAPT-Data supports three types of plugins:

1. **GeneratorPlugin** - Custom incident generators
2. **ExporterPlugin** - Custom export formats
3. **AnalyzerPlugin** - Custom analysis tools

### Plugin Structure

All plugins follow this structure:

```python
# 1. Import required base classes
from generator.core.plugins import GeneratorPlugin  # or ExporterPlugin, AnalyzerPlugin

# 2. Implement your functionality class
class MyCustomGenerator:
    def __init__(self, context, **params):
        # Initialize with incident context
        pass

    def generate(self) -> dict:
        # Generate telemetry data
        pass

# 3. Create plugin wrapper
class MyCustomGeneratorPlugin(GeneratorPlugin):
    name = "my_custom_generator"  # Use in scenarios
    version = "1.0.0"
    description = "Description of what it does"
    generator_class = MyCustomGenerator

# 4. Export plugin instance
plugin = MyCustomGeneratorPlugin()
```

### Plugin Installation

**Option 1: Auto-discovery (Recommended)**
```bash
cp your_plugin.py ~/.adapt-data/plugins/
# Plugin will be discovered on next CLI run
```

**Option 2: Verify installation**
```bash
adapt-data list-plugins
```

### Plugin Best Practices

1. **Use descriptive names**: Plugin names should be lowercase with underscores
2. **Include version numbers**: Follow semantic versioning (MAJOR.MINOR.PATCH)
3. **Add comprehensive docstrings**: Help users understand your plugin
4. **Handle errors gracefully**: Log warnings instead of crashing
5. **Use distributions/patterns**: Make data realistic with built-in utilities
6. **Follow existing patterns**: Look at built-in generators for examples

### Testing Plugins

Test your plugins with pytest:

```python
# tests/test_my_plugin.py
from pathlib import Path
from datetime import datetime, timedelta
from generator.core.base import IncidentContext
from my_plugin import MyCustomGenerator

def test_my_plugin_generates_data():
    context = IncidentContext(
        start_time=datetime.utcnow(),
        duration=timedelta(hours=1),
        severity="SEV3",
        output_dir=Path("/tmp/test_output"),
        scenario_config={}
    )

    generator = MyCustomGenerator(context)
    result = generator.generate()

    assert result["incident_type"] == "my_custom_type"
    assert result["log_count"] > 0
```

## Plugin API Reference

### GeneratorPlugin

**Required Attributes:**
- `name` (str): Unique identifier used in scenario files
- `version` (str): Semantic version string
- `description` (str): Human-readable description
- `generator_class` (type): Your generator class

**Your Generator Class Must Implement:**
- `__init__(self, context: IncidentContext, **params)`: Initialize with context
- `generate(self) -> dict`: Generate telemetry, return summary

**Available Helpers (from BaseGenerator):**
- `self.save_jsonl(data, filename, subdir)`: Save data to JSONL
- `self._get_service_hosts(service_name)`: Get hosts for a service
- `self.context.is_during_incident(timestamp)`: Check if time is during incident
- `self.context.topology`: Access service topology

### ExporterPlugin

**Required Attributes:**
- `name` (str): Format name used with `--format`
- `version` (str): Semantic version string
- `description` (str): Human-readable description
- `exporter_class` (type): Your exporter class

**Your Exporter Class Must Implement:**
- `__init__(self, dataset_dir: Path)`: Initialize with dataset directory
- `export(self, output_path: Path)`: Export to specified path

### AnalyzerPlugin

**Required Attributes:**
- `name` (str): Unique analyzer identifier
- `version` (str): Semantic version string
- `description` (str): Human-readable description
- `analyzer_class` (type): Your analyzer class

**Your Analyzer Class Must Implement:**
- `__init__(self, dataset_dir: Path)`: Initialize with dataset directory
- `analyze(self) -> dict`: Perform analysis, return results

## Troubleshooting

### Plugin not discovered
- Check plugin file is in `~/.adapt-data/plugins/`
- Verify plugin exports `plugin` variable
- Check for syntax errors with `python your_plugin.py`
- Use `adapt-data list-plugins` to verify

### Import errors
- Ensure ADAPT-Data is installed: `pip install -e .`
- Check Python path includes ADAPT-Data
- Verify all required imports are available

### Plugin crashes
- Add try/except blocks around risky operations
- Use `logger.error()` instead of raising exceptions
- Test with small datasets first

## Additional Resources

- [ADAPT-Data Architecture](../../docs/architecture.md)
- [Generator Development Guide](../../docs/plugin_development.md)
- [API Reference](../../docs/api_reference.md)
- [Built-in Generators](../../generator/incidents/)

## Contributing

Found a bug or have an improvement? Please submit an issue or pull request to the ADAPT-Data repository.

## License

These examples are provided under the same license as ADAPT-Data. See LICENSE file for details.
