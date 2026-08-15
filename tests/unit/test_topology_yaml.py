"""Tests for YAML-defined custom topologies."""

from pathlib import Path

import pytest
import yaml

from generator.core.topology import (
    TopologyGenerator,
    TopologyValidationError,
    find_topology_file,
    load_topology_file,
    validate_topology,
)

BUNDLED_TOPOLOGY_DIR = Path(__file__).parent.parent.parent / "topology"


def write_topology(tmp_path: Path, data: dict) -> Path:
    """Write a topology mapping to a temporary YAML file."""
    path = tmp_path / "topology.yaml"
    with open(path, "w") as f:
        yaml.dump(data, f)
    return path


MINIMAL = {
    "name": "minimal",
    "services": [
        {"name": "api", "type": "api", "instances": 2},
        {"name": "db", "type": "database", "instances": 1},
    ],
    "dependencies": [{"from": "api", "to": "db", "type": "database", "critical": True}],
}


class TestValidateTopology:
    """Test topology structural validation."""

    def test_accepts_valid_topology(self):
        """A well-formed topology passes."""
        validate_topology(MINIMAL)

    def test_rejects_empty_services(self):
        """A topology needs at least one service."""
        with pytest.raises(TopologyValidationError, match="services"):
            validate_topology({"services": [], "dependencies": []})

    def test_rejects_duplicate_service_names(self):
        """Service names must be unique."""
        topology = {
            "services": [
                {"name": "api", "type": "api"},
                {"name": "api", "type": "worker"},
            ],
            "dependencies": [],
        }
        with pytest.raises(TopologyValidationError, match="Duplicate"):
            validate_topology(topology)

    def test_rejects_unknown_service_type(self):
        """Service types are constrained to the documented set."""
        topology = {"services": [{"name": "api", "type": "quantum"}], "dependencies": []}
        with pytest.raises(TopologyValidationError, match="invalid type"):
            validate_topology(topology)

    def test_rejects_missing_service_name(self):
        """A service without a name cannot be referenced."""
        topology = {"services": [{"type": "api"}], "dependencies": []}
        with pytest.raises(TopologyValidationError, match="name"):
            validate_topology(topology)

    @pytest.mark.parametrize("instances", [0, -1, 1.5, "two", True])
    def test_rejects_invalid_instance_counts(self, instances):
        """Instance counts must be integers of at least one."""
        topology = {
            "services": [{"name": "api", "type": "api", "instances": instances}],
            "dependencies": [],
        }
        with pytest.raises(TopologyValidationError, match="instances"):
            validate_topology(topology)

    def test_rejects_dependency_on_undefined_service(self):
        """Edges must point at services that exist."""
        topology = {
            "services": [{"name": "api", "type": "api"}],
            "dependencies": [{"from": "api", "to": "ghost"}],
        }
        with pytest.raises(TopologyValidationError, match="ghost"):
            validate_topology(topology)

    def test_rejects_unknown_dependency_type(self):
        """Dependency types are constrained to the documented set."""
        topology = {
            "services": [
                {"name": "api", "type": "api"},
                {"name": "db", "type": "database"},
            ],
            "dependencies": [{"from": "api", "to": "db", "type": "carrier-pigeon"}],
        }
        with pytest.raises(TopologyValidationError, match="invalid type"):
            validate_topology(topology)


class TestLoadTopologyFile:
    """Test loading topologies from disk."""

    def test_loads_services_and_dependencies(self, tmp_path):
        """A valid file yields its services and edges."""
        services, dependencies = load_topology_file(write_topology(tmp_path, MINIMAL))

        assert [s["name"] for s in services] == ["api", "db"]
        assert dependencies == MINIMAL["dependencies"]

    def test_lifts_nested_dependencies_to_edges(self, tmp_path):
        """Per-service dependencies become top-level edges."""
        data = {
            "services": [
                {
                    "name": "api",
                    "type": "api",
                    "dependencies": [{"target": "db", "type": "database", "critical": True}],
                },
                {"name": "db", "type": "database"},
            ]
        }

        services, dependencies = load_topology_file(write_topology(tmp_path, data))

        assert dependencies == [{"from": "api", "to": "db", "type": "database", "critical": True}]
        # The nested key is consumed, not left on the service.
        assert "dependencies" not in services[0]

    def test_merges_nested_and_top_level_dependencies(self, tmp_path):
        """Both dependency forms can be used in one file."""
        data = {
            "services": [
                {
                    "name": "api",
                    "type": "api",
                    "dependencies": [{"target": "cache", "type": "cache"}],
                },
                {"name": "db", "type": "database"},
                {"name": "cache", "type": "cache"},
            ],
            "dependencies": [{"from": "api", "to": "db", "type": "database"}],
        }

        _, dependencies = load_topology_file(write_topology(tmp_path, data))

        assert len(dependencies) == 2
        assert {d["to"] for d in dependencies} == {"db", "cache"}

    def test_rejects_missing_file(self, tmp_path):
        """A missing file reports clearly."""
        with pytest.raises(TopologyValidationError, match="not found"):
            load_topology_file(tmp_path / "absent.yaml")

    def test_rejects_non_yaml_suffix(self, tmp_path):
        """Only YAML files are accepted."""
        path = tmp_path / "topology.json"
        path.write_text("{}")

        with pytest.raises(TopologyValidationError, match="must be YAML"):
            load_topology_file(path)

    def test_rejects_malformed_yaml(self, tmp_path):
        """Unparseable YAML reports as a topology error."""
        path = tmp_path / "topology.yaml"
        path.write_text("services: [unclosed")

        with pytest.raises(TopologyValidationError, match="Invalid YAML"):
            load_topology_file(path)

    def test_rejects_invalid_content(self, tmp_path):
        """Validation errors surface on load."""
        data = {"services": [{"name": "api", "type": "not-a-type"}]}

        with pytest.raises(TopologyValidationError, match="invalid type"):
            load_topology_file(write_topology(tmp_path, data))


class TestFindTopologyFile:
    """Test topology resolution by name or path."""

    def test_finds_bundled_topology_by_name(self):
        """Bundled topologies resolve by bare name."""
        assert find_topology_file("ecommerce") is not None

    def test_finds_topology_by_path(self, tmp_path):
        """A direct path resolves to itself."""
        path = write_topology(tmp_path, MINIMAL)

        assert find_topology_file(str(path)) == path

    def test_returns_none_for_unknown(self):
        """An unresolvable reference returns None rather than raising."""
        assert find_topology_file("no-such-topology") is None


class TestBundledTopologies:
    """The shipped topology files must stay valid."""

    @pytest.mark.parametrize(
        "topology_file",
        sorted(BUNDLED_TOPOLOGY_DIR.glob("*.yaml")),
        ids=lambda p: p.stem,
    )
    def test_bundled_topology_is_valid(self, topology_file):
        """Every bundled topology loads and validates."""
        services, dependencies = load_topology_file(topology_file)

        assert services
        assert dependencies


class TestTopologyGeneratorFromYaml:
    """Test wiring a loaded topology into the generator."""

    def test_generates_topology_from_file(self, sample_context, tmp_path):
        """Custom services and edges reach the generated topology."""
        generator = TopologyGenerator.from_yaml(sample_context, write_topology(tmp_path, MINIMAL))
        topology = generator.generate()

        assert [s["name"] for s in topology["services"]] == ["api", "db"]
        assert topology["dependencies"] == MINIMAL["dependencies"]

    def test_custom_dependencies_drive_graph_queries(self, sample_context, tmp_path):
        """Upstream/downstream lookups use the custom edges, not the defaults."""
        generator = TopologyGenerator.from_yaml(sample_context, write_topology(tmp_path, MINIMAL))

        assert generator.get_upstream_services("api") == ["db"]
        assert generator.get_downstream_services("db") == ["api"]

    def test_default_topology_still_used_without_file(self, sample_context):
        """Omitting a file keeps the built-in topology."""
        topology = TopologyGenerator(sample_context).generate()

        assert any(s["name"] == "api-gateway" for s in topology["services"])
