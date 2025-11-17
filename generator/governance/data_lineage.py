"""Data lineage tracking and visualization.

Tracks data flow through systems and generates lineage graphs
showing transformations, dependencies, and impact analysis.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from enum import Enum

from generator.core.utils import generate_uuid, timestamp_to_iso


class DatasetType(Enum):
    """Types of datasets."""
    RAW = "raw"
    STAGING = "staging"
    PROCESSED = "processed"
    ANALYTICS = "analytics"
    ARCHIVE = "archive"


@dataclass
class DatasetNode:
    """Represents a dataset in the lineage graph."""

    dataset_id: str
    name: str
    dataset_type: DatasetType
    schema: dict[str, str]  # column_name -> data_type
    owner: str
    tags: list[str] = field(default_factory=list)
    sensitivity: str = "public"  # public, internal, confidential, restricted
    created_at: datetime = field(default_factory=datetime.utcnow)
    row_count: int = 0
    size_bytes: int = 0


@dataclass
class Transformation:
    """Represents a data transformation."""

    transformation_id: str
    name: str
    source_datasets: list[str]
    target_dataset: str
    transformation_type: str  # sql, spark, airflow, dbt
    code: Optional[str] = None
    executed_at: datetime = field(default_factory=datetime.utcnow)
    duration_seconds: float = 0
    rows_processed: int = 0


class DataLineageTracker:
    """Track and visualize data lineage."""

    def __init__(self):
        """Initialize lineage tracker."""
        self.datasets: dict[str, DatasetNode] = {}
        self.transformations: list[Transformation] = []

    def register_dataset(
        self,
        name: str,
        dataset_type: DatasetType,
        schema: dict[str, str],
        owner: str,
        sensitivity: str = "internal",
        tags: list[str] = None
    ) -> str:
        """Register a dataset.

        Args:
            name: Dataset name
            dataset_type: Type of dataset
            schema: Column schema
            owner: Dataset owner
            sensitivity: Data sensitivity level
            tags: Dataset tags

        Returns:
            Dataset ID
        """
        dataset_id = generate_uuid()

        dataset = DatasetNode(
            dataset_id=dataset_id,
            name=name,
            dataset_type=dataset_type,
            schema=schema,
            owner=owner,
            sensitivity=sensitivity,
            tags=tags or []
        )

        self.datasets[dataset_id] = dataset
        return dataset_id

    def record_transformation(
        self,
        name: str,
        source_dataset_ids: list[str],
        target_dataset_id: str,
        transformation_type: str,
        code: str = None,
        duration_seconds: float = 0,
        rows_processed: int = 0
    ) -> str:
        """Record a data transformation.

        Args:
            name: Transformation name
            source_dataset_ids: Source dataset IDs
            target_dataset_id: Target dataset ID
            transformation_type: Type of transformation
            code: Transformation code (optional)
            duration_seconds: Execution duration
            rows_processed: Number of rows processed

        Returns:
            Transformation ID
        """
        transformation_id = generate_uuid()

        transformation = Transformation(
            transformation_id=transformation_id,
            name=name,
            source_datasets=source_dataset_ids,
            target_dataset=target_dataset_id,
            transformation_type=transformation_type,
            code=code,
            duration_seconds=duration_seconds,
            rows_processed=rows_processed
        )

        self.transformations.append(transformation)
        return transformation_id

    def get_upstream_datasets(self, dataset_id: str) -> list[DatasetNode]:
        """Get all upstream datasets (dependencies).

        Args:
            dataset_id: Dataset ID

        Returns:
            List of upstream datasets
        """
        upstream_ids = set()

        # Find transformations that produce this dataset
        for transform in self.transformations:
            if transform.target_dataset == dataset_id:
                upstream_ids.update(transform.source_datasets)

        # Recursively find upstream datasets
        all_upstream_ids = set(upstream_ids)
        for upstream_id in upstream_ids:
            all_upstream_ids.update(
                ds.dataset_id for ds in self.get_upstream_datasets(upstream_id)
            )

        return [self.datasets[ds_id] for ds_id in all_upstream_ids if ds_id in self.datasets]

    def get_downstream_datasets(self, dataset_id: str) -> list[DatasetNode]:
        """Get all downstream datasets (consumers).

        Args:
            dataset_id: Dataset ID

        Returns:
            List of downstream datasets
        """
        downstream_ids = set()

        # Find transformations that consume this dataset
        for transform in self.transformations:
            if dataset_id in transform.source_datasets:
                downstream_ids.add(transform.target_dataset)

        # Recursively find downstream datasets
        all_downstream_ids = set(downstream_ids)
        for downstream_id in downstream_ids:
            all_downstream_ids.update(
                ds.dataset_id for ds in self.get_downstream_datasets(downstream_id)
            )

        return [self.datasets[ds_id] for ds_id in all_downstream_ids if ds_id in self.datasets]

    def get_column_lineage(
        self,
        dataset_id: str,
        column_name: str
    ) -> list[dict[str, Any]]:
        """Get column-level lineage.

        Args:
            dataset_id: Dataset ID
            column_name: Column name

        Returns:
            Column lineage path
        """
        lineage = []

        # Find transformations that create this dataset
        for transform in self.transformations:
            if transform.target_dataset == dataset_id:
                # Simplified: assume same column names in source
                for source_id in transform.source_datasets:
                    if source_id in self.datasets:
                        source_dataset = self.datasets[source_id]
                        if column_name in source_dataset.schema:
                            lineage.append({
                                "dataset": source_dataset.name,
                                "column": column_name,
                                "transformation": transform.name,
                                "type": source_dataset.schema[column_name]
                            })

        return lineage

    def analyze_impact(self, dataset_id: str) -> dict[str, Any]:
        """Analyze impact of changes to a dataset.

        Args:
            dataset_id: Dataset ID

        Returns:
            Impact analysis report
        """
        if dataset_id not in self.datasets:
            return {"error": "Dataset not found"}

        dataset = self.datasets[dataset_id]
        downstream = self.get_downstream_datasets(dataset_id)

        # Calculate impact score
        impact_score = len(downstream) * 10

        # Identify high-sensitivity downstream datasets
        sensitive_downstream = [
            ds for ds in downstream
            if ds.sensitivity in ["confidential", "restricted"]
        ]

        return {
            "dataset": dataset.name,
            "impact_score": impact_score,
            "affected_datasets": len(downstream),
            "affected_dataset_names": [ds.name for ds in downstream],
            "sensitive_downstream": len(sensitive_downstream),
            "sensitive_dataset_names": [ds.name for ds in sensitive_downstream],
            "recommendation": self._get_recommendation(impact_score, len(sensitive_downstream))
        }

    def _get_recommendation(self, impact_score: int, sensitive_count: int) -> str:
        """Get recommendation based on impact."""
        if impact_score > 100 or sensitive_count > 0:
            return "High impact - require approval and testing before changes"
        elif impact_score > 50:
            return "Medium impact - recommend testing in staging"
        else:
            return "Low impact - safe to proceed with standard review"

    def export_lineage_graph(self) -> dict[str, Any]:
        """Export lineage as graph structure.

        Returns:
            Lineage graph in JSON format
        """
        nodes = []
        edges = []

        # Export datasets as nodes
        for dataset in self.datasets.values():
            nodes.append({
                "id": dataset.dataset_id,
                "name": dataset.name,
                "type": dataset.dataset_type.value,
                "owner": dataset.owner,
                "sensitivity": dataset.sensitivity,
                "tags": dataset.tags,
                "schema": dataset.schema
            })

        # Export transformations as edges
        for transform in self.transformations:
            for source_id in transform.source_datasets:
                edges.append({
                    "source": source_id,
                    "target": transform.target_dataset,
                    "transformation": transform.name,
                    "type": transform.transformation_type,
                    "executed_at": timestamp_to_iso(transform.executed_at)
                })

        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "total_datasets": len(self.datasets),
                "total_transformations": len(self.transformations),
                "generated_at": timestamp_to_iso(datetime.utcnow())
            }
        }
