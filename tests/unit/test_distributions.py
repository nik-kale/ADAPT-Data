"""Comprehensive tests for the distributions module.

Tests all distribution classes, the factory pattern, and predefined distributions.
"""

import pytest
import numpy as np
from generator.core.distributions import (
    Distribution,
    UniformDistribution,
    NormalDistribution,
    ExponentialDistribution,
    LogNormalDistribution,
    PoissonDistribution,
    WeibullDistribution,
    BimodalDistribution,
    DistributionFactory,
    LATENCY_DISTRIBUTION,
    ERROR_RATE_DISTRIBUTION,
    THROUGHPUT_DISTRIBUTION,
    CPU_DISTRIBUTION,
    MEMORY_DISTRIBUTION,
    DISK_IO_DISTRIBUTION,
)


class TestUniformDistribution:
    """Test UniformDistribution class."""

    def test_sample_returns_number(self):
        """Test that sample() returns a numeric value."""
        dist = UniformDistribution(min_val=0.0, max_val=10.0)
        sample = dist.sample()
        assert isinstance(sample, (int, float))

    def test_sample_within_range(self):
        """Test that samples are within the specified range."""
        dist = UniformDistribution(min_val=5.0, max_val=15.0)
        for _ in range(100):
            sample = dist.sample()
            assert 5.0 <= sample <= 15.0

    def test_multiple_samples_show_variance(self):
        """Test that multiple samples show variance."""
        dist = UniformDistribution(min_val=0.0, max_val=100.0)
        samples = [dist.sample() for _ in range(50)]
        # Check that not all samples are the same
        assert len(set(samples)) > 1
        # Check that standard deviation is non-zero
        assert np.std(samples) > 0

    def test_sample_int_returns_integers(self):
        """Test that sample_int() returns integer values."""
        dist = UniformDistribution(min_val=0.0, max_val=100.0)
        sample_int = dist.sample_int(min_val=0, max_val=100)
        assert isinstance(sample_int, int)

    def test_sample_int_within_bounds(self):
        """Test that sample_int() respects min/max bounds."""
        dist = UniformDistribution(min_val=0.0, max_val=200.0)
        for _ in range(50):
            sample_int = dist.sample_int(min_val=10, max_val=50)
            assert 10 <= sample_int <= 50


class TestNormalDistribution:
    """Test NormalDistribution class."""

    def test_sample_returns_number(self):
        """Test that sample() returns a numeric value."""
        dist = NormalDistribution(mean=50.0, std=10.0)
        sample = dist.sample()
        assert isinstance(sample, (int, float))

    def test_sample_around_mean(self):
        """Test that samples cluster around the mean."""
        dist = NormalDistribution(mean=100.0, std=10.0)
        samples = [dist.sample() for _ in range(1000)]
        mean_sample = np.mean(samples)
        # Mean should be close to specified mean (within 2 std errors)
        assert abs(mean_sample - 100.0) < 2.0

    def test_multiple_samples_show_variance(self):
        """Test that multiple samples show variance."""
        dist = NormalDistribution(mean=50.0, std=15.0)
        samples = [dist.sample() for _ in range(100)]
        assert len(set(samples)) > 1
        assert np.std(samples) > 0

    def test_sample_int_returns_integers(self):
        """Test that sample_int() returns integer values."""
        dist = NormalDistribution(mean=50.0, std=10.0)
        sample_int = dist.sample_int(min_val=0, max_val=100)
        assert isinstance(sample_int, int)

    def test_sample_int_clipping(self):
        """Test that sample_int() clips values to bounds."""
        dist = NormalDistribution(mean=200.0, std=10.0)
        # Mean is 200, but max is 100, should clip
        for _ in range(20):
            sample_int = dist.sample_int(min_val=0, max_val=100)
            assert 0 <= sample_int <= 100


class TestExponentialDistribution:
    """Test ExponentialDistribution class."""

    def test_sample_returns_number(self):
        """Test that sample() returns a numeric value."""
        dist = ExponentialDistribution(rate=1.0)
        sample = dist.sample()
        assert isinstance(sample, (int, float))

    def test_sample_positive(self):
        """Test that samples are positive (exponential is always >= 0)."""
        dist = ExponentialDistribution(rate=2.0)
        for _ in range(100):
            sample = dist.sample()
            assert sample >= 0

    def test_multiple_samples_show_variance(self):
        """Test that multiple samples show variance."""
        dist = ExponentialDistribution(rate=1.0)
        samples = [dist.sample() for _ in range(100)]
        assert len(set(samples)) > 1
        assert np.std(samples) > 0

    def test_sample_int_returns_integers(self):
        """Test that sample_int() returns integer values."""
        dist = ExponentialDistribution(rate=0.5)
        sample_int = dist.sample_int(min_val=0, max_val=100)
        assert isinstance(sample_int, int)

    def test_higher_rate_lower_mean(self):
        """Test that higher rate produces lower mean values."""
        dist_low_rate = ExponentialDistribution(rate=0.5)
        dist_high_rate = ExponentialDistribution(rate=2.0)

        samples_low = [dist_low_rate.sample() for _ in range(1000)]
        samples_high = [dist_high_rate.sample() for _ in range(1000)]

        # Higher rate should give lower mean
        assert np.mean(samples_low) > np.mean(samples_high)


class TestLogNormalDistribution:
    """Test LogNormalDistribution class."""

    def test_sample_returns_number(self):
        """Test that sample() returns a numeric value."""
        dist = LogNormalDistribution(mu=1.0, sigma=0.5)
        sample = dist.sample()
        assert isinstance(sample, (int, float))

    def test_sample_positive(self):
        """Test that samples are positive (log-normal is always > 0)."""
        dist = LogNormalDistribution(mu=0.0, sigma=1.0)
        for _ in range(100):
            sample = dist.sample()
            assert sample > 0

    def test_multiple_samples_show_variance(self):
        """Test that multiple samples show variance."""
        dist = LogNormalDistribution(mu=2.0, sigma=0.5)
        samples = [dist.sample() for _ in range(100)]
        assert len(set(samples)) > 1
        assert np.std(samples) > 0

    def test_sample_int_returns_integers(self):
        """Test that sample_int() returns integer values."""
        dist = LogNormalDistribution(mu=3.0, sigma=0.5)
        sample_int = dist.sample_int(min_val=0, max_val=1000)
        assert isinstance(sample_int, int)


class TestPoissonDistribution:
    """Test PoissonDistribution class."""

    def test_sample_returns_number(self):
        """Test that sample() returns a numeric value."""
        dist = PoissonDistribution(lambda_=5.0)
        sample = dist.sample()
        assert isinstance(sample, (int, float))

    def test_sample_non_negative(self):
        """Test that samples are non-negative (Poisson is always >= 0)."""
        dist = PoissonDistribution(lambda_=3.0)
        for _ in range(100):
            sample = dist.sample()
            assert sample >= 0

    def test_multiple_samples_show_variance(self):
        """Test that multiple samples show variance."""
        dist = PoissonDistribution(lambda_=10.0)
        samples = [dist.sample() for _ in range(100)]
        assert len(set(samples)) > 1
        assert np.std(samples) > 0

    def test_sample_int_returns_integers(self):
        """Test that sample_int() returns integer values."""
        dist = PoissonDistribution(lambda_=5.0)
        sample_int = dist.sample_int(min_val=0, max_val=50)
        assert isinstance(sample_int, int)

    def test_lambda_affects_mean(self):
        """Test that lambda parameter affects the mean."""
        dist_low = PoissonDistribution(lambda_=2.0)
        dist_high = PoissonDistribution(lambda_=10.0)

        samples_low = [dist_low.sample() for _ in range(1000)]
        samples_high = [dist_high.sample() for _ in range(1000)]

        # Higher lambda should give higher mean
        assert np.mean(samples_high) > np.mean(samples_low)


class TestWeibullDistribution:
    """Test WeibullDistribution class."""

    def test_sample_returns_number(self):
        """Test that sample() returns a numeric value."""
        dist = WeibullDistribution(shape=1.5, scale=2.0)
        sample = dist.sample()
        assert isinstance(sample, (int, float))

    def test_sample_positive(self):
        """Test that samples are positive (Weibull is always > 0)."""
        dist = WeibullDistribution(shape=2.0, scale=1.0)
        for _ in range(100):
            sample = dist.sample()
            assert sample > 0

    def test_multiple_samples_show_variance(self):
        """Test that multiple samples show variance."""
        dist = WeibullDistribution(shape=1.5, scale=3.0)
        samples = [dist.sample() for _ in range(100)]
        assert len(set(samples)) > 1
        assert np.std(samples) > 0

    def test_sample_int_returns_integers(self):
        """Test that sample_int() returns integer values."""
        dist = WeibullDistribution(shape=2.0, scale=50.0)
        sample_int = dist.sample_int(min_val=0, max_val=200)
        assert isinstance(sample_int, int)


class TestBimodalDistribution:
    """Test BimodalDistribution class."""

    def test_sample_returns_number(self):
        """Test that sample() returns a numeric value."""
        dist = BimodalDistribution(mean1=10.0, std1=2.0, mean2=50.0, std2=5.0, mix=0.5)
        sample = dist.sample()
        assert isinstance(sample, (int, float))

    def test_multiple_samples_show_variance(self):
        """Test that multiple samples show variance."""
        dist = BimodalDistribution(mean1=20.0, std1=3.0, mean2=80.0, std2=5.0, mix=0.5)
        samples = [dist.sample() for _ in range(100)]
        assert len(set(samples)) > 1
        assert np.std(samples) > 0

    def test_sample_int_returns_integers(self):
        """Test that sample_int() returns integer values."""
        dist = BimodalDistribution(mean1=20.0, std1=5.0, mean2=80.0, std2=10.0, mix=0.5)
        sample_int = dist.sample_int(min_val=0, max_val=100)
        assert isinstance(sample_int, int)

    def test_bimodal_distribution_pattern(self):
        """Test that samples show bimodal pattern."""
        # Two well-separated modes
        dist = BimodalDistribution(mean1=10.0, std1=1.0, mean2=90.0, std2=1.0, mix=0.5)
        samples = [dist.sample() for _ in range(1000)]

        # Should have samples near both modes
        samples_near_mode1 = sum(1 for s in samples if s < 50)
        samples_near_mode2 = sum(1 for s in samples if s >= 50)

        # Both modes should have significant representation
        assert samples_near_mode1 > 300
        assert samples_near_mode2 > 300

    def test_mix_parameter_affects_distribution(self):
        """Test that mix parameter affects mode selection."""
        # Heavily favor first mode
        dist_mode1 = BimodalDistribution(mean1=10.0, std1=1.0, mean2=90.0, std2=1.0, mix=0.9)
        # Heavily favor second mode
        dist_mode2 = BimodalDistribution(mean1=10.0, std1=1.0, mean2=90.0, std2=1.0, mix=0.1)

        samples_mode1 = [dist_mode1.sample() for _ in range(1000)]
        samples_mode2 = [dist_mode2.sample() for _ in range(1000)]

        # First distribution should have more samples near 10
        assert np.mean(samples_mode1) < np.mean(samples_mode2)


class TestDistributionFactory:
    """Test DistributionFactory class."""

    def test_create_uniform_distribution(self):
        """Test creating UniformDistribution from config."""
        config = {'type': 'uniform', 'min': 5.0, 'max': 15.0}
        dist = DistributionFactory.create(config)
        assert isinstance(dist, UniformDistribution)
        assert dist.min_val == 5.0
        assert dist.max_val == 15.0

    def test_create_normal_distribution(self):
        """Test creating NormalDistribution from config."""
        config = {'type': 'normal', 'mean': 100.0, 'std': 20.0}
        dist = DistributionFactory.create(config)
        assert isinstance(dist, NormalDistribution)
        assert dist.mean == 100.0
        assert dist.std == 20.0

    def test_create_exponential_distribution(self):
        """Test creating ExponentialDistribution from config."""
        config = {'type': 'exponential', 'rate': 2.5}
        dist = DistributionFactory.create(config)
        assert isinstance(dist, ExponentialDistribution)
        assert dist.rate == 2.5

    def test_create_lognormal_distribution(self):
        """Test creating LogNormalDistribution from config."""
        config = {'type': 'lognormal', 'mu': 1.5, 'sigma': 0.8}
        dist = DistributionFactory.create(config)
        assert isinstance(dist, LogNormalDistribution)
        assert dist.mu == 1.5
        assert dist.sigma == 0.8

    def test_create_poisson_distribution(self):
        """Test creating PoissonDistribution from config."""
        config = {'type': 'poisson', 'lambda': 7.0}
        dist = DistributionFactory.create(config)
        assert isinstance(dist, PoissonDistribution)
        assert dist.lambda_ == 7.0

    def test_create_weibull_distribution(self):
        """Test creating WeibullDistribution from config."""
        config = {'type': 'weibull', 'shape': 2.5, 'scale': 3.0}
        dist = DistributionFactory.create(config)
        assert isinstance(dist, WeibullDistribution)
        assert dist.shape == 2.5
        assert dist.scale == 3.0

    def test_create_bimodal_distribution(self):
        """Test creating BimodalDistribution from config."""
        config = {
            'type': 'bimodal',
            'mean1': 20.0,
            'std1': 5.0,
            'mean2': 80.0,
            'std2': 10.0,
            'mix': 0.6
        }
        dist = DistributionFactory.create(config)
        assert isinstance(dist, BimodalDistribution)
        assert dist.mix == 0.6

    def test_create_with_defaults(self):
        """Test creating distribution with default parameters."""
        config = {'type': 'normal'}
        dist = DistributionFactory.create(config)
        assert isinstance(dist, NormalDistribution)
        assert dist.mean == 0.0
        assert dist.std == 1.0

    def test_create_default_type_uniform(self):
        """Test that default type is uniform when not specified."""
        config = {}
        dist = DistributionFactory.create(config)
        assert isinstance(dist, UniformDistribution)

    def test_create_case_insensitive(self):
        """Test that type matching is case-insensitive."""
        config = {'type': 'NORMAL', 'mean': 50.0}
        dist = DistributionFactory.create(config)
        assert isinstance(dist, NormalDistribution)

    def test_create_unknown_type_raises_error(self):
        """Test that unknown distribution type raises ValueError."""
        config = {'type': 'unknown_distribution'}
        with pytest.raises(ValueError, match="Unknown distribution type"):
            DistributionFactory.create(config)

    def test_create_invalid_type_raises_error(self):
        """Test that invalid distribution type raises ValueError."""
        config = {'type': 'foobar'}
        with pytest.raises(ValueError, match="Unknown distribution type"):
            DistributionFactory.create(config)


class TestPredefinedDistributions:
    """Test predefined distribution constants."""

    def test_latency_distribution_exists(self):
        """Test that LATENCY_DISTRIBUTION is defined."""
        assert LATENCY_DISTRIBUTION is not None
        assert isinstance(LATENCY_DISTRIBUTION, Distribution)

    def test_latency_distribution_type(self):
        """Test that LATENCY_DISTRIBUTION is LogNormalDistribution."""
        assert isinstance(LATENCY_DISTRIBUTION, LogNormalDistribution)

    def test_latency_distribution_samples(self):
        """Test that LATENCY_DISTRIBUTION produces valid samples."""
        sample = LATENCY_DISTRIBUTION.sample()
        assert sample > 0
        assert isinstance(sample, (int, float))

    def test_error_rate_distribution_exists(self):
        """Test that ERROR_RATE_DISTRIBUTION is defined."""
        assert ERROR_RATE_DISTRIBUTION is not None
        assert isinstance(ERROR_RATE_DISTRIBUTION, Distribution)

    def test_error_rate_distribution_type(self):
        """Test that ERROR_RATE_DISTRIBUTION is ExponentialDistribution."""
        assert isinstance(ERROR_RATE_DISTRIBUTION, ExponentialDistribution)

    def test_error_rate_distribution_samples(self):
        """Test that ERROR_RATE_DISTRIBUTION produces valid samples."""
        sample = ERROR_RATE_DISTRIBUTION.sample()
        assert sample >= 0
        assert isinstance(sample, (int, float))

    def test_throughput_distribution_exists(self):
        """Test that THROUGHPUT_DISTRIBUTION is defined."""
        assert THROUGHPUT_DISTRIBUTION is not None
        assert isinstance(THROUGHPUT_DISTRIBUTION, Distribution)

    def test_throughput_distribution_type(self):
        """Test that THROUGHPUT_DISTRIBUTION is NormalDistribution."""
        assert isinstance(THROUGHPUT_DISTRIBUTION, NormalDistribution)

    def test_throughput_distribution_samples(self):
        """Test that THROUGHPUT_DISTRIBUTION produces valid samples."""
        sample = THROUGHPUT_DISTRIBUTION.sample()
        assert isinstance(sample, (int, float))

    def test_cpu_distribution_exists(self):
        """Test that CPU_DISTRIBUTION is defined."""
        assert CPU_DISTRIBUTION is not None
        assert isinstance(CPU_DISTRIBUTION, Distribution)

    def test_cpu_distribution_type(self):
        """Test that CPU_DISTRIBUTION is BimodalDistribution."""
        assert isinstance(CPU_DISTRIBUTION, BimodalDistribution)

    def test_cpu_distribution_samples(self):
        """Test that CPU_DISTRIBUTION produces valid samples."""
        sample = CPU_DISTRIBUTION.sample()
        assert isinstance(sample, (int, float))

    def test_memory_distribution_exists(self):
        """Test that MEMORY_DISTRIBUTION is defined."""
        assert MEMORY_DISTRIBUTION is not None
        assert isinstance(MEMORY_DISTRIBUTION, Distribution)

    def test_memory_distribution_type(self):
        """Test that MEMORY_DISTRIBUTION is NormalDistribution."""
        assert isinstance(MEMORY_DISTRIBUTION, NormalDistribution)

    def test_memory_distribution_samples(self):
        """Test that MEMORY_DISTRIBUTION produces valid samples."""
        sample = MEMORY_DISTRIBUTION.sample()
        assert isinstance(sample, (int, float))

    def test_disk_io_distribution_exists(self):
        """Test that DISK_IO_DISTRIBUTION is defined."""
        assert DISK_IO_DISTRIBUTION is not None
        assert isinstance(DISK_IO_DISTRIBUTION, Distribution)

    def test_disk_io_distribution_type(self):
        """Test that DISK_IO_DISTRIBUTION is WeibullDistribution."""
        assert isinstance(DISK_IO_DISTRIBUTION, WeibullDistribution)

    def test_disk_io_distribution_samples(self):
        """Test that DISK_IO_DISTRIBUTION produces valid samples."""
        sample = DISK_IO_DISTRIBUTION.sample()
        assert sample > 0
        assert isinstance(sample, (int, float))

    def test_all_predefined_distributions_functional(self):
        """Test that all predefined distributions can produce samples."""
        predefined = [
            LATENCY_DISTRIBUTION,
            ERROR_RATE_DISTRIBUTION,
            THROUGHPUT_DISTRIBUTION,
            CPU_DISTRIBUTION,
            MEMORY_DISTRIBUTION,
            DISK_IO_DISTRIBUTION,
        ]

        for dist in predefined:
            # Each should be able to sample
            sample = dist.sample()
            assert isinstance(sample, (int, float))

            # Each should be able to sample integers
            sample_int = dist.sample_int(0, 100)
            assert isinstance(sample_int, int)
            assert 0 <= sample_int <= 100
