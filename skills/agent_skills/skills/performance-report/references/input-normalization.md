# Input Normalization

This note defines a deterministic normalization workflow for messy time series.

## Step 1: object inspection

If the input is a `Series`:

- keep the series name if present
- validate the index
- coerce numeric values carefully

If the input is a `DataFrame`:

- list columns
- locate a date axis
- coerce candidate numeric columns
- measure row loss by coercion

## Step 2: date axis inference

Preferred order:

1. existing `DatetimeIndex`
2. column named `date`, `datetime`, `timestamp`, `time`, or `dt`
3. a column with high datetime parse success and mostly unique values

After selection:

- convert to pandas datetime
- drop rows with missing dates only if unavoidable and report how many
- sort ascending
- check for duplicates and either aggregate deliberately or report them

## Step 3: candidate column identification

Rank columns by:

1. explicit user hint
2. analytical names:
   - `ret`, `return`, `returns`
   - `pnl`
   - `nav`, `value`, `wealth`, `equity`
   - `price`, `close`, `level`
   - `strategy`, `portfolio`
3. numeric coercion success
4. non-trivial variance

Demote columns whose names look like metadata:

- `id`
- `name`
- `ticker`
- `asset`
- `desk`
- `currency`
- `comment`

## Step 4: classification heuristics

These heuristics are directional, not perfect. Report uncertainty when signals conflict.

### Likely returns

Signals:

- names contain `ret`, `return`, `rtn`
- values mostly between `-1` and `1`
- many sign changes
- distribution centered near zero
- compounding makes economic sense

### Likely PnL

Signals:

- names contain `pnl`, `profit`, `loss`
- values can be large positive and negative currency amounts
- cumulative sum yields a plausible equity curve
- no obvious bounded return scale

### Likely NAV or wealth

Signals:

- names contain `nav`, `wealth`, `equity`, `aum`
- values usually positive
- smoother path than returns
- percentage changes look plausible as returns

### Likely price or level

Signals:

- names contain `price`, `close`, `px`, `level`, `index`
- values positive
- first differences are less interpretable than percentage changes

## Step 5: frequency inference

Use median date spacing after sorting unique timestamps.

Suggested mapping:

- median gap <= 2 days -> `daily`
- median gap between 5 and 10 days -> `weekly`
- median gap between 20 and 40 days -> `monthly`
- median gap between 60 and 120 days -> `quarterly`
- median gap > 200 days -> `yearly`

If many gaps differ sharply, label the frequency as irregular and be conservative about annualization.

## Step 6: transformation rules

- `returns`: use directly
- `nav_or_wealth` or `price_or_level`: derive returns with `pct_change()`
- `pnl`: keep as PnL for primary reporting; only derive returns when a capital base exists

For level-to-return conversion:

```python
returns = levels.sort_index().pct_change().dropna()
```

For PnL cumulative path:

```python
cum_pnl = pnl.sort_index().cumsum()
```

## Step 7: uncertainty reporting

If two columns are close contenders, present both with a ranking table in prose:

- which column ranked first
- which signals drove the ranking
- what remains uncertain

Never say "selected automatically" without showing the basis.
