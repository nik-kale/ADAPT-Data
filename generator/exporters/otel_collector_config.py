"""OpenTelemetry Collector configuration generator."""

import yaml
from pathlib import Path
from typing import Any, Optional

from generator.core.logging_config import get_logger

logger = get_logger(__name__)


class OTELCollectorConfigGenerator:
    """Generate OpenTelemetry Collector configuration for ADAPT-Data.

    Creates collector configs optimized for receiving and processing
    ADAPT-Data synthetic telemetry.
    """

    def __init__(self, output_dir: Path):
        """Initialize config generator.

        Args:
            output_dir: Directory to write configuration files
        """
        self.output_dir = output_dir

    def generate_basic_config(
        self,
        receivers: list[str] = None,
        exporters: list[str] = None,
        include_profiling: bool = True
    ) -> Path:
        """Generate basic OTEL Collector configuration.

        Args:
            receivers: List of receivers to enable (default: otlp, prometheus)
            exporters: List of exporters to enable (default: logging, prometheus, jaeger)
            include_profiling: Include profiling pipeline

        Returns:
            Path to generated config file
        """
        if receivers is None:
            receivers = ["otlp", "prometheus"]

        if exporters is None:
            exporters = ["logging", "prometheusremotewrite", "jaeger"]

        config = {
            "receivers": self._get_receivers_config(receivers),
            "processors": self._get_processors_config(),
            "exporters": self._get_exporters_config(exporters),
            "service": self._get_service_config(include_profiling)
        }

        # Write config
        config_path = self.output_dir / "otel-collector-config.yaml"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Generated OTEL Collector config: {config_path}")
        return config_path

    def generate_kubernetes_config(
        self,
        namespace: str = "adapt-data",
        include_service_mesh: bool = False
    ) -> Path:
        """Generate Kubernetes-optimized OTEL Collector configuration.

        Args:
            namespace: Kubernetes namespace
            include_service_mesh: Include service mesh (Istio/Linkerd) support

        Returns:
            Path to generated config file
        """
        receivers = ["otlp", "prometheus", "k8s_cluster", "k8s_events"]
        if include_service_mesh:
            receivers.append("zipkin")  # For Istio/Linkerd

        config = {
            "receivers": self._get_receivers_config(receivers),
            "processors": self._get_k8s_processors_config(),
            "exporters": self._get_exporters_config(["logging", "prometheusremotewrite", "jaeger"]),
            "service": self._get_service_config(include_profiling=True)
        }

        # Add K8s-specific configs
        if "k8s_cluster" in config["receivers"]:
            config["receivers"]["k8s_cluster"]["auth_type"] = "serviceAccount"
            config["receivers"]["k8s_cluster"]["node"] = "${K8S_NODE_NAME}"

        # Write config
        config_path = self.output_dir / "otel-collector-k8s-config.yaml"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Generated Kubernetes OTEL Collector config: {config_path}")
        return config_path

    def _get_receivers_config(self, receivers: list[str]) -> dict[str, Any]:
        """Get receivers configuration.

        Args:
            receivers: List of receiver names

        Returns:
            Receivers config dict
        """
        config = {}

        if "otlp" in receivers:
            config["otlp"] = {
                "protocols": {
                    "grpc": {
                        "endpoint": "0.0.0.0:4317"
                    },
                    "http": {
                        "endpoint": "0.0.0.0:4318"
                    }
                }
            }

        if "prometheus" in receivers:
            config["prometheus"] = {
                "config": {
                    "scrape_configs": [{
                        "job_name": "adapt-data-metrics",
                        "scrape_interval": "15s",
                        "static_configs": [{
                            "targets": ["localhost:9090"]
                        }]
                    }]
                }
            }

        if "jaeger" in receivers:
            config["jaeger"] = {
                "protocols": {
                    "grpc": {
                        "endpoint": "0.0.0.0:14250"
                    },
                    "thrift_http": {
                        "endpoint": "0.0.0.0:14268"
                    }
                }
            }

        if "zipkin" in receivers:
            config["zipkin"] = {
                "endpoint": "0.0.0.0:9411"
            }

        if "k8s_cluster" in receivers:
            config["k8s_cluster"] = {
                "collection_interval": "30s",
                "node_conditions_to_report": ["Ready", "MemoryPressure", "DiskPressure"],
                "allocatable_types_to_report": ["cpu", "memory", "storage"]
            }

        if "k8s_events" in receivers:
            config["k8s_events"] = {
                "auth_type": "serviceAccount"
            }

        return config

    def _get_processors_config(self) -> dict[str, Any]:
        """Get processors configuration.

        Returns:
            Processors config dict
        """
        return {
            "batch": {
                "timeout": "10s",
                "send_batch_size": 1024
            },
            "memory_limiter": {
                "check_interval": "1s",
                "limit_mib": 512,
                "spike_limit_mib": 128
            },
            "resource": {
                "attributes": [{
                    "key": "telemetry.source",
                    "value": "adapt-data",
                    "action": "upsert"
                }]
            },
            "attributes": {
                "actions": [
                    {
                        "key": "environment",
                        "value": "synthetic",
                        "action": "insert"
                    },
                    {
                        "key": "generated_by",
                        "value": "adapt-data",
                        "action": "insert"
                    }
                ]
            }
        }

    def _get_k8s_processors_config(self) -> dict[str, Any]:
        """Get Kubernetes-specific processors configuration.

        Returns:
            Processors config dict
        """
        base_config = self._get_processors_config()

        # Add K8s attributes processor
        base_config["k8sattributes"] = {
            "auth_type": "serviceAccount",
            "passthrough": False,
            "extract": {
                "metadata": [
                    "k8s.namespace.name",
                    "k8s.deployment.name",
                    "k8s.pod.name",
                    "k8s.pod.uid",
                    "k8s.node.name"
                ],
                "labels": [{
                    "tag_name": "app.label.$$1",
                    "key": "app.kubernetes.io/$$1",
                    "from": "pod"
                }]
            },
            "pod_association": [
                {"sources": [{"from": "resource_attribute", "name": "k8s.pod.ip"}]},
                {"sources": [{"from": "resource_attribute", "name": "k8s.pod.uid"}]},
                {"sources": [{"from": "connection"}]}
            ]
        }

        return base_config

    def _get_exporters_config(self, exporters: list[str]) -> dict[str, Any]:
        """Get exporters configuration.

        Args:
            exporters: List of exporter names

        Returns:
            Exporters config dict
        """
        config = {}

        if "logging" in exporters:
            config["logging"] = {
                "loglevel": "info",
                "sampling_initial": 5,
                "sampling_thereafter": 200
            }

        if "prometheusremotewrite" in exporters:
            config["prometheusremotewrite"] = {
                "endpoint": "http://prometheus:9090/api/v1/write",
                "tls": {
                    "insecure": True
                }
            }

        if "jaeger" in exporters:
            config["jaeger"] = {
                "endpoint": "jaeger:14250",
                "tls": {
                    "insecure": True
                }
            }

        if "zipkin" in exporters:
            config["zipkin"] = {
                "endpoint": "http://zipkin:9411/api/v2/spans",
                "format": "json"
            }

        if "otlp" in exporters:
            config["otlp"] = {
                "endpoint": "otlp-backend:4317",
                "tls": {
                    "insecure": True
                }
            }

        if "otlphttp" in exporters:
            config["otlphttp"] = {
                "endpoint": "http://otlp-backend:4318",
                "compression": "gzip"
            }

        return config

    def _get_service_config(self, include_profiling: bool = True) -> dict[str, Any]:
        """Get service pipeline configuration.

        Args:
            include_profiling: Include profiling pipeline

        Returns:
            Service config dict
        """
        pipelines = {
            "traces": {
                "receivers": ["otlp"],
                "processors": ["memory_limiter", "resource", "attributes", "batch"],
                "exporters": ["logging", "jaeger"]
            },
            "metrics": {
                "receivers": ["otlp", "prometheus"],
                "processors": ["memory_limiter", "resource", "attributes", "batch"],
                "exporters": ["logging", "prometheusremotewrite"]
            },
            "logs": {
                "receivers": ["otlp"],
                "processors": ["memory_limiter", "resource", "attributes", "batch"],
                "exporters": ["logging"]
            }
        }

        if include_profiling:
            pipelines["profiles"] = {
                "receivers": ["otlp"],
                "processors": ["memory_limiter", "batch"],
                "exporters": ["logging"]
            }

        return {
            "telemetry": {
                "logs": {
                    "level": "info"
                },
                "metrics": {
                    "address": ":8888"
                }
            },
            "pipelines": pipelines
        }

    def generate_docker_compose(
        self,
        include_backends: bool = True
    ) -> Path:
        """Generate Docker Compose file for OTEL Collector setup.

        Args:
            include_backends: Include backend services (Prometheus, Jaeger)

        Returns:
            Path to generated docker-compose.yml
        """
        services = {
            "otel-collector": {
                "image": "otel/opentelemetry-collector-contrib:latest",
                "command": ["--config=/etc/otel-collector-config.yaml"],
                "volumes": ["./otel-collector-config.yaml:/etc/otel-collector-config.yaml"],
                "ports": [
                    "4317:4317",  # OTLP gRPC
                    "4318:4318",  # OTLP HTTP
                    "9090:9090",  # Prometheus exporter
                    "8888:8888",  # Collector metrics
                ]
            }
        }

        if include_backends:
            services["prometheus"] = {
                "image": "prom/prometheus:latest",
                "ports": ["9091:9090"],
                "command": [
                    "--config.file=/etc/prometheus/prometheus.yml",
                    "--enable-feature=remote-write-receiver"
                ]
            }

            services["jaeger"] = {
                "image": "jaegertracing/all-in-one:latest",
                "ports": [
                    "16686:16686",  # Jaeger UI
                    "14250:14250",  # gRPC
                ]
            }

        compose_config = {
            "version": "3.8",
            "services": services
        }

        # Write docker-compose.yml
        compose_path = self.output_dir / "docker-compose.yml"
        with open(compose_path, 'w') as f:
            yaml.dump(compose_config, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Generated Docker Compose file: {compose_path}")
        return compose_path
