I need you to generate synthetic option data. including synthetic underlying. Make sure at mid price, there is no arbitrage opportunity,

The data should be in csv format, once read into python program using pandas, i would like it to have no index, but columns of:
[date, option_name, bid, ask, mid, expiration, strike, underlying, moneyness, implied volatility, delta]

The option name should be reflecting the expiration and strike.

I want to have a 20-days long time series, with options in certain range everyday:
expiration is from 1 business day to 10 business days;
moneyness from 80% to 120%;
you should decide the right granularity of the option strikes;

underlying initial level is 1000, suppose move at drifted brownian motion, with 5% annual upside drift and 10% annualized volatility.

You cannot just generate random numbers, but you need to have a program generate scientific results and guarantee no arbitrage.

all data should be stored in a folder data/, parallel to documents and src/

---

for tests: you need to add test cases testing the arbitrage condition of the options based on mid price

for examples: you need to have a python script running and loading the data.

