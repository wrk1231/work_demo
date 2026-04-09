# Metrics Spec

This spec defines the minimum metric set and when each metric is valid.

## Base metadata

Always report:

- sample start
- sample end
- observation count
- frequency guess
- series classification

## Return-series metrics

Valid when the input is actual returns or returns derived from a level/NAV series.

- cumulative return
- annualized return
- annualized volatility
- Sharpe
- max drawdown
- drawdown duration, when feasible
- hit rate
- best period return
- worst period return
- skew
- kurtosis

Reference formulas:

```python
ann_factor = {"daily": 252, "weekly": 52, "monthly": 12, "quarterly": 4, "yearly": 1}[freq]
cumulative_return = (1 + returns).prod() - 1
annualized_return = (1 + cumulative_return) ** (ann_factor / len(returns)) - 1
annualized_vol = returns.std(ddof=1) * ann_factor ** 0.5
sharpe = returns.mean() / returns.std(ddof=1) * ann_factor ** 0.5
wealth = (1 + returns.fillna(0)).cumprod()
drawdown = wealth / wealth.cummax() - 1
max_drawdown = drawdown.min()
hit_rate = (returns > 0).mean()
```

Notes:

- Sharpe assumes a zero risk-free rate unless the repo explicitly supplies one.
- If volatility is zero or nearly zero, Sharpe is undefined.
- Annualized return is unreliable for very short samples. Report that caveat.

## PnL metrics

Valid when only currency PnL is available.

- cumulative PnL
- average period PnL
- PnL volatility
- best period PnL
- worst period PnL
- hit rate
- drawdown on cumulative PnL

Do not report:

- cumulative return
- annualized return
- Sharpe as a return metric

Unless the repo provides a documented capital base or exposure series.

## Drawdown duration

Feasible when a cumulative wealth or cumulative PnL path exists.

Simple approach:

- identify stretches where drawdown is below zero
- count periods until a new high water mark is reached

If the sample ends in drawdown, state that the current drawdown is still open.

## Best and worst period

Use the inferred frequency.

Examples:

- daily returns -> best day, worst day
- monthly returns -> best month, worst month

## Validity rules

Do not compute or present a metric if:

- the series classification does not support it
- there are too few observations
- frequency cannot be inferred or is too irregular for a credible annualization

When a metric is omitted, say why.
