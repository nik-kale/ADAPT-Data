"""OpenTelemetry Semantic Conventions.

This module provides utilities for generating telemetry data that complies
with OpenTelemetry semantic conventions.

Reference: https://opentelemetry.io/docs/specs/semconv/
"""

from typing import Any


class SemanticConventions:
    """OpenTelemetry semantic conventions for telemetry attributes."""

    # Resource attributes
    RESOURCE_SERVICE_NAME = "service.name"
    RESOURCE_SERVICE_NAMESPACE = "service.namespace"
    RESOURCE_SERVICE_INSTANCE_ID = "service.instance.id"
    RESOURCE_SERVICE_VERSION = "service.version"
    RESOURCE_DEPLOYMENT_ENVIRONMENT = "deployment.environment"

    # Cloud attributes
    CLOUD_PROVIDER = "cloud.provider"
    CLOUD_PLATFORM = "cloud.platform"
    CLOUD_REGION = "cloud.region"
    CLOUD_AVAILABILITY_ZONE = "cloud.availability_zone"
    CLOUD_ACCOUNT_ID = "cloud.account.id"

    # Container attributes
    CONTAINER_NAME = "container.name"
    CONTAINER_ID = "container.id"
    CONTAINER_IMAGE_NAME = "container.image.name"
    CONTAINER_IMAGE_TAG = "container.image.tag"

    # Host attributes
    HOST_NAME = "host.name"
    HOST_ID = "host.id"
    HOST_TYPE = "host.type"
    HOST_ARCH = "host.arch"
    HOST_IMAGE_NAME = "host.image.name"
    HOST_IMAGE_ID = "host.image.id"
    HOST_IMAGE_VERSION = "host.image.version"

    # Kubernetes attributes
    K8S_CLUSTER_NAME = "k8s.cluster.name"
    K8S_NAMESPACE_NAME = "k8s.namespace.name"
    K8S_POD_NAME = "k8s.pod.name"
    K8S_POD_UID = "k8s.pod.uid"
    K8S_CONTAINER_NAME = "k8s.container.name"
    K8S_DEPLOYMENT_NAME = "k8s.deployment.name"
    K8S_NODE_NAME = "k8s.node.name"

    # HTTP attributes
    HTTP_METHOD = "http.method"
    HTTP_URL = "http.url"
    HTTP_TARGET = "http.target"
    HTTP_HOST = "http.host"
    HTTP_SCHEME = "http.scheme"
    HTTP_STATUS_CODE = "http.status_code"
    HTTP_FLAVOR = "http.flavor"
    HTTP_USER_AGENT = "http.user_agent"
    HTTP_REQUEST_CONTENT_LENGTH = "http.request_content_length"
    HTTP_RESPONSE_CONTENT_LENGTH = "http.response_content_length"
    HTTP_ROUTE = "http.route"

    # Database attributes
    DB_SYSTEM = "db.system"
    DB_CONNECTION_STRING = "db.connection_string"
    DB_USER = "db.user"
    DB_NAME = "db.name"
    DB_STATEMENT = "db.statement"
    DB_OPERATION = "db.operation"
    DB_SQL_TABLE = "db.sql.table"

    # RPC attributes
    RPC_SYSTEM = "rpc.system"
    RPC_SERVICE = "rpc.service"
    RPC_METHOD = "rpc.method"
    RPC_GRPC_STATUS_CODE = "rpc.grpc.status_code"

    # Messaging attributes
    MESSAGING_SYSTEM = "messaging.system"
    MESSAGING_DESTINATION = "messaging.destination"
    MESSAGING_DESTINATION_KIND = "messaging.destination_kind"
    MESSAGING_OPERATION = "messaging.operation"
    MESSAGING_MESSAGE_ID = "messaging.message_id"
    MESSAGING_KAFKA_PARTITION = "messaging.kafka.partition"

    # Network attributes
    NET_PEER_NAME = "net.peer.name"
    NET_PEER_IP = "net.peer.ip"
    NET_PEER_PORT = "net.peer.port"
    NET_HOST_NAME = "net.host.name"
    NET_HOST_IP = "net.host.ip"
    NET_HOST_PORT = "net.host.port"
    NET_TRANSPORT = "net.transport"

    # Error attributes
    ERROR_TYPE = "error.type"
    EXCEPTION_TYPE = "exception.type"
    EXCEPTION_MESSAGE = "exception.message"
    EXCEPTION_STACKTRACE = "exception.stacktrace"
    EXCEPTION_ESCAPED = "exception.escaped"

    # Thread attributes
    THREAD_ID = "thread.id"
    THREAD_NAME = "thread.name"

    # Code attributes
    CODE_FUNCTION = "code.function"
    CODE_NAMESPACE = "code.namespace"
    CODE_FILEPATH = "code.filepath"
    CODE_LINENO = "code.lineno"

    # GenAI semantic conventions (new)
    GENAI_SYSTEM = "gen_ai.system"
    GENAI_REQUEST_MODEL = "gen_ai.request.model"
    GENAI_REQUEST_MAX_TOKENS = "gen_ai.request.max_tokens"
    GENAI_REQUEST_TEMPERATURE = "gen_ai.request.temperature"
    GENAI_REQUEST_TOP_P = "gen_ai.request.top_p"
    GENAI_RESPONSE_ID = "gen_ai.response.id"
    GENAI_RESPONSE_MODEL = "gen_ai.response.model"
    GENAI_RESPONSE_FINISH_REASONS = "gen_ai.response.finish_reasons"
    GENAI_USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
    GENAI_USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
    GENAI_USAGE_TOTAL_TOKENS = "gen_ai.usage.total_tokens"
    GENAI_PROMPT = "gen_ai.prompt"
    GENAI_COMPLETION = "gen_ai.completion"

    @staticmethod
    def get_http_span_attributes(
        method: str,
        url: str,
        status_code: int,
        route: str = None,
        user_agent: str = None
    ) -> dict[str, Any]:
        """Get HTTP span attributes following semantic conventions.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL
            status_code: HTTP status code
            route: HTTP route pattern (optional)
            user_agent: User agent string (optional)

        Returns:
            Dictionary of HTTP semantic convention attributes
        """
        attrs = {
            SemanticConventions.HTTP_METHOD: method,
            SemanticConventions.HTTP_URL: url,
            SemanticConventions.HTTP_STATUS_CODE: status_code,
        }

        if route:
            attrs[SemanticConventions.HTTP_ROUTE] = route
        if user_agent:
            attrs[SemanticConventions.HTTP_USER_AGENT] = user_agent

        return attrs

    @staticmethod
    def get_database_span_attributes(
        system: str,
        operation: str,
        table: str = None,
        statement: str = None
    ) -> dict[str, Any]:
        """Get database span attributes following semantic conventions.

        Args:
            system: Database system (postgresql, mysql, redis, etc.)
            operation: Database operation (SELECT, INSERT, etc.)
            table: Table name (optional)
            statement: SQL statement (optional)

        Returns:
            Dictionary of database semantic convention attributes
        """
        attrs = {
            SemanticConventions.DB_SYSTEM: system,
            SemanticConventions.DB_OPERATION: operation,
        }

        if table:
            attrs[SemanticConventions.DB_SQL_TABLE] = table
        if statement:
            attrs[SemanticConventions.DB_STATEMENT] = statement

        return attrs

    @staticmethod
    def get_messaging_span_attributes(
        system: str,
        destination: str,
        operation: str,
        message_id: str = None
    ) -> dict[str, Any]:
        """Get messaging span attributes following semantic conventions.

        Args:
            system: Messaging system (kafka, rabbitmq, etc.)
            destination: Destination name (topic, queue)
            operation: Operation (publish, receive, process)
            message_id: Message ID (optional)

        Returns:
            Dictionary of messaging semantic convention attributes
        """
        attrs = {
            SemanticConventions.MESSAGING_SYSTEM: system,
            SemanticConventions.MESSAGING_DESTINATION: destination,
            SemanticConventions.MESSAGING_OPERATION: operation,
        }

        if message_id:
            attrs[SemanticConventions.MESSAGING_MESSAGE_ID] = message_id

        return attrs

    @staticmethod
    def get_resource_attributes(
        service_name: str,
        service_version: str = "1.0.0",
        deployment_environment: str = "production",
        service_namespace: str = None,
        service_instance_id: str = None
    ) -> dict[str, Any]:
        """Get resource attributes following semantic conventions.

        Args:
            service_name: Service name
            service_version: Service version
            deployment_environment: Environment (production, staging, etc.)
            service_namespace: Service namespace (optional)
            service_instance_id: Service instance ID (optional)

        Returns:
            Dictionary of resource semantic convention attributes
        """
        attrs = {
            SemanticConventions.RESOURCE_SERVICE_NAME: service_name,
            SemanticConventions.RESOURCE_SERVICE_VERSION: service_version,
            SemanticConventions.RESOURCE_DEPLOYMENT_ENVIRONMENT: deployment_environment,
        }

        if service_namespace:
            attrs[SemanticConventions.RESOURCE_SERVICE_NAMESPACE] = service_namespace
        if service_instance_id:
            attrs[SemanticConventions.RESOURCE_SERVICE_INSTANCE_ID] = service_instance_id

        return attrs

    @staticmethod
    def get_k8s_resource_attributes(
        cluster_name: str,
        namespace: str,
        pod_name: str,
        pod_uid: str,
        container_name: str = None,
        deployment_name: str = None,
        node_name: str = None
    ) -> dict[str, Any]:
        """Get Kubernetes resource attributes following semantic conventions.

        Args:
            cluster_name: Cluster name
            namespace: Namespace
            pod_name: Pod name
            pod_uid: Pod UID
            container_name: Container name (optional)
            deployment_name: Deployment name (optional)
            node_name: Node name (optional)

        Returns:
            Dictionary of Kubernetes semantic convention attributes
        """
        attrs = {
            SemanticConventions.K8S_CLUSTER_NAME: cluster_name,
            SemanticConventions.K8S_NAMESPACE_NAME: namespace,
            SemanticConventions.K8S_POD_NAME: pod_name,
            SemanticConventions.K8S_POD_UID: pod_uid,
        }

        if container_name:
            attrs[SemanticConventions.K8S_CONTAINER_NAME] = container_name
        if deployment_name:
            attrs[SemanticConventions.K8S_DEPLOYMENT_NAME] = deployment_name
        if node_name:
            attrs[SemanticConventions.K8S_NODE_NAME] = node_name

        return attrs

    @staticmethod
    def get_genai_span_attributes(
        system: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        temperature: float = None,
        max_tokens: int = None
    ) -> dict[str, Any]:
        """Get GenAI span attributes following semantic conventions.

        Args:
            system: GenAI system (openai, anthropic, etc.)
            model: Model name
            input_tokens: Input token count
            output_tokens: Output token count
            temperature: Sampling temperature (optional)
            max_tokens: Max tokens (optional)

        Returns:
            Dictionary of GenAI semantic convention attributes
        """
        attrs = {
            SemanticConventions.GENAI_SYSTEM: system,
            SemanticConventions.GENAI_REQUEST_MODEL: model,
            SemanticConventions.GENAI_USAGE_INPUT_TOKENS: input_tokens,
            SemanticConventions.GENAI_USAGE_OUTPUT_TOKENS: output_tokens,
            SemanticConventions.GENAI_USAGE_TOTAL_TOKENS: input_tokens + output_tokens,
        }

        if temperature is not None:
            attrs[SemanticConventions.GENAI_REQUEST_TEMPERATURE] = temperature
        if max_tokens is not None:
            attrs[SemanticConventions.GENAI_REQUEST_MAX_TOKENS] = max_tokens

        return attrs
