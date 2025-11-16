# Output Data Validation

ADAPT-Data includes comprehensive output validation to ensure generated telemetry data meets quality standards for training and analysis.

## Overview

The validation system performs quality checks on all generated data including:
- **Metrics**: Time-series metric data
- **Logs**: Application and system logs
- **Traces**: Distributed traces

Validation runs automatically after generation (when enabled) or can be invoked manually.

## Validation Checks

### Timestamp Validation
- **Format**: Verifies timestamps are in ISO 8601 format (`YYYY-MM-DDTHH:MM:SS.fffffZ`)
- **Monotonicity**: Ensures timestamps are monotonically increasing within each file
- **Range**: Checks timestamps fall within expected incident window (30 min buffer before/after)

### Metric Validation
- **Required Fields**: `timestamp`, `metric_name`, `value`, `service`
- **Value Validation**:
  - No NaN or Inf values
  - Numeric types only (int or float)
  - Negative values flagged for non-gauge metrics
- **Anomaly Presence**: Verifies anomalies exist during incident window
- **Baseline Data**: Checks baseline data exists before/after incident

### Log Validation
- **Required Fields**: `timestamp`, `level`, `service`, `message`
- **Log Levels**: Must be one of: DEBUG, INFO, WARN, WARNING, ERROR, FATAL, CRITICAL
- **Message Validation**: Non-empty string messages
- **Error/Warning Presence**: Ensures problematic logs exist during incident

### Trace Validation
- **Required Fields**: `trace_id`, `timestamp`, `spans`
- **Span Validation**:
  - Required span fields: `span_id`, `service`, `operation`, `start_time`, `duration_ms`
  - Duration must be non-negative, numeric, and finite
  - Service names must be consistent

### Service Consistency
- Service names referenced in data must exist in topology
- Common infrastructure services are automatically allowed

## Configuration

Validation is controlled via `.adapt-data.yaml`:

```yaml
validation:
  validate_on_generation: true  # Enable automatic validation after generation
  strict_mode: false            # Enable strict validation (fails on warnings)
```

Environment variable override:
```bash
ADAPT_VALIDATE_ON_GENERATION=true
```

## Usage

### Automatic Validation

When `validate_on_generation: true` (default), validation runs automatically:

```bash
adapt-data generate --scenario latency_regression --output ./output
```

Output:
```
Generating latency_regression incident...
Running output validation...
✓ Validation passed: 3 files validated
  Validation report saved to: ./output/validation_report.json
```

### Manual Validation

Call `validate_output()` on any generator:

```python
from generator.core.base import IncidentContext
from generator.incidents.latency_regression import LatencyRegressionGenerator

# Create and run generator
generator = LatencyRegressionGenerator(context)
result = generator.generate()

# Validate output
validation_results = generator.validate_output()

# Check results
if validation_results["summary"]["validation_passed"]:
    print("✓ Validation passed!")
else:
    print(f"✗ Found {validation_results['summary']['total_errors']} errors")
```

### Using the Standalone Validate Command

Validate existing datasets:

```bash
adapt-data validate ./output --strict
```

## Validation Results

The `validate_output()` method returns a dictionary:

```python
{
    "errors": [           # Critical issues that break data integrity
        "Metric at index 5 has NaN value",
        "Log timestamp format invalid"
    ],
    "warnings": [         # Issues that may affect analysis quality
        "Service 'unknown-svc' not in topology",
        "No ERROR logs found during incident"
    ],
    "info": [            # Informational messages
        "Validating 1500 metrics from metrics_abc123.jsonl",
        "Log levels: {'ERROR': 12, 'INFO': 145, 'WARN': 8}"
    ],
    "summary": {
        "total_errors": 2,
        "total_warnings": 5,
        "files_validated": 3,
        "validation_passed": false  # True if no errors
    }
}
```

### Validation Report

When automatic validation runs, a detailed report is saved to:
```
<output_dir>/validation_report.json
```

This JSON file contains all validation results for auditing and debugging.

## Error Handling

### Errors (Critical Issues)
- Invalid timestamp formats
- NaN/Inf metric values
- Missing required fields
- Non-monotonic timestamps (strict ordering)
- Negative durations in traces
- Invalid log levels

### Warnings (Quality Issues)
- Unknown service names
- Missing anomalies during incident
- Missing baseline data
- No ERROR/WARN logs
- Timestamps outside expected range
- Empty log messages

### Info Messages
- File processing status
- Data distribution statistics
- Anomaly/baseline counts
- Log level distributions

## Best Practices

1. **Always enable validation during development**:
   ```yaml
   validation:
     validate_on_generation: true
   ```

2. **Review validation reports** in `validation_report.json`

3. **Fix errors immediately** - errors indicate data quality issues

4. **Investigate warnings** - may indicate scenario configuration problems

5. **Use strict mode for production**:
   ```yaml
   validation:
     strict_mode: true  # Treat warnings as errors
   ```

## Example Output

```
$ adapt-data generate --scenario latency_regression --output ./output

Loading scenario: latency_regression.yaml
Generating topology...
Generating latency_regression incident...
  Generated 1500 metric points
  Generated 850 log entries
  Generated 20 traces
Running output validation...
  Validating 1500 metrics from metrics_abc123.jsonl
  Metrics: 750 anomalous, 750 baseline
  Validating 850 log entries from logs_abc123.jsonl
  Log levels: {'DEBUG': 50, 'ERROR': 12, 'INFO': 780, 'WARN': 8}
  Validating 20 traces from traces_abc123.jsonl
✓ Validation passed: 3 files validated
  Validation report saved to: ./output/validation_report.json
✓ Successfully generated incident: abc123
  Output directory: ./output
  Incident type: latency_regression
  Duration: 1h
  Severity: SEV3
```

## Extending Validation

To add custom validation checks, subclass `BaseGenerator` and override validation methods:

```python
class CustomGenerator(BaseGenerator):
    def _validate_metrics(self, issues: dict[str, list[str]]) -> None:
        """Add custom metric validation."""
        super()._validate_metrics(issues)

        # Add custom checks
        metrics_dir = self.context.output_dir / "metrics"
        for metrics_file in metrics_dir.glob("*.jsonl"):
            metrics = self._load_jsonl(metrics_file)

            # Custom validation logic
            for metric in metrics:
                if metric["value"] > 10000:
                    issues["warnings"].append(
                        f"Unusually high metric value: {metric['value']}"
                    )
```

## Troubleshooting

### Common Issues

**"Non-monotonic timestamps" error**
- Cause: Timestamps not in ascending order
- Fix: Check time-series generation logic, ensure proper sorting

**"No anomalies detected" warning**
- Cause: Incident window has no anomalous data
- Fix: Verify anomaly injection is working correctly

**"Unknown service" warning**
- Cause: Service referenced in data not in topology
- Fix: Add service to topology or fix service name typos

**"Invalid timestamp format" error**
- Cause: Timestamp not in ISO 8601 format
- Fix: Use `timestamp_to_iso()` utility function

## Performance

Validation performance scales linearly with data volume:
- ~1000 metrics/second
- ~2000 logs/second
- ~500 traces/second

For large datasets (>100MB), validation may take several seconds.

## See Also

- [Data Generation Guide](./generation.md)
- [Scenario Configuration](./scenarios.md)
- [Configuration Reference](./configuration.md)
