# Chart Recipes

These recipes assume pandas inputs and pure matplotlib. Use seaborn only if the repo already relies on it.

## Line chart

Use for one level or one metric over time.

- default figure size: `(10, 5)`
- leave missing data as gaps
- use a title only if it adds context beyond the series name

## Multi-line chart

Use for 2 to 6 comparable series.

- default figure size: `(11, 6)`
- align by index
- include a legend unless labels are directly annotated
- if more than 6 series, consider small multiples or a focused subset

## Cumulative return chart

Use for return series, not raw prices.

Reference snippet:

```python
import pandas as pd
import matplotlib.pyplot as plt

wealth = (1 + returns.fillna(0)).cumprod()
ax = wealth.plot(figsize=(11, 6))
ax.set_ylabel("Growth of 1")
```

Notes:

- returns should be decimal, not percent
- if the series is a NAV or price, transform to returns first or state that you are plotting levels instead

## Drawdown chart

Use for level or wealth series after constructing a running peak.

Reference snippet:

```python
wealth = (1 + returns.fillna(0)).cumprod()
drawdown = wealth / wealth.cummax() - 1
ax = drawdown.plot(figsize=(11, 4))
ax.set_ylabel("Drawdown")
```

Use percentage formatting on the y-axis.

## Rolling Sharpe or rolling volatility

Use only when the input is a return series and there are enough observations.

- default lookback windows:
  - `21` for short-term daily diagnostics
  - `63` for quarterly-ish daily diagnostics
  - `252` for annual daily diagnostics
- rolling volatility:
  - `returns.rolling(window).std() * annualization_factor ** 0.5`
- rolling Sharpe:
  - annualized rolling mean divided by annualized rolling std

Do not compute rolling Sharpe on price, NAV, or PnL levels.

## Histogram

Use for return distributions or residuals.

- default figure size: `(8, 5)`
- use a moderate bin count such as `30`
- for return data, format the x-axis as percent when appropriate

## Scatter plot

Use for factor-versus-market, actual-versus-predicted, or cross-sectional diagnostics.

- default figure size: `(7, 7)`
- if adding a regression line, make the line explicit and keep marker styling minimal
- label axes with the compared quantities

## Bar chart

Use for discrete comparisons such as annual returns or metric tables turned into graphics.

- sort bars deliberately
- rotate labels only when necessary
- do not use stacked bars unless the decomposition matters

## Heatmap

Pure matplotlib is acceptable for small matrices such as monthly return grids or correlation matrices.

- use `imshow` or `pcolormesh`
- always add a colorbar
- set explicit tick labels
- annotate cells only when the matrix is small enough to remain readable

Fallback:

- if the heatmap is complex and the repo has no helper, use a numeric table or a simpler chart instead of building elaborate custom styling

## Saving figures

Use:

```python
fig.savefig(output_path, bbox_inches="tight")
```

For publication workflows, add explicit `dpi` only if the repo standard requires it.
