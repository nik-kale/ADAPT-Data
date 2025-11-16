# Contributing to ADAPT-Data

Thank you for your interest in contributing to ADAPT-Data! This document provides guidelines for contributing.

## Ways to Contribute

- 🐛 Report bugs
- 💡 Suggest new features or incident types
- 📝 Improve documentation
- 🔧 Submit bug fixes
- ✨ Add new incident generators
- 🧪 Add tests

## Getting Started

1. Fork the repository
2. Clone your fork:
```bash
git clone https://github.com/your-username/adapt-data.git
cd adapt-data
```

3. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
```

4. Install development dependencies:
```bash
pip install -e ".[dev]"
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/my-new-feature
# or
git checkout -b fix/my-bug-fix
```

### 2. Make Changes

- Write clean, readable code
- Follow existing code style
- Add type hints to all functions
- Include docstrings for public APIs

### 3. Format Code

```bash
# Format with black
black .

# Check types
mypy .

# Lint
ruff check .
```

### 4. Add Tests

```bash
# Run tests
pytest

# With coverage
pytest --cov=generator --cov=cli
```

### 5. Update Documentation

- Update README.md if needed
- Add/update docstrings
- Update relevant docs/ files

### 6. Commit Changes

Write clear commit messages:

```bash
git commit -m "Add support for custom metric generators"
```

### 7. Push and Create PR

```bash
git push origin feature/my-new-feature
```

Then create a Pull Request on GitHub.

## Adding a New Incident Type

To add a new incident generator:

### 1. Create Generator File

`generator/incidents/my_incident.py`:

```python
"""My custom incident generator."""

from typing import Any
from generator.core.base import BaseGenerator, IncidentContext
from generator.core.timeline import TimelineGenerator

class MyIncidentGenerator(BaseGenerator):
    """Generates my custom incident type."""

    def __init__(self, context: IncidentContext, my_param: str) -> None:
        super().__init__(context)
        self.my_param = my_param
        context.affected_services = ["my-service"]
        context.root_cause = "My incident root cause"

    def generate(self) -> dict[str, Any]:
        """Generate complete incident dataset."""
        logs = self._generate_logs()
        metrics = self._generate_metrics()
        # ... etc

        return {
            "incident_id": self.context.incident_id,
            "incident_type": "my_incident",
            # ... summary
        }

    def _generate_logs(self) -> list[dict[str, Any]]:
        # Implementation
        pass

    # ... other methods
```

### 2. Register Generator

In `cli/generate.py`:

```python
GENERATOR_MAP = {
    # ...
    "my_incident": MyIncidentGenerator,
}
```

### 3. Create Scenario Template

`scenarios/my_incident.yaml`:

```yaml
type: my_incident
description: My custom incident type

parameters:
  my_param: value

metadata:
  category: performance  # or availability, network, etc.
  common_causes:
    - Cause 1
    - Cause 2
```

### 4. Add Tests

`tests/test_my_incident.py`:

```python
def test_my_incident_generation():
    context = IncidentContext(...)
    generator = MyIncidentGenerator(context, my_param="test")
    result = generator.generate()
    assert result["incident_type"] == "my_incident"
```

### 5. Update Documentation

Add to README.md and docs/architecture.md.

## Code Style Guidelines

### Python

- Follow PEP 8
- Use type hints
- Max line length: 100 characters
- Use docstrings (Google style)

### Example:

```python
def generate_metric(
    timestamp: datetime,
    service: str,
    value: float
) -> dict[str, Any]:
    """Generate a metric data point.

    Args:
        timestamp: Metric timestamp
        service: Service name
        value: Metric value

    Returns:
        Metric dictionary conforming to schema
    """
    return {
        "timestamp": timestamp_to_iso(timestamp),
        "service": service,
        "value": value
    }
```

## Testing Guidelines

- Write tests for all new functionality
- Aim for >80% code coverage
- Use descriptive test names
- Test edge cases and error conditions

## Documentation Guidelines

- Update README.md for user-facing changes
- Update architecture.md for design changes
- Add/update docstrings for all public APIs
- Include code examples in documentation

## Pull Request Process

1. Ensure all tests pass
2. Update documentation
3. Add entry to CHANGELOG (if exists)
4. Request review from maintainers
5. Address review feedback
6. Wait for approval and merge

## Code Review Checklist

Reviewers will check:

- [ ] Code follows style guidelines
- [ ] Tests are included and passing
- [ ] Documentation is updated
- [ ] No breaking changes (or properly documented)
- [ ] Commits are clean and logical
- [ ] PR description explains changes

## Questions?

- Open an issue for discussion
- Reach out to maintainers
- Check existing issues and PRs

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

Thank you for contributing to ADAPT-Data! 🎉
