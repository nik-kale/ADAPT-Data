# API Reference

This document provides comprehensive API documentation for ADAPT-Data's core classes, configuration, distributions, patterns, plugins, and utilities.

## Table of Contents

- [Core Classes](#core-classes)
  - [IncidentContext](#incidentcontext)
  - [BaseGenerator](#basegenerator)
  - [TopologyGenerator](#topologygenerator)
  - [TimelineGenerator](#timelinegenerator)
- [Configuration Classes](#configuration-classes)
  - [AdaptDataConfig](#adaptdataconfig)
  - [DifficultyConfig](#difficultyconfig)
- [Distribution Classes](#distribution-classes)
- [Pattern Classes](#pattern-classes)
- [Plugin Classes](#plugin-classes)
- [Utility Functions](#utility-functions)

---

## Core Classes

### IncidentContext

Context object containing all information about an incident generation session.

**Module:** `generator.core.base`

#### Attributes

| Name | Type | Description | Default |
|------|------|-------------|---------|
| `incident_id` | `str` | Unique incident identifier | Auto-generated UUID |
| `start_time` | `datetime` | When the incident starts | `datetime.utcnow()` |
| `end_time` | `datetime` | When the incident ends | Computed from `start_time + duration` |
| `duration` | `timedelta` | Incident duration | `timedelta(hours=1)` |
| `severity` | `str` | Incident severity (SEV1-SEV4) | `"SEV3"` |
| `affected_services` | `list[str]` | List of affected service names | `[]` |
| `root_cause` | `str` | Root cause description | `""` |
| `output_dir` | `Path` | Directory to write output files | `Path("./output")` |
| `topology` | `dict[str, Any]` | System topology definition | `{}` |
| `scenario_config` | `dict[str, Any]` | Additional scenario configuration | `{}` |

#### Methods

##### `is_during_incident(timestamp: datetime) -> bool`

Check if a timestamp falls during the incident window.

**Parameters:**
- `timestamp` (datetime): Timestamp to check

**Returns:**
- `bool`: True if timestamp is during incident (start_time ≤ timestamp ≤ end_time)

**Example:**
```python
if context.is_during_incident(current_time):
    # Inject anomaly
    value = value * 10
```

##### `get_incident_progress(timestamp: datetime) -> float`

Get progress through incident as a ratio.

**Parameters:**
- `timestamp` (datetime): Current timestamp

**Returns:**
- `float`: Progress ratio (0.0 at start, 1.0 at end)

**Example:**
```python
progress = context.get_incident_progress(current_time)
severity_multiplier = 1.0 + (progress * 2.0)  # Gradually worsen
```

#### Example

```python
from datetime import datetime, timedelta
from pathlib import Path
from generator.core.base import IncidentContext

context = IncidentContext(
    start_time=datetime.utcnow(),
    duration=timedelta(hours=2),
    severity="SEV2",
    affected_services=["api-gateway", "auth-service"],
    root_cause="Database connection pool exhaustion",
    output_dir=Path("./output/incident-001"),
    topology={"services": [...], "dependencies": [...]},
    scenario_config={"custom_param": "value"}
)

print(context.incident_id)  # e.g., "a1b2c3d4-..."
print(context.is_during_incident(datetime.utcnow()))  # True
```

---

### BaseGenerator

Abstract base class for all data generators. Provides common functionality for saving data and accessing context.

**Module:** `generator.core.base`

#### Constructor

```python
def __init__(self, context: IncidentContext) -> None
```

**Parameters:**
- `context` (IncidentContext): Incident context object

#### Abstract Methods

##### `generate() -> dict[str, Any]`

Generate data for this component. Must be implemented by subclasses.

**Returns:**
- `dict[str, Any]`: Dictionary containing generation results and statistics

#### Helper Methods

##### `save_json(data: Any, filename: str, subdir: str = "") -> Path`

Save data as JSON file.

**Parameters:**
- `data` (Any): Data to save
- `filename` (str): Output filename
- `subdir` (str, optional): Subdirectory within output_dir

**Returns:**
- `Path`: Path to saved file

**Example:**
```python
topology = {"services": [...], "dependencies": [...]}
path = self.save_json(topology, "topology.json", "topology")
```

##### `save_jsonl(records: list[dict[str, Any]], filename: str, subdir: str = "") -> Path`

Save records as JSON Lines file (one JSON object per line).

**Parameters:**
- `records` (list[dict]): List of records to save
- `filename` (str): Output filename
- `subdir` (str, optional): Subdirectory within output_dir

**Returns:**
- `Path`: Path to saved file

**Example:**
```python
logs = [
    {"timestamp": "...", "level": "ERROR", "message": "..."},
    {"timestamp": "...", "level": "INFO", "message": "..."}
]
self.save_jsonl(logs, f"logs_{context.incident_id}.jsonl", "logs")
```

##### `_get_service_hosts(service_name: str) -> list[str]`

Get list of host identifiers for a service.

**Parameters:**
- `service_name` (str): Service name

**Returns:**
- `list[str]`: List of host identifiers (e.g., `["api-gateway-000", "api-gateway-001"]`)

**Example:**
```python
hosts = self._get_service_hosts("api-gateway")
for host in hosts:
    # Generate metrics for each host
    pass
```

##### `_iterate_time_window(start_offset_minutes: int = -30, end_offset_minutes: int = 30, step: timedelta = timedelta(seconds=1))`

Iterate over time window for data generation.

**Parameters:**
- `start_offset_minutes` (int): Minutes before incident start (negative value). Default: -30
- `end_offset_minutes` (int): Minutes after incident end (positive value). Default: 30
- `step` (timedelta): Time step between iterations. Default: 1 second

**Yields:**
- `datetime`: Current timestamp in the iteration

**Example:**
```python
metrics = []
for current_time in self._iterate_time_window(step=timedelta(minutes=1)):
    metric = {
        "timestamp": timestamp_to_iso(current_time),
        "value": sample_distribution(),
        # ...
    }
    metrics.append(metric)
```

##### `validate_output() -> dict[str, Any]`

Validate generated output data quality.

**Returns:**
- `dict[str, Any]`: Validation results with errors, warnings, info, and summary

**Example:**
```python
result = generator.generate()
validation = generator.validate_output()
if not validation["summary"]["validation_passed"]:
    print(f"Validation errors: {validation['errors']}")
```

#### Example Implementation

```python
from generator.core.base import BaseGenerator, IncidentContext

class MyGenerator(BaseGenerator):
    def __init__(self, context: IncidentContext, **params):
        super().__init__(context)
        self.my_param = params.get('my_param', 'default')

    def generate(self) -> dict[str, Any]:
        logs = self._generate_logs()
        metrics = self._generate_metrics()

        self.save_jsonl(logs, f"logs_{self.context.incident_id}.jsonl", "logs")
        self.save_jsonl(metrics, f"metrics_{self.context.incident_id}.jsonl", "metrics")

        return {
            "incident_id": self.context.incident_id,
            "log_count": len(logs),
            "metric_count": len(metrics)
        }

    def _generate_logs(self) -> list[dict]:
        # Implementation
        pass

    def _generate_metrics(self) -> list[dict]:
        # Implementation
        pass
```

---

### TopologyGenerator

Generates service topology graphs representing system architecture.

**Module:** `generator.core.topology`

#### Constructor

```python
def __init__(
    self,
    context: IncidentContext,
    services: Optional[list[dict[str, Any]]] = None
) -> None
```

**Parameters:**
- `context` (IncidentContext): Incident context
- `services` (list[dict], optional): Custom service definitions. If None, generates default microservices topology

#### Methods

##### `generate() -> dict[str, Any]`

Generate complete topology with services and dependencies.

**Returns:**
- `dict[str, Any]`: Topology definition with keys:
  - `services`: List of service definitions
  - `dependencies`: List of dependency edges

**Example:**
```python
from generator.core.topology import TopologyGenerator

topo_gen = TopologyGenerator(context)
topology = topo_gen.generate()

print(f"Services: {len(topology['services'])}")
print(f"Dependencies: {len(topology['dependencies'])}")
```

##### `get_downstream_services(service_name: str) -> list[str]`

Get services that depend on the given service.

**Parameters:**
- `service_name` (str): Service to check

**Returns:**
- `list[str]`: List of downstream service names

**Example:**
```python
# Find all services that depend on the database
downstream = topo_gen.get_downstream_services("postgres-primary")
# Returns: ["user-service", "order-service", "auth-service", ...]
```

##### `get_upstream_services(service_name: str) -> list[str]`

Get services that the given service depends on.

**Parameters:**
- `service_name` (str): Service to check

**Returns:**
- `list[str]`: List of upstream service names

**Example:**
```python
# Find what the order service depends on
upstream = topo_gen.get_upstream_services("order-service")
# Returns: ["postgres-primary", "inventory-service", "payment-service", ...]
```

#### Service Definition Format

```python
{
    "name": "api-gateway",
    "type": "gateway",
    "instances": 3,
    "region": "us-east-1",
    "metadata": {
        "version": "1.2.3",
        "tier": "critical",
        "sla_target": 99.9
    }
}
```

#### Dependency Definition Format

```python
{
    "from": "api-gateway",
    "to": "auth-service",
    "type": "http",
    "critical": True
}
```

---

### TimelineGenerator

Generates incident timelines with events, alerts, and milestones.

**Module:** `generator.core.timeline`

#### Constructor

```python
def __init__(self, context: IncidentContext) -> None
```

**Parameters:**
- `context` (IncidentContext): Incident context

#### Methods

##### `add_event(timestamp: datetime, event_type: str, description: str, service: str = "", metadata: dict[str, Any] | None = None) -> None`

Add a generic event to the timeline.

**Parameters:**
- `timestamp` (datetime): When the event occurred
- `event_type` (str): Type of event
- `description` (str): Human-readable description
- `service` (str, optional): Service name
- `metadata` (dict, optional): Additional metadata

**Example:**
```python
timeline_gen.add_event(
    timestamp=datetime.utcnow(),
    event_type="incident_detected",
    description="High error rate detected",
    service="api-gateway",
    metadata={"error_rate": 15.2}
)
```

##### `add_anomaly_detection(timestamp: datetime, service: str, metric: str, threshold: float, actual_value: float) -> None`

Add an anomaly detection event.

**Parameters:**
- `timestamp` (datetime): When anomaly was detected
- `service` (str): Affected service
- `metric` (str): Metric name
- `threshold` (float): Threshold value
- `actual_value` (float): Actual observed value

##### `add_alert(timestamp: datetime, service: str, alert_name: str, severity: str = "warning") -> None`

Add an alert event.

**Parameters:**
- `timestamp` (datetime): When alert fired
- `service` (str): Affected service
- `alert_name` (str): Name of the alert
- `severity` (str): Alert severity (warning, critical, etc.)

##### `add_config_change(timestamp: datetime, service: str, change_description: str, initiator: str = "automated") -> None`

Add a configuration change event.

##### `add_deployment(timestamp: datetime, service: str, old_version: str, new_version: str) -> None`

Add a deployment event.

##### `add_mitigation(timestamp: datetime, service: str, action: str) -> None`

Add a mitigation attempt event.

##### `add_resolution(timestamp: datetime, description: str) -> None`

Add incident resolution event.

##### `generate() -> dict[str, Any]`

Generate complete timeline document.

**Returns:**
- `dict[str, Any]`: Timeline with sorted events

#### Example

```python
from generator.core.timeline import TimelineGenerator

timeline_gen = TimelineGenerator(context)

# Add events
timeline_gen.add_anomaly_detection(
    timestamp=context.start_time,
    service="api-gateway",
    metric="latency_p95",
    threshold=500,
    actual_value=2500
)

timeline_gen.add_alert(
    timestamp=context.start_time + timedelta(minutes=2),
    service="api-gateway",
    alert_name="HighLatency",
    severity="critical"
)

timeline_gen.add_mitigation(
    timestamp=context.start_time + timedelta(minutes=10),
    service="api-gateway",
    action="Scaled up from 3 to 6 instances"
)

timeline_gen.add_resolution(
    timestamp=context.end_time,
    description="Fixed connection pool configuration and scaled back to 3 instances"
)

timeline = timeline_gen.generate()
```

---

## Configuration Classes

### AdaptDataConfig

Main configuration class for ADAPT-Data settings.

**Module:** `generator.core.config`

#### Attributes

| Name | Type | Description |
|------|------|-------------|
| `logging` | `LoggingConfig` | Logging configuration |
| `generation` | `GenerationConfig` | Default generation settings |
| `validation` | `ValidationConfig` | Validation settings |
| `export` | `ExportConfig` | Export settings |
| `advanced` | `AdvancedConfig` | Advanced settings |

#### Sub-Configuration Classes

##### LoggingConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `level` | `str` | `"INFO"` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `enable_colors` | `bool` | `True` | Enable colored output |
| `log_file` | `str \| None` | `None` | Log file path |

##### GenerationConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `default_duration` | `str` | `"1h"` | Default incident duration |
| `default_severity` | `str` | `"SEV3"` | Default severity level |
| `default_output_dir` | `str` | `"./output"` | Default output directory |
| `enable_progress` | `bool` | `True` | Show progress indicators |
| `parallel_generation` | `bool` | `False` | Enable parallel generation |
| `random_seed` | `int \| None` | `None` | Random seed for reproducibility |

##### ValidationConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `strict_mode` | `bool` | `False` | Enable strict validation |
| `max_scenario_size_mb` | `int` | `1` | Max scenario file size in MB |
| `validate_on_generation` | `bool` | `True` | Validate output after generation |

##### ExportConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `default_format` | `str` | `"opentelemetry"` | Default export format |
| `prometheus_port` | `int` | `9090` | Default Prometheus port |
| `replay_speed` | `float` | `1.0` | Default replay speed |

##### AdvancedConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enable_distributions` | `bool` | `True` | Use parameterized distributions |
| `enable_patterns` | `bool` | `True` | Apply time-series patterns |
| `enable_correlation` | `bool` | `True` | Generate correlated anomalies |
| `noise_level` | `float` | `0.1` | Base noise level (0-1) |

#### Functions

##### `load_config(config_path: Optional[Path] = None, force_reload: bool = False) -> AdaptDataConfig`

Load configuration from file or use defaults.

**Parameters:**
- `config_path` (Path, optional): Path to config file (auto-detected if None)
- `force_reload` (bool): Force reload even if already loaded

**Returns:**
- `AdaptDataConfig`: Configuration object

##### `get_config() -> AdaptDataConfig`

Get global configuration instance.

**Returns:**
- `AdaptDataConfig`: Configuration object (loads if not already loaded)

#### Example

```python
from generator.core.config import get_config, load_config

# Use auto-detected config
config = get_config()
print(config.generation.default_duration)  # "1h"
print(config.logging.level)  # "INFO"

# Load specific config file
config = load_config(Path("/path/to/.adapt-data.yaml"))

# Access nested settings
if config.advanced.enable_distributions:
    # Use distributions
    pass
```

#### Configuration File Example

```yaml
# .adapt-data.yaml
logging:
  level: DEBUG
  enable_colors: true

generation:
  default_duration: 2h
  default_severity: SEV2
  default_output_dir: ./incidents
  enable_progress: true
  random_seed: 42

validation:
  strict_mode: false
  validate_on_generation: true

advanced:
  enable_distributions: true
  enable_patterns: true
  noise_level: 0.15
```

---

### DifficultyConfig

Configuration for difficulty levels in challenge scenarios.

**Module:** `generator.core.difficulty`

#### DifficultyLevel Enum

| Level | Numeric Value | Description |
|-------|---------------|-------------|
| `BEGINNER` | 1 | Simple scenarios for learning |
| `EASY` | 2 | Basic incidents with clear signals |
| `MEDIUM` | 3 | Moderate complexity with some noise |
| `HARD` | 4 | Complex scenarios with red herrings |
| `EXPERT` | 5 | Advanced scenarios with subtle correlations |

#### Attributes

| Name | Type | Description |
|------|------|-------------|
| `level` | `DifficultyLevel` | Difficulty level enum |
| `num_services` | `int` | Number of services in topology |
| `num_incidents` | `int` | Number of incidents in cascade |
| `noise_level` | `float` | Amount of noise/red herrings (0-1) |
| `correlation_strength` | `float` | How obvious correlations are (0-1) |
| `hint_availability` | `int` | Number of hints available |
| `time_limit_minutes` | `int \| None` | Suggested time limit |
| `log_volume_multiplier` | `float` | Log entry multiplier |
| `metric_density` | `float` | Metrics per minute |
| `trace_complexity` | `int` | Average spans per trace |

#### Functions

##### `get_difficulty_config(level: DifficultyLevel) -> DifficultyConfig`

Get predefined configuration for a difficulty level.

**Parameters:**
- `level` (DifficultyLevel): Difficulty level

**Returns:**
- `DifficultyConfig`: Configuration for that level

##### `calculate_score(difficulty: DifficultyLevel, time_taken_minutes: float, hints_used: int, correct: bool) -> dict[str, Any]`

Calculate score for a challenge attempt.

**Parameters:**
- `difficulty` (DifficultyLevel): Challenge difficulty
- `time_taken_minutes` (float): Time taken in minutes
- `hints_used` (int): Number of hints used
- `correct` (bool): Whether solution was correct

**Returns:**
- `dict`: Score breakdown with total_score, breakdown, and rank

#### Example

```python
from generator.core.difficulty import (
    DifficultyLevel,
    get_difficulty_config,
    calculate_score
)

# Get difficulty configuration
difficulty = DifficultyLevel.MEDIUM
config = get_difficulty_config(difficulty)

print(f"Services: {config.num_services}")  # 8
print(f"Noise level: {config.noise_level}")  # 0.3
print(f"Time limit: {config.time_limit_minutes} min")  # 30

# Calculate score for attempt
score_result = calculate_score(
    difficulty=DifficultyLevel.HARD,
    time_taken_minutes=30,
    hints_used=1,
    correct=True
)

print(score_result)
# {
#     "total_score": 440,
#     "breakdown": {
#         "base": 100,
#         "time_bonus": 25,
#         "hint_penalty": -10,
#         "difficulty_multiplier": 4
#     },
#     "rank": "Expert"
# }
```

---

## Distribution Classes

Probability distributions for realistic data generation.

**Module:** `generator.core.distributions`

### Base Class: Distribution

All distributions inherit from this abstract base class.

#### Methods

##### `sample() -> float`

Sample a value from the distribution.

**Returns:**
- `float`: Sampled value

##### `sample_int(min_val: int = 0, max_val: int = 100) -> int`

Sample an integer value with clipping.

**Parameters:**
- `min_val` (int): Minimum value
- `max_val` (int): Maximum value

**Returns:**
- `int`: Integer sample clipped to range

---

### 1. UniformDistribution

Uniform distribution between min and max values.

#### Constructor

```python
UniformDistribution(min_val: float = 0.0, max_val: float = 1.0)
```

**Parameters:**
- `min_val` (float): Minimum value
- `max_val` (float): Maximum value

#### Example

```python
from generator.core.distributions import UniformDistribution

dist = UniformDistribution(min_val=0, max_val=100)
value = dist.sample()  # Random value between 0 and 100
```

---

### 2. NormalDistribution

Normal (Gaussian) distribution.

#### Constructor

```python
NormalDistribution(mean: float = 0.0, std: float = 1.0)
```

**Parameters:**
- `mean` (float): Mean value (center of distribution)
- `std` (float): Standard deviation (spread)

#### Example

```python
from generator.core.distributions import NormalDistribution

# CPU usage around 60% with 10% std dev
cpu_dist = NormalDistribution(mean=60, std=10)
cpu_value = cpu_dist.sample()
```

---

### 3. ExponentialDistribution

Exponential distribution for modeling time between events.

#### Constructor

```python
ExponentialDistribution(rate: float = 1.0)
```

**Parameters:**
- `rate` (float): Rate parameter (lambda). Higher values mean shorter intervals.

#### Example

```python
from generator.core.distributions import ExponentialDistribution

# Error rate with low frequency
error_dist = ExponentialDistribution(rate=100)
error_rate = error_dist.sample()  # Typically small values
```

---

### 4. LogNormalDistribution

Log-normal distribution for modeling multiplicative processes.

#### Constructor

```python
LogNormalDistribution(mu: float = 0.0, sigma: float = 1.0)
```

**Parameters:**
- `mu` (float): Mean of underlying normal distribution
- `sigma` (float): Standard deviation of underlying normal distribution

#### Example

```python
from generator.core.distributions import LogNormalDistribution

# Latency distribution (right-skewed)
latency_dist = LogNormalDistribution(mu=3.5, sigma=0.5)
latency_ms = latency_dist.sample()  # ~50ms typical, with long tail
```

---

### 5. PoissonDistribution

Poisson distribution for modeling count data.

#### Constructor

```python
PoissonDistribution(lambda_: float = 1.0)
```

**Parameters:**
- `lambda_` (float): Rate parameter (average number of events)

#### Example

```python
from generator.core.distributions import PoissonDistribution

# Number of requests per second
request_dist = PoissonDistribution(lambda_=10.0)
request_count = int(request_dist.sample())
```

---

### 6. WeibullDistribution

Weibull distribution for modeling failure rates and lifetimes.

#### Constructor

```python
WeibullDistribution(shape: float = 1.0, scale: float = 1.0)
```

**Parameters:**
- `shape` (float): Shape parameter (k). Controls distribution shape.
- `scale` (float): Scale parameter (lambda). Controls spread.

#### Example

```python
from generator.core.distributions import WeibullDistribution

# Disk I/O throughput
io_dist = WeibullDistribution(shape=1.5, scale=100)
io_mbps = io_dist.sample()
```

---

### 7. BimodalDistribution

Bimodal distribution combining two normal distributions.

#### Constructor

```python
BimodalDistribution(
    mean1: float = 0.0,
    std1: float = 1.0,
    mean2: float = 5.0,
    std2: float = 1.0,
    mix: float = 0.5
)
```

**Parameters:**
- `mean1` (float): Mean of first mode
- `std1` (float): Std deviation of first mode
- `mean2` (float): Mean of second mode
- `std2` (float): Std deviation of second mode
- `mix` (float): Mixing proportion for first mode (0-1)

#### Example

```python
from generator.core.distributions import BimodalDistribution

# CPU usage: mostly 20% (normal), sometimes 80% (under load)
cpu_dist = BimodalDistribution(
    mean1=20, std1=5,
    mean2=80, std2=10,
    mix=0.9  # 90% normal, 10% high load
)
cpu_value = cpu_dist.sample()
```

---

### DistributionFactory

Factory for creating distributions from configuration dictionaries.

#### Method

##### `create(config: dict[str, Any]) -> Distribution`

Create distribution from configuration.

**Parameters:**
- `config` (dict): Configuration with 'type' and parameters

**Returns:**
- `Distribution`: Distribution instance

**Raises:**
- `ValueError`: If distribution type is unknown

#### Example

```python
from generator.core.distributions import DistributionFactory

# Create from config
config = {
    'type': 'normal',
    'mean': 100,
    'std': 15
}
dist = DistributionFactory.create(config)
value = dist.sample()

# All supported types:
configs = [
    {'type': 'uniform', 'min': 0, 'max': 100},
    {'type': 'normal', 'mean': 50, 'std': 10},
    {'type': 'exponential', 'rate': 2.0},
    {'type': 'lognormal', 'mu': 3.0, 'sigma': 0.5},
    {'type': 'poisson', 'lambda': 5.0},
    {'type': 'weibull', 'shape': 2.0, 'scale': 100},
    {'type': 'bimodal', 'mean1': 20, 'std1': 5, 'mean2': 80, 'std2': 10, 'mix': 0.7}
]
```

---

### Predefined Distributions

Commonly used distributions for telemetry data.

```python
from generator.core.distributions import (
    LATENCY_DISTRIBUTION,      # LogNormal(mu=3.5, sigma=0.5) ~50ms
    ERROR_RATE_DISTRIBUTION,   # Exponential(rate=100) - low error rate
    THROUGHPUT_DISTRIBUTION,   # Normal(mean=1000, std=100) requests/sec
    CPU_DISTRIBUTION,          # Bimodal - mostly 20%, sometimes 80%
    MEMORY_DISTRIBUTION,       # Normal(mean=60, std=10) percent
    DISK_IO_DISTRIBUTION       # Weibull(shape=1.5, scale=100) MB/s
)

# Usage
latency = LATENCY_DISTRIBUTION.sample()
```

---

## Pattern Classes

Time-series patterns for realistic temporal behavior.

**Module:** `generator.core.patterns`

### Base Class: TimeSeriesPattern

All patterns inherit from this abstract base class.

#### Methods

##### `apply(base_value: float, timestamp: datetime) -> float`

Apply pattern to base value at given timestamp.

**Parameters:**
- `base_value` (float): Base value to modify
- `timestamp` (datetime): Current timestamp

**Returns:**
- `float`: Modified value with pattern applied

---

### 1. SeasonalPattern

Seasonal pattern with configurable period and amplitude.

#### Constructor

```python
SeasonalPattern(
    period_hours: float = 24.0,
    amplitude: float = 0.3,
    phase_shift: float = 0.0,
    baseline_time: Optional[datetime] = None
)
```

**Parameters:**
- `period_hours` (float): Period length in hours (24=daily, 168=weekly)
- `amplitude` (float): Pattern amplitude as fraction of base value (0-1)
- `phase_shift` (float): Phase shift in radians
- `baseline_time` (datetime, optional): Reference time for phase calculation

#### Example

```python
from generator.core.patterns import SeasonalPattern

# Daily pattern with peak at 2pm
daily_pattern = SeasonalPattern(
    period_hours=24.0,
    amplitude=0.3,
    phase_shift=math.pi / 6  # Peak at 14:00
)

base_traffic = 1000
actual_traffic = daily_pattern.apply(base_traffic, datetime.utcnow())
```

---

### 2. TrendPattern

Linear or exponential trend over time.

#### Constructor

```python
TrendPattern(
    trend_type: str = "linear",
    rate: float = 0.01,
    baseline_time: Optional[datetime] = None
)
```

**Parameters:**
- `trend_type` (str): Type of trend ('linear' or 'exponential')
- `rate` (float): Rate of change per hour
- `baseline_time` (datetime, optional): Reference time for trend calculation

#### Example

```python
from generator.core.patterns import TrendPattern

# Growing load: 1% increase per hour
growth = TrendPattern(trend_type='linear', rate=0.01)

# Exponential growth (e.g., memory leak)
leak = TrendPattern(trend_type='exponential', rate=0.05)

base_memory = 60
memory_with_leak = leak.apply(base_memory, datetime.utcnow())
```

---

### 3. CyclicalPattern

Multiple overlapping cycles (e.g., daily + weekly).

#### Constructor

```python
CyclicalPattern(patterns: list[SeasonalPattern])
```

**Parameters:**
- `patterns` (list[SeasonalPattern]): List of seasonal patterns to combine

#### Example

```python
from generator.core.patterns import CyclicalPattern, SeasonalPattern

# Combine daily and weekly patterns
daily = SeasonalPattern(period_hours=24, amplitude=0.3)
weekly = SeasonalPattern(period_hours=168, amplitude=0.2)

cyclical = CyclicalPattern([daily, weekly])
value = cyclical.apply(1000, datetime.utcnow())
```

---

### 4. BurstPattern

Periodic bursts or spikes.

#### Constructor

```python
BurstPattern(
    burst_interval_minutes: int = 60,
    burst_duration_minutes: int = 5,
    burst_multiplier: float = 3.0,
    baseline_time: Optional[datetime] = None
)
```

**Parameters:**
- `burst_interval_minutes` (int): Time between bursts
- `burst_duration_minutes` (int): Duration of each burst
- `burst_multiplier` (float): Multiplier during burst
- `baseline_time` (datetime, optional): Reference time

#### Example

```python
from generator.core.patterns import BurstPattern

# Hourly batch job: 5 minutes every hour, 5x load
batch_job = BurstPattern(
    burst_interval_minutes=60,
    burst_duration_minutes=5,
    burst_multiplier=5.0
)

base_load = 100
current_load = batch_job.apply(base_load, datetime.utcnow())
```

---

### 5. NoisePattern

Random noise overlay for realism.

#### Constructor

```python
NoisePattern(
    noise_level: float = 0.1,
    seed: Optional[int] = None
)
```

**Parameters:**
- `noise_level` (float): Noise amplitude as fraction of value (0-1)
- `seed` (int, optional): Random seed for reproducibility

#### Example

```python
from generator.core.patterns import NoisePattern

# Add 5% random noise
noise = NoisePattern(noise_level=0.05)

clean_value = 100
noisy_value = noise.apply(clean_value, datetime.utcnow())
# Result: ~95-105 with Gaussian distribution
```

---

### 6. CompositePattern

Combines multiple patterns for complex behavior.

#### Constructor

```python
CompositePattern(patterns: list[TimeSeriesPattern])
```

**Parameters:**
- `patterns` (list[TimeSeriesPattern]): List of patterns to apply in order

#### Example

```python
from generator.core.patterns import (
    CompositePattern,
    TrendPattern,
    SeasonalPattern,
    NoisePattern
)

# Complex pattern: growing load + daily variation + noise
pattern = CompositePattern([
    TrendPattern(trend_type='linear', rate=0.01),
    SeasonalPattern(period_hours=24, amplitude=0.3),
    NoisePattern(noise_level=0.05)
])

value = pattern.apply(1000, datetime.utcnow())
```

---

### Predefined Pattern Creators

Helper functions for common patterns.

#### `create_daily_pattern(amplitude: float = 0.3) -> SeasonalPattern`

Create daily pattern with peak at 2pm.

#### `create_weekly_pattern(amplitude: float = 0.2) -> SeasonalPattern`

Create weekly pattern with lower weekend traffic.

#### `create_business_hours_pattern() -> CompositePattern`

Create realistic business hours pattern (daily + weekly + noise).

#### `create_growth_pattern(rate: float = 0.001) -> CompositePattern`

Create growing load pattern with daily variation.

#### `create_batch_job_pattern() -> CompositePattern`

Create pattern for hourly batch jobs.

#### Example

```python
from generator.core.patterns import (
    create_business_hours_pattern,
    create_batch_job_pattern,
    create_growth_pattern
)

# Realistic business hours traffic
business_pattern = create_business_hours_pattern()
traffic = business_pattern.apply(1000, datetime.utcnow())

# Batch processing
batch_pattern = create_batch_job_pattern()
load = batch_pattern.apply(100, datetime.utcnow())

# Gradual growth
growth_pattern = create_growth_pattern(rate=0.002)
growing_load = growth_pattern.apply(500, datetime.utcnow())
```

---

## Plugin Classes

Plugin system for extending ADAPT-Data.

**Module:** `generator.core.plugins`

### GeneratorPlugin

Base class for custom incident generator plugins.

#### Properties

| Name | Type | Description |
|------|------|-------------|
| `name` | `str` | Plugin name (abstract) |
| `version` | `str` | Plugin version (abstract) |
| `description` | `str` | Plugin description |

#### Methods

##### `initialize() -> None`

Initialize the plugin. Called when plugin is loaded.

##### `generate(context: Any, **kwargs) -> dict[str, Any]`

Generate incident data.

**Parameters:**
- `context` (Any): Incident context
- `**kwargs`: Generator-specific parameters

**Returns:**
- `dict[str, Any]`: Generation result

#### Example

```python
from generator.core.plugins import GeneratorPlugin
from generator.core.base import BaseGenerator, IncidentContext

class MyGenerator(BaseGenerator):
    def __init__(self, context: IncidentContext, **params):
        super().__init__(context)
        self.custom_param = params.get('custom_param', 'default')

    def generate(self) -> dict:
        # Implementation
        return {"incident_id": self.context.incident_id}

class MyGeneratorPlugin(GeneratorPlugin):
    name = "my_custom_generator"
    version = "1.0.0"
    description = "My custom incident generator"

    def initialize(self) -> None:
        # Setup code
        pass

    def generate(self, context, **kwargs):
        generator = MyGenerator(context, **kwargs)
        return generator.generate()

# Export plugin
plugin = MyGeneratorPlugin()
```

---

### ExporterPlugin

Base class for custom exporter plugins.

#### Methods

##### `export(dataset_dir: Path, output_path: Path, **kwargs) -> None`

Export dataset to custom format.

**Parameters:**
- `dataset_dir` (Path): Dataset directory
- `output_path` (Path): Output file path
- `**kwargs`: Exporter-specific parameters

#### Example

```python
from pathlib import Path
from generator.core.plugins import ExporterPlugin

class JSONExporter:
    def __init__(self, dataset_dir: Path):
        self.dataset_dir = dataset_dir

    def export(self, output_path: Path):
        # Load and export data
        pass

class JSONExporterPlugin(ExporterPlugin):
    name = "json"
    version = "1.0.0"
    description = "Export to JSON format"

    def initialize(self) -> None:
        pass

    def export(self, dataset_dir: Path, output_path: Path, **kwargs) -> None:
        exporter = JSONExporter(dataset_dir)
        exporter.export(output_path)

plugin = JSONExporterPlugin()
```

---

### AnalyzerPlugin

Base class for custom analyzer plugins.

#### Methods

##### `analyze(dataset_dir: Path) -> dict[str, Any]`

Analyze dataset.

**Parameters:**
- `dataset_dir` (Path): Dataset directory

**Returns:**
- `dict[str, Any]`: Analysis results

#### Example

```python
from pathlib import Path
from generator.core.plugins import AnalyzerPlugin

class ErrorRateAnalyzer:
    def __init__(self, dataset_dir: Path):
        self.dataset_dir = dataset_dir

    def analyze(self) -> dict:
        # Perform analysis
        return {"error_rate": 0.05}

class ErrorRateAnalyzerPlugin(AnalyzerPlugin):
    name = "error_rate_analyzer"
    version = "1.0.0"
    description = "Analyzes error rates"

    def initialize(self) -> None:
        pass

    def analyze(self, dataset_dir: Path) -> dict:
        analyzer = ErrorRateAnalyzer(dataset_dir)
        return analyzer.analyze()

plugin = ErrorRateAnalyzerPlugin()
```

---

### PluginRegistry

Registry for managing plugins.

#### Methods

##### `register_generator(plugin_class: Type[GeneratorPlugin]) -> None`

Register a generator plugin.

##### `register_exporter(plugin_class: Type[ExporterPlugin]) -> None`

Register an exporter plugin.

##### `register_analyzer(plugin_class: Type[AnalyzerPlugin]) -> None`

Register an analyzer plugin.

##### `get_generator(name: str) -> Optional[GeneratorPlugin]`

Get generator plugin by name.

##### `get_exporter(name: str) -> Optional[ExporterPlugin]`

Get exporter plugin by name.

##### `get_analyzer(name: str) -> Optional[AnalyzerPlugin]`

Get analyzer plugin by name.

##### `list_plugins() -> dict[str, list[str]]`

List all registered plugins.

**Returns:**
- `dict`: Dictionary with keys 'generators', 'exporters', 'analyzers'

##### `load_from_directory(plugin_dir: Path) -> None`

Load plugins from a directory.

#### Example

```python
from pathlib import Path
from generator.core.plugins import get_plugin_registry

# Get global registry
registry = get_plugin_registry()

# List all plugins
plugins = registry.list_plugins()
print(f"Generators: {plugins['generators']}")
print(f"Exporters: {plugins['exporters']}")
print(f"Analyzers: {plugins['analyzers']}")

# Get specific plugin
generator = registry.get_generator("latency_regression")
if generator:
    result = generator.generate(context)

# Load custom plugins
registry.load_from_directory(Path("~/.adapt-data/plugins"))
```

---

## Utility Functions

Common utility functions for data generation.

**Module:** `generator.core.utils`

### generate_id

Generate a random identifier.

```python
def generate_id(prefix: str = "", length: int = 16) -> str
```

**Parameters:**
- `prefix` (str): Optional prefix for the ID
- `length` (int): Length of the random part

**Returns:**
- `str`: Generated identifier

**Example:**
```python
from generator.core.utils import generate_id

trace_id = generate_id(prefix="trace-", length=16)
# Result: "trace-a1b2c3d4e5f6g7h8"
```

---

### generate_uuid

Generate a UUID v4.

```python
def generate_uuid() -> str
```

**Returns:**
- `str`: UUID string

**Example:**
```python
from generator.core.utils import generate_uuid

incident_id = generate_uuid()
# Result: "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"
```

---

### timestamp_to_iso

Convert datetime to ISO 8601 string.

```python
def timestamp_to_iso(dt: datetime) -> str
```

**Parameters:**
- `dt` (datetime): Datetime object

**Returns:**
- `str`: ISO 8601 formatted string

**Example:**
```python
from datetime import datetime
from generator.core.utils import timestamp_to_iso

now = datetime.utcnow()
iso_string = timestamp_to_iso(now)
# Result: "2025-11-16T14:30:45.123456Z"
```

---

### parse_duration

Parse a duration string like '5m', '2h', '30s'.

```python
def parse_duration(duration_str: str) -> timedelta
```

**Parameters:**
- `duration_str` (str): Duration string (format: `<number><unit>`)
  - Units: `s` (seconds), `m` (minutes), `h` (hours), `d` (days)

**Returns:**
- `timedelta`: Timedelta object

**Raises:**
- `ValueError`: If unit is unknown

**Example:**
```python
from generator.core.utils import parse_duration

duration = parse_duration("2h")  # 2 hours
duration = parse_duration("30m")  # 30 minutes
duration = parse_duration("90s")  # 90 seconds
duration = parse_duration("7d")  # 7 days
```

---

### random_choice_weighted

Choose randomly from weighted choices.

```python
def random_choice_weighted(choices: list[tuple[str, float]]) -> str
```

**Parameters:**
- `choices` (list[tuple]): List of (value, weight) tuples

**Returns:**
- `str`: Selected value

**Example:**
```python
from generator.core.utils import random_choice_weighted

# 70% INFO, 20% WARN, 10% ERROR
log_level = random_choice_weighted([
    ("INFO", 0.7),
    ("WARN", 0.2),
    ("ERROR", 0.1)
])
```

---

### jitter

Add random jitter to a value.

```python
def jitter(value: float, percent: float = 0.1) -> float
```

**Parameters:**
- `value` (float): Base value
- `percent` (float): Jitter percentage (default 10%)

**Returns:**
- `float`: Value with jitter applied

**Example:**
```python
from generator.core.utils import jitter

base_latency = 100  # ms
actual_latency = jitter(base_latency, percent=0.1)
# Result: ~90-110 ms
```

---

### exponential_backoff

Calculate exponential backoff with jitter.

```python
def exponential_backoff(
    base_value: float,
    iteration: int,
    max_value: Optional[float] = None,
    jitter_percent: float = 0.2
) -> float
```

**Parameters:**
- `base_value` (float): Base value
- `iteration` (int): Current iteration (0-indexed)
- `max_value` (float, optional): Optional maximum value cap
- `jitter_percent` (float): Jitter percentage to apply

**Returns:**
- `float`: Backoff value

**Example:**
```python
from generator.core.utils import exponential_backoff

for retry in range(5):
    backoff = exponential_backoff(
        base_value=1.0,
        iteration=retry,
        max_value=30.0,
        jitter_percent=0.2
    )
    print(f"Retry {retry}: wait {backoff:.2f}s")
# Output:
# Retry 0: wait 0.95s
# Retry 1: wait 1.87s
# Retry 2: wait 4.21s
# Retry 3: wait 7.64s
# Retry 4: wait 15.89s
```

---

### gaussian_noise

Generate Gaussian noise.

```python
def gaussian_noise(mean: float, stddev: float) -> float
```

**Parameters:**
- `mean` (float): Mean value
- `stddev` (float): Standard deviation

**Returns:**
- `float`: Random value from Gaussian distribution

**Example:**
```python
from generator.core.utils import gaussian_noise

noise = gaussian_noise(mean=0, stddev=5)
actual_value = base_value + noise
```

---

### spike_pattern

Generate a spike pattern value.

```python
def spike_pattern(
    baseline: float,
    spike_multiplier: float,
    current_time: datetime,
    spike_start: datetime,
    spike_duration: timedelta
) -> float
```

**Parameters:**
- `baseline` (float): Baseline value
- `spike_multiplier` (float): Multiplier during spike
- `current_time` (datetime): Current timestamp
- `spike_start` (datetime): When spike starts
- `spike_duration` (timedelta): How long spike lasts

**Returns:**
- `float`: Value (baseline or spiked with gradual ramp)

**Example:**
```python
from datetime import datetime, timedelta
from generator.core.utils import spike_pattern

baseline_traffic = 1000
spike_start = datetime.utcnow()
spike_duration = timedelta(minutes=10)

for offset in range(20):
    current_time = spike_start + timedelta(minutes=offset)
    traffic = spike_pattern(
        baseline=baseline_traffic,
        spike_multiplier=5.0,
        current_time=current_time,
        spike_start=spike_start,
        spike_duration=spike_duration
    )
    print(f"{offset}min: {traffic:.0f} req/s")
```

---

## Complete Example

Here's a complete example using multiple API components:

```python
from datetime import datetime, timedelta
from pathlib import Path
from generator.core.base import BaseGenerator, IncidentContext
from generator.core.topology import TopologyGenerator
from generator.core.timeline import TimelineGenerator
from generator.core.distributions import LogNormalDistribution, LATENCY_DISTRIBUTION
from generator.core.patterns import create_business_hours_pattern, NoisePattern
from generator.core.utils import timestamp_to_iso, generate_uuid

# Create context
context = IncidentContext(
    start_time=datetime.utcnow(),
    duration=timedelta(hours=1),
    severity="SEV2",
    affected_services=["api-gateway"],
    root_cause="Connection pool exhaustion",
    output_dir=Path("./output/incident-001")
)

# Generate topology
topo_gen = TopologyGenerator(context)
topology = topo_gen.generate()

# Create timeline
timeline_gen = TimelineGenerator(context)
timeline_gen.add_anomaly_detection(
    timestamp=context.start_time,
    service="api-gateway",
    metric="latency_p95",
    threshold=500,
    actual_value=2500
)
timeline = timeline_gen.generate()

# Custom generator
class MyGenerator(BaseGenerator):
    def __init__(self, context: IncidentContext):
        super().__init__(context)
        self.latency_dist = LATENCY_DISTRIBUTION
        self.pattern = create_business_hours_pattern()

    def generate(self) -> dict:
        metrics = []
        for current_time in self._iterate_time_window(step=timedelta(minutes=1)):
            base_latency = self.latency_dist.sample()
            latency = self.pattern.apply(base_latency, current_time)

            # Add anomaly during incident
            if context.is_during_incident(current_time):
                latency *= 5.0

            metrics.append({
                "timestamp": timestamp_to_iso(current_time),
                "metric_name": "latency_ms",
                "value": latency,
                "service": "api-gateway",
                "anomaly_injected": context.is_during_incident(current_time)
            })

        self.save_jsonl(metrics, f"metrics_{context.incident_id}.jsonl", "metrics")
        return {"metric_count": len(metrics)}

# Generate data
generator = MyGenerator(context)
result = generator.generate()
print(f"Generated {result['metric_count']} metrics")
```

---

## See Also

- [Plugin Development Guide](plugin_development.md)
- [Architecture Documentation](architecture.md)
- [Example Plugins](../examples/plugins/)
- [Built-in Generators](../generator/incidents/)
