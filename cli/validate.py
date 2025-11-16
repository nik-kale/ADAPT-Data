"""Validate dataset command implementation."""

import json
import sys
from pathlib import Path
from typing import Any

import jsonschema


def load_schema(schema_name: str) -> dict[str, Any]:
    """Load JSON schema.

    Args:
        schema_name: Schema filename

    Returns:
        Schema dictionary
    """
    schema_path = Path(__file__).parent.parent / "schema" / schema_name
    with open(schema_path, 'r') as f:
        return json.load(f)


def validate_jsonl_file(file_path: Path, schema: dict[str, Any], strict: bool) -> tuple[int, int]:
    """Validate a JSONL file against schema.

    Args:
        file_path: Path to JSONL file
        schema: JSON schema
        strict: Enable strict validation

    Returns:
        Tuple of (total_count, error_count)
    """
    total = 0
    errors = 0

    with open(file_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue

            total += 1
            try:
                record = json.loads(line)
                jsonschema.validate(instance=record, schema=schema)
            except json.JSONDecodeError as e:
                errors += 1
                print(f"  ✗ Line {line_num}: Invalid JSON - {e}")
                if strict:
                    raise
            except jsonschema.ValidationError as e:
                errors += 1
                print(f"  ✗ Line {line_num}: Schema validation failed - {e.message}")
                if strict:
                    raise

    return total, errors


def validate_json_file(file_path: Path, schema: dict[str, Any], strict: bool) -> bool:
    """Validate a JSON file against schema.

    Args:
        file_path: Path to JSON file
        schema: JSON schema
        strict: Enable strict validation

    Returns:
        True if valid, False otherwise
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        jsonschema.validate(instance=data, schema=schema)
        return True
    except json.JSONDecodeError as e:
        print(f"  ✗ Invalid JSON - {e}")
        if strict:
            raise
        return False
    except jsonschema.ValidationError as e:
        print(f"  ✗ Schema validation failed - {e.message}")
        if strict:
            raise
        return False


def validate_dataset(dataset_dir: Path, strict: bool = False) -> int:
    """Validate generated dataset.

    Args:
        dataset_dir: Directory containing dataset
        strict: Enable strict validation mode

    Returns:
        Exit code
    """
    if not dataset_dir.exists():
        print(f"Error: Dataset directory not found: {dataset_dir}")
        return 1

    print(f"Validating dataset: {dataset_dir}\n")

    total_errors = 0

    # Validate logs
    logs_dir = dataset_dir / "logs"
    if logs_dir.exists():
        print("Validating logs...")
        log_schema = load_schema("log_schema.json")
        for log_file in logs_dir.glob("*.jsonl"):
            total, errors = validate_jsonl_file(log_file, log_schema, strict)
            if errors == 0:
                print(f"  ✓ {log_file.name}: {total} records valid")
            else:
                print(f"  ✗ {log_file.name}: {errors}/{total} records invalid")
                total_errors += errors

    # Validate metrics
    metrics_dir = dataset_dir / "metrics"
    if metrics_dir.exists():
        print("\nValidating metrics...")
        metric_schema = load_schema("metric_schema.json")
        for metric_file in metrics_dir.glob("*.jsonl"):
            total, errors = validate_jsonl_file(metric_file, metric_schema, strict)
            if errors == 0:
                print(f"  ✓ {metric_file.name}: {total} records valid")
            else:
                print(f"  ✗ {metric_file.name}: {errors}/{total} records invalid")
                total_errors += errors

    # Validate traces
    traces_dir = dataset_dir / "traces"
    if traces_dir.exists():
        print("\nValidating traces...")
        trace_schema = load_schema("trace_schema.json")
        for trace_file in traces_dir.glob("*.jsonl"):
            total, errors = validate_jsonl_file(trace_file, trace_schema, strict)
            if errors == 0:
                print(f"  ✓ {trace_file.name}: {total} records valid")
            else:
                print(f"  ✗ {trace_file.name}: {errors}/{total} records invalid")
                total_errors += errors

    # Validate config deltas
    config_dir = dataset_dir / "config_deltas"
    if config_dir.exists():
        print("\nValidating config deltas...")
        config_schema = load_schema("config_delta_schema.json")
        for config_file in config_dir.glob("*.jsonl"):
            total, errors = validate_jsonl_file(config_file, config_schema, strict)
            if errors == 0:
                print(f"  ✓ {config_file.name}: {total} records valid")
            else:
                print(f"  ✗ {config_file.name}: {errors}/{total} records invalid")
                total_errors += errors

    # Validate timelines
    timelines_dir = dataset_dir / "timelines"
    if timelines_dir.exists():
        print("\nValidating timelines...")
        timeline_schema = load_schema("timeline_schema.json")
        for timeline_file in timelines_dir.glob("*.json"):
            if validate_json_file(timeline_file, timeline_schema, strict):
                print(f"  ✓ {timeline_file.name}: valid")
            else:
                print(f"  ✗ {timeline_file.name}: invalid")
                total_errors += 1

    # Validate topology
    topology_dir = dataset_dir / "topology"
    if topology_dir.exists():
        print("\nValidating topology...")
        topology_schema = load_schema("topology_schema.json")
        for topology_file in topology_dir.glob("*.json"):
            if validate_json_file(topology_file, topology_schema, strict):
                print(f"  ✓ {topology_file.name}: valid")
            else:
                print(f"  ✗ {topology_file.name}: invalid")
                total_errors += 1

    # Summary
    print(f"\n{'='*60}")
    if total_errors == 0:
        print("✓ All files validated successfully!")
        return 0
    else:
        print(f"✗ Validation failed with {total_errors} error(s)")
        return 1
