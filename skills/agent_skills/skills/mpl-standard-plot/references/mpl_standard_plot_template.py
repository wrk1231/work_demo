from __future__ import annotations

from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd


def find_style_file(repo_root: str | Path) -> Path:
    repo_root = Path(repo_root)
    candidates = [
        repo_root / "styles" / "house.mplstyle",
        repo_root / "plotting" / "house.mplstyle",
        repo_root / "config" / "house.mplstyle",
    ]
    candidates.extend(sorted(repo_root.glob("*.mplstyle")))

    for candidate in candidates:
        if candidate.exists():
            return candidate

    matches = sorted(repo_root.rglob("*.mplstyle"))
    if not matches:
        raise FileNotFoundError("No .mplstyle file found in repo.")
    return matches[0]


def use_house_style(repo_root: str | Path) -> Path:
    style_path = find_style_file(repo_root)
    plt.style.use(style_path)
    return style_path


def _coerce_series_or_frame(data: pd.Series | pd.DataFrame) -> pd.DataFrame:
    if isinstance(data, pd.Series):
        frame = data.to_frame(name=data.name or "value")
    else:
        frame = data.copy()
    frame.index = pd.to_datetime(frame.index)
    frame = frame.sort_index()
    return frame.apply(pd.to_numeric, errors="coerce")


def plot_cumulative_returns(
    returns: pd.Series | pd.DataFrame,
    *,
    repo_root: str | Path,
    title: str = "Cumulative Returns",
    output_path: str | Path | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    use_house_style(repo_root)
    frame = _coerce_series_or_frame(returns)
    wealth = (1 + frame.fillna(0)).cumprod()

    fig, ax = plt.subplots(figsize=(11, 6))
    wealth.plot(ax=ax)
    ax.set_title(title)
    ax.set_ylabel("Growth of 1")
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
    ax.legend(loc="best")

    if output_path:
        fig.savefig(output_path, bbox_inches="tight")
    return fig, ax


def plot_drawdown(
    returns: pd.Series | pd.DataFrame,
    *,
    repo_root: str | Path,
    title: str = "Drawdown",
    output_path: str | Path | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    use_house_style(repo_root)
    frame = _coerce_series_or_frame(returns)
    wealth = (1 + frame.fillna(0)).cumprod()
    drawdown = wealth.divide(wealth.cummax()).subtract(1.0)

    fig, ax = plt.subplots(figsize=(11, 4))
    drawdown.plot(ax=ax)
    ax.set_title(title)
    ax.set_ylabel("Drawdown")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1.0))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
    ax.legend(loc="best")

    if output_path:
        fig.savefig(output_path, bbox_inches="tight")
    return fig, ax


if __name__ == "__main__":
    repo_root = Path(".")
    sample_index = pd.date_range("2022-01-03", periods=252, freq="B")
    sample_returns = pd.DataFrame(
        {
            "strategy_a": pd.Series(0.0005, index=sample_index),
            "strategy_b": pd.Series(0.0003, index=sample_index),
        }
    )
    plot_cumulative_returns(sample_returns, repo_root=repo_root, output_path="cumulative_returns.png")
    plot_drawdown(sample_returns, repo_root=repo_root, output_path="drawdown.png")
