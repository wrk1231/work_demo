# Design

This skill assumes a thin adapter layer between registry entries and vendor APIs.

## Operational model

The agent should separate four concerns:

1. interpret the user's language
2. resolve securities through the YAML registry
3. choose vendor identifiers and normalized fields
4. ask repo code to fetch the data

This separation matters because the agent should be able to explain each decision independently.

## Minimal adapter contract

The adapter can be a class, module, or set of functions. Keep it small. The contract should support:

- `resolve_security(registry_entry, field=None)`:
  returns a structure containing the chosen vendor ticker and normalized field
- `fetch_history(resolved, start=None, end=None, frequency=None)`:
  returns a date-indexed `Series` or single-column `DataFrame`
- `fetch_reference(resolved, fields)`:
  returns scalar metadata such as currency or sector when needed

The adapter should own vendor-native details:

- mapping normalized fields to vendor-native fields
- session management
- vendor-specific error handling
- frequency code translation
- repo-specific authentication

The skill should own:

- registry resolution
- ambiguity handling
- choice of economic meaning
- output normalization

## Vendor selection policy

Use the same rules across projects unless the repo overrides them:

1. explicit user vendor wins
2. required field availability wins
3. existing repo adapter path wins
4. otherwise choose the vendor whose default field is semantically closest

Example:

- Request: "Bloomberg `PX_LAST` for SPX and Datastream total return for AGG"
- Resolution:
  - `spx` via Bloomberg, field `px_last`
  - `agg` via Datastream, field `tot_return_index`

## DataFrame versus Series

Return a `Series` only when all of the following are true:

- one registry entry
- one normalized field
- one aligned output column

Return a `DataFrame` otherwise.

This keeps the object shape stable and easy to reason about.

## Output metadata to mention in agent responses

When summarizing a load, include:

- registry key
- vendor
- vendor ticker
- normalized field
- date range
- frequency
- any resampling or coercion

Keep the metadata in the response or in a light dict. Do not build an unnecessary metadata class unless the repo already uses one.
