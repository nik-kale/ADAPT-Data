# Changelog

All notable changes to ADAPT-Data will be documented in this file.

## [0.2.0] - 2025-01-16

### Added - Testing & Quality

- **Comprehensive Test Suite**: Unit and integration tests for all generators
  - Unit tests for utilities, anomaly injectors, and core components
  - Integration tests for incident generators validating schema conformance
  - 100+ test cases ensuring correctness

- **Property-Based Testing**: Added Hypothesis for robust testing
  - Tests mathematical properties of injectors and utilities
  - Catches edge cases automatically
  - Ensures invariants hold across all inputs

- **Golden File Testing**: Reproducibility validation
  - Tests ensure same seed produces identical output
  - Prevents regressions in generation logic

- **CI/CD Pipeline**: GitHub Actions workflow
  - Multi-platform testing (Linux, macOS, Windows)
  - Python 3.10, 3.11, 3.12 support
  - Automatic code quality checks (black, ruff, mypy)
  - Coverage reporting to Codecov
  - Package build validation

### Added - Core Features

- **Multi-Incident Cascades**: Generate cascading failure scenarios
  - Chain multiple incidents that trigger each other
  - Realistic failure propagation
  - Timeline correlation across incidents

- **Dataset Statistics & Profiling**: Analyze generated datasets
  - Comprehensive statistics on logs, metrics, traces
  - Distribution analysis and percentiles
  - Export stats to JSON

- **Interactive Configuration Wizard**: User-friendly scenario creation
  - Step-by-step prompts for all incident types
  - Parameter validation
  - Automatic YAML generation

### Added - Integration & Export

- **OpenTelemetry Exporter**: Export to OTLP format
  - Convert traces to OTLP format
  - Convert metrics to OTLP format
  - Compatible with OTel collectors

- **Prometheus Integration**: Metrics serving and export
  - Serve metrics via HTTP endpoint
  - Prometheus text format export
  - Configurable replay speed for testing

### Added - Education & Research

- **RCA Challenge Sets**: Training scenarios for root cause analysis
  - Progressive hint system
  - Scoring rubrics
  - Solution validation
  - Example challenge: "The Mysterious Latency Spike"

- **Real-World Incident Library**: Recreations of famous outages
  - Based on public postmortems
  - AWS, Google Cloud, Azure incidents
  - Educational and benchmarking purposes
  - Example: AWS US-EAST-1 Power Outage 2023

### Enhanced

- **Extended pyproject.toml**: Additional dependency groups
  - `[streaming]`: Kafka support for real-time generation
  - `[exporters]`: OpenTelemetry and Prometheus clients
  - `[tui]`: Rich and Textual for interactive UIs
  - `[all]`: Install everything

- **Updated CLI**: New commands
  - `stats`: Analyze dataset statistics
  - `wizard`: Interactive scenario builder
  - `export`: Export to OpenTelemetry/Prometheus
  - `serve`: HTTP metrics server

### Documentation

- **Expanded Test Coverage**: Tests directory with fixtures
- **Export Examples**: How to integrate with observability stacks
- **Challenge Documentation**: Creating and solving RCA challenges

## [0.1.0] - 2025-01-15

### Initial Release

- 6 incident generators (latency, auth, dependency, config, packet loss, noise)
- JSON schemas for all telemetry types
- YAML-based scenario definitions
- CLI for generation and validation
- Comprehensive documentation
- Production-ready codebase with type hints
