---
name: mpl-standard-plot
description: Produce matplotlib charts that follow a repository house .mplstyle file, using deterministic chart recipes and minimal style overrides for research workflows.
---

# Purpose

Use this skill to generate matplotlib charts that respect a repository house style instead of ad hoc styling. The skill tells the agent how to find a `.mplstyle` file, apply it consistently, and make chart-specific decisions without drifting away from the style contract.

# When to use

Use this skill for requests such as:

- "Plot cumulative returns for these three strategies using house style."
- "Make a drawdown chart for this series."
- "Scatter factor return vs market return with regression line but keep house style."
- "Compare rolling 63d vol for these columns."

Do not use it when:

- the repo already has a plotting helper that fully encapsulates style behavior and the user wants that helper used
- the task is a non-matplotlib visualization stack unless the repo explicitly bridges it back to matplotlib

# Inputs expected

- A pandas `Series` or `DataFrame`
- A repository `.mplstyle` file, or a clear repo convention for where it lives
- Optional chart intent:
  - chart type
  - title or subtitle
  - output path
  - axis labels
  - log scale
  - benchmark or comparison series

# Outputs expected

- A matplotlib figure saved or shown using the house style
- Clear code or notebook cells that load the style explicitly
- Sensible chart-specific formatting that does not fight the style file

# Step-by-step workflow

1. Locate the house `.mplstyle`.
   Check repo-default paths first, such as:
   - `styles/house.mplstyle`
   - `plotting/house.mplstyle`
   - `config/house.mplstyle`
   - repo root for `*.mplstyle`

2. If no default path exists, search the repo for `*.mplstyle`.
   If multiple candidates exist, prefer one named `house`, `default`, or the one already imported by repo code. If none exist, fail clearly instead of inventing a style.

3. Load the style explicitly near plot creation.

```python
from pathlib import Path

import matplotlib.pyplot as plt

STYLE_PATH = Path("styles/house.mplstyle")
plt.style.use(STYLE_PATH)
```

4. Inspect the data before plotting.
   Confirm datetime handling, missing values, and whether the series are in level or return space. Do not choose a cumulative return chart on raw prices unless that transformation is intentional.

5. Choose a chart recipe.
   Use the recipe that matches the analytical question. Prefer the simplest chart that answers the question.

6. Apply chart-specific settings only where the style file should not decide.
   Typical explicit settings:
   - figure size
   - title
   - subtitle via `fig.text` when needed
   - axis labels
   - legend location
   - date locator and formatter
   - percentage formatter
   - log scale
   - save path and export parameters

7. Avoid unnecessary overrides.
   Do not set colors, fonts, line widths, or grid choices in code unless the chart is unreadable under the house style.

8. Save or display the figure.
   When saving, use `bbox_inches="tight"` and state the file path.

# Guardrails

- Do not call seaborn or another style system on top of the `.mplstyle` unless the repo already does that deliberately.
- Do not set random custom colors because the chart "looks nicer."
- Do not manually restyle every axis element that the `.mplstyle` should control.
- Do not hide missing data by silently interpolating lines.
- Do not use twin axes unless the analytical question truly requires it.
- Do not fail open when the repo has no `.mplstyle`; report that the style contract cannot be satisfied.

# Acceptance criteria

- The chart uses the repository `.mplstyle`.
- Chart-specific decisions are explicit and limited.
- Common research chart types can be produced without ad hoc styling.
- The output is consistent across notebooks and scripts.

# Examples of good agent behavior

- "I found `styles/house.mplstyle` and applied it with `plt.style.use(...)` before creating the figure."
- "This is a cumulative return chart, so I first converted returns into a wealth index and then plotted the cumulative path."
- "I kept the style file in control of colors and fonts. The only explicit overrides are figure size, title, legend placement, and percentage formatting."
- "The repo has no `.mplstyle` file, so I stopped instead of inventing a visual style that would drift from house standards."

# Reference files

Read these only when needed:

- [`references/style-contract.md`](references/style-contract.md) for the style division of labor
- [`references/chart-recipes.md`](references/chart-recipes.md) for common research plot patterns
- [`references/example-queries.md`](references/example-queries.md) for prompt-to-chart mappings
- [`references/mpl_standard_plot_template.py`](references/mpl_standard_plot_template.py) for a minimal house-style plotting template
