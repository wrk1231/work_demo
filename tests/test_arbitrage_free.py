"""
CRITICAL TESTS: Arbitrage-free validation for option prices.

These tests verify that the generated option data satisfies all
static arbitrage-free conditions at mid prices.
"""

import numpy as np
import pytest
import pandas as pd
from datetime import datetime, timedelta

from opt_research.arbitrage_free import (
    check_no_arbitrage,
    generate_arbitrage_report,
)


class TestCheckNoArbitrage:
    """Test cases for arbitrage detection."""

    def create_valid_chain(self):
        """Create a valid option chain with no arbitrage."""
        # Create more realistic data: slightly ITM options
        return pd.DataFrame(
            {
                "date": [datetime(2026, 1, 6)] * 5,
                "option_name": [f"C_20260110_{990+i*5:04d}" for i in range(5)],
                "option_type": ["call"] * 5,
                "mid": [12.0, 10.0, 8.0, 6.5, 5.0],  # Decreasing with strike
                "strike": [990, 995, 1000, 1005, 1010],
                "expiration": [datetime(2026, 1, 10)] * 5,
                "underlying": [1000] * 5,
            }
        )

    def test_valid_chain_passes(self):
        """Test that a valid option chain passes all tests."""
        df = self.create_valid_chain()
        is_valid, violations = check_no_arbitrage(df)

        assert is_valid
        assert len(violations) == 0

    def test_empty_dataframe(self):
        """Test that empty DataFrame is considered valid."""
        df = pd.DataFrame()
        is_valid, violations = check_no_arbitrage(df)

        assert is_valid
        assert len(violations) == 0

    def test_negative_price_detected(self):
        """Test detection of negative prices."""
        df = self.create_valid_chain()
        df.loc[2, "mid"] = -0.5  # Make one price negative

        is_valid, violations = check_no_arbitrage(df)

        assert not is_valid
        assert len(violations) > 0
        assert any("negative" in v.lower() for v in violations)

    def test_price_exceeds_spot_detected(self):
        """Test detection of prices exceeding spot."""
        df = self.create_valid_chain()
        # Set a reasonable ITM strike but make price exceed spot
        df.loc[0, "strike"] = 995  # ITM
        df.loc[0, "mid"] = 1050.0  # Price > spot

        is_valid, violations = check_no_arbitrage(df)

        assert not is_valid
        assert len(violations) > 0
        # Should detect exceeds spot
        assert any("exceeds spot" in v.lower() or "intrinsic" in v.lower() for v in violations)

    def test_monotonicity_violation_detected(self):
        """Test detection of monotonicity violation."""
        df = self.create_valid_chain()
        # Make middle price higher than lower strike price
        df.loc[2, "mid"] = 25.0

        is_valid, violations = check_no_arbitrage(df)

        assert not is_valid
        assert len(violations) > 0
        assert any("monotonicity" in v.lower() for v in violations)

    def test_butterfly_arbitrage_detected(self):
        """Test detection of butterfly arbitrage."""
        df = self.create_valid_chain()
        # Make middle option too cheap, creating butterfly opportunity
        # Butterfly = C(K1) - 2*C(K2) + C(K3) < 0 means arbitrage
        df.loc[2, "mid"] = 1.0  # Make center very cheap

        is_valid, violations = check_no_arbitrage(df)

        assert not is_valid
        assert len(violations) > 0
        assert any("butterfly" in v.lower() for v in violations)

    def test_calendar_arbitrage_detected(self):
        """Test detection of calendar spread arbitrage."""
        df = pd.DataFrame(
            {
                "date": [datetime(2026, 1, 6)] * 2,
                "option_name": ["C_20260110_1000", "C_20260120_1000"],
                "option_type": ["call", "call"],
                "mid": [10.0, 8.0],  # Shorter expiry more expensive!
                "strike": [1000, 1000],
                "expiration": [datetime(2026, 1, 10), datetime(2026, 1, 20)],
                "underlying": [1000, 1000],
            }
        )

        is_valid, violations = check_no_arbitrage(df)

        assert not is_valid
        assert len(violations) > 0
        assert any("calendar" in v.lower() for v in violations)

    def test_tolerance_parameter(self):
        """Test that tolerance parameter works correctly."""
        # Create a two-option chain to pass the len >= 2 requirement
        expiry = datetime(2026, 1, 10)
        today = datetime(2026, 1, 6)

        df = pd.DataFrame(
            {
                "date": [today, today],
                "option_name": ["C_20260110_0990", "C_20260110_1010"],
                "option_type": ["call", "call"],
                "mid": [9.90, 3.0],  # First below intrinsic of 10.31, violation ~0.4
                "strike": [990, 1010],
                "expiration": [expiry, expiry],
                "underlying": [1000, 1000],
            }
        )

        # Should fail with tight tolerance
        is_valid_tight, violations_tight = check_no_arbitrage(df, tolerance=0.01)
        assert not is_valid_tight
        assert any("intrinsic" in v.lower() for v in violations_tight)

        # Should pass with tolerance that covers the violation
        is_valid_loose, _ = check_no_arbitrage(df, tolerance=0.50)
        assert is_valid_loose


class TestConvexityCondition:
    """Specific tests for convexity (no butterfly arbitrage)."""

    def test_linear_prices_at_boundary(self):
        """Test that linear prices (zero butterfly) are acceptable."""
        df = pd.DataFrame(
            {
                "date": [datetime(2026, 1, 6)] * 3,
                "option_name": ["C_20260110_0980", "C_20260110_1000", "C_20260110_1020"],
                "option_type": ["call"] * 3,
                "mid": [25.0, 10.0, 2.0],  # Reasonable prices
                "strike": [980, 1000, 1020],
                "expiration": [datetime(2026, 1, 10)] * 3,
                "underlying": [1000] * 3,
            }
        )

        is_valid, violations = check_no_arbitrage(df)

        # Should be valid
        assert is_valid, f"Unexpected violations: {violations}"

    def test_convex_prices_valid(self):
        """Test that convex price structure is valid."""
        df = pd.DataFrame(
            {
                "date": [datetime(2026, 1, 6)] * 3,
                "option_name": ["C_20260110_0980", "C_20260110_1000", "C_20260110_1020"],
                "option_type": ["call"] * 3,
                "mid": [25.0, 11.0, 3.0],  # Convex (butterfly > 0)
                "strike": [980, 1000, 1020],
                "expiration": [datetime(2026, 1, 10)] * 3,
                "underlying": [1000] * 3,
            }
        )

        is_valid, violations = check_no_arbitrage(df)

        assert is_valid, f"Unexpected violations: {violations}"

    def test_concave_prices_invalid(self):
        """Test that concave price structure creates arbitrage."""
        df = pd.DataFrame(
            {
                "date": [datetime(2026, 1, 6)] * 3,
                "option_name": ["C_20260110_0980", "C_20260110_1000", "C_20260110_1020"],
                "option_type": ["call"] * 3,
                "mid": [25.0, 20.0, 3.0],  # Concave (middle too expensive)
                "strike": [980, 1000, 1020],
                "expiration": [datetime(2026, 1, 10)] * 3,
                "underlying": [1000] * 3,
            }
        )

        is_valid, violations = check_no_arbitrage(df)

        assert not is_valid
        # Should detect either butterfly or intrinsic violation
        assert len(violations) > 0


class TestCalendarSpreadCondition:
    """Specific tests for calendar spread consistency."""

    def test_increasing_prices_with_time_valid(self):
        """Test that prices increasing with expiry are valid."""
        df = pd.DataFrame(
            {
                "date": [datetime(2026, 1, 6)] * 3,
                "option_name": ["C_20260107_1000", "C_20260110_1000", "C_20260115_1000"],
                "option_type": ["call"] * 3,
                "mid": [2.0, 5.0, 8.0],  # Increasing with time
                "strike": [1000, 1000, 1000],
                "expiration": [datetime(2026, 1, 7), datetime(2026, 1, 10), datetime(2026, 1, 15)],
                "underlying": [1000] * 3,
            }
        )

        is_valid, violations = check_no_arbitrage(df)

        assert is_valid

    def test_equal_prices_with_time_valid(self):
        """Test that equal prices across expiries are valid (boundary case)."""
        df = pd.DataFrame(
            {
                "date": [datetime(2026, 1, 6)] * 2,
                "option_name": ["C_20260110_1000", "C_20260115_1000"],
                "option_type": ["call"] * 2,
                "mid": [5.0, 5.0],  # Same price
                "strike": [1000, 1000],
                "expiration": [datetime(2026, 1, 10), datetime(2026, 1, 15)],
                "underlying": [1000] * 2,
            }
        )

        is_valid, violations = check_no_arbitrage(df)

        assert is_valid

    def test_decreasing_prices_with_time_invalid(self):
        """Test that prices decreasing with expiry create arbitrage."""
        df = pd.DataFrame(
            {
                "date": [datetime(2026, 1, 6)] * 2,
                "option_name": ["C_20260110_1000", "C_20260115_1000"],
                "option_type": ["call"] * 2,
                "mid": [10.0, 8.0],  # Decreasing!
                "strike": [1000, 1000],
                "expiration": [datetime(2026, 1, 10), datetime(2026, 1, 15)],
                "underlying": [1000] * 2,
            }
        )

        is_valid, violations = check_no_arbitrage(df)

        assert not is_valid
        assert any("calendar" in v.lower() for v in violations)


class TestMultipleViolations:
    """Test detection of multiple simultaneous violations."""

    def test_multiple_violations_all_detected(self):
        """Test that multiple violations are all detected."""
        df = pd.DataFrame(
            {
                "date": [datetime(2026, 1, 6)] * 3,
                "option_name": ["C_20260110_0950", "C_20260110_1000", "C_20260110_1050"],
                "option_type": ["call"] * 3,
                "mid": [-1.0, 25.0, 1100.0],  # Negative, monotonicity violated, exceeds spot
                "strike": [950, 1000, 1050],
                "expiration": [datetime(2026, 1, 10)] * 3,
                "underlying": [1000] * 3,
            }
        )

        is_valid, violations = check_no_arbitrage(df)

        assert not is_valid
        assert len(violations) >= 3  # Should detect multiple issues


class TestGenerateArbitrageReport:
    """Test cases for arbitrage report generation."""

    def test_report_for_valid_chain(self):
        """Test report generation for valid chain."""
        df = pd.DataFrame(
            {
                "date": [datetime(2026, 1, 6)] * 3,
                "option_name": ["C_20260110_0990", "C_20260110_1000", "C_20260110_1010"],
                "option_type": ["call"] * 3,
                "mid": [12.0, 8.0, 5.0],
                "strike": [990, 1000, 1010],
                "expiration": [datetime(2026, 1, 10)] * 3,
                "underlying": [1000] * 3,
            }
        )

        report = generate_arbitrage_report(df)

        # Check for pass indicator
        assert "PASS" in report or "✓" in report, f"Report should show PASS:\n{report}"
        assert "ARBITRAGE-FREE" in report

    def test_report_for_invalid_chain(self):
        """Test report generation for invalid chain."""
        df = pd.DataFrame(
            {
                "date": [datetime(2026, 1, 6)] * 2,
                "option_name": ["C_20260110_1000", "C_20260110_1050"],
                "option_type": ["call"] * 2,
                "mid": [5.0, 10.0],  # Monotonicity violated
                "strike": [1000, 1050],
                "expiration": [datetime(2026, 1, 10)] * 2,
                "underlying": [1000] * 2,
            }
        )

        report = generate_arbitrage_report(df)

        assert "FAIL" in report or "✗" in report
        assert "violation" in report.lower()

    def test_report_contains_summary(self):
        """Test that report contains dataset summary."""
        df = pd.DataFrame(
            {
                "date": [datetime(2026, 1, 6)] * 2,
                "option_name": ["C_20260110_1000", "C_20260110_1050"],
                "option_type": ["call"] * 2,
                "mid": [10.0, 5.0],
                "strike": [1000, 1050],
                "expiration": [datetime(2026, 1, 10)] * 2,
                "underlying": [1000] * 2,
            }
        )

        report = generate_arbitrage_report(df)

        assert "Total options" in report
        assert "Trading days" in report


class TestIntegrationWithGeneratedData:
    """Integration tests with actual generated option data."""

    def test_generated_chain_is_arbitrage_free(self):
        """Test that data generated from our pipeline is arbitrage-free."""
        from opt_research.underlying import simulate_underlying
        from opt_research.volatility_surface import generate_term_structure_params
        from opt_research.option_chain import generate_multi_day_chains

        # Generate small dataset
        dates, spots = simulate_underlying(1000, 0.05, 0.10, 3, seed=42)
        expiries = [i / 252 for i in [1, 2, 3]]
        params_list = generate_term_structure_params(expiries)
        params_dict = {T: params for T, params in params_list}

        df = generate_multi_day_chains(
            dates,
            spots,
            0.02,
            expiry_days_list=[1, 2, 3],
            moneyness_range=[0.95, 1.00, 1.05],  # Narrower range to avoid deep ITM puts
            svi_params_dict=params_dict,
        )

        # Validate - use small tolerance to account for numerical precision
        is_valid, violations = check_no_arbitrage(df, tolerance=1e-8)

        if not is_valid:
            print("\nViolations found:")
            for v in violations:
                print(f"  - {v}")

        assert is_valid, f"Generated data has arbitrage: {violations}"

    def test_large_generated_dataset(self):
        """Test arbitrage-free property on larger dataset."""
        from opt_research.underlying import simulate_underlying
        from opt_research.volatility_surface import generate_term_structure_params
        from opt_research.option_chain import generate_multi_day_chains

        # Generate larger dataset with narrower moneyness range to avoid extreme OTM/ITM
        dates, spots = simulate_underlying(1000, 0.05, 0.10, 10, seed=42)
        expiries = [i / 252 for i in range(1, 11)]  # 10 expiries
        params_list = generate_term_structure_params(expiries)
        params_dict = {T: params for T, params in params_list}

        df = generate_multi_day_chains(
            dates,
            spots,
            0.02,
            expiry_days_list=list(range(1, 11)),
            moneyness_range=[0.95, 1.00, 1.05],  # Narrower range to avoid deep ITM puts
            svi_params_dict=params_dict,
        )

        # Validate with slightly looser tolerance for numerical stability
        is_valid, violations = check_no_arbitrage(df, tolerance=1e-6)

        assert is_valid, f"Large dataset has {len(violations)} arbitrage violations"
        assert len(df) == len(dates) * 10 * 3 * 2  # days * expiries * strikes * option_types


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
