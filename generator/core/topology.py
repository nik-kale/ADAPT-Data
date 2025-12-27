"""Topology generation utilities."""

import random
from pathlib import Path
from typing import Any, Optional

import yaml

from generator.core.base import BaseGenerator, IncidentContext
from generator.core.logging_config import get_logger

logger = get_logger(__name__)


class TopologyGenerator(BaseGenerator):
    """Generates service topology graphs."""

    def __init__(
        self,
        context: IncidentContext,
        services: Optional[list[dict[str, Any]]] = None,
        topology_file: Optional[str] = None
    ) -> None:
        """Initialize topology generator.

        Args:
            context: Incident context
            services: Optional list of service definitions
            topology_file: Optional path to topology YAML file
        """
        super().__init__(context)
        
        # Load from YAML file if provided
        if topology_file:
            topology_data = self._load_topology_file(topology_file)
            self.services = topology_data.get('services', [])
            self.dependencies = topology_data.get('dependencies', [])
            self.topology_metadata = {
                'name': topology_data.get('name', 'custom'),
                'version': topology_data.get('version', '1.0'),
                'description': topology_data.get('description', '')
            }
            logger.info(f"Loaded topology from {topology_file}: {self.topology_metadata['name']}")
        else:
            self.services = services or self._generate_default_services()
            self.dependencies = self._generate_dependencies()
            self.topology_metadata = {
                'name': 'default',
                'version': '1.0',
                'description': 'Default ADAPT-Data topology'
            }

    def _load_topology_file(self, topology_file: str) -> dict[str, Any]:
        """Load topology from YAML file.

        Args:
            topology_file: Path to topology YAML file

        Returns:
            Topology configuration dictionary

        Raises:
            FileNotFoundError: If topology file doesn't exist
            ValueError: If topology file is invalid
        """
        # Try to find topology file
        topology_path = Path(topology_file)
        
        # If not absolute, try relative to project topology directory
        if not topology_path.is_absolute():
            project_root = Path(__file__).parent.parent.parent
            topology_dir = project_root / "topology"
            topology_path = topology_dir / topology_file
            
            # If still not found, try with .yaml extension
            if not topology_path.exists() and not topology_file.endswith('.yaml'):
                topology_path = topology_dir / f"{topology_file}.yaml"
        
        if not topology_path.exists():
            raise FileNotFoundError(f"Topology file not found: {topology_file}")
        
        # Load and validate YAML
        try:
            with open(topology_path, 'r') as f:
                topology_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid topology YAML: {e}")
        
        # Validate required fields
        if 'services' not in topology_data:
            raise ValueError("Topology must contain 'services' field")
        
        if 'dependencies' not in topology_data:
            raise ValueError("Topology must contain 'dependencies' field")
        
        # Validate services
        for service in topology_data['services']:
            required_fields = ['name', 'type', 'instances', 'region']
            missing = [f for f in required_fields if f not in service]
            if missing:
                raise ValueError(f"Service missing required fields: {missing}")
        
        logger.debug(f"Loaded {len(topology_data['services'])} services and "
                    f"{len(topology_data['dependencies'])} dependencies from {topology_path}")
        
        return topology_data

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
            "name": self.topology_metadata['name'],
            "version": self.topology_metadata['version'],
            "description": self.topology_metadata['description'],
            "services": self.services,
            "dependencies": self.dependencies
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
        return [
            dep["from"]
            for dep in self.dependencies
            if dep["to"] == service_name
        ]

    def get_upstream_services(self, service_name: str) -> list[str]:
        """Get services that the given service depends on.

        Args:
            service_name: Service to check

        Returns:
            List of upstream service names
        """
        return [
            dep["to"]
            for dep in self.dependencies
            if dep["from"] == service_name
        ]
