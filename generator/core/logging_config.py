"""Logging configuration for ADAPT-Data.

This module provides centralized logging for all ADAPT-Data components.

Two output formats are supported: human-readable text for interactive use, and
structured JSON for CI pipelines and log aggregation systems that need to parse
the output.
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Attributes present on every LogRecord; anything else was added by the caller
# and belongs in the structured output.
_STANDARD_RECORD_FIELDS = frozenset(
    logging.LogRecord("", 0, "", 0, "", None, None).__dict__
) | {"message", "asctime", "taskName"}

VALID_LOG_FORMATS = ("text", "json")


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels."""

    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        if record.levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
            )
        return super().format(record)


class StructuredJSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects.

    Emits a stable set of fields on every line so downstream tooling can index
    them, plus any extra attributes attached via ``logger.info(..., extra={})``.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Serialize a log record as a JSON object.

        Args:
            record: Record to format

        Returns:
            JSON-encoded log line
        """
        entry = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Only useful for locating the emitting code; keep them out of the way
        # of the fields people actually query on.
        entry["source"] = {
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)

        if record.stack_info:
            entry["stack"] = self.formatStack(record.stack_info)

        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _STANDARD_RECORD_FIELDS
        }
        if extras:
            entry["context"] = extras

        return json.dumps(entry, default=str)


def _resolve_log_format(log_format: Optional[str]) -> str:
    """Resolve the effective log format.

    Precedence: explicit argument, then ``ADAPT_LOG_FORMAT``, then text.

    Args:
        log_format: Explicitly requested format, if any

    Returns:
        Either 'text' or 'json'
    """
    candidate = log_format or os.getenv("ADAPT_LOG_FORMAT") or "text"
    candidate = candidate.lower()

    if candidate not in VALID_LOG_FORMATS:
        # Logging is not configured yet, so warn on stderr rather than recursing.
        print(
            f"Warning: unknown log format '{candidate}', falling back to 'text'. "
            f"Valid formats: {', '.join(VALID_LOG_FORMATS)}",
            file=sys.stderr,
        )
        return "text"

    return candidate


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    enable_colors: bool = True,
    log_format: Optional[str] = None
) -> logging.Logger:
    """Set up logging for ADAPT-Data.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
        enable_colors: Whether to use colored output for console
        log_format: 'text' or 'json'. Defaults to the ADAPT_LOG_FORMAT
            environment variable, then 'text'. JSON output is never colored.

    Returns:
        Configured logger instance
    """
    resolved_format = _resolve_log_format(log_format)

    # Handlers go on the root logger, not on "adapt_data": modules call
    # get_logger(__name__) and so log under "generator.*" / "cli.*", which are
    # not children of "adapt_data" and would otherwise never reach a handler.
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()

    logger = logging.getLogger("adapt_data")
    logger.setLevel(level)
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    console_format: logging.Formatter
    if resolved_format == "json":
        console_format = StructuredJSONFormatter()
    elif enable_colors and sys.stdout.isatty():
        console_format = ColoredFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        console_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # Always DEBUG for file
        file_format: logging.Formatter
        if resolved_format == "json":
            file_format = StructuredJSONFormatter()
        else:
            file_format = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        file_handler.setFormatter(file_format)
        root_logger.addHandler(file_handler)

        # The file handler wants DEBUG records, so the root threshold must not
        # filter them out before they reach it.
        root_logger.setLevel(min(level, logging.DEBUG))

    return logger


def get_logger(name: str = "adapt_data") -> logging.Logger:
    """Get logger instance.

    Args:
        name: Logger name (typically __name__ from calling module)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Default logger setup
logger = setup_logging()
