"""Topology generation utilities."""

from pathlib import Path
from typing import Any, Optional

import yaml

from generator.core.base import BaseGenerator, IncidentContext
from generator.core.logging_config import get_logger

logger = get_logger(__name__)

# Mirrors the enums in schema/topology_schema.json.
VALID_SERVICE_TYPES = {
    "api",
    "database",
    "cache",
    "queue",
    "frontend",
    "worker",
    "gateway",
    "auth",
    "storage",
}
VALID_DEPENDENCY_TYPES = {"http", "grpc", "database", "cache", "queue", "storage"}


class TopologyValidationError(ValueError):
    """Raised when a topology definition is malformed."""


class TopologyGenerator(BaseGenerator):
    """Generates service topology graphs."""

    def __init__(
        self,
        context: IncidentContext,
        services: Optional[list[dict[str, Any]]] = None,
        dependencies: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        """Initialize topology generator.

        Args:
            context: Incident context
            services: Optional list of service definitions
            dependencies: Optional list of dependency edges. Defaults to the
                built-in graph, which only matches the built-in services.
        """
        super().__init__(context)
        self.services = services or self._generate_default_services()
        self._custom_dependencies = dependencies

    @classmethod
    def from_yaml(cls, context: IncidentContext, topology_path: Path) -> "TopologyGenerator":
        """Build a generator from a topology YAML file.

        Args:
            context: Incident context
            topology_path: Path to the topology definition

        Returns:
            Generator configured with the file's services and dependencies

        Raises:
            TopologyValidationError: If the file is missing or malformed
        """
        services, dependencies = load_topology_file(topology_path)
        return cls(context, services=services, dependencies=dependencies)

    def _generate_default_services(self) -> list[dict[str, Any]]:
        """Generate a default microservices topology.

        Returns:
            List of service definitions
        """
        return [
            {
                "name": "api-gateway",
                "type": "gateway",
                "instances": 3,
                "region": "us-east-1",
                "metadata": {
                    "version": "1.2.3",
                    "tier": "critical",
                    "sla_target": 99.9
                }
            },
            {
                "name": "auth-service",
                "type": "auth",
                "instances": 2,
                "region": "us-east-1",
                "metadata": {
                    "version": "2.1.0",
                    "tier": "critical",
                    "sla_target": 99.99
                }
            },
            {
                "name": "user-service",
                "type": "api",
                "instances": 4,
                "region": "us-east-1",
                "metadata": {
                    "version": "3.0.1",
                    "tier": "high",
                    "sla_target": 99.9
                }
            },
            {
                "name": "order-service",
                "type": "api",
                "instances": 4,
                "region": "us-east-1",
                "metadata": {
                    "version": "1.5.2",
                    "tier": "critical",
                    "sla_target": 99.95
                }
            },
            {
                "name": "payment-service",
                "type": "api",
                "instances": 3,
                "region": "us-east-1",
                "metadata": {
                    "version": "2.3.1",
                    "tier": "critical",
                    "sla_target": 99.99
                }
            },
            {
                "name": "inventory-service",
                "type": "api",
                "instances": 2,
                "region": "us-east-1",
                "metadata": {
                    "version": "1.8.0",
                    "tier": "high",
                    "sla_target": 99.5
                }
            },
            {
                "name": "notification-worker",
                "type": "worker",
                "instances": 2,
                "region": "us-east-1",
                "metadata": {
                    "version": "1.1.0",
                    "tier": "medium",
                    "sla_target": 99.0
                }
            },
            {
                "name": "postgres-primary",
                "type": "database",
                "instances": 1,
                "region": "us-east-1",
                "metadata": {
                    "version": "14.5",
                    "tier": "critical",
                    "sla_target": 99.99
                }
            },
            {
                "name": "redis-cache",
                "type": "cache",
                "instances": 2,
                "region": "us-east-1",
                "metadata": {
                    "version": "7.0.5",
                    "tier": "high",
                    "sla_target": 99.9
                }
            },
            {
                "name": "rabbitmq",
                "type": "queue",
                "instances": 2,
                "region": "us-east-1",
                "metadata": {
                    "version": "3.11.0",
                    "tier": "high",
                    "sla_target": 99.9
                }
            }
        ]

    def _generate_dependencies(self) -> list[dict[str, Any]]:
        """Generate dependency graph based on services.

        Returns:
            List of dependency edges
        """
        if self._custom_dependencies is not None:
            return self._custom_dependencies

        dependencies = [
            # Gateway dependencies
            {"from": "api-gateway", "to": "auth-service", "type": "http", "critical": True},
            {"from": "api-gateway", "to": "user-service", "type": "http", "critical": True},
            {"from": "api-gateway", "to": "order-service", "type": "http", "critical": True},
            {"from": "api-gateway", "to": "redis-cache", "type": "cache", "critical": False},

            # Service dependencies
            {"from": "user-service", "to": "postgres-primary", "type": "database", "critical": True},
            {"from": "user-service", "to": "redis-cache", "type": "cache", "critical": False},

            {"from": "order-service", "to": "postgres-primary", "type": "database", "critical": True},
            {"from": "order-service", "to": "inventory-service", "type": "http", "critical": True},
            {"from": "order-service", "to": "payment-service", "type": "http", "critical": True},
            {"from": "order-service", "to": "rabbitmq", "type": "queue", "critical": False},

            {"from": "payment-service", "to": "postgres-primary", "type": "database", "critical": True},

            {"from": "inventory-service", "to": "postgres-primary", "type": "database", "critical": True},
            {"from": "inventory-service", "to": "redis-cache", "type": "cache", "critical": True},

            {"from": "notification-worker", "to": "rabbitmq", "type": "queue", "critical": True},

            # Auth dependencies
            {"from": "auth-service", "to": "postgres-primary", "type": "database", "critical": True},
            {"from": "auth-service", "to": "redis-cache", "type": "cache", "critical": True},
        ]

        return dependencies

    def generate(self) -> dict[str, Any]:
        """Generate complete topology.

        Returns:
            Topology definition
        """
        topology = {
            "services": self.services,
            "dependencies": self._generate_dependencies()
        }

        # Save to file
        self.save_json(topology, "topology.json", "topology")

        return topology

    def get_downstream_services(self, service_name: str) -> list[str]:
        """Get services that depend on the given service.

        Args:
            service_name: Service to check

        Returns:
            List of downstream service names
        """
        dependencies = self._generate_dependencies()
        return [
            dep["from"]
            for dep in dependencies
            if dep["to"] == service_name
        ]

    def get_upstream_services(self, service_name: str) -> list[str]:
        """Get services that the given service depends on.

        Args:
            service_name: Service to check

        Returns:
            List of upstream service names
        """
        dependencies = self._generate_dependencies()
        return [
            dep["to"]
            for dep in dependencies
            if dep["from"] == service_name
        ]


def validate_topology(topology: dict[str, Any]) -> None:
    """Validate a topology definition.

    Checks the structure the generators rely on: named services with known
    types, and dependency edges that point at services which actually exist.

    Args:
        topology: Parsed topology definition

    Raises:
        TopologyValidationError: If the definition is malformed
    """
    if not isinstance(topology, dict):
        raise TopologyValidationError("Topology must be a mapping")

    services = topology.get("services")
    if not isinstance(services, list) or not services:
        raise TopologyValidationError("Topology must define a non-empty 'services' list")

    names: set[str] = set()
    for index, service in enumerate(services):
        if not isinstance(service, dict):
            raise TopologyValidationError(f"Service at index {index} must be a mapping")

        name = service.get("name")
        if not name or not isinstance(name, str):
            raise TopologyValidationError(f"Service at index {index} is missing a string 'name'")

        if name in names:
            raise TopologyValidationError(f"Duplicate service name: {name}")
        names.add(name)

        service_type = service.get("type")
        if service_type not in VALID_SERVICE_TYPES:
            raise TopologyValidationError(
                f"Service '{name}' has invalid type '{service_type}'. "
                f"Must be one of: {sorted(VALID_SERVICE_TYPES)}"
            )

        instances = service.get("instances", 1)
        if not isinstance(instances, int) or isinstance(instances, bool) or instances < 1:
            raise TopologyValidationError(
                f"Service '{name}' has invalid 'instances': {instances!r} (must be an integer >= 1)"
            )

    dependencies = topology.get("dependencies", [])
    if not isinstance(dependencies, list):
        raise TopologyValidationError("Topology 'dependencies' must be a list")

    for index, dependency in enumerate(dependencies):
        if not isinstance(dependency, dict):
            raise TopologyValidationError(f"Dependency at index {index} must be a mapping")

        source, target = dependency.get("from"), dependency.get("to")
        for role, value in (("from", source), ("to", target)):
            if value not in names:
                raise TopologyValidationError(
                    f"Dependency at index {index} has '{role}: {value}' "
                    f"which is not a defined service"
                )

        dependency_type = dependency.get("type")
        if dependency_type is not None and dependency_type not in VALID_DEPENDENCY_TYPES:
            raise TopologyValidationError(
                f"Dependency {source} -> {target} has invalid type '{dependency_type}'. "
                f"Must be one of: {sorted(VALID_DEPENDENCY_TYPES)}"
            )


def _normalize_services(
    services: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split inline per-service dependencies out into edge form.

    Topology files may nest dependencies under each service, which reads better
    than a separate edge list. Generators expect flat edges, so lift them here.

    Args:
        services: Service definitions, possibly with nested 'dependencies'

    Returns:
        Tuple of (services without nested dependencies, extracted edges)
    """
    cleaned: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    for service in services:
        if not isinstance(service, dict):
            cleaned.append(service)
            continue

        service_copy = dict(service)
        nested = service_copy.pop("dependencies", None)

        if isinstance(nested, list):
            for entry in nested:
                if not isinstance(entry, dict):
                    continue
                edges.append(
                    {
                        "from": service_copy.get("name"),
                        "to": entry.get("target", entry.get("to")),
                        "type": entry.get("type", "http"),
                        "critical": entry.get("critical", False),
                    }
                )

        cleaned.append(service_copy)

    return cleaned, edges


def load_topology_file(
    topology_path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Load and validate a topology YAML file.

    Dependencies may be declared either as a top-level ``dependencies`` list or
    nested under each service; both forms are accepted and merged.

    Args:
        topology_path: Path to the topology YAML file

    Returns:
        Tuple of (services, dependencies)

    Raises:
        TopologyValidationError: If the file is missing, unreadable or invalid
    """
    topology_path = Path(topology_path)

    if not topology_path.exists():
        raise TopologyValidationError(f"Topology file not found: {topology_path}")

    if topology_path.suffix not in (".yaml", ".yml"):
        raise TopologyValidationError(f"Topology file must be YAML: {topology_path}")

    try:
        with open(topology_path) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise TopologyValidationError(f"Invalid YAML in {topology_path}: {e}") from e

    if not isinstance(data, dict):
        raise TopologyValidationError(f"Topology file must contain a mapping: {topology_path}")

    raw_services = data.get("services")
    if not isinstance(raw_services, list) or not raw_services:
        raise TopologyValidationError(
            f"Topology file must define a non-empty 'services' list: {topology_path}"
        )

    services, nested_edges = _normalize_services(raw_services)

    top_level_edges = data.get("dependencies", [])
    if not isinstance(top_level_edges, list):
        raise TopologyValidationError(f"Topology 'dependencies' must be a list: {topology_path}")

    dependencies = [*top_level_edges, *nested_edges]

    validate_topology({"services": services, "dependencies": dependencies})

    logger.info(
        f"Loaded topology '{data.get('name', topology_path.stem)}' from {topology_path}: "
        f"{len(services)} services, {len(dependencies)} dependencies"
    )

    return services, dependencies


def find_topology_file(topology_name: str) -> Optional[Path]:
    """Find a topology file by name or path.

    Args:
        topology_name: Topology name (resolved against the bundled ``topology/``
            directory) or a direct path to a YAML file

    Returns:
        Path to the topology file, or None if it could not be found
    """
    direct = Path(topology_name)
    if direct.exists() and direct.suffix in (".yaml", ".yml"):
        return direct

    topology_dir = Path(__file__).parent.parent.parent / "topology"
    for suffix in (".yaml", ".yml"):
        candidate = topology_dir / f"{topology_name}{suffix}"
        if candidate.exists():
            return candidate

    return None
