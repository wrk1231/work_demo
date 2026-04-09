"""Tests for Black-Scholes option pricing module."""

import numpy as np
import pytest

from opt_research.option_pricing import (
    black_scholes_call,
    black_scholes_delta,
    black_scholes_put,
    black_scholes_put_delta,
    black_scholes_vega,
    implied_volatility_newton,
)


class TestBlackScholesCall:
    """Test cases for Black-Scholes call pricing."""

    def test_atm_option(self):
        """Test pricing of at-the-money option."""
        price = black_scholes_call(S=100, K=100, T=0.25, r=0.02, sigma=0.20)

        assert price > 0
        assert price < 100  # Call price must be less than spot

    def test_deep_itm(self):
        """Test that deep ITM call approaches intrinsic value."""
        S, K = 100, 50
        price = black_scholes_call(S=S, K=K, T=0.25, r=0.02, sigma=0.20)
        intrinsic = S - K

        assert price > intrinsic
        assert price < S

    def test_deep_otm(self):
        """Test that deep OTM call has small value."""
        price = black_scholes_call(S=100, K=150, T=0.25, r=0.02, sigma=0.20)

        assert price > 0
        assert price < 5  # Should be relatively small

    def test_expired_option_itm(self):
        """Test expired ITM option returns intrinsic value."""
        S, K = 110, 100
        price = black_scholes_call(S=S, K=K, T=0, r=0.02, sigma=0.20)

        assert price == max(S - K, 0)

    def test_expired_option_otm(self):
        """Test expired OTM option returns zero."""
        price = black_scholes_call(S=90, K=100, T=0, r=0.02, sigma=0.20)

        assert price == 0

    def test_vectorized_pricing(self):
        """Test vectorized pricing for multiple strikes."""
        S = 100
        K = np.array([90, 95, 100, 105, 110])
        prices = black_scholes_call(S=S, K=K, T=0.25, r=0.02, sigma=0.20)

        assert len(prices) == 5
        # Prices should decrease with strike
        assert all(prices[i] >= prices[i + 1] for i in range(len(prices) - 1))

    def test_price_increases_with_vol(self):
        """Test that option price increases with volatility."""
        S, K, T, r = 100, 100, 0.25, 0.02

        price_low_vol = black_scholes_call(S, K, T, r, sigma=0.10)
        price_high_vol = black_scholes_call(S, K, T, r, sigma=0.30)

        assert price_high_vol > price_low_vol

    def test_price_increases_with_time(self):
        """Test that option price increases with time to expiry."""
        S, K, r, sigma = 100, 100, 0.02, 0.20

        price_short = black_scholes_call(S, K, T=0.1, r=r, sigma=sigma)
        price_long = black_scholes_call(S, K, T=0.5, r=r, sigma=sigma)

        assert price_long > price_short


class TestBlackScholesDelta:
    """Test cases for Black-Scholes call delta calculation."""

    def test_atm_delta_approx_half(self):
        """Test that ATM call delta is approximately 0.5."""
        delta = black_scholes_delta(S=100, K=100, T=0.25, r=0.02, sigma=0.20)

        assert 0.4 < delta < 0.6

    def test_deep_itm_delta_near_one(self):
        """Test that deep ITM call has delta near 1."""
        delta = black_scholes_delta(S=100, K=50, T=0.25, r=0.02, sigma=0.20)

        assert delta > 0.95

    def test_deep_otm_delta_near_zero(self):
        """Test that deep OTM call has delta near 0."""
        delta = black_scholes_delta(S=100, K=150, T=0.25, r=0.02, sigma=0.20)

        assert delta < 0.05

    def test_delta_bounds(self):
        """Test that delta is always between 0 and 1."""
        deltas = black_scholes_delta(
            S=100, K=np.array([80, 90, 100, 110, 120]), T=0.25, r=0.02, sigma=0.20
        )

        assert np.all(deltas >= 0)
        assert np.all(deltas <= 1)

    def test_expired_itm_delta(self):
        """Test expired ITM option has delta = 1."""
        delta = black_scholes_delta(S=110, K=100, T=0, r=0.02, sigma=0.20)

        assert delta == 1.0

    def test_expired_otm_delta(self):
        """Test expired OTM option has delta = 0."""
        delta = black_scholes_delta(S=90, K=100, T=0, r=0.02, sigma=0.20)

        assert delta == 0.0


class TestBlackScholesPut:
    """Test cases for Black-Scholes put pricing."""

    def test_atm_option(self):
        """Test pricing of at-the-money put option."""
        price = black_scholes_put(S=100, K=100, T=0.25, r=0.02, sigma=0.20)

        assert price > 0
        assert price < 100  # Put price must be less than strike

    def test_deep_itm(self):
        """Test that deep ITM put approaches intrinsic value."""
        S, K = 50, 100
        price = black_scholes_put(S=S, K=K, T=0.25, r=0.02, sigma=0.20)
        intrinsic = K - S

        assert price > intrinsic * 0.9  # Allow for time value
        assert price < K

    def test_deep_otm(self):
        """Test that deep OTM put has small value."""
        price = black_scholes_put(S=150, K=100, T=0.25, r=0.02, sigma=0.20)

        assert price > 0
        assert price < 5  # Should be relatively small

    def test_expired_option_itm(self):
        """Test expired ITM put returns intrinsic value."""
        S, K = 90, 100
        price = black_scholes_put(S=S, K=K, T=0, r=0.02, sigma=0.20)

        assert price == max(K - S, 0)

    def test_expired_option_otm(self):
        """Test expired OTM put returns zero."""
        price = black_scholes_put(S=110, K=100, T=0, r=0.02, sigma=0.20)

        assert price == 0

    def test_vectorized_pricing(self):
        """Test vectorized pricing for multiple strikes."""
        S = 100
        K = np.array([90, 95, 100, 105, 110])
        prices = black_scholes_put(S=S, K=K, T=0.25, r=0.02, sigma=0.20)

        assert len(prices) == 5
        # Put prices should increase with strike
        assert all(prices[i] <= prices[i + 1] for i in range(len(prices) - 1))

    def test_price_increases_with_vol(self):
        """Test that put price increases with volatility."""
        S, K, T, r = 100, 100, 0.25, 0.02

        price_low_vol = black_scholes_put(S, K, T, r, sigma=0.10)
        price_high_vol = black_scholes_put(S, K, T, r, sigma=0.30)

        assert price_high_vol > price_low_vol


class TestBlackScholesPutDelta:
    """Test cases for Black-Scholes put delta calculation."""

    def test_atm_delta_approx_minus_half(self):
        """Test that ATM put delta is approximately -0.5."""
        delta = black_scholes_put_delta(S=100, K=100, T=0.25, r=0.02, sigma=0.20)

        assert -0.6 < delta < -0.4

    def test_deep_itm_delta_near_minus_one(self):
        """Test that deep ITM put has delta near -1."""
        delta = black_scholes_put_delta(S=50, K=100, T=0.25, r=0.02, sigma=0.20)

        assert delta < -0.95

    def test_deep_otm_delta_near_zero(self):
        """Test that deep OTM put has delta near 0."""
        delta = black_scholes_put_delta(S=150, K=100, T=0.25, r=0.02, sigma=0.20)

        assert delta > -0.05

    def test_delta_bounds(self):
        """Test that put delta is always between -1 and 0."""
        deltas = black_scholes_put_delta(
            S=100, K=np.array([80, 90, 100, 110, 120]), T=0.25, r=0.02, sigma=0.20
        )

        assert np.all(deltas <= 0)
        assert np.all(deltas >= -1)

    def test_expired_itm_delta(self):
        """Test expired ITM put has delta = -1."""
        delta = black_scholes_put_delta(S=90, K=100, T=0, r=0.02, sigma=0.20)

        assert delta == -1.0

    def test_expired_otm_delta(self):
        """Test expired OTM put has delta = 0."""
        delta = black_scholes_put_delta(S=110, K=100, T=0, r=0.02, sigma=0.20)

        assert delta == 0.0

    def test_put_call_delta_parity(self):
        """Test that call delta - put delta = 1."""
        S, K, T, r, sigma = 100, 100, 0.25, 0.02, 0.20
        call_delta = black_scholes_delta(S, K, T, r, sigma)
        put_delta = black_scholes_put_delta(S, K, T, r, sigma)

        assert abs((call_delta - put_delta) - 1.0) < 1e-10


class TestBlackScholesVega:
    """Test cases for Black-Scholes vega calculation."""

    def test_vega_positive(self):
        """Test that vega is always positive."""
        vega = black_scholes_vega(S=100, K=100, T=0.25, r=0.02, sigma=0.20)

        assert vega > 0

    def test_atm_has_highest_vega(self):
        """Test that ATM options have highest vega."""
        S = 100
        vegas = black_scholes_vega(
            S=S, K=np.array([80, 90, 100, 110, 120]), T=0.25, r=0.02, sigma=0.20
        )

        atm_index = 2  # K=100
        assert vegas[atm_index] == max(vegas)

    def test_vega_decreases_near_expiry(self):
        """Test that vega decreases as expiry approaches."""
        S, K, r, sigma = 100, 100, 0.02, 0.20

        vega_long = black_scholes_vega(S, K, T=0.5, r=r, sigma=sigma)
        vega_short = black_scholes_vega(S, K, T=0.1, r=r, sigma=sigma)

        assert vega_long > vega_short

    def test_expired_option_zero_vega(self):
        """Test that expired option has zero vega."""
        vega = black_scholes_vega(S=100, K=100, T=0, r=0.02, sigma=0.20)

        assert vega == 0.0


class TestImpliedVolatility:
    """Test cases for implied volatility calculation."""

    def test_recover_known_vol(self):
        """Test that we can recover a known volatility."""
        S, K, T, r = 100, 100, 0.25, 0.02
        true_vol = 0.25

        price = black_scholes_call(S, K, T, r, true_vol)
        recovered_vol = implied_volatility_newton(price, S, K, T, r)

        assert abs(recovered_vol - true_vol) < 1e-4

    def test_itm_option(self):
        """Test IV calculation for ITM option."""
        S, K, T, r = 110, 100, 0.25, 0.02
        true_vol = 0.20

        price = black_scholes_call(S, K, T, r, true_vol)
        recovered_vol = implied_volatility_newton(price, S, K, T, r)

        assert abs(recovered_vol - true_vol) < 1e-4

    def test_otm_option(self):
        """Test IV calculation for OTM option."""
        S, K, T, r = 90, 100, 0.25, 0.02
        true_vol = 0.30

        price = black_scholes_call(S, K, T, r, true_vol)
        recovered_vol = implied_volatility_newton(price, S, K, T, r)

        assert abs(recovered_vol - true_vol) < 1e-4

    def test_price_below_intrinsic_raises_error(self):
        """Test that price below intrinsic value raises error."""
        S, K, T, r = 110, 100, 0.25, 0.02
        intrinsic = S - K * np.exp(-r * T)
        invalid_price = intrinsic - 1  # Below intrinsic

        with pytest.raises(ValueError, match="below intrinsic"):
            implied_volatility_newton(invalid_price, S, K, T, r)

    def test_price_above_spot_raises_error(self):
        """Test that price above spot raises error."""
        S, K, T, r = 100, 100, 0.25, 0.02
        invalid_price = S + 1  # Above spot

        with pytest.raises(ValueError, match="above spot"):
            implied_volatility_newton(invalid_price, S, K, T, r)

    def test_expired_option_raises_error(self):
        """Test that expired option raises error."""
        with pytest.raises(ValueError, match="expired"):
            implied_volatility_newton(5.0, 100, 100, 0, 0.02)


class TestBlackScholesConsistency:
    """Test consistency properties of Black-Scholes model."""

    def test_put_call_parity(self):
        """Test that put-call parity holds: C - P = S - K*exp(-rT)."""
        S, K, T, r, sigma = 100, 100, 0.25, 0.02, 0.20

        call_price = black_scholes_call(S, K, T, r, sigma)
        put_price = black_scholes_put(S, K, T, r, sigma)

        # C - P = S - K*exp(-rT)
        lhs = call_price - put_price
        rhs = S - K * np.exp(-r * T)

        assert abs(lhs - rhs) < 1e-10

    def test_put_call_parity_bounds(self):
        """Test that call price satisfies bounds."""
        S, K, T, r, sigma = 100, 100, 0.25, 0.02, 0.20

        call_price = black_scholes_call(S, K, T, r, sigma)
        intrinsic = max(S - K * np.exp(-r * T), 0)

        # Call should be above intrinsic and below spot
        assert call_price >= intrinsic
        assert call_price <= S

    def test_monotonicity_in_strike(self):
        """Test that call prices decrease with strike."""
        S, T, r, sigma = 100, 0.25, 0.02, 0.20
        strikes = np.array([90, 95, 100, 105, 110])

        prices = black_scholes_call(S, strikes, T, r, sigma)

        # Verify monotonically decreasing
        for i in range(len(prices) - 1):
            assert prices[i] >= prices[i + 1]

    def test_convexity_no_butterfly(self):
        """Test that call prices satisfy convexity (no butterfly arbitrage)."""
        S, T, r, sigma = 100, 0.25, 0.02, 0.20
        strikes = np.array([95, 100, 105])

        prices = black_scholes_call(S, strikes, T, r, sigma)

        # Butterfly: C(K1) - 2*C(K2) + C(K3) >= 0
        butterfly = prices[0] - 2 * prices[1] + prices[2]
        assert butterfly >= -1e-10  # Allow small numerical error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
