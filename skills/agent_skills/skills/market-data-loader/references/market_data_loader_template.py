from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


@dataclass(frozen=True)
class ResolvedSecurity:
    key: str
    vendor: str
    vendor_ticker: str
    normalized_field: str
    frequency: str
    currency: str | None = None
    output_column: str | None = None


class MarketDataAdapter:
    """Replace the NotImplementedError bodies with repo-specific vendor code."""

    def fetch_history(
        self,
        resolved: ResolvedSecurity,
        *,
        start: str | None = None,
        end: str | None = None,
        frequency: str | None = None,
    ) -> pd.Series:
        raise NotImplementedError("Connect this method to Bloomberg or Datastream in your repo.")


def load_registry(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        registry = yaml.safe_load(handle)
    if "securities" not in registry:
        raise ValueError("Registry must contain a top-level 'securities' mapping.")
    return registry


def _normalize_text(value: str) -> str:
    return " ".join(value.strip().lower().replace("&", "and").split())


def resolve_security(registry: dict[str, Any], query: str) -> tuple[str, dict[str, Any]]:
    securities = registry["securities"]
    normalized_query = _normalize_text(query)

    if query in securities:
        return query, securities[query]

    exact_alias_matches: list[tuple[str, dict[str, Any]]] = []
    normalized_matches: list[tuple[str, dict[str, Any]]] = []

    for key, entry in securities.items():
        aliases = entry.get("aliases", [])
        vendors = entry.get("vendors", {})
        names_to_check = [key, entry.get("internal_name", ""), *aliases]

        if any(query.lower() == alias.lower() for alias in aliases):
            exact_alias_matches.append((key, entry))
            continue

        for vendor_block in vendors.values():
            ticker = vendor_block.get("ticker")
            if isinstance(ticker, str) and ticker.lower() == query.lower():
                exact_alias_matches.append((key, entry))
                break

        if any(_normalize_text(str(name)) == normalized_query for name in names_to_check):
            normalized_matches.append((key, entry))

    matches = exact_alias_matches or normalized_matches
    if not matches:
        raise KeyError(f"No registry entry matches {query!r}.")
    if len(matches) > 1:
        keys = ", ".join(match[0] for match in matches)
        raise ValueError(f"Ambiguous registry match for {query!r}: {keys}")
    return matches[0]


def choose_field(entry: dict[str, Any], requested_field: str | None = None) -> str:
    if requested_field:
        return requested_field.lower()
    return str(entry["defaults"]["field"]).lower()


def choose_vendor(entry: dict[str, Any], requested_vendor: str | None = None) -> str:
    vendors = entry["vendors"]
    if requested_vendor:
        if requested_vendor not in vendors:
            raise KeyError(f"Vendor {requested_vendor!r} is not available for this entry.")
        return requested_vendor
    if "bloomberg" in vendors:
        return "bloomberg"
    return next(iter(vendors))


def build_resolved_security(
    key: str,
    entry: dict[str, Any],
    *,
    requested_vendor: str | None = None,
    requested_field: str | None = None,
    requested_frequency: str | None = None,
) -> ResolvedSecurity:
    vendor = choose_vendor(entry, requested_vendor=requested_vendor)
    vendor_block = entry["vendors"][vendor]
    field = choose_field(entry, requested_field=requested_field)
    defaults = entry["defaults"]
    output = entry.get("output", {})
    return ResolvedSecurity(
        key=key,
        vendor=vendor,
        vendor_ticker=str(vendor_block["ticker"]),
        normalized_field=field,
        frequency=requested_frequency or str(defaults["frequency"]).lower(),
        currency=defaults.get("currency"),
        output_column=output.get("column", key),
    )


def load_history(
    registry_path: str | Path,
    requests: list[dict[str, str]],
    adapter: MarketDataAdapter,
    *,
    start: str | None = None,
    end: str | None = None,
) -> pd.Series | pd.DataFrame:
    registry = load_registry(registry_path)
    frames: list[pd.Series] = []

    for request in requests:
        key, entry = resolve_security(registry, request["instrument"])
        resolved = build_resolved_security(
            key,
            entry,
            requested_vendor=request.get("vendor"),
            requested_field=request.get("field"),
            requested_frequency=request.get("frequency"),
        )
        series = adapter.fetch_history(
            resolved,
            start=start,
            end=end,
            frequency=resolved.frequency,
        )
        if not isinstance(series, pd.Series):
            raise TypeError("Adapter must return a pandas Series for each history request.")
        series = pd.to_numeric(series, errors="coerce").sort_index()
        column_name = resolved.output_column or resolved.key
        if resolved.normalized_field != str(entry["defaults"]["field"]).lower():
            column_name = f"{column_name}__{resolved.normalized_field}"
        frames.append(series.rename(column_name))

    if not frames:
        raise ValueError("No requests supplied.")
    if len(frames) == 1:
        return frames[0]
    return pd.concat(frames, axis=1)


if __name__ == "__main__":
    # Replace DummyAdapter with your repo's Bloomberg/Datastream adapter implementation.
    class DummyAdapter(MarketDataAdapter):
        def fetch_history(
            self,
            resolved: ResolvedSecurity,
            *,
            start: str | None = None,
            end: str | None = None,
            frequency: str | None = None,
        ) -> pd.Series:
            index = pd.date_range(start=start or "2020-01-01", periods=5, freq="B")
            values = pd.Series(range(100, 105), index=index, name=resolved.output_column)
            return values

    data = load_history(
        registry_path=Path(__file__).resolve().parents[2] / "shared" / "sample_security_registry.yaml",
        requests=[
            {"instrument": "SPX", "vendor": "bloomberg", "field": "px_last"},
            {"instrument": "AGG", "vendor": "datastream", "field": "tot_return_index"},
        ],
        adapter=DummyAdapter(),
        start="2020-01-01",
    )
    print(data)
