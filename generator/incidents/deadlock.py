"""Database deadlock incident generator."""

import random
from datetime import datetime, timedelta
from typing import Any

from generator.core.base import BaseGenerator, IncidentContext
from generator.core.distributions import (
    UniformDistribution,
    LogNormalDistribution
)
from generator.core.patterns import (
    create_business_hours_pattern,
    NoisePattern
)
from generator.core.logging_config import get_logger
from generator.core.timeline import TimelineGenerator
from generator.core.utils import timestamp_to_iso, generate_uuid

logger = get_logger(__name__)

# Distributions for realistic data generation
_TRANSACTION_ID_DIST = UniformDistribution(min_val=100000, max_val=999999)
_LOCK_WAIT_DIST = LogNormalDistribution(mu=3, sigma=1)  # ~10-100ms


class DeadlockGenerator(BaseGenerator):
    """Generates a database deadlock incident scenario.

    Simulates multi-table deadlock scenarios with cyclic wait patterns,
    including lock wait timeouts, transaction rollbacks, and connection
    pool exhaustion.
    """

    def __init__(
        self,
        context: IncidentContext,
        affected_service: str = "order-service",
        database_service: str = "postgres-primary",
        deadlock_frequency: float = 0.1,
        affected_tables: list[str] = None
    ) -> None:
        """Initialize deadlock generator.

        Args:
            context: Incident context
            affected_service: Service experiencing deadlocks
            database_service: Database service name
            deadlock_frequency: Deadlock occurrence rate (0.0-1.0)
            affected_tables: List of tables involved in deadlocks
        """
        super().__init__(context)
        self.affected_service = affected_service
        self.database_service = database_service
        self.deadlock_frequency = deadlock_frequency
        self.affected_tables = affected_tables or ["orders", "payments", "inventory"]

        # Apply difficulty configuration if available
        if hasattr(context, 'difficulty_config') and context.difficulty_config:
            diff_config = context.difficulty_config
            noise_level = diff_config.noise_level

            # Adjust complexity based on difficulty
            if diff_config.level.value == 'beginner':
                # Higher deadlock frequency for easier detection
                self.deadlock_frequency *= 1.5
            elif diff_config.level.value == 'expert':
                # Lower frequency, harder to detect
                self.deadlock_frequency *= 0.6

            self.log_volume_multiplier = diff_config.log_volume_multiplier
            self.metric_density_multiplier = diff_config.metric_density / 3.0

            logger.info(f"Applied {diff_config.level.value} difficulty adjustments: "
                       f"deadlock_frequency={self.deadlock_frequency:.2f}, "
                       f"noise_level={noise_level:.2f}")
        else:
            noise_level = 0.05
            self.log_volume_multiplier = 1.0
            self.metric_density_multiplier = 1.0

        # Time-series patterns
        self.request_rate_pattern = create_business_hours_pattern()
        self.noise = NoisePattern(noise_level=noise_level)

        # Update context
        context.affected_services = [affected_service, database_service]
        context.root_cause = (
            f"Database deadlock in {database_service} involving tables: "
            f"{', '.join(self.affected_tables)}"
        )

    def generate(self) -> dict[str, Any]:
        """Generate complete incident dataset.

        Returns:
            Summary of generated data
        """
        logger.info(f"Generating database deadlock incident for {self.affected_service}...")
        logger.info(f"  Database: {self.database_service}")
        logger.info(f"  Deadlock frequency: {self.deadlock_frequency:.2f}")
        logger.info(f"  Affected tables: {', '.join(self.affected_tables)}")

        # Generate components
        logs = self._generate_logs()
        metrics = self._generate_metrics()
        traces = self._generate_traces()
        timeline = self._generate_timeline()

        logger.info(f"  Generated {len(logs)} log entries")
        logger.info(f"  Generated {len(metrics)} metric points")
        logger.info(f"  Generated {len(traces)} traces")
        logger.info(f"  Generated timeline with {len(timeline['events'])} events")

        # Save files
        self.save_jsonl(logs, f"logs_{self.context.incident_id}.jsonl", "logs")
        self.save_jsonl(metrics, f"metrics_{self.context.incident_id}.jsonl", "metrics")
        self.save_jsonl(traces, f"traces_{self.context.incident_id}.jsonl", "traces")
        self.save_json(timeline, f"timeline_{self.context.incident_id}.json", "timelines")

        return {
            "incident_id": self.context.incident_id,
            "incident_type": "database_deadlock",
            "affected_service": self.affected_service,
            "database_service": self.database_service,
            "log_count": len(logs),
            "metric_count": len(metrics),
            "trace_count": len(traces)
        }

    def _generate_logs(self) -> list[dict[str, Any]]:
        """Generate log entries."""
        logs = []
        service_hosts = self._get_service_hosts(self.affected_service)
        db_hosts = self._get_service_hosts(self.database_service)

        # Log sampling rate based on difficulty
        log_sample_rate = 0.05 * self.log_volume_multiplier

        for current_time in self._iterate_time_window(step=timedelta(seconds=10)):
            is_during_incident = self.context.is_during_incident(current_time)

            # Application service logs
            for host in service_hosts:
                # Baseline application logs
                if self._should_generate_log(log_sample_rate):
                    logs.append({
                        "timestamp": timestamp_to_iso(current_time),
                        "level": "INFO",
                        "service": self.affected_service,
                        "host": host,
                        "message": "Processing order transaction",
                        "transaction_id": int(_TRANSACTION_ID_DIST.sample())
                    })

                # Deadlock-related logs during incident
                if is_during_incident and self._should_generate_log(self.deadlock_frequency):
                    # Lock wait timeout
                    transaction_id = int(_TRANSACTION_ID_DIST.sample())
                    table1, table2 = random.sample(self.affected_tables, 2)
                    lock_wait_ms = _LOCK_WAIT_DIST.sample() * 100  # 100-1000ms

                    logs.append({
                        "timestamp": timestamp_to_iso(current_time),
                        "level": "ERROR",
                        "service": self.affected_service,
                        "host": host,
                        "message": f"Lock wait timeout exceeded: could not obtain lock on {table1}",
                        "error_type": "LockWaitTimeout",
                        "transaction_id": transaction_id,
                        "table": table1,
                        "lock_wait_ms": round(lock_wait_ms, 2)
                    })

                    # Transaction rollback
                    logs.append({
                        "timestamp": timestamp_to_iso(current_time + timedelta(milliseconds=100)),
                        "level": "WARN",
                        "service": self.affected_service,
                        "host": host,
                        "message": f"Transaction {transaction_id} rolled back due to deadlock",
                        "transaction_id": transaction_id,
                        "rollback_reason": "deadlock_detected"
                    })

                # Connection pool warnings during incident
                if is_during_incident and self._should_generate_log(0.3):
                    logs.append({
                        "timestamp": timestamp_to_iso(current_time),
                        "level": "WARN",
                        "service": self.affected_service,
                        "host": host,
                        "message": "Connection pool nearing exhaustion - active connections at 95%",
                        "active_connections": 19,
                        "max_connections": 20,
                        "pool_utilization": 0.95
                    })

            # Database logs
            for db_host in db_hosts:
                # PostgreSQL-style deadlock detection logs
                if is_during_incident and self._should_generate_log(self.deadlock_frequency):
                    table1, table2 = random.sample(self.affected_tables, 2)
                    txn1_id = int(_TRANSACTION_ID_DIST.sample())
                    txn2_id = int(_TRANSACTION_ID_DIST.sample())

                    logs.append({
                        "timestamp": timestamp_to_iso(current_time),
                        "level": "ERROR",
                        "service": self.database_service,
                        "host": db_host,
                        "message": (
                            f"DEADLOCK DETECTED: Process {txn1_id} waits for ShareLock on "
                            f"transaction {txn2_id}; blocked by process {txn2_id}. "
                            f"Process {txn2_id} waits for ShareLock on transaction {txn1_id}; "
                            f"blocked by process {txn1_id}."
                        ),
                        "error_type": "DeadlockDetected",
                        "transaction_1": txn1_id,
                        "transaction_2": txn2_id,
                        "table_1": table1,
                        "table_2": table2,
                        "lock_type": "ShareLock"
                    })

                # pg_stat_activity - blocked queries
                if is_during_incident and self._should_generate_log(0.2):
                    logs.append({
                        "timestamp": timestamp_to_iso(current_time),
                        "level": "WARN",
                        "service": self.database_service,
                        "host": db_host,
                        "message": "Query waiting for lock acquisition",
                        "query": f"UPDATE {random.choice(self.affected_tables)} SET ...",
                        "wait_event": "transactionid",
                        "state": "active",
                        "backend_type": "client backend"
                    })

        return sorted(logs, key=lambda x: x["timestamp"])

    def _generate_metrics(self) -> list[dict[str, Any]]:
        """Generate metric data points."""
        metrics = []
        service_hosts = self._get_service_hosts(self.affected_service)
        db_hosts = self._get_service_hosts(self.database_service)

        # Metric sampling interval based on difficulty
        metric_step = timedelta(seconds=60 / self.metric_density_multiplier)

        for current_time in self._iterate_time_window(step=metric_step):
            is_during_incident = self.context.is_during_incident(current_time)
            incident_intensity = self.context.get_incident_progress(current_time) if is_during_incident else 0.0

            # Application service metrics
            for host in service_hosts:
                # Transaction rollback rate (increases during deadlocks)
                baseline_rollbacks = 0.5  # 0.5/min baseline
                rollback_rate = baseline_rollbacks + (incident_intensity * self.deadlock_frequency * 50)
                metrics.append({
                    "timestamp": timestamp_to_iso(current_time),
                    "metric_name": "transaction_rollback_rate",
                    "value": self.noise.apply(rollback_rate),
                    "service": self.affected_service,
                    "host": host,
                    "metric_type": "gauge",
                    "anomaly_injected": is_during_incident
                })

                # Lock wait time (ms)
                baseline_lock_wait = 10
                lock_wait_ms = baseline_lock_wait + (incident_intensity * 500)
                metrics.append({
                    "timestamp": timestamp_to_iso(current_time),
                    "metric_name": "lock_wait_duration_ms",
                    "value": self.noise.apply(lock_wait_ms),
                    "service": self.affected_service,
                    "host": host,
                    "metric_type": "gauge",
                    "anomaly_injected": is_during_incident and lock_wait_ms > 100
                })

                # Connection pool utilization
                baseline_pool = 0.4  # 40% baseline
                pool_utilization = baseline_pool + (incident_intensity * 0.5)
                metrics.append({
                    "timestamp": timestamp_to_iso(current_time),
                    "metric_name": "connection_pool_utilization",
                    "value": min(1.0, self.noise.apply(pool_utilization)),
                    "service": self.affected_service,
                    "host": host,
                    "metric_type": "gauge",
                    "anomaly_injected": pool_utilization > 0.8
                })

            # Database metrics
            for db_host in db_hosts:
                # Deadlock count
                deadlock_count = 0 if not is_during_incident else int(incident_intensity * 10)
                metrics.append({
                    "timestamp": timestamp_to_iso(current_time),
                    "metric_name": "deadlock_count",
                    "value": deadlock_count,
                    "service": self.database_service,
                    "host": db_host,
                    "metric_type": "counter",
                    "anomaly_injected": deadlock_count > 0
                })

                # Lock conflicts
                baseline_conflicts = 5
                lock_conflicts = baseline_conflicts + (incident_intensity * 100)
                metrics.append({
                    "timestamp": timestamp_to_iso(current_time),
                    "metric_name": "lock_conflicts",
                    "value": int(self.noise.apply(lock_conflicts)),
                    "service": self.database_service,
                    "host": db_host,
                    "metric_type": "gauge",
                    "anomaly_injected": lock_conflicts > 20
                })

                # Active connections
                baseline_connections = 15
                active_connections = baseline_connections + (incident_intensity * 5)
                metrics.append({
                    "timestamp": timestamp_to_iso(current_time),
                    "metric_name": "active_connections",
                    "value": int(min(20, self.noise.apply(active_connections))),
                    "service": self.database_service,
                    "host": db_host,
                    "metric_type": "gauge",
                    "anomaly_injected": active_connections > 18
                })

        return sorted(metrics, key=lambda x: x["timestamp"])

    def _generate_traces(self) -> list[dict[str, Any]]:
        """Generate distributed trace data."""
        traces = []
        service_hosts = self._get_service_hosts(self.affected_service)

        # Generate trace every 5 minutes
        for current_time in self._iterate_time_window(step=timedelta(minutes=5)):
            is_during_incident = self.context.is_during_incident(current_time)
            incident_intensity = self.context.get_incident_progress(current_time) if is_during_incident else 0.0

            host = random.choice(service_hosts)

            # Base duration
            base_duration_ms = 50
            # Add lock wait time during incident
            lock_wait = incident_intensity * 500
            duration_ms = base_duration_ms + lock_wait

            # Check if this trace experiences deadlock
            has_deadlock = is_during_incident and random.random() < self.deadlock_frequency

            trace = {
                "trace_id": generate_uuid(),
                "timestamp": timestamp_to_iso(current_time),
                "duration_ms": duration_ms,
                "service": self.affected_service,
                "error": has_deadlock,
                "spans": [
                    {
                        "span_id": generate_uuid(),
                        "service": self.affected_service,
                        "operation": "update_order",
                        "start_time": timestamp_to_iso(current_time),
                        "duration_ms": duration_ms,
                        "host": host,
                        "error": has_deadlock,
                        "tags": {
                            "http.method": "POST",
                            "http.status_code": 500 if has_deadlock else 200,
                            "db.statement": f"UPDATE {random.choice(self.affected_tables)} SET ..."
                        }
                    }
                ]
            }

            if has_deadlock:
                trace["spans"][0]["tags"]["error.type"] = "DeadlockException"
                trace["spans"][0]["tags"]["error.message"] = "Lock wait timeout exceeded"

            traces.append(trace)

        return sorted(traces, key=lambda x: x["timestamp"])

    def _generate_timeline(self) -> dict[str, Any]:
        """Generate incident timeline."""
        timeline_gen = TimelineGenerator(self.context)

        # Add deadlock detection event
        detection_time = self.context.start_time + timedelta(minutes=5)
        timeline_gen.add_event(
            timestamp=detection_time,
            event_type="detection",
            description=f"Increased deadlock rate detected in {self.database_service}",
            severity="warning"
        )

        # Add peak deadlock event
        peak_time = self.context.start_time + (self.context.duration / 2)
        timeline_gen.add_event(
            timestamp=peak_time,
            event_type="escalation",
            description=(
                f"Deadlock rate peaked: {', '.join(self.affected_tables)} experiencing "
                "lock conflicts"
            ),
            severity="critical"
        )

        # Add mitigation event
        mitigation_time = self.context.end_time - timedelta(minutes=10)
        timeline_gen.add_event(
            timestamp=mitigation_time,
            event_type="mitigation",
            description="Increased connection pool size and added table-level locking hints",
            severity="info"
        )

        return timeline_gen.generate()

