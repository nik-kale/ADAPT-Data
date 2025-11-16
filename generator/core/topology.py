"""Topology generation utilities."""

import random
from typing import Any, Optional

from generator.core.base import BaseGenerator, IncidentContext


class TopologyGenerator(BaseGenerator):
    """Generates service topology graphs."""

    def __init__(
        self,
        context: IncidentContext,
        services: Optional[list[dict[str, Any]]] = None
    ) -> None:
        """Initialize topology generator.

        Args:
            context: Incident context
            services: Optional list of service definitions
        """
        super().__init__(context)
        self.services = services or self._generate_default_services()

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
