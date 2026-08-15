# ADAPT-Data: Synthetic Telemetry & Incident Dataset Generator

**ADAPT-Data** is a synthetic dataset generator and incident simulation engine for creating reproducible logs, metrics, traces, and configuration deltas that mimic real-world cloud and SaaS incidents. The toolkit includes generators for latency regressions, authentication failures, dependency outages, noisy metrics, and change-event correlations. It produces structured datasets suitable for benchmarking RCA algorithms, evaluating agentic diagnostic frameworks, training LLMs, or powering demos for ADAPT-RCA and ADAPT-UI.

## Features

- 🎯 **8 Incident Types**: Latency regression, auth failures, dependency outages, config drift, packet loss, bursty noise, memory leaks, and database deadlocks
- 📊 **Rich Telemetry**: Generates logs, metrics, traces, config changes, and incident timelines
- 🔗 **Correlated Signals**: Shared correlation IDs join logs, metrics, and traces for the same event
- 🔄 **Reproducible**: YAML-based scenario definitions for consistent dataset generation
- ✅ **Schema-Validated**: JSON schemas for all data types with built-in validation
- 🏗️ **Topology-Aware**: Built-in microservices graph, or define your own in YAML
- 📈 **Ready to Visualize**: Grafana dashboards for every incident type, with a one-command stack
- 📤 **Export Anywhere**: OpenTelemetry, Prometheus, and Datadog formats
- 🚀 **Production-Quality**: Fully typed Python codebase with comprehensive error handling

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/adapt-data.git
cd adapt-data

# Install dependencies
pip install -r requirements.txt

# Or install as package
pip install -e .
```

### Generate Your First Incident

```bash
# Generate a latency regression incident
python -m cli.main generate \
  --scenario latency_regression \
  --output ./my_incident \
  --duration 1h \
  --severity SEV2

# Validate the generated dataset
python -m cli.main validate ./my_incident
```

### List Available Scenarios

```bash
python -m cli.main list-scenarios
```

## Incident Types

### 1. Latency Regression
Simulates performance degradation due to inefficient code or queries.
- **Signals**: p95 latency spike, slow query logs, elevated DB CPU
- **Root Causes**: Inefficient queries, missing indexes, N+1 problems

### 2. Authentication Failures
Models auth service issues from cache/database problems.
- **Signals**: Auth error rate spike, cache connection failures
- **Root Causes**: Connection pool exhaustion, cache unavailability

### 3. Dependency Outage
Complete failure of a critical dependency causing cascades.
- **Signals**: Service unavailability, widespread 500 errors
- **Root Causes**: Infrastructure failure, resource exhaustion

### 4. Configuration Drift
Unintended config changes causing performance issues.
- **Signals**: Resource pool saturation, queue depth increase
- **Root Causes**: Accidental changes, auto-tuning errors

### 5. Packet Loss
Network degradation between services or regions.
- **Signals**: Packet loss metrics, TCP retransmits, timeouts
- **Root Causes**: Network hardware issues, routing problems

### 6. Bursty Noise
Intermittent resource contention from noisy neighbors.
- **Signals**: Periodic CPU spikes, high latency variance
- **Root Causes**: Batch jobs, scheduled tasks, other tenants

### 7. Memory Leak
Gradual heap exhaustion ending in an OOM kill.
- **Signals**: Steadily rising heap with no plateau, GC pause and frequency climbing, throughput falling, exit code 137
- **Root Causes**: Unbounded caches, unregistered listeners, retained buffers

### 8. Database Deadlock
Concurrent transactions locking tables in opposing order.
- **Signals**: Deadlock detector firing (SQLSTATE 40P01 / MySQL 1213), rollback bursts, blocked sessions, pool saturation
- **Root Causes**: Inconsistent lock ordering, raised concurrency, long transactions

## Generated Data Structure

```
output/
├── logs/
│   └── logs_<incident_id>.jsonl
├── metrics/
│   └── metrics_<incident_id>.jsonl
├── traces/
│   └── traces_<incident_id>.jsonl
├── config_deltas/
│   └── config_<incident_id>.jsonl
├── timelines/
│   └── timeline_<incident_id>.json
└── topology/
    └── topology.json
```

## Creating Custom Scenarios

Create a YAML file in `scenarios/`:

```yaml
type: latency_regression
description: Custom latency incident

parameters:
  affected_service: my-service
  baseline_latency_ms: 100.0
  degraded_latency_ms: 800.0
  error_threshold_ms: 2000.0

metadata:
  category: performance
  common_causes:
    - Custom cause 1
    - Custom cause 2
```

Then generate:

```bash
python -m cli.main generate --scenario my_custom_scenario --output ./output
```

## Custom Topologies

Generate incidents against your own architecture instead of the built-in graph:

```bash
# Use a bundled topology
python -m cli.main generate --scenario latency_regression \
  --topology ecommerce --output ./output

# Or your own YAML file
python -m cli.main generate --scenario latency_regression \
  --topology ./my-topology.yaml --output ./output
```

See [topology/README.md](topology/README.md) for the file format and bundled
topologies.

## Visualizing Incidents

Grafana dashboards ship for every incident type:

```bash
# Replay a dataset as Prometheus metrics
python -m cli.main serve ./output --port 9091 --replay-speed 60

# Bring up Grafana + Prometheus with dashboards pre-provisioned
docker compose -f dashboards/docker-compose.yml up
# → http://localhost:3000
```

See [dashboards/README.md](dashboards/README.md) for details.

## Exporting

```bash
# OpenTelemetry / Prometheus
python -m cli.main export ./output --format opentelemetry --output otlp.json
python -m cli.main export ./output --format prometheus --output metrics.txt

# Datadog — metrics, logs and traces
python -m cli.main export ./output --format datadog --dd-signal all --output ./dd
```

## Structured Logging

For CI pipelines and log aggregation, emit machine-readable logs:

```bash
python -m cli.main --log-format json generate --scenario memory_leak --output ./output

# Or via environment variable
ADAPT_LOG_FORMAT=json python -m cli.main generate --scenario memory_leak --output ./output
```

## Integration with ADAPT Ecosystem

### With ADAPT-RCA
```bash
# Use ADAPT-Data output as input to ADAPT-RCA
adapt-rca analyze --data ./my_incident
```

### With ADAPT-UI
```bash
# Visualize incident in ADAPT-UI
adapt-ui --load ./my_incident
```

## Architecture

```
generator/
├── core/          # Base framework (generators, timeline, topology, utils)
├── incidents/     # Incident-specific generators
└── anomalies/     # Anomaly injection utilities

cli/               # Command-line interface
scenarios/         # YAML scenario definitions
schema/            # JSON schemas for validation
incident_packs/    # Pre-generated datasets
```

See [docs/architecture.md](docs/architecture.md) for detailed architecture information.

## Data Schemas

All generated data conforms to strict JSON schemas:

- **Logs**: Structured logs with timestamps, levels, services, metadata
- **Metrics**: Time-series metrics with tags and anomaly flags
- **Traces**: Distributed traces with spans and timing
- **Config Deltas**: Configuration changes with before/after values
- **Timelines**: Event timelines with incident progression
- **Topology**: Service dependency graphs

See [docs/schema.md](docs/schema.md) for complete schema documentation.

## Use Cases

- 🧪 **Testing RCA Algorithms**: Benchmark root cause analysis systems
- 📚 **Training Data**: Generate datasets for ML/LLM training
- 🎓 **Education**: Teach incident response and debugging
- 🎬 **Demos**: Showcase observability and diagnostic tools
- 🔬 **Research**: Study incident patterns and detection methods

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black .

# Type checking
mypy .

# Linting
ruff check .
```

## Documentation

- [Tutorial](docs/tutorial.md) - Step-by-step guide
- [Architecture](docs/architecture.md) - System design and components
- [Schema Reference](docs/schema.md) - Complete schema documentation
- [API Reference](docs/api.md) - Python API documentation

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Citation

If you use ADAPT-Data in your research, please cite:

```bibtex
@software{adapt_data,
  title = {ADAPT-Data: Synthetic Telemetry \& Incident Dataset Generator},
  author = {ADAPT Team},
  year = {2025},
  url = {https://github.com/your-org/adapt-data}
}
```

## Related Projects

- **ADAPT-RCA**: AI-powered root cause analysis engine
- **ADAPT-UI**: Interactive incident visualization and analysis interface

---

**Questions or Issues?** Open an issue on GitHub or reach out to the ADAPT team.
