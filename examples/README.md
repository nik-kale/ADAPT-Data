# Examples

This directory contains example scenarios and sample outputs to help you get started with ADAPT-Data.

## Quick Start Example

Generate a simple latency regression incident:

```bash
cd examples
python generate_example.py
```

This will create a sample incident in `examples/outputs/`.

## Example Scenarios

The `scenarios/` directory contains example scenario configurations that demonstrate different use cases:

- **simple_latency.yaml** - Basic latency regression
- **multi_service_cascade.yaml** - Multi-service failure cascade
- **intermittent_issue.yaml** - Bursty, intermittent performance problem

## Sample Outputs

Pre-generated sample data is available in `outputs/` for:
- Quick testing
- Understanding output format
- Integration examples

## Using Examples

### Load Example in ADAPT-RCA

```bash
adapt-rca analyze --data ./outputs/sample_latency_incident
```

### Load Example in ADAPT-UI

```bash
adapt-ui --load ./outputs/sample_latency_incident
```

### Validate Example

```bash
python -m cli.main validate ./outputs/sample_latency_incident
```

## Creating Your Own Examples

1. Copy an example scenario
2. Modify parameters
3. Generate with:
```bash
python -m cli.main generate --scenario your_scenario --output ./outputs/your_output
```

## Example Code

See `generate_example.py` for a Python example of programmatic incident generation.
