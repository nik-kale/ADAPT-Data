# ADAPT-Data Quick Reference Guide

Quick reference for all ADAPT-Data capabilities in version 0.2.0

## 🚀 Quick Start

```bash
# Install
pip install -e ".[all]"  # Install everything

# Generate incident
python -m cli.main generate --scenario latency_regression --output ./incident

# Validate
python -m cli.main validate ./incident

# Analyze
python -m cli.main stats ./incident
```

---

## 📋 CLI Commands

### Core Commands

```bash
# List available scenarios
python -m cli.main list-scenarios

# Generate incident
python -m cli.main generate \
  --scenario SCENARIO_NAME \
  --output ./output \
  --duration 1h \
  --severity SEV2

# Validate dataset
python -m cli.main validate ./dataset [--strict]

# Interactive wizard
python -m cli.main wizard
```

### Analytics Commands

```bash
# Analyze dataset statistics
python -m cli.main stats ./dataset

# Export statistics to JSON
python -m cli.main stats ./dataset --output stats.json
```

### Export Commands

```bash
# Export to OpenTelemetry format
python -m cli.main export ./dataset \
  --format opentelemetry \
  --output traces_otlp.json

# Export to Prometheus format
python -m cli.main export ./dataset \
  --format prometheus \
  --output metrics.prom

# Serve metrics via HTTP (Prometheus)
python -m cli.main serve ./dataset \
  --port 9090 \
  --replay-speed 10.0
```

---

## 🎯 Incident Types

| Type | Description | Key Parameters |
|------|-------------|----------------|
| `latency_regression` | Performance degradation | baseline_latency_ms, degraded_latency_ms |
| `auth_failure` | Authentication failures | spike_error_rate |
| `dependency_outage` | Service outage | failed_service, dependent_services |
| `config_drift` | Config change issues | config_key, old_value, new_value |
| `packet_loss` | Network degradation | packet_loss_percent |
| `bursty_noise` | Resource contention | burst_frequency_minutes |
| `cascade` | Multi-incident chain | cascade_config |

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=generator --cov=cli

# Run specific test types
pytest tests/unit           # Unit tests
pytest tests/integration    # Integration tests
pytest tests/golden         # Golden file tests

# Property-based tests
pytest tests/unit/test_properties.py -v
```

---

## 📊 Dataset Structure

```
output/
├── logs/               # Log entries (JSONL)
├── metrics/            # Time-series metrics (JSONL)
├── traces/             # Distributed traces (JSONL)
├── config_deltas/      # Configuration changes (JSONL)
├── timelines/          # Incident timelines (JSON)
└── topology/           # Service topology (JSON)
```

---

## 🔧 Scenario Configuration

### Basic Scenario (YAML)

```yaml
type: latency_regression
description: My custom incident

parameters:
  affected_service: order-service
  baseline_latency_ms: 50.0
  degraded_latency_ms: 500.0

metadata:
  category: performance
  difficulty: medium
```

### Cascade Scenario

```yaml
type: cascade
description: Multi-incident cascade

cascade_incidents:
  - type: deployment
    time: "T+0m"
    service: api-gateway

  - type: latency_regression
    time: "T+5m"
    service: api-gateway
    delay: 5m
    duration: 30m

  - type: dependency_outage
    time: "T+20m"
    service: postgres-primary
    delay: 20m
```

---

## 🎓 RCA Challenges

```bash
# Generate a challenge
python -m cli.main generate --scenario challenges/challenge_001

# View challenge details
cat challenges/challenge_001_latency_mystery.yaml

# Attempt solution
# 1. Generate incident
# 2. Analyze with your RCA tool
# 3. Compare against solution in YAML
```

### Challenge Structure

- **Title & Description**: Scenario setup
- **Difficulty**: easy/medium/hard/expert
- **Hints**: Progressive 5-level hint system
- **Solution**: Expected root cause
- **Evaluation**: Scoring rubric
- **Learning Objectives**: Skills to practice

---

## 🌍 Real-World Incidents

```bash
# Generate real-world incident recreation
python -m cli.main generate \
  --scenario real_world_incidents/aws_us_east_1_power_outage_2023 \
  --output ./aws_outage

# View incident details
cat real_world_incidents/aws_us_east_1_power_outage_2023.yaml
```

---

## 🔌 Integration Examples

### With OpenTelemetry

```bash
# Export traces
python -m cli.main export ./incident \
  --format opentelemetry \
  --output traces.json

# Send to OTel collector
curl -X POST http://otel-collector:4318/v1/traces \
  -H "Content-Type: application/json" \
  -d @traces.json
```

### With Prometheus

```bash
# Start metrics server
python -m cli.main serve ./incident --port 9090

# Configure Prometheus
# prometheus.yml:
scrape_configs:
  - job_name: 'adapt-data'
    static_configs:
      - targets: ['localhost:9090']

# Query metrics
curl http://localhost:9090/metrics
```

### With Grafana

```bash
# Serve metrics
python -m cli.main serve ./incident --port 9090 --replay-speed 10.0

# Point Grafana to localhost:9090
# Watch incident unfold in real dashboards
```

---

## 📈 Statistics Output

```bash
$ python -m cli.main stats ./incident

======================================================================
DATASET STATISTICS
======================================================================

📝 LOGS:
  Total Entries: 1,245
  Log Levels:
    ERROR: 234 (18.8%)
    WARN: 123 (9.9%)
    INFO: 888 (71.3%)

📊 METRICS:
  Total Data Points: 720
  Unique Metrics: 15
  Anomalous Points: 180 (25.0%)

🔍 TRACES:
  Total Traces: 20
  Total Spans: 60
  Avg Spans/Trace: 3.0
  Duration Stats (ms):
    Mean: 542.30
    p95: 1250.00
    p99: 2100.00

📅 TIMELINE:
  Incident ID: abc-123
  Severity: SEV2
  Root Cause: Database query regression
  Total Events: 5
======================================================================
```

---

## 🧬 Property-Based Testing Examples

```python
from hypothesis import given, strategies as st
from generator.core.utils import jitter

@given(
    value=st.floats(min_value=1.0, max_value=10000.0),
    percent=st.floats(min_value=0.0, max_value=0.5)
)
def test_jitter_bounded(value, percent):
    """Jitter stays within bounds for any valid input."""
    result = jitter(value, percent)
    assert value * (1 - percent) <= result <= value * (1 + percent)
```

---

## 📦 Package Installation Options

```bash
# Minimal (core only)
pip install -e .

# Development
pip install -e ".[dev]"

# With streaming
pip install -e ".[streaming]"

# With exporters
pip install -e ".[exporters]"

# With TUI
pip install -e ".[tui]"

# Everything
pip install -e ".[all]"
```

---

## 🎯 Common Workflows

### Generate & Analyze

```bash
# 1. Generate
python -m cli.main generate --scenario latency_regression --output ./test1

# 2. Validate
python -m cli.main validate ./test1

# 3. Analyze
python -m cli.main stats ./test1 --output stats.json

# 4. Export
python -m cli.main export ./test1 --format opentelemetry --output otlp.json
```

### Batch Generation

```bash
# Generate multiple scenarios
for scenario in latency_regression auth_failure dependency_outage; do
  python -m cli.main generate \
    --scenario $scenario \
    --output ./incidents/$scenario
done

# Validate all
for dir in ./incidents/*; do
  python -m cli.main validate $dir
done
```

### Live Demo

```bash
# Generate incident
python -m cli.main generate --scenario latency_regression --output ./demo

# Serve metrics for Prometheus/Grafana
python -m cli.main serve ./demo --port 9090 --replay-speed 30.0

# Watch incident unfold at 30x speed in your dashboards!
```

---

## 🆘 Troubleshooting

### Missing Dependencies

```bash
# If OpenTelemetry export fails
pip install "adapt-data[exporters]"

# If Prometheus serve fails
pip install prometheus-client

# If tests fail
pip install "adapt-data[dev]"
```

### Validation Errors

```bash
# Run strict validation for detailed errors
python -m cli.main validate ./incident --strict

# Check schema files
ls schema/*.json

# Verify JSONL format
head -n 1 ./incident/logs/*.jsonl | jq .
```

---

## 📚 Additional Resources

- **Tutorial**: `docs/tutorial.md`
- **Architecture**: `docs/architecture.md`
- **Schemas**: `docs/schema.md`
- **Contributing**: `CONTRIBUTING.md`
- **Changelog**: `CHANGELOG.md`
- **Examples**: `examples/`

---

## 💡 Pro Tips

1. **Use wizard for quick scenarios**: `python -m cli.main wizard`
2. **Export stats for presentations**: `--output stats.json`
3. **Speed up demos**: `--replay-speed 60.0` (60x real-time)
4. **Test alerts**: Use `serve` command with real Prometheus
5. **Benchmark RCA**: Use challenges with scoring rubrics
6. **Learn from real incidents**: Check `real_world_incidents/`

---

**Version**: 0.2.0
**Last Updated**: 2025-01-16
