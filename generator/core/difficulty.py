"""Difficulty levels and adaptive complexity for incident generation.

This module provides difficulty levels that adjust the complexity of
generated incidents for training and challenge scenarios.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class DifficultyLevel(Enum):
    """Difficulty levels for incidents."""

    BEGINNER = "beginner"
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"

    @property
    def numeric_value(self) -> int:
        """Get numeric difficulty value (1-5)."""
        mapping = {
            DifficultyLevel.BEGINNER: 1,
            DifficultyLevel.EASY: 2,
            DifficultyLevel.MEDIUM: 3,
            DifficultyLevel.HARD: 4,
            DifficultyLevel.EXPERT: 5,
        }
        return mapping[self]

    @classmethod
    def from_string(cls, value: str) -> "DifficultyLevel":
        """Create difficulty level from string.

        Args:
            value: Difficulty level string

        Returns:
            DifficultyLevel enum

        Raises:
            ValueError: If invalid difficulty level
        """
        try:
            return cls(value.lower())
        except ValueError:
            raise ValueError(
                f"Invalid difficulty level: {value}. "
                f"Must be one of: {', '.join([d.value for d in cls])}"
            )


@dataclass
class DifficultyConfig:
    """Configuration parameters for a difficulty level."""

    level: DifficultyLevel
    num_services: int  # Number of services in topology
    num_incidents: int  # Number of incidents in cascade
    noise_level: float  # Amount of noise/red herrings (0-1)
    correlation_strength: float  # How obvious correlations are (0-1)
    hint_availability: int  # Number of hints available
    time_limit_minutes: Optional[int]  # Suggested time limit
    log_volume_multiplier: float  # Log entry multiplier
    metric_density: float  # Metrics per minute
    trace_complexity: int  # Average spans per trace

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "level": self.level.value,
            "num_services": self.num_services,
            "num_incidents": self.num_incidents,
            "noise_level": self.noise_level,
            "correlation_strength": self.correlation_strength,
            "hint_availability": self.hint_availability,
            "time_limit_minutes": self.time_limit_minutes,
            "log_volume_multiplier": self.log_volume_multiplier,
            "metric_density": self.metric_density,
            "trace_complexity": self.trace_complexity,
        }


# Predefined difficulty configurations
DIFFICULTY_CONFIGS = {
    DifficultyLevel.BEGINNER: DifficultyConfig(
        level=DifficultyLevel.BEGINNER,
        num_services=3,
        num_incidents=1,
        noise_level=0.1,
        correlation_strength=0.9,
        hint_availability=5,
        time_limit_minutes=15,
        log_volume_multiplier=0.5,
        metric_density=1.0,
        trace_complexity=2,
    ),
    DifficultyLevel.EASY: DifficultyConfig(
        level=DifficultyLevel.EASY,
        num_services=5,
        num_incidents=1,
        noise_level=0.2,
        correlation_strength=0.8,
        hint_availability=4,
        time_limit_minutes=20,
        log_volume_multiplier=0.7,
        metric_density=2.0,
        trace_complexity=3,
    ),
    DifficultyLevel.MEDIUM: DifficultyConfig(
        level=DifficultyLevel.MEDIUM,
        num_services=8,
        num_incidents=2,
        noise_level=0.3,
        correlation_strength=0.6,
        hint_availability=3,
        time_limit_minutes=30,
        log_volume_multiplier=1.0,
        metric_density=3.0,
        trace_complexity=4,
    ),
    DifficultyLevel.HARD: DifficultyConfig(
        level=DifficultyLevel.HARD,
        num_services=12,
        num_incidents=3,
        noise_level=0.5,
        correlation_strength=0.4,
        hint_availability=2,
        time_limit_minutes=45,
        log_volume_multiplier=1.5,
        metric_density=5.0,
        trace_complexity=6,
    ),
    DifficultyLevel.EXPERT: DifficultyConfig(
        level=DifficultyLevel.EXPERT,
        num_services=15,
        num_incidents=4,
        noise_level=0.7,
        correlation_strength=0.2,
        hint_availability=1,
        time_limit_minutes=60,
        log_volume_multiplier=2.0,
        metric_density=8.0,
        trace_complexity=8,
    ),
}


def get_difficulty_config(level: DifficultyLevel) -> DifficultyConfig:
    """Get configuration for a difficulty level.

    Args:
        level: Difficulty level

    Returns:
        Difficulty configuration
    """
    return DIFFICULTY_CONFIGS[level]


def calculate_score(
    difficulty: DifficultyLevel,
    time_taken_minutes: float,
    hints_used: int,
    correct: bool
) -> dict[str, Any]:
    """Calculate score for a challenge attempt.

    Args:
        difficulty: Challenge difficulty
        time_taken_minutes: Time taken in minutes
        hints_used: Number of hints used
        correct: Whether solution was correct

    Returns:
        Score breakdown dictionary
    """
    if not correct:
        return {
            "total_score": 0,
            "breakdown": {
                "base": 0,
                "time_bonus": 0,
                "hint_penalty": 0,
                "difficulty_multiplier": 0,
            },
            "rank": "Failed"
        }

    config = get_difficulty_config(difficulty)
    base_score = 100

    # Time bonus (up to 50% for finishing quickly)
    if config.time_limit_minutes:
        time_ratio = time_taken_minutes / config.time_limit_minutes
        if time_ratio < 0.5:
            time_bonus = 50
        elif time_ratio < 0.75:
            time_bonus = 25
        elif time_ratio <= 1.0:
            time_bonus = 10
        else:
            time_bonus = 0
    else:
        time_bonus = 0

    # Hint penalty (10 points per hint)
    hint_penalty = hints_used * 10

    # Difficulty multiplier
    difficulty_multiplier = difficulty.numeric_value

    # Calculate total
    total = (base_score + time_bonus - hint_penalty) * difficulty_multiplier

    # Determine rank
    if total >= 500:
        rank = "Master"
    elif total >= 400:
        rank = "Expert"
    elif total >= 300:
        rank = "Advanced"
    elif total >= 200:
        rank = "Proficient"
    elif total >= 100:
        rank = "Competent"
    else:
        rank = "Novice"

    return {
        "total_score": max(0, total),
        "breakdown": {
            "base": base_score,
            "time_bonus": time_bonus,
            "hint_penalty": -hint_penalty,
            "difficulty_multiplier": difficulty_multiplier,
        },
        "rank": rank
    }


def recommend_next_difficulty(
    current_difficulty: DifficultyLevel,
    score: int,
    time_ratio: float
) -> tuple[DifficultyLevel, str]:
    """Recommend next difficulty level based on performance.

    Args:
        current_difficulty: Current difficulty level
        score: Total score achieved
        time_ratio: Time taken / time limit

    Returns:
        Tuple of (recommended_difficulty, reason)
    """
    current_level = current_difficulty.numeric_value

    # Excellent performance: move up
    if score >= 400 and time_ratio < 0.75:
        if current_level < 5:
            next_difficulty = DifficultyLevel(
                list(DifficultyLevel)[current_level]
            )
            return next_difficulty, "Excellent performance! Ready for harder challenges."
        else:
            return current_difficulty, "Already at maximum difficulty. Keep practicing!"

    # Good performance: stay at current level or move up
    elif score >= 300:
        if time_ratio < 0.5 and current_level < 5:
            next_difficulty = DifficultyLevel(
                list(DifficultyLevel)[current_level]
            )
            return next_difficulty, "Good performance. Try the next level!"
        else:
            return current_difficulty, "Good job! Practice more at this level."

    # Struggling: move down or stay
    elif score < 200:
        if current_level > 1:
            next_difficulty = DifficultyLevel(
                list(DifficultyLevel)[current_level - 2]
            )
            return next_difficulty, "Try an easier level to build fundamentals."
        else:
            return current_difficulty, "Keep practicing at this level."

    # Average performance: stay at current level
    else:
        return current_difficulty, "Practice more at this level to improve."
