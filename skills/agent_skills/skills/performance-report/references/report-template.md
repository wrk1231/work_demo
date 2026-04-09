# Report Template

Use this structure for final output. Keep it concise, but do not skip the diagnosis.

## 1. Input diagnosis

State:

- input type: `Series` or `DataFrame`
- date axis used
- candidate columns inspected
- inferred frequency
- missing-value or coercion issues

Example:

"Input is a `DataFrame` with 6 columns. I used `date` as the time axis, coerced 3 numeric candidates, and inferred a daily frequency from mostly one-business-day spacing. Column `comment` was ignored as metadata. `strategy_ret` lost 2 rows during numeric coercion."

## 2. Selected series and why

State:

- chosen column
- series classification
- top alternative if ambiguity remains

Example:

"I selected `strategy_nav` as the primary series. It is strictly positive, date-aligned, and its name indicates a NAV path. `portfolio_value` is a secondary candidate but appears to be a similar level series rather than a distinct return stream."

## 3. Transformations applied

State only what was actually done.

Examples:

- "Derived period returns from NAV with `pct_change()`."
- "Computed cumulative PnL from period PnL."
- "Dropped 4 duplicate timestamps after keeping the last observation per day."

## 4. Summary metrics

Report the metric block that matches the selected series type. Do not include invalid metrics.

## 5. Risk metrics

Include:

- drawdown stats where valid
- volatility where valid
- Sharpe where valid
- tail-shape stats such as skew and kurtosis when the sample is large enough

## 6. Optional charts

Recommend or create:

- cumulative curve
- drawdown
- return histogram
- rolling volatility or Sharpe when enough data exists

If charts are generated, hand them off to `mpl-standard-plot` conventions.

## 7. Warnings and caveats

State:

- uncertainty in column selection
- annualization risk
- irregular frequency
- missing values
- metric omissions and why
