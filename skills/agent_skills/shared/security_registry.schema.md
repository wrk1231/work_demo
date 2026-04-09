# Security Registry Schema

The registry is a single YAML file that maps human-facing names to vendor identifiers and sensible defaults. The goal is safe extension by humans, not abstract completeness.

## File shape

Top-level structure:

```yaml
version: 1
defaults:
  frequency: daily
  field_priority:
    price: [px_last, close]
    total_return: [tot_return_index, px_total_return]
    yield: [yield_to_maturity, par_yield]
securities:
  spx:
    ...
```

Rules:

- `version` is required.
- `defaults` is optional but recommended.
- `securities` is required and contains a mapping of registry keys to entries.

## Entry schema

Each security entry should include:

```yaml
spx:
  internal_name: S&P 500 Index
  aliases:
    - SPX
    - S&P 500
    - S and P 500
  asset_class: equity_index
  vendors:
    bloomberg:
      ticker: SPX Index
      default_fields: [PX_LAST]
    datastream:
      ticker: S&PCOMP
      default_fields: [P]
  defaults:
    dataset: price
    field: px_last
    frequency: daily
    currency: USD
  output:
    column: spx
    family: spot_index
  notes: Spot index level. Not a total return series.
```

Required fields per entry:

- `internal_name`
- `aliases`
- `asset_class`
- `vendors`
- `defaults`

Strongly recommended:

- `output`
- `notes`

## Field definitions

### `internal_name`

Human-readable canonical label.

### `aliases`

List of human phrases used for resolution. Include:

- short tickers
- common long names
- frequent abbreviations

Keep aliases specific enough to avoid accidental matches.

### `asset_class`

Plain string used for heuristics, such as:

- `equity_index`
- `volatility_index`
- `bond_etf`
- `commodity`
- `fx`
- `rates`

### `vendors`

Map vendor name to vendor-specific identifiers and default fields.

Expected vendor keys:

- `bloomberg`
- `datastream`

Each vendor block may contain:

- `ticker`: vendor identifier used for historical queries
- `default_fields`: vendor-native field names
- `reference_fields`: optional reference-data defaults
- `notes`: optional vendor-specific caveats

### `defaults`

Repository-level neutral defaults used by the agent.

Expected keys:

- `dataset`: one of `price`, `total_return`, `yield`, `spread`, `nav`, or another repo-defined semantic type
- `field`: normalized field name such as `px_last` or `tot_return_index`
- `frequency`: normalized label from the shared conventions
- `currency`: optional reporting currency

### `output`

Optional output hints:

- `column`: preferred base column name
- `family`: semantic family such as `spot_index`, `total_return_index`, or `volatility_future`

### `notes`

Plain text for ambiguity handling, caveats, or scope limits.

## Normalized field names

Use normalized field names in `defaults.field` even if vendors use different labels.

Recommended base vocabulary:

- `px_last`
- `close`
- `open`
- `high`
- `low`
- `volume`
- `tot_return_index`
- `yield_to_maturity`
- `par_yield`
- `nav`
- `pnl`

Map vendor-native fields in adapter code, not in the skill.

Examples:

- Bloomberg `PX_LAST` -> `px_last`
- Datastream `P` -> `px_last`
- Datastream `RI` -> `tot_return_index`

## Extension rules

When adding a new security:

1. Choose a stable registry key in lowercase snake case.
2. Add at least one vendor identifier for each subscription that can support the asset.
3. Set `defaults.dataset` to the most common use case, not the most convenient vendor field.
4. Add notes when ambiguity is likely.
5. Keep aliases minimal; add only names users actually say.

## Validation rules

A valid registry should satisfy:

1. Each key is unique.
2. No alias duplicates another key or alias unless both entries mark the ambiguity in `notes`.
3. At least one vendor block exists per entry.
4. `defaults.field` is consistent with `defaults.dataset`.
5. `output.column`, if present, is unique across entries.

## Agent resolution order

Given a user request:

1. Exact registry key match.
2. Exact alias match, case-insensitive.
3. Exact vendor ticker match, case-insensitive.
4. Normalized phrase match against aliases and `internal_name`.
5. If multiple candidates remain, stop and report the top candidates.

Do not use fuzzy matching that could silently pick the wrong instrument.
