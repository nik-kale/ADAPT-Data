# ADAPT-Data Feature Discovery Analysis

**Repository**: ADAPT-Data
**Analysis Date**: 2025-12-26
**Analyzer**: Senior Software Architect Review

---

## Executive Summary

ADAPT-Data is a well-architected synthetic telemetry and incident dataset generator. The codebase demonstrates solid fundamentals with comprehensive validation, typed Python, and good test coverage. This analysis identifies 8 high-impact feature opportunities that would meaningfully enhance the project while remaining achievable by a single developer in 1-5 days each.

---

## Summary Table

| # | Feature | Category | Effort | Value | Priority |
|---|---------|----------|--------|-------|----------|
| 1 | Streaming JSON Output for Large Datasets | Code Quality | Low | High | **3.0** |
| 2 | Memory Leak Incident Generator | Functional | Medium | High | **1.5** |
| 3 | Structured JSON Logging Option | Observability | Low | Medium | **2.0** |
| 4 | Datadog Exporter Integration | Functional | Medium | High | **1.5** |
| 5 | Customizable Topology via YAML | Architecture | Medium | High | **1.5** |
| 6 | Grafana Dashboard Templates | Documentation/DX | Low | High | **3.0** |
| 7 | Database Deadlock Incident Generator | Functional | Medium | Medium | **1.0** |
| 8 | Correlation ID Propagation | Observability | Low | Medium | **2.0** |

---

## Detailed Feature Requests

---

### Feature #1: Streaming JSON Output for Large Datasets

**Category**: Code Quality & Optimization

**Problem Statement**:
Currently, all generated data is held in memory before being written to disk (see `generator/core/base.py:134-156` - `save_jsonl()` method). For long-duration incidents or high-frequency metrics, this can cause memory exhaustion. Users generating datasets for production RCA testing often need multi-hour incident windows which can produce millions of data points.

**Proposed Solution**:
- Add a `StreamingJSONWriter` class that writes records directly to disk as they're generated
- Implement a `yield`-based generation pattern in incident generators
- Add `--streaming` flag to CLI generate command
- Provide memory usage estimates before generation begins
- Add progress updates showing records written vs memory used

**Implementation Approach**:
```python
# generator/core/streaming.py
class StreamingJSONLWriter:
    def __init__(self, filepath: Path, buffer_size: int = 1000):
        self.filepath = filepath
        self.buffer = []
        self.buffer_size = buffer_size

    def write(self, record: dict) -> None:
        self.buffer.append(record)
        if len(self.buffer) >= self.buffer_size:
            self.flush()

    def flush(self) -> None:
        with open(self.filepath, 'a') as f:
            for record in self.buffer:
                f.write(json.dumps(record, default=str) + '\n')
        self.buffer.clear()
```

**Impact Assessment**:
- **Effort**: Low (1-2 days)
- **Value**: High - Enables enterprise-scale dataset generation
- **Priority Score**: 3.0

**Success Metrics**:
- Memory usage stays constant regardless of dataset size
- Successfully generate 10M+ record datasets without OOM
- Generation throughput remains within 20% of non-streaming mode

---

### Feature #2: Memory Leak Incident Generator

**Category**: Functional Enhancement

**Problem Statement**:
Memory leaks are one of the most common and difficult-to-diagnose production incidents. The current 6 incident types (`latency_regression`, `auth_failure`, `dependency_outage`, `config_drift`, `packet_loss`, `bursty_noise`) don't include this critical scenario. RCA systems training on ADAPT-Data will lack exposure to this common failure mode.

**Proposed Solution**:
- Create `MemoryLeakGenerator` in `generator/incidents/memory_leak.py`
- Generate realistic signals: gradually increasing memory usage, eventual OOM killer events, garbage collection pressure logs
- Include correlated signals: increased GC pause times, reduced throughput, eventual container restarts
- Support for gradual leak (slow) and rapid leak (fast) patterns

**Implementation Approach**:
```python
class MemoryLeakGenerator(BaseGenerator):
    """Simulates gradual memory exhaustion leading to OOM."""

    def __init__(self, context, affected_service, leak_rate_mb_per_min=10.0,
                 initial_memory_mb=512.0, max_memory_mb=2048.0):
        # Signals to generate:
        # - memory_usage_bytes (gauge) - linear increase with noise
        # - gc_pause_duration_ms - increases as memory grows
        # - gc_collection_count - increases frequency
        # - container_restart events at OOM threshold
```

**Impact Assessment**:
- **Effort**: Medium (2-3 days)
- **Value**: High - Addresses critical gap in incident coverage
- **Priority Score**: 1.5

**Success Metrics**:
- Generated datasets correctly show memory growth pattern
- Correlated GC metrics exhibit realistic degradation
- OOM events trigger appropriate restart signals

---

### Feature #3: Structured JSON Logging Option

**Category**: Observability Stack

**Problem Statement**:
The current logging system (`generator/core/logging_config.py:33-100`) outputs human-readable formatted logs. For production deployments and CI/CD pipelines, structured JSON logs are preferred for parsing by log aggregation systems. Users running ADAPT-Data in automated pipelines cannot easily integrate logs with their observability stack.

**Proposed Solution**:
- Add `--log-format json` CLI option
- Create `StructuredJSONFormatter` that outputs JSON-serialized log records
- Include standard fields: timestamp, level, logger, message, and arbitrary context
- Support log correlation IDs for tracing generation steps
- Add environment variable `ADAPT_LOG_FORMAT=json` for non-interactive usage

**Implementation Approach**:
```python
class StructuredJSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, 'correlation_id', None),
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)
```

**Impact Assessment**:
- **Effort**: Low (1 day)
- **Value**: Medium - Improves CI/CD and production integration
- **Priority Score**: 2.0

**Success Metrics**:
- All log output parseable as valid JSON when `--log-format json` specified
- No performance degradation vs text logging
- Logs queryable in common log aggregation tools (Loki, Elasticsearch)

---

### Feature #4: Datadog Exporter Integration

**Category**: Functional Enhancement

**Problem Statement**:
ADAPT-Data currently supports OpenTelemetry and Prometheus exports (`generator/exporters/`). Datadog is one of the most widely-used observability platforms in enterprise environments. Teams using Datadog cannot directly import generated incidents for RCA training or demos without manual conversion.

**Proposed Solution**:
- Create `DatadogExporter` class in `generator/exporters/datadog.py`
- Support Datadog metrics API format (JSON payload with metric points)
- Support Datadog logs API format
- Support Datadog APM trace format
- Add `--format datadog` option to export command
- Include optional `--dd-api-key` for direct submission to Datadog

**Implementation Approach**:
```python
class DatadogExporter:
    """Export ADAPT-Data to Datadog format."""

    def export_metrics(self, output_path: Path) -> None:
        """Export metrics in Datadog submit format."""
        # Convert to Datadog series format:
        # { "series": [{ "metric": "name", "points": [[timestamp, value]], "tags": [...] }] }

    def export_traces(self, output_path: Path) -> None:
        """Export traces in Datadog APM format."""
        # Convert to Datadog trace format with spans, service, resource, type
```

**Impact Assessment**:
- **Effort**: Medium (2-3 days)
- **Value**: High - Unlocks large enterprise user base
- **Priority Score**: 1.5

**Success Metrics**:
- Exported files pass Datadog API validation
- Successfully import 1000+ traces to Datadog
- Metrics appear correctly in Datadog dashboards

---

### Feature #5: Customizable Topology via YAML

**Category**: Architecture & Scalability

**Problem Statement**:
The current topology generator (`generator/core/topology.py:26-143`) uses a hardcoded default microservices architecture. Users simulating incidents in their specific architectures (e.g., different service names, regions, dependencies) must modify Python code. This limits adoption by users who want to model their actual production topology.

**Proposed Solution**:
- Add support for topology YAML files: `topology/*.yaml`
- Allow scenarios to reference custom topologies: `topology: my_architecture.yaml`
- Validate topology files against a JSON schema
- Provide topology templates for common architectures (e-commerce, fintech, SaaS)
- Auto-generate dependency graphs from topology definitions

**Implementation Approach**:
```yaml
# topology/my_architecture.yaml
name: my-production-topology
version: "1.0"
services:
  - name: frontend
    type: gateway
    instances: 5
    region: us-west-2
    dependencies:
      - target: api-server
        type: http
        critical: true
  - name: api-server
    type: api
    instances: 10
    dependencies:
      - target: postgres-primary
        type: database
        critical: true
```

**Impact Assessment**:
- **Effort**: Medium (2-3 days)
- **Value**: High - Enables real-world topology simulation
- **Priority Score**: 1.5

**Success Metrics**:
- Users can generate incidents using custom topologies without code changes
- Topology validation catches invalid configurations
- Generated incident data correctly references custom service names

---

### Feature #6: Grafana Dashboard Templates

**Category**: Documentation & Developer Experience

**Problem Statement**:
Users generate incident datasets but have no easy way to visualize them. Manually creating Grafana dashboards for each incident type is time-consuming. This creates friction for demos, training sessions, and validating generated data quality.

**Proposed Solution**:
- Create Grafana dashboard JSON templates in `dashboards/grafana/`
- One dashboard per incident type showing key signals
- Include a "master" dashboard showing cross-incident comparisons
- Add `adapt-data dashboards export` command to generate Grafana-importable JSON
- Include docker-compose example with Grafana + Prometheus pre-configured

**Implementation Approach**:
```
dashboards/
├── grafana/
│   ├── latency_regression.json
│   ├── auth_failure.json
│   ├── dependency_outage.json
│   ├── config_drift.json
│   ├── packet_loss.json
│   ├── bursty_noise.json
│   └── incident_overview.json
├── docker-compose.grafana.yml
└── README.md
```

**Impact Assessment**:
- **Effort**: Low (1-2 days)
- **Value**: High - Dramatically improves demo and validation experience
- **Priority Score**: 3.0

**Success Metrics**:
- Users can visualize incidents with single docker-compose command
- Dashboard panels correctly show incident signals
- Documentation includes screenshots and usage examples

---

### Feature #7: Database Deadlock Incident Generator

**Category**: Functional Enhancement

**Problem Statement**:
Database deadlocks are a common production incident pattern, especially in high-concurrency systems. The current incident types don't model this scenario. Deadlocks have unique signals (lock wait timeouts, transaction rollbacks, specific error patterns) that differ from general latency issues.

**Proposed Solution**:
- Create `DeadlockGenerator` in `generator/incidents/deadlock.py`
- Generate realistic signals: lock wait timeouts, transaction rollbacks, connection pool exhaustion
- Model multi-table deadlock scenarios with cyclic wait patterns
- Include database-specific error messages (PostgreSQL, MySQL variants)
- Support for partial deadlock resolution and cascading failures

**Implementation Approach**:
```python
class DeadlockGenerator(BaseGenerator):
    """Simulates database deadlock scenarios."""

    def __init__(self, context, affected_service, database_service="postgres-primary",
                 deadlock_frequency=0.1, affected_tables=None):
        # Signals:
        # - lock_wait_timeout errors in logs
        # - pg_stat_activity showing blocked queries
        # - transaction_rollback_count metric spike
        # - connection_pool_exhausted warnings
```

**Impact Assessment**:
- **Effort**: Medium (2-3 days)
- **Value**: Medium - Important but less common than memory leaks
- **Priority Score**: 1.0

**Success Metrics**:
- Deadlock signals match real PostgreSQL/MySQL error patterns
- Lock wait chains visible in generated data
- RCA systems can identify circular dependencies

---

### Feature #8: Correlation ID Propagation in Generated Data

**Category**: Observability Stack

**Problem Statement**:
The current generation (`generator/incidents/*.py`) creates individual logs, metrics, and traces but doesn't consistently propagate correlation IDs across data types. This makes it harder for RCA systems to correlate related signals across different telemetry types - a key challenge in real incident analysis.

**Proposed Solution**:
- Add `correlation_id` field to all generated telemetry
- Ensure logs, metrics, and traces for the same "event" share correlation IDs
- Generate request chains with proper parent-child correlation
- Include `x-request-id` style headers in trace metadata
- Add `--correlation-density` flag to control how many events get correlated

**Implementation Approach**:
```python
class CorrelatedEventGenerator:
    def generate_correlated_event(self, timestamp, service, event_type):
        correlation_id = generate_uuid()

        # Generate log with correlation_id
        log = {"correlation_id": correlation_id, ...}

        # Generate metric with correlation_id in tags
        metric = {"tags": {"correlation_id": correlation_id}, ...}

        # Generate trace with correlation_id as attribute
        trace = {"attributes": {"correlation_id": correlation_id}, ...}
```

**Impact Assessment**:
- **Effort**: Low (1-2 days)
- **Value**: Medium - Improves realism and RCA training quality
- **Priority Score**: 2.0

**Success Metrics**:
- 80%+ of events have traceable correlation chains
- RCA systems can group related events correctly
- Correlation IDs are unique and don't collide

---

## Additional Observations

### Strengths Identified
1. **Excellent validation infrastructure** - Pydantic models, JSON schemas, path traversal protection
2. **Comprehensive test coverage** - Unit, integration, and golden file tests
3. **Well-documented** - 12 documentation files covering all major topics
4. **Clean architecture** - Clear separation between generators, exporters, and CLI

### Minor Improvements (Not Prioritized)
- Add `py.typed` marker for better IDE support
- Consider async support for exporters (future scalability)
- Add dependency vulnerability scanning to CI
- Create contributing.md with PR templates

---

## Competitive Comparison

| Feature | ADAPT-Data | Locust | Chaos Monkey | Gremlin |
|---------|-----------|--------|--------------|---------|
| Incident Types | 6 | N/A | 3 | 10+ |
| Trace Generation | Yes | No | No | Limited |
| Custom Topologies | Partial | N/A | No | Yes |
| Observability Export | 2 formats | N/A | No | Yes |
| Open Source | Yes | Yes | Yes | No |

ADAPT-Data fills a unique niche in synthetic observability data generation. The recommended features would strengthen competitive position particularly in enterprise adoption (Datadog export, custom topologies) and realistic incident coverage (memory leaks, deadlocks).

---

## Recommended Implementation Order

1. **Sprint 1 (Quick Wins)**:
   - Streaming JSON Output (#1) - Unblocks enterprise use
   - Grafana Dashboard Templates (#6) - Immediate demo value

2. **Sprint 2 (Core Features)**:
   - Memory Leak Generator (#2) - Critical incident type
   - Customizable Topology (#5) - Major adoption enabler

3. **Sprint 3 (Ecosystem Integration)**:
   - Datadog Exporter (#4) - Enterprise reach
   - Structured JSON Logging (#3) - CI/CD friendliness

4. **Sprint 4 (Polish)**:
   - Correlation ID Propagation (#8) - RCA quality
   - Deadlock Generator (#7) - Incident coverage

---

*Analysis complete. All features are designed for incremental implementation with backward compatibility.*
