# Option Backtester - PLAN

**Job Name:** option_backtest  
**Created:** 2026-01-06  
**Status:** Phase 0 Complete - Ready for Phase 1

---

## Objective

Build a **mark-to-market backtester** for European options using the synthetic options data in `data/synthetic_options.csv`. The backtester will:

1. Accept external trading signals (target positions) - **no strategy logic**
2. Execute trades at correct bid/ask prices (buy at ASK, sell at BID)
3. Handle option expiration with cash settlement
4. Track portfolio value, positions, and transaction costs
5. Provide both simple (time series) and comprehensive (detailed breakdown) outputs

**Key Constraint**: This is a pure mark-to-market engine. No stop-loss, take-profit, or any strategy logic.

**Pre-requisite**: ✅ COMPLETE - Updated `synthetic_options.csv` to include `option_type` column.

---

## Phase 0: Update Synthetic Options Data (COMPLETE ✅)

**Status:** Completed

### Changes Made:

1. **option_pricing.py**: Added `black_scholes_put()` and `black_scholes_put_delta()` functions
2. **option_chain.py**: Updated to generate both calls and puts with `option_type` column
3. **arbitrage_free.py**: Updated `check_no_arbitrage()` to handle put option validation
   - Separate intrinsic value bounds for puts vs calls
   - Correct monotonicity check (puts increase with strike)
   - Calendar spread check skips deep ITM puts (expected behavior for European puts)
   - Butterfly tolerance increased for realistic volatility smiles
4. **data_generator.py**: Narrowed moneyness range to [0.90-1.10] to avoid edge cases
5. **All test files updated**: Added `option_type` column to test DataFrames
6. **examples/load_option_data.py**: Updated expected headers

### Current Data Schema:
```
date, option_name, option_type, bid, ask, mid, expiration, strike, underlying, moneyness, implied_volatility, delta
```

### Generated Dataset:
- **Total options:** 4,620 (2,310 calls + 2,310 puts)
- **Trading days:** 21
- **Unique strikes:** 51
- **All 113 tests passing**

---

## File Structure

```
opt_research/
├── src/
│   └── opt_research/
│       ├── __init__.py                 # Update to export backtester
│       ├── backtester/
│       │   ├── __init__.py
│       │   ├── portfolio.py            # Portfolio state management
│       │   ├── market_data.py          # Market data loader & option metadata
│       │   ├── execution.py            # Trade execution logic
│       │   ├── settlement.py           # Option expiration & cash settlement
│       │   ├── mtm.py                  # Mark-to-market valuation engine
│       │   └── backtest_engine.py      # Main orchestrator
├── tests/
│   └── test_backtester/
│       ├── __init__.py
│       ├── test_portfolio.py           # Portfolio state tests
│       ├── test_market_data.py         # Market data loading tests
│       ├── test_execution.py           # Trade execution tests
│       ├── test_settlement.py          # Settlement logic tests
│       ├── test_mtm.py                 # MTM valuation tests
│       └── test_backtest_engine.py     # Integration tests
├── examples/
│   └── run_backtest.py                 # Example backtest with sample orders
└── data/
    └── synthetic_options.csv           # Already exists
```

---

## Input/Output Specification

### Input: Trading Orders DataFrame

```python
orders_df = pd.DataFrame({
    'date': [...],           # Trading date (datetime)
    'option_name': [...],    # e.g., 'C_20260107_1000'
    'target_units': [...]    # Target position (float, can be negative)
})
```

**Semantics**:
- `target_units` is the **absolute target position** for that option on that date
- If current position is 0 and target is 5.0 → buy 5.0 units
- If current position is 5.0 and target is 3.0 → sell 2.0 units
- If current position is 0 and target is -3.0 → short sell 3.0 units
- Negative units = short position

### Output: Simple

```python
simple_output = pd.DataFrame({
    'date': [...],           # Trading date
    'portfolio_value': [...]  # Total portfolio value (cash + positions MTM)
})
```

### Output: Comprehensive

```python
comprehensive_output = pd.DataFrame({
    'date': [...],                    # Trading date
    'option_name': [...],             # Option identifier
    'option_type': [...],             # 'call' or 'put'
    'units': [...],                   # Current position (+ = long, - = short)
    'bid': [...],                     # Current bid price
    'ask': [...],                     # Current ask price
    'mid': [...],                     # Current mid price
    'mtm_price': [...],               # Price used for MTM (bid for long, ask for short)
    'position_value': [...],          # units * mtm_price
    'unrealized_pnl': [...],          # Current P&L vs entry cost
    'transaction_cost': [...],        # Cumulative transaction cost for this position
    'weight': [...],                  # Position weight in portfolio (%)
    'expiration': [...],              # Option expiration date
    'strike': [...],                  # Strike price
    'days_to_expiry': [...],          # Days until expiration
    'underlying_price': [...],        # Current underlying price
    'intrinsic_value': [...],         # Intrinsic value at current spot
})
```

Plus summary row per date:
- Total portfolio value
- Total cash
- Total position value
- Total transaction costs (cumulative)
- Total unrealized P&L

---

## Core Logic

### 1. Option Naming Convention

From `synthetic_options.csv`, option names follow: `C_YYYYMMDD_KKKK` or `P_YYYYMMDD_KKKK`
- `C` = Call, `P` = Put
- `YYYYMMDD` = Expiration date
- `KKKK` = Strike price (zero-padded)

**Data now includes `option_type` column directly** - no parsing needed for type.

**Parsing logic** (for expiration/strike only):
```python
def parse_option_name(name: str) -> dict:
    # e.g., 'C_20260107_1000' → {'expiration': date(2026,1,7), 'strike': 1000}
    parts = name.split('_')
    expiration = datetime.strptime(parts[1], '%Y%m%d').date()
    strike = int(parts[2])
    return {'expiration': expiration, 'strike': strike}
```

The `option_type` column in the CSV provides 'call' or 'put' directly.

### 2. Trade Execution

```
ON EACH TRADING DAY:
1. Load target positions from orders_df for this date
2. For each option with a target:
   a. Get current position (0 if not held)
   b. Calculate delta = target_units - current_units
   c. If delta > 0: BUY delta units at ASK price
   d. If delta < 0: SELL |delta| units at BID price
   e. Update cash: cash -= delta * execution_price
   f. Record transaction cost: |delta| * (ask - bid) / 2
3. Update position holdings
```

### 3. Mark-to-Market Valuation

```
FOR EACH POSITION:
- If units > 0 (long): MTM at BID (we would sell to close)
- If units < 0 (short): MTM at ASK (we would buy to close)

position_value = units * mtm_price
# Note: For short positions, units < 0 and mtm at ask, so value is negative

PORTFOLIO VALUE = cash + sum(position_values)
```

### 4. Option Settlement at Expiration

```
ON EXPIRATION DATE:
1. Identify all positions expiring today
2. Get final underlying price from market data
3. For each expiring option:
   a. Get option_type from market data ('call' or 'put')
   b. Calculate settlement value:
      - CALL (option_type == 'call'): max(0, underlying - strike) per unit
      - PUT (option_type == 'put'): max(0, strike - underlying) per unit
   c. Cash settlement:
      - Long position: cash += units * settlement_value
      - Short position: cash += units * settlement_value  # units < 0, so pays out
   d. Remove position from holdings
```

### 5. Transaction Cost Calculation

```
For any trade of delta units:
- We always cross the spread to trade
- BUY: pay ASK (higher than mid)
- SELL: receive BID (lower than mid)

Transaction cost = |delta| * (ask - bid) / 2
(This is the cost vs mid-price execution)

Alternatively:
Transaction cost = |delta| * (execution_price - mid)
```

### 6. Configuration Flags

```python
@dataclass
class BacktestConfig:
    initial_cash: float = 10_000_000.0  # $10M
    allow_negative_value: bool = True    # Allow portfolio value < 0
    allow_borrowing: bool = True         # Allow cash < 0 (borrow at 0%)
    cash_interest_rate: float = 0.0      # No interest on cash
    borrow_interest_rate: float = 0.0    # No interest on borrowed funds
```

---

## Data Flow Diagram

```
┌─────────────────┐     ┌─────────────────┐
│  orders_df      │     │ synthetic_      │
│  (date,name,    │     │ options.csv     │
│   target_units) │     │                 │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
┌─────────────────────────────────────────┐
│           BacktestEngine                 │
│  ┌───────────────────────────────────┐  │
│  │  1. Load market data for date     │  │
│  │  2. Handle settlements (if any)   │  │
│  │  3. Execute trades                │  │
│  │  4. Mark-to-market all positions  │  │
│  │  5. Record daily snapshot         │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│  Simple Output  │     │ Comprehensive   │
│  (date, pv)     │     │ Output          │
└─────────────────┘     └─────────────────┘
```

---

## Synthetic Test Data Strategy

### Sample Orders for Testing

Generate a small set of realistic trading orders:

```python
# Strategy: Buy some near-ATM calls, hold, let some expire
sample_orders = pd.DataFrame({
    'date': [
        '2026-01-06', '2026-01-06',  # Day 1: Enter 2 positions
        '2026-01-08',                 # Day 3: Adjust position
        '2026-01-10',                 # Day 5: Close one position
    ],
    'option_name': [
        'C_20260107_1000', 'C_20260110_1000',  # 1-day and 4-day ATM calls
        'C_20260110_1000',                      # Adjust 4-day call
        'C_20260110_1000',                      # Close before expiry
    ],
    'target_units': [
        10.0, 5.0,   # Buy 10 and 5 units
        8.0,         # Reduce from 5 to 8 (buy 3 more)
        0.0,         # Close position
    ]
})
```

### Test Scenarios

1. **Basic Long Position**: Buy, hold, sell
2. **Short Position**: Short sell, cover
3. **Option Expiration ITM**: Position expires in-the-money
4. **Option Expiration OTM**: Position expires worthless
5. **Mixed Portfolio**: Multiple positions with different expirations
6. **Edge Cases**: Zero units, fractional units, same-day open/close

---

## Virtual Environment

Already configured in `opt_research` conda environment:
- Python 3.12.12
- numpy >= 1.26.0
- pandas >= 2.1.0
- pytest >= 7.4.0
- black >= 23.0.0

No additional packages required.

---

## Checklist

### Phase 0: Update Synthetic Options Data (Pre-requisite)
- [ ] Update `src/opt_research/option_chain.py` to add `option_type` column
- [ ] Update `src/opt_research/data_generator.py` if needed
- [ ] Regenerate `data/synthetic_options.csv` with `option_type` column
- [ ] Update `examples/load_option_data.py` to display `option_type`
- [ ] Verify CSV has correct structure with new column

### Phase 1: Core Modules
- [ ] Create `src/opt_research/backtester/__init__.py`
- [ ] Implement `market_data.py` - Load CSV, parse option names, metadata lookup
- [ ] Implement `portfolio.py` - Portfolio state (cash, positions, history)
- [ ] Implement `execution.py` - Trade execution at bid/ask
- [ ] Implement `settlement.py` - Option expiration cash settlement
- [ ] Implement `mtm.py` - Mark-to-market valuation engine
- [ ] Implement `backtest_engine.py` - Main orchestrator

### Phase 2: Testing
- [ ] Create `tests/test_backtester/__init__.py`
- [ ] Write `test_market_data.py` - Test option parsing, data loading
- [ ] Write `test_portfolio.py` - Test state management
- [ ] Write `test_execution.py` - Test trade execution logic
- [ ] Write `test_settlement.py` - Test settlement calculations
- [ ] Write `test_mtm.py` - Test MTM valuations
- [ ] Write `test_backtest_engine.py` - Integration tests

### Phase 3: Example & Validation
- [ ] Create `examples/run_backtest.py` with sample orders
- [ ] Run full backtest on synthetic data
- [ ] Validate output correctness manually
- [ ] Generate final report

---

## Risk & Edge Cases

1. **Option Not Found**: Order references non-existent option → Error
2. **Trading After Expiration**: Order on expired option → Skip with warning
3. **Insufficient Liquidity**: Not modeled (assume infinite liquidity)
4. **Negative Portfolio Value**: Configurable - default allows
5. **Same-Day Multiple Orders**: Same option can have only one target per day
6. **Weekend/Holiday**: Not modeled (use trading days from market data)

---

## Success Criteria

1. ✅ Correctly executes buy/sell at ask/bid prices
2. ✅ Handles option expiration with correct settlement (call/put differentiation)
3. ✅ Tracks transaction costs accurately
4. ✅ MTM uses bid for longs, ask for shorts
5. ✅ Simple output: Daily portfolio value time series
6. ✅ Comprehensive output: Full position details with weights
7. ✅ All tests pass
8. ✅ Example backtest runs successfully on synthetic data

---

## Notes

- All options in `synthetic_options.csv` are **calls** (prefix `C_`)
- For future put support, the naming convention would be `P_YYYYMMDD_KKKK`
- Settlement is always **cash settlement** (no physical delivery)
- No margin requirements modeled
- No transaction fees beyond bid-ask spread

---

**Ready for Stage B: Execution**
