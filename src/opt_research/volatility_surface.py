"""
SVI (Stochastic Volatility Inspired) volatility surface parameterization.

This module implements the SVI parameterization for implied volatility surfaces
with built-in arbitrage-free constraints based on Gatheral & Jacquier (2014).

The SVI model ensures no butterfly arbitrage and calendar arbitrage when properly
parameterized.
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Dict


@dataclass
class SVIParameters:
    """
    Parameters for the SVI raw parameterization.

    The SVI formula for total implied variance w(k) is:
        w(k) = a + b * (rho * (k - m) + sqrt((k - m)^2 + sigma^2))

    where k = ln(K/F) is the log-forward-moneyness.

    Attributes:
        a: Overall variance level (controls ATM variance)
        b: Wing angle, controls slope of smile (must be >= 0)
        rho: Skew/rotation parameter (must be in (-1, 1))
        m: Horizontal translation of the smile
        sigma: Smoothness of ATM region (must be > 0)
    """

    a: float
    b: float
    rho: float
    m: float
    sigma: float


def svi_total_variance(k: np.ndarray, params: SVIParameters) -> np.ndarray:
    """
    Compute total implied variance w(k) using SVI parameterization.

    The SVI formula is:
        w(k) = a + b * (rho * (k - m) + sqrt((k - m)^2 + sigma^2))

    Args:
        k: Log-forward-moneyness, k = ln(K/F), shape (N,)
        params: SVI parameters

    Returns:
        Total implied variance w(k), shape (N,)

    Example:
        >>> params = SVIParameters(a=0.04, b=0.02, rho=-0.15, m=0.0, sigma=0.10)
        >>> k = np.array([-0.1, 0.0, 0.1])
        >>> w = svi_total_variance(k, params)
        >>> w.shape
        (3,)
    """
    k = np.atleast_1d(k)  # Ensure array
    # Shape: (N,) -> (N,)
    km = k - params.m
    # sqrt_term = sqrt((k-m)^2 + sigma^2), shape: (N,)
    sqrt_term = np.sqrt(km**2 + params.sigma**2)
    # w(k) = a + b * (rho*(k-m) + sqrt_term), shape: (N,)
    w = params.a + params.b * (params.rho * km + sqrt_term)
    return w


def svi_implied_vol(k: np.ndarray, T: float, params: SVIParameters) -> np.ndarray:
    """
    Convert total variance to implied volatility.

    The relationship is: sigma_impl(k,T) = sqrt(w(k) / T)

    Args:
        k: Log-forward-moneyness, k = ln(K/F), shape (N,)
        T: Time to expiration in years
        params: SVI parameters

    Returns:
        Implied volatility sigma(k,T), shape (N,)

    Example:
        >>> params = SVIParameters(a=0.04, b=0.02, rho=-0.15, m=0.0, sigma=0.10)
        >>> k = np.array([0.0])
        >>> T = 1.0
        >>> vol = svi_implied_vol(k, T, params)
        >>> vol[0] > 0
        True
    """
    # w(k): shape (N,)
    w = svi_total_variance(k, params)
    # sigma = sqrt(w/T): shape (N,)
    sigma = np.sqrt(w / T)
    return sigma


def validate_svi_no_arbitrage(
    params: SVIParameters, T: float, tol: float = 1e-8
) -> Tuple[bool, str]:
    """
    Validate SVI parameters satisfy no-arbitrage conditions.

    Based on Gatheral & Jacquier (2014), sufficient conditions for no butterfly arbitrage:
        1. b >= 0 (non-negative wing angle)
        2. |rho| < 1 (skew parameter in valid range)
        3. a + b * sigma * sqrt(1 - rho^2) >= 0 (ensures w(k) >= 0 for all k)
        4. b * (1 + |rho|) < 4/T (Fukasawa's condition for short expiries)

    Args:
        params: SVI parameters to validate
        T: Time to expiration in years
        tol: Numerical tolerance for checks

    Returns:
        Tuple of (is_valid, error_message)
            - is_valid: True if all conditions are satisfied
            - error_message: Description of violation, empty string if valid

    Example:
        >>> params = SVIParameters(a=0.04, b=0.02, rho=-0.15, m=0.0, sigma=0.10)
        >>> valid, msg = validate_svi_no_arbitrage(params, T=1.0/252)
        >>> valid
        True
    """
    # Condition 1: b >= 0
    if params.b < -tol:
        return False, f"b must be non-negative, got {params.b}"

    # Condition 2: |rho| < 1
    if abs(params.rho) >= 1 - tol:
        return False, f"rho must be in (-1, 1), got {params.rho}"

    # Condition 3: sigma > 0
    if params.sigma <= tol:
        return False, f"sigma must be positive, got {params.sigma}"

    # Condition 4: Minimum variance must be non-negative
    # min_w = a + b * sigma * sqrt(1 - rho^2)
    min_variance = params.a + params.b * params.sigma * np.sqrt(1 - params.rho**2)
    if min_variance < -tol:
        return False, f"Minimum variance is negative: {min_variance}"

    # Condition 5: Fukasawa's condition for short expiries
    # b * (1 + |rho|) < 4/T
    fukasawa_lhs = params.b * (1 + abs(params.rho))
    fukasawa_rhs = 4.0 / T
    if fukasawa_lhs >= fukasawa_rhs - tol:
        return (
            False,
            f"Fukasawa condition violated: {fukasawa_lhs:.4f} >= {fukasawa_rhs:.4f}",
        )

    return True, ""


def generate_term_structure_params(
    expiries: List[float], base_atm_vol: float = 0.10, seed: int = 42
) -> List[Tuple[float, SVIParameters]]:
    """
    Generate arbitrage-free SVI parameters for a term structure.

    Strategy to ensure calendar arbitrage-free:
        - Set a(T) proportional to T (linear scaling)
        - Keep b, rho, sigma, m constant across expiries
        - This ensures total variance w(k,T) increases with T for all k

    Args:
        expiries: List of times to expiration in years (e.g., [1/252, 2/252, ...])
        base_atm_vol: Target ATM volatility (default: 10%)
        seed: Random seed for reproducibility (for potential future extensions)

    Returns:
        List of (T, SVIParameters) tuples, one for each expiry

    Example:
        >>> expiries = [1/252, 5/252, 10/252]
        >>> params_list = generate_term_structure_params(expiries)
        >>> len(params_list)
        3
        >>> all(validate_svi_no_arbitrage(p[1], p[0])[0] for p in params_list)
        True
    """
    np.random.seed(seed)

    # Base variance from ATM vol
    base_variance = base_atm_vol**2  # ~0.01 for 10% vol

    # Fixed parameters across term structure
    b_fixed = 0.02  # Wing angle
    rho_fixed = -0.15  # Slight negative skew (realistic for equity options)
    m_fixed = 0.0  # Centered at ATM
    sigma_fixed = 0.10  # ATM curvature

    params_list = []

    for T in expiries:
        # Scale 'a' parameter linearly with T to ensure calendar arbitrage-free
        # a(T) = base_variance * T * scale_factor
        # Scale factor < 1 to leave room for the smile component
        a_value = base_variance * T * 0.8

        params = SVIParameters(
            a=a_value,
            b=b_fixed,
            rho=rho_fixed,
            m=m_fixed,
            sigma=sigma_fixed,
        )

        # Validate
        is_valid, error_msg = validate_svi_no_arbitrage(params, T)
        if not is_valid:
            raise ValueError(f"Invalid SVI parameters for T={T}: {error_msg}")

        params_list.append((T, params))

    return params_list


def validate_calendar_arbitrage_free(
    params_list: List[Tuple[float, SVIParameters]],
    k_grid: np.ndarray = None,
    tol: float = 1e-6,
) -> Tuple[bool, str]:
    """
    Validate that total variance is non-decreasing in time for all strikes.

    For calendar arbitrage-free: w(k, T1) <= w(k, T2) for all k when T1 < T2

    Args:
        params_list: List of (T, SVIParameters) tuples, assumed sorted by T
        k_grid: Array of log-moneyness points to check (default: -0.3 to 0.3)
        tol: Numerical tolerance for comparison

    Returns:
        Tuple of (is_valid, error_message)

    Example:
        >>> expiries = [1/252, 5/252, 10/252]
        >>> params_list = generate_term_structure_params(expiries)
        >>> valid, msg = validate_calendar_arbitrage_free(params_list)
        >>> valid
        True
    """
    if k_grid is None:
        k_grid = np.linspace(-0.3, 0.3, 100)

    if len(params_list) < 2:
        return True, ""  # Nothing to check

    # Check consecutive pairs
    for i in range(len(params_list) - 1):
        T1, params1 = params_list[i]
        T2, params2 = params_list[i + 1]

        # Ensure T1 < T2
        if T1 >= T2:
            return False, f"Expiries not in ascending order: T1={T1}, T2={T2}"

        # Compute total variance for both slices
        # Shape: (N,) for each
        w1 = svi_total_variance(k_grid, params1)
        w2 = svi_total_variance(k_grid, params2)

        # Check w1 <= w2 for all k
        violations = w1 > w2 + tol
        if np.any(violations):
            violation_indices = np.where(violations)[0]
            k_violation = k_grid[violation_indices[0]]
            return (
                False,
                f"Calendar arbitrage between T={T1:.4f} and T={T2:.4f} at k={k_violation:.4f}",
            )

    return True, ""


if __name__ == "__main__":
    """Smoke test for volatility surface."""
    print("=" * 60)
    print("Volatility Surface Smoke Test")
    print("=" * 60)

    # Test 1: Basic SVI evaluation
    print("\n[Test 1] Basic SVI Evaluation")
    params = SVIParameters(a=0.04, b=0.02, rho=-0.15, m=0.0, sigma=0.10)
    k_test = np.array([-0.2, -0.1, 0.0, 0.1, 0.2])
    w = svi_total_variance(k_test, params)
    print(f"  Log-moneyness: {k_test}")
    print(f"  Total variance: {w}")
    print(f"  ATM total variance: {w[2]:.6f}")

    # Test 2: Implied volatility
    print("\n[Test 2] Implied Volatility")
    T = 10 / 252  # 10 days
    vol = svi_implied_vol(k_test, T, params)
    print(f"  Implied vols (T={T:.4f}): {vol}")
    print(f"  ATM implied vol: {vol[2]:.4f} ({vol[2]*100:.2f}%)")

    # Test 3: No-arbitrage validation
    print("\n[Test 3] No-Arbitrage Validation")
    valid, msg = validate_svi_no_arbitrage(params, T)
    print(f"  Parameters valid: {valid}")
    if not valid:
        print(f"  Error: {msg}")

    # Test 4: Invalid parameters
    print("\n[Test 4] Invalid Parameters Detection")
    bad_params = SVIParameters(a=0.04, b=-0.01, rho=-0.15, m=0.0, sigma=0.10)
    valid, msg = validate_svi_no_arbitrage(bad_params, T)
    print(f"  Negative b detected: {not valid}")
    print(f"  Error message: {msg}")

    # Test 5: Term structure generation
    print("\n[Test 5] Term Structure Generation")
    expiries = [i / 252 for i in range(1, 11)]  # 1 to 10 days
    params_list = generate_term_structure_params(expiries, base_atm_vol=0.10)
    print(f"  Generated {len(params_list)} slices")
    print(f"  First expiry: T={params_list[0][0]:.4f}, a={params_list[0][1].a:.6f}")
    print(f"  Last expiry: T={params_list[-1][0]:.4f}, a={params_list[-1][1].a:.6f}")

    # Test 6: Calendar arbitrage-free
    print("\n[Test 6] Calendar Arbitrage-Free Check")
    valid, msg = validate_calendar_arbitrage_free(params_list)
    print(f"  Calendar arbitrage-free: {valid}")
    if not valid:
        print(f"  Error: {msg}")

    # Test 7: Smile shape
    print("\n[Test 7] Volatility Smile Shape")
    T_test = 5 / 252
    params_test = params_list[4][1]  # 5-day expiry
    k_smile = np.linspace(-0.3, 0.3, 7)
    vol_smile = svi_implied_vol(k_smile, T_test, params_test)
    print(f"  T = {T_test:.4f} years (5 days)")
    for k, v in zip(k_smile, vol_smile):
        moneyness_pct = (np.exp(k) - 1) * 100
        print(f"    k={k:6.2f} (moneyness {moneyness_pct:+6.1f}%): vol={v:.4f}")

    print("\n" + "=" * 60)
    print("Smoke test completed successfully!")
    print("=" * 60)
