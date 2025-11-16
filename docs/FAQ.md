# Frequently Asked Questions (FAQ)

Common questions, issues, and solutions for ADAPT-Data.

## Table of Contents

- [Installation](#installation)
- [Getting Started](#getting-started)
- [Generation](#generation)
- [Configuration](#configuration)
- [Data Quality](#data-quality)
- [Performance](#performance)
- [Troubleshooting](#troubleshooting)
- [Integration](#integration)
- [Advanced Usage](#advanced-usage)

## Installation

### Q: How do I install ADAPT-Data?

**A:** Install from source or pip:

```bash
# From source (recommended for development)
git clone https://github.com/your-org/ADAPT-Data.git
cd ADAPT-Data
pip install -e .

# From pip (when available)
pip install adapt-data

# With optional dependencies
pip install "adapt-data[all]"  # Everything
pip install "adapt-data[tui]"  # Progress bars
pip install "adapt-data[exporters]"  # OpenTelemetry, Prometheus
```

### Q: What Python version is required?

**A:** Python 3.10 or higher.

```bash
# Check your Python version
python --version

# If too old, install newer Python
# Ubuntu/Debian
sudo apt install python3.10

# macOS with Homebrew
brew install python@3.10
```

### Q: Installation fails with "No module named 'pydantic'"

**A:** Install dependencies:

```bash
# Install all dependencies
pip install -r requirements.txt

# Or specific dependency
pip install pydantic>=2.0.0
```

### Q: How do I verify installation?

**A:** Run the doctor command:

```bash
python -m cli.main doctor --verbose
```

Expected output:
```
✓ Python version: 3.10.0
✓ Required dependencies installed
✓ Optional dependencies: rich (available)
✓ Configuration file: .adapt-data.yaml
✓ All checks passed
```

## Getting Started

### Q: How do I generate my first incident?

**A:** Use the generate command:

```bash
python -m cli.main generate \
  --scenario latency_regression \
  --output ./my-first-incident \
  --duration 1h
```

### Q: What scenarios are available?

**A:** List all scenarios:

```bash
python -m cli.main list-scenarios
```

Built-in incident types:
- `latency_regression`: Performance degradation
- `auth_failure`: Authentication failures
- `dependency_outage`: Dependency failures
- `config_drift`: Configuration issues
- `packet_loss`: Network degradation
- `bursty_noise`: Resource contention

### Q: How do I create a custom scenario?

**A:** Create a YAML file in `scenarios/`:

```yaml
# scenarios/my_scenario.yaml
type: latency_regression
description: My custom latency issue

parameters:
  affected_service: my-service
  baseline_latency_ms: 100.0
  degraded_latency_ms: 1000.0
  error_threshold_ms: 2000.0

metadata:
  category: performance
```

Use with:
```bash
python -m cli.main generate --scenario my_scenario --output ./data
```

See [Scenarios Guide](scenarios.md) for details.

### Q: How do I use the interactive wizard?

**A:** Run the wizard command:

```bash
python -m cli.main wizard
```

Follow the prompts to create a scenario interactively.

## Generation

### Q: How long does generation take?

**A:** Depends on incident duration:

| Duration | Time | Data Size |
|----------|------|-----------|
| 30m      | ~2s  | ~5 MB     |
| 1h       | ~3s  | ~10 MB    |
| 2h       | ~5s  | ~20 MB    |
| 24h      | ~45s | ~200 MB   |

### Q: Can I generate reproducible datasets?

**A:** Yes, use a random seed:

```bash
# Via config file
echo "generation:
  random_seed: 42" >> .adapt-data.yaml

# Via environment variable
export ADAPT_RANDOM_SEED=42

# Generate (will produce identical output each time)
python -m cli.main generate --scenario latency_regression --output ./data
```

### Q: How do I generate datasets for different severity levels?

**A:** Use the `--severity` flag:

```bash
# SEV1: Critical
python -m cli.main generate --scenario dependency_outage --severity SEV1

# SEV2: Major
python -m cli.main generate --scenario auth_failure --severity SEV2

# SEV3: Moderate (default)
python -m cli.main generate --scenario latency_regression --severity SEV3

# SEV4: Minor
python -m cli.main generate --scenario config_drift --severity SEV4
```

Severity affects:
- Anomaly magnitude
- Error rates
- Duration of peak impact
- Number of affected services

### Q: What is difficulty level?

**A:** Difficulty controls scenario complexity for training/benchmarking:

```bash
python -m cli.main generate \
  --scenario latency_regression \
  --difficulty hard
```

Levels:
- **Beginner**: 1-2 services, clear signals, low noise
- **Easy**: 2-3 services, obvious correlations
- **Medium**: 3-5 services, moderate noise
- **Hard**: 5-10 services, high noise, multiple concurrent anomalies
- **Expert**: 10+ services, very high noise, cascading failures

### Q: How do I generate multi-hour or multi-day incidents?

**A:** Use the `--duration` flag:

```bash
# 4 hours
python -m cli.main generate --scenario latency --duration 4h

# 12 hours
python -m cli.main generate --scenario auth_failure --duration 12h

# 3 days (72 hours)
python -m cli.main generate --scenario dependency_outage --duration 72h
```

**Note:** Long durations take more time and memory.

### Q: Can I generate data for specific time ranges?

**A:** Not directly, but you can adjust timestamps in generated data:

```python
import json
from datetime import datetime, timedelta

# Load generated metrics
with open("output/metrics/metrics_*.jsonl") as f:
    metrics = [json.loads(line) for line in f]

# Shift to desired time
target_start = datetime(2025, 1, 15, 14, 30, 0)
for metric in metrics:
    # Parse and shift timestamp
    ts = datetime.fromisoformat(metric["timestamp"].replace("Z", ""))
    shifted = target_start + (ts - original_start)
    metric["timestamp"] = shifted.isoformat() + "Z"
```

## Configuration

### Q: Where should I put `.adapt-data.yaml`?

**A:** Three options:

1. **Project directory** (recommended for teams):
   ```bash
   cd /path/to/project
   cat > .adapt-data.yaml <<EOF
   generation:
     default_duration: 2h
   EOF
   ```

2. **Home directory** (personal preferences):
   ```bash
   cat > ~/.adapt-data.yaml <<EOF
   logging:
     level: DEBUG
   EOF
   ```

3. **Parent directories**: ADAPT-Data searches up to 10 levels

Priority: Project > Parent dirs > Home directory

### Q: What settings should I use for CI/CD?

**A:** Recommended CI/CD configuration:

```yaml
# .adapt-data.yaml (check into repo)
logging:
  level: INFO
  enable_colors: false  # Plain text in CI

generation:
  enable_progress: false  # No progress bars in CI
  random_seed: 42        # Reproducible tests

validation:
  strict_mode: true  # Fail on warnings

advanced:
  enable_patterns: false  # Disable time-based patterns
```

Environment variables in CI:
```yaml
# .github/workflows/test.yml
env:
  ADAPT_LOG_LEVEL: INFO
  ADAPT_ENABLE_PROGRESS: false
  ADAPT_RANDOM_SEED: 42
```

### Q: How do I disable progress bars?

**A:** Three ways:

```bash
# 1. Config file
echo "generation:
  enable_progress: false" >> .adapt-data.yaml

# 2. Environment variable
export ADAPT_ENABLE_PROGRESS=false

# 3. Progress bars auto-disable in non-TTY (pipes, CI)
python -m cli.main generate ... | tee log.txt  # No progress shown
```

### Q: How do I change the log level?

**A:** Multiple options:

```bash
# 1. Config file
echo "logging:
  level: DEBUG" >> .adapt-data.yaml

# 2. Environment variable (overrides config)
export ADAPT_LOG_LEVEL=DEBUG

# 3. Edit Python code (not recommended)
# generator/core/logging_config.py
```

Levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`

## Data Quality

### Q: How realistic is the generated data?

**A:** Very realistic for synthetic data:

- **Distributions**: Uses realistic probability distributions (LogNormal for latency, Poisson for counts)
- **Patterns**: Daily/weekly business patterns, seasonal trends
- **Correlations**: Correlated anomalies across dependent services
- **Noise**: Realistic variance and jitter
- **Ground Truth**: All anomalies labeled for validation

**Limitations:**
- Not based on real production data (by design)
- Simplified service topologies
- Predictable patterns (can be tuned)

### Q: How do I validate generated data?

**A:** Use the validate command:

```bash
# Standard validation
python -m cli.main validate ./output

# Strict mode (fail on warnings)
python -m cli.main validate ./output --strict
```

Checks:
- Schema conformance
- Timestamp validity and monotonicity
- Required fields presence
- Value ranges
- Anomaly presence during incident window

### Q: How do I ensure data has anomalies?

**A:** Check the validation output:

```bash
python -m cli.main validate ./output
```

Look for:
```
✓ Metrics in metrics_*.jsonl: 245 anomalous, 615 baseline
✓ ERROR/WARN logs present during incident window
```

If no anomalies detected:
1. Check incident window timing
2. Verify scenario parameters (multipliers, error rates)
3. Check if incident type supports anomalies

### Q: How do I analyze generated data?

**A:** Use the stats and correlate commands:

```bash
# Dataset statistics
python -m cli.main stats ./output

# Correlation analysis
python -m cli.main correlate ./output

# Export for further analysis
python -m cli.main stats ./output --output stats.json
python -m cli.main correlate ./output --output correlations.json
```

## Performance

### Q: Why is generation slow?

**A:** Several factors:

1. **Long duration**: 24h takes longer than 1h
2. **Advanced features**: Distributions, patterns add overhead
3. **Difficulty level**: Higher difficulty = more services/data
4. **Disk I/O**: Writing large files

**Solutions:**

```yaml
# Faster generation
advanced:
  enable_distributions: false
  enable_patterns: false
  enable_correlation: false
  noise_level: 0.05

generation:
  parallel_generation: true  # Experimental
```

### Q: Why is memory usage high?

**A:** Data is generated in-memory before writing.

**Solutions:**

1. **Reduce duration**:
   ```bash
   python -m cli.main generate --duration 30m  # Instead of 24h
   ```

2. **Disable advanced features**:
   ```yaml
   advanced:
     enable_patterns: false
     enable_correlation: false
   ```

3. **Use streaming** (future feature)

### Q: Can I generate data in parallel?

**A:** Experimental feature:

```yaml
generation:
  parallel_generation: true
```

**Note:** May cause issues with reproducibility and memory usage. Test thoroughly.

### Q: How much disk space is needed?

**A:** Rough estimates:

| Duration | Disk Space |
|----------|------------|
| 30m      | ~5 MB      |
| 1h       | ~10 MB     |
| 2h       | ~20 MB     |
| 24h      | ~200 MB    |
| 7 days   | ~1.4 GB    |

Varies based on:
- Incident type
- Difficulty level
- Number of services
- Advanced features enabled

## Troubleshooting

### Q: "ModuleNotFoundError: No module named 'generator'"

**A:** Install ADAPT-Data properly:

```bash
# From project directory
pip install -e .

# Verify installation
python -c "import generator; print('OK')"
```

### Q: "FileNotFoundError: scenarios/latency_regression.yaml"

**A:** Run from project root directory:

```bash
# Check current directory
pwd

# Should be in ADAPT-Data root
cd /path/to/ADAPT-Data

# Verify scenarios exist
ls scenarios/
```

Or use full path:
```bash
python -m cli.main generate --scenario /full/path/to/scenario.yaml
```

### Q: "ValidationError: Invalid parameter value"

**A:** Check scenario parameters:

```yaml
# Common errors:
type: auth_failure
parameters:
  affected_service: auth-service
  baseline_error_rate: 0.001  # Must be 0.0-1.0 (not 0.1%)
  spike_error_rate: 25        # ERROR: Should be 0.25 (not 25%)
```

Fix:
```yaml
  baseline_error_rate: 0.001
  spike_error_rate: 0.25  # Correct: 0.25 = 25%
```

### Q: Progress bars not showing

**A:** Common causes:

1. **Rich not installed**:
   ```bash
   pip install rich>=13.0
   ```

2. **Disabled in config**:
   ```yaml
   generation:
     enable_progress: true
   ```

3. **Non-TTY environment** (expected):
   ```bash
   # Progress bars don't show in pipes or CI
   python -m cli.main generate ... | tee log.txt
   ```

### Q: Generated data has no errors during incident

**A:** Check error parameters:

```yaml
# For auth_failure
parameters:
  baseline_error_rate: 0.001  # 0.1% baseline
  spike_error_rate: 0.25      # Must be significantly higher

# For latency_regression
parameters:
  error_threshold_ms: 1000.0  # Errors when latency exceeds this
  degraded_latency_ms: 500.0  # Must be < threshold for no errors
```

Solution: Increase spike_error_rate or ensure degraded_latency_ms > error_threshold_ms

### Q: "Configuration file not found" warning

**A:** This is informational, not an error. ADAPT-Data uses defaults.

To remove warning:
```bash
# Create config file
cat > .adapt-data.yaml <<EOF
logging:
  level: INFO
EOF
```

### Q: Output validation fails

**A:** Common issues:

1. **Non-monotonic timestamps**: Bug in custom generator
2. **Missing required fields**: Schema violation
3. **Invalid values** (NaN, Inf): Math error in generation

Run validation with verbose logging:
```bash
export ADAPT_LOG_LEVEL=DEBUG
python -m cli.main validate ./output --strict
```

Check specific issues reported and fix generator code.

## Integration

### Q: How do I use with ADAPT-RCA?

**A:** Generate data, then analyze with ADAPT-RCA:

```bash
# 1. Generate incident data
python -m cli.main generate \
  --scenario latency_regression \
  --output ./incident-data

# 2. Analyze with ADAPT-RCA
adapt-rca analyze --data ./incident-data
```

### Q: How do I export to Prometheus?

**A:** Use the export command:

```bash
# Export to Prometheus text format
python -m cli.main export ./output \
  --format prometheus \
  --output metrics.prom

# Or serve via HTTP
python -m cli.main serve ./output --port 9090
```

Then scrape with Prometheus:
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'adapt-data'
    static_configs:
      - targets: ['localhost:9090']
```

### Q: How do I export to OpenTelemetry?

**A:** Use the export command:

```bash
# Export traces
python -m cli.main export ./output \
  --format opentelemetry \
  --output traces.json

# Export metrics
python -m cli.main export ./output \
  --format opentelemetry \
  --output metrics.json
```

### Q: How do I integrate with Elasticsearch?

**A:** Load JSONL logs directly:

```bash
# Bulk import logs
curl -X POST "localhost:9200/_bulk" \
  -H "Content-Type: application/x-ndjson" \
  --data-binary "@output/logs/logs_*.jsonl"
```

Or use Filebeat:
```yaml
# filebeat.yml
filebeat.inputs:
  - type: log
    paths:
      - /path/to/output/logs/*.jsonl
    json.keys_under_root: true
```

### Q: How do I use with Grafana?

**A:** Via Prometheus or direct JSON:

**Option 1: Prometheus datasource**
```bash
# Serve metrics
python -m cli.main serve ./output --port 9090
```
Add `http://localhost:9090` as Prometheus datasource in Grafana.

**Option 2: JSON datasource**
Install JSON datasource plugin and point to `output/metrics/metrics_*.jsonl`.

## Advanced Usage

### Q: How do I create cascading incidents?

**A:** Use cascade scenario type:

```yaml
# scenarios/cascade.yaml
type: cascade
description: Multi-stage cascading failure

incidents:
  - type: config_drift
    delay_minutes: 0
    parameters:
      affected_service: payment-service
      config_key: pool_size
      old_value: 100
      new_value: 10

  - type: latency_regression
    delay_minutes: 5
    parameters:
      affected_service: payment-service
      baseline_latency_ms: 50.0
      degraded_latency_ms: 800.0

  - type: dependency_outage
    delay_minutes: 15
    parameters:
      failed_service: payment-service
      dependent_services: [order-service, user-service]
```

### Q: How do I create custom generators?

**A:** See [Plugin Development Guide](plugin_development.md):

```python
from generator.core.base import BaseGenerator

class MyGenerator(BaseGenerator):
    def generate(self):
        # Custom logic
        pass
```

### Q: How do I add custom metrics?

**A:** Extend incident generators:

```python
from generator.incidents.latency_regression import LatencyRegressionGenerator

class ExtendedGenerator(LatencyRegressionGenerator):
    def generate(self):
        result = super().generate()

        # Add custom metrics
        custom_metrics = self._generate_custom_metrics()
        self.save_jsonl(custom_metrics, "custom_metrics.jsonl", "metrics")

        return result
```

### Q: How do I simulate specific real-world incidents?

**A:** Model after real incidents:

```yaml
# Based on AWS US-EAST-1 outage
type: dependency_outage
description: Power outage in data center

parameters:
  failed_service: availability-zone-1a
  dependent_services:
    - ec2-instances
    - rds-primary
    - elasticache
    - load-balancer

metadata:
  category: infrastructure
  incident_date: "2023-06-13"
  reference: "https://aws.amazon.com/message/..."
```

See `real_world_incidents/` directory for examples.

### Q: Can I train ML models on this data?

**A:** Yes! Common use cases:

1. **Anomaly detection**:
   - Use `anomaly_injected` field as ground truth labels
   - Train on metrics with anomaly_injected=false
   - Test on anomaly_injected=true

2. **Root cause analysis**:
   - Train on topology + metrics + logs
   - Predict affected_service from patterns

3. **Time-series forecasting**:
   - Use baseline periods for training
   - Test on incident periods

**Example:**
```python
import pandas as pd

# Load metrics
metrics = pd.read_json("output/metrics/metrics_*.jsonl", lines=True)

# Split by anomaly flag
baseline = metrics[metrics["anomaly_injected"] == False]
anomalies = metrics[metrics["anomaly_injected"] == True]

# Train model
model.fit(baseline[["value"]])
predictions = model.predict(anomalies[["value"]])
```

## Getting Help

### Q: Where can I get help?

**A:**

1. **Documentation**: Read [docs/](.)
2. **GitHub Issues**: https://github.com/your-org/ADAPT-Data/issues
3. **Discussions**: GitHub Discussions
4. **Community**: ADAPT community channels

### Q: How do I report a bug?

**A:** Open GitHub issue with:

1. ADAPT-Data version: `python -m cli.main version`
2. Python version: `python --version`
3. OS: `uname -a` (Linux/Mac) or `systeminfo` (Windows)
4. Steps to reproduce
5. Expected vs actual behavior
6. Logs (enable DEBUG: `export ADAPT_LOG_LEVEL=DEBUG`)

### Q: How do I request a feature?

**A:** Open GitHub issue with:

1. Use case description
2. Proposed solution (if any)
3. Alternative solutions considered
4. Why this benefits ADAPT-Data users

### Q: How do I contribute?

**A:** See [CONTRIBUTING.md](../CONTRIBUTING.md):

1. Fork repository
2. Create feature branch
3. Make changes with tests
4. Submit pull request
5. Respond to review feedback

## Related Documentation

- [Tutorial](tutorial.md) - Getting started guide
- [Configuration](configuration.md) - Configuration options
- [Scenarios](scenarios.md) - Creating scenarios
- [Generation](generation.md) - How generation works
- [UPGRADE](UPGRADE.md) - Upgrading between versions
