"""Logging configuration for ADAPT-Data.

This module provides centralized logging for all ADAPT-Data components.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


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
    """Formatter that outputs logs as structured JSON.

    Outputs each log record as a single-line JSON object with standard fields
    plus any custom attributes attached to the record.

    Example output:
    {
      "timestamp": "2025-12-26T10:30:45.123Z",
      "level": "INFO",
      "logger": "adapt_data.generator",
      "message": "Generating incident...",
      "function": "generate",
      "line": 42
    }
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON string representation of log record
        """
        # Build base log entry
        log_entry = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "function": record.funcName,
            "line": record.lineno
        }

        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }

        # Add any custom attributes (correlation_id, request_id, etc.)
        # Skip standard LogRecord attributes
        standard_attrs = {
            'name', 'msg', 'args', 'created', 'filename', 'funcName',
            'levelname', 'levelno', 'lineno', 'module', 'msecs',
            'message', 'pathname', 'process', 'processName',
            'relativeCreated', 'thread', 'threadName', 'exc_info',
            'exc_text', 'stack_info'
        }

        for key, value in record.__dict__.items():
            if key not in standard_attrs:
                log_entry[key] = value

        return json.dumps(log_entry)


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    enable_colors: bool = True,
    log_format: str = "text"
) -> logging.Logger:
    """Set up logging for ADAPT-Data.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
        enable_colors: Whether to use colored output for console (ignored if log_format is json)
        log_format: Output format - "text" for human-readable or "json" for structured JSON

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("adapt_data")
    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Choose formatter based on log_format
    if log_format.lower() == "json":
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
    logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)  # Always DEBUG for file

        # Use JSON format for file if requested, otherwise text
        if log_format.lower() == "json":
            file_format = StructuredJSONFormatter()
        else:
            file_format = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)

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
