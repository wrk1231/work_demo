# Python Research Skill Suite

This demo package contains three Codex-style skills for a Python research workflow:

1. `market-data-loader` resolves human requests to securities in a YAML registry and loads normalized pandas objects through vendor adapters.
2. `mpl-standard-plot` turns pandas outputs into consistent matplotlib charts using the repo's house `.mplstyle`.
3. `performance-report` diagnoses messy time series inputs, selects the right analysis path, and produces a reusable report.

The suite is intentionally small. It does not define a framework, service, or CLI. It defines agent behavior, file conventions, validation rules, and a few minimal code snippets that can be copied into a repo with minimal edits.

## How the skills fit together

Typical workflow:

1. Maintain a YAML security registry such as [`shared/sample_security_registry.yaml`](shared/sample_security_registry.yaml).
2. Use `market-data-loader` to resolve requests like "load SPX and VIX daily closes since 2010".
3. Use `mpl-standard-plot` to visualize the resulting series with the repo's `.mplstyle`.
4. Use `performance-report` to analyze returns, NAV, price, or PnL series without pretending certainty when the input is messy.

## Shared conventions

- Registry format and validation: [`shared/security_registry.schema.md`](shared/security_registry.schema.md)
- Common naming, typing, and agent behavior: [`shared/conventions.md`](shared/conventions.md)
- Concrete sample registry: [`shared/sample_security_registry.yaml`](shared/sample_security_registry.yaml)

## Example prompts

- "Load SPX and VIX daily closes since 2010 and return a DataFrame."
- "Pull Bloomberg `PX_LAST` for SPX and Datastream total return for AGG."
- "Plot cumulative returns for these three strategy columns using house style."
- "Make a drawdown chart for this NAV series."
- "Generate a performance report from this DataFrame and explain which column you selected."

## Assumptions

- Python-first workflow with `pandas` and `matplotlib`.
- Bloomberg and Datastream access exist, but the exact Python wrapper may vary by repo.
- The agent works in a repository that can hold a YAML registry and a `.mplstyle` file.
- The agent should be usable both interactively and in repo-based scripts or notebooks.

## Minimal integration pattern

Keep repo-specific logic outside the skills. In a real project, add:

- one registry file, usually under `config/` or `data/`
- one small adapter module for Bloomberg and Datastream access
- one house `.mplstyle` file, preferably near other plotting config
- one utility module for normalization and report generation if the analysis is repeated

These skills define the operational contract for those pieces.

## Reference templates

Each skill now includes a small Python template:

- `market-data-loader`: `references/market_data_loader_template.py`
- `mpl-standard-plot`: `references/mpl_standard_plot_template.py`
- `performance-report`: `references/performance_report_template.py`

These are reference implementations, not a framework. They are meant to be copied into a repo and edited in place.

## Demo assets

The suite also includes two demo-oriented files:

- `examples/house_demo.mplstyle`: a small house style file suitable for local demos
- `examples/end_to_end_demo.py`: a single script that shows registry-backed loading, house-style plotting, and performance analysis working together
