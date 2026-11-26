# company-screeners

## High growth, cheap on sales, ranked by operating margin

`screen_growth_value.py` screens global public companies (primary listings, values in USD) for:

- market cap > USD 5M
- revenue (TTM) / market cap > 0.7
- expected YoY revenue growth > 25% — analyst consensus revenue for the current, not yet
  reported fiscal year vs. the last reported fiscal year

and ranks the survivors by TTM operating margin, best first.

    python3 screen_growth_value.py results.csv                              # global, primary listings
    python3 screen_growth_value.py results_us_canada.csv --north-america    # US and Canadian exchanges only

The US/Canada run covers NYSE, NASDAQ, NYSE American, Cboe, TSX, TSXV, CSE and Cboe Canada,
including foreign companies' ADRs; OTC-traded names are not counted as listed.

Data comes from the TradingView global screener. Companies with no analyst revenue estimate
cannot be tested for expected growth and are left out. The CSVs hold the runs of 2026-11-26.
