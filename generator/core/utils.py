"""Utility functions for data generation."""

import random
import string
import uuid
from datetime import datetime, timedelta
from typing import Optional


def generate_id(prefix: str = "", length: int = 16) -> str:
    """Generate a random identifier.

    Args:
        prefix: Optional prefix for the ID
        length: Length of the random part

    Returns:
        Generated identifier string
    """
    random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    return f"{prefix}{random_part}" if prefix else random_part


def generate_uuid() -> str:
    """Generate a UUID v4.

    Returns:
        UUID string
    """
    return str(uuid.uuid4())


def timestamp_to_iso(dt: datetime) -> str:
    """Convert datetime to ISO 8601 string.

    Args:
        dt: Datetime object

    Returns:
        ISO 8601 formatted string
    """
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def parse_duration(duration_str: str) -> timedelta:
    """Parse a duration string like '5m', '2h', '30s'.

    Args:
        duration_str: Duration string

    Returns:
        timedelta object
    """
    units = {
        's': 'seconds',
        'm': 'minutes',
        'h': 'hours',
        'd': 'days',
    }

    unit = duration_str[-1]
    if unit not in units:
        raise ValueError(f"Unknown duration unit: {unit}")

    value = int(duration_str[:-1])
    return timedelta(**{units[unit]: value})


def random_choice_weighted(choices: list[tuple[str, float]]) -> str:
    """Choose randomly from weighted choices.

    Args:
        choices: List of (value, weight) tuples

    Returns:
        Selected value
    """
    values, weights = zip(*choices)
    return random.choices(values, weights=weights, k=1)[0]


def jitter(value: float, percent: float = 0.1) -> float:
    """Add random jitter to a value.

    Args:
        value: Base value
        percent: Jitter percentage (default 10%)

    Returns:
        Value with jitter applied
    """
    jitter_amount = value * percent
    return value + random.uniform(-jitter_amount, jitter_amount)


def exponential_backoff(
    base_value: float,
    iteration: int,
    max_value: Optional[float] = None,
    jitter_percent: float = 0.2
) -> float:
    """Calculate exponential backoff with jitter.

    Args:
        base_value: Base value
        iteration: Current iteration (0-indexed)
        max_value: Optional maximum value cap
        jitter_percent: Jitter percentage to apply

    Returns:
        Backoff value
    """
    value = base_value * (2 ** iteration)
    if max_value:
        value = min(value, max_value)
    return jitter(value, jitter_percent)


def gaussian_noise(mean: float, stddev: float) -> float:
    """Generate Gaussian noise.

    Args:
        mean: Mean value
        stddev: Standard deviation

    Returns:
        Random value from Gaussian distribution
    """
    return random.gauss(mean, stddev)


def spike_pattern(
    baseline: float,
    spike_multiplier: float,
    current_time: datetime,
    spike_start: datetime,
    spike_duration: timedelta
) -> float:
    """Generate a spike pattern value.

    Args:
        baseline: Baseline value
        spike_multiplier: Multiplier during spike
        current_time: Current timestamp
        spike_start: When spike starts
        spike_duration: How long spike lasts

    Returns:
        Value (baseline or spiked)
    """
    spike_end = spike_start + spike_duration

    if spike_start <= current_time <= spike_end:
        # Gradual ramp up/down at edges
        spike_progress = (current_time - spike_start) / spike_duration

        if spike_progress < 0.1:  # Ramp up
            multiplier = 1 + (spike_multiplier - 1) * (spike_progress / 0.1)
        elif spike_progress > 0.9:  # Ramp down
            multiplier = 1 + (spike_multiplier - 1) * ((1 - spike_progress) / 0.1)
        else:  # Full spike
            multiplier = spike_multiplier

        return baseline * multiplier

    return baseline
