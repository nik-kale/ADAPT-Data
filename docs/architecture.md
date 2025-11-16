# Architecture Documentation

This document describes the architecture and design of ADAPT-Data.

## Overview

ADAPT-Data follows a modular architecture with clear separation between:
- Core framework (base classes, utilities)
- Incident generators (scenario-specific logic)
- Anomaly injectors (reusable anomaly patterns)
- CLI interface (user-facing commands)

## Directory Structure

```
adapt-data/
├── generator/           # Core generation framework
│   ├── core/           # Base classes and utilities
│   │   ├── base.py     # BaseGenerator, IncidentContext
│   │   ├── timeline.py # Timeline generation
│   │   ├── topology.py # Service topology
│   │   └── utils.py    # Utility functions
│   ├── incidents/      # Incident-specific generators
│   │   ├── latency_regression.py
│   │   ├── auth_failure.py
│   │   ├── dependency_outage.py
│   │   ├── config_drift.py
│   │   ├── packet_loss.py
│   │   └── bursty_noise.py
│   └── anomalies/      # Anomaly injection utilities
│       └── injectors.py
├── cli/                # Command-line interface
│   ├── main.py         # CLI entry point
│   ├── generate.py     # Generate command
│   ├── validate.py     # Validate command
│   └── scenarios.py    # Scenario management
├── scenarios/          # YAML scenario definitions
├── schema/             # JSON schemas
├── incident_packs/     # Pre-generated datasets
└── docs/              # Documentation
```

## Core Components

### 1. IncidentContext

The `IncidentContext` class holds state for an incident generation session:

```python
@dataclass
class IncidentContext:
    incident_id: str
    start_time: datetime
    end_time: datetime
    duration: timedelta
    severity: str
    affected_services: list[str]
    root_cause: str
    output_dir: Path
    topology: dict[str, Any]
    scenario_config: dict[str, Any]
```

**Key Methods:**
- `is_during_incident(timestamp)`: Check if time is during incident
- `get_incident_progress(timestamp)`: Get progress (0.0 to 1.0)

### 2. BaseGenerator

Abstract base class for all generators:

```python
class BaseGenerator(ABC):
    def __init__(self, context: IncidentContext):
        self.context = context

    @abstractmethod
    def generate(self) -> dict[str, Any]:
        """Generate data for this component."""
        pass

    def save_json(self, data, filename, subdir=""):
        """Save data as JSON."""
        pass

    def save_jsonl(self, records, filename, subdir=""):
        """Save records as JSON Lines."""
        pass
```

**Design Pattern:**
All generators inherit from `BaseGenerator` and implement `generate()`. This ensures consistent interface and provides common functionality.

### 3. Anomaly Injectors

Reusable components for injecting anomalies into metrics:

- **LatencyInjector**: Spike latency during incident windows
- **ErrorRateInjector**: Increase error rates
- **ThroughputInjector**: Modify request throughput
- **MemoryLeakInjector**: Simulate memory leaks
- **CPUSpikeInjector**: Inject CPU usage spikes

**Example Usage:**
```python
injector = LatencyInjector(
    baseline_ms=50.0,
    anomaly_multiplier=10.0,
    spike_start=incident_start,
    spike_duration=timedelta(hours=1)
)

latency = injector.get_latency(current_timestamp)
```

### 4. Timeline Generator

Manages incident event timeline:

```python
timeline = TimelineGenerator(context)
timeline.add_deployment(time, service, old_ver, new_ver)
timeline.add_anomaly_detection(time, service, metric, threshold, value)
timeline.add_alert(time, service, alert_name, severity)
timeline.add_mitigation(time, service, action)
timeline.add_resolution(time, description)
result = timeline.generate()
```

### 5. Topology Generator

Generates service dependency graphs:

```python
topo = TopologyGenerator(context, services=[...])
topology = topo.generate()

# Query topology
downstream = topo.get_downstream_services("database")
upstream = topo.get_upstream_services("api-gateway")
```

## Data Flow

```
1. User invokes CLI
   └─> cli/main.py

2. Load scenario YAML
   └─> scenarios/latency_regression.yaml

3. Create IncidentContext
   └─> Sets time window, severity, output dir

4. Generate topology
   └─> TopologyGenerator creates service graph

5. Instantiate incident generator
   └─> LatencyRegressionGenerator(context, **params)

6. Generate telemetry
   ├─> _generate_logs()
   ├─> _generate_metrics()
   ├─> _generate_traces()
   ├─> _generate_config_deltas()
   └─> _generate_timeline()

7. Save outputs
   └─> JSONL files in output_dir/

8. Validate (optional)
   └─> cli/validate.py checks against schemas
```

## Incident Generator Pattern

Each incident generator follows this pattern:

```python
class MyIncidentGenerator(BaseGenerator):
    def __init__(self, context, **params):
        super().__init__(context)
        # Store params
        # Update context (affected_services, root_cause)

    def generate(self):
        logs = self._generate_logs()
        metrics = self._generate_metrics()
        traces = self._generate_traces()
        config = self._generate_config_deltas()
        timeline = self._generate_timeline()

        # Save all data
        self.save_jsonl(logs, "logs.jsonl", "logs")
        # ... etc

        return summary_dict

    def _generate_logs(self):
        # Create anomaly injectors
        # Iterate over time
        # Generate normal and anomalous logs
        return logs

    # Similar for metrics, traces, config, timeline
```

## Time-Based Generation

All generators iterate over time windows:

```python
current_time = context.start_time - timedelta(minutes=30)  # Pre-incident
end_time = context.end_time + timedelta(minutes=30)        # Post-incident

while current_time < end_time:
    is_during_incident = context.is_during_incident(current_time)

    if is_during_incident:
        # Generate anomalous data
        value = anomaly_injector.get_value(current_time)
    else:
        # Generate normal baseline data
        value = baseline + noise

    current_time += timedelta(seconds=1)
```

This creates realistic datasets with:
- Baseline behavior before incident
- Anomalous behavior during incident
- Recovery after incident

## Extensibility

### Adding New Incident Types

1. Create generator in `generator/incidents/`:

```python
class MyCustomGenerator(BaseGenerator):
    def __init__(self, context, my_param):
        super().__init__(context)
        self.my_param = my_param
        context.affected_services = ["my-service"]
        context.root_cause = "My custom root cause"

    def generate(self):
        # Implement generation logic
        pass
```

2. Register in `cli/generate.py`:

```python
GENERATOR_MAP = {
    # ...
    "my_custom": MyCustomGenerator,
}
```

3. Create scenario YAML:

```yaml
type: my_custom
description: My custom incident
parameters:
  my_param: value
```

### Adding New Anomaly Injectors

Create new injector in `generator/anomalies/injectors.py`:

```python
class MyAnomalyInjector:
    def __init__(self, baseline, spike_multiplier, ...):
        self.baseline = baseline
        # ...

    def get_value(self, timestamp):
        # Calculate anomalous value based on time
        return value
```

## Design Principles

1. **Separation of Concerns**: Core framework, incident logic, and CLI are separate
2. **Composition Over Inheritance**: Use injectors and utilities via composition
3. **Time-Based Simulation**: All data generation respects temporal ordering
4. **Schema-First**: All outputs conform to strict schemas
5. **Reproducibility**: Same scenario + seed = same output
6. **Extensibility**: Easy to add new incident types and anomalies

## Performance Considerations

- **Streaming Output**: Use JSONL for large datasets
- **Memory Efficiency**: Generate and write in chunks
- **Lazy Evaluation**: Don't materialize all data at once
- **Parallelization**: Future support for parallel generation

## Testing Strategy

1. **Unit Tests**: Test individual components (injectors, utils)
2. **Integration Tests**: Test full generation pipeline
3. **Schema Validation**: Ensure all output conforms to schemas
4. **Golden File Tests**: Compare against known-good outputs

## Future Enhancements

- Support for multi-region incidents
- Cross-service cascade failures
- Seasonal patterns and trends
- User-defined custom metrics
- Streaming output for large datasets
- Distributed generation for scale
