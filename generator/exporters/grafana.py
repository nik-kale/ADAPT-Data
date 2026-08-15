"""Grafana dashboard generation.

Builds Grafana dashboard JSON for each incident type, wired to the metric names
the generators actually emit. Dashboards target a Prometheus datasource, which
pairs with ``adapt-data serve`` or an export scraped into Prometheus.
"""

import json
from pathlib import Path
from typing import Any, NamedTuple

from generator.core.logging_config import get_logger

logger = get_logger(__name__)

# Grafana dashboard JSON schema version. 39 corresponds to Grafana 10.x, which
# newer versions still import cleanly.
SCHEMA_VERSION = 39

# Grafana unit identifiers.
UNIT_MS = "ms"
UNIT_PERCENT = "percent"
UNIT_BYTES = "bytes"
UNIT_SHORT = "short"
UNIT_OPS = "ops"


class Panel(NamedTuple):
    """A single dashboard panel.

    Attributes:
        title: Panel heading
        metrics: Metric names to plot, one series each
        unit: Grafana unit identifier for the y-axis
        description: Explains what the panel shows during this incident
    """

    title: str
    metrics: tuple[str, ...]
    unit: str
    description: str = ""


class DashboardSpec(NamedTuple):
    """Dashboard definition for one incident type.

    Attributes:
        slug: Filename stem and dashboard UID suffix
        title: Human-readable dashboard title
        description: What the dashboard is for
        panels: Panels to render, in display order
    """

    slug: str
    title: str
    description: str
    panels: tuple[Panel, ...]


DASHBOARD_SPECS: tuple[DashboardSpec, ...] = (
    DashboardSpec(
        slug="latency_regression",
        title="ADAPT · Latency Regression",
        description="Request latency percentiles and the database time behind them",
        panels=(
            Panel(
                "Request Duration Percentiles",
                (
                    "http_request_duration_p50",
                    "http_request_duration_p95",
                    "http_request_duration_p99",
                ),
                UNIT_MS,
                "p99 separating from p50 points at a tail-latency regression",
            ),
            Panel(
                "Database Query Duration",
                ("db_query_duration_ms",),
                UNIT_MS,
                "Query time tracking request latency implicates the data layer",
            ),
            Panel("Request Rate", ("http_requests_total",), UNIT_OPS),
            Panel("Error Rate", ("http_error_rate",), UNIT_PERCENT),
        ),
    ),
    DashboardSpec(
        slug="auth_failure",
        title="ADAPT · Auth Failure",
        description="Authentication error rates and the cache behind them",
        panels=(
            Panel(
                "Auth Error Rate",
                ("auth_error_rate",),
                UNIT_PERCENT,
                "The primary signal: share of auth attempts failing",
            ),
            Panel("Auth Request Volume", ("auth_requests_total",), UNIT_OPS),
            Panel(
                "Redis Connections and Errors",
                ("redis_active_connections", "redis_connection_errors"),
                UNIT_SHORT,
                "Connection errors rising alongside auth failures implicates the cache",
            ),
            Panel("Connection Pool", ("connection_pool_active",), UNIT_SHORT),
        ),
    ),
    DashboardSpec(
        slug="dependency_outage",
        title="ADAPT · Dependency Outage",
        description="Availability of a failed dependency and its blast radius",
        panels=(
            Panel(
                "Service Availability",
                ("service_available",),
                UNIT_SHORT,
                "Drops to 0 while the dependency is down",
            ),
            Panel("Error Rate", ("http_error_rate",), UNIT_PERCENT),
            Panel("Request Duration (p95)", ("http_request_duration_p95",), UNIT_MS),
            Panel("Request Rate", ("http_requests_total",), UNIT_OPS),
        ),
    ),
    DashboardSpec(
        slug="config_drift",
        title="ADAPT · Config Drift",
        description="Resource pool saturation following a configuration change",
        panels=(
            Panel(
                "Transaction Pool Utilization",
                ("transaction_pool_utilization", "transaction_pool_size"),
                UNIT_PERCENT,
                "Saturation after an undersized pool is applied",
            ),
            Panel(
                "Queue Depth",
                ("transaction_queue_depth",),
                UNIT_SHORT,
                "Work backing up behind the saturated pool",
            ),
            Panel("Request Duration (p95)", ("http_request_duration_p95",), UNIT_MS),
            Panel("Error Rate", ("http_error_rate",), UNIT_PERCENT),
        ),
    ),
    DashboardSpec(
        slug="packet_loss",
        title="ADAPT · Packet Loss",
        description="Network degradation and the timeouts it causes",
        panels=(
            Panel(
                "Packet Loss",
                ("network_packet_loss_percent",),
                UNIT_PERCENT,
                "The primary signal for network-layer degradation",
            ),
            Panel("TCP Retransmit Rate", ("network_retransmit_rate",), UNIT_SHORT),
            Panel("Request Timeout Rate", ("http_request_timeout_rate",), UNIT_PERCENT),
            Panel("Request Duration (p95)", ("http_request_duration_p95",), UNIT_MS),
        ),
    ),
    DashboardSpec(
        slug="bursty_noise",
        title="ADAPT · Bursty Noise",
        description="Periodic resource contention from a noisy neighbour",
        panels=(
            Panel(
                "CPU Usage",
                ("cpu_usage_percent",),
                UNIT_PERCENT,
                "Regular spikes rather than a sustained shift",
            ),
            Panel("Memory Usage", ("memory_usage_mb",), UNIT_SHORT),
            Panel(
                "Request Duration Percentiles",
                (
                    "http_request_duration_p50",
                    "http_request_duration_p95",
                    "http_request_duration_p99",
                ),
                UNIT_MS,
                "Latency variance widens during each burst",
            ),
        ),
    ),
    DashboardSpec(
        slug="memory_leak",
        title="ADAPT · Memory Leak",
        description="Heap growth, GC degradation and the OOM kill that follows",
        panels=(
            Panel(
                "Memory Utilization",
                ("process_memory_utilization_percent",),
                UNIT_PERCENT,
                "A steady climb with no plateau is the signature of a leak",
            ),
            Panel("Process Memory", ("process_memory_usage_bytes",), UNIT_BYTES),
            Panel(
                "GC Pause Duration",
                ("gc_pause_duration_ms",),
                UNIT_MS,
                "Pauses lengthen as the collector fights for headroom",
            ),
            Panel("GC Collection Frequency", ("gc_collections_per_minute",), UNIT_SHORT),
            Panel(
                "Throughput",
                ("http_requests_per_second",),
                UNIT_OPS,
                "Falls as GC takes an increasing share of CPU",
            ),
            Panel(
                "Container Restarts",
                ("container_restarts_total",),
                UNIT_SHORT,
                "A step here marks the OOM kill",
            ),
        ),
    ),
    DashboardSpec(
        slug="deadlock",
        title="ADAPT · Database Deadlock",
        description="Lock contention, rollbacks and pool pressure",
        panels=(
            Panel(
                "Deadlock Rate",
                ("db_deadlocks_per_minute",),
                UNIT_SHORT,
                "The defining signal: the detector aborting victim transactions",
            ),
            Panel(
                "Blocked Sessions",
                ("db_blocked_sessions",),
                UNIT_SHORT,
                "Sessions parked waiting on a lock",
            ),
            Panel("Lock Wait Duration", ("db_lock_wait_duration_ms",), UNIT_MS),
            Panel(
                "Transaction Rollbacks",
                ("transaction_rollbacks_per_minute",),
                UNIT_SHORT,
                "Application-side view of the aborted transactions",
            ),
            Panel(
                "Connection Pool Utilization",
                ("db_connection_pool_utilization_percent",),
                UNIT_PERCENT,
                "Blocked sessions hold connections, squeezing the pool",
            ),
            Panel("Request Error Rate", ("http_request_errors_percent",), UNIT_PERCENT),
        ),
    ),
)

# Cross-incident view, useful when the incident type is not known up front.
OVERVIEW_SPEC = DashboardSpec(
    slug="incident_overview",
    title="ADAPT · Incident Overview",
    description="Golden signals across every ADAPT-Data incident type",
    panels=(
        Panel(
            "Latency (p95)",
            ("http_request_duration_p95",),
            UNIT_MS,
            "Golden signal: latency",
        ),
        Panel(
            "Error Rates",
            ("http_error_rate", "auth_error_rate", "http_request_errors_percent"),
            UNIT_PERCENT,
            "Golden signal: errors",
        ),
        Panel(
            "Traffic",
            ("http_requests_total", "http_requests_per_second"),
            UNIT_OPS,
            "Golden signal: traffic",
        ),
        Panel(
            "Saturation",
            (
                "cpu_usage_percent",
                "process_memory_utilization_percent",
                "db_connection_pool_utilization_percent",
            ),
            UNIT_PERCENT,
            "Golden signal: saturation",
        ),
        Panel(
            "Availability",
            ("service_available",),
            UNIT_SHORT,
            "Hard failure signal",
        ),
    ),
)


class GrafanaDashboardBuilder:
    """Builds Grafana dashboard JSON from :class:`DashboardSpec` definitions."""

    def __init__(self, datasource_uid: str = "adapt-prometheus") -> None:
        """Initialize the builder.

        Args:
            datasource_uid: UID of the Prometheus datasource the panels query.
                Matches the UID provisioned in dashboards/docker-compose.yml.
        """
        self.datasource_uid = datasource_uid

    def _datasource(self) -> dict[str, str]:
        """Return the datasource reference used by every panel and template."""
        return {"type": "prometheus", "uid": self.datasource_uid}

    def _build_panel(self, panel: Panel, panel_id: int, grid_y: int) -> dict[str, Any]:
        """Render one panel.

        Args:
            panel: Panel definition
            panel_id: Unique numeric ID within the dashboard
            grid_y: Row position on the dashboard grid

        Returns:
            Grafana panel object
        """
        targets = [
            {
                "datasource": self._datasource(),
                # $service is supplied by the dashboard template variable.
                "expr": f'{metric}{{service=~"$service"}}',
                "legendFormat": f"{{{{service}}}} · {{{{host}}}}",
                "refId": chr(ord("A") + index),
            }
            for index, metric in enumerate(panel.metrics)
        ]

        return {
            "id": panel_id,
            "type": "timeseries",
            "title": panel.title,
            "description": panel.description,
            "datasource": self._datasource(),
            "gridPos": {"h": 8, "w": 12, "x": 0 if panel_id % 2 else 12, "y": grid_y},
            "targets": targets,
            "fieldConfig": {
                "defaults": {
                    "unit": panel.unit,
                    "custom": {
                        "drawStyle": "line",
                        "lineWidth": 2,
                        "fillOpacity": 8,
                        "showPoints": "never",
                    },
                },
                "overrides": [],
            },
            "options": {
                "legend": {"displayMode": "list", "placement": "bottom", "showLegend": True},
                "tooltip": {"mode": "multi", "sort": "desc"},
            },
        }

    def build(self, spec: DashboardSpec) -> dict[str, Any]:
        """Render a full dashboard.

        Args:
            spec: Dashboard definition

        Returns:
            Grafana dashboard object, ready to import
        """
        panels = [
            self._build_panel(panel, panel_id=index + 1, grid_y=(index // 2) * 8)
            for index, panel in enumerate(spec.panels)
        ]

        return {
            "uid": f"adapt-{spec.slug.replace('_', '-')}",
            "title": spec.title,
            "description": spec.description,
            "tags": ["adapt-data", "incident", spec.slug],
            "schemaVersion": SCHEMA_VERSION,
            "version": 1,
            "editable": True,
            "refresh": "10s",
            "time": {"from": "now-3h", "to": "now"},
            "timezone": "utc",
            "templating": {
                "list": [
                    {
                        "name": "service",
                        "label": "Service",
                        "type": "query",
                        "datasource": self._datasource(),
                        "query": {"query": "label_values(service)", "refId": "adapt-services"},
                        "refresh": 1,
                        "includeAll": True,
                        "multi": True,
                        "current": {"text": "All", "value": "$__all"},
                    }
                ]
            },
            "annotations": {
                "list": [
                    {
                        "name": "Incident window",
                        "datasource": self._datasource(),
                        "enable": True,
                        "iconColor": "red",
                        "expr": 'ALERTS{alertstate="firing"}',
                    }
                ]
            },
            "panels": panels,
        }

    def build_all(self) -> dict[str, dict[str, Any]]:
        """Render every bundled dashboard.

        Returns:
            Mapping of slug to dashboard object
        """
        specs = (*DASHBOARD_SPECS, OVERVIEW_SPEC)
        return {spec.slug: self.build(spec) for spec in specs}

    def export(self, output_dir: Path) -> list[Path]:
        """Write every dashboard to a directory as JSON.

        Args:
            output_dir: Directory to write dashboards into. Created if absent.

        Returns:
            Paths written, in slug order
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        written: list[Path] = []
        for slug, dashboard in sorted(self.build_all().items()):
            target = output_dir / f"{slug}.json"
            with open(target, "w") as f:
                json.dump(dashboard, f, indent=2)
                f.write("\n")
            written.append(target)

        logger.info(f"Exported {len(written)} Grafana dashboards to {output_dir}")
        return written
