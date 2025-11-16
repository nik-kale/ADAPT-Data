# Schema Documentation

ADAPT-Data uses JSON schemas to ensure data quality and consistency. All generated data conforms to these schemas and can be validated using the built-in validation tools.

## Schema Files

All schemas are located in the `schema/` directory:

- `log_schema.json` - Log entry schema
- `metric_schema.json` - Metric data point schema
- `trace_schema.json` - Distributed trace schema
- `topology_schema.json` - Service topology schema
- `config_delta_schema.json` - Configuration change schema
- `timeline_schema.json` - Incident timeline schema

## Log Schema

Structured log entries with metadata and context.

### Required Fields

- `timestamp` (string, ISO 8601): When the log was generated
- `level` (enum): Log level - DEBUG, INFO, WARN, ERROR, FATAL
- `service` (string): Service or component name
- `message` (string): Log message content

### Optional Fields

- `trace_id` (string): Distributed trace ID
- `span_id` (string): Span ID within trace
- `host` (string): Host or pod identifier
- `region` (string): Cloud region or datacenter
- `metadata` (object): Additional structured data
  - `user_id`, `request_id`, `endpoint`, `method`
  - `status_code`, `duration_ms`, `error_code`
  - `stack_trace`
- `labels` (object): Key-value labels for categorization

### Example

```json
{
  "timestamp": "2025-01-15T10:30:45.123Z",
  "level": "ERROR",
  "service": "order-service",
  "host": "order-service-002",
  "message": "Database query timeout",
  "metadata": {
    "duration_ms": 5000,
    "error_code": "TIMEOUT",
    "query": "SELECT * FROM orders WHERE user_id = ?"
  }
}
```

## Metric Schema

Time-series metric data points with tags and metadata.

### Required Fields

- `timestamp` (string, ISO 8601): Measurement timestamp
- `metric_name` (string): Metric identifier
- `value` (number): Metric value
- `service` (string): Service name

### Optional Fields

- `metric_type` (enum): counter, gauge, histogram, summary
- `unit` (string): Unit of measurement (ms, bytes, requests, etc.)
- `host` (string): Host identifier
- `region` (string): Region
- `tags` (object): Metric dimensions/tags
- `anomaly_injected` (boolean): Flag for synthetic anomalies

### Example

```json
{
  "timestamp": "2025-01-15T10:30:00.000Z",
  "metric_name": "http_request_duration_p95",
  "value": 523.45,
  "service": "api-gateway",
  "metric_type": "gauge",
  "unit": "ms",
  "host": "api-gateway-001",
  "tags": {
    "endpoint": "/api/orders",
    "method": "GET"
  },
  "anomaly_injected": true
}
```

## Trace Schema

Distributed traces with parent-child span relationships.

### Required Fields

- `trace_id` (string): Unique trace identifier
- `spans` (array): List of spans in the trace

### Span Fields

Each span contains:
- `span_id` (string): Unique span ID
- `parent_span_id` (string|null): Parent span ID (null for root)
- `service` (string): Service executing the span
- `operation` (string): Operation name
- `start_time` (string, ISO 8601): Span start time
- `duration_ms` (number): Duration in milliseconds
- `status` (enum): OK, ERROR, TIMEOUT
- `tags` (object): Span metadata
- `logs` (array): Span-scoped log events

### Example

```json
{
  "trace_id": "abc123-def456",
  "spans": [
    {
      "span_id": "span-1",
      "parent_span_id": null,
      "service": "api-gateway",
      "operation": "HTTP GET /api/orders",
      "start_time": "2025-01-15T10:30:00.000Z",
      "duration_ms": 542.3,
      "status": "OK",
      "tags": {
        "http.method": "GET",
        "http.path": "/api/orders"
      }
    },
    {
      "span_id": "span-2",
      "parent_span_id": "span-1",
      "service": "order-service",
      "operation": "getOrders",
      "start_time": "2025-01-15T10:30:00.005Z",
      "duration_ms": 530.1,
      "status": "OK",
      "tags": {}
    }
  ]
}
```

## Topology Schema

Service dependency graph defining the system architecture.

### Required Fields

- `services` (array): List of services
- `dependencies` (array): Dependency edges

### Service Fields

- `name` (string): Service name
- `type` (enum): api, database, cache, queue, frontend, worker, gateway, auth, storage
- `instances` (integer): Number of replicas
- `region` (string): Primary region
- `metadata` (object): Additional metadata
  - `version`, `owner`, `tier`, `sla_target`

### Dependency Fields

- `from` (string): Source service
- `to` (string): Target service
- `type` (enum): http, grpc, database, cache, queue, storage
- `critical` (boolean): Whether dependency is critical

### Example

```json
{
  "services": [
    {
      "name": "api-gateway",
      "type": "gateway",
      "instances": 3,
      "region": "us-east-1",
      "metadata": {
        "version": "1.2.3",
        "tier": "critical",
        "sla_target": 99.9
      }
    }
  ],
  "dependencies": [
    {
      "from": "api-gateway",
      "to": "order-service",
      "type": "http",
      "critical": true
    }
  ]
}
```

## Config Delta Schema

Configuration changes over time.

### Required Fields

- `timestamp` (string, ISO 8601): When change occurred
- `service` (string): Affected service
- `change_type` (enum): deployment, config_update, scaling, feature_flag, secret_rotation, cert_renewal
- `changes` (array): List of changes

### Change Fields

- `key` (string): Configuration key
- `old_value`: Previous value
- `new_value`: New value
- `category` (enum): performance, security, feature, infrastructure, other

### Optional Fields

- `initiator` (string): Who/what made the change
- `rollback_available` (boolean): Whether change can be rolled back

### Example

```json
{
  "timestamp": "2025-01-15T10:25:00.000Z",
  "service": "payment-service",
  "change_type": "config_update",
  "initiator": "ops-team",
  "changes": [
    {
      "key": "max_concurrent_transactions",
      "old_value": 100,
      "new_value": 10,
      "category": "performance"
    }
  ],
  "rollback_available": true
}
```

## Timeline Schema

Incident timeline with key events.

### Required Fields

- `incident_id` (string): Unique incident ID
- `start_time` (string, ISO 8601): Incident start
- `end_time` (string, ISO 8601): Incident end
- `events` (array): Timeline events

### Event Fields

- `timestamp` (string, ISO 8601): Event time
- `event_type` (enum): anomaly_detected, alert_fired, config_change, deployment, mitigation_attempted, resolved, other
- `description` (string): Event description
- `service` (string): Related service
- `metadata` (object): Additional context

### Optional Timeline Fields

- `title` (string): Incident title
- `severity` (enum): SEV1, SEV2, SEV3, SEV4
- `affected_services` (array): List of affected services
- `root_cause` (string): Root cause description

### Example

```json
{
  "incident_id": "inc-123",
  "title": "Database latency regression",
  "start_time": "2025-01-15T10:30:00.000Z",
  "end_time": "2025-01-15T11:30:00.000Z",
  "severity": "SEV2",
  "affected_services": ["order-service"],
  "root_cause": "Inefficient database query introduced in deployment",
  "events": [
    {
      "timestamp": "2025-01-15T10:30:00.000Z",
      "event_type": "deployment",
      "description": "Deployed order-service v1.5.2",
      "service": "order-service"
    },
    {
      "timestamp": "2025-01-15T10:32:00.000Z",
      "event_type": "anomaly_detected",
      "description": "Anomaly detected in http_request_duration_p95",
      "service": "order-service",
      "metadata": {
        "threshold": 100.0,
        "actual_value": 500.0
      }
    }
  ]
}
```

## Validation

Use the built-in validator:

```bash
python -m cli.main validate ./output --strict
```

Or programmatically:

```python
import json
import jsonschema

with open('schema/log_schema.json') as f:
    schema = json.load(f)

with open('output/logs/logs_abc123.jsonl') as f:
    for line in f:
        record = json.loads(line)
        jsonschema.validate(instance=record, schema=schema)
```
