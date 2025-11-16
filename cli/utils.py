"""Utility CLI commands."""

import platform
import shutil
import sys
from pathlib import Path
from typing import Optional

from generator.core.logging_config import get_logger

logger = get_logger(__name__)


def get_version() -> str:
    """Get ADAPT-Data version.

    Returns:
        Version string
    """
    # Read from pyproject.toml
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    if pyproject_path.exists():
        with open(pyproject_path) as f:
            for line in f:
                if line.startswith("version"):
                    return line.split("=")[1].strip().strip('"')
    return "unknown"


def print_version() -> None:
    """Print version information."""
    version = get_version()
    logger.info(f"ADAPT-Data version {version}")
    logger.info(f"Python {sys.version}")
    logger.info(f"Platform: {platform.platform()}")


def doctor(verbose: bool = False) -> int:
    """Run health checks on ADAPT-Data installation.

    Args:
        verbose: Print verbose output

    Returns:
        Exit code (0 = healthy, 1 = issues found)
    """
    logger.info("Running ADAPT-Data health checks...")
    logger.info("")

    issues = []

    # Check Python version
    py_version = sys.version_info
    if py_version < (3, 10):
        issues.append(f"Python version {py_version.major}.{py_version.minor} is too old (requires >=3.10)")
    else:
        logger.info(f"✓ Python version: {py_version.major}.{py_version.minor}.{py_version.micro}")

    # Check required dependencies
    required_deps = [
        ("yaml", "PyYAML"),
        ("jsonschema", "jsonschema"),
        ("numpy", "numpy"),
        ("pydantic", "pydantic"),
    ]

    for module_name, package_name in required_deps:
        try:
            __import__(module_name)
            logger.info(f"✓ {package_name} installed")
        except ImportError:
            issues.append(f"Required package '{package_name}' not installed")

    # Check optional dependencies
    if verbose:
        logger.info("")
        logger.info("Optional dependencies:")
        optional_deps = [
            ("prometheus_client", "prometheus-client"),
            ("kafka", "kafka-python"),
            ("rich", "rich"),
            ("textual", "textual"),
        ]

        for module_name, package_name in optional_deps:
            try:
                __import__(module_name)
                logger.info(f"  ✓ {package_name} installed")
            except ImportError:
                logger.info(f"  ○ {package_name} not installed (optional)")

    # Check schemas directory
    schema_dir = Path(__file__).parent.parent / "schema"
    if schema_dir.exists():
        schema_count = len(list(schema_dir.glob("*.json")))
        logger.info(f"✓ Found {schema_count} schema files")
    else:
        issues.append("Schema directory not found")

    # Check scenarios directory
    scenarios_dir = Path(__file__).parent.parent / "scenarios"
    if scenarios_dir.exists():
        scenario_count = len(list(scenarios_dir.glob("*.yaml")))
        logger.info(f"✓ Found {scenario_count} scenario files")
    else:
        logger.info("  ○ No scenarios directory (optional)")

    # Summary
    logger.info("")
    if issues:
        logger.error(f"✗ Found {len(issues)} issue(s):")
        for issue in issues:
            logger.error(f"  - {issue}")
        return 1
    else:
        logger.info("✓ All checks passed!")
        return 0


def clean(
    path: Path,
    dry_run: bool = False,
    force: bool = False
) -> int:
    """Clean generated datasets and temporary files.

    Args:
        path: Directory to clean
        dry_run: Show what would be deleted without deleting
        force: Don't ask for confirmation

    Returns:
        Exit code
    """
    if not path.exists():
        logger.error(f"Path does not exist: {path}")
        return 1

    # Find files to clean
    patterns_to_clean = [
        "*.jsonl",
        "*.json",
        "__pycache__",
        "*.pyc",
        "*.pyo",
        ".pytest_cache",
        ".coverage",
        "htmlcov",
    ]

    files_to_delete = []
    dirs_to_delete = []

    for pattern in patterns_to_clean:
        if "*" in pattern:
            files_to_delete.extend(path.rglob(pattern))
        else:
            # Directory patterns
            dirs_to_delete.extend([d for d in path.rglob(pattern) if d.is_dir()])

    total_size = sum(f.stat().st_size for f in files_to_delete if f.is_file())

    if not files_to_delete and not dirs_to_delete:
        logger.info("Nothing to clean")
        return 0

    # Show what will be deleted
    logger.info(f"Found {len(files_to_delete)} files and {len(dirs_to_delete)} directories to clean")
    logger.info(f"Total size: {total_size / 1024 / 1024:.2f} MB")

    if dry_run:
        logger.info("")
        logger.info("Dry run - would delete:")
        for f in files_to_delete[:10]:  # Show first 10
            logger.info(f"  {f}")
        if len(files_to_delete) > 10:
            logger.info(f"  ... and {len(files_to_delete) - 10} more")
        return 0

    # Confirm deletion
    if not force:
        response = input("\nProceed with deletion? [y/N]: ")
        if response.lower() != 'y':
            logger.info("Cancelled")
            return 0

    # Delete files
    deleted_count = 0
    for f in files_to_delete:
        try:
            f.unlink()
            deleted_count += 1
        except Exception as e:
            logger.error(f"Error deleting {f}: {e}")

    for d in dirs_to_delete:
        try:
            shutil.rmtree(d)
            deleted_count += 1
        except Exception as e:
            logger.error(f"Error deleting {d}: {e}")

    logger.info("")
    logger.info(f"✓ Deleted {deleted_count} items")
    return 0


def info(dataset_dir: Path) -> int:
    """Display quick information about a dataset.

    Args:
        dataset_dir: Path to dataset

    Returns:
        Exit code
    """
    if not dataset_dir.exists():
        logger.error(f"Dataset directory not found: {dataset_dir}")
        return 1

    logger.info(f"Dataset: {dataset_dir}")
    logger.info("")

    # Count files by type
    subdirs = ["logs", "metrics", "traces", "config_deltas", "timelines", "topology"]

    for subdir in subdirs:
        dir_path = dataset_dir / subdir
        if dir_path.exists():
            if subdir in ["timelines", "topology"]:
                file_count = len(list(dir_path.glob("*.json")))
            else:
                file_count = len(list(dir_path.glob("*.jsonl")))

            if file_count > 0:
                logger.info(f"  {subdir}: {file_count} file(s)")

    # Total size
    total_size = sum(
        f.stat().st_size
        for f in dataset_dir.rglob("*")
        if f.is_file()
    )
    logger.info("")
    logger.info(f"Total size: {total_size / 1024 / 1024:.2f} MB")

    return 0
