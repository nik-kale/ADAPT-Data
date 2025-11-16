# Scenario File Format

This document provides a comprehensive guide to creating custom scenario files for ADAPT-Data incident generation.

## Overview

Scenarios define incident parameters in YAML format. Each scenario specifies:
- Incident type
- Parameters specific to that incident
- Metadata for categorization and documentation

## Basic Structure

All scenario files follow this structure:

```yaml
type: <incident_type>
description: <human-readable description>

parameters:
  <parameter1>: <value1>
  <parameter2>: <value2>
  # ... more parameters

metadata:
  category: <category>
  common_causes:
    - <cause1>
    - <cause2>
  detection_signals:
    - <signal1>
    - <signal2>
  mitigation_strategies:
    - <strategy1>
    - <strategy2>
```

### Top-Level Fields

- **`type`** (required): Incident type identifier
- **`description`** (required): Human-readable description of the scenario
- **`parameters`** (required): Type-specific configuration parameters
- **`metadata`** (optional): Additional information for documentation and analysis

## Incident Types

ADAPT-Data supports 6 incident types. Each has specific parameters.

### 1. Latency Regression

Simulates performance degradation due to inefficient code, queries, or resource exhaustion.

**Type:** `latency_regression`

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `affected_service` | string | Yes | - | Name of the service experiencing latency issues |
| `baseline_latency_ms` | float | Yes | - | Normal latency in milliseconds |
| `degraded_latency_ms` | float | Yes | - | Elevated latency during incident (ms) |
| `error_threshold_ms` | float | Yes | - | Latency threshold that triggers errors (ms) |

**Example:**

```yaml
type: latency_regression
description: Database query regression causing elevated API latency

parameters:
  affected_service: order-service
  baseline_latency_ms: 50.0
  degraded_latency_ms: 500.0
  error_threshold_ms: 1000.0

metadata:
  category: performance
  common_causes:
    - Inefficient database query
    - Missing index
    - N+1 query problem
    - Increased data volume
  detection_signals:
    - p95 latency spike
    - Slow query logs
    - Database CPU increase
  mitigation_strategies:
    - Rollback deployment
    - Add database index
    - Optimize query
    - Scale database
```

**Generated Data:**
- Metrics: Latency (p50, p95, p99), error rate, throughput
- Logs: Slow query warnings, timeout errors
- Traces: Spans with elevated duration
- Timeline: Latency degradation progression

### 2. Authentication Failure

Models authentication service failures from cache or database issues.

**Type:** `auth_failure`

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `affected_service` | string | Yes | - | Authentication service name |
| `baseline_error_rate` | float | Yes | - | Normal error rate (0.0-1.0) |
| `spike_error_rate` | float | Yes | - | Error rate during incident (0.0-1.0) |

**Example:**

```yaml
type: auth_failure
description: Authentication service failures due to cache unavailability

parameters:
  affected_service: auth-service
  baseline_error_rate: 0.001  # 0.1% normal error rate
  spike_error_rate: 0.25      # 25% during incident

metadata:
  category: availability
  common_causes:
    - Redis connection pool exhaustion
    - Cache service outage
    - Network connectivity issues
    - Resource limits hit
  detection_signals:
    - Auth error rate spike
    - 401/403 response increase
    - Cache connection errors
  mitigation_strategies:
    - Increase cache connection limits
    - Restart cache service
    - Implement graceful degradation
    - Add circuit breakers
```

**Generated Data:**
- Metrics: Error rate, auth attempts, cache connection failures
- Logs: Auth failures (401/403), cache errors
- Traces: Failed authentication spans
- Timeline: Error rate spike progression

### 3. Dependency Outage

Simulates complete failure of a critical dependency causing cascading failures.

**Type:** `dependency_outage`

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `failed_service` | string | Yes | - | Name of the failed dependency |
| `dependent_services` | list[string] | Yes | - | Services that depend on the failed service |

**Example:**

```yaml
type: dependency_outage
description: Complete database outage causing cascading service failures

parameters:
  failed_service: postgres-primary
  dependent_services:
    - user-service
    - order-service
    - payment-service

metadata:
  category: availability
  common_causes:
    - Infrastructure failure
    - Resource exhaustion
    - Disk full
    - Network partition
  detection_signals:
    - Service health check failures
    - Connection errors across multiple services
    - 500 error rate spike
  mitigation_strategies:
    - Failover to replica
    - Restart database
    - Clear disk space
    - Fix network partition
```

**Generated Data:**
- Metrics: Error rate (500s), connection failures, health check failures
- Logs: Database connection errors, service unavailable messages
- Traces: Failed database connection spans
- Timeline: Cascade progression across dependent services

### 4. Configuration Drift

Simulates unintended configuration changes causing performance issues.

**Type:** `config_drift`

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `affected_service` | string | Yes | - | Service with configuration change |
| `config_key` | string | Yes | - | Name of the changed configuration |
| `old_value` | any | Yes | - | Previous (correct) value |
| `new_value` | any | Yes | - | New (problematic) value |

**Example:**

```yaml
type: config_drift
description: Configuration change reducing resource limits causing performance degradation

parameters:
  affected_service: payment-service
  config_key: max_concurrent_transactions
  old_value: 100
  new_value: 10

metadata:
  category: configuration
  common_causes:
    - Accidental configuration change
    - Auto-tuning gone wrong
    - Copy-paste error
    - Misunderstanding of setting
  detection_signals:
    - Resource pool exhaustion
    - Queue depth increase
    - Latency increase
    - Config change event correlation
  mitigation_strategies:
    - Rollback configuration
    - Review change history
    - Implement config validation
    - Add change approvals
```

**Generated Data:**
- Metrics: Queue depth, resource utilization, latency
- Logs: Configuration change events, resource exhaustion warnings
- Config deltas: Before/after configuration values
- Timeline: Configuration change event and impact

### 5. Packet Loss

Simulates network degradation causing packet loss between services.

**Type:** `packet_loss`

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `affected_services` | list[string] | Yes | - | Services experiencing packet loss |
| `packet_loss_percent` | float | Yes | - | Percentage of packets lost (0-100) |

**Example:**

```yaml
type: packet_loss
description: Network degradation causing packet loss between services

parameters:
  affected_services:
    - order-service
    - inventory-service
  packet_loss_percent: 15.0  # 15% packet loss

metadata:
  category: network
  common_causes:
    - Network hardware failure
    - Routing issues
    - Firewall misconfiguration
    - Region-to-region connectivity problems
  detection_signals:
    - Packet loss metrics spike
    - TCP retransmit increase
    - Connection timeouts
    - Request retry increase
  mitigation_strategies:
    - Route around failed network
    - Fix network hardware
    - Update firewall rules
    - Engage network team
```

**Generated Data:**
- Metrics: Packet loss percentage, TCP retransmits, connection timeouts
- Logs: Network errors, retry attempts
- Traces: Spans with network-related errors
- Timeline: Packet loss onset and resolution

### 6. Bursty Noise

Simulates intermittent resource contention from noisy neighbors.

**Type:** `bursty_noise`

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `affected_service` | string | Yes | - | Service experiencing resource contention |
| `burst_frequency_minutes` | integer | Yes | - | How often bursts occur (in minutes) |
| `burst_duration_seconds` | integer | Yes | - | How long each burst lasts (in seconds) |

**Example:**

```yaml
type: bursty_noise
description: Noisy neighbor causing intermittent resource contention

parameters:
  affected_service: user-service
  burst_frequency_minutes: 5   # Burst every 5 minutes
  burst_duration_seconds: 30   # Each burst lasts 30 seconds

metadata:
  category: resource_contention
  common_causes:
    - Batch job running on same host
    - Other tenant's workload spike
    - Scheduled tasks
    - Backup/maintenance operations
  detection_signals:
    - Intermittent CPU spikes
    - High variance in latency metrics
    - Periodic performance degradation
    - GC pressure
  mitigation_strategies:
    - Move to dedicated resources
    - Throttle batch jobs
    - Add resource limits
    - Scale out service
```

**Generated Data:**
- Metrics: CPU spikes, latency variance, memory pressure
- Logs: GC events, throttling warnings
- Traces: Periodic latency spikes
- Timeline: Burst pattern with regular intervals

## Metadata Section

The metadata section provides context and documentation for scenarios. While optional, it's recommended for better understanding and analysis.

### Metadata Fields

```yaml
metadata:
  category: <category>           # Incident category
  common_causes:                 # Typical root causes
    - <cause1>
    - <cause2>
  detection_signals:             # Observable signals
    - <signal1>
    - <signal2>
  mitigation_strategies:         # Remediation approaches
    - <strategy1>
    - <strategy2>
  tags:                          # Optional: Custom tags
    - <tag1>
    - <tag2>
  difficulty: <level>            # Optional: beginner, easy, medium, hard, expert
  estimated_mttr_minutes: <int>  # Optional: Expected time to resolve
```

### Category Values

Common categories:
- `performance`: Latency, throughput issues
- `availability`: Outages, service unavailability
- `configuration`: Config changes, drift
- `network`: Network connectivity, packet loss
- `resource_contention`: CPU, memory, disk contention
- `security`: Authentication, authorization issues

## Advanced Features

### Using Variables

You can reference environment variables in scenario files:

```yaml
type: latency_regression
description: Latency regression with configurable baseline

parameters:
  affected_service: ${SERVICE_NAME:-order-service}
  baseline_latency_ms: ${BASELINE_LATENCY:-50.0}
  degraded_latency_ms: 500.0
  error_threshold_ms: 1000.0
```

**Note:** Variable substitution is not yet implemented but planned for future releases.

### Multi-Service Scenarios

For complex scenarios affecting multiple services:

```yaml
type: dependency_outage
description: Database outage affecting entire backend stack

parameters:
  failed_service: postgres-primary
  dependent_services:
    - user-service
    - order-service
    - payment-service
    - inventory-service
    - notification-service

metadata:
  category: availability
  tags:
    - database
    - cascade
    - high-severity
  difficulty: hard
  estimated_mttr_minutes: 45
```

### Cascading Incidents

Create multi-stage incidents by chaining scenarios:

```yaml
# scenarios/cascade_example.yaml
type: cascade
description: Configuration change triggers latency, then outage

incidents:
  - type: config_drift
    delay_minutes: 0
    parameters:
      affected_service: payment-service
      config_key: connection_pool_size
      old_value: 100
      new_value: 10

  - type: latency_regression
    delay_minutes: 5
    parameters:
      affected_service: payment-service
      baseline_latency_ms: 50.0
      degraded_latency_ms: 800.0
      error_threshold_ms: 2000.0

  - type: dependency_outage
    delay_minutes: 15
    parameters:
      failed_service: payment-service
      dependent_services:
        - order-service
        - user-service
```

**Note:** Cascade type requires special handling and is documented separately.

## Best Practices

### 1. Descriptive Names

Use clear, descriptive scenario names:

```yaml
# Good
description: Redis connection pool exhaustion causing auth failures

# Less helpful
description: Auth problem
```

### 2. Realistic Parameters

Base parameters on real-world observations:

```yaml
# Realistic
parameters:
  baseline_latency_ms: 45.0
  degraded_latency_ms: 850.0  # ~19x increase

# Unrealistic
parameters:
  baseline_latency_ms: 1.0
  degraded_latency_ms: 100000.0  # 100,000x increase
```

### 3. Complete Metadata

Always include metadata for better analysis:

```yaml
metadata:
  category: performance
  common_causes:
    - Unoptimized database query
    - Missing index on users table
  detection_signals:
    - p95 latency > 500ms
    - Slow query log entries
    - Database CPU > 80%
  mitigation_strategies:
    - Add composite index on (user_id, created_at)
    - Implement query result caching
    - Optimize JOIN operations
  tags:
    - database
    - performance
    - query-optimization
```

### 4. Scenario Organization

Organize scenarios by type or use case:

```
scenarios/
├── latency/
│   ├── db_query_regression.yaml
│   ├── api_slowdown.yaml
│   └── cache_miss_storm.yaml
├── auth/
│   ├── redis_failure.yaml
│   └── rate_limiting.yaml
└── network/
    ├── cross_region_packet_loss.yaml
    └── dns_resolution_delay.yaml
```

### 5. Version Control

Keep scenarios in version control with descriptive commit messages:

```bash
git add scenarios/latency/db_query_regression.yaml
git commit -m "Add DB query regression scenario for user service"
```

## Validation

ADAPT-Data validates scenario files automatically. Common validation errors:

### Missing Required Fields

```yaml
# ERROR: Missing required field 'affected_service'
type: latency_regression
description: Latency issue

parameters:
  baseline_latency_ms: 50.0
  degraded_latency_ms: 500.0
  # Missing: affected_service, error_threshold_ms
```

**Fix:** Add all required parameters for the incident type.

### Invalid Data Types

```yaml
# ERROR: baseline_error_rate must be a float
type: auth_failure
description: Auth failures

parameters:
  affected_service: auth-service
  baseline_error_rate: "0.001"  # String instead of float
  spike_error_rate: 0.25
```

**Fix:** Use correct data types (no quotes for numbers).

### Out of Range Values

```yaml
# ERROR: Error rates must be between 0.0 and 1.0
type: auth_failure
description: Auth failures

parameters:
  affected_service: auth-service
  baseline_error_rate: 0.001
  spike_error_rate: 25  # Should be 0.25 (not 25%)
```

**Fix:** Check parameter constraints and ranges.

### Invalid YAML Syntax

```yaml
# ERROR: Invalid YAML indentation
type: latency_regression
description: Latency issue
parameters:
affected_service: order-service  # Missing indentation
  baseline_latency_ms: 50.0
```

**Fix:** Use consistent 2-space indentation.

## Testing Scenarios

Before using scenarios in production:

### 1. Validate Syntax

```bash
python -m cli.main generate \
  --scenario ./scenarios/my_scenario.yaml \
  --output /tmp/test \
  --duration 5m
```

### 2. Inspect Output

```bash
# Check generated files
ls -la /tmp/test/

# Validate dataset
python -m cli.main validate /tmp/test

# View statistics
python -m cli.main stats /tmp/test
```

### 3. Verify Anomalies

```bash
# Check for anomaly presence
grep -r "anomaly_injected.*true" /tmp/test/metrics/

# View timeline
cat /tmp/test/timelines/timeline_*.json | jq .
```

## Example Scenarios

### Simple Latency Regression

```yaml
type: latency_regression
description: Simple latency increase in API service

parameters:
  affected_service: api-gateway
  baseline_latency_ms: 100.0
  degraded_latency_ms: 800.0
  error_threshold_ms: 2000.0

metadata:
  category: performance
  difficulty: beginner
```

### Complex Auth Failure

```yaml
type: auth_failure
description: Redis cluster failure causing widespread auth issues

parameters:
  affected_service: auth-service
  baseline_error_rate: 0.0005  # 0.05% baseline
  spike_error_rate: 0.35       # 35% during incident

metadata:
  category: availability
  common_causes:
    - Redis cluster split-brain
    - Network partition in cache layer
    - Connection pool exhaustion
  detection_signals:
    - Auth error rate > 10%
    - Redis connection errors in logs
    - 401 response rate spike across all services
  mitigation_strategies:
    - Force Redis cluster re-election
    - Restart auth service instances
    - Enable fallback to database auth
    - Increase Redis connection pool limits
  tags:
    - redis
    - cache
    - authentication
    - high-severity
  difficulty: hard
  estimated_mttr_minutes: 30
```

### Network Packet Loss

```yaml
type: packet_loss
description: Cross-region network degradation

parameters:
  affected_services:
    - us-east-api
    - us-west-api
    - eu-central-api
  packet_loss_percent: 12.5

metadata:
  category: network
  common_causes:
    - Transit provider issues
    - BGP routing problems
    - DDoS attack side effects
  detection_signals:
    - Packet loss metrics > 5%
    - Cross-region latency increase
    - TCP retransmit rate spike
    - User-reported slowness from specific regions
  mitigation_strategies:
    - Failover to alternate transit provider
    - Enable region-local fallbacks
    - Contact ISP/transit provider
  tags:
    - network
    - cross-region
    - infrastructure
  difficulty: expert
```

## Related Documentation

- [Configuration Guide](configuration.md) - Global settings
- [Generation Process](generation.md) - How data is generated
- [Tutorial](tutorial.md) - Step-by-step guide
- [Architecture](architecture.md) - System design
