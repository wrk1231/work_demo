from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


ANNUALIZATION = {
    "daily": 252,
    "weekly": 52,
    "monthly": 12,
    "quarterly": 4,
    "yearly": 1,
}


@dataclass
class AnalysisResult:
    column: str
    classification: str
    frequency: str
    report: dict[str, Any]


def infer_frequency(index: pd.DatetimeIndex) -> str:
    unique_index = pd.DatetimeIndex(sorted(index.dropna().unique()))
    if len(unique_index) < 3:
        return "daily"
    median_gap = unique_index.to_series().diff().dropna().median()
    days = median_gap.days
    if days <= 2:
        return "daily"
    if 5 <= days <= 10:
        return "weekly"
    if 20 <= days <= 40:
        return "monthly"
    if 60 <= days <= 120:
        return "quarterly"
    return "yearly"


def classify_series(name: str, series: pd.Series) -> str:
    lowered = name.lower()
    clean = pd.to_numeric(series, errors="coerce").dropna()

    if any(token in lowered for token in ("ret", "return", "rtn")) and clean.abs().quantile(0.95) <= 1.0:
        return "returns"
    if "pnl" in lowered or "profit" in lowered or "loss" in lowered:
        return "pnl"
    if any(token in lowered for token in ("nav", "wealth", "equity", "aum", "portfolio", "value")):
        return "nav_or_wealth"
    if any(token in lowered for token in ("price", "close", "px", "level", "index")):
        return "price_or_level"
    if clean.abs().quantile(0.95) <= 1.0 and clean.median() < 0.1:
        return "returns"
    if (clean > 0).mean() > 0.95:
        return "nav_or_wealth"
    return "pnl"


def select_primary_column(frame: pd.DataFrame) -> str:
    candidates = []
    for column in frame.columns:
        coerced = pd.to_numeric(frame[column], errors="coerce")
        score = coerced.notna().mean()
        lowered = column.lower()
        if any(token in lowered for token in ("ret", "return", "nav", "pnl", "strategy", "portfolio", "value")):
            score += 0.25
        if coerced.std(skipna=True) and coerced.std(skipna=True) > 0:
            score += 0.10
        candidates.append((score, column))
    if not candidates:
        raise ValueError("No candidate analysis columns found.")
    candidates.sort(reverse=True)
    return candidates[0][1]


def ensure_datetime_index(data: pd.Series | pd.DataFrame) -> pd.DataFrame:
    if isinstance(data, pd.Series):
        frame = data.to_frame(name=data.name or "value")
    else:
        frame = data.copy()

    if not isinstance(frame.index, pd.DatetimeIndex):
        date_column = None
        for candidate in ("date", "datetime", "timestamp", "time", "dt"):
            if candidate in frame.columns:
                date_column = candidate
                break
        if date_column is None:
            raise ValueError("No DatetimeIndex or date-like column found.")
        frame[date_column] = pd.to_datetime(frame[date_column], errors="coerce")
        frame = frame.set_index(date_column)

    frame.index = pd.to_datetime(frame.index, errors="coerce")
    frame = frame[~frame.index.isna()].sort_index()
    return frame


def compute_return_metrics(returns: pd.Series, frequency: str) -> dict[str, Any]:
    ann_factor = ANNUALIZATION[frequency]
    returns = pd.to_numeric(returns, errors="coerce").dropna()
    wealth = (1 + returns).cumprod()
    drawdown = wealth.divide(wealth.cummax()).subtract(1.0)

    vol = returns.std(ddof=1)
    sharpe = None if vol == 0 or pd.isna(vol) else returns.mean() / vol * ann_factor ** 0.5

    return {
        "sample_start": returns.index.min(),
        "sample_end": returns.index.max(),
        "count": int(returns.shape[0]),
        "cumulative_return": (1 + returns).prod() - 1,
        "annualized_return": (1 + returns).prod() ** (ann_factor / len(returns)) - 1,
        "annualized_vol": vol * ann_factor ** 0.5,
        "sharpe": sharpe,
        "max_drawdown": drawdown.min(),
        "hit_rate": (returns > 0).mean(),
        "best_period": returns.max(),
        "worst_period": returns.min(),
        "skew": returns.skew(),
        "kurtosis": returns.kurtosis(),
    }


def compute_pnl_metrics(pnl: pd.Series) -> dict[str, Any]:
    pnl = pd.to_numeric(pnl, errors="coerce").dropna()
    cum_pnl = pnl.cumsum()
    drawdown = cum_pnl.subtract(cum_pnl.cummax())
    return {
        "sample_start": pnl.index.min(),
        "sample_end": pnl.index.max(),
        "count": int(pnl.shape[0]),
        "cumulative_pnl": pnl.sum(),
        "average_period_pnl": pnl.mean(),
        "pnl_vol": pnl.std(ddof=1),
        "max_drawdown_on_cum_pnl": drawdown.min(),
        "hit_rate": (pnl > 0).mean(),
        "best_period": pnl.max(),
        "worst_period": pnl.min(),
    }


def analyze_performance(data: pd.Series | pd.DataFrame, column: str | None = None) -> AnalysisResult:
    frame = ensure_datetime_index(data)
    column = column or select_primary_column(frame)
    series = pd.to_numeric(frame[column], errors="coerce")
    classification = classify_series(column, series)
    frequency = infer_frequency(frame.index)

    if classification == "returns":
        report = compute_return_metrics(series.dropna(), frequency)
    elif classification in {"nav_or_wealth", "price_or_level"}:
        returns = series.sort_index().pct_change().dropna()
        report = compute_return_metrics(returns, frequency)
        report["transformation"] = "Derived returns with pct_change() from a level-like series."
    else:
        report = compute_pnl_metrics(series.dropna())
        report["warning"] = "Sharpe and return metrics omitted because the selected series looks like PnL."

    report["selected_series"] = column
    report["classification"] = classification
    report["frequency_guess"] = frequency
    return AnalysisResult(column=column, classification=classification, frequency=frequency, report=report)


if __name__ == "__main__":
    sample = pd.DataFrame(
        {
            "date": pd.date_range("2023-01-02", periods=252, freq="B"),
            "strategy_nav": 100 * (1 + pd.Series(0.0004, index=range(252))).cumprod(),
            "comment": ["ok"] * 252,
        }
    )
    result = analyze_performance(sample)
    print(result.report)
