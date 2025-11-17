"""Chaos engineering experiment templates.

Provides pre-defined chaos experiments for common failure scenarios.
"""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ChaosExperiment:
    """Represents a chaos engineering experiment."""

    name: str
    description: str
    blast_radius: str  # pod, node, zone, region
    duration_minutes: int
    hypothesis: str
    steady_state: dict[str, Any]
    injection: dict[str, Any]
    rollback: dict[str, Any]


class ChaosTemplates:
    """Pre-defined chaos engineering experiment templates."""

    @staticmethod
    def pod_kill() -> ChaosExperiment:
        """Random pod termination experiment."""
        return ChaosExperiment(
            name="pod-kill",
            description="Randomly kill pods to test resilience",
            blast_radius="pod",
            duration_minutes=10,
            hypothesis="Application should recover from pod failures within 30 seconds",
            steady_state={
                "availability": "> 99.9%",
                "error_rate": "< 0.1%",
                "p99_latency": "< 200ms"
            },
            injection={
                "type": "pod_kill",
                "target": "random",
                "count": 1,
                "interval_seconds": 60
            },
            rollback={
                "automatic": True,
                "timeout_minutes": 15
            }
        )

    @staticmethod
    def network_latency() -> ChaosExperiment:
        """Network latency injection experiment."""
        return ChaosExperiment(
            name="network-latency",
            description="Inject network latency between services",
            blast_radius="pod",
            duration_minutes=15,
            hypothesis="Application should gracefully handle network latency up to 500ms",
            steady_state={
                "p95_latency": "< 100ms",
                "timeout_rate": "< 0.1%"
            },
            injection={
                "type": "network_latency",
                "latency_ms": 500,
                "jitter_ms": 100,
                "target_service": "database"
            },
            rollback={
                "automatic": True,
                "timeout_minutes": 20
            }
        )

    @staticmethod
    def cpu_stress() -> ChaosExperiment:
        """CPU stress test experiment."""
        return ChaosExperiment(
            name="cpu-stress",
            description="Stress CPU on pods",
            blast_radius="pod",
            duration_minutes=10,
            hypothesis="Application should maintain SLO under CPU stress",
            steady_state={
                "cpu_usage": "< 70%",
                "availability": "> 99%"
            },
            injection={
                "type": "cpu_stress",
                "cpu_percent": 90,
                "workers": 2
            },
            rollback={
                "automatic": True,
                "timeout_minutes": 15
            }
        )

    @staticmethod
    def zone_outage() -> ChaosExperiment:
        """Availability zone outage experiment."""
        return ChaosExperiment(
            name="zone-outage",
            description="Simulate availability zone failure",
            blast_radius="zone",
            duration_minutes=30,
            hypothesis="Multi-AZ deployment should handle zone failure",
            steady_state={
                "availability": "> 99.9%",
                "cross_zone_traffic": "balanced"
            },
            injection={
                "type": "zone_failure",
                "zone": "us-east-1a",
                "action": "cordon_and_drain"
            },
            rollback={
                "automatic": False,
                "manual_steps": ["Uncordon nodes", "Verify pod distribution"]
            }
        )

    @staticmethod
    def memory_leak() -> ChaosExperiment:
        """Memory leak injection experiment."""
        return ChaosExperiment(
            name="memory-leak",
            description="Simulate gradual memory leak",
            blast_radius="pod",
            duration_minutes=20,
            hypothesis="OOM killer should evict pod before system impact",
            steady_state={
                "memory_usage": "< 80%",
                "oom_kills": "0"
            },
            injection={
                "type": "memory_stress",
                "rate_mb_per_minute": 50,
                "max_memory_mb": 1024
            },
            rollback={
                "automatic": True,
                "timeout_minutes": 25
            }
        )

    @staticmethod
    def get_all_templates() -> list[ChaosExperiment]:
        """Get all chaos experiment templates."""
        return [
            ChaosTemplates.pod_kill(),
            ChaosTemplates.network_latency(),
            ChaosTemplates.cpu_stress(),
            ChaosTemplates.zone_outage(),
            ChaosTemplates.memory_leak()
        ]
