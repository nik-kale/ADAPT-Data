# OpenTelemetry Integration Guide

ADAPT-Data v2.0 provides comprehensive OpenTelemetry (OTEL) support, including OTLP export, semantic conventions compliance, profiling data generation, and seamless integration with the OTEL ecosystem.

## Table of Contents

- [Overview](#overview)
- [Exporting to OTLP Format](#exporting-to-otlp-format)
- [Semantic Conventions](#semantic-conventions)
- [Profiling Data](#profiling-data)
- [OTEL Collector Setup](#otel-collector-setup)
- [Integration Examples](#integration-examples)
- [Multi-Format Export](#multi-format-export)

## Overview

OpenTelemetry is the industry standard for observability instrumentation. ADAPT-Data generates synthetic telemetry that fully complies with OTEL specifications, making it ideal for:

- Testing OTEL pipelines and collectors
- Developing OTEL-based observability solutions
- Training teams on OTEL concepts
- Benchmarking OTEL backends

## Exporting to OTLP Format

### Export Traces

```python
from pathlib import Path
from generator.exporters.opentelemetry import OpenTelemetryExporter

# Initialize exporter
exporter = OpenTelemetryExporter(dataset_dir=Path("./output"))

# Export traces in OTLP format
exporter.export_traces(output_path=Path("./output/otlp/traces.json"))
```

### Export Metrics

```python
# Export metrics in OTLP format
exporter.export_metrics(output_path=Path("./output/otlp/metrics.json"))
```

### OTLP Format Structure

ADAPT-Data generates OTLP-compliant JSON that can be:
- Posted directly to OTLP HTTP endpoints
- Converted to protobuf for gRPC
- Ingested by any OTLP-compatible backend

**Example OTLP Trace:**

```json
{
  "resourceSpans": [{
    "resource": {
      "attributes": [
        {"key": "service.name", "value": {"stringValue": "api-service"}},
        {"key": "service.version", "value": {"stringValue": "1.0.0"}}
      ]
    },
    "scopeSpans": [{
      "scope": {"name": "adapt-data"},
      "spans": [{
        "traceId": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
        "spanId": "a1b2c3d4e5f6g7h8",
        "name": "GET /api/users",
        "kind": 3,
        "startTimeUnixNano": 1704067200000000000,
        "endTimeUnixNano": 1704067200050000000,
        "attributes": [
          {"key": "http.method", "value": {"stringValue": "GET"}},
          {"key": "http.status_code", "value": {"intValue": 200}}
        ],
        "status": {"code": 1}
      }]
    }]
  }]
}
```

## Semantic Conventions

ADAPT-Data follows OpenTelemetry Semantic Conventions for all generated telemetry.

### Using Semantic Conventions

```python
from generator.core.semantic_conventions import SemanticConventions

# HTTP span attributes
http_attrs = SemanticConventions.get_http_span_attributes(
    method="POST",
    url="https://api.example.com/users",
    status_code=201,
    route="/users"
)

# Database span attributes
db_attrs = SemanticConventions.get_database_span_attributes(
    system="postgresql",
    operation="SELECT",
    table="users",
    statement="SELECT * FROM users WHERE id = $1"
)

# Resource attributes
resource_attrs = SemanticConventions.get_resource_attributes(
    service_name="payment-service",
    service_version="2.1.0",
    deployment_environment="production"
)
```

### Supported Conventions

- **HTTP**: Methods, status codes, routes, user agents
- **Database**: Systems, operations, tables, statements
- **RPC**: gRPC, Thrift, custom RPC frameworks
- **Messaging**: Kafka, RabbitMQ, SQS, pub/sub systems
- **Kubernetes**: Pods, deployments, namespaces, nodes
- **GenAI**: LLM calls, token usage, model parameters

### GenAI Semantic Conventions (New!)

```python
# GenAI span attributes
genai_attrs = SemanticConventions.get_genai_span_attributes(
    system="openai",
    model="gpt-4",
    input_tokens=150,
    output_tokens=300,
    temperature=0.7,
    max_tokens=1000
)
```

## Profiling Data

ADAPT-Data v2.0 introduces profiling data generation compatible with OpenTelemetry profiling signals.

### Generating CPU Profiles

```python
from datetime import datetime, timedelta
from generator.core.profiling import ProfilingGenerator

# Initialize profiling generator
profiler = ProfilingGenerator(service="api-service", host="api-001")

# Generate CPU profile
cpu_profile = profiler.generate_cpu_profile(
    start_time=datetime.utcnow(),
    duration=timedelta(seconds=30),
    num_samples=100,
    is_anomalous=True  # Inject anomalous CPU patterns
)

# Export to OTLP format
otlp_profile = profiler.to_otlp_format(cpu_profile)

# Or export to pprof format
pprof_profile = profiler.to_pprof_format(cpu_profile)
```

### Generating Memory Profiles

```python
# Generate memory/heap profile with leak pattern
memory_profile = profiler.generate_memory_profile(
    start_time=datetime.utcnow(),
    duration=timedelta(seconds=30),
    num_samples=100,
    is_anomalous=True  # Inject memory leak pattern
)
```

### Generating Goroutine Profiles

```python
# Generate goroutine profile showing leak
goroutine_profile = profiler.generate_goroutine_profile(
    start_time=datetime.utcnow(),
    is_anomalous=True  # Show goroutine leak
)
```

### Profile Types

| Type | Description | Use Case |
|------|-------------|----------|
| CPU | CPU usage samples with stack traces | Identify CPU hotspots |
| Memory/Heap | Memory allocation samples | Detect memory leaks |
| Goroutine | Goroutine count and stacks | Find goroutine leaks |

## OTEL Collector Setup

ADAPT-Data can generate OTEL Collector configurations optimized for your use case.

### Basic Configuration

```python
from pathlib import Path
from generator.exporters.otel_collector_config import OTELCollectorConfigGenerator

# Initialize config generator
config_gen = OTELCollectorConfigGenerator(output_dir=Path("./config"))

# Generate basic config
config_path = config_gen.generate_basic_config(
    receivers=["otlp", "prometheus"],
    exporters=["logging", "prometheusremotewrite", "jaeger"],
    include_profiling=True
)
```

This generates a complete `otel-collector-config.yaml`:

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318
  prometheus:
    config:
      scrape_configs:
        - job_name: adapt-data-metrics
          scrape_interval: 15s
          static_configs:
            - targets: ['localhost:9090']

processors:
  batch:
    timeout: 10s
    send_batch_size: 1024
  memory_limiter:
    check_interval: 1s
    limit_mib: 512
    spike_limit_mib: 128
  resource:
    attributes:
      - key: telemetry.source
        value: adapt-data
        action: upsert

exporters:
  logging:
    loglevel: info
  prometheusremotewrite:
    endpoint: http://prometheus:9090/api/v1/write
  jaeger:
    endpoint: jaeger:14250

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, resource, batch]
      exporters: [logging, jaeger]
    metrics:
      receivers: [otlp, prometheus]
      processors: [memory_limiter, resource, batch]
      exporters: [logging, prometheusremotewrite]
    profiles:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [logging]
```

### Kubernetes Configuration

```python
# Generate Kubernetes-optimized config
k8s_config = config_gen.generate_kubernetes_config(
    namespace="adapt-data",
    include_service_mesh=True  # Includes Istio/Linkerd support
)
```

### Docker Compose Setup

```python
# Generate complete Docker Compose setup
compose_path = config_gen.generate_docker_compose(
    include_backends=True  # Includes Prometheus, Jaeger
)
```

Run the stack:

```bash
docker-compose up -d
```

Access UIs:
- **Jaeger UI**: http://localhost:16686
- **Prometheus**: http://localhost:9091
- **Collector Metrics**: http://localhost:8888/metrics

## Integration Examples

### Sending Data to OTEL Collector

```bash
# Start OTEL Collector
docker-compose up -d otel-collector

# Generate incident data
python -m cli.main generate \
  --scenario latency_regression \
  --output ./incident_data

# Export to OTLP
python -m cli.main export \
  --input ./incident_data \
  --format otlp \
  --output ./otlp_export

# Send to collector
curl -X POST http://localhost:4318/v1/traces \
  -H "Content-Type: application/json" \
  -d @./otlp_export/traces.json
```

### Integration with Observability Backends

#### Datadog

```yaml
exporters:
  datadog:
    api:
      site: datadoghq.com
      key: ${DD_API_KEY}
```

#### New Relic

```yaml
exporters:
  otlphttp:
    endpoint: https://otlp.nr-data.net:4318
    headers:
      api-key: ${NEW_RELIC_LICENSE_KEY}
```

#### Grafana Cloud

```yaml
exporters:
  otlphttp:
    endpoint: https://otlp-gateway-prod-us-central-0.grafana.net/otlp
    headers:
      authorization: Basic ${GRAFANA_CLOUD_API_KEY}
```

## Multi-Format Export

ADAPT-Data supports multiple trace formats beyond OTLP.

### Jaeger Format

```python
from generator.exporters.jaeger import JaegerExporter

jaeger_exporter = JaegerExporter(dataset_dir=Path("./output"))
jaeger_exporter.export_traces(output_path=Path("./jaeger/traces.json"))
```

Upload to Jaeger:

```bash
curl -X POST http://localhost:14268/api/traces \
  -H "Content-Type: application/json" \
  -d @./jaeger/traces.json
```

### Zipkin Format

```python
from generator.exporters.zipkin import ZipkinExporter

zipkin_exporter = ZipkinExporter(dataset_dir=Path("./output"))
zipkin_exporter.export_traces(output_path=Path("./zipkin/traces.json"))
```

Upload to Zipkin:

```bash
curl -X POST http://localhost:9411/api/v2/spans \
  -H "Content-Type: application/json" \
  -d @./zipkin/traces.json
```

### Prometheus Format

```python
from generator.exporters.prometheus import PrometheusExporter

prom_exporter = PrometheusExporter(dataset_dir=Path("./output"))

# Export to text format
prom_exporter.export_text_format(output_path=Path("./prom/metrics.txt"))

# Or serve via HTTP for scraping
prom_exporter.serve(port=9090, replay_speed=10.0)  # 10x speed
```

## Best Practices

1. **Use Semantic Conventions**: Always use the provided semantic convention helpers for consistent attribute naming
2. **Enable Profiling**: Include profiling data for comprehensive performance analysis
3. **Batch Processing**: Use the OTEL Collector's batch processor to optimize throughput
4. **Resource Attributes**: Set resource attributes to identify synthetic data
5. **Sampling**: For large datasets, configure appropriate sampling in the collector

## Troubleshooting

### Collector Not Receiving Data

Check the collector is listening:

```bash
curl http://localhost:13133/  # Health check
```

### Invalid OTLP Format

Validate generated JSON:

```bash
python -m cli.main validate ./output --format otlp
```

### High Memory Usage

Adjust collector memory limiter:

```yaml
processors:
  memory_limiter:
    limit_mib: 1024
    spike_limit_mib: 256
```

## References

- [OpenTelemetry Specification](https://opentelemetry.io/docs/specs/otel/)
- [OTLP Protocol](https://opentelemetry.io/docs/specs/otlp/)
- [Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/)
- [OTEL Collector](https://opentelemetry.io/docs/collector/)
- [Profiling Signals](https://opentelemetry.io/docs/specs/otel/profiles/)
