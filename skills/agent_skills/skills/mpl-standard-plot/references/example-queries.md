# Example Queries

## Example 1

User request:

"Plot cumulative returns for these three strategies using house style."

Expected behavior:

- locate `.mplstyle`
- confirm the input represents returns
- compound into a wealth index
- create a multi-line chart
- format the y-axis as growth of 1 or percentage, depending on repo convention

## Example 2

User request:

"Make a drawdown chart for this series."

Expected behavior:

- determine whether the series is already wealth-like or needs a return-to-wealth transform
- compute running peak and drawdown
- keep style-driven colors unless one explicit color is already standard in repo code

## Example 3

User request:

"Scatter factor return vs market return with regression line but keep house style."

Expected behavior:

- align the two return series on common dates
- create a scatter plot
- add a simple regression line
- keep marker styling minimal and avoid overriding the palette unless needed for contrast

## Example 4

User request:

"Compare rolling 63d vol for these columns."

Expected behavior:

- confirm the inputs are returns
- compute 63-day rolling annualized volatility
- use percentage formatting on the y-axis
- title the chart with the window length if the user did not provide a title

## Example 5

User request:

"Use house style for this notebook chart."

Expected behavior:

- find the `.mplstyle`
- add explicit style loading in the notebook cell or helper import
- do not rely on notebook state from earlier cells
