# Custom Topology Definitions

Define custom service architectures for ADAPT-Data incident generation. Topology files enable modeling your actual production environment instead of using the default topology.

## Quick Start

### Using a Pre-Built Topology

```yaml
# In your scenario YAML file
type: latency_regression
topology: fintech  # References topology/fintech.yaml

parameters:
  affected_service: transaction-service
  # ... other parameters
```

### Creating a Custom Topology

Create a YAML file in `topology/`:

```yaml
name: my-platform
version: "1.0"
description: My custom microservices architecture

services:
  - name: api-gateway
    type: gateway
    instances: 3
    region: us-east-1
    metadata:
      version: "1.0.0"
      tier: critical
      sla_target: 99.9

  - name: user-service
    type: api
    instances: 4
    region: us-east-1
    metadata:
      version: "2.1.0"
      tier: high
      sla_target: 99.5

  - name: postgres-primary
    type: database
    instances: 1
    region: us-east-1
    metadata:
      version: "14.5"
      tier: critical
      sla_target: 99.99

dependencies:
  - from: api-gateway
    to: user-service
    type: http
    critical: true

  - from: user-service
    to: postgres-primary
    type: database
    critical: true
```

## Topology Schema

### Root Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Topology identifier |
| `version` | string | Yes | Semantic version |
| `description` | string | No | Human-readable description |
| `services` | array | Yes | List of service definitions |
| `dependencies` | array | Yes | List of dependency edges |

### Service Definition

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique service identifier |
| `type` | string | Yes | Service type (see below) |
| `instances` | integer | Yes | Number of instances/replicas |
| `region` | string | Yes | Deployment region |
| `metadata` | object | No | Additional metadata |

**Service Types:**
- `gateway` - API gateway, load balancer
- `api` - Backend API service
- `auth` - Authentication/authorization service
- `worker` - Background worker, job processor
- `database` - Database (SQL or NoSQL)
- `cache` - Cache service (Redis, Memcached)
- `queue` - Message queue (Kafka, RabbitMQ)

**Metadata Fields (Optional):**
- `version` - Application version
- `tier` - Criticality tier (critical, high, medium, low)
- `sla_target` - Uptime SLA target (0-100)

### Dependency Definition

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `from` | string | Yes | Source service name |
| `to` | string | Yes | Target service name |
| `type` | string | Yes | Connection type |
| `critical` | boolean | Yes | Whether dependency is critical |

**Dependency Types:**
- `http` - HTTP/REST API call
- `grpc` - gRPC call
- `database` - Database connection
- `cache` - Cache connection
- `queue` - Message queue connection

## Pre-Built Topologies

### E-Commerce Platform (`e-commerce.yaml`)

Standard e-commerce architecture with:
- 10 services
- API gateway, auth, user, order, payment, inventory services
- PostgreSQL database, Redis cache, RabbitMQ queue
- 17 dependencies

**Use for:** Retail, marketplace, shopping applications

### FinTech Platform (`fintech.yaml`)

Financial services architecture with:
- 11 services
- Enhanced auth, fraud detection, compliance services
- Transaction processing, account management
- Kafka messaging, PostgreSQL with replicas
- 15 dependencies

**Use for:** Banking, payments, financial applications

## Advanced Usage

### Multi-Region Topologies

```yaml
services:
  - name: api-gateway-us
    type: gateway
    instances: 3
    region: us-east-1

  - name: api-gateway-eu
    type: gateway
    instances: 3
    region: eu-west-1

  - name: postgres-us
    type: database
    instances: 1
    region: us-east-1

  - name: postgres-eu-replica
    type: database
    instances: 1
    region: eu-west-1

dependencies:
  - from: api-gateway-us
    to: postgres-us
    type: database
    critical: true

  - from: api-gateway-eu
    to: postgres-eu-replica
    type: database
    critical: true
```

### Cascading Failures

Define critical paths for cascade incident scenarios:

```yaml
dependencies:
  # Critical path: gateway -> auth -> database
  - from: api-gateway
    to: auth-service
    type: http
    critical: true  # Failure propagates

  - from: auth-service
    to: postgres-primary
    type: database
    critical: true  # Failure propagates

  # Non-critical: cache failures don't cascade
  - from: api-gateway
    to: redis-cache
    type: cache
    critical: false  # Graceful degradation
```

### Variable Instance Counts

Scale services independently:

```yaml
services:
  # High-traffic user-facing service
  - name: api-gateway
    instances: 10

  # Moderate traffic
  - name: user-service
    instances: 4

  # Low traffic admin service
  - name: admin-service
    instances: 2

  # Singleton database
  - name: postgres-primary
    instances: 1
```

## Validation

Topology files are validated when loaded:

```bash
# Generate with custom topology
python -m cli.main generate \
  --scenario my_scenario \
  --output ./output

# Validation errors will be reported:
# - Missing required fields
# - Invalid service references in dependencies
# - Circular dependencies
# - YAML syntax errors
```

## Integration with Scenarios

Reference topologies in scenario files:

```yaml
# scenarios/custom_incident.yaml
type: latency_regression
topology: fintech  # Load topology/fintech.yaml

parameters:
  affected_service: transaction-service  # Must exist in topology
  baseline_latency_ms: 100.0
  degraded_latency_ms: 800.0
```

If `topology` is not specified, the default ADAPT-Data topology is used.

## Topology Output

Generated datasets include the resolved topology:

```
output/
├── topology/
│   └── topology.json  # Complete topology with all services and dependencies
├── logs/
├── metrics/
└── traces/
```

The `topology.json` file contains:
- All services with metadata
- Complete dependency graph
- Topology name and version
- Service instance counts

## Best Practices

### 1. Model Your Actual Architecture

Use service names and relationships that match your production environment for realistic incident scenarios.

### 2. Include Critical Paths

Mark dependencies as `critical: true` if failure should propagate. This enables cascade incident generation.

### 3. Realistic Instance Counts

Match production instance counts for accurate resource utilization patterns.

### 4. Use Metadata

Add version, tier, and SLA information for richer incident context:

```yaml
metadata:
  version: "2.3.1"
  tier: critical
  sla_target: 99.99
  team: platform
  oncall: platform-oncall@company.com
```

### 5. Document Dependencies

Comment complex dependency relationships:

```yaml
dependencies:
  # Payment processing critical path
  - from: order-service
    to: payment-service
    type: http
    critical: true  # Orders fail if payments are down
```

## Troubleshooting

### Topology File Not Found

```
FileNotFoundError: Topology file not found: my-topology
```

**Solutions:**
- Place file in `topology/` directory
- Use filename without `.yaml` extension in scenario
- Or provide full path: `topology: /path/to/my-topology.yaml`

### Invalid Service Reference

```
ValueError: Dependency references unknown service: unknown-service
```

**Solution:** Ensure all services referenced in `dependencies` are defined in `services`.

### YAML Syntax Error

```
ValueError: Invalid topology YAML: ...
```

**Solution:** Validate YAML syntax:
```bash
python -c "import yaml; yaml.safe_load(open('topology/my-topology.yaml'))"
```

## Examples

See included topology files:
- `e-commerce.yaml` - Standard e-commerce architecture
- `fintech.yaml` - Financial services with fraud detection

## Contributing

When adding topology templates:
1. Use descriptive service names
2. Include realistic dependency graph
3. Add metadata for all services
4. Document the topology's intended use case
5. Ensure all dependencies reference existing services

## License

Same as ADAPT-Data project license.

