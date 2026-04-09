# Style Contract

The `.mplstyle` file should own stable visual identity. Plot code should own analytical meaning.

## The style file should control

- font family and default text sizes
- color cycle
- line widths and marker defaults
- axes face and edge colors
- grid visibility and default styling
- legend frame defaults
- figure DPI and save DPI, if the repo standardizes them

## Plot code should control

- figure size
- chart type
- title and subtitle text
- axis labels
- axis scale, such as log scale
- date locators and formatters
- percent, currency, or numeric tick formatting
- legend inclusion and location
- annotation of events, regressions, or thresholds
- save path and file format

## Allowed overrides

Override style defaults only when one of these conditions is true:

- the chart is unreadable under the default color cycle because too many series are present
- a twin axis is analytically necessary
- the style was designed for a light background and the export target requires a dark one, or the reverse
- publication export requires a specific size, DPI, or monochrome treatment

When overriding, keep the override local to the chart code and state why.

## Style discovery order

Use this deterministic search order:

1. repo-configured path already used in code
2. `styles/house.mplstyle`
3. `plotting/house.mplstyle`
4. `config/house.mplstyle`
5. any `*.mplstyle` in repo root
6. repo-wide search for `*.mplstyle`

If multiple files remain plausible, prefer the one named `house` or the one referenced by existing plotting modules.

## Avoiding style drift

- Always call `plt.style.use(style_path)` in scripts, even if a notebook already loaded the style earlier.
- In notebooks, place style loading in the first plotting cell or a dedicated setup cell.
- Do not copy style constants into notebook code.
- If the repo already has a helper like `configure_plots()`, reuse it instead of reimplementing style loading.
