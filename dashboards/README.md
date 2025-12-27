# ADAPT-Data Grafana Dashboards

Pre-built Grafana dashboards for visualizing ADAPT-Data generated incidents. These dashboards provide instant observability for all incident types, making it easy to demo, validate, and analyze generated telemetry data.

## Quick Start

### 1. Generate Incident Data

```bash
# Generate a latency regression incident
python -m cli.main generate \
  --scenario latency_regression \
  --output ./output \
  --duration 1h \
  --severity SEV2

# Export to Prometheus format
python -m cli.main export \
  --format prometheus \
  --output ./output/metrics.txt \
  ./output
```

### 2. Start Grafana + Prometheus

```bash
cd dashboards/
docker-compose -f docker-compose.grafana.yml up -d
```

### 3. Serve Metrics to Prometheus

```bash
# In a separate terminal
python -m cli.main serve ./output --port 8000
```

### 4. Access Grafana

Open [http://localhost:3000](http://localhost:3000)

**Default credentials:**
- Username: `admin`
- Password: `adapt-data`

The dashboards will be automatically loaded in the "ADAPT-Data" folder.

## Available Dashboards

### Incident Overview
**File:** `grafana/incident_overview.json`

Master dashboard showing cross-service metrics:
- Service latency (all services)
- Error rates across services
- Service health status
- CPU and memory usage trends

**Use for:** High-level incident detection and comparison

### Latency Regression
**File:** `grafana/latency_regression.json`

Focuses on performance degradation signals:
- HTTP request latency percentiles (p50, p95, p99)
- Database CPU usage
- Database query duration
- Slow query rate

**Use for:** Diagnosing performance degradation incidents

### Authentication Failures
**File:** `grafana/auth_failure.json`

Tracks authentication system health:
- Auth error rate
- Cache connection pool status
- Cache connection errors
- Cache hit rate

**Use for:** Debugging auth service and cache issues

## Dashboard Features

### Automatic Data Source Configuration
Dashboards are pre-configured to use the Prometheus datasource. No manual configuration needed.

### Real-Time Updates
Dashboards refresh every 5 seconds to show live incident progression.

### Variable Support
Many dashboards support service filtering via dropdown variables.

### Annotations
Dashboards support Grafana annotations for marking incident start/end times.

## Architecture

```
dashboards/
├── grafana/
│   ├── incident_overview.json          # Master dashboard
│   ├── latency_regression.json         # Latency incident dashboard
│   ├── auth_failure.json               # Auth failure dashboard
│   └── provisioning/                   # Auto-provisioning configs
│       ├── datasources/
│       │   └── prometheus.yml          # Prometheus datasource
│       └── dashboards/
│           └── adapt-data.yml          # Dashboard loader
├── docker-compose.grafana.yml          # Docker Compose setup
├── prometheus.yml                      # Prometheus scrape config
└── README.md                           # This file
```

## Customization

### Adding Custom Panels

1. Open dashboard in Grafana UI
2. Click "Add panel"
3. Configure query using available metrics
4. Save dashboard
5. Export JSON via Settings → JSON Model
6. Save to `grafana/` directory

### Modifying Metric Queries

Edit the dashboard JSON files directly or use Grafana's UI:

```json
{
  "targets": [
    {
      "expr": "your_prometheus_query_here",
      "legendFormat": "{{label}}",
      "refId": "A"
    }
  ]
}
```

### Changing Refresh Rate

Update the `refresh` field in dashboard JSON:

```json
{
  "refresh": "5s"  // Options: "5s", "10s", "30s", "1m", etc.
}
```

## Troubleshooting

### Dashboards Not Loading

**Check Grafana logs:**
```bash
docker logs adapt-grafana
```

**Verify provisioning directory:**
```bash
docker exec adapt-grafana ls /etc/grafana/provisioning/dashboards
```

### No Data Showing

**Verify Prometheus is scraping:**
1. Open [http://localhost:9090/targets](http://localhost:9090/targets)
2. Ensure `adapt-data-metrics` target is UP
3. Check that `python -m cli.main serve` is running

**Test metric queries:**
```bash
# Query Prometheus directly
curl 'http://localhost:9090/api/v1/query?query=http_request_duration_p95'
```

### Connection Refused Errors

**If using Docker Desktop on Mac/Windows:**
- Change `host.docker.internal` to actual host IP
- Update `prometheus.yml` scrape target

**If running on Linux:**
- Use `--network host` in docker-compose
- Or add explicit IP address

## Integration with ADAPT-RCA

Generated dashboards can be exported and imported into ADAPT-RCA visualization:

```bash
# Export dashboard state
curl -u admin:adapt-data \
  http://localhost:3000/api/dashboards/uid/adapt-data-latency \
  > dashboard_snapshot.json
```

## Advanced Usage

### Importing Dashboards Manually

If auto-provisioning fails, import manually:

1. Open Grafana → Dashboards → Import
2. Upload JSON file from `grafana/` directory
3. Select "prometheus" as datasource
4. Click Import

### Creating Dashboard Snapshots

Share dashboards without requiring Grafana access:

1. Open dashboard
2. Click Share → Snapshot
3. Set expiration time
4. Publish and share URL

### Alerting

Add alert rules to panels:

1. Edit panel
2. Switch to Alert tab
3. Configure conditions
4. Set notification channel

### Exporting Metrics to Other Tools

Prometheus metrics can be queried via API:

```bash
# Export current metrics
curl http://localhost:9090/api/v1/query?query=http_request_duration_p95 \
  | jq '.data.result'
```

## Development

### Testing Dashboard Changes

1. Modify JSON file
2. Restart Grafana container:
   ```bash
   docker-compose -f docker-compose.grafana.yml restart grafana
   ```
3. Dashboard will reload automatically

### Validating JSON

```bash
# Validate JSON syntax
jq empty grafana/latency_regression.json
```

## Additional Resources

- [Grafana Dashboard Documentation](https://grafana.com/docs/grafana/latest/dashboards/)
- [Prometheus Query Language](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [ADAPT-Data Metrics Reference](../docs/api_reference.md)

## License

Same as ADAPT-Data project license.

