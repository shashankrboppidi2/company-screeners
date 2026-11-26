# company-screeners

## High growth, cheap on sales, ranked by operating margin

`screen_growth_value.py` screens global public companies (primary listings, values in USD) for:

- market cap > USD 5M
- revenue (TTM) / market cap > 0.7
- expected YoY revenue growth > 25% — analyst consensus revenue for the current, not yet
  reported fiscal year vs. the last reported fiscal year

and ranks the survivors by TTM operating margin, best first.

    python3 screen_growth_value.py results.csv

Data comes from the TradingView global screener. Companies with no analyst revenue estimate
cannot be tested for expected growth and are left out. `results.csv` holds the run of 2026-11-26.
