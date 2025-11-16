"""Example Custom Generator Plugin for ADAPT-Data.

This plugin demonstrates how to create a custom incident generator
that simulates a memory leak scenario.

To use this plugin:
1. Copy this file to ~/.adapt-data/plugins/
2. The plugin will be auto-discovered on startup
3. Use in scenarios with type: "memory_leak"
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from generator.core.base import BaseGenerator, IncidentContext
from generator.core.distributions import UniformDistribution, ExponentialDistribution
from generator.core.logging_config import get_logger
from generator.core.plugins import GeneratorPlugin
from generator.core.utils import timestamp_to_iso, generate_uuid

logger = get_logger(__name__)


class MemoryLeakGenerator(BaseGenerator):
    """Generates a memory leak incident scenario.

    Simulates gradual memory exhaustion leading to OOM errors.
    """

    def __init__(
        self,
        context: IncidentContext,
        affected_service: str = "user-service",
        initial_memory_mb: float = 512.0,
        leak_rate_mb_per_min: float = 5.0,
        oom_threshold_mb: float = 2048.0
    ) -> None:
        """Initialize memory leak generator.

        Args:
            context: Incident context
            affected_service: Service experiencing memory leak
            initial_memory_mb: Starting memory usage
            leak_rate_mb_per_min: Memory leak rate per minute
            oom_threshold_mb: Memory threshold that triggers OOM
        """
        super().__init__(context)
        self.affected_service = affected_service
        self.initial_memory_mb = initial_memory_mb
        self.leak_rate_mb_per_min = leak_rate_mb_per_min
        self.oom_threshold_mb = oom_threshold_mb

        # Distributions
        self.jitter_dist = UniformDistribution(min_val=-10, max_val=10)
        self.gc_pause_dist = ExponentialDistribution(rate=0.1)

        # Update context
        context.affected_services = [affected_service]
        context.root_cause = f"Memory leak in {affected_service} due to unclosed resources"

    def generate(self) -> dict[str, Any]:
        """Generate complete incident dataset."""
        logger.info(f"Generating memory leak incident for {self.affected_service}...")

        logs = self._generate_logs()
        metrics = self._generate_metrics()
        traces = []  # Simplified - no traces for this example

        logger.info(f"  Generated {len(logs)} log entries")
        logger.info(f"  Generated {len(metrics)} metric points")

        # Save files
        self.save_jsonl(logs, f"logs_{self.context.incident_id}.jsonl", "logs")
        self.save_jsonl(metrics, f"metrics_{self.context.incident_id}.jsonl", "metrics")

        return {
            "incident_id": self.context.incident_id,
            "incident_type": "memory_leak",
            "affected_service": self.affected_service,
            "log_count": len(logs),
            "metric_count": len(metrics)
        }

    def _generate_logs(self) -> list[dict[str, Any]]:
        """Generate log entries showing memory leak progression."""
        logs = []
        hosts = self._get_service_hosts(self.affected_service)

        current_time = self.context.start_time - timedelta(minutes=30)
        end_time = self.context.end_time + timedelta(minutes=30)

        while current_time < end_time:
            # Calculate current memory based on leak rate
            minutes_elapsed = (current_time - self.context.start_time).total_seconds() / 60
            current_memory = self.initial_memory_mb + (self.leak_rate_mb_per_min * minutes_elapsed)
            current_memory = max(self.initial_memory_mb, current_memory)

            for host in hosts:
                # Normal operation logs
                if current_time.second % 10 == 0:
                    logs.append({
                        "timestamp": timestamp_to_iso(current_time),
                        "level": "INFO",
                        "service": self.affected_service,
                        "host": host,
                        "message": f"Memory usage: {int(current_memory)}MB",
                        "metadata": {
                            "memory_mb": int(current_memory),
                            "memory_percent": int((current_memory / self.oom_threshold_mb) * 100)
                        }
                    })

                # Warning logs when memory high
                if current_memory > self.oom_threshold_mb * 0.8 and current_time.second % 30 == 0:
                    logs.append({
                        "timestamp": timestamp_to_iso(current_time),
                        "level": "WARN",
                        "service": self.affected_service,
                        "host": host,
                        "message": "High memory usage detected",
                        "metadata": {
                            "memory_mb": int(current_memory),
                            "threshold_mb": int(self.oom_threshold_mb),
                            "leak_suspected": True
                        }
                    })

                # OOM errors when threshold exceeded
                if current_memory > self.oom_threshold_mb:
                    logs.append({
                        "timestamp": timestamp_to_iso(current_time),
                        "level": "ERROR",
                        "service": self.affected_service,
                        "host": host,
                        "message": "OutOfMemoryError: Java heap space",
                        "metadata": {
                            "memory_mb": int(current_memory),
                            "error_type": "OOMError",
                            "stack_trace": "java.lang.OutOfMemoryError: Java heap space"
                        }
                    })

            current_time += timedelta(seconds=1)

        return logs

    def _generate_metrics(self) -> list[dict[str, Any]]:
        """Generate memory metrics showing gradual increase."""
        metrics = []
        hosts = self._get_service_hosts(self.affected_service)

        current_time = self.context.start_time - timedelta(minutes=30)
        end_time = self.context.end_time + timedelta(minutes=30)

        while current_time < end_time:
            minutes_elapsed = (current_time - self.context.start_time).total_seconds() / 60
            base_memory = self.initial_memory_mb + (self.leak_rate_mb_per_min * minutes_elapsed)
            base_memory = max(self.initial_memory_mb, base_memory)

            for host in hosts:
                # Add jitter to memory value
                memory_with_jitter = base_memory + self.jitter_dist.sample()

                metrics.append({
                    "timestamp": timestamp_to_iso(current_time),
                    "metric_name": "jvm_memory_used_bytes",
                    "value": int(memory_with_jitter * 1024 * 1024),  # Convert to bytes
                    "service": self.affected_service,
                    "metric_type": "gauge",
                    "unit": "bytes",
                    "host": host,
                    "tags": {"memory_pool": "heap"},
                    "anomaly_injected": self.context.is_during_incident(current_time)
                })

                # GC frequency increases as memory fills
                if base_memory > self.oom_threshold_mb * 0.7:
                    gc_pause_ms = max(10, self.gc_pause_dist.sample() * 1000)
                    metrics.append({
                        "timestamp": timestamp_to_iso(current_time),
                        "metric_name": "jvm_gc_pause_seconds",
                        "value": gc_pause_ms / 1000.0,
                        "service": self.affected_service,
                        "metric_type": "gauge",
                        "unit": "seconds",
                        "host": host,
                        "tags": {"gc_type": "G1 Young Generation"},
                        "anomaly_injected": True
                    })

            current_time += timedelta(minutes=1)

        return metrics


# Plugin registration
class MemoryLeakGeneratorPlugin(GeneratorPlugin):
    """Plugin wrapper for MemoryLeakGenerator."""

    name = "memory_leak"
    version = "1.0.0"
    description = "Generates memory leak incidents with gradual OOM progression"
    generator_class = MemoryLeakGenerator


# Export plugin instance
plugin = MemoryLeakGeneratorPlugin()
