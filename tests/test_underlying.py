"""Tests for underlying asset simulation module."""

import numpy as np
import pytest
from datetime import datetime

from opt_research.underlying import (
    simulate_underlying,
    get_underlying_statistics,
)


class TestSimulateUnderlying:
    """Test cases for GBM simulation."""

    def test_basic_simulation(self):
        """Test basic GBM simulation produces correct output shape."""
        dates, prices = simulate_underlying(1000, 0.05, 0.10, 10, seed=42)

        assert len(dates) == 11  # n_days + 1 (includes initial)
        assert len(prices) == 11
        assert prices[0] == 1000.0  # Initial price

    def test_reproducibility(self):
        """Test that same seed produces identical results."""
        _, prices1 = simulate_underlying(1000, 0.05, 0.10, 10, seed=42)
        _, prices2 = simulate_underlying(1000, 0.05, 0.10, 10, seed=42)

        np.testing.assert_array_equal(prices1, prices2)

    def test_different_seeds(self):
        """Test that different seeds produce different results."""
        _, prices1 = simulate_underlying(1000, 0.05, 0.10, 10, seed=42)
        _, prices2 = simulate_underlying(1000, 0.05, 0.10, 10, seed=123)

        assert not np.allclose(prices1, prices2)

    def test_positive_prices(self):
        """Test that all simulated prices are positive."""
        _, prices = simulate_underlying(1000, 0.05, 0.10, 100, seed=42)

        assert np.all(prices > 0)

    def test_zero_volatility(self):
        """Test deterministic path with zero volatility."""
        _, prices = simulate_underlying(1000, 0.05, 0.0, 10, seed=42)

        # With zero vol, path should be deterministic: S(t) = S0 * exp(drift*t)
        dt = 1 / 252
        expected_final = 1000 * np.exp(0.05 * 10 * dt)

        assert abs(prices[-1] - expected_final) < 1e-10

    def test_start_date(self):
        """Test custom start date."""
        start = datetime(2025, 1, 1)
        dates, _ = simulate_underlying(1000, 0.05, 0.10, 5, seed=42, start_date=start)

        assert dates[0] == start
        assert len(dates) == 6


class TestGetUnderlyingStatistics:
    """Test cases for statistics calculation."""

    def test_statistics_keys(self):
        """Test that all expected keys are present in statistics."""
        _, prices = simulate_underlying(1000, 0.05, 0.10, 20, seed=42)
        stats = get_underlying_statistics(prices)

        expected_keys = {
            "realized_return",
            "realized_volatility",
            "max_drawdown",
            "final_price",
            "initial_price",
        }

        assert set(stats.keys()) == expected_keys

    def test_initial_final_prices(self):
        """Test that initial and final prices match the array."""
        _, prices = simulate_underlying(1000, 0.05, 0.10, 20, seed=42)
        stats = get_underlying_statistics(prices)

        assert stats["initial_price"] == prices[0]
        assert stats["final_price"] == prices[-1]

    def test_positive_volatility(self):
        """Test that realized volatility is non-negative."""
        _, prices = simulate_underlying(1000, 0.05, 0.10, 20, seed=42)
        stats = get_underlying_statistics(prices)

        assert stats["realized_volatility"] >= 0

    def test_max_drawdown_negative(self):
        """Test that max drawdown is non-positive."""
        _, prices = simulate_underlying(1000, 0.05, 0.10, 20, seed=42)
        stats = get_underlying_statistics(prices)

        assert stats["max_drawdown"] <= 0

    def test_constant_prices(self):
        """Test statistics for constant price path."""
        prices = np.array([100.0] * 10)
        stats = get_underlying_statistics(prices)

        assert abs(stats["realized_volatility"]) < 1e-10
        assert abs(stats["realized_return"]) < 1e-10
        assert abs(stats["max_drawdown"]) < 1e-10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
