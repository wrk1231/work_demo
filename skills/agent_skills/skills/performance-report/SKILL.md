---
name: performance-report
description: Diagnose messy pandas time series inputs, infer the correct analysis path, compute valid performance metrics, and produce a reusable report with explicit caveats for returns, NAV, price, or PnL data.
---

# Purpose

Use this skill to turn a messy pandas time series into a defensible performance report. The skill inspects the input, identifies candidate analysis columns, classifies the selected series, applies only valid transformations, and reports uncertainty instead of fabricating confidence.

# When to use

Use this skill for requests such as:

- "Analyze this strategy time series."
- "Generate a performance report from this DataFrame."
- "Figure out which column is the strategy and compute Sharpe and drawdown."
- "Compare the two candidate return columns."

Do not use it when:

- the user only wants a raw plot with no inference
- the repo already has a strict report function and the task is simply to call it

# Inputs expected

- A `pandas.Series` or `pandas.DataFrame`
- Optional metadata:
  - which column the user believes is primary
  - whether the data is returns, NAV, price, or PnL
  - benchmark series
  - risk-free assumption if the repo uses one

# Outputs expected

- A report with this structure:
  1. Input diagnosis
  2. Selected series and why
  3. Transformations applied
  4. Summary metrics
  5. Risk metrics
  6. Optional charts
  7. Warnings and caveats
- Optional charts that can be handed to `mpl-standard-plot`

# Step-by-step workflow

1. Inspect object type.
   Determine whether the input is a `Series` or `DataFrame`. If it is a `Series`, treat it as the primary candidate and still validate the index and dtype.

2. Infer the date axis.
   Prefer a `DatetimeIndex`. If none exists, inspect columns for date-like names such as `date`, `dt`, `timestamp`, or `time`. Convert only one date axis. If several plausible date columns exist, rank them and report the choice.

3. Identify candidate analysis columns.
   For a `DataFrame`, inspect numeric or numeric-like columns after coercion. Ignore obvious metadata columns such as IDs, names, text labels, currencies, or flags unless the repo documents them as analytical.

4. Classify each candidate column.
   Use column name, value scale, monotonicity, sign pattern, and distribution to classify each column as likely:
   - `returns`
   - `pnl`
   - `nav_or_wealth`
   - `price_or_level`

5. Rank candidates.
   Prefer:
   - an explicitly user-named column
   - columns whose names indicate strategy output, such as `ret`, `return`, `nav`, `portfolio`, `strategy`, or `pnl`
   - columns with low coercion loss
   - columns with a date-aligned history and meaningful variance

6. Select the primary analysis path.
   Apply these rules:
   - `returns`: use directly for return-based metrics
   - `nav_or_wealth` or `price_or_level`: derive returns first, then compute return-based metrics
   - `pnl`: compute a PnL report by default; compute return metrics only if a capital base or NAV is available

7. Infer frequency.
   Use the median spacing of the datetime index and map it to a normalized frequency. State uncertainty if the spacing is irregular or sparse.

8. Compute metrics that are valid for the selected path.
   Use the spec in `references/metrics-spec.md`. Omit or mark invalid metrics rather than forcing them.

9. Generate optional charts.
   If charts help, propose or create:
   - cumulative curve
   - drawdown
   - return histogram
   - rolling vol or rolling Sharpe when enough data exists

10. Write the report.
   Explain the inference, transformations, metrics, and caveats in plain English. Do not hide uncertain classification.

# Guardrails

- Do not compute Sharpe on raw prices, NAV levels, or PnL without a valid return transformation.
- Do not annualize without a documented or inferred frequency.
- Do not choose a column silently when multiple strong candidates exist.
- Do not treat strings that happened to coerce numerically as clean data without reporting coercion loss.
- Do not hide missing values or duplicated dates.
- Do not present a return report when only PnL was observed and no capital base is known.

# Acceptance criteria

- The report clearly explains which series was analyzed and why.
- Return-based metrics are only computed on actual or derived returns.
- Frequency assumptions are explicit.
- Ambiguity is surfaced instead of buried.
- The report structure is reusable across projects.

# Examples of good agent behavior

- "I selected `strategy_ret` because it is numeric, date-aligned, and its name clearly indicates returns. I ignored `strategy_name` and `book` because they are metadata."
- "The input looks like a NAV series, not returns, so I first derived period returns before computing annualized return, volatility, Sharpe, and drawdown."
- "Two columns remain plausible: `portfolio` and `nav`. I ranked `nav` first because it is smoother, strictly positive, and its name indicates a level series, but I am reporting both candidates instead of pretending certainty."
- "This appears to be raw PnL. I can report cumulative PnL and drawdown on cumulative PnL, but Sharpe requires either returns or a documented capital base."

# Reference files

Read these only when needed:

- [`references/input-normalization.md`](references/input-normalization.md) for the deterministic inference workflow
- [`references/metrics-spec.md`](references/metrics-spec.md) for valid metrics and formula rules
- [`references/report-template.md`](references/report-template.md) for the standard report structure
- [`references/example-queries.md`](references/example-queries.md) for prompt-to-analysis mappings
- [`references/performance_report_template.py`](references/performance_report_template.py) for a minimal normalization and metrics template
