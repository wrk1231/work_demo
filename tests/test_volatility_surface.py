"""Tests for SVI volatility surface module."""

import numpy as np
import pytest

from opt_research.volatility_surface import (
    SVIParameters,
    svi_total_variance,
    svi_implied_vol,
    validate_svi_no_arbitrage,
    generate_term_structure_params,
    validate_calendar_arbitrage_free,
)


class TestSVITotalVariance:
    """Test cases for SVI total variance calculation."""

    def test_basic_evaluation(self):
        """Test basic SVI variance calculation."""
        params = SVIParameters(a=0.04, b=0.02, rho=-0.15, m=0.0, sigma=0.10)
        k = np.array([0.0])

        w = svi_total_variance(k, params)

        assert len(w) == 1
        assert w[0] > 0  # Variance should be positive

    def test_atm_variance(self):
        """Test that ATM (k=m) variance equals a + b*sigma."""
        params = SVIParameters(a=0.04, b=0.02, rho=-0.15, m=0.0, sigma=0.10)
        k = np.array([0.0])  # ATM when m=0

        w = svi_total_variance(k, params)
        expected = params.a + params.b * params.sigma

        np.testing.assert_almost_equal(w[0], expected, decimal=10)

    def test_vectorized(self):
        """Test vectorized evaluation."""
        params = SVIParameters(a=0.04, b=0.02, rho=-0.15, m=0.0, sigma=0.10)
        k = np.array([-0.2, -0.1, 0.0, 0.1, 0.2])

        w = svi_total_variance(k, params)

        assert len(w) == 5
        assert np.all(w > 0)

    def test_symmetry_with_zero_rho(self):
        """Test that with rho=0, variance is symmetric around m."""
        params = SVIParameters(a=0.04, b=0.02, rho=0.0, m=0.0, sigma=0.10)
        k = np.array([-0.1, 0.1])

        w = svi_total_variance(k, params)

        np.testing.assert_almost_equal(w[0], w[1], decimal=10)


class TestSVIImpliedVol:
    """Test cases for SVI implied volatility."""

    def test_volatility_from_variance(self):
        """Test conversion from total variance to implied vol."""
        params = SVIParameters(a=0.04, b=0.02, rho=-0.15, m=0.0, sigma=0.10)
        k = np.array([0.0])
        T = 1.0

        vol = svi_implied_vol(k, T, params)
        w = svi_total_variance(k, params)

        np.testing.assert_almost_equal(vol[0] ** 2 * T, w[0], decimal=10)

    def test_positive_volatility(self):
        """Test that implied volatility is always positive."""
        params = SVIParameters(a=0.04, b=0.02, rho=-0.15, m=0.0, sigma=0.10)
        k = np.linspace(-0.3, 0.3, 20)
        T = 0.1

        vol = svi_implied_vol(k, T, params)

        assert np.all(vol > 0)


class TestValidateSVINoArbitrage:
    """Test cases for SVI no-arbitrage validation."""

    def test_valid_parameters(self):
        """Test that valid parameters pass validation."""
        params = SVIParameters(a=0.04, b=0.02, rho=-0.15, m=0.0, sigma=0.10)
        T = 10 / 252  # 10 days

        is_valid, msg = validate_svi_no_arbitrage(params, T)

        assert is_valid
        assert msg == ""

    def test_negative_b(self):
        """Test that negative b is detected."""
        params = SVIParameters(a=0.04, b=-0.01, rho=-0.15, m=0.0, sigma=0.10)
        T = 10 / 252

        is_valid, msg = validate_svi_no_arbitrage(params, T)

        assert not is_valid
        assert "non-negative" in msg.lower()

    def test_rho_out_of_bounds(self):
        """Test that |rho| >= 1 is detected."""
        params = SVIParameters(a=0.04, b=0.02, rho=1.0, m=0.0, sigma=0.10)
        T = 10 / 252

        is_valid, msg = validate_svi_no_arbitrage(params, T)

        assert not is_valid
        assert "rho" in msg.lower()

    def test_negative_sigma(self):
        """Test that negative sigma is detected."""
        params = SVIParameters(a=0.04, b=0.02, rho=-0.15, m=0.0, sigma=-0.10)
        T = 10 / 252

        is_valid, msg = validate_svi_no_arbitrage(params, T)

        assert not is_valid
        assert "positive" in msg.lower()

    def test_fukasawa_condition(self):
        """Test Fukasawa condition for short expiries."""
        # Create parameters that violate Fukasawa: b*(1+|rho|) >= 4/T
        T = 1 / 252  # 1 day, so 4/T ≈ 1008
        b_bad = 1000.0  # Large b to violate b*(1+|ρ|) < 4/T
        params = SVIParameters(a=0.04, b=b_bad, rho=-0.8, m=0.0, sigma=0.10)
        # b*(1+|ρ|) = 1000 * 1.8 = 1800 > 1008, violates condition

        is_valid, msg = validate_svi_no_arbitrage(params, T)

        assert not is_valid
        assert "fukasawa" in msg.lower()


class TestGenerateTermStructureParams:
    """Test cases for term structure generation."""

    def test_correct_number_of_slices(self):
        """Test that correct number of slices are generated."""
        expiries = [1 / 252, 5 / 252, 10 / 252]
        params_list = generate_term_structure_params(expiries)

        assert len(params_list) == 3

    def test_all_valid(self):
        """Test that all generated parameters are valid."""
        expiries = [i / 252 for i in range(1, 11)]
        params_list = generate_term_structure_params(expiries)

        for T, params in params_list:
            is_valid, msg = validate_svi_no_arbitrage(params, T)
            assert is_valid, f"Invalid params for T={T}: {msg}"

    def test_increasing_a_parameter(self):
        """Test that 'a' parameter increases with time."""
        expiries = [i / 252 for i in range(1, 11)]
        params_list = generate_term_structure_params(expiries)

        a_values = [params.a for _, params in params_list]

        # Check that a is increasing
        for i in range(len(a_values) - 1):
            assert a_values[i] < a_values[i + 1]

    def test_constant_other_parameters(self):
        """Test that b, rho, sigma, m remain constant."""
        expiries = [i / 252 for i in range(1, 11)]
        params_list = generate_term_structure_params(expiries)

        b_values = [params.b for _, params in params_list]
        rho_values = [params.rho for _, params in params_list]

        # All b values should be equal
        assert len(set(b_values)) == 1
        # All rho values should be equal
        assert len(set(rho_values)) == 1


class TestValidateCalendarArbitrageFree:
    """Test cases for calendar arbitrage validation."""

    def test_valid_term_structure(self):
        """Test that properly generated term structure is calendar arbitrage-free."""
        expiries = [i / 252 for i in range(1, 11)]
        params_list = generate_term_structure_params(expiries)

        is_valid, msg = validate_calendar_arbitrage_free(params_list)

        assert is_valid
        assert msg == ""

    def test_empty_list(self):
        """Test that empty list is considered valid."""
        is_valid, msg = validate_calendar_arbitrage_free([])

        assert is_valid

    def test_single_expiry(self):
        """Test that single expiry is valid (nothing to compare)."""
        expiries = [5 / 252]
        params_list = generate_term_structure_params(expiries)

        is_valid, msg = validate_calendar_arbitrage_free(params_list)

        assert is_valid

    def test_wide_moneyness_range(self):
        """Test calendar arbitrage check across wide moneyness range."""
        expiries = [1 / 252, 10 / 252]
        params_list = generate_term_structure_params(expiries)
        k_grid = np.linspace(-0.5, 0.5, 200)

        is_valid, msg = validate_calendar_arbitrage_free(params_list, k_grid)

        assert is_valid


class TestSVISmileProperties:
    """Test cases for volatility smile properties."""

    def test_negative_skew(self):
        """Test that negative rho produces downward sloping smile."""
        params = SVIParameters(a=0.04, b=0.02, rho=-0.3, m=0.0, sigma=0.10)
        k = np.array([-0.2, 0.0, 0.2])  # OTM put, ATM, OTM call
        T = 10 / 252

        vols = svi_implied_vol(k, T, params)

        # With negative skew, OTM puts (k<0) should have higher vol than OTM calls (k>0)
        assert vols[0] > vols[2]

    def test_positive_skew(self):
        """Test that positive rho produces upward sloping smile."""
        params = SVIParameters(a=0.04, b=0.02, rho=0.3, m=0.0, sigma=0.10)
        k = np.array([-0.2, 0.0, 0.2])
        T = 10 / 252

        vols = svi_implied_vol(k, T, params)

        # With positive skew, OTM calls should have higher vol than OTM puts
        assert vols[2] > vols[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
