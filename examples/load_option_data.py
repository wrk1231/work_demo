#!/usr/bin/env python3
"""
Example script for loading and analyzing synthetic option data.

This script demonstrates how to:
1. Load the synthetic options dataset
2. Perform basic data exploration
3. Analyze option characteristics
4. Verify data quality and arbitrage-free properties
"""

import pandas as pd
import numpy as np
from pathlib import Path


def load_synthetic_options(filepath: str = "../data/synthetic_options.csv") -> pd.DataFrame:
    """
    Load synthetic options data from CSV file.

    Args:
        filepath: Path to the CSV file (relative or absolute)

    Returns:
        DataFrame with option data

    Example:
        >>> df = load_synthetic_options()
        >>> print(df.columns.tolist())
        ['date', 'option_name', 'option_type', 'bid', 'ask', 'mid', 'expiration', 'strike', ...]
    """
    # Expected CSV headers
    expected_headers = [
        "date",
        "option_name",
        "option_type",
        "bid",
        "ask",
        "mid",
        "expiration",
        "strike",
        "underlying",
        "moneyness",
        "implied_volatility",
        "delta",
    ]
    
    # Convert relative path to absolute if needed
    filepath = Path(__file__).parent / filepath
    
    # Load CSV with explicit header row (row 0)
    df = pd.read_csv(filepath, header=0)
    
    # Validate headers
    actual_headers = df.columns.tolist()
    if actual_headers != expected_headers:
        missing = set(expected_headers) - set(actual_headers)
        extra = set(actual_headers) - set(expected_headers)
        if missing or extra:
            print(f"⚠ Warning: CSV headers don't match expected format")
            if missing:
                print(f"  Missing columns: {missing}")
            if extra:
                print(f"  Extra columns: {extra}")
    
    # Convert date columns to datetime
    df["date"] = pd.to_datetime(df["date"])
    df["expiration"] = pd.to_datetime(df["expiration"])
    
    return df


def explore_dataset(df: pd.DataFrame) -> None:
    """
    Print summary statistics and exploration of the dataset.

    Args:
        df: DataFrame with option data
    """
    print("=" * 70)
    print("SYNTHETIC OPTION DATASET EXPLORATION")
    print("=" * 70)

    print(f"\n1. Dataset Overview")
    print(f"   Total options: {len(df):,}")
    print(f"   Trading days: {df['date'].nunique()}")
    print(f"   Unique strikes: {df['strike'].nunique()}")
    print(f"   Unique expiries: {df['expiration'].nunique()}")
    print(f"   Date range: {df['date'].min()} to {df['date'].max()}")

    print(f"\n2. Price Statistics")
    print(f"   Mid price range: ${df['mid'].min():.4f} to ${df['mid'].max():.2f}")
    print(f"   Average mid price: ${df['mid'].mean():.2f}")
    print(f"   Average bid-ask spread: ${(df['ask'] - df['bid']).mean():.4f}")

    print(f"\n3. Underlying Price Path")
    underlying_path = df.groupby("date")["underlying"].first()
    print(f"   Initial price: ${underlying_path.iloc[0]:.2f}")
    print(f"   Final price: ${underlying_path.iloc[-1]:.2f}")
    print(f"   Min price: ${underlying_path.min():.2f}")
    print(f"   Max price: ${underlying_path.max():.2f}")
    print(f"   Total return: {(underlying_path.iloc[-1]/underlying_path.iloc[0] - 1)*100:.2f}%")

    print(f"\n4. Option Characteristics")
    print(f"   Moneyness range: {df['moneyness'].min():.2%} to {df['moneyness'].max():.2%}")
    print(
        f"   Implied volatility range: {df['implied_volatility'].min():.2%} to {df['implied_volatility'].max():.2%}"
    )
    print(f"   Delta range: {df['delta'].min():.4f} to {df['delta'].max():.4f}")

    print(f"\n5. Time to Expiration")
    df_temp = df.copy()
    df_temp["days_to_expiry"] = (df_temp["expiration"] - df_temp["date"]).dt.days
    print(f"   Min DTE: {df_temp['days_to_expiry'].min()} days")
    print(f"   Max DTE: {df_temp['days_to_expiry'].max()} days")
    print(f"   Average DTE: {df_temp['days_to_expiry'].mean():.1f} days")


def analyze_single_day(df: pd.DataFrame, date: str) -> None:
    """
    Analyze options for a specific trading day.

    Args:
        df: DataFrame with option data
        date: Date string in 'YYYY-MM-DD' format
    """
    print(f"\n{'=' * 70}")
    print(f"SINGLE DAY ANALYSIS: {date}")
    print("=" * 70)

    # Filter to specific date
    day_df = df[df["date"] == date].copy()

    if len(day_df) == 0:
        print(f"No data found for date: {date}")
        return

    spot = day_df["underlying"].iloc[0]
    print(f"\nSpot price: ${spot:.2f}")
    print(f"Total options: {len(day_df)}")

    # Analyze by expiration
    print(f"\nOptions by expiration:")
    exp_groups = day_df.groupby("expiration")
    for exp, group in exp_groups:
        dte = (exp - pd.Timestamp(date)).days
        atm_option = group.iloc[(group["strike"] - spot).abs().argsort()[:1]]
        print(
            f"  {exp.date()} (DTE={dte:2d}): {len(group):2d} options, "
            f"ATM strike={atm_option['strike'].iloc[0]:.0f}, "
            f"ATM price=${atm_option['mid'].iloc[0]:.2f}, "
            f"ATM IV={atm_option['implied_volatility'].iloc[0]:.2%}"
        )


def check_arbitrage_conditions(df: pd.DataFrame) -> None:
    """
    Verify basic arbitrage-free conditions on the data.

    Args:
        df: DataFrame with option data
    """
    print(f"\n{'=' * 70}")
    print("ARBITRAGE-FREE CONDITION CHECKS")
    print("=" * 70)

    violations = []

    # Check 1: All prices are non-negative
    negative_prices = df[df["mid"] < 0]
    if len(negative_prices) > 0:
        violations.append(f"❌ Found {len(negative_prices)} negative prices")
    else:
        print("✓ All prices are non-negative")

    # Check 2: Call price <= Spot price
    exceeds_spot = df[df["mid"] > df["underlying"]]
    if len(exceeds_spot) > 0:
        violations.append(f"❌ Found {len(exceeds_spot)} prices exceeding spot")
    else:
        print("✓ All prices are below spot price")

    # Check 3: Call price >= Intrinsic value (simplified check)
    df["intrinsic"] = np.maximum(0, df["underlying"] - df["strike"])
    below_intrinsic = df[df["mid"] < df["intrinsic"] - 0.01]  # Small tolerance
    if len(below_intrinsic) > 0:
        violations.append(f"❌ Found {len(below_intrinsic)} prices below intrinsic value")
    else:
        print("✓ All prices are above intrinsic value")

    # Check 4: Monotonicity in strike (per date/expiry)
    monotonicity_violations = 0
    for (date, exp), group in df.groupby(["date", "expiration"]):
        sorted_group = group.sort_values("strike")
        prices = sorted_group["mid"].values
        if not all(prices[i] >= prices[i + 1] - 0.01 for i in range(len(prices) - 1)):
            monotonicity_violations += 1

    if monotonicity_violations > 0:
        violations.append(f"❌ Found {monotonicity_violations} monotonicity violations")
    else:
        print("✓ Monotonicity in strike satisfied")

    # Summary
    if violations:
        print(f"\n⚠ WARNING: {len(violations)} arbitrage condition(s) violated:")
        for v in violations:
            print(f"  {v}")
    else:
        print(f"\n✅ All basic arbitrage-free conditions satisfied!")


def main():
    """Main execution function."""
    # Load data
    print("Loading synthetic option data...")
    df = load_synthetic_options()
    print(f"Loaded {len(df)} options\n")

    # Display CSV headers and top rows
    print("=" * 70)
    print("CSV HEADERS AND TOP 10 ROWS")
    print("=" * 70)
    print(f"\nColumn names: {df.columns.tolist()}\n")
    print("First 10 rows of data:")
    print(df.head(10).to_string())
    print()
    
    # Check arbitrage conditions
    check_arbitrage_conditions(df)

    print(f"\n{'=' * 70}")
    print("Example script completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
