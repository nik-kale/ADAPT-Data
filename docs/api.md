# API Overview

Quick reference for ADAPT-Data's Python API. For detailed documentation, see the full [API Reference](api_reference.md).

## Installation

```bash
pip install -e .
```

## Quick Start

### Generate an Incident

```python
from pathlib import Path
from datetime import datetime, timedelta
from generator.core.base import IncidentContext
from generator.incidents.latency_regression import LatencyRegressionGenerator

# Create incident context
context = IncidentContext(
    incident_id="inc_001",
    start_time=datetime.utcnow(),
    duration=timedelta(hours=1),
    severity="SEV2",
    affected_services=["order-service"],
    root_cause="Database query regression",
    output_dir=Path("./output"),
    scenario_config={
        "baseline_latency_ms": 50.0,
        "degraded_latency_ms": 500.0,
        "error_threshold_ms": 1000.0
    }
)

# Generate incident data
generator = LatencyRegressionGenerator(context)
result = generator.generate()

print(f"Generated {result['metrics_count']} metrics")
print(f"Generated {result['logs_count']} logs")
```

## Core Classes

### IncidentContext

Container for incident generation session state.

```python
from generator.core.base import IncidentContext
from datetime import datetime, timedelta
from pathlib import Path

context = IncidentContext(
    incident_id="inc_123",              # Unique incident ID
    start_time=datetime.utcnow(),       # Incident start time
    duration=timedelta(hours=2),        # Incident duration
    severity="SEV2",                    # Severity: SEV1-SEV4
    affected_services=["api-service"],  # List of affected services
    root_cause="Connection pool exhaustion",
    output_dir=Path("./output"),        # Output directory
    topology={},                        # Service topology
    scenario_config={}                  # Scenario-specific config
)

# Useful methods
context.is_during_incident(timestamp)      # Check if time is during incident
context.get_incident_progress(timestamp)   # Get progress (0.0-1.0)
```

**See:** [API Reference - IncidentContext](api_reference.md#incidentcontext)

### BaseGenerator

Abstract base class for all generators.

```python
from generator.core.base import BaseGenerator

class CustomGenerator(BaseGenerator):
    def generate(self) -> dict:
        """Generate incident data."""
        # Generate metrics
        metrics = self._generate_metrics()
        self.save_jsonl(metrics, "metrics.jsonl", "metrics")

        # Generate logs
        logs = self._generate_logs()
        self.save_jsonl(logs, "logs.jsonl", "logs")

        return {
            "metrics_count": len(metrics),
            "logs_count": len(logs)
        }
```

**Common Methods:**
- `save_json(data, filename, subdir)` - Save as JSON
- `save_jsonl(records, filename, subdir)` - Save as JSON Lines
- `validate_output()` - Validate generated data

**See:** [API Reference - BaseGenerator](api_reference.md#basegenerator)

## Incident Generators

### Latency Regression

```python
from generator.incidents.latency_regression import LatencyRegressionGenerator

context.scenario_config = {
    "affected_service": "order-service",
    "baseline_latency_ms": 50.0,
    "degraded_latency_ms": 500.0,
    "error_threshold_ms": 1000.0
}

generator = LatencyRegressionGenerator(context)
result = generator.generate()
```

**See:** [API Reference - LatencyRegressionGenerator](api_reference.md#latencyregressiongenerator)

### Authentication Failure

```python
from generator.incidents.auth_failure import AuthFailureGenerator

context.scenario_config = {
    "affected_service": "auth-service",
    "baseline_error_rate": 0.001,  # 0.1%
    "spike_error_rate": 0.25       # 25%
}

generator = AuthFailureGenerator(context)
result = generator.generate()
```

**See:** [API Reference - AuthFailureGenerator](api_reference.md#authfailuregenerator)

### Dependency Outage

```python
from generator.incidents.dependency_outage import DependencyOutageGenerator

context.scenario_config = {
    "failed_service": "postgres-primary",
    "dependent_services": ["user-service", "order-service"]
}

generator = DependencyOutageGenerator(context)
result = generator.generate()
```

**See:** [API Reference - DependencyOutageGenerator](api_reference.md#dependencyoutagegenerator)

### Configuration Drift

```python
from generator.incidents.config_drift import ConfigDriftGenerator

context.scenario_config = {
    "affected_service": "payment-service",
    "config_key": "max_concurrent_transactions",
    "old_value": 100,
    "new_value": 10
}

generator = ConfigDriftGenerator(context)
result = generator.generate()
```

**See:** [API Reference - ConfigDriftGenerator](api_reference.md#configdriftgenerator)

### Packet Loss

```python
from generator.incidents.packet_loss import PacketLossGenerator

context.scenario_config = {
    "affected_services": ["order-service", "inventory-service"],
    "packet_loss_percent": 15.0
}

generator = PacketLossGenerator(context)
result = generator.generate()
```

**See:** [API Reference - PacketLossGenerator](api_reference.md#packetlossgenerator)

### Bursty Noise

```python
from generator.incidents.bursty_noise import BurstyNoiseGenerator

context.scenario_config = {
    "affected_service": "user-service",
    "burst_frequency_minutes": 5,
    "burst_duration_seconds": 30
}

generator = BurstyNoiseGenerator(context)
result = generator.generate()
```

**See:** [API Reference - BurstyNoiseGenerator](api_reference.md#burstnoisegenerator)

## Anomaly Injectors

### Latency Injector

```python
from generator.anomalies.injectors import LatencyInjector
from datetime import datetime, timedelta

injector = LatencyInjector(
    baseline_ms=50.0,
    anomaly_multiplier=10.0,
    spike_start=datetime.utcnow(),
    spike_duration=timedelta(minutes=15)
)

# Get latency value for timestamp
latency = injector.get_latency(timestamp)
```

**See:** [API Reference - LatencyInjector](api_reference.md#latencyinjector)

### Error Rate Injector

```python
from generator.anomalies.injectors import ErrorRateInjector

injector = ErrorRateInjector(
    baseline_error_rate=0.001,
    anomaly_error_rate=0.15,
    spike_start=datetime.utcnow(),
    spike_duration=timedelta(minutes=20)
)

# Check if request should error
if injector.should_error(timestamp):
    # Generate error
    pass

# Get error rate
error_rate = injector.get_error_rate(timestamp)
```

**See:** [API Reference - ErrorRateInjector](api_reference.md#errorrateinjector)

### Throughput Injector

```python
from generator.anomalies.injectors import ThroughputInjector

injector = ThroughputInjector(
    baseline_rps=100.0,
    anomaly_multiplier=0.3,  # 30% of baseline (drop)
    spike_start=datetime.utcnow(),
    spike_duration=timedelta(minutes=10)
)

# Get throughput value
throughput = injector.get_throughput(timestamp)
```

**See:** [API Reference - ThroughputInjector](api_reference.md#throughputinjector)

## Configuration

### Loading Configuration

```python
from generator.core.config import get_config, load_config
from pathlib import Path

# Get global config (auto-loads from .adapt-data.yaml)
config = get_config()

# Or load from specific path
config = load_config(Path(".adapt-data.yaml"))

# Access settings
log_level = config.logging.level
default_duration = config.generation.default_duration
random_seed = config.generation.random_seed
```

**See:** [API Reference - Configuration](api_reference.md#configuration)

### Creating Config Files

```python
from generator.core.config import create_default_config_file
from pathlib import Path

# Create default config file
create_default_config_file(Path(".adapt-data.yaml"))
```

**See:** [Configuration Guide](configuration.md)

## Utilities

### Timeline Generation

```python
from generator.core.timeline import TimelineGenerator

timeline_gen = TimelineGenerator(context)
timeline = timeline_gen.generate()

# Save timeline
timeline_gen.save(Path("./output/timelines/timeline.json"))
```

**See:** [API Reference - TimelineGenerator](api_reference.md#timelinegenerator)

### Topology Generation

```python
from generator.core.topology import TopologyGenerator

topo_gen = TopologyGenerator()
topology = topo_gen.generate_default_topology()

# Or custom topology
topology = topo_gen.generate_custom_topology(
    services=["api", "db", "cache"],
    dependencies=[("api", "db"), ("api", "cache")]
)
```

**See:** [API Reference - TopologyGenerator](api_reference.md#topologygenerator)

### Utility Functions

```python
from generator.core.utils import (
    generate_uuid,
    timestamp_to_iso,
    gaussian_noise,
    jitter,
    spike_pattern
)

# Generate unique ID
incident_id = generate_uuid()  # "inc_a1b2c3d4"

# Convert timestamp to ISO format
iso_time = timestamp_to_iso(datetime.utcnow())  # "2025-01-16T10:15:00.123456Z"

# Add noise
noisy_value = gaussian_noise(mean=100, stddev=10)

# Add jitter (±10%)
jittered = jitter(value=100, jitter_percent=0.1)

# Create spike pattern
value = spike_pattern(
    baseline=50.0,
    spike_multiplier=10.0,
    current_time=timestamp,
    spike_start=start_time,
    spike_duration=timedelta(minutes=15)
)
```

**See:** [API Reference - Utilities](api_reference.md#utilities)

## Validation

### Validating Generated Data

```python
from generator.core.base import BaseGenerator

generator = LatencyRegressionGenerator(context)
generator.generate()

# Validate output
issues = generator.validate_output()

print(f"Errors: {len(issues['errors'])}")
print(f"Warnings: {len(issues['warnings'])}")
print(f"Validation passed: {issues['summary']['validation_passed']}")

# Check specific issues
for error in issues['errors']:
    print(f"ERROR: {error}")

for warning in issues['warnings']:
    print(f"WARNING: {warning}")
```

**See:** [API Reference - Validation](api_reference.md#validation)

### Schema Validation

```python
from generator.core.validation import (
    validate_scenario,
    validate_metrics,
    validate_logs,
    validate_traces
)

# Validate scenario file
errors = validate_scenario(scenario_path)

# Validate generated data
metric_errors = validate_metrics(metrics_data)
log_errors = validate_logs(logs_data)
trace_errors = validate_traces(traces_data)
```

**See:** [API Reference - Schema Validation](api_reference.md#schema-validation)

## Exporters

### OpenTelemetry Exporter

```python
from generator.exporters.opentelemetry import OpenTelemetryExporter
from pathlib import Path

exporter = OpenTelemetryExporter(Path("./output"))

# Export traces
exporter.export_traces(Path("traces.json"))

# Export metrics
exporter.export_metrics(Path("metrics.json"))
```

**See:** [API Reference - OpenTelemetryExporter](api_reference.md#opentelemetryexporter)

### Prometheus Exporter

```python
from generator.exporters.prometheus import PrometheusExporter

exporter = PrometheusExporter(Path("./output"))

# Export to Prometheus text format
exporter.export_text_format(Path("metrics.prom"))

# Serve via HTTP
exporter.serve(port=9090, replay_speed=1.0)
```

**See:** [API Reference - PrometheusExporter](api_reference.md#prometheusexporter)

## Plugins

### Using Plugins

```python
from generator.core.plugins import get_plugin_registry

registry = get_plugin_registry()

# List available plugins
plugins = registry.list_plugins()
print(plugins['generators'])
print(plugins['exporters'])
print(plugins['analyzers'])

# Get specific plugin
custom_generator = registry.get_generator("my_custom_incident")
custom_exporter = registry.get_exporter("my_format")
```

**See:** [Plugin Development Guide](plugin_development.md)

### Creating Custom Plugins

```python
from generator.core.base import BaseGenerator

class MyCustomGenerator(BaseGenerator):
    name = "my_custom_incident"
    version = "1.0.0"
    description = "My custom incident type"

    def generate(self) -> dict:
        # Custom generation logic
        metrics = []
        logs = []

        # Generate data
        for timestamp in self._iterate_time_window():
            # ... generate metrics and logs
            pass

        # Save data
        self.save_jsonl(metrics, "metrics.jsonl", "metrics")
        self.save_jsonl(logs, "logs.jsonl", "logs")

        return {
            "metrics_count": len(metrics),
            "logs_count": len(logs)
        }
```

**See:** [Plugin Development Guide](plugin_development.md)

## Advanced Features

### Distributions

```python
from generator.core.distributions import (
    NormalDistribution,
    LogNormalDistribution,
    ExponentialDistribution,
    get_distribution
)

# Use predefined distribution
latency_dist = get_distribution("latency", mean=50.0, variance=100.0)
latency = latency_dist.sample()

# Create custom distribution
custom_dist = NormalDistribution(mean=100.0, stddev=15.0)
value = custom_dist.sample()
```

**See:** [API Reference - Distributions](api_reference.md#distributions)

### Patterns

```python
from generator.core.patterns import (
    DailyPattern,
    WeeklyPattern,
    BurstPattern,
    apply_pattern
)

# Apply daily business hours pattern
pattern = DailyPattern()
multiplier = pattern.apply(timestamp)
adjusted_value = baseline_value * multiplier

# Apply burst pattern
burst = BurstPattern(
    burst_frequency=timedelta(minutes=5),
    burst_duration=timedelta(seconds=30),
    burst_multiplier=3.0
)
value = baseline * burst.apply(timestamp)
```

**See:** [API Reference - Patterns](api_reference.md#patterns)

### Difficulty Levels

```python
from generator.core.difficulty import (
    DifficultyLevel,
    get_difficulty_config,
    calculate_score
)

# Get config for difficulty level
config = get_difficulty_config(DifficultyLevel.HARD)
print(config.num_services)      # 5-10
print(config.noise_level)       # 0.25
print(config.num_incidents)     # 2-3

# Calculate score
score = calculate_score(
    time_to_resolution=timedelta(minutes=15),
    hints_used=2,
    difficulty=DifficultyLevel.HARD
)
```

**See:** [API Reference - Difficulty](api_reference.md#difficulty)

## CLI Integration

### Running CLI Commands Programmatically

```python
import sys
from cli.generate import generate_incident
from cli.validate import validate_dataset
from pathlib import Path

# Generate incident
exit_code = generate_incident(
    scenario="latency_regression",
    output_dir=Path("./output"),
    duration="1h",
    severity="SEV2",
    difficulty="medium",
    global_config=None
)

# Validate dataset
exit_code = validate_dataset(
    dataset_dir=Path("./output"),
    strict=True
)
```

**See:** [API Reference - CLI](api_reference.md#cli-integration)

## Common Patterns

### Custom Metric Generation

```python
from generator.core.base import BaseGenerator
from datetime import timedelta

class CustomMetricGenerator(BaseGenerator):
    def _generate_metrics(self):
        metrics = []

        for timestamp in self._iterate_time_window(
            start_offset_minutes=-30,
            end_offset_minutes=30,
            step=timedelta(minutes=1)
        ):
            # Check if during incident
            is_incident = self.context.is_during_incident(timestamp)

            # Generate metric
            metric = {
                "timestamp": timestamp.isoformat() + "Z",
                "metric_name": "custom.metric",
                "value": self._calculate_value(timestamp, is_incident),
                "service": self.context.affected_services[0],
                "anomaly_injected": is_incident
            }
            metrics.append(metric)

        return metrics

    def _calculate_value(self, timestamp, is_incident):
        baseline = 100.0
        if is_incident:
            progress = self.context.get_incident_progress(timestamp)
            return baseline * (1 + progress * 5)  # Up to 6x during incident
        return baseline
```

### Custom Log Generation

```python
def _generate_logs(self):
    logs = []

    for timestamp in self._iterate_time_window(step=timedelta(seconds=10)):
        if not self._should_generate_log(probability=0.1):
            continue

        is_incident = self.context.is_during_incident(timestamp)

        log = {
            "timestamp": timestamp.isoformat() + "Z",
            "level": "ERROR" if is_incident and random.random() > 0.5 else "INFO",
            "service": self.context.affected_services[0],
            "message": self._generate_message(is_incident),
            "context": {}
        }
        logs.append(log)

    return logs
```

## Full Documentation

For complete API documentation with all classes, methods, and parameters, see:

- **[Full API Reference](api_reference.md)** - Complete API documentation
- **[Architecture](architecture.md)** - System design and internals
- **[Plugin Development](plugin_development.md)** - Creating custom plugins
- **[Schema Reference](schema.md)** - Data schemas and validation

## Examples

See the `examples/` directory for complete working examples:

- `examples/generate_example.py` - Basic generation
- `examples/plugins/example_custom_generator.py` - Custom generator
- `examples/plugins/example_exporter.py` - Custom exporter
- `examples/test_validation.py` - Validation examples

## Support

- **GitHub Issues**: Report bugs and request features
- **Discussions**: Ask questions and share ideas
- **Documentation**: Browse all guides at `/docs`
