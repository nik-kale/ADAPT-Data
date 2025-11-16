# ADAPT-Data Quickstart Guide

Get productive with ADAPT-Data in 20 minutes. Generate synthetic incident datasets for testing, training, and research.

## Installation (5 minutes)

```bash
# Clone and install
git clone https://github.com/your-org/adapt-data.git
cd adapt-data
pip install -e .

# Verify installation
adapt-data --help
adapt-data doctor
```

## Generate Your First Incident (10 minutes)

### Quick Start

```bash
# Generate a latency regression incident
adapt-data generate --scenario latency_regression --output ./my_first_incident

# Explore the output
adapt-data info ./my_first_incident
```

### Custom Parameters

```bash
adapt-data generate \
  --scenario latency_regression \
  --output ./incident \
  --duration 1h \
  --severity SEV2 \
  --difficulty medium
```

**Parameters:**
- `--scenario`: latency_regression, auth_failure, dependency_outage, packet_loss, config_drift, bursty_noise
- `--duration`: 30m, 1h, 2h
- `--severity`: SEV1 (critical) to SEV4 (low)
- `--difficulty`: beginner, easy, medium, hard, expert

### Explore Generated Data

```bash
# View logs and metrics
head -n 3 ./incident/logs/*.jsonl | jq
head -n 3 ./incident/metrics/*.jsonl | jq

# View incident timeline
cat ./incident/timelines/*.json | jq '.events[] | {timestamp, event_type, description}'
```

**Data Structure:**
```
incident/
├── logs/           # Structured logs (JSONL)
├── metrics/        # Time-series metrics (JSONL)
├── traces/         # Distributed traces (JSONL)
├── config_deltas/  # Configuration changes (JSONL)
├── timelines/      # Incident timeline (JSON)
└── topology/       # Service dependency graph (JSON)
```

## Validation & Export (5 minutes)

### Validate Dataset

```bash
adapt-data validate ./incident                    # Standard validation
adapt-data validate ./incident --strict            # Strict mode with detailed errors
```

### Analyze & Export

```bash
# View statistics
adapt-data stats ./incident
adapt-data stats ./incident --output stats.json

# Export to OpenTelemetry
adapt-data export ./incident --format opentelemetry --output traces.otlp

# Export to Prometheus
adapt-data export ./incident --format prometheus --output metrics.prom

# Serve via HTTP
adapt-data serve ./incident --port 9090
```

## Next Steps

### Try Different Scenarios

```bash
# Authentication failure
adapt-data generate --scenario auth_failure --output ./auth --duration 30m --severity SEV1

# Dependency outage
adapt-data generate --scenario dependency_outage --output ./outage --duration 45m

# Network issues
adapt-data generate --scenario packet_loss --output ./network --duration 20m

# Configuration drift
adapt-data generate --scenario config_drift --output ./config --duration 1h

# List all scenarios
adapt-data list-scenarios
```

### Adjust Difficulty

Difficulty levels control incident complexity and noise:
- `beginner` - Simple patterns, clear signals
- `easy` - Obvious correlations
- `medium` - Some red herrings
- `hard` - Multiple factors, noisy data
- `expert` - Subtle patterns, cascading failures

```bash
adapt-data generate --scenario latency_regression --output ./expert --difficulty expert
```

### Create Custom Scenarios

**Interactive wizard:**
```bash
adapt-data wizard
```

**Manual YAML** (`scenarios/my_custom.yaml`):
```yaml
type: latency_regression
description: Custom API latency regression

parameters:
  affected_service: user-service
  baseline_latency_ms: 25.0
  degraded_latency_ms: 400.0
  error_threshold_ms: 1000.0

metadata:
  category: performance
  common_causes:
    - Inefficient database query
    - Missing index
```

Generate it:
```bash
adapt-data generate --scenario my_custom --output ./custom
```

### Batch Generation

```bash
# Generate multiple incidents for training datasets
for i in {1..10}; do
  adapt-data generate --scenario latency_regression --output ./incidents/incident_$i
done
```

### Analyze Correlations

```bash
# Find metric/log/event correlations
adapt-data correlate ./incident
adapt-data correlate ./incident --output correlations.json
```

## Quick Reference

### Essential Commands

| Command | Description |
|---------|-------------|
| `adapt-data generate` | Generate incident dataset |
| `adapt-data validate` | Validate schemas |
| `adapt-data list-scenarios` | Show available scenarios |
| `adapt-data info` | Dataset information |
| `adapt-data stats` | Dataset statistics |
| `adapt-data export` | Export to other formats |
| `adapt-data wizard` | Interactive creator |
| `adapt-data correlate` | Analyze correlations |

### Available Scenarios

1. **latency_regression** - Slow queries, performance degradation
2. **auth_failure** - Authentication service failures
3. **dependency_outage** - Critical dependency failures
4. **packet_loss** - Network degradation
5. **config_drift** - Configuration changes
6. **bursty_noise** - Resource contention

## Integration with ADAPT Ecosystem

```bash
# With ADAPT-RCA
adapt-data generate --scenario latency_regression --output ./incident
adapt-rca analyze --data ./incident

# With ADAPT-UI
adapt-data generate --scenario auth_failure --output ./incident
adapt-ui --load ./incident
```

## Troubleshooting

**Command not found:**
```bash
pip install -e .
# Or: python -m cli.main --help
```

**Scenario not found:**
```bash
adapt-data list-scenarios
```

**Validation failed:**
```bash
adapt-data validate ./incident --strict
```

## Learn More

- **[Tutorial](tutorial.md)** - Comprehensive step-by-step guide
- **[Architecture](architecture.md)** - System design and components
- **[Schema Reference](schema.md)** - Complete data schemas
- **[Plugin Development](plugin_development.md)** - Create custom generators
- **[Validation Guide](validation.md)** - Advanced validation features

**Get Help:** [GitHub Issues](https://github.com/your-org/adapt-data/issues)

**You're ready to go!** Generate incidents, validate datasets, and export to your observability stack.
