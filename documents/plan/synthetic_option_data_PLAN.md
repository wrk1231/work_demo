# Synthetic Option Data Generation - PLAN

**Job Name:** synthetic_option_data  
**Created:** 2026-01-06  
**Status:** Planning

---

## Objective

Generate a scientifically valid synthetic options dataset with **no-arbitrage guarantees** at mid prices. The dataset will include:
- 20 trading days of option chain data
- Options with expirations from 1 to 10 business days
- Moneyness range from 80% to 120%
- Underlying simulated via geometric Brownian motion (GBM)
- Proper bid/ask spreads with arbitrage-free mid prices
- Black-Scholes implied volatilities and deltas

---

## File Structure

```
opt_research/
├── pyproject.toml
├── data/
│   └── synthetic_options.csv
├── src/
│   └── opt_research/
│       ├── __init__.py
│       ├── underlying.py          # GBM simulation for underlying
│       ├── volatility_surface.py  # SVI parameterization & surface construction
│       ├── option_pricing.py      # Black-Scholes pricing & Greeks
│       ├── option_chain.py        # Option chain generation (uses vol surface)
│       ├── arbitrage_free.py      # Arbitrage-free constraints validation
│       └── data_generator.py      # Main orchestrator to generate CSV
├── tests/
│   ├── __init__.py
│   ├── test_underlying.py
│   ├── test_volatility_surface.py # Test SVI constraints & surface properties
│   ├── test_option_pricing.py
│   ├── test_option_chain.py
│   └── test_arbitrage_free.py     # Critical: test no-arbitrage conditions
├── examples/
│   └── load_option_data.py        # Demo script loading and inspecting data
└── documents/
    ├── plan/
    │   └── synthetic_option_data_PLAN.md
    ├── raw_plan/
    │   └── synthetic_option_data.md
    └── report/
        └── synthetic_option_data_REPORT.md
```

---

## Synthetic Data Strategy

### Underlying Asset Simulation

| Parameter | Value |
|-----------|-------|
| Initial Price (S₀) | 1000 |
| Annual Drift (μ) | 5% = 0.05 |
| Annual Volatility (σ) | 10% = 0.10 |
| Time Steps | 20 business days |
| Model | Geometric Brownian Motion |

**GBM Formula:**
$$S_{t+\Delta t} = S_t \cdot \exp\left[(\mu - \frac{\sigma^2}{2})\Delta t + \sigma \sqrt{\Delta t} \cdot Z\right]$$

Where $Z \sim N(0,1)$ and $\Delta t = \frac{1}{252}$ (1 business day).

**Seed:** Use fixed seed (42) for reproducibility.

### Option Chain Design

| Parameter | Range |
|-----------|-------|
| Expirations | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 business days |
| Moneyness | 80%, 85%, 90%, 95%, 100%, 105%, 110%, 115%, 120% (9 strikes) |
| Option Type | Calls only (puts derivable via put-call parity) |
| Risk-free Rate | 2% annual |

**Strike Calculation:** $K = S_t \times \text{moneyness}$, rounded to nearest 5.

**Option Naming Convention:** `C_YYYYMMDD_KKKK` where:
- `C` = Call
- `YYYYMMDD` = Expiration date
- `KKKK` = Strike price (zero-padded)

### Algorithm Overview: Volatility Surface First, Then Price

The key insight: **Black-Scholes prices are arbitrage-free if and only if the implied volatility surface satisfies specific mathematical constraints.** We construct the vol surface first with these constraints, then price.

```
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: Simulate Underlying Path (GBM)                        │
│          S₀ = 1000, 20 days                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 2: Construct Arbitrage-Free Volatility Surface           │
│          For each day t:                                        │
│          - Generate ATM base vol: σ_ATM(t)                      │
│          - Add smile via SVI parameterization                   │
│          - Enforce calendar arbitrage constraint                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 3: Price Options with Black-Scholes                       │
│          Use σ(K, T) from surface to compute prices             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 4: Validate No-Arbitrage Conditions                       │
│          - Monotonicity, Convexity, Calendar spreads            │
└─────────────────────────────────────────────────────────────────┘
```

---

### Step 2 Deep Dive: Volatility Surface Construction

#### 2A. SVI Parameterization (Stochastic Volatility Inspired)

We use the **SVI raw parameterization** for total implied variance $w(k, T) = \sigma^2(k, T) \cdot T$:

$$w(k) = a + b \left( \rho (k - m) + \sqrt{(k - m)^2 + \sigma^2} \right)$$

Where:
- $k = \ln(K/F)$ is log-forward-moneyness, $F = S \cdot e^{rT}$
- $a$ = overall variance level
- $b$ = controls the angle of the wings (b ≥ 0)
- $\rho$ = controls the skew/rotation (-1 < ρ < 1)
- $m$ = horizontal translation
- $\sigma$ = controls the smoothness of the ATM region (σ > 0)

**Implied volatility from total variance:**
$$\sigma_{impl}(k, T) = \sqrt{\frac{w(k)}{T}}$$

#### 2B. SVI No-Arbitrage Conditions (Gatheral & Jacquier)

For **no butterfly arbitrage** in a single slice, the density $g(k)$ must be non-negative:

$$g(k) = \left(1 - \frac{k w'(k)}{2w(k)}\right)^2 - \frac{(w'(k))^2}{4}\left(\frac{1}{w(k)} + \frac{1}{4}\right) + \frac{w''(k)}{2} \geq 0$$

**Sufficient conditions (simpler to enforce):**
1. $b \geq 0$
2. $|\rho| < 1$
3. $a + b \cdot \sigma \cdot \sqrt{1 - \rho^2} \geq 0$ (ensures $w(k) \geq 0$ for all $k$)
4. $b(1 + |\rho|) < \frac{4}{T}$ (Fukasawa's condition for small T)

#### 2C. Calendar Arbitrage-Free Condition

For different expiries $T_1 < T_2$, total variance must be non-decreasing:

$$w(k, T_1) \leq w(k, T_2) \quad \forall k$$

**Implementation:** We parameterize SVI for each expiry slice and ensure that:
- $a(T)$ is increasing in $T$
- $b(T)$ is adjusted so the wings don't cross

#### 2D. Concrete Parameter Choices

| Parameter | Base Value | Daily Variation |
|-----------|------------|-----------------|
| $a(T)$ | $0.01 \cdot T$ | Small positive drift |
| $b$ | 0.02 | Fixed |
| $\rho$ | -0.15 | Slight negative skew (realistic) |
| $m$ | 0 | Centered at ATM |
| $\sigma$ | 0.10 | Fixed curvature |

**ATM variance target:** $w_{ATM} = a + b \cdot \sigma \approx 0.01 \cdot T + 0.002$

This gives ATM vol ≈ $\sqrt{0.01 + 0.002/T} \approx 10\%$ for short expiries.

---

### Step 3: Black-Scholes Pricing

**Call Price:**
$$C = S \cdot N(d_1) - K \cdot e^{-rT} \cdot N(d_2)$$

Where:
$$d_1 = \frac{\ln(S/K) + (r + \frac{\sigma_{impl}^2}{2})T}{\sigma_{impl}\sqrt{T}}$$
$$d_2 = d_1 - \sigma_{impl}\sqrt{T}$$

**Delta:**
$$\Delta_{call} = N(d_1)$$

**Critical:** $\sigma_{impl}$ comes from the SVI surface, NOT a constant!

---

### Bid-Ask Spread Model

To ensure realistic markets while maintaining no-arbitrage at mid:
- **Mid Price** = Black-Scholes theoretical price (using SVI vol)
- **Spread** = max(0.01, 0.02 × mid_price) (2% of mid, min $0.01)
- **Bid** = mid - spread/2
- **Ask** = mid + spread/2

Ensures bid > 0 always.

---

### Step 4: No-Arbitrage Validation Tests

These are **verification tests** on the final prices (should pass by construction):

| Test | Condition | What it catches |
|------|-----------|-----------------|
| **Non-negative** | $C \geq 0$ | Invalid prices |
| **Intrinsic bound** | $C \geq \max(0, S - K e^{-rT})$ | Prices below intrinsic |
| **Upper bound** | $C \leq S$ | Prices above spot |
| **Monotonicity** | $C(K_1) \geq C(K_2)$ if $K_1 < K_2$ | Call spread arbitrage |
| **Convexity** | $C(K_1) - 2C(K_2) + C(K_3) \geq 0$ for $K_1 < K_2 < K_3$ | Butterfly arbitrage |
| **Calendar** | $C(T_1) \leq C(T_2)$ if $T_1 < T_2$ (same K) | Calendar spread arbitrage |

---

### Why This Guarantees No-Arbitrage

1. **SVI is arbitrage-free by construction** when parameters satisfy Gatheral-Jacquier conditions
2. **Black-Scholes prices from any valid vol surface are arbitrage-free** (fundamental theorem)
3. **Calendar constraint on total variance** ensures no calendar spread arbitrage
4. **Validation tests** provide a safety net to catch implementation bugs

---

## Virtual Environment

### Core Packages

| Package | Version | Purpose |
|---------|---------|---------|
| python | 3.12.12 | Runtime |
| numpy | ≥1.26.0 | Numerical computations |
| pandas | ≥2.1.0 | Data manipulation |
| scipy | ≥1.11.0 | Statistics (norm.cdf) |
| pytest | ≥7.4.0 | Testing framework |
| black | ≥23.0.0 | Code formatting |

---

## Logic Draft

### Module 1: `underlying.py`

```pseudo
function simulate_underlying(S0, drift, volatility, n_days, seed):
    set random seed
    dt = 1/252
    
    prices = [S0]
    for i in 1 to n_days:
        Z = random normal(0, 1)
        S_next = S_prev * exp((drift - 0.5*vol^2)*dt + vol*sqrt(dt)*Z)
        prices.append(S_next)
    
    return array of (dates, prices)
```

### Module 2: `volatility_surface.py` (NEW - Core of No-Arbitrage)

```pseudo
class SVIParameters:
    a: float  # variance level
    b: float  # wing angle (b >= 0)
    rho: float  # skew (-1 < rho < 1)
    m: float  # horizontal shift
    sigma: float  # ATM curvature (sigma > 0)

function svi_total_variance(k, params):
    """Compute total implied variance w(k) for log-moneyness k"""
    # w(k) = a + b * (rho*(k-m) + sqrt((k-m)^2 + sigma^2))
    return params.a + params.b * (
        params.rho * (k - params.m) + 
        sqrt((k - params.m)^2 + params.sigma^2)
    )

function svi_implied_vol(k, T, params):
    """Convert total variance to implied volatility"""
    w = svi_total_variance(k, params)
    return sqrt(w / T)

function validate_svi_no_arbitrage(params, T):
    """Check Gatheral-Jacquier conditions"""
    assert params.b >= 0, "b must be non-negative"
    assert abs(params.rho) < 1, "rho must be in (-1, 1)"
    assert params.sigma > 0, "sigma must be positive"
    
    # Ensure w(k) >= 0 for all k
    min_variance = params.a + params.b * params.sigma * sqrt(1 - params.rho^2)
    assert min_variance >= 0, "Variance can go negative"
    
    # Fukasawa condition for short expiries
    assert params.b * (1 + abs(params.rho)) < 4/T, "Fukasawa violated"
    
    return True

function generate_term_structure_params(expiries, base_atm_vol=0.10):
    """
    Generate SVI params for each expiry ensuring calendar arbitrage-free.
    
    Key constraint: total variance w(k, T) must be increasing in T for all k.
    
    Strategy: 
    - Set a(T) = base_variance * T (linear in T)
    - Keep b, rho, sigma, m constant across expiries
    - This ensures w scales with T, so w(T2) > w(T1) when T2 > T1
    """
    params_list = []
    
    base_variance = base_atm_vol^2  # ~0.01 for 10% vol
    
    for T in expiries:
        params = SVIParameters(
            a = base_variance * T * 0.8,  # 80% from time scaling
            b = 0.02,                      # Fixed wing angle
            rho = -0.15,                   # Slight negative skew
            m = 0.0,                       # Centered
            sigma = 0.10                   # Fixed curvature
        )
        validate_svi_no_arbitrage(params, T)
        params_list.append((T, params))
    
    return params_list

function validate_calendar_arbitrage_free(params_list, k_grid):
    """Verify w(k, T1) <= w(k, T2) for T1 < T2 at all k points"""
    for i in range(len(params_list) - 1):
        T1, params1 = params_list[i]
        T2, params2 = params_list[i + 1]
        
        for k in k_grid:
            w1 = svi_total_variance(k, params1)
            w2 = svi_total_variance(k, params2)
            assert w1 <= w2 + epsilon, f"Calendar arbitrage at k={k}"
    
    return True
```

### Module 3: `option_pricing.py`

```pseudo
function black_scholes_call(S, K, T, r, sigma):
    """Price call option using Black-Scholes formula"""
    if T <= 0:
        return max(S - K, 0)  # Expired: intrinsic value
    
    d1 = (ln(S/K) + (r + sigma^2/2)*T) / (sigma*sqrt(T))
    d2 = d1 - sigma*sqrt(T)
    
    price = S * N(d1) - K * exp(-r*T) * N(d2)
    return price

function black_scholes_delta(S, K, T, r, sigma):
    """Compute delta of call option"""
    if T <= 0:
        return 1.0 if S > K else 0.0
    
    d1 = (ln(S/K) + (r + sigma^2/2)*T) / (sigma*sqrt(T))
    return N(d1)

function black_scholes_vega(S, K, T, r, sigma):
    """Compute vega for Newton-Raphson IV solver"""
    d1 = (ln(S/K) + (r + sigma^2/2)*T) / (sigma*sqrt(T))
    return S * sqrt(T) * N'(d1)
```

### Module 4: `option_chain.py`

```pseudo
function generate_option_chain(date, spot, r, expiry_days_list, moneyness_range, svi_params_by_expiry):
    """
    Generate full option chain for a single trading day.
    
    Args:
        date: Trading date
        spot: Current spot price
        r: Risk-free rate
        expiry_days_list: [1, 2, 3, ..., 10] business days
        moneyness_range: [0.80, 0.85, ..., 1.20]
        svi_params_by_expiry: Dict[T -> SVIParameters]
    """
    options = []
    forward = spot * exp(r * T)  # Forward price for log-moneyness
    
    for exp_days in expiry_days_list:
        exp_date = add_business_days(date, exp_days)
        T = exp_days / 252
        svi_params = svi_params_by_expiry[T]
        
        for m in moneyness_range:
            K = round_to_nearest_5(spot * m)
            
            # Compute log-forward-moneyness
            F = spot * exp(r * T)
            k = ln(K / F)
            
            # Get implied vol from SVI surface
            sigma_impl = svi_implied_vol(k, T, svi_params)
            
            # Price with Black-Scholes using surface vol
            mid = black_scholes_call(spot, K, T, r, sigma_impl)
            
            # Bid-ask spread
            spread = max(0.01, 0.02 * mid)
            bid = max(0.01, mid - spread/2)
            ask = mid + spread/2
            
            # Delta
            delta = black_scholes_delta(spot, K, T, r, sigma_impl)
            
            # Moneyness for output
            moneyness = K / spot
            
            option = {
                'date': date,
                'option_name': f"C_{exp_date:%Y%m%d}_{K:04.0f}",
                'bid': bid,
                'ask': ask,
                'mid': mid,
                'expiration': exp_date,
                'strike': K,
                'underlying': spot,
                'moneyness': moneyness,
                'implied_volatility': sigma_impl,
                'delta': delta
            }
            options.append(option)
    
    return DataFrame(options)
```

### Module 5: `arbitrage_free.py`

```pseudo
function check_no_arbitrage(options_df, tolerance=1e-8):
    """
    Comprehensive arbitrage validation on the final option prices.
    Returns list of violations (empty if no arbitrage).
    """
    violations = []
    
    # Group by date
    for date, daily_df in options_df.groupby('date'):
        
        # Group by expiration for strike-space tests
        for exp, exp_df in daily_df.groupby('expiration'):
            sorted_df = exp_df.sort_values('strike')
            mids = sorted_df['mid'].values
            strikes = sorted_df['strike'].values
            S = sorted_df['underlying'].iloc[0]
            
            # Test 1: Non-negative prices
            if any(mids < 0):
                violations.append(f"{date}/{exp}: Negative price")
            
            # Test 2: Upper bound C <= S
            if any(mids > S + tolerance):
                violations.append(f"{date}/{exp}: Price exceeds spot")
            
            # Test 3: Monotonicity in strike
            for i in range(1, len(mids)):
                if mids[i] > mids[i-1] + tolerance:
                    violations.append(
                        f"{date}/{exp}: Monotonicity violated at K={strikes[i]}"
                    )
            
            # Test 4: Convexity (butterfly condition)
            for i in range(1, len(mids) - 1):
                butterfly = mids[i-1] - 2*mids[i] + mids[i+1]
                if butterfly < -tolerance:
                    violations.append(
                        f"{date}/{exp}: Butterfly arbitrage at K={strikes[i]}"
                    )
        
        # Test 5: Calendar spread (same strike, longer expiry >= shorter)
        for strike, strike_df in daily_df.groupby('strike'):
            sorted_by_exp = strike_df.sort_values('expiration')
            mids = sorted_by_exp['mid'].values
            exps = sorted_by_exp['expiration'].values
            
            for i in range(1, len(mids)):
                if mids[i] < mids[i-1] - tolerance:
                    violations.append(
                        f"{date}/K={strike}: Calendar arbitrage {exps[i-1]} vs {exps[i]}"
                    )
    
    return violations
```

### Module 6: `data_generator.py`

```pseudo
function generate_dataset(seed=42):
    """Main orchestrator: generate complete synthetic options dataset"""
    
    # Step 1: Simulate underlying
    underlying_path = simulate_underlying(
        S0=1000, drift=0.05, volatility=0.10, n_days=20, seed=seed
    )
    
    # Step 2: Generate SVI parameters for term structure
    expiry_days = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    svi_params = generate_term_structure_params(
        expiries=[d/252 for d in expiry_days],
        base_atm_vol=0.10
    )
    
    # Validate calendar arbitrage-free
    k_grid = linspace(-0.25, 0.25, 100)  # log-moneyness grid
    validate_calendar_arbitrage_free(svi_params, k_grid)
    
    # Step 3: Generate option chains for each day
    moneyness_range = [0.80, 0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15, 1.20]
    r = 0.02  # risk-free rate
    
    all_options = []
    for date, spot in underlying_path:
        daily_chain = generate_option_chain(
            date, spot, r, expiry_days, moneyness_range, svi_params
        )
        all_options.append(daily_chain)
    
    df = pd.concat(all_options, ignore_index=True)
    
    # Step 4: Validate no-arbitrage
    violations = check_no_arbitrage(df)
    if violations:
        raise ValueError(f"Arbitrage detected: {violations}")
    
    # Step 5: Save to CSV
    os.makedirs('data', exist_ok=True)
    df.to_csv('data/synthetic_options.csv', index=False)
    
    return df
```

---

## Checklist

### Phase 1: Environment Setup
- [x] Create conda environment `opt_research` with Python 3.12.12
- [x] Create `pyproject.toml` with dependencies
- [x] Install package in editable mode (`pip install -e .`)

### Phase 2: Core Implementation
- [x] Implement `src/opt_research/__init__.py`
- [x] Implement `src/opt_research/underlying.py` with GBM simulation
- [x] Implement `src/opt_research/volatility_surface.py` (SVI parameterization, no-arb constraints)
- [x] Implement `src/opt_research/option_pricing.py` (BS pricing, Greeks)
- [x] Implement `src/opt_research/option_chain.py` (chain generation using vol surface)
- [x] Implement `src/opt_research/arbitrage_free.py` (validation logic)
- [x] Implement `src/opt_research/data_generator.py` (main orchestrator)

### Phase 3: Testing
- [ ] Create `tests/__init__.py`
- [ ] Create `tests/test_underlying.py` - test GBM properties
- [ ] Create `tests/test_volatility_surface.py` - **CRITICAL** test SVI constraints
- [ ] Create `tests/test_option_pricing.py` - test BS formula correctness
- [ ] Create `tests/test_option_chain.py` - test chain structure
- [ ] Create `tests/test_arbitrage_free.py` - **CRITICAL** arbitrage tests on final prices
- [ ] Run all tests and verify passing

### Phase 4: Data Generation
- [ ] Create `data/` directory
- [ ] Run `data_generator.py` to generate `synthetic_options.csv`
- [ ] Validate CSV structure and content

### Phase 5: Examples
- [ ] Create `examples/load_option_data.py`
- [ ] Verify example runs successfully

### Phase 6: Report
- [ ] Create `documents/report/synthetic_option_data_REPORT.md`
- [ ] Document test results
- [ ] Self-review against coding standards

---

## Change Log

*(To be updated during execution if plan deviates)*

| Date | Change | Reason |
|------|--------|--------|
| - | - | - |
