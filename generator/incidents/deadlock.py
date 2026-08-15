"""Database deadlock incident generator."""

import random
from datetime import timedelta
from typing import Any

from generator.core.base import BaseGenerator, IncidentContext
from generator.core.correlation import CorrelationGenerator
from generator.core.distributions import LogNormalDistribution, UniformDistribution
from generator.core.logging_config import get_logger
from generator.core.patterns import NoisePattern, create_business_hours_pattern
from generator.core.timeline import TimelineGenerator
from generator.core.utils import generate_uuid, jitter, timestamp_to_iso

logger = get_logger(__name__)

# Transaction and process identifiers, shaped to look like real database output.
_TXN_ID_DIST = UniformDistribution(min_val=100000, max_val=999999)
_PID_DIST = UniformDistribution(min_val=1000, max_val=32000)
_LOCK_WAIT_DIST = LogNormalDistribution(mu=7, sigma=0.8)  # ~1s, long right tail

SUPPORTED_DIALECTS = ("postgres", "mysql")


class DeadlockGenerator(BaseGenerator):
    """Generates a database deadlock incident scenario.

    Simulates concurrent transactions acquiring row locks on the same tables in
    opposing orders. What separates this from ordinary slow queries is the
    cyclic wait: transaction A holds a lock B needs while B holds one A needs,
    so the database has to pick a victim and roll it back. The visible pattern
    is bursts of rollbacks and lock-wait timeouts rather than a uniform
    slowdown.
    """

    def __init__(
        self,
        context: IncidentContext,
        affected_service: str = "order-service",
        database_service: str = "postgres-primary",
        deadlock_frequency: float = 0.12,
        affected_tables: list[str] | None = None,
        dialect: str = "postgres",
        lock_timeout_ms: float = 5000.0,
        correlation_density: float = 0.8,
    ) -> None:
        """Initialize deadlock generator.

        Args:
            context: Incident context
            affected_service: Service issuing the conflicting transactions
            database_service: Database where the locks contend
            deadlock_frequency: Probability a transaction deadlocks during the incident
            affected_tables: Tables involved in the lock cycle (at least two)
            dialect: Database dialect shaping error messages ('postgres' or 'mysql')
            lock_timeout_ms: Lock wait timeout before the transaction aborts
            correlation_density: Fraction of records carrying a correlation ID

        Raises:
            ValueError: If the dialect is unsupported, the frequency is outside
                [0, 1], or fewer than two tables are given
        """
        super().__init__(context)

        if dialect not in SUPPORTED_DIALECTS:
            raise ValueError(f"dialect must be one of {SUPPORTED_DIALECTS}, got '{dialect}'")
        if not 0.0 <= deadlock_frequency <= 1.0:
            raise ValueError(
                f"deadlock_frequency must be between 0.0 and 1.0, got {deadlock_frequency}"
            )

        self.affected_tables = affected_tables or ["orders", "inventory"]
        if len(self.affected_tables) < 2:
            raise ValueError(
                f"affected_tables needs at least 2 tables to form a lock cycle, "
                f"got {self.affected_tables}"
            )

        self.affected_service = affected_service
        self.database_service = database_service
        self.deadlock_frequency = deadlock_frequency
        self.dialect = dialect
        self.lock_timeout_ms = lock_timeout_ms

        # Apply difficulty configuration if available
        if getattr(context, "difficulty_config", None):
            diff_config = context.difficulty_config
            noise_level = diff_config.noise_level

            if diff_config.level.value == "beginner":
                self.deadlock_frequency = min(1.0, self.deadlock_frequency * 2.0)
            elif diff_config.level.value == "expert":
                # Rare deadlocks buried in normal traffic.
                self.deadlock_frequency *= 0.4

            self.log_volume_multiplier = diff_config.log_volume_multiplier
            logger.info(
                f"Applied {diff_config.level.value} difficulty adjustments: "
                f"deadlock_frequency={self.deadlock_frequency:.3f}, "
                f"noise_level={noise_level:.2f}"
            )
        else:
            noise_level = 0.05
            self.log_volume_multiplier = 1.0

        self.noise = NoisePattern(noise_level=noise_level)
        self.request_rate_pattern = create_business_hours_pattern()
        self.correlation = CorrelationGenerator(density=correlation_density)

        # Update context
        context.affected_services = [affected_service, database_service]
        context.root_cause = (
            f"Database deadlock in {database_service}: concurrent transactions from "
            f"{affected_service} lock {' and '.join(self.affected_tables[:2])} in "
            f"opposing order, forcing the deadlock detector to abort victims"
        )

    def _deadlock_error(self, victim_txn: int, blocking_txn: int) -> tuple[str, str]:
        """Build a dialect-appropriate deadlock error.

        Args:
            victim_txn: Transaction chosen as the deadlock victim
            blocking_txn: Transaction it was waiting on

        Returns:
            Tuple of (message, error_code)
        """
        if self.dialect == "postgres":
            return (
                f"deadlock detected: process {victim_txn} waits for ShareLock on "
                f"transaction {blocking_txn}; blocked by process {blocking_txn}",
                "40P01",
            )

        return (
            "Deadlock found when trying to get lock; try restarting transaction",
            "1213",
        )

    def _lock_timeout_error(self) -> tuple[str, str]:
        """Build a dialect-appropriate lock timeout error.

        Returns:
            Tuple of (message, error_code)
        """
        if self.dialect == "postgres":
            return ("canceling statement due to lock timeout", "55P03")

        return ("Lock wait timeout exceeded; try restarting transaction", "1205")

    def _lock_cycle(self) -> list[dict[str, str]]:
        """Describe the circular wait between transactions.

        Returns:
            Ordered wait edges, each naming the table whose lock is held
        """
        tables = self.affected_tables[:2]
        return [
            {"waiting_on": tables[1], "holding": tables[0]},
            {"waiting_on": tables[0], "holding": tables[1]},
        ]

    def generate(self) -> dict[str, Any]:
        """Generate complete incident dataset.

        Returns:
            Summary of generated data
        """
        logger.info(f"Generating deadlock incident for {self.affected_service}...")

        logs = self._generate_logs()
        metrics = self._generate_metrics()
        traces = self._generate_traces()
        config_deltas = self._generate_config_deltas()
        timeline = self._generate_timeline()

        logger.info(f"  Generated {len(logs)} log entries")
        logger.info(f"  Generated {len(metrics)} metric points")
        logger.info(f"  Generated {len(traces)} traces")
        logger.info(f"  Generated {len(config_deltas)} config changes")
        logger.info(f"  Generated timeline with {len(timeline['events'])} events")

        self.save_jsonl(logs, f"logs_{self.context.incident_id}.jsonl", "logs")
        self.save_jsonl(metrics, f"metrics_{self.context.incident_id}.jsonl", "metrics")
        self.save_jsonl(traces, f"traces_{self.context.incident_id}.jsonl", "traces")
        self.save_jsonl(config_deltas, f"config_{self.context.incident_id}.jsonl", "config_deltas")

        return {
            "incident_id": self.context.incident_id,
            "incident_type": "deadlock",
            "affected_service": self.affected_service,
            "log_count": len(logs),
            "metric_count": len(metrics),
            "trace_count": len(traces),
            "config_change_count": len(config_deltas),
        }

    def _generate_logs(self) -> list[dict[str, Any]]:
        """Generate log entries."""
        logs = []
        hosts = self._get_service_hosts(self.affected_service)
        db_hosts = self._get_service_hosts(self.database_service)

        for current_time in self._iterate_time_window(step=timedelta(seconds=5)):
            during_incident = self.context.is_during_incident(current_time)

            for host in hosts:
                base_rate = 0.2 * self.log_volume_multiplier
                request_rate = self.request_rate_pattern.apply(base_rate, current_time)

                if not self._should_generate_log(request_rate):
                    continue

                deadlocked = during_incident and random.random() < self.deadlock_frequency
                scope = self.correlation.new_scope()

                if not deadlocked:
                    log_entry = {
                        "timestamp": timestamp_to_iso(current_time),
                        "level": "INFO",
                        "service": self.affected_service,
                        "host": host,
                        "message": "Transaction committed",
                        "metadata": {
                            "endpoint": "/api/orders",
                            "method": "POST",
                            "status_code": 200,
                            "duration_ms": round(jitter(35.0, 0.3), 2),
                            "transaction_id": str(int(_TXN_ID_DIST.sample())),
                        },
                    }
                    if scope:
                        scope.stamp_log(log_entry)
                    logs.append(log_entry)
                    continue

                victim_txn = int(_TXN_ID_DIST.sample())
                blocking_txn = int(_TXN_ID_DIST.sample())
                lock_wait_ms = min(float(_LOCK_WAIT_DIST.sample()), self.lock_timeout_ms)
                message, error_code = self._deadlock_error(victim_txn, blocking_txn)

                # The application sees the rollback.
                app_log = {
                    "timestamp": timestamp_to_iso(current_time),
                    "level": "ERROR",
                    "service": self.affected_service,
                    "host": host,
                    "message": "Transaction rolled back after deadlock, retrying",
                    "metadata": {
                        "endpoint": "/api/orders",
                        "method": "POST",
                        "status_code": 500,
                        "duration_ms": round(lock_wait_ms, 2),
                        "error_code": error_code,
                        "transaction_id": str(victim_txn),
                        "blocked_by_transaction": str(blocking_txn),
                        "tables": ",".join(self.affected_tables[:2]),
                    },
                }
                if scope:
                    scope.stamp_log(app_log)
                logs.append(app_log)

                # The database logs the detected cycle.
                db_log = {
                    "timestamp": timestamp_to_iso(current_time),
                    "level": "ERROR",
                    "service": self.database_service,
                    "host": db_hosts[0],
                    "message": message,
                    "metadata": {
                        "error_code": error_code,
                        "duration_ms": round(lock_wait_ms, 2),
                        "victim_pid": str(int(_PID_DIST.sample())),
                        "lock_cycle": str(self._lock_cycle()),
                    },
                }
                if scope:
                    scope.stamp_log(db_log)
                logs.append(db_log)

                # Long waits time out before the detector resolves the cycle.
                if lock_wait_ms >= self.lock_timeout_ms * 0.9:
                    timeout_message, timeout_code = self._lock_timeout_error()
                    timeout_log = {
                        "timestamp": timestamp_to_iso(current_time + timedelta(milliseconds=50)),
                        "level": "WARN",
                        "service": self.database_service,
                        "host": db_hosts[0],
                        "message": timeout_message,
                        "metadata": {
                            "error_code": timeout_code,
                            "duration_ms": round(self.lock_timeout_ms, 2),
                            "table": self.affected_tables[0],
                        },
                    }
                    if scope:
                        scope.stamp_log(timeout_log)
                    logs.append(timeout_log)

        logs.sort(key=lambda entry: entry["timestamp"])
        return logs

    def _generate_metrics(self) -> list[dict[str, Any]]:
        """Generate metrics."""
        metrics = []
        hosts = self._get_service_hosts(self.affected_service)
        db_hosts = self._get_service_hosts(self.database_service)

        for current_time in self._iterate_time_window(step=timedelta(minutes=1)):
            is_anomaly = self.context.is_during_incident(current_time)

            # Contention scales with how often transactions collide.
            contention = self.deadlock_frequency if is_anomaly else 0.0
            deadlocks_per_min = 60.0 * contention * 0.2
            blocked_sessions = 25.0 * contention
            pool_utilization = 35.0 + 55.0 * contention

            for db_host in db_hosts:
                scope = self.correlation.new_scope()
                sample = [
                    {
                        "timestamp": timestamp_to_iso(current_time),
                        "metric_name": "db_deadlocks_per_minute",
                        "value": round(
                            max(0.0, self.noise.apply(deadlocks_per_min, current_time)), 2
                        ),
                        "service": self.database_service,
                        "metric_type": "gauge",
                        "unit": "deadlocks",
                        "host": db_host,
                        "tags": {"database": self.database_service},
                        "anomaly_injected": is_anomaly,
                    },
                    {
                        "timestamp": timestamp_to_iso(current_time),
                        "metric_name": "db_blocked_sessions",
                        "value": round(
                            max(0.0, self.noise.apply(blocked_sessions, current_time)), 2
                        ),
                        "service": self.database_service,
                        "metric_type": "gauge",
                        "unit": "sessions",
                        "host": db_host,
                        "tags": {"database": self.database_service},
                        "anomaly_injected": is_anomaly,
                    },
                    {
                        "timestamp": timestamp_to_iso(current_time),
                        "metric_name": "db_lock_wait_duration_ms",
                        "value": round(
                            max(
                                0.0,
                                self.noise.apply(self.lock_timeout_ms * contention, current_time),
                            ),
                            2,
                        ),
                        "service": self.database_service,
                        "metric_type": "gauge",
                        "unit": "ms",
                        "host": db_host,
                        "tags": {"table": self.affected_tables[0]},
                        "anomaly_injected": is_anomaly,
                    },
                    {
                        "timestamp": timestamp_to_iso(current_time),
                        "metric_name": "db_connection_pool_utilization_percent",
                        "value": round(
                            min(100.0, max(0.0, self.noise.apply(pool_utilization, current_time))),
                            2,
                        ),
                        "service": self.database_service,
                        "metric_type": "gauge",
                        "unit": "percent",
                        "host": db_host,
                        "tags": {},
                        "anomaly_injected": is_anomaly,
                    },
                ]

                if scope:
                    for metric in sample:
                        scope.stamp_metric(metric)
                metrics.extend(sample)

            for host in hosts:
                scope = self.correlation.new_scope()
                sample = [
                    {
                        "timestamp": timestamp_to_iso(current_time),
                        "metric_name": "transaction_rollbacks_per_minute",
                        "value": round(
                            max(0.0, self.noise.apply(deadlocks_per_min, current_time)), 2
                        ),
                        "service": self.affected_service,
                        "metric_type": "gauge",
                        "unit": "rollbacks",
                        "host": host,
                        "tags": {"reason": "deadlock"},
                        "anomaly_injected": is_anomaly,
                    },
                    {
                        "timestamp": timestamp_to_iso(current_time),
                        "metric_name": "http_request_errors_percent",
                        "value": round(
                            min(100.0, max(0.0, self.noise.apply(contention * 100, current_time))),
                            2,
                        ),
                        "service": self.affected_service,
                        "metric_type": "gauge",
                        "unit": "percent",
                        "host": host,
                        "tags": {"endpoint": "/api/orders"},
                        "anomaly_injected": is_anomaly,
                    },
                ]

                if scope:
                    for metric in sample:
                        scope.stamp_metric(metric)
                metrics.extend(sample)

        return metrics

    def _generate_traces(self) -> list[dict[str, Any]]:
        """Generate distributed traces."""
        traces = []
        sample_count = 20

        for i in range(sample_count):
            trace_time = self.context.start_time + (self.context.duration / sample_count) * i
            deadlocked = random.random() < self.deadlock_frequency

            lock_wait_ms = (
                min(float(_LOCK_WAIT_DIST.sample()), self.lock_timeout_ms) if deadlocked else 0.0
            )
            db_duration = jitter(14.0, 0.3) + lock_wait_ms

            trace_id = generate_uuid()
            trace = {
                "trace_id": trace_id,
                "timestamp": timestamp_to_iso(trace_time),
                "spans": [
                    {
                        "span_id": generate_uuid(),
                        "parent_span_id": None,
                        "service": "api-gateway",
                        "operation": "HTTP POST /api/orders",
                        "start_time": timestamp_to_iso(trace_time),
                        "duration_ms": round(db_duration + 20, 2),
                        "status": "ERROR" if deadlocked else "OK",
                        "tags": {"http.method": "POST", "http.path": "/api/orders"},
                    },
                    {
                        "span_id": generate_uuid(),
                        "parent_span_id": trace_id,
                        "service": self.affected_service,
                        "operation": "createOrderTransaction",
                        "start_time": timestamp_to_iso(trace_time + timedelta(milliseconds=3)),
                        "duration_ms": round(db_duration + 8, 2),
                        "status": "ERROR" if deadlocked else "OK",
                        "tags": {
                            "db.transaction": "BEGIN...COMMIT",
                            "retry_attempt": "1" if deadlocked else "0",
                        },
                    },
                    {
                        "span_id": generate_uuid(),
                        "parent_span_id": trace_id,
                        "service": self.database_service,
                        "operation": f"UPDATE {self.affected_tables[0]}",
                        "start_time": timestamp_to_iso(trace_time + timedelta(milliseconds=6)),
                        "duration_ms": round(db_duration, 2),
                        "status": "ERROR" if deadlocked else "OK",
                        "tags": {
                            "db.statement": (
                                f"UPDATE {self.affected_tables[0]} SET status = ? WHERE id = ?"
                            ),
                            "db.lock_wait_ms": round(lock_wait_ms, 2),
                        },
                    },
                ],
            }

            scope = self.correlation.new_scope()
            if scope:
                scope.stamp_trace(trace)

            traces.append(trace)

        return traces

    def _generate_config_deltas(self) -> list[dict[str, Any]]:
        """Generate configuration changes."""
        # A concurrency increase turned a latent lock-ordering bug into an incident.
        change_time = self.context.start_time - timedelta(minutes=10)

        return [
            {
                "timestamp": timestamp_to_iso(change_time),
                "service": self.affected_service,
                "change_type": "config_update",
                "initiator": "platform-team",
                "changes": [
                    {
                        "key": "worker.concurrency",
                        "old_value": "8",
                        "new_value": "32",
                        "category": "performance",
                    },
                    {
                        "key": "db.lock_timeout_ms",
                        "old_value": "1000",
                        "new_value": str(int(self.lock_timeout_ms)),
                        "category": "performance",
                    },
                ],
                "rollback_available": True,
            }
        ]

    def _generate_timeline(self) -> dict[str, Any]:
        """Generate incident timeline."""
        timeline = TimelineGenerator(self.context)

        change_time = self.context.start_time - timedelta(minutes=10)
        timeline.add_config_change(
            change_time,
            self.affected_service,
            "Raised worker concurrency from 8 to 32",
            initiator="platform-team",
        )

        detection_time = self.context.start_time + timedelta(minutes=3)
        timeline.add_anomaly_detection(
            detection_time,
            self.database_service,
            "db_deadlocks_per_minute",
            threshold=1.0,
            actual_value=round(60.0 * self.deadlock_frequency * 0.2, 2),
        )

        timeline.add_alert(
            self.context.start_time + timedelta(minutes=4),
            self.database_service,
            "Elevated deadlock rate and blocked sessions",
            severity="critical",
        )

        timeline.add_mitigation(
            self.context.end_time - timedelta(minutes=6),
            self.affected_service,
            "Reduced worker concurrency to 8 to relieve lock contention",
        )

        timeline.add_mitigation(
            self.context.end_time - timedelta(minutes=3),
            self.affected_service,
            (
                f"Deployed consistent lock ordering across "
                f"{' and '.join(self.affected_tables[:2])}"
            ),
        )

        timeline.add_resolution(
            self.context.end_time,
            "Deadlock rate returned to baseline after lock ordering fix",
        )

        return timeline.generate()
