# Example Queries

## Example 1

User request:

"Load SPX and VIX daily closes since 2010."

Mapping:

- `SPX` -> registry key `spx`
- `VIX` -> registry key `vix`
- field intent `daily closes` -> normalized field `px_last`
- start date `2010` -> `2010-01-01`
- frequency `daily`

Expected result:

- `DataFrame` with columns `spx` and `vix`

## Example 2

User request:

"Get AGG total return series."

Mapping:

- `AGG` -> registry key `agg`
- phrase `total return series` -> `tot_return_index`
- vendor: choose default supported vendor if no explicit preference

Expected result:

- `Series` named `agg`

## Example 3

User request:

"Pull Bloomberg PX_LAST for SPX and Datastream total return for AGG."

Mapping:

- `spx`:
  - vendor `bloomberg`
  - vendor field `PX_LAST`
  - normalized field `px_last`
- `agg`:
  - vendor `datastream`
  - phrase `total return` -> normalized field `tot_return_index`
  - adapter maps to vendor-native Datastream field such as `RI`

Expected result:

- `DataFrame` with columns `spx` and `agg`
- response text mentions mixed vendors explicitly

## Example 4

User request:

"Load SPX return series."

Handling:

- `spx` exists, but sample registry notes that it is a spot index level
- `return series` is ambiguous:
  - derive returns from `spx` levels
  - load a separate total return index if one exists

Expected agent behavior:

- do not silently choose
- explain that the registry does not currently encode SPX total return
- if the user only needs derived spot returns for analytics, say that this is a transformation step rather than a direct registry field

## Example 5

User request:

"Load VIX futures."

Handling:

- `vix` in the sample registry is the spot index only
- no futures entry exists

Expected agent behavior:

- report that the registry lacks a VIX futures entry
- do not substitute the spot index
