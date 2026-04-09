# YAML Format

This note complements the shared schema with practical defaults and ambiguity rules.

## Default selection rules

When the user does not specify a field:

1. If the user phrase implies a semantic dataset, use it.
   - `return series` -> `tot_return_index`
   - `yield` -> `par_yield` or `yield_to_maturity`
   - `price`, `close`, `spot`, `level` -> `px_last`
2. Otherwise use `defaults.field`.
3. If the request still maps to multiple economic concepts, stop and explain the ambiguity.

## Ambiguity handling

The registry should not try to solve ambiguity by stuffing multiple products into one entry.

Preferred pattern:

- `spx` for spot index level
- `spx_tr` for total return index if the repo needs it
- `vix` for spot volatility index
- `vix_1` or another explicit key for a futures series

If the registry does not distinguish the variants, the agent should not guess.

Examples:

- "Load SPX" -> safe to use `spx` spot index
- "Load SPX return series" -> if only `spx` exists and notes say spot only, explain that total return is not represented and offer the best existing alternative only if clearly documented
- "Load VIX" -> safe to use spot `vix`
- "Load VIX futures" -> require a futures registry entry
- "Get AGG" -> use `agg` default `tot_return_index` because the registry declares that as the default dataset
- "Get AGG price" -> override the default and request `px_last` if the adapter supports it

## Naming output columns

Use the registry `output.column` when present. Otherwise fall back to the registry key.

Examples:

- one field: `spx`
- multiple fields for one security: `spx__px_last`, `spx__volume`
- mixed frequencies after resampling: `spx__px_last__monthly`

## Frequency normalization

If the user requests a normalized reporting frequency, prefer:

- vendor-native frequency when the vendor can supply it directly
- otherwise resample after fetch and state the resampling rule

Resampling defaults:

- prices and levels: last observation in period
- yields and spreads: last observation in period unless the repo says average
- returns: compound within period, not sum, unless the series is known to be arithmetic PnL

## Failure messages

Missing registry entry:

- "The registry does not contain an entry matching `MSCI EM value`. I checked keys, aliases, and vendor tickers."

Ambiguous registry match:

- "The phrase `SPX return` could mean a total return index or a return series derived from spot levels. The current registry only documents `spx` as a spot index."

Unsupported vendor:

- "The registry entry `ust_10y` has Bloomberg and Datastream identifiers, but your repo does not expose a Datastream adapter yet."
