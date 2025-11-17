"""Kubernetes pod eviction incident generator.

Simulates pod evictions due to resource pressure, including:
- OOMKilled (out of memory)
- Node pressure evictions
- Priority-based preemption
- Proactive node drain
"""

import random
from datetime import datetime, timedelta
from typing import Any

from generator.core.base import BaseGenerator, IncidentContext
from generator.core.semantic_conventions import SemanticConventions
from generator.core.utils import generate_uuid, timestamp_to_iso


class KubernetesPodEvictionGenerator(BaseGenerator):
    """Generate Kubernetes pod eviction incidents.

    Simulates realistic K8s pod evictions with full semantic conventions.
    """

    def __init__(
        self,
        context: IncidentContext,
        affected_service: str = "web-service",
        cluster_name: str = "production-cluster",
        namespace: str = "default",
        eviction_reason: str = "OOMKilled",
        num_pods: int = 5,
        node_name: str = "node-1"
    ):
        """Initialize pod eviction incident generator.

        Args:
            context: Incident context
            affected_service: Service experiencing evictions
            cluster_name: Kubernetes cluster name
            namespace: Kubernetes namespace
            eviction_reason: Eviction reason (OOMKilled, NodePressure, Preempted)
            num_pods: Number of pods affected
            node_name: Node experiencing issues
        """
        super().__init__(context)
        self.affected_service = affected_service
        self.cluster_name = cluster_name
        self.namespace = namespace
        self.eviction_reason = eviction_reason
        self.num_pods = num_pods
        self.node_name = node_name

        # Update context
        context.affected_services = [affected_service]
        context.root_cause = (
            f"Kubernetes pod evictions ({eviction_reason}) on {node_name} "
            f"due to resource constraints"
        )

    def generate(self) -> dict[str, Any]:
        """Generate pod eviction incident data."""
        logs = self._generate_logs()
        metrics = self._generate_metrics()
        timeline = self._generate_timeline()

        # Save all data
        self.save_jsonl(logs, f"logs_{self.context.incident_id}.jsonl", "logs")
        self.save_jsonl(metrics, f"metrics_{self.context.incident_id}.jsonl", "metrics")
        self.save_json(timeline, f"timeline_{self.context.incident_id}.json", "timelines")

        return {
            "incident_id": self.context.incident_id,
            "incident_type": "kubernetes_pod_eviction",
            "affected_services": self.context.affected_services,
            "root_cause": self.context.root_cause,
            "num_logs": len(logs),
            "num_metrics": len(metrics)
        }

    def _generate_logs(self) -> list[dict[str, Any]]:
        """Generate Kubernetes event logs."""
        logs = []

        # Generate pod names
        pod_names = [f"{self.affected_service}-{generate_uuid()[:8]}" for _ in range(self.num_pods)]

        for current_time in self._iterate_time_window(step=timedelta(seconds=30)):
            is_during = self.context.is_during_incident(current_time)

            # Normal pod lifecycle logs
            if random.random() < 0.2:
                logs.append({
                    "timestamp": timestamp_to_iso(current_time),
                    "level": "INFO",
                    "service": "kubelet",
                    "host": self.node_name,
                    "message": f"Pod {random.choice(pod_names)} is running",
                    "metadata": {
                        "cluster": self.cluster_name,
                        "namespace": self.namespace,
                        "pod": random.choice(pod_names)
                    }
                })

            # Eviction warnings
            if is_during and random.random() < 0.5:
                pod = random.choice(pod_names)
                if self.eviction_reason == "OOMKilled":
                    logs.append({
                        "timestamp": timestamp_to_iso(current_time),
                        "level": "WARN",
                        "service": "kubelet",
                        "host": self.node_name,
                        "message": f"Pod {pod} exceeded memory limits",
                        "metadata": {
                            "cluster": self.cluster_name,
                            "namespace": self.namespace,
                            "pod": pod,
                            "memory_limit": "512Mi",
                            "memory_usage": "650Mi"
                        }
                    })
                elif self.eviction_reason == "NodePressure":
                    logs.append({
                        "timestamp": timestamp_to_iso(current_time),
                        "level": "WARN",
                        "service": "kubelet",
                        "host": self.node_name,
                        "message": f"Node {self.node_name} under memory pressure",
                        "metadata": {
                            "cluster": self.cluster_name,
                            "node": self.node_name,
                            "pressure_type": "MemoryPressure"
                        }
                    })

            # Eviction events
            if is_during and random.random() < 0.3:
                pod = random.choice(pod_names)
                logs.append({
                    "timestamp": timestamp_to_iso(current_time),
                    "level": "ERROR",
                    "service": "kube-scheduler",
                    "host": "control-plane",
                    "message": f"Pod {pod} evicted: {self.eviction_reason}",
                    "metadata": {
                        "cluster": self.cluster_name,
                        "namespace": self.namespace,
                        "pod": pod,
                        "node": self.node_name,
                        "reason": self.eviction_reason
                    }
                })

                # Pod restart log
                logs.append({
                    "timestamp": timestamp_to_iso(current_time + timedelta(seconds=10)),
                    "level": "INFO",
                    "service": "kube-scheduler",
                    "host": "control-plane",
                    "message": f"Rescheduling pod {pod} after eviction",
                    "metadata": {
                        "cluster": self.cluster_name,
                        "namespace": self.namespace,
                        "pod": pod,
                        "target_node": "node-2"  # Reschedule to different node
                    }
                })

        return logs

    def _generate_metrics(self) -> list[dict[str, Any]]:
        """Generate Kubernetes metrics."""
        metrics = []

        for current_time in self._iterate_time_window(step=timedelta(minutes=1)):
            is_during = self.context.is_during_incident(current_time)

            # Node memory usage
            if is_during:
                node_memory_pct = random.uniform(85, 98)
            else:
                node_memory_pct = random.uniform(50, 70)

            metrics.append({
                "timestamp": timestamp_to_iso(current_time),
                "metric_name": "kube.node.memory.usage_pct",
                "value": node_memory_pct,
                "unit": "percent",
                "service": "kubelet",
                "host": self.node_name,
                "tags": {
                    "cluster": self.cluster_name,
                    "node": self.node_name
                },
                "anomaly_injected": is_during
            })

            # Pod restart count
            if is_during:
                restart_count = random.randint(3, 10)
            else:
                restart_count = random.randint(0, 1)

            metrics.append({
                "timestamp": timestamp_to_iso(current_time),
                "metric_name": "kube.pod.restart_count",
                "value": restart_count,
                "unit": "count",
                "service": self.affected_service,
                "host": self.node_name,
                "tags": {
                    "cluster": self.cluster_name,
                    "namespace": self.namespace,
                    "service": self.affected_service
                },
                "anomaly_injected": is_during
            })

            # Pod count
            if is_during:
                # Pods cycling between evicted and running
                running_pods = random.randint(2, self.num_pods - 1)
            else:
                running_pods = self.num_pods

            metrics.append({
                "timestamp": timestamp_to_iso(current_time),
                "metric_name": "kube.deployment.pods_running",
                "value": running_pods,
                "unit": "count",
                "service": self.affected_service,
                "host": "control-plane",
                "tags": {
                    "cluster": self.cluster_name,
                    "namespace": self.namespace,
                    "deployment": self.affected_service
                },
                "anomaly_injected": is_during
            })

            # OOM kill count
            if is_during and self.eviction_reason == "OOMKilled":
                oom_kills = random.randint(1, 3)
                metrics.append({
                    "timestamp": timestamp_to_iso(current_time),
                    "metric_name": "kube.pod.oom_kills",
                    "value": oom_kills,
                    "unit": "count",
                    "service": self.affected_service,
                    "host": self.node_name,
                    "tags": {
                        "cluster": self.cluster_name,
                        "namespace": self.namespace
                    },
                    "anomaly_injected": True
                })

        return metrics

    def _generate_timeline(self) -> dict[str, Any]:
        """Generate incident timeline."""
        return {
            "incident_id": self.context.incident_id,
            "start_time": timestamp_to_iso(self.context.start_time),
            "end_time": timestamp_to_iso(self.context.end_time),
            "severity": self.context.severity,
            "events": [
                {
                    "timestamp": timestamp_to_iso(self.context.start_time - timedelta(minutes=10)),
                    "event_type": "normal",
                    "description": f"All {self.num_pods} pods running normally on {self.node_name}"
                },
                {
                    "timestamp": timestamp_to_iso(self.context.start_time),
                    "event_type": "detection",
                    "description": f"First pod eviction detected: {self.eviction_reason}"
                },
                {
                    "timestamp": timestamp_to_iso(self.context.start_time + timedelta(minutes=5)),
                    "event_type": "escalation",
                    "description": f"Multiple pods evicted from {self.node_name}"
                },
                {
                    "timestamp": timestamp_to_iso(self.context.start_time + timedelta(minutes=10)),
                    "event_type": "mitigation",
                    "description": f"Pods rescheduled to other nodes, {self.node_name} cordoned"
                },
                {
                    "timestamp": timestamp_to_iso(self.context.end_time),
                    "event_type": "resolution",
                    "description": f"All pods running stably, {self.node_name} drained and replaced"
                }
            ]
        }
