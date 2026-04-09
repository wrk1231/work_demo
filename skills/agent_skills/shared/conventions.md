# Shared Conventions

This document defines conventions shared by the three skills. Follow these defaults unless the user or repository already defines stricter rules.

## Core principles

- Prefer deterministic resolution over agent improvisation.
- Use repository files before inventing new structure.
- Keep outputs easy to hand to downstream code: `pandas.Series`, `pandas.DataFrame`, plain dicts, and saved image files.
- State uncertainty explicitly. Do not hide ambiguity behind confident-looking tables or charts.
- When defaults are applied, say which defaults were chosen and why.

## Canonical object expectations

- Use a `DatetimeIndex` for time series outputs unless the user explicitly needs a date column.
- Keep the index sorted ascending.
- Use timezone-naive timestamps unless the source data is intraday and timezone matters.
- Use numeric dtypes for analysis columns. Coerce carefully and report dropped rows.
- Preserve the raw object only when needed for diagnostics. Downstream workflow should use normalized objects.

## Column naming

Use concise, stable names that survive plotting and reporting.

Preferred format:

`<security_key>[__<field>][__<frequency>]`

Examples:

- `spx`
- `spx__px_last`
- `agg__tot_return_index`
- `ust_10y__yield__monthly`

Rules:

- `security_key` is the YAML registry key.
- Omit the field suffix when exactly one requested field uses the registry default and the context is obvious.
- Include a field suffix when:
  - multiple fields are requested
  - the field is not the registry default
  - multiple vendors use semantically different defaults
- Include a frequency suffix only when the returned data is intentionally resampled or differs from the registry default.

## Frequency labels

Normalize user language to:

- `daily`
- `weekly`
- `monthly`
- `quarterly`
- `yearly`

Map common synonyms:

- `d`, `1d`, `business daily` -> `daily`
- `w`, `weekly` -> `weekly`
- `m`, `month-end`, `monthly` -> `monthly`
- `q`, `quarterly` -> `quarterly`
- `a`, `annual`, `yearly` -> `yearly`

If the vendor returns business-day data but the user says "daily", treat that as acceptable unless the request explicitly requires calendar days.

## Date parsing

- Accept ISO dates first: `YYYY-MM-DD`.
- Accept year-only inputs like `2010` and interpret as `2010-01-01`.
- Accept relative phrases only if the repo already has utilities for them; otherwise resolve them to explicit ISO dates in code and in the agent response.
- Reject impossible dates early.
- If the user omits a start date:
  - prefer the narrowest safe default already used in the repo
  - otherwise require a repository default or state that the full available history will be requested

## Missing values

- Do not forward-fill by default for analytics.
- For charts, leave gaps unless the chart type specifically requires a transformed series.
- For comparisons, align on the union of dates first, then drop missing rows only for the metric that requires complete overlap.
- Always report substantial row loss after coercion or alignment.

## Return, level, and PnL semantics

- `return` means period return, usually decimal unless a repo explicitly uses percent units.
- `level` means price, index level, NAV, wealth, or any cumulative state variable.
- `pnl` means period profit and loss in currency units, not normalized return.
- Do not compute return-based metrics directly on level or PnL inputs without a documented transformation.

## Validation checklist

Before handing data from one skill to the next, confirm:

1. Index is datetime-like and sorted.
2. Analysis columns are numeric.
3. Column names are stable and interpretable.
4. Units are known or explicitly unknown.
5. Frequency is known, inferred, or clearly marked as uncertain.

## Failure reporting

When a step fails, report:

1. what was requested
2. what was attempted
3. which rule blocked progress
4. what concrete file, identifier, or input is missing

Bad:

- "Data load failed."

Good:

- "The registry does not contain an entry matching `Euro Stoxx banks`. I checked keys, aliases, and vendor tickers in `sample_security_registry.yaml`. Add a registry entry or specify an existing alias."
