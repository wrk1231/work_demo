from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "shared" / "sample_security_registry.yaml"
STYLE_TARGET = ROOT / "styles" / "house.mplstyle"
MPLCONFIGDIR = ROOT / ".mplconfig"

os.environ.setdefault("MPLCONFIGDIR", str(MPLCONFIGDIR))


def load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


market_loader = load_module(
    "market_loader_template",
    ROOT / "skills" / "market-data-loader" / "references" / "market_data_loader_template.py",
)
plotting = load_module(
    "mpl_plot_template",
    ROOT / "skills" / "mpl-standard-plot" / "references" / "mpl_standard_plot_template.py",
)
performance = load_module(
    "performance_template",
    ROOT / "skills" / "performance-report" / "references" / "performance_report_template.py",
)


class DemoAdapter(market_loader.MarketDataAdapter):
    """Offline adapter that returns synthetic data with stable shapes for the demo."""

    def fetch_history(
        self,
        resolved: market_loader.ResolvedSecurity,
        *,
        start: str | None = None,
        end: str | None = None,
        frequency: str | None = None,
    ) -> pd.Series:
        index = pd.date_range(start=start or "2020-01-01", end=end or "2020-12-31", freq="B")
        step = pd.Series(range(len(index)), index=index, dtype="float64")
        if resolved.key == "spx":
            daily_returns = 0.0001 + (step % 17) * 0.00005 - 0.0003
            values = 3000 * (1 + daily_returns).cumprod()
        elif resolved.key == "agg":
            daily_returns = 0.00006 + (step % 11) * 0.00004 - 0.0002
            values = 100 * (1 + daily_returns).cumprod()
        else:
            daily_returns = 0.00008 + (step % 13) * 0.00003 - 0.00018
            values = 50 * (1 + daily_returns).cumprod()
        return values.rename(resolved.output_column or resolved.key)


def ensure_demo_style() -> Path:
    STYLE_TARGET.parent.mkdir(parents=True, exist_ok=True)
    STYLE_TARGET.write_text((ROOT / "examples" / "house_demo.mplstyle").read_text(encoding="utf-8"), encoding="utf-8")
    return STYLE_TARGET


def main() -> None:
    style_path = ensure_demo_style()
    print(f"Using style file: {style_path}")

    raw = market_loader.load_history(
        registry_path=REGISTRY_PATH,
        requests=[
            {"instrument": "SPX", "vendor": "bloomberg", "field": "px_last"},
            {"instrument": "AGG", "vendor": "datastream", "field": "tot_return_index"},
        ],
        adapter=DemoAdapter(),
        start="2020-01-01",
        end="2020-12-31",
    )
    if isinstance(raw, pd.Series):
        raw = raw.to_frame()

    returns = raw.pct_change().dropna()
    plotting.plot_cumulative_returns(
        returns,
        repo_root=ROOT,
        title="Demo Cumulative Returns",
        output_path=ROOT / "examples" / "demo_cumulative_returns.png",
    )
    plotting.plot_drawdown(
        returns,
        repo_root=ROOT,
        title="Demo Drawdown",
        output_path=ROOT / "examples" / "demo_drawdown.png",
    )

    result = performance.analyze_performance(returns[["agg"]], column="agg")
    print("Performance report:")
    for key, value in result.report.items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    main()
