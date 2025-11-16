# Incident Packs

This directory contains pre-generated incident datasets for quick testing and demos.

## Structure

Each subdirectory contains a complete incident dataset:

```
latency/
├── logs/
├── metrics/
├── traces/
├── config_deltas/
├── timelines/
└── topology/
```

## Available Packs

- **latency/** - Latency regression incidents
- **auth/** - Authentication failure spikes
- **dependency/** - Dependency outage scenarios
- **config/** - Configuration drift incidents
- **network/** - Packet loss and network issues
- **multi/** - Multi-service cascade failures

## Usage

You can use these pre-generated datasets directly with ADAPT-RCA or ADAPT-UI:

```bash
# Point ADAPT-RCA to a pre-generated incident
adapt-rca analyze --data ./incident_packs/latency/example_001

# Load in ADAPT-UI
adapt-ui --load ./incident_packs/latency/example_001
```

## Generating New Packs

To generate additional incident packs:

```bash
python -m cli.main generate --scenario latency_regression --output ./incident_packs/latency/new_incident
```
