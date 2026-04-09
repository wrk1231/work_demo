---
name: market-data-loader
description: Resolve human-language market data requests through a YAML security registry, choose Bloomberg or Datastream identifiers deterministically, and return normalized pandas Series or DataFrames for research workflows.
---

# Purpose

Use this skill when the user wants market data loaded from a registry-backed security universe instead of ad hoc ticker guesses. The skill resolves human requests, chooses a vendor and field, handles ambiguity explicitly, and returns pandas objects that downstream plotting and performance analysis can consume.

# When to use

Use this skill for requests such as:

- "Load SPX and VIX daily closes since 2010."
- "Get AGG total return series."
- "Pull Bloomberg `PX_LAST` for SPX and Datastream total return for AGG."
- "Resolve these names through our security registry and return a DataFrame."

Do not use it when:

- the user already provided a fully prepared pandas object
- the repo has no registry and the task is not about building one
- the request is for vendor functionality outside simple historical or reference data

# Inputs expected

- A YAML security registry file following [`../../shared/security_registry.schema.md`](../../shared/security_registry.schema.md)
- A user request containing one or more instruments, dates, fields, or frequencies
- Repo-specific adapter code or notebook code that can call Bloomberg and Datastream
- Optional user hints:
  - vendor choice
  - output shape
  - explicit fields
  - explicit frequency

# Outputs expected

- A normalized `pandas.Series` when exactly one security and one field are requested
- A normalized `pandas.DataFrame` when multiple securities or fields are requested
- A short resolution summary stating:
  - which registry entries were matched
  - which vendor identifiers were used
  - which fields and frequency were chosen
  - any ambiguity or fallback applied

# Step-by-step workflow

1. Locate the registry file.
   Prefer a repo-specific registry if one already exists. If none exists, use the path explicitly provided by the user. If the task is only a demo or documentation task, use the shared sample registry.

2. Read the registry schema and registry file.
   Validate the basic shape before using it: top-level `securities` exists, each selected entry has `aliases`, `vendors`, and `defaults`.

3. Parse the user request into structured intent.
   Extract:
   - requested instruments
   - vendor constraints, if any
   - field intent, such as `close`, `price`, `return series`, or `yield`
   - date range
   - frequency
   - desired output shape

4. Resolve each instrument deterministically.
   Use the resolution order from [`../../shared/security_registry.schema.md`](../../shared/security_registry.schema.md):
   exact key, exact alias, exact vendor ticker, normalized phrase match. If more than one candidate remains, stop and report the ambiguity.

5. Choose the vendor per security.
   Apply these rules in order:
   - if the user specified a vendor, use it if the registry entry supports it
   - if the requested field exists only in one vendor block, use that vendor
   - otherwise prefer the repo's existing adapter path
   - if no repo preference exists, prefer Bloomberg for Bloomberg-native field requests and Datastream for Datastream-native field requests
   - if still tied, use the first available vendor but state that choice

6. Choose fields.
   Apply these rules:
   - if the user explicitly names a normalized field, use it
   - if the user names a vendor-native field, map it through adapter logic and keep the normalized field in the output metadata
   - if the user says `return series`, prefer `tot_return_index`
   - if the user says `close`, `last`, or `price`, prefer `px_last`
   - if the user omits the field, use `defaults.field`
   - if the phrase is ambiguous and would materially change meaning, stop and report the top interpretations

7. Normalize dates and frequency.
   Follow [`../../shared/conventions.md`](../../shared/conventions.md). Convert year-only inputs to `YYYY-01-01`, normalize frequency labels, and keep vendor-native business-day history unless explicit resampling is requested.

8. Call the adapter.
   Expect a small adapter layer, not a full framework. A minimal interface is enough:

```python
from dataclasses import dataclass
from typing import Iterable, Mapping, Optional

import pandas as pd

@dataclass(frozen=True)
class ResolvedSecurity:
    key: str
    vendor: str
    vendor_ticker: str
    normalized_field: str
    frequency: str
    currency: str | None = None

class MarketDataAdapter:
    def resolve_security(self, registry_entry: Mapping, *, field: str | None = None) -> ResolvedSecurity:
        raise NotImplementedError

    def fetch_history(
        self,
        resolved: ResolvedSecurity,
        start: str | None = None,
        end: str | None = None,
        frequency: str | None = None,
    ) -> pd.Series:
        raise NotImplementedError

    def fetch_reference(
        self,
        resolved: ResolvedSecurity,
        fields: Iterable[str],
    ) -> Mapping[str, object]:
        raise NotImplementedError
```

9. Normalize the output object.
   - sort by date ascending
   - coerce to numeric where appropriate
   - apply canonical column naming from [`../../shared/conventions.md`](../../shared/conventions.md)
   - return `Series` for one security plus one field
   - return `DataFrame` otherwise

10. Report resolution and caveats.
   State what was loaded and what assumptions were used. If defaults were chosen, say so.

# Guardrails

- Do not bypass the registry by guessing tickers from memory when a registry is available.
- Do not silently choose between spot, total return, and futures variants.
- Do not silently convert vendor-native fields into different economic concepts.
- Do not forward-fill missing prices before handing them to performance analysis.
- Do not merge multiple securities into one column.
- Do not assume a specific Bloomberg or Datastream package name; work through the repo's adapter code.

# Acceptance criteria

- The requested instruments are resolved from one YAML registry file.
- Vendor selection is deterministic and explainable.
- Field defaults are consistent with the registry and the user request.
- Ambiguous requests are surfaced rather than guessed.
- The returned pandas object has stable names, sorted dates, and numeric values suitable for plotting or reporting.

# Examples of good agent behavior

- "I matched `SPX` to registry key `spx` and used Bloomberg ticker `SPX Index` with normalized field `px_last` because you asked for close prices."
- "I matched `AGG` to `agg`. Because you asked for a return series and the registry default dataset is `total_return`, I used normalized field `tot_return_index`."
- "Your request for `VIX` is clear for the spot index, but not for futures. I will not assume a futures contract without a specific registry entry."
- "The registry has no entry matching `Euro Stoxx banks`. I checked keys, aliases, and vendor tickers. Add a registry entry or give an existing alias."

# Reference files

Read these only when needed:

- [`references/design.md`](references/design.md) for the operational model and adapter contract
- [`references/yaml-format.md`](references/yaml-format.md) for registry details and defaults
- [`references/example-queries.md`](references/example-queries.md) for concrete language-to-registry mappings
- [`references/market_data_loader_template.py`](references/market_data_loader_template.py) for a minimal registry loader and adapter template
