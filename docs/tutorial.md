# ADAPT-Data Tutorial

This tutorial will walk you through using ADAPT-Data to generate synthetic incident datasets.

## Prerequisites

- Python 3.10 or later
- Basic understanding of observability concepts (logs, metrics, traces)

## Installation

```bash
# Clone the repository
git clone https://github.com/your-org/adapt-data.git
cd adapt-data

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -m cli.main --help
```

## Part 1: Your First Incident

Let's generate a simple latency regression incident.

### Step 1: List Available Scenarios

```bash
python -m cli.main list-scenarios
```

You should see output like:

```
Available scenarios:

  latency_regression
    Type: latency_regression
    Description: Database query regression causing elevated API latency

  auth_failure
    Type: auth_failure
    Description: Authentication service failures due to cache unavailability

  ...
```

### Step 2: Generate an Incident

```bash
python -m cli.main generate \
  --scenario latency_regression \
  --output ./my_first_incident \
  --duration 1h \
  --severity SEV2
```

You'll see progress output:

```
Loading scenario: scenarios/latency_regression.yaml
Generating topology...
Generating latency_regression incident for order-service...
  Generated 1245 log entries
  Generated 720 metric points
  Generated 20 traces
  Generated 1 config changes
  Generated timeline with 5 events

✓ Successfully generated incident: abc123-def456
  Output directory: ./my_first_incident
  Incident type: latency_regression
  Duration: 1h
  Severity: SEV2
```

### Step 3: Explore the Output

```bash
tree ./my_first_incident
```

```
my_first_incident/
├── logs/
│   └── logs_abc123.jsonl
├── metrics/
│   └── metrics_abc123.jsonl
├── traces/
│   └── traces_abc123.jsonl
├── config_deltas/
│   └── config_abc123.jsonl
├── timelines/
│   └── timeline_abc123.json
└── topology/
    └── topology.json
```

### Step 4: Examine the Data

**View logs:**
```bash
head -n 3 ./my_first_incident/logs/logs_abc123.jsonl | jq
```

**View metrics:**
```bash
head -n 3 ./my_first_incident/metrics/metrics_abc123.jsonl | jq
```

**View timeline:**
```bash
cat ./my_first_incident/timelines/timeline_abc123.json | jq
```

### Step 5: Validate the Dataset

```bash
python -m cli.main validate ./my_first_incident
```

Expected output:

```
Validating dataset: ./my_first_incident

Validating logs...
  ✓ logs_abc123.jsonl: 1245 records valid

Validating metrics...
  ✓ metrics_abc123.jsonl: 720 records valid

Validating traces...
  ✓ traces_abc123.jsonl: 20 records valid

...

============================================================
✓ All files validated successfully!
```

## Part 2: Understanding the Data

### Logs

Logs show the incident progression:

**Before incident (normal):**
```json
{
  "timestamp": "2025-01-15T10:25:00.000Z",
  "level": "INFO",
  "service": "order-service",
  "message": "HTTP GET /api/orders/1234",
  "metadata": {
    "status_code": 200,
    "duration_ms": 52.3
  }
}
```

**During incident (degraded):**
```json
{
  "timestamp": "2025-01-15T10:35:00.000Z",
  "level": "WARN",
  "service": "order-service",
  "message": "Slow database query detected",
  "metadata": {
    "query": "SELECT * FROM orders WHERE user_id = ?",
    "duration_ms": 482.7,
    "rows_examined": 45000
  }
}
```

### Metrics

Metrics show performance over time:

```json
{
  "timestamp": "2025-01-15T10:35:00.000Z",
  "metric_name": "http_request_duration_p95",
  "value": 523.45,
  "service": "order-service",
  "metric_type": "gauge",
  "unit": "ms",
  "anomaly_injected": true
}
```

The `anomaly_injected` flag helps identify synthetic anomalies.

### Traces

Traces show request flow through services:

```json
{
  "trace_id": "trace-xyz",
  "spans": [
    {
      "span_id": "span-1",
      "parent_span_id": null,
      "service": "api-gateway",
      "operation": "HTTP GET /api/orders/123",
      "duration_ms": 542.3,
      "status": "OK"
    },
    {
      "span_id": "span-2",
      "parent_span_id": "span-1",
      "service": "order-service",
      "operation": "getOrder",
      "duration_ms": 530.1
    }
  ]
}
```

### Timeline

Timeline shows incident events:

```json
{
  "incident_id": "abc123",
  "start_time": "2025-01-15T10:30:00.000Z",
  "end_time": "2025-01-15T11:30:00.000Z",
  "events": [
    {
      "timestamp": "2025-01-15T10:25:00.000Z",
      "event_type": "deployment",
      "description": "Deployed order-service from 1.5.1 to 1.5.2"
    },
    {
      "timestamp": "2025-01-15T10:32:00.000Z",
      "event_type": "anomaly_detected",
      "description": "Anomaly detected in http_request_duration_p95"
    }
  ]
}
```

## Part 3: Trying Other Incident Types

### Authentication Failure

```bash
python -m cli.main generate \
  --scenario auth_failure \
  --output ./auth_incident \
  --duration 30m \
  --severity SEV1
```

This generates:
- Auth error rate spikes
- Redis connection failures
- Cascading 401 errors

### Dependency Outage

```bash
python -m cli.main generate \
  --scenario dependency_outage \
  --output ./outage_incident \
  --duration 45m \
  --severity SEV1
```

This simulates:
- Database complete outage
- Multiple services affected
- Widespread failures

### Network Issues

```bash
python -m cli.main generate \
  --scenario packet_loss \
  --output ./network_incident \
  --duration 20m \
  --severity SEV2
```

This creates:
- Packet loss between services
- Connection timeouts
- Request retries

## Part 4: Creating Custom Scenarios

### Step 1: Create Scenario File

Create `scenarios/my_custom.yaml`:

```yaml
type: latency_regression
description: Custom API latency regression

parameters:
  affected_service: user-service
  baseline_latency_ms: 25.0
  degraded_latency_ms: 300.0
  error_threshold_ms: 500.0

metadata:
  category: performance
  common_causes:
    - Heavy query on user database
    - Increased user table size
```

### Step 2: Generate Custom Incident

```bash
python -m cli.main generate \
  --scenario my_custom \
  --output ./custom_incident \
  --duration 2h \
  --severity SEV3
```

### Step 3: Adjust Parameters

Edit the YAML to tune the incident:

```yaml
parameters:
  affected_service: user-service
  baseline_latency_ms: 50.0       # Increased baseline
  degraded_latency_ms: 800.0      # More severe degradation
  error_threshold_ms: 1500.0      # Higher error threshold
```

Regenerate to see the difference.

## Part 5: Integration with ADAPT Ecosystem

### Using with ADAPT-RCA

```bash
# Generate incident
python -m cli.main generate --scenario latency_regression --output ./incident

# Analyze with ADAPT-RCA
adapt-rca analyze --data ./incident
```

ADAPT-RCA will:
1. Load the synthetic data
2. Run root cause analysis algorithms
3. Identify the latency regression
4. Correlate with the deployment event

### Using with ADAPT-UI

```bash
# Generate incident
python -m cli.main generate --scenario auth_failure --output ./incident

# Visualize in ADAPT-UI
adapt-ui --load ./incident
```

ADAPT-UI will display:
- Interactive timeline
- Service dependency graph
- Metric visualizations
- Log search interface

## Part 6: Advanced Usage

### Generating Multiple Incidents

```bash
for i in {1..10}; do
  python -m cli.main generate \
    --scenario latency_regression \
    --output ./incidents/incident_$i \
    --duration 1h \
    --severity SEV2
done
```

### Batch Validation

```bash
for dir in ./incidents/*; do
  echo "Validating $dir"
  python -m cli.main validate "$dir"
done
```

### Extracting Statistics

```bash
# Count log entries
wc -l ./incident/logs/*.jsonl

# Count ERROR level logs
grep '"level": "ERROR"' ./incident/logs/*.jsonl | wc -l

# Find max latency
jq -r '.value' ./incident/metrics/*.jsonl | sort -n | tail -1
```

### Using in Python

```python
from datetime import datetime, timedelta
from pathlib import Path

from generator.core.base import IncidentContext
from generator.core.topology import TopologyGenerator
from generator.incidents.latency_regression import LatencyRegressionGenerator

# Create context
context = IncidentContext(
    start_time=datetime.utcnow(),
    duration=timedelta(hours=1),
    severity="SEV2",
    output_dir=Path("./my_incident")
)

# Generate topology
topo = TopologyGenerator(context)
topology = topo.generate()
context.topology = topology

# Generate incident
generator = LatencyRegressionGenerator(
    context,
    affected_service="order-service",
    baseline_latency_ms=50.0,
    degraded_latency_ms=500.0
)

result = generator.generate()
print(f"Generated incident: {result['incident_id']}")
```

## Tips and Best Practices

1. **Start Small**: Begin with short durations (30m) to iterate quickly
2. **Validate Early**: Always validate after generation
3. **Use Version Control**: Track your custom scenarios in git
4. **Document Scenarios**: Add detailed descriptions to YAML files
5. **Realistic Parameters**: Base parameters on real incidents when possible
6. **Combine with Real Data**: Mix synthetic and real data for testing

## Troubleshooting

### "Scenario not found"

Make sure the scenario file exists:
```bash
ls scenarios/
```

### "Schema validation failed"

Run with `--strict` to see detailed errors:
```bash
python -m cli.main validate ./incident --strict
```

### "Permission denied" on output

Check output directory permissions:
```bash
mkdir -p ./output
chmod 755 ./output
```

## Next Steps

- Read [Architecture](architecture.md) to understand internals
- Check [Schema Reference](schema.md) for detailed schemas
- Explore pre-generated datasets in `incident_packs/`
- Try integrating with your observability stack
- Contribute new incident types!

## Getting Help

- Open an issue on GitHub
- Check existing issues for solutions
- Reach out to the ADAPT team

Happy incident generating! 🚀
