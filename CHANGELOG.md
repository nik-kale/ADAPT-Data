# Changelog

All notable changes to ADAPT-Data will be documented in this file.

## [0.3.0] - 2025-01-16

### Added - Production-Ready Features

- **Centralized Logging Framework**: Structured logging throughout the codebase
  - Color-coded terminal output (INFO=green, WARNING=yellow, ERROR=red)
  - File logging support with module-level loggers
  - Replaced 40+ print() statements with proper logging
  - Production-ready observability

- **Input Validation Framework**: Pydantic-based validation
  - Type-safe validation for all configuration types
  - Security validation (path traversal prevention, size limits)
  - Comprehensive parameter validation for all incident types
  - Clear, actionable error messages

- **Utility CLI Commands**: Developer experience improvements
  - `version`: Show version and system information
  - `doctor`: Run health checks on installation
  - `clean`: Clean generated files with dry-run support
  - `info`: Quick dataset information display

### Fixed - Critical Bugs

- **Cascade Generator Data Merging**: Fixed critical data loss bug
  - Sub-incidents now write to unique subdirectories
  - Data is properly collected and merged
  - Timeline correctly correlates all incidents
  - No more data overwrites

- **Security Vulnerabilities**: Hardened against attacks
  - Path traversal prevention in file operations
  - Input sanitization and length limits
  - File size limits (1MB for scenario files)
  - Safe path resolution

- **Missing Error Handling**: Comprehensive error handling
  - All file operations now have try/except blocks
  - Detailed error logging with context
  - Graceful degradation where possible
  - No silent failures in exporters

- **Cascade Generator Registration**: Registered in GENERATOR_MAP
  - Cascade scenarios now accessible from CLI
  - Properly integrated with validation system

### Enhanced

- **OpenTelemetry Exporter**: Added comprehensive error handling
  - Line-by-line error tracking
  - Input validation before processing
  - Helpful error messages with file:line context

- **Prometheus Exporter**: Added comprehensive error handling
  - Server startup error handling
  - Metric replay error tracking
  - File operation error handling

- **Generate Command**: Security and validation improvements
  - Input validation using Pydantic models
  - Secure output directory creation
  - Proper error logging throughout

### Dependencies

- **Added**: `pydantic>=2.0.0` for input validation

### Documentation

- **Added**: V0.3.0_IMPROVEMENTS.md - Comprehensive release notes
- **Updated**: Version to 0.3.0 in pyproject.toml

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
