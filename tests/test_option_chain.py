"""Tests for option chain generation module."""

import numpy as np
import pytest
from datetime import datetime

from opt_research.option_chain import (
    generate_option_chain,
    generate_multi_day_chains,
    add_business_days,
)
from opt_research.volatility_surface import generate_term_structure_params
from opt_research.underlying import simulate_underlying


class TestAddBusinessDays:
    """Test cases for business day addition."""

    def test_add_one_day(self):
        """Test adding one business day."""
        start = datetime(2026, 1, 6)
        result = add_business_days(start, 1)

        assert result == datetime(2026, 1, 7)

    def test_add_multiple_days(self):
        """Test adding multiple business days."""
        start = datetime(2026, 1, 6)
        result = add_business_days(start, 5)

        assert result == datetime(2026, 1, 11)


class TestGenerateOptionChain:
    """Test cases for single-day option chain generation."""

    @pytest.fixture
    def svi_params_dict(self):
        """Create SVI parameters for testing."""
        expiries = [i / 252 for i in [1, 2, 5, 10]]
        params_list = generate_term_structure_params(expiries)
        return {T: params for T, params in params_list}

    def test_basic_chain_generation(self, svi_params_dict):
        """Test basic option chain generation."""
        date = datetime(2026, 1, 6)
        spot = 1000.0
        r = 0.02

        chain = generate_option_chain(
            date,
            spot,
            r,
            expiry_days_list=[1, 2],
            moneyness_range=[0.95, 1.00, 1.05],
            svi_params_dict=svi_params_dict,
        )

        expected_options = 2 * 3 * 2  # 2 expiries * 3 strikes * 2 option types
        assert len(chain) == expected_options

    def test_output_columns(self, svi_params_dict):
        """Test that output has all required columns."""
        date = datetime(2026, 1, 6)
        chain = generate_option_chain(
            date,
            1000.0,
            0.02,
            expiry_days_list=[1],
            moneyness_range=[1.00],
            svi_params_dict=svi_params_dict,
        )

        expected_cols = {
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
        }

        assert set(chain.columns) == expected_cols

    def test_bid_ask_spread(self, svi_params_dict):
        """Test that bid < mid < ask."""
        date = datetime(2026, 1, 6)
        chain = generate_option_chain(
            date,
            1000.0,
            0.02,
            expiry_days_list=[5],
            moneyness_range=[0.90, 1.00, 1.10],
            svi_params_dict=svi_params_dict,
        )

        assert all(chain["bid"] < chain["mid"])
        assert all(chain["mid"] < chain["ask"])

    def test_positive_prices(self, svi_params_dict):
        """Test that all prices are positive."""
        date = datetime(2026, 1, 6)
        chain = generate_option_chain(
            date,
            1000.0,
            0.02,
            expiry_days_list=[1, 5, 10],
            moneyness_range=[0.80, 0.90, 1.00, 1.10, 1.20],
            svi_params_dict=svi_params_dict,
        )

        assert all(chain["bid"] > 0)
        assert all(chain["mid"] > 0)
        assert all(chain["ask"] > 0)

    def test_delta_bounds(self, svi_params_dict):
        """Test that call delta is between 0 and 1, put delta is between -1 and 0."""
        date = datetime(2026, 1, 6)
        chain = generate_option_chain(
            date,
            1000.0,
            0.02,
            expiry_days_list=[5],
            moneyness_range=[0.80, 0.90, 1.00, 1.10, 1.20],
            svi_params_dict=svi_params_dict,
        )

        calls = chain[chain["option_type"] == "call"]
        puts = chain[chain["option_type"] == "put"]

        assert all(calls["delta"] >= 0)
        assert all(calls["delta"] <= 1)
        assert all(puts["delta"] <= 0)
        assert all(puts["delta"] >= -1)

    def test_moneyness_calculation(self, svi_params_dict):
        """Test that moneyness is correctly calculated."""
        date = datetime(2026, 1, 6)
        spot = 1000.0
        chain = generate_option_chain(
            date,
            spot,
            0.02,
            expiry_days_list=[1],
            moneyness_range=[0.90, 1.00, 1.10],
            svi_params_dict=svi_params_dict,
        )

        # Moneyness should be strike / spot
        for _, row in chain.iterrows():
            expected_moneyness = row["strike"] / spot
            assert abs(row["moneyness"] - expected_moneyness) < 1e-10

    def test_option_naming(self, svi_params_dict):
        """Test option name format for calls and puts."""
        date = datetime(2026, 1, 6)
        chain = generate_option_chain(
            date,
            1000.0,
            0.02,
            expiry_days_list=[5],
            moneyness_range=[1.00],
            svi_params_dict=svi_params_dict,
        )

        calls = chain[chain["option_type"] == "call"]
        puts = chain[chain["option_type"] == "put"]

        call_name = calls.iloc[0]["option_name"]
        put_name = puts.iloc[0]["option_name"]

        # Call should start with C_ and put with P_
        assert call_name.startswith("C_")
        assert put_name.startswith("P_")
        assert len(call_name.split("_")) == 3  # C_YYYYMMDD_KKKK
        assert len(put_name.split("_")) == 3  # P_YYYYMMDD_KKKK

    def test_strike_rounding(self, svi_params_dict):
        """Test that strikes are rounded to nearest 5."""
        date = datetime(2026, 1, 6)
        chain = generate_option_chain(
            date,
            1000.0,
            0.02,
            expiry_days_list=[1],
            moneyness_range=[0.98],  # Should round to 980
            svi_params_dict=svi_params_dict,
        )

        strike = chain.iloc[0]["strike"]
        assert strike % 5 == 0


class TestGenerateMultiDayChains:
    """Test cases for multi-day option chain generation."""

    @pytest.fixture
    def setup_data(self):
        """Create test data for multi-day chains."""
        dates, spots = simulate_underlying(1000, 0.05, 0.10, 5, seed=42)
        expiries = [i / 252 for i in [1, 2, 3]]
        params_list = generate_term_structure_params(expiries)
        params_dict = {T: params for T, params in params_list}

        return dates, spots, params_dict

    def test_multi_day_generation(self, setup_data):
        """Test generation of chains for multiple days."""
        dates, spots, params_dict = setup_data

        chains = generate_multi_day_chains(
            dates,
            spots,
            0.02,
            expiry_days_list=[1, 2, 3],
            moneyness_range=[0.95, 1.00, 1.05],
            svi_params_dict=params_dict,
        )

        expected_total = len(dates) * 3 * 3 * 2  # days * expiries * strikes * option_types
        assert len(chains) == expected_total

    def test_unique_dates(self, setup_data):
        """Test that chains are generated for each date."""
        dates, spots, params_dict = setup_data

        chains = generate_multi_day_chains(
            dates,
            spots,
            0.02,
            expiry_days_list=[1, 2],
            moneyness_range=[1.00],
            svi_params_dict=params_dict,
        )

        assert chains["date"].nunique() == len(dates)

    def test_changing_underlying(self, setup_data):
        """Test that underlying price changes with dates."""
        dates, spots, params_dict = setup_data

        chains = generate_multi_day_chains(
            dates,
            spots,
            0.02,
            expiry_days_list=[1],
            moneyness_range=[1.00],
            svi_params_dict=params_dict,
        )

        # Underlying should vary across dates
        underlying_values = chains.groupby("date")["underlying"].first().values
        assert len(set(underlying_values)) > 1  # Not all the same

    def test_strikes_follow_spot(self, setup_data):
        """Test that strikes are proportional to spot."""
        dates, spots, params_dict = setup_data

        chains = generate_multi_day_chains(
            dates,
            spots,
            0.02,
            expiry_days_list=[1],
            moneyness_range=[1.00],  # ATM
            svi_params_dict=params_dict,
        )

        # ATM strikes should be close to spot (within rounding)
        # Filter to unique date/strike combos (calls and puts have same strike)
        for _, row in chains.drop_duplicates(subset=["date", "strike"]).iterrows():
            assert abs(row["strike"] - row["underlying"]) < 10


class TestOptionChainConsistency:
    """Test consistency properties of generated option chains."""

    @pytest.fixture
    def sample_chain(self):
        """Create a sample option chain for testing."""
        date = datetime(2026, 1, 6)
        expiries = [i / 252 for i in [1, 5, 10]]
        params_list = generate_term_structure_params(expiries)
        params_dict = {T: params for T, params in params_list}

        return generate_option_chain(
            date,
            1000.0,
            0.02,
            expiry_days_list=[1, 5, 10],
            moneyness_range=[0.90, 0.95, 1.00, 1.05, 1.10],
            svi_params_dict=params_dict,
        )

    def test_monotonicity_in_strike(self, sample_chain):
        """Test that call prices decrease with strike for same expiry."""
        calls = sample_chain[sample_chain["option_type"] == "call"]
        for exp in calls["expiration"].unique():
            exp_df = calls[calls["expiration"] == exp].sort_values("strike")
            prices = exp_df["mid"].values

            # Call prices should be non-increasing with strike
            for i in range(len(prices) - 1):
                assert prices[i] >= prices[i + 1] - 1e-8

    def test_put_monotonicity_in_strike(self, sample_chain):
        """Test that put prices increase with strike for same expiry."""
        puts = sample_chain[sample_chain["option_type"] == "put"]
        for exp in puts["expiration"].unique():
            exp_df = puts[puts["expiration"] == exp].sort_values("strike")
            prices = exp_df["mid"].values

            # Put prices should be non-decreasing with strike
            for i in range(len(prices) - 1):
                assert prices[i] <= prices[i + 1] + 1e-8

    def test_calendar_spread(self, sample_chain):
        """Test that longer expiry has higher price for same strike and option type."""
        calls = sample_chain[sample_chain["option_type"] == "call"]
        for strike in calls["strike"].unique():
            strike_df = calls[calls["strike"] == strike].sort_values("expiration")
            if len(strike_df) < 2:
                continue

            prices = strike_df["mid"].values

            # Call prices should be non-decreasing with expiration
            for i in range(len(prices) - 1):
                assert prices[i] <= prices[i + 1] + 1e-8

    def test_delta_progression_with_moneyness(self, sample_chain):
        """Test that call delta decreases as strike increases (more OTM)."""
        # Take one expiry, calls only
        calls = sample_chain[sample_chain["option_type"] == "call"]
        exp = calls["expiration"].iloc[0]
        exp_df = calls[calls["expiration"] == exp].sort_values("strike")

        deltas = exp_df["delta"].values

        # Call delta should decrease as strike increases (more OTM)
        for i in range(len(deltas) - 1):
            assert deltas[i] >= deltas[i + 1] - 1e-8

    def test_put_delta_progression_with_moneyness(self, sample_chain):
        """Test that put delta decreases (becomes more negative) as strike increases."""
        # Take one expiry, puts only
        puts = sample_chain[sample_chain["option_type"] == "put"]
        exp = puts["expiration"].iloc[0]
        exp_df = puts[puts["expiration"] == exp].sort_values("strike")

        deltas = exp_df["delta"].values

        # Put delta should decrease (become more negative) as strike increases
        # At lower strikes, puts are OTM (delta closer to 0)
        # At higher strikes, puts are ITM (delta closer to -1)
        for i in range(len(deltas) - 1):
            assert deltas[i] >= deltas[i + 1] - 1e-8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
