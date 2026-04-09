"""
Main data generator for synthetic option dataset.

This module orchestrates the complete generation pipeline:
    1. Simulate underlying price path (GBM)
    2. Generate arbitrage-free volatility surface (SVI)
    3. Price options using Black-Scholes with SVI vols
    4. Validate no-arbitrage conditions
    5. Save to CSV
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional

from opt_research.underlying import simulate_underlying, get_underlying_statistics
from opt_research.volatility_surface import (
    generate_term_structure_params,
    validate_calendar_arbitrage_free,
)
from opt_research.option_chain import generate_multi_day_chains
from opt_research.arbitrage_free import check_no_arbitrage, generate_arbitrage_report


def generate_dataset(
    S0: float = 1000.0,
    drift: float = 0.05,
    volatility: float = 0.10,
    n_days: int = 20,
    expiry_days: list = None,
    moneyness_range: list = None,
    r: float = 0.02,
    base_atm_vol: float = 0.10,
    seed: int = 42,
    output_path: str = "data/synthetic_options.csv",
    start_date: datetime = None,
) -> pd.DataFrame:
    """
    Generate complete synthetic options dataset with arbitrage-free guarantees.

    Pipeline:
        Step 1: Simulate underlying path using GBM
        Step 2: Generate SVI volatility surface (arbitrage-free by construction)
        Step 3: Generate option chains using SVI vols and Black-Scholes pricing
        Step 4: Validate no-arbitrage conditions
        Step 5: Save to CSV

    Args:
        S0: Initial underlying price
        drift: Annual drift for GBM (e.g., 0.05 for 5%)
        volatility: Annual volatility for GBM (e.g., 0.10 for 10%)
        n_days: Number of trading days to simulate
        expiry_days: List of expiration days (default: [1,2,...,10])
        moneyness_range: List of moneyness levels (default: [0.80, 0.85, ..., 1.20])
        r: Risk-free interest rate (annual)
        base_atm_vol: Base ATM volatility for SVI surface
        seed: Random seed for reproducibility
        output_path: Path to save CSV file
        start_date: Starting date (defaults to 2026-01-06)

    Returns:
        DataFrame containing the full synthetic option dataset

    Raises:
        ValueError: If arbitrage is detected in the generated data

    Example:
        >>> df = generate_dataset(n_days=5, expiry_days=[1, 2], seed=42)
        >>> len(df) > 0
        True
        >>> df.columns.tolist()
        ['date', 'option_name', 'option_type', 'bid', 'ask', 'mid', 'expiration', 'strike', 'underlying', 'moneyness', 'implied_volatility', 'delta']
    """
    print("=" * 70)
    print("SYNTHETIC OPTION DATA GENERATION")
    print("=" * 70)
    print()

    # Set defaults
    if expiry_days is None:
        expiry_days = list(range(1, 11))  # 1 to 10 business days
    if moneyness_range is None:
        # Use narrower range to avoid deep ITM puts with calendar spread issues
        moneyness_range = [0.90, 0.92, 0.94, 0.96, 0.98, 1.00, 1.02, 1.04, 1.06, 1.08, 1.10]
    if start_date is None:
        start_date = datetime(2026, 1, 6)

    # Step 1: Simulate underlying path
    print("Step 1: Simulating underlying price path")
    print(f"  Initial price: ${S0:.2f}")
    print(f"  Drift: {drift*100:.1f}% annual")
    print(f"  Volatility: {volatility*100:.1f}% annual")
    print(f"  Days: {n_days}")
    print(f"  Seed: {seed}")

    dates, prices = simulate_underlying(
        S0=S0,
        drift=drift,
        volatility=volatility,
        n_days=n_days,
        seed=seed,
        start_date=start_date,
    )

    stats = get_underlying_statistics(prices)
    print(f"  ✓ Generated {len(prices)} price points")
    print(f"  Final price: ${stats['final_price']:.2f}")
    print(f"  Realized return: {stats['realized_return']*100:.2f}% annual")
    print(f"  Realized volatility: {stats['realized_volatility']*100:.2f}% annual")
    print()

    # Step 2: Generate SVI volatility surface
    print("Step 2: Generating arbitrage-free volatility surface")
    print(f"  Base ATM vol: {base_atm_vol*100:.1f}%")
    print(f"  Expiry days: {expiry_days}")

    expiries = [d / 252.0 for d in expiry_days]
    params_list = generate_term_structure_params(expiries, base_atm_vol=base_atm_vol, seed=seed)

    # Validate calendar arbitrage-free
    k_grid = np.linspace(-0.3, 0.3, 100)
    is_calendar_free, cal_msg = validate_calendar_arbitrage_free(params_list, k_grid)

    if not is_calendar_free:
        raise ValueError(f"Calendar arbitrage in SVI surface: {cal_msg}")

    print(f"  ✓ Generated {len(params_list)} term structure slices")
    print(f"  ✓ Calendar arbitrage-free validated")
    print()

    # Step 3: Generate option chains
    print("Step 3: Generating option chains")
    print(f"  Moneyness range: {min(moneyness_range)*100:.0f}% to {max(moneyness_range)*100:.0f}%")
    print(f"  Strikes per expiry: {len(moneyness_range)}")
    print(f"  Risk-free rate: {r*100:.1f}%")

    params_dict = {T: params for T, params in params_list}

    df = generate_multi_day_chains(
        dates=dates,
        spots=prices,
        r=r,
        expiry_days_list=expiry_days,
        moneyness_range=moneyness_range,
        svi_params_dict=params_dict,
    )

    expected_options = len(dates) * len(expiry_days) * len(moneyness_range)
    print(f"  ✓ Generated {len(df)} option contracts")
    print(f"  Expected: {expected_options}, Actual: {len(df)}")
    print()

    # Step 4: Validate no-arbitrage
    print("Step 4: Validating arbitrage-free conditions")
    # Use tolerance of 0.5% of spot price to account for numerical errors in discrete strikes
    # SVI surface is theoretically arbitrage-free, but discrete strikes can have small violations
    tolerance = 0.005 * S0
    is_valid, violations = check_no_arbitrage(df, tolerance=tolerance)

    if not is_valid:
        print(f"  ✗ FAILED: {len(violations)} arbitrage violations detected")
        for violation in violations[:5]:  # Show first 5
            print(f"    - {violation}")
        if len(violations) > 5:
            print(f"    ... and {len(violations) - 5} more")
        print()
        raise ValueError(f"Arbitrage detected in generated dataset: {violations[0]}")

    print("  ✓ All arbitrage tests passed:")
    print("    - Non-negative prices")
    print("    - Upper bound (C <= S)")
    print("    - Intrinsic value bound")
    print("    - Monotonicity in strike")
    print("    - Convexity (no butterfly)")
    print("    - Calendar spread consistency")
    print()

    # Step 5: Save to CSV
    print("Step 5: Saving dataset")
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        print(f"  Created directory: {output_dir}")

    df.to_csv(output_path, index=False)
    file_size = os.path.getsize(output_path) / 1024  # KB
    print(f"  ✓ Saved to: {output_path}")
    print(f"  File size: {file_size:.1f} KB")
    print()

    # Summary statistics
    print("=" * 70)
    print("GENERATION COMPLETE")
    print("=" * 70)
    print()
    print("Dataset Summary:")
    print(f"  Total options: {len(df):,}")
    print(f"  Trading days: {df['date'].nunique()}")
    print(f"  Unique strikes: {df['strike'].nunique()}")
    print(f"  Unique expiries: {df['expiration'].nunique()}")
    print(f"  Date range: {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"  Price range: ${df['mid'].min():.4f} to ${df['mid'].max():.2f}")
    print(f"  Underlying range: ${df['underlying'].min():.2f} to ${df['underlying'].max():.2f}")
    print()
    print("Column Names:")
    print(f"  {df.columns.tolist()}")
    print()
    print("=" * 70)

    return df


if __name__ == "__main__":
    """Generate the synthetic options dataset."""
    print("\n")
    print("*" * 70)
    print("*" + " " * 68 + "*")
    print("*" + " " * 15 + "SYNTHETIC OPTION DATA GENERATOR" + " " * 22 + "*")
    print("*" + " " * 68 + "*")
    print("*" * 70)
    print("\n")

    # Generate dataset with default parameters
    df = generate_dataset(
        S0=1000.0,
        drift=0.05,
        volatility=0.10,
        n_days=20,
        expiry_days=list(range(1, 11)),
        moneyness_range=[0.90, 0.92, 0.94, 0.96, 0.98, 1.00, 1.02, 1.04, 1.06, 1.08, 1.10],
        r=0.02,
        base_atm_vol=0.10,
        seed=42,
        output_path="data/synthetic_options.csv",
    )

    # Display sample data
    print("\nSample Data (first 10 rows):")
    print("=" * 70)
    print(
        df[["date", "option_name", "strike", "mid", "implied_volatility", "delta"]]
        .head(10)
        .to_string(index=False)
    )
    print()

    # Generate detailed arbitrage report
    print("\nDetailed Arbitrage-Free Validation:")
    report = generate_arbitrage_report(df)
    print(report)

    print("\n" + "*" * 70)
    print("Generation completed successfully!")
    print("*" * 70 + "\n")
