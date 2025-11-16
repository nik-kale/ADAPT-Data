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


def init_project(project_path: Path, force: bool = False) -> int:
    """Initialize a new ADAPT-Data project.

    Creates the project structure with:
    - .adapt-data.yaml configuration file
    - scenarios/ directory
    - output/ directory
    - plugins/ directory
    - Example scenario file

    Args:
        project_path: Path to project directory
        force: Overwrite existing files

    Returns:
        Exit code (0 = success, 1 = error)
    """
    # Convert to absolute path
    project_path = project_path.resolve()

    logger.info(f"Initializing ADAPT-Data project at: {project_path}")
    logger.info("")

    # Create project directory if it doesn't exist
    if not project_path.exists():
        try:
            project_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"✓ Created project directory: {project_path}")
        except Exception as e:
            logger.error(f"Failed to create project directory: {e}")
            return 1
    else:
        logger.info(f"✓ Using existing directory: {project_path}")

    # Check if .adapt-data.yaml already exists
    config_file = project_path / ".adapt-data.yaml"
    if config_file.exists() and not force:
        logger.info(f"  .adapt-data.yaml already exists (use --force to overwrite)")
    else:
        # Copy default config from ADAPT-Data installation
        source_config = Path(__file__).parent.parent / ".adapt-data.yaml"
        if source_config.exists():
            try:
                shutil.copy2(source_config, config_file)
                logger.info(f"✓ Created .adapt-data.yaml")
            except Exception as e:
                logger.error(f"Failed to create config file: {e}")
                return 1
        else:
            logger.warning(f"Source config not found at {source_config}")

    # Create directories
    directories = ["scenarios", "output", "plugins"]
    for dir_name in directories:
        dir_path = project_path / dir_name
        if not dir_path.exists():
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"✓ Created {dir_name}/ directory")
            except Exception as e:
                logger.error(f"Failed to create {dir_name}/ directory: {e}")
                return 1
        else:
            logger.info(f"  {dir_name}/ directory already exists")

    # Create example scenario file
    example_scenario = project_path / "scenarios" / "example_latency.yaml"
    if example_scenario.exists() and not force:
        logger.info(f"  example_latency.yaml already exists (use --force to overwrite)")
    else:
        example_content = """type: latency_regression
description: Example latency regression scenario - Database query slowdown

parameters:
  affected_service: api-service
  baseline_latency_ms: 50.0
  degraded_latency_ms: 500.0
  error_threshold_ms: 1000.0

metadata:
  category: performance
  common_causes:
    - Inefficient database query
    - Missing database index
    - N+1 query problem
    - Increased data volume
  detection_signals:
    - p95 latency spike
    - Slow query logs
    - Database CPU increase
  mitigation_strategies:
    - Rollback deployment
    - Add database index
    - Optimize query
    - Scale database
"""
        try:
            with open(example_scenario, 'w') as f:
                f.write(example_content)
            logger.info(f"✓ Created example scenario: scenarios/example_latency.yaml")
        except Exception as e:
            logger.error(f"Failed to create example scenario: {e}")
            return 1

    # Create README in plugins directory
    plugins_readme = project_path / "plugins" / "README.md"
    if not plugins_readme.exists() or force:
        readme_content = """# Custom Plugins

Place your custom ADAPT-Data plugins in this directory.

## Plugin Types

- **Generators**: Custom incident scenario generators
- **Exporters**: Custom export format handlers
- **Analyzers**: Custom dataset analysis tools

## Structure

```
plugins/
├── my_generator.py
├── my_exporter.py
└── my_analyzer.py
```

See the ADAPT-Data documentation for plugin development guide.
"""
        try:
            with open(plugins_readme, 'w') as f:
                f.write(readme_content)
            logger.info(f"✓ Created plugins/README.md")
        except Exception as e:
            logger.warning(f"Failed to create plugins README: {e}")

    # Success message with next steps
    logger.info("")
    logger.info("✓ Project initialization complete!")
    logger.info("")
    logger.info("Next steps:")
    logger.info("  1. Edit .adapt-data.yaml to customize configuration")
    logger.info("  2. Review the example scenario: scenarios/example_latency.yaml")
    logger.info("  3. Generate your first dataset:")
    logger.info(f"     adapt-data generate --scenario example_latency --output {project_path}/output")
    logger.info("")

    return 0
