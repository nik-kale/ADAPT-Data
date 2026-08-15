# Changelog

All notable changes to ADAPT-Data will be documented in this file.

## [Unreleased]

### Added

- **Memory Leak Incident Type**: Gradual heap exhaustion ending in an OOM kill
  - Steadily rising heap with correlated GC pause and frequency degradation
  - Throughput decay as garbage collection takes CPU share
  - OOM kill at the container limit with optional restart and heap reset
  - Scenario: `scenarios/memory_leak.yaml`

- **Database Deadlock Incident Type**: Cyclic lock contention between transactions
  - Dialect-accurate errors for PostgreSQL (SQLSTATE 40P01) and MySQL (1213)
  - Paired application-side rollbacks and database-side deadlock detection
  - Blocked sessions, lock wait duration and connection pool saturation metrics
  - Scenario: `scenarios/deadlock.yaml`

- **Custom Topologies**: Define your own architecture in YAML
  - `--topology <name|path>` on `generate`, or a `topology:` key in a scenario
  - Bundled `ecommerce` and `saas-multitenant` topologies
  - Dependencies declarable per-service or as a top-level edge list
  - Validation catches unknown service types, duplicate names and dangling edges

- **Datadog Exporter**: Third export target alongside OpenTelemetry and Prometheus
  - Metrics (series API), logs (logs intake) and traces (APM) payloads
  - `export --format datadog --dd-signal {metrics,logs,traces,all}`
  - `--dd-service-prefix` keeps synthetic data separable from real telemetry
  - Log `dd.trace_id` matches the APM span IDs, so logs and traces join

- **Grafana Dashboards**: A dashboard per incident type, plus an overview
  - `adapt-data dashboards` regenerates them from specs
  - `docker compose -f dashboards/docker-compose.yml up` for a ready stack
  - Panels carry a `service` template variable and are verified by tests to
    reference only metrics the generators actually emit

- **Structured JSON Logging**: Machine-readable output for CI and log aggregation
  - `--log-format json` or `ADAPT_LOG_FORMAT=json`
  - Stable fields plus source location, exceptions, and `extra=` context

- **Correlation IDs**: Shared identifiers joining related telemetry
  - One ID spans the log, metric and trace for an event; spans inherit it
  - `correlation_density` controls what fraction of events are correlated
  - Added to the log, metric and trace schemas

- **Streaming JSONL Writer**: Constant-memory output for large datasets
  - `StreamingJSONLWriter` and `BaseGenerator.stream_jsonl()`
  - `stream_jsonl()` reader and `estimate_record_count()` helper

### Fixed

- **MemoryLeakInjector exceeded its memory cap**: jitter was applied after the
  `max_memory_mb` clamp, so readings could exceed the limit, and `has_crashed()`
  compared against that jittered value so its verdict flipped at random. Memory
  is now clamped after jitter, and crash detection uses the uncapped projection.
  Fixes two failing tests.
- **INFO logs were silently dropped**: handlers were attached to the `adapt_data`
  logger while modules log under `generator.*` / `cli.*`, which are not its
  children, so only ERROR and above reached the terminal via the last-resort
  handler. Handlers now go on the root logger.
- Invalid `category` and `change_type` values in new generators' config deltas
  now conform to `schema/config_delta_schema.json`.

## [0.4.0] - 2025-01-16

### Added - Advanced Features

- **Progress Indicators**: Rich library integration for beautiful progress bars
  - Spinner, bar, and time tracking for long operations
  - Automatic fallback to logging if rich unavailable
  - Context manager API: `get_progress_tracker().track()`

- **Parameterized Distributions**: 7 probability distributions for realistic data
  - Uniform, Normal, Exponential, LogNormal, Poisson, Weibull, Bimodal
  - Distribution factory for easy configuration
  - Predefined distributions for common metrics (latency, errors, throughput)

- **Time-Series Patterns**: Realistic temporal behavior
  - Seasonal patterns (daily, weekly, monthly cycles)
  - Trend patterns (linear, exponential growth/decline)
  - Burst patterns (periodic spikes)
  - Cyclical and composite patterns
  - Business hours, growth, and batch job patterns

- **Difficulty Levels**: Progressive complexity for challenges
  - 5 levels: Beginner, Easy, Medium, Hard, Expert
  - Adaptive complexity configuration (services, incidents, noise, correlations)
  - Scoring system with ranks (Novice to Master)
  - Recommendation engine for next difficulty

- **Configuration File System**: Centralized configuration management
  - `.adapt-data.yaml` configuration files
  - Hierarchical search (current → parent → home)
  - Environment variable overrides (`ADAPT_LOG_LEVEL`, etc.)
  - Sections: logging, generation, validation, export, advanced

- **Correlation Analysis**: Intelligent data relationship detection
  - Metric-metric correlations (Pearson)
  - Temporal pattern detection (trends)
  - Service error rate analysis
  - Anomaly correlation tracking (log-metric relationships)
  - New CLI command: `correlate`

- **Plugin System Framework**: Extensibility architecture
  - Three plugin types: Generators, Exporters, Analyzers
  - Auto-discovery from `~/.adapt-data/plugins/`
  - Plugin registry with lifecycle management
  - Base classes for custom plugins

### Enhanced

- **CLI**: New commands and improved UX
  - `correlate`: Analyze correlations in datasets
  - Progress indicators in all long-running operations

### Dependencies

- **No new required dependencies**: All features degrade gracefully
- **Optional**: `rich>=13.0` for progress bars (already in `[tui]`)

### Documentation

- **Added**: V0.4.0_IMPROVEMENTS.md - Comprehensive feature guide
- **Updated**: Version to 0.4.0 in pyproject.toml

### Breaking Changes

- **None**: Fully backward compatible with v0.3.0

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
