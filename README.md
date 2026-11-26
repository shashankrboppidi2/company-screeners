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

## Forward-looking variant (US and Canadian listings)

`screen_forward.py` keeps the size and revenue / market cap tests but looks ahead:

- forward growth > 25% — consensus revenue for the next two unreported quarters vs. the same
  two quarters a year earlier
- ranked by forward net margin — consensus EPS x shares / consensus revenue over those quarters

The data source has no consensus operating profit, so the forward margin is a net margin
(usually on adjusted earnings). Output: `results_us_canada_forward.csv`.
