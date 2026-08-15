# Grafana Dashboards

Pre-built Grafana dashboards for every ADAPT-Data incident type, plus a
cross-incident overview. Panels are wired to the metric names the generators
actually emit, so a generated dataset fills them in without further setup.

## Quick start

```bash
# 1. Generate an incident
python -m cli.main generate --scenario memory_leak --output ./out --duration 1h

# 2. Replay it as Prometheus metrics (60x speed so an hour takes a minute)
python -m cli.main serve ./out --port 9091 --replay-speed 60

# 3. In another terminal, bring up Grafana + Prometheus
docker compose -f dashboards/docker-compose.yml up

# 4. Open http://localhost:3000 — dashboards are pre-provisioned under the
#    "ADAPT-Data" folder. No login required.
```

Prometheus scrapes the replay server on the host, so step 2 must be running for
panels to show data.

## Dashboards

| Dashboard | UID | Key panels |
|-----------|-----|------------|
| Incident Overview | `adapt-incident-overview` | The four golden signals across all incident types |
| Latency Regression | `adapt-latency-regression` | p50/p95/p99 duration, DB query time |
| Auth Failure | `adapt-auth-failure` | Auth error rate, Redis connections and errors |
| Dependency Outage | `adapt-dependency-outage` | Service availability, error rate, blast radius |
| Config Drift | `adapt-config-drift` | Pool utilization, queue depth |
| Packet Loss | `adapt-packet-loss` | Loss percent, TCP retransmits, timeouts |
| Bursty Noise | `adapt-bursty-noise` | CPU spikes, latency variance |
| Memory Leak | `adapt-memory-leak` | Heap utilization, GC pause and frequency, restarts |
| Database Deadlock | `adapt-deadlock` | Deadlock rate, blocked sessions, rollbacks |

Every dashboard carries a `service` template variable, so a single dashboard
covers all services in the topology or can be narrowed to one.

## Regenerating

Dashboard JSON is generated from specs in `generator/exporters/grafana.py`:

```bash
# Rewrite dashboards/grafana/*.json
python -m cli.main dashboards

# Target a datasource UID that already exists in your Grafana
python -m cli.main dashboards --datasource-uid my-prometheus --output /tmp/dash
```

Edit the `DASHBOARD_SPECS` table in `generator/exporters/grafana.py` to change
panels, then re-run the command — the JSON files are build output, not the
source of truth.

## Importing into an existing Grafana

The files under `dashboards/grafana/` are standard Grafana dashboard JSON.
Import them through **Dashboards → New → Import**, or via the API:

```bash
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $GRAFANA_TOKEN" \
  -d "{\"dashboard\": $(cat dashboards/grafana/memory_leak.json), \"overwrite\": true}"
```

Export with `--datasource-uid` set to your own Prometheus UID first, otherwise
the panels point at a datasource that does not exist in your instance.
