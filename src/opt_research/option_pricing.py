"""
Black-Scholes option pricing and Greeks calculation.

This module implements the Black-Scholes-Merton model for European call option
pricing and related Greeks (Delta, Vega).
"""

import numpy as np
from scipy.stats import norm
from typing import Union


def black_scholes_call(
    S: Union[float, np.ndarray],
    K: Union[float, np.ndarray],
    T: Union[float, np.ndarray],
    r: float,
    sigma: Union[float, np.ndarray],
) -> Union[float, np.ndarray]:
    """
    Price European call option using Black-Scholes formula.

    The Black-Scholes formula for a call option is:
        C = S * N(d1) - K * exp(-rT) * N(d2)

    where:
        d1 = [ln(S/K) + (r + sigma^2/2)*T] / (sigma*sqrt(T))
        d2 = d1 - sigma*sqrt(T)
        N(x) = cumulative distribution function of standard normal

    Args:
        S: Spot price (current underlying price)
        K: Strike price
        T: Time to expiration in years
        r: Risk-free interest rate (annualized)
        sigma: Implied volatility (annualized)

    Returns:
        Call option price

    Note:
        For expired options (T <= 0), returns intrinsic value max(S - K, 0)

    Example:
        >>> price = black_scholes_call(100, 100, 0.25, 0.02, 0.20)
        >>> price > 0
        True
        >>> price < 100  # Call price less than spot
        True
    """
    S = np.atleast_1d(S)
    K = np.atleast_1d(K)
    T = np.atleast_1d(T)
    sigma = np.atleast_1d(sigma)

    # Handle expired options
    expired = T <= 0
    if np.any(expired):
        result = np.maximum(S - K, 0)
        if np.all(expired):
            return np.squeeze(result)
        # Mixed case: some expired, some not
        # Continue with BS formula for non-expired

    # Black-Scholes formula
    # d1 = [ln(S/K) + (r + sigma^2/2)*T] / (sigma*sqrt(T))
    # Shape: broadcast to common shape
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    # d2 = d1 - sigma*sqrt(T)
    # Shape: same as d1
    d2 = d1 - sigma * np.sqrt(T)

    # Call price = S * N(d1) - K * exp(-rT) * N(d2)
    # Shape: broadcast to common shape
    call_price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)

    # Handle expired options
    if np.any(expired):
        call_price = np.where(expired, np.maximum(S - K, 0), call_price)

    return np.squeeze(call_price)


def black_scholes_put(
    S: Union[float, np.ndarray],
    K: Union[float, np.ndarray],
    T: Union[float, np.ndarray],
    r: float,
    sigma: Union[float, np.ndarray],
) -> Union[float, np.ndarray]:
    """
    Price European put option using Black-Scholes formula.

    The Black-Scholes formula for a put option is:
        P = K * exp(-rT) * N(-d2) - S * N(-d1)

    where:
        d1 = [ln(S/K) + (r + sigma^2/2)*T] / (sigma*sqrt(T))
        d2 = d1 - sigma*sqrt(T)
        N(x) = cumulative distribution function of standard normal

    Args:
        S: Spot price (current underlying price)
        K: Strike price
        T: Time to expiration in years
        r: Risk-free interest rate (annualized)
        sigma: Implied volatility (annualized)

    Returns:
        Put option price

    Note:
        For expired options (T <= 0), returns intrinsic value max(K - S, 0)

    Example:
        >>> price = black_scholes_put(100, 100, 0.25, 0.02, 0.20)
        >>> price > 0
        True
        >>> price < 100  # Put price less than strike
        True
    """
    S = np.atleast_1d(S)
    K = np.atleast_1d(K)
    T = np.atleast_1d(T)
    sigma = np.atleast_1d(sigma)

    # Handle expired options
    expired = T <= 0
    if np.any(expired):
        result = np.maximum(K - S, 0)
        if np.all(expired):
            return np.squeeze(result)

    # Black-Scholes formula
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    # Put price = K * exp(-rT) * N(-d2) - S * N(-d1)
    put_price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

    # Handle expired options
    if np.any(expired):
        put_price = np.where(expired, np.maximum(K - S, 0), put_price)

    return np.squeeze(put_price)


def black_scholes_put_delta(
    S: Union[float, np.ndarray],
    K: Union[float, np.ndarray],
    T: Union[float, np.ndarray],
    r: float,
    sigma: Union[float, np.ndarray],
) -> Union[float, np.ndarray]:
    """
    Calculate delta of European put option.

    Delta measures the rate of change of option price with respect to
    the underlying asset price.

    For a put option: Delta = N(d1) - 1

    where d1 = [ln(S/K) + (r + sigma^2/2)*T] / (sigma*sqrt(T))

    Args:
        S: Spot price
        K: Strike price
        T: Time to expiration in years
        r: Risk-free interest rate
        sigma: Implied volatility

    Returns:
        Put option delta (between -1 and 0)

    Note:
        For expired options (T <= 0):
            - Delta = 0 if S > K (out-of-the-money)
            - Delta = -1 if S <= K (in-the-money)

    Example:
        >>> delta = black_scholes_put_delta(100, 100, 0.25, 0.02, 0.20)
        >>> -1 < delta < 0
        True
    """
    S = np.atleast_1d(S)
    K = np.atleast_1d(K)
    T = np.atleast_1d(T)
    sigma = np.atleast_1d(sigma)

    # Handle expired options
    expired = T <= 0
    if np.any(expired):
        result = np.where(S > K, 0.0, -1.0)
        if np.all(expired):
            return np.squeeze(result)

    # Calculate d1
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))

    # Put Delta = N(d1) - 1
    delta = norm.cdf(d1) - 1

    # Handle expired options
    if np.any(expired):
        delta = np.where(expired, np.where(S > K, 0.0, -1.0), delta)

    return np.squeeze(delta)


def black_scholes_delta(
    S: Union[float, np.ndarray],
    K: Union[float, np.ndarray],
    T: Union[float, np.ndarray],
    r: float,
    sigma: Union[float, np.ndarray],
) -> Union[float, np.ndarray]:
    """
    Calculate delta of European call option.

    Delta measures the rate of change of option price with respect to
    the underlying asset price.

    For a call option: Delta = N(d1)

    where d1 = [ln(S/K) + (r + sigma^2/2)*T] / (sigma*sqrt(T))

    Args:
        S: Spot price
        K: Strike price
        T: Time to expiration in years
        r: Risk-free interest rate
        sigma: Implied volatility

    Returns:
        Call option delta (between 0 and 1)

    Note:
        For expired options (T <= 0):
            - Delta = 1 if S > K (in-the-money)
            - Delta = 0 if S <= K (out-of-the-money)

    Example:
        >>> delta = black_scholes_delta(100, 100, 0.25, 0.02, 0.20)
        >>> 0 < delta < 1
        True
    """
    S = np.atleast_1d(S)
    K = np.atleast_1d(K)
    T = np.atleast_1d(T)
    sigma = np.atleast_1d(sigma)

    # Handle expired options
    expired = T <= 0
    if np.any(expired):
        result = np.where(S > K, 1.0, 0.0)
        if np.all(expired):
            return np.squeeze(result)

    # Calculate d1
    # d1 = [ln(S/K) + (r + sigma^2/2)*T] / (sigma*sqrt(T))
    # Shape: broadcast to common shape
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))

    # Delta = N(d1)
    # Shape: same as d1
    delta = norm.cdf(d1)

    # Handle expired options
    if np.any(expired):
        delta = np.where(expired, np.where(S > K, 1.0, 0.0), delta)

    return np.squeeze(delta)


def black_scholes_vega(
    S: Union[float, np.ndarray],
    K: Union[float, np.ndarray],
    T: Union[float, np.ndarray],
    r: float,
    sigma: Union[float, np.ndarray],
) -> Union[float, np.ndarray]:
    """
    Calculate vega of European call option.

    Vega measures the rate of change of option price with respect to
    volatility. It's the same for both calls and puts.

    Vega = S * sqrt(T) * N'(d1)

    where:
        N'(x) = standard normal probability density function = exp(-x^2/2) / sqrt(2*pi)
        d1 = [ln(S/K) + (r + sigma^2/2)*T] / (sigma*sqrt(T))

    Args:
        S: Spot price
        K: Strike price
        T: Time to expiration in years
        r: Risk-free interest rate
        sigma: Implied volatility

    Returns:
        Option vega (in units of price change per unit volatility change)

    Note:
        Vega is typically expressed as price change per 1% change in volatility.
        The returned value is per unit (1.0) change in volatility.
        To get vega per 1% volatility change, multiply by 0.01.

    Example:
        >>> vega = black_scholes_vega(100, 100, 0.25, 0.02, 0.20)
        >>> vega > 0
        True
    """
    S = np.atleast_1d(S)
    K = np.atleast_1d(K)
    T = np.atleast_1d(T)
    sigma = np.atleast_1d(sigma)

    # Handle expired options (vega = 0 for expired options)
    expired = T <= 0
    if np.all(expired):
        result = np.zeros_like(S, dtype=float)
        return np.squeeze(result)

    # Calculate d1
    # d1 = [ln(S/K) + (r + sigma^2/2)*T] / (sigma*sqrt(T))
    # Shape: broadcast to common shape
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))

    # Vega = S * sqrt(T) * N'(d1)
    # where N'(d1) = exp(-d1^2/2) / sqrt(2*pi)
    # Shape: same as d1
    vega = S * np.sqrt(T) * norm.pdf(d1)

    # Handle expired options
    if np.any(expired):
        vega = np.where(expired, 0.0, vega)

    return np.squeeze(vega)


def implied_volatility_newton(
    price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    initial_guess: float = 0.2,
    max_iterations: int = 100,
    tolerance: float = 1e-6,
) -> float:
    """
    Calculate implied volatility using Newton-Raphson method.

    Given an observed option price, find the volatility that produces
    that price in the Black-Scholes model.

    Args:
        price: Observed call option price
        S: Spot price
        K: Strike price
        T: Time to expiration in years
        r: Risk-free interest rate
        initial_guess: Starting point for Newton-Raphson (default: 20%)
        max_iterations: Maximum number of iterations
        tolerance: Convergence tolerance

    Returns:
        Implied volatility that produces the observed price

    Raises:
        ValueError: If convergence fails or price is invalid

    Example:
        >>> # Price a call with 20% vol
        >>> true_vol = 0.20
        >>> price = black_scholes_call(100, 100, 0.25, 0.02, true_vol)
        >>> # Recover the volatility
        >>> iv = implied_volatility_newton(price, 100, 100, 0.25, 0.02)
        >>> abs(iv - true_vol) < 1e-4
        True
    """
    # Check for expired option
    if T <= 0:
        raise ValueError("Cannot calculate IV for expired option")

    # Check intrinsic value bounds
    intrinsic = max(S - K * np.exp(-r * T), 0)
    if price < intrinsic - tolerance:
        raise ValueError(f"Price {price} below intrinsic value {intrinsic}")
    if price > S:
        raise ValueError(f"Price {price} above spot {S}")

    # Newton-Raphson iteration
    sigma = initial_guess
    for iteration in range(max_iterations):
        # Calculate price and vega at current sigma
        calc_price = black_scholes_call(S, K, T, r, sigma)
        vega = black_scholes_vega(S, K, T, r, sigma)

        # Check for convergence
        price_diff = calc_price - price
        if abs(price_diff) < tolerance:
            return sigma

        # Check for zero vega (shouldn't happen, but be safe)
        if vega < 1e-10:
            raise ValueError("Vega too small, Newton-Raphson failed")

        # Newton-Raphson update: sigma_new = sigma_old - f(sigma) / f'(sigma)
        sigma = sigma - price_diff / vega

        # Keep sigma positive and reasonable
        sigma = max(0.001, min(sigma, 5.0))

    raise ValueError(f"Implied volatility did not converge after {max_iterations} iterations")


if __name__ == "__main__":
    """Smoke test for option pricing."""
    print("=" * 60)
    print("Option Pricing Smoke Test")
    print("=" * 60)

    # Test parameters
    S = 100.0
    K = 100.0
    T = 0.25  # 3 months
    r = 0.02
    sigma = 0.20

    # Test 1: Basic call pricing
    print("\n[Test 1] Basic Call Pricing")
    call_price = black_scholes_call(S, K, T, r, sigma)
    print(f"  Spot: {S}, Strike: {K}, T: {T}, r: {r}, vol: {sigma}")
    print(f"  Call price: {call_price:.4f}")

    # Test 2: Greeks
    print("\n[Test 2] Greeks Calculation")
    delta = black_scholes_delta(S, K, T, r, sigma)
    vega = black_scholes_vega(S, K, T, r, sigma)
    print(f"  Delta: {delta:.4f}")
    print(f"  Vega: {vega:.4f}")

    # Test 3: ATM vs OTM vs ITM
    print("\n[Test 3] Moneyness Comparison")
    strikes = [80, 90, 100, 110, 120]
    for strike in strikes:
        price = black_scholes_call(S, strike, T, r, sigma)
        delta_val = black_scholes_delta(S, strike, T, r, sigma)
        moneyness = "ITM" if strike < S else ("ATM" if strike == S else "OTM")
        print(f"  K={strike:3d} ({moneyness}): Price={price:6.3f}, Delta={delta_val:.3f}")

    # Test 4: Expired option
    print("\n[Test 4] Expired Option")
    S_exp = 110
    K_exp = 100
    T_exp = 0  # Expired
    price_exp = black_scholes_call(S_exp, K_exp, T_exp, r, sigma)
    intrinsic = max(S_exp - K_exp, 0)
    print(f"  Spot: {S_exp}, Strike: {K_exp}, T: {T_exp}")
    print(f"  Price: {price_exp:.2f}")
    print(f"  Intrinsic value: {intrinsic:.2f}")
    print(f"  Match: {abs(price_exp - intrinsic) < 1e-10}")

    # Test 5: Implied volatility
    print("\n[Test 5] Implied Volatility")
    true_vol = 0.25
    market_price = black_scholes_call(S, K, T, r, true_vol)
    recovered_vol = implied_volatility_newton(market_price, S, K, T, r)
    print(f"  True volatility: {true_vol:.4f}")
    print(f"  Market price: {market_price:.4f}")
    print(f"  Recovered volatility: {recovered_vol:.4f}")
    print(f"  Error: {abs(recovered_vol - true_vol):.6f}")

    # Test 6: Vectorized pricing
    print("\n[Test 6] Vectorized Pricing")
    S_vec = np.array([95, 100, 105])
    K_vec = np.array([100, 100, 100])
    prices_vec = black_scholes_call(S_vec, K_vec, T, r, sigma)
    print(f"  Spots: {S_vec}")
    print(f"  Strikes: {K_vec}")
    print(f"  Prices: {prices_vec}")

    # Test 7: Put-call parity check
    print("\n[Test 7] Bounds Check")
    # Call price should be between intrinsic and spot
    intrinsic_bound = max(S - K * np.exp(-r * T), 0)
    upper_bound = S
    print(f"  Call price: {call_price:.4f}")
    print(f"  Intrinsic bound: {intrinsic_bound:.4f}")
    print(f"  Upper bound (spot): {upper_bound:.4f}")
    print(f"  Within bounds: {intrinsic_bound <= call_price <= upper_bound}")

    print("\n" + "=" * 60)
    print("Smoke test completed successfully!")
    print("=" * 60)
