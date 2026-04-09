"""
Underlying asset simulation using Geometric Brownian Motion.

This module provides functionality to simulate stock price paths using the
standard GBM process with specified drift and volatility parameters.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Tuple, List


def simulate_underlying(
    S0: float,
    drift: float,
    volatility: float,
    n_days: int,
    seed: int = 42,
    start_date: datetime = None,
) -> Tuple[List[datetime], np.ndarray]:
    """
    Simulate underlying asset price path using Geometric Brownian Motion.

    The GBM process is defined as:
        S(t+dt) = S(t) * exp[(μ - σ²/2)dt + σ√dt * Z]

    where:
        μ = drift (annualized)
        σ = volatility (annualized)
        dt = 1/252 (one business day)
        Z ~ N(0,1) (standard normal random variable)

    Args:
        S0: Initial asset price
        drift: Annualized drift (e.g., 0.05 for 5%)
        volatility: Annualized volatility (e.g., 0.10 for 10%)
        n_days: Number of business days to simulate
        seed: Random seed for reproducibility
        start_date: Starting date for the simulation (defaults to today)

    Returns:
        Tuple of (dates, prices) where:
            - dates: List of datetime objects for each trading day
            - prices: numpy array of simulated prices

    Example:
        >>> dates, prices = simulate_underlying(1000, 0.05, 0.10, 20, seed=42)
        >>> len(prices)
        21  # Includes initial price
        >>> prices[0]
        1000.0
    """
    np.random.seed(seed)

    # Time step: 1 business day in years
    dt = 1.0 / 252.0

    # Initialize price array
    prices = np.zeros(n_days + 1)  # +1 to include initial price
    prices[0] = S0

    # Generate random shocks
    # Shape: (n_days,) -> (n_days,)
    Z = np.random.standard_normal(n_days)

    # GBM simulation
    for i in range(n_days):
        # Drift-adjusted term: (μ - σ²/2)dt
        drift_term = (drift - 0.5 * volatility**2) * dt
        # Diffusion term: σ√dt * Z
        diffusion_term = volatility * np.sqrt(dt) * Z[i]
        # S(t+1) = S(t) * exp[drift_term + diffusion_term]
        prices[i + 1] = prices[i] * np.exp(drift_term + diffusion_term)

    # Generate business day dates
    if start_date is None:
        start_date = datetime(2026, 1, 6)  # Default start date

    dates = [start_date + timedelta(days=i) for i in range(n_days + 1)]

    return dates, prices


def get_underlying_statistics(prices: np.ndarray, dt: float = 1 / 252) -> dict:
    """
    Calculate realized statistics from simulated price path.

    Args:
        prices: Array of simulated prices
        dt: Time step in years (default: 1/252 for daily)

    Returns:
        Dictionary containing:
            - realized_return: Annualized realized return
            - realized_volatility: Annualized realized volatility
            - max_drawdown: Maximum drawdown percentage
            - final_price: Final price in the path

    Example:
        >>> dates, prices = simulate_underlying(1000, 0.05, 0.10, 20, seed=42)
        >>> stats = get_underlying_statistics(prices)
        >>> 'realized_volatility' in stats
        True
    """
    # Calculate log returns: r(t) = ln(S(t)/S(t-1))
    # Shape: (N,) -> (N-1,)
    log_returns = np.diff(np.log(prices))

    # Realized annualized return
    total_return = (prices[-1] / prices[0]) - 1
    n_periods = len(prices) - 1
    annualized_return = (1 + total_return) ** (1 / (n_periods * dt)) - 1

    # Realized annualized volatility
    realized_vol = np.std(log_returns, ddof=1) * np.sqrt(1 / dt)

    # Maximum drawdown
    cummax = np.maximum.accumulate(prices)
    drawdowns = (prices - cummax) / cummax
    max_drawdown = np.min(drawdowns)

    return {
        "realized_return": annualized_return,
        "realized_volatility": realized_vol,
        "max_drawdown": max_drawdown,
        "final_price": prices[-1],
        "initial_price": prices[0],
    }


if __name__ == "__main__":
    """Smoke test for underlying simulation."""
    print("=" * 60)
    print("Underlying Simulation Smoke Test")
    print("=" * 60)

    # Test 1: Basic simulation
    print("\n[Test 1] Basic GBM Simulation")
    dates, prices = simulate_underlying(S0=1000, drift=0.05, volatility=0.10, n_days=20, seed=42)
    print(f"  Initial price: {prices[0]:.2f}")
    print(f"  Final price: {prices[-1]:.2f}")
    print(f"  Price path length: {len(prices)}")
    print(f"  Date range: {dates[0].date()} to {dates[-1].date()}")

    # Test 2: Statistics
    print("\n[Test 2] Realized Statistics")
    stats = get_underlying_statistics(prices)
    for key, value in stats.items():
        if "price" in key:
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value:.4f}")

    # Test 3: Reproducibility
    print("\n[Test 3] Reproducibility Check")
    _, prices1 = simulate_underlying(1000, 0.05, 0.10, 10, seed=42)
    _, prices2 = simulate_underlying(1000, 0.05, 0.10, 10, seed=42)
    identical = np.allclose(prices1, prices2)
    print(f"  Same seed produces identical results: {identical}")

    # Test 4: Different seeds produce different paths
    _, prices3 = simulate_underlying(1000, 0.05, 0.10, 10, seed=123)
    different = not np.allclose(prices1, prices3)
    print(f"  Different seeds produce different results: {different}")

    print("\n" + "=" * 60)
    print("Smoke test completed successfully!")
    print("=" * 60)
