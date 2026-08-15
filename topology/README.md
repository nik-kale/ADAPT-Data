# Topology Definitions

Custom service topologies for incident generation. Point a run at one of these
instead of the built-in default microservices graph, or drop in a YAML file
describing your own architecture.

## Usage

```bash
# Use a bundled topology by name
python -m cli.main generate --scenario latency_regression \
  --topology ecommerce --output ./out

# Or pass a path to your own file
python -m cli.main generate --scenario latency_regression \
  --topology ./my-topology.yaml --output ./out
```

A scenario can also pin its own topology, which applies whenever `--topology`
is not given:

```yaml
type: latency_regression
description: Checkout latency regression
topology: ecommerce
parameters:
  affected_service: checkout-service
```

## Bundled topologies

| Name | Services | Shape |
|------|----------|-------|
| `ecommerce` | 15 | Storefront, checkout, payments, fulfilment |
| `saas-multitenant` | 12 | Control plane, tenant routing, async workers, analytics |

## File format

```yaml
name: my-topology
description: What this models
version: "1.0"

services:
  - name: api-server         # required, unique
    type: api                # required, see valid types below
    instances: 4             # optional, integer >= 1, default 1
    region: us-east-1        # optional
    metadata:                # optional
      version: "1.0.0"
      tier: critical         # critical | high | medium | low
      sla_target: 99.9
    dependencies:            # optional, nested edge form
      - target: postgres-primary
        type: database
        critical: true

  - name: postgres-primary
    type: database
    instances: 1

# Optional top-level edge form. Merged with any nested dependencies.
dependencies:
  - from: api-server
    to: postgres-primary
    type: database
    critical: true
```

Both dependency forms are accepted and merged, so use whichever reads better
for your architecture.

**Valid service types**: `api`, `database`, `cache`, `queue`, `frontend`,
`worker`, `gateway`, `auth`, `storage`

**Valid dependency types**: `http`, `grpc`, `database`, `cache`, `queue`,
`storage`

## Validation

Topology files are validated on load. Loading fails with a clear error when:

- A service is missing `name`, or two services share one
- A service `type` is outside the valid set
- `instances` is not an integer >= 1
- A dependency points at a service that is not defined
- A dependency `type` is outside the valid set

Check a file without generating a full dataset:

```bash
python -c "
from pathlib import Path
from generator.core.topology import load_topology_file
services, deps = load_topology_file(Path('topology/ecommerce.yaml'))
print(f'{len(services)} services, {len(deps)} dependencies')
"
```
