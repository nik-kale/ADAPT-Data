"""Tests for structured JSON logging."""

import json
import logging

import pytest

from generator.core.logging_config import (
    StructuredJSONFormatter,
    _resolve_log_format,
    get_logger,
    setup_logging,
)


def make_record(**overrides) -> logging.LogRecord:
    """Build a log record with sensible defaults."""
    defaults = {
        "name": "generator.core.test",
        "level": logging.INFO,
        "pathname": "/app/generator/core/test.py",
        "lineno": 42,
        "msg": "hello %s",
        "args": ("world",),
        "exc_info": None,
    }
    defaults.update(overrides)
    return logging.LogRecord(**defaults)


class TestStructuredJSONFormatter:
    """Test JSON log formatting."""

    def test_emits_valid_json(self):
        """Each line parses as a JSON object."""
        entry = json.loads(StructuredJSONFormatter().format(make_record()))

        assert isinstance(entry, dict)

    def test_includes_standard_fields(self):
        """Timestamp, level, logger and message are always present."""
        entry = json.loads(StructuredJSONFormatter().format(make_record()))

        assert entry["level"] == "INFO"
        assert entry["logger"] == "generator.core.test"
        assert entry["message"] == "hello world"
        assert entry["timestamp"].endswith("Z")

    def test_includes_source_location(self):
        """Source location aids debugging."""
        entry = json.loads(StructuredJSONFormatter().format(make_record()))

        assert entry["source"]["line"] == 42
        assert entry["source"]["module"] == "test"

    def test_includes_exception_text(self):
        """Exceptions are serialized into the entry."""
        try:
            raise ValueError("boom")
        except ValueError:
            import sys

            record = make_record(level=logging.ERROR, exc_info=sys.exc_info())

        entry = json.loads(StructuredJSONFormatter().format(record))

        assert "ValueError: boom" in entry["exception"]

    def test_includes_extra_context(self):
        """Fields passed via extra= land under 'context'."""
        record = make_record()
        record.incident_id = "abc-123"
        record.severity = "SEV1"

        entry = json.loads(StructuredJSONFormatter().format(record))

        assert entry["context"] == {"incident_id": "abc-123", "severity": "SEV1"}

    def test_omits_context_when_no_extras(self):
        """No 'context' key appears when nothing extra was attached."""
        entry = json.loads(StructuredJSONFormatter().format(make_record()))

        assert "context" not in entry

    def test_serializes_unencodable_values(self):
        """Values json cannot encode fall back to str()."""
        from datetime import datetime

        record = make_record()
        record.when = datetime(2025, 1, 15)

        entry = json.loads(StructuredJSONFormatter().format(record))

        assert entry["context"]["when"] == "2025-01-15 00:00:00"


class TestResolveLogFormat:
    """Test log format resolution and precedence."""

    def test_defaults_to_text(self, monkeypatch):
        """With nothing set, text wins."""
        monkeypatch.delenv("ADAPT_LOG_FORMAT", raising=False)

        assert _resolve_log_format(None) == "text"

    def test_explicit_argument_wins_over_env(self, monkeypatch):
        """An explicit request beats the environment."""
        monkeypatch.setenv("ADAPT_LOG_FORMAT", "json")

        assert _resolve_log_format("text") == "text"

    def test_reads_env_var(self, monkeypatch):
        """The environment is used when no argument is given."""
        monkeypatch.setenv("ADAPT_LOG_FORMAT", "json")

        assert _resolve_log_format(None) == "json"

    def test_is_case_insensitive(self, monkeypatch):
        """Casing does not matter."""
        monkeypatch.delenv("ADAPT_LOG_FORMAT", raising=False)

        assert _resolve_log_format("JSON") == "json"

    def test_falls_back_on_unknown_format(self, monkeypatch, capsys):
        """An unknown format warns and falls back rather than crashing."""
        monkeypatch.delenv("ADAPT_LOG_FORMAT", raising=False)

        assert _resolve_log_format("xml") == "text"
        assert "unknown log format" in capsys.readouterr().err


class TestSetupLogging:
    """Test handler configuration."""

    @pytest.fixture(autouse=True)
    def restore_logging(self):
        """Leave global logging state as it was found."""
        root = logging.getLogger()
        saved_handlers, saved_level = root.handlers[:], root.level
        yield
        root.handlers[:] = saved_handlers
        root.setLevel(saved_level)

    def test_module_loggers_reach_a_handler(self, capsys):
        """Records from generator.* / cli.* loggers are actually emitted.

        Handlers must land on the root logger: module loggers are named
        'generator.core.x', which is not a child of 'adapt_data'.
        """
        setup_logging(level=logging.INFO, log_format="text")

        get_logger("generator.core.somewhere").info("visible-info")

        assert "visible-info" in capsys.readouterr().out

    def test_json_format_produces_parseable_output(self, capsys):
        """JSON mode emits machine-readable lines."""
        setup_logging(level=logging.INFO, log_format="json")

        get_logger("cli.generate").info("structured")

        entry = json.loads(capsys.readouterr().out.strip())
        assert entry["message"] == "structured"
        assert entry["logger"] == "cli.generate"

    def test_repeated_setup_does_not_duplicate_handlers(self, capsys):
        """Reconfiguring replaces handlers instead of stacking them."""
        setup_logging(level=logging.INFO, log_format="text")
        setup_logging(level=logging.INFO, log_format="text")

        get_logger("generator.core.somewhere").info("once")

        assert capsys.readouterr().out.count("once") == 1

    def test_writes_json_to_log_file(self, tmp_path):
        """File output honours the JSON format too."""
        log_file = tmp_path / "adapt.log"
        setup_logging(level=logging.INFO, log_file=log_file, log_format="json")

        get_logger("generator.core.somewhere").info("to-file")

        for handler in logging.getLogger().handlers:
            handler.flush()

        entries = [json.loads(line) for line in log_file.read_text().splitlines() if line]
        assert any(e["message"] == "to-file" for e in entries)
