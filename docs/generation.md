# Generation Process

This document explains how ADAPT-Data generates synthetic telemetry data, including the generation workflow, data types produced, anomaly injection, and timeline creation.

## Overview

ADAPT-Data generates realistic incident datasets through a multi-stage process:

1. **Configuration Loading**: Load scenario and global configuration
2. **Topology Creation**: Build service dependency graph
3. **Timeline Generation**: Create incident event timeline
4. **Data Generation**: Generate logs, metrics, traces, and config deltas
5. **Anomaly Injection**: Inject realistic anomalies during incident window
6. **Validation**: Verify data quality and schema conformance
7. **Output**: Write structured data files

## Generation Workflow

### 1. Initialization Phase

When you run a generation command:

```bash
python -m cli.main generate --scenario latency_regression --output ./data --duration 1h
```

ADAPT-Data performs these steps:

**Step 1: Load Configuration**
- Read `.adapt-data.yaml` configuration file
- Apply environment variable overrides
- Apply CLI flag overrides
- Validate configuration

**Step 2: Load Scenario**
- Parse scenario YAML file
- Validate scenario parameters
- Determine incident type
- Extract metadata

**Step 3: Create Incident Context**
- Generate unique incident ID
- Calculate start/end times based on duration
- Determine affected services
- Create output directories

```python
# Internal representation
context = IncidentContext(
    incident_id="inc_a1b2c3d4",
    start_time=datetime(2025, 1, 16, 10, 0, 0),
    end_time=datetime(2025, 1, 16, 11, 0, 0),
    duration=timedelta(hours=1),
    severity="SEV3",
    affected_services=["order-service"],
    root_cause="Database query regression",
    output_dir=Path("./data"),
    topology={...},
    scenario_config={...}
)
```

### 2. Topology Creation

ADAPT-Data builds a service dependency graph:

**Default Topology:**
```python
{
    "services": [
        {
            "name": "api-gateway",
            "type": "gateway",
            "instances": 3,
            "dependencies": ["user-service", "order-service"]
        },
        {
            "name": "order-service",
            "type": "application",
            "instances": 5,
            "dependencies": ["postgres-primary", "redis-cache"]
        },
        {
            "name": "postgres-primary",
            "type": "database",
            "instances": 1,
            "dependencies": []
        }
    ],
    "connections": [
        {"from": "api-gateway", "to": "order-service"},
        {"from": "order-service", "to": "postgres-primary"}
    ]
}
```

**Topology Features:**
- Service dependencies (directed graph)
- Instance counts (for realistic load distribution)
- Service types (application, database, cache, gateway)
- Regions and zones (for multi-region scenarios)

### 3. Timeline Generation

The timeline tracks incident progression:

**Timeline Structure:**
```json
{
  "incident_id": "inc_a1b2c3d4",
  "start_time": "2025-01-16T10:00:00Z",
  "end_time": "2025-01-16T11:00:00Z",
  "severity": "SEV3",
  "events": [
    {
      "timestamp": "2025-01-16T10:00:00Z",
      "event_type": "incident_start",
      "description": "Latency regression detected in order-service"
    },
    {
      "timestamp": "2025-01-16T10:05:00Z",
      "event_type": "anomaly_onset",
      "description": "p95 latency increased from 50ms to 500ms",
      "affected_services": ["order-service"]
    },
    {
      "timestamp": "2025-01-16T10:15:00Z",
      "event_type": "error_threshold",
      "description": "Error rate exceeded 5%"
    },
    {
      "timestamp": "2025-01-16T10:45:00Z",
      "event_type": "mitigation_start",
      "description": "Database index added"
    },
    {
      "timestamp": "2025-01-16T10:55:00Z",
      "event_type": "anomaly_resolution",
      "description": "Latency returned to baseline"
    },
    {
      "timestamp": "2025-01-16T11:00:00Z",
      "event_type": "incident_end",
      "description": "Incident resolved"
    }
  ]
}
```

**Timeline Phases:**
1. **Baseline Period** (-30 to 0 minutes): Normal operations
2. **Onset** (0 to +5 minutes): Gradual anomaly introduction
3. **Peak Impact** (+5 to +45 minutes): Full incident effect
4. **Mitigation** (+45 to +55 minutes): Recovery actions
5. **Resolution** (+55 to +60 minutes): Return to baseline
6. **Post-Incident** (+60 to +90 minutes): Stability monitoring

### 4. Data Generation

ADAPT-Data generates four types of telemetry data:

#### A. Metrics

Time-series metrics with 1-minute granularity:

**Metric Structure:**
```json
{
  "timestamp": "2025-01-16T10:15:00Z",
  "metric_name": "http.server.latency",
  "value": 523.4,
  "unit": "ms",
  "service": "order-service",
  "host": "order-service-002",
  "tags": {
    "method": "GET",
    "endpoint": "/api/orders",
    "status_code": "200"
  },
  "metric_type": "gauge",
  "anomaly_injected": true
}
```

**Common Metrics Generated:**

**Latency Metrics:**
- `http.server.latency`: Request latency (p50, p95, p99)
- `db.query.duration`: Database query duration
- `cache.operation.latency`: Cache operation latency

**Error Metrics:**
- `http.server.error_rate`: HTTP error rate (4xx, 5xx)
- `db.connection.errors`: Database connection failures
- `auth.failure_rate`: Authentication failure rate

**Throughput Metrics:**
- `http.server.requests`: Request count
- `db.queries`: Query count
- `cache.operations`: Cache operation count

**Resource Metrics:**
- `system.cpu.usage`: CPU utilization (%)
- `system.memory.usage`: Memory usage (bytes)
- `db.connection_pool.size`: Connection pool utilization

**Network Metrics:**
- `network.packet_loss`: Packet loss percentage
- `network.tcp.retransmits`: TCP retransmit count
- `network.connection.timeouts`: Connection timeout count

#### B. Logs

Structured log entries with varying levels:

**Log Structure:**
```json
{
  "timestamp": "2025-01-16T10:15:23.456Z",
  "level": "ERROR",
  "service": "order-service",
  "host": "order-service-002",
  "message": "Database query timeout after 2000ms",
  "context": {
    "query": "SELECT * FROM orders WHERE user_id = ?",
    "duration_ms": 2143,
    "error_code": "QUERY_TIMEOUT"
  },
  "trace_id": "abc123def456",
  "span_id": "span789"
}
```

**Log Levels:**
- **DEBUG**: Detailed diagnostic information (15% of logs)
- **INFO**: General informational messages (60% of logs)
- **WARN**: Warning conditions (20% of logs)
- **ERROR**: Error conditions (5% of logs during baseline, 30% during incident)

**Log Types Generated:**

**Application Logs:**
- Request/response logs
- Business logic events
- Transaction completion

**Error Logs:**
- Exceptions and stack traces
- Timeout errors
- Connection failures
- Authentication failures

**Slow Query Logs:**
- Database queries exceeding threshold
- Query plans and parameters
- Row counts and durations

**System Logs:**
- Service startup/shutdown
- Configuration changes
- Health check results

#### C. Traces

Distributed traces with spans:

**Trace Structure:**
```json
{
  "trace_id": "abc123def456",
  "timestamp": "2025-01-16T10:15:23.456Z",
  "duration_ms": 2156,
  "service": "api-gateway",
  "operation": "GET /api/orders",
  "spans": [
    {
      "span_id": "span001",
      "parent_span_id": null,
      "service": "api-gateway",
      "operation": "GET /api/orders",
      "start_time": "2025-01-16T10:15:23.456Z",
      "duration_ms": 2156,
      "tags": {
        "http.method": "GET",
        "http.url": "/api/orders",
        "http.status_code": 200
      }
    },
    {
      "span_id": "span002",
      "parent_span_id": "span001",
      "service": "order-service",
      "operation": "query_orders",
      "start_time": "2025-01-16T10:15:23.478Z",
      "duration_ms": 2121,
      "tags": {
        "db.query": "SELECT * FROM orders",
        "db.rows": 50
      },
      "anomaly_injected": true
    }
  ]
}
```

**Span Features:**
- Parent-child relationships
- Service boundaries
- Operation names
- Tags and metadata
- Error indicators
- Anomaly flags

#### D. Configuration Deltas

Configuration change events (for config_drift incidents):

**Config Delta Structure:**
```json
{
  "timestamp": "2025-01-16T10:00:00Z",
  "service": "payment-service",
  "config_key": "max_concurrent_transactions",
  "old_value": 100,
  "new_value": 10,
  "changed_by": "auto-tuner",
  "change_reason": "Performance optimization attempt",
  "rollback_available": true
}
```

### 5. Anomaly Injection

ADAPT-Data uses specialized injectors to create realistic anomalies:

#### Latency Injector

Increases latency during incident window:

```python
class LatencyInjector:
    def get_latency(self, timestamp: datetime) -> float:
        if incident_window(timestamp):
            # Gradual ramp-up
            progress = get_incident_progress(timestamp)
            if progress < 0.2:  # First 20% - ramp up
                multiplier = 1 + (target_multiplier - 1) * (progress / 0.2)
            elif progress > 0.8:  # Last 20% - ramp down
                multiplier = 1 + (target_multiplier - 1) * ((1 - progress) / 0.2)
            else:  # Middle 60% - sustained
                multiplier = target_multiplier

            latency = baseline * multiplier
        else:
            latency = baseline

        # Add realistic noise
        return latency + gaussian_noise(0, baseline * 0.1)
```

**Latency Pattern:**
```
Latency (ms)
   500 |              ________________
       |            /                  \
   300 |          /                      \
   100 |        /                          \
    50 |______/                              \______
       |
       +------------------------------------------> Time
       -30m    0    +15m   +45m   +60m    +90m
              Baseline  Peak    Recovery  Post
```

#### Error Rate Injector

Increases error rate during incidents:

```python
class ErrorRateInjector:
    def get_error_rate(self, timestamp: datetime) -> float:
        if incident_window(timestamp):
            progress = get_incident_progress(timestamp)
            # Gradual increase/decrease
            if progress < 0.1:
                rate = baseline + (spike_rate - baseline) * (progress / 0.1)
            elif progress > 0.9:
                rate = baseline + (spike_rate - baseline) * ((1 - progress) / 0.1)
            else:
                rate = spike_rate
        else:
            rate = baseline_error_rate

        return rate
```

#### Throughput Injector

Modifies request throughput:

```python
class ThroughputInjector:
    def get_throughput(self, timestamp: datetime) -> float:
        base_rps = apply_daily_pattern(timestamp, baseline_rps)

        if incident_window(timestamp):
            multiplier = anomaly_multiplier  # < 1 for drop, > 1 for spike
            return base_rps * multiplier

        return base_rps
```

### 6. Advanced Features

#### A. Probability Distributions

ADAPT-Data uses realistic probability distributions:

**Normal Distribution** (latency, CPU):
```python
value = np.random.normal(mean, stddev)
```

**Exponential Distribution** (inter-arrival times):
```python
value = np.random.exponential(scale)
```

**LogNormal Distribution** (query durations):
```python
value = np.random.lognormal(mean, sigma)
```

**Poisson Distribution** (request counts):
```python
value = np.random.poisson(lambda_)
```

#### B. Time-Series Patterns

**Daily Pattern** (business hours):
```python
def daily_pattern(hour: int) -> float:
    # Higher load during business hours
    if 9 <= hour <= 17:
        return 1.5  # 50% more traffic
    elif 22 <= hour or hour <= 6:
        return 0.3  # 70% less traffic
    else:
        return 1.0
```

**Weekly Pattern**:
```python
def weekly_pattern(weekday: int) -> float:
    # Lower load on weekends
    if weekday >= 5:  # Saturday, Sunday
        return 0.4
    return 1.0
```

**Seasonal Pattern**:
```python
def seasonal_pattern(month: int) -> float:
    # Higher load during Q4 (holiday season)
    if month >= 10:
        return 1.3
    return 1.0
```

**Burst Pattern** (bursty_noise):
```python
def burst_pattern(timestamp: datetime) -> float:
    minutes_since_start = (timestamp - start_time).total_seconds() / 60

    # Check if in burst window
    if minutes_since_start % burst_frequency < (burst_duration / 60):
        return 3.0  # 3x multiplier during burst
    return 1.0
```

#### C. Correlation

Generate correlated anomalies across services:

**Dependent Service Correlation:**
```python
# When database is slow, all dependent services are affected
if "postgres-primary" in affected_services:
    for dependent in get_dependents("postgres-primary"):
        inject_latency_anomaly(dependent, multiplier=0.7)
        inject_error_anomaly(dependent, error_rate=0.1)
```

**Metric Correlation:**
```python
# High CPU correlates with high latency
if cpu_usage > 80:
    latency_multiplier = 1 + (cpu_usage - 80) / 20  # Linear correlation
```

## Data Quality and Realism

### Noise and Variance

ADAPT-Data adds realistic noise to all metrics:

**Gaussian Noise:**
```python
def gaussian_noise(mean: float, stddev: float) -> float:
    return random.gauss(mean, stddev)

# Example
latency = 50.0 + gaussian_noise(0, 5.0)  # 50ms ± 5ms
```

**Jitter:**
```python
def jitter(value: float, jitter_percent: float = 0.1) -> float:
    return value * (1 + random.uniform(-jitter_percent, jitter_percent))

# Example
throughput = jitter(100.0, 0.15)  # 100 RPS ± 15%
```

### Data Consistency

ADAPT-Data ensures data consistency:

**Timestamp Alignment:**
- All data uses ISO 8601 format with UTC timezone
- Metrics aligned to 1-minute boundaries
- Logs have sub-second precision
- Traces maintain causality

**Service Consistency:**
- All services exist in topology
- Host names follow pattern: `{service}-{instance:03d}`
- Dependencies are respected in trace spans

**Anomaly Marking:**
- All anomalous data points flagged with `anomaly_injected: true`
- Baseline data flagged with `anomaly_injected: false`
- Enables ground truth evaluation

## Output Structure

Generated datasets follow this structure:

```
output/
├── logs/
│   └── logs_inc_a1b2c3d4.jsonl
├── metrics/
│   └── metrics_inc_a1b2c3d4.jsonl
├── traces/
│   └── traces_inc_a1b2c3d4.jsonl
├── config_deltas/
│   └── config_inc_a1b2c3d4.jsonl
├── timelines/
│   └── timeline_inc_a1b2c3d4.json
└── topology/
    └── topology.json
```

**File Formats:**
- `.jsonl`: JSON Lines (one JSON object per line) for streaming data
- `.json`: Pretty-printed JSON for structured data

## Performance Considerations

### Generation Speed

Typical generation times:

| Duration | Metrics | Logs | Traces | Time |
|----------|---------|------|--------|------|
| 30m      | ~180    | ~500 | ~100   | 2s   |
| 1h       | ~360    | ~1000| ~200   | 3s   |
| 2h       | ~720    | ~2000| ~400   | 5s   |
| 24h      | ~8640   | ~24k | ~4800  | 45s  |

**Optimization Tips:**
- Use `parallel_generation: false` for predictable memory usage
- Set `enable_progress: false` in CI/CD for cleaner output
- Use smaller durations for faster iteration
- Enable `random_seed` for reproducible testing

### Memory Usage

Memory usage scales with duration:

- **1-hour incident**: ~50 MB RAM
- **24-hour incident**: ~500 MB RAM
- **Multi-day cascade**: ~2 GB RAM

## Reproducibility

### Fixed Seed Generation

For reproducible datasets:

```yaml
# .adapt-data.yaml
generation:
  random_seed: 42

advanced:
  enable_patterns: false  # Disable time-based patterns
  noise_level: 0.0        # Disable noise
```

```bash
python -m cli.main generate \
  --scenario latency_regression \
  --output ./reproducible-data
```

### Golden Files

Use golden file testing:

```python
# Generate reference dataset
python -m cli.main generate \
  --scenario latency_regression \
  --output ./golden/latency \
  ADAPT_RANDOM_SEED=42

# Later: Generate and compare
python -m cli.main generate \
  --scenario latency_regression \
  --output ./new-data \
  ADAPT_RANDOM_SEED=42

diff -r ./golden/latency ./new-data
```

## Extending Generation

### Custom Generators

Create custom incident generators:

```python
from generator.core.base import BaseGenerator, IncidentContext

class CustomIncidentGenerator(BaseGenerator):
    def __init__(self, context: IncidentContext):
        super().__init__(context)
        self.affected_service = context.scenario_config.get("affected_service")

    def generate(self) -> dict:
        # Generate custom metrics
        metrics = self._generate_custom_metrics()

        # Generate custom logs
        logs = self._generate_custom_logs()

        # Save data
        self.save_jsonl(metrics, f"metrics_{self.context.incident_id}.jsonl", "metrics")
        self.save_jsonl(logs, f"logs_{self.context.incident_id}.jsonl", "logs")

        return {
            "metrics_count": len(metrics),
            "logs_count": len(logs)
        }
```

### Custom Anomaly Injectors

Create custom injectors:

```python
class CustomAnomalyInjector:
    def __init__(self, baseline, anomaly_value, spike_start, spike_duration):
        self.baseline = baseline
        self.anomaly_value = anomaly_value
        self.spike_start = spike_start
        self.spike_duration = spike_duration

    def get_value(self, timestamp: datetime) -> float:
        spike_end = self.spike_start + self.spike_duration

        if self.spike_start <= timestamp <= spike_end:
            # Custom anomaly pattern
            progress = (timestamp - self.spike_start) / self.spike_duration
            return self.baseline + (self.anomaly_value - self.baseline) * sin(progress * pi)

        return self.baseline
```

## Related Documentation

- [Scenarios](scenarios.md) - Scenario file format
- [Configuration](configuration.md) - Configuration options
- [Architecture](architecture.md) - System design
- [Schema Reference](schema.md) - Data schemas
