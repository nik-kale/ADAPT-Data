"""Parameterized probability distributions for realistic data generation.

This module provides various probability distributions that can be used
to generate more realistic telemetry data with configurable parameters.
"""

import random
from abc import ABC, abstractmethod
from typing import Any, Optional

import numpy as np


class Distribution(ABC):
    """Base class for probability distributions."""

    @abstractmethod
    def sample(self) -> float:
        """Sample a value from the distribution.

        Returns:
            Sampled value
        """
        pass

    def sample_int(self, min_val: int = 0, max_val: int = 100) -> int:
        """Sample an integer value.

        Args:
            min_val: Minimum value
            max_val: Maximum value

        Returns:
            Integer sample
        """
        return int(np.clip(self.sample(), min_val, max_val))


class UniformDistribution(Distribution):
    """Uniform distribution between min and max."""

    def __init__(self, min_val: float = 0.0, max_val: float = 1.0) -> None:
        """Initialize uniform distribution.

        Args:
            min_val: Minimum value
            max_val: Maximum value
        """
        self.min_val = min_val
        self.max_val = max_val

    def sample(self) -> float:
        """Sample from uniform distribution."""
        return random.uniform(self.min_val, self.max_val)


class NormalDistribution(Distribution):
    """Normal (Gaussian) distribution."""

    def __init__(self, mean: float = 0.0, std: float = 1.0) -> None:
        """Initialize normal distribution.

        Args:
            mean: Mean value
            std: Standard deviation
        """
        self.mean = mean
        self.std = std

    def sample(self) -> float:
        """Sample from normal distribution."""
        return random.gauss(self.mean, self.std)


class ExponentialDistribution(Distribution):
    """Exponential distribution for modeling time between events."""

    def __init__(self, rate: float = 1.0) -> None:
        """Initialize exponential distribution.

        Args:
            rate: Rate parameter (lambda)
        """
        self.rate = rate

    def sample(self) -> float:
        """Sample from exponential distribution."""
        return random.expovariate(self.rate)


class LogNormalDistribution(Distribution):
    """Log-normal distribution for modeling multiplicative processes."""

    def __init__(self, mu: float = 0.0, sigma: float = 1.0) -> None:
        """Initialize log-normal distribution.

        Args:
            mu: Mean of underlying normal distribution
            sigma: Standard deviation of underlying normal distribution
        """
        self.mu = mu
        self.sigma = sigma

    def sample(self) -> float:
        """Sample from log-normal distribution."""
        return random.lognormvariate(self.mu, self.sigma)


class PoissonDistribution(Distribution):
    """Poisson distribution for modeling count data."""

    def __init__(self, lambda_: float = 1.0) -> None:
        """Initialize Poisson distribution.

        Args:
            lambda_: Rate parameter
        """
        self.lambda_ = lambda_

    def sample(self) -> float:
        """Sample from Poisson distribution."""
        return float(np.random.poisson(self.lambda_))


class WeibullDistribution(Distribution):
    """Weibull distribution for modeling failure rates."""

    def __init__(self, shape: float = 1.0, scale: float = 1.0) -> None:
        """Initialize Weibull distribution.

        Args:
            shape: Shape parameter (k)
            scale: Scale parameter (lambda)
        """
        self.shape = shape
        self.scale = scale

    def sample(self) -> float:
        """Sample from Weibull distribution."""
        return random.weibullvariate(self.scale, self.shape)


class BimodalDistribution(Distribution):
    """Bimodal distribution combining two normal distributions."""

    def __init__(
        self,
        mean1: float = 0.0,
        std1: float = 1.0,
        mean2: float = 5.0,
        std2: float = 1.0,
        mix: float = 0.5
    ) -> None:
        """Initialize bimodal distribution.

        Args:
            mean1: Mean of first mode
            std1: Std of first mode
            mean2: Mean of second mode
            std2: Std of second mode
            mix: Mixing proportion for first mode (0-1)
        """
        self.dist1 = NormalDistribution(mean1, std1)
        self.dist2 = NormalDistribution(mean2, std2)
        self.mix = mix

    def sample(self) -> float:
        """Sample from bimodal distribution."""
        if random.random() < self.mix:
            return self.dist1.sample()
        return self.dist2.sample()


class DistributionFactory:
    """Factory for creating distributions from configuration."""

    @staticmethod
    def create(config: dict[str, Any]) -> Distribution:
        """Create distribution from configuration.

        Args:
            config: Distribution configuration with 'type' and parameters

        Returns:
            Distribution instance

        Raises:
            ValueError: If distribution type is unknown

        Example:
            >>> config = {'type': 'normal', 'mean': 100, 'std': 15}
            >>> dist = DistributionFactory.create(config)
            >>> value = dist.sample()
        """
        dist_type = config.get('type', 'uniform').lower()

        if dist_type == 'uniform':
            return UniformDistribution(
                min_val=config.get('min', 0.0),
                max_val=config.get('max', 1.0)
            )
        elif dist_type == 'normal':
            return NormalDistribution(
                mean=config.get('mean', 0.0),
                std=config.get('std', 1.0)
            )
        elif dist_type == 'exponential':
            return ExponentialDistribution(
                rate=config.get('rate', 1.0)
            )
        elif dist_type == 'lognormal':
            return LogNormalDistribution(
                mu=config.get('mu', 0.0),
                sigma=config.get('sigma', 1.0)
            )
        elif dist_type == 'poisson':
            return PoissonDistribution(
                lambda_=config.get('lambda', 1.0)
            )
        elif dist_type == 'weibull':
            return WeibullDistribution(
                shape=config.get('shape', 1.0),
                scale=config.get('scale', 1.0)
            )
        elif dist_type == 'bimodal':
            return BimodalDistribution(
                mean1=config.get('mean1', 0.0),
                std1=config.get('std1', 1.0),
                mean2=config.get('mean2', 5.0),
                std2=config.get('std2', 1.0),
                mix=config.get('mix', 0.5)
            )
        else:
            raise ValueError(f"Unknown distribution type: {dist_type}")


# Predefined distributions for common use cases
LATENCY_DISTRIBUTION = LogNormalDistribution(mu=3.5, sigma=0.5)  # ~50ms typical
ERROR_RATE_DISTRIBUTION = ExponentialDistribution(rate=100)  # Low error rate
THROUGHPUT_DISTRIBUTION = NormalDistribution(mean=1000, std=100)  # Requests/sec
CPU_DISTRIBUTION = BimodalDistribution(mean1=20, std1=5, mean2=80, std2=10, mix=0.9)
MEMORY_DISTRIBUTION = NormalDistribution(mean=60, std=10)  # Percent
DISK_IO_DISTRIBUTION = WeibullDistribution(shape=1.5, scale=100)  # MB/s
