# Example Queries

## Example 1

User request:

"Analyze this strategy time series."

Expected behavior:

- inspect object type
- identify the date axis
- classify the main series as returns, NAV, price, or PnL
- produce a report with explicit caveats

## Example 2

User request:

"Generate a performance report from this DataFrame."

Expected behavior:

- rank candidate columns instead of assuming the first numeric column is correct
- explain why one column was selected
- compute only metrics valid for that series type

## Example 3

User request:

"Figure out which column is the strategy and compute Sharpe and drawdown."

Expected behavior:

- search for return-like or NAV-like columns
- if the selected column is NAV, derive returns before Sharpe
- if the selected column is PnL, explain that Sharpe is not valid without a capital base

## Example 4

User request:

"Compare the two candidate return columns."

Expected behavior:

- keep both columns
- compute comparable return metrics
- explain differences in missing values, sample coverage, and volatility

## Example 5

User request:

"This DataFrame has `value`, `portfolio`, and `pnl`. Tell me what to analyze."

Expected behavior:

- rank the candidates
- explain which one is most likely the investable performance series
- present a fallback ranking if certainty is low
