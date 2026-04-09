"""
Option chain generation combining volatility surface and Black-Scholes pricing.

This module generates complete option chains for given dates, strikes, and expiries,
using the SVI volatility surface for implied volatilities and Black-Scholes for pricing.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict

from opt_research.volatility_surface import SVIParameters, svi_implied_vol
from opt_research.option_pricing import (
    black_scholes_call,
    black_scholes_delta,
    black_scholes_put,
    black_scholes_put_delta,
)


def add_business_days(start_date: datetime, n_days: int) -> datetime:
    """
    Add business days to a date (simple implementation assuming all days are business days).

    Args:
        start_date: Starting date
        n_days: Number of business days to add

    Returns:
        New date after adding n business days

    Note:
        This is a simplified implementation that treats all days as business days.
        For production use, consider using pandas.tseries.offsets.BDay or a proper
        business day calendar.
    """
    return start_date + timedelta(days=n_days)


def generate_option_chain(
    date: datetime,
    spot: float,
    r: float,
    expiry_days_list: List[int],
    moneyness_range: List[float],
    svi_params_dict: Dict[float, SVIParameters],
) -> pd.DataFrame:
    """
    Generate a complete option chain for a single trading day.

    This function combines:
        1. The SVI volatility surface to get implied volatilities
        2. Black-Scholes formula to price options
        3. Bid-ask spread model for market realism

    Args:
        date: Trading date
        spot: Current spot price of the underlying
        r: Risk-free interest rate (annualized)
        expiry_days_list: List of expiration days (e.g., [1, 2, 3, ..., 10])
        moneyness_range: List of moneyness levels (e.g., [0.80, 0.85, ..., 1.20])
        svi_params_dict: Dictionary mapping time to expiry (years) to SVI parameters

    Returns:
        DataFrame with columns:
            - date: Trading date
            - option_name: Option identifier (e.g., "C_20260107_1000" or "P_20260107_1000")
            - option_type: 'call' or 'put'
            - bid: Bid price
            - ask: Ask price
            - mid: Mid price (Black-Scholes theoretical)
            - expiration: Expiration date
            - strike: Strike price
            - underlying: Underlying spot price
            - moneyness: Strike / Spot ratio
            - implied_volatility: Implied volatility from SVI surface
            - delta: Option delta

    Example:
        >>> from opt_research.volatility_surface import generate_term_structure_params
        >>> expiries = [i/252 for i in range(1, 11)]
        >>> params_list = generate_term_structure_params(expiries)
        >>> params_dict = {T: params for T, params in params_list}
        >>> date = datetime(2026, 1, 6)
        >>> chain = generate_option_chain(date, 1000, 0.02, [1, 2], [0.95, 1.00, 1.05], params_dict)
        >>> len(chain)  # 2 expiries * 3 strikes * 2 option types (call/put)
        12
    """
    options = []

    for exp_days in expiry_days_list:
        # Calculate expiration date and time to expiry
        exp_date = add_business_days(date, exp_days)
        T = exp_days / 252.0  # Time to expiry in years

        # Get SVI parameters for this expiry
        if T not in svi_params_dict:
            raise ValueError(f"No SVI parameters found for T={T}")
        svi_params = svi_params_dict[T]

        # Forward price for log-moneyness calculation
        # F = S * exp(r*T)
        forward = spot * np.exp(r * T)

        for moneyness in moneyness_range:
            # Calculate strike price, rounded to nearest 5
            K = np.round(spot * moneyness / 5) * 5

            # Compute log-forward-moneyness: k = ln(K/F)
            k = np.log(K / forward)

            # Get implied volatility from SVI surface
            # svi_implied_vol expects array input, so wrap and unwrap
            sigma_impl = float(svi_implied_vol(np.array([k]), T, svi_params)[0])

            # Generate bid-ask spread
            # Spread = max(0.01, 2% of mid price) - calculated separately for each type

            # Generate CALL option
            call_mid = float(black_scholes_call(spot, K, T, r, sigma_impl))
            call_spread = max(0.01, 0.02 * call_mid)
            call_bid = max(0.01, call_mid - call_spread / 2)
            call_ask = call_mid + call_spread / 2
            call_delta = float(black_scholes_delta(spot, K, T, r, sigma_impl))
            call_name = f"C_{exp_date.strftime('%Y%m%d')}_{int(K):04d}"

            call_option = {
                "date": date,
                "option_name": call_name,
                "option_type": "call",
                "bid": call_bid,
                "ask": call_ask,
                "mid": call_mid,
                "expiration": exp_date,
                "strike": K,
                "underlying": spot,
                "moneyness": K / spot,
                "implied_volatility": sigma_impl,
                "delta": call_delta,
            }
            options.append(call_option)

            # Generate PUT option
            put_mid = float(black_scholes_put(spot, K, T, r, sigma_impl))
            put_spread = max(0.01, 0.02 * put_mid)
            put_bid = max(0.01, put_mid - put_spread / 2)
            put_ask = put_mid + put_spread / 2
            put_delta = float(black_scholes_put_delta(spot, K, T, r, sigma_impl))
            put_name = f"P_{exp_date.strftime('%Y%m%d')}_{int(K):04d}"

            put_option = {
                "date": date,
                "option_name": put_name,
                "option_type": "put",
                "bid": put_bid,
                "ask": put_ask,
                "mid": put_mid,
                "expiration": exp_date,
                "strike": K,
                "underlying": spot,
                "moneyness": K / spot,
                "implied_volatility": sigma_impl,
                "delta": put_delta,
            }
            options.append(put_option)

    # Convert to DataFrame
    df = pd.DataFrame(options)

    return df


def generate_multi_day_chains(
    dates: List[datetime],
    spots: np.ndarray,
    r: float,
    expiry_days_list: List[int],
    moneyness_range: List[float],
    svi_params_dict: Dict[float, SVIParameters],
) -> pd.DataFrame:
    """
    Generate option chains for multiple trading days.

    Args:
        dates: List of trading dates
        spots: Array of spot prices corresponding to each date
        r: Risk-free interest rate
        expiry_days_list: List of expiration days
        moneyness_range: List of moneyness levels
        svi_params_dict: Dictionary of SVI parameters by expiry

    Returns:
        Concatenated DataFrame with all option chains

    Example:
        >>> from opt_research.underlying import simulate_underlying
        >>> from opt_research.volatility_surface import generate_term_structure_params
        >>> dates, spots = simulate_underlying(1000, 0.05, 0.10, 5, seed=42)
        >>> expiries = [i/252 for i in [1, 2, 3]]
        >>> params_list = generate_term_structure_params(expiries)
        >>> params_dict = {T: params for T, params in params_list}
        >>> chains = generate_multi_day_chains(
        ...     dates, spots, 0.02, [1, 2, 3], [0.90, 1.00, 1.10], params_dict
        ... )
        >>> len(chains) == len(dates) * 3 * 3 * 2  # days * expiries * strikes * option_types
        True
    """
    all_chains = []

    for date, spot in zip(dates, spots):
        daily_chain = generate_option_chain(
            date, spot, r, expiry_days_list, moneyness_range, svi_params_dict
        )
        all_chains.append(daily_chain)

    # Concatenate all chains
    df = pd.concat(all_chains, ignore_index=True)

    return df


if __name__ == "__main__":
    """Smoke test for option chain generation."""
    print("=" * 60)
    print("Option Chain Generation Smoke Test")
    print("=" * 60)

    from opt_research.volatility_surface import generate_term_structure_params
    from opt_research.underlying import simulate_underlying

    # Test 1: Single day option chain
    print("\n[Test 1] Single Day Option Chain")
    date = datetime(2026, 1, 6)
    spot = 1000.0
    r = 0.02

    # Generate SVI parameters
    expiry_days = [1, 2, 5, 10]
    expiries = [d / 252 for d in expiry_days]
    params_list = generate_term_structure_params(expiries)
    params_dict = {T: params for T, params in params_list}

    # Generate chain
    moneyness = [0.90, 0.95, 1.00, 1.05, 1.10]
    chain = generate_option_chain(date, spot, r, expiry_days, moneyness, params_dict)

    print(f"  Generated {len(chain)} options")
    print(f"  Unique expiries: {chain['expiration'].nunique()}")
    print(f"  Unique strikes: {chain['strike'].nunique()}")
    print(f"  Option types: {chain['option_type'].unique().tolist()}")
    print(f"\n  Sample options (calls and puts):")
    print(chain[["option_name", "option_type", "strike", "mid", "implied_volatility", "delta"]].head(10))

    # Test 2: Multi-day chains
    print("\n[Test 2] Multi-Day Option Chains")
    dates, spots = simulate_underlying(1000, 0.05, 0.10, 5, seed=42)
    multi_chain = generate_multi_day_chains(
        dates, spots, r, [1, 5, 10], [0.95, 1.00, 1.05], params_dict
    )

    print(f"  Trading days: {len(dates)}")
    print(f"  Total options: {len(multi_chain)}")
    print(f"  Options per day: {len(multi_chain) / len(dates):.0f}")

    # Test 3: Bid-ask spreads
    print("\n[Test 3] Bid-Ask Spread Analysis")
    sample = chain.head(5)
    for _, row in sample.iterrows():
        spread_pct = (row["ask"] - row["bid"]) / row["mid"] * 100
        print(
            f"  {row['option_name']}: mid={row['mid']:.3f}, "
            f"bid={row['bid']:.3f}, ask={row['ask']:.3f}, spread={spread_pct:.2f}%"
        )

    # Test 4: Volatility smile (using calls only)
    print("\n[Test 4] Volatility Smile (5-day expiry, calls only)")
    calls_only = chain[chain["option_type"] == "call"]
    smile = calls_only[calls_only["expiration"] == calls_only["expiration"].unique()[2]].sort_values("strike")
    print(f"  Expiry: {smile['expiration'].iloc[0].date()}")
    for _, row in smile.iterrows():
        print(
            f"    K={row['strike']:4.0f} (M={row['moneyness']:.2f}): "
            f"vol={row['implied_volatility']:.4f}, price={row['mid']:.3f}"
        )

    # Test 5: Delta progression (calls vs puts)
    print("\n[Test 5] Delta vs Strike (1-day expiry, calls and puts)")
    first_expiry = chain["expiration"].unique()[0]
    delta_analysis = chain[chain["expiration"] == first_expiry].sort_values(
        ["strike", "option_type"]
    )
    print(f"  Spot: {spot:.0f}")
    for _, row in delta_analysis.iterrows():
        moneyness_label = (
            "ITM" if row["strike"] < spot else ("ATM" if row["strike"] == spot else "OTM")
        )
        print(f"    K={row['strike']:4.0f} ({moneyness_label}) {row['option_type']}: delta={row['delta']:.4f}")

    print("\n" + "=" * 60)
    print("Smoke test completed successfully!")
    print("=" * 60)
