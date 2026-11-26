#!/usr/bin/env python3
"""Screen global public companies for cheap-on-sales, fast-growing names.

Criteria
  * market cap > USD 5M
  * revenue (TTM) / market cap > 0.7
  * expected YoY revenue growth > 25%
      = analyst consensus revenue for the current (not yet reported) fiscal year
        vs. revenue of the last reported fiscal year
Ranking
  * operating margin (TTM), best first

Data: TradingView global screener (all values converted to USD). Each company
appears once.

Usage
  screen_growth_value.py [out.csv]               global, primary listings
  screen_growth_value.py out.csv --north-america  anything listed on a US or
      Canadian exchange (NYSE, NASDAQ, NYSE American, Cboe, TSX, TSXV, CSE,
      Cboe Canada), including foreign companies' ADRs; OTC is not a listing
"""
import csv
import datetime as dt
import json
import sys
import time
import urllib.request

URL = "https://scanner.tradingview.com/global/scan"
MIN_MCAP = 5e6
MIN_REV_TO_MCAP = 0.7
MIN_GROWTH = 25.0
MAX_SANE_MARGIN = 100.0
PAGE = 5000
NA_EXCHANGES = ["NYSE", "NASDAQ", "AMEX", "CBOE", "TSX", "TSXV", "CSE", "NEO"]

COLUMNS = [
    "name", "description", "exchange", "country", "sector", "industry",
    "type", "market_cap_basic", "total_revenue_ttm", "total_revenue_fy",
    "revenue_forecast_next_fy", "operating_margin_ttm",
    "total_revenue_yoy_growth_ttm", "fiscal_period_end_fy", "is_primary",
]


def fetch_universe(exchanges=None):
    scope = ({"left": "exchange", "operation": "in_range", "right": exchanges} if exchanges
             else {"left": "is_primary", "operation": "equal", "right": True})
    rows, start = [], 0
    while True:
        body = {
            "columns": COLUMNS,
            "filter": [
                scope,
                {"left": "type", "operation": "in_range", "right": ["stock", "dr"]},
                {"left": "market_cap_basic", "operation": "greater", "right": MIN_MCAP},
                {"left": "revenue_forecast_next_fy", "operation": "nempty"},
            ],
            "sort": {"sortBy": "market_cap_basic", "sortOrder": "desc"},
            "range": [start, start + PAGE],
        }
        req = urllib.request.Request(
            URL, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
        for attempt in range(4):
            try:
                data = json.load(urllib.request.urlopen(req, timeout=60))
                break
            except Exception as exc:  # network hiccup: back off and retry
                if attempt == 3:
                    raise
                time.sleep(2 ** (attempt + 1))
        batch = data.get("data") or []
        rows += [dict(zip(COLUMNS, r["d"]), symbol=r["s"]) for r in batch]
        start += PAGE
        if start >= data.get("totalCount", 0) or not batch:
            return rows, data.get("totalCount", 0)


def screen(rows, margin_digits=2):
    out = []
    for r in rows:
        mcap, rev = r["market_cap_basic"], r["total_revenue_ttm"]
        base, fwd = r["total_revenue_fy"], r["revenue_forecast_next_fy"]
        margin = r["operating_margin_ttm"]
        if not mcap or not rev or not base or not fwd or base <= 0 or margin is None:
            continue
        ratio = rev / mcap
        growth = (fwd / base - 1) * 100
        if mcap > MIN_MCAP and ratio > MIN_REV_TO_MCAP and growth > MIN_GROWTH:
            fy_end = r["fiscal_period_end_fy"]
            out.append({
                "symbol": r["symbol"],
                "primary_listing": bool(r["is_primary"]),
                "company": r["description"],
                "country": r["country"],
                "sector": r["sector"],
                "industry": r["industry"],
                "market_cap_usd_m": round(mcap / 1e6, 1),
                "revenue_ttm_usd_m": round(rev / 1e6, 1),
                "revenue_to_mcap": round(ratio, 2),
                "last_fy_revenue_usd_m": round(base / 1e6, 1),
                "fwd_fy_revenue_est_usd_m": round(fwd / 1e6, 1),
                "expected_growth_pct": round(growth, 1),
                "ttm_actual_growth_pct": (round(r["total_revenue_yoy_growth_ttm"], 1)
                                          if r["total_revenue_yoy_growth_ttm"] is not None else ""),
                "operating_margin_ttm_pct": round(margin, 2),
                "last_fy_end": (dt.datetime.fromtimestamp(fy_end, dt.timezone.utc).date().isoformat()
                                if fy_end else ""),
            })
    # Operating margins above 100% are accounting artifacts (e.g. fair-value
    # gains booked above the operating line), not real profitability.
    out = [r for r in out if r["operating_margin_ttm_pct"] <= MAX_SANE_MARGIN]
    # One company can have several listings (share classes, ADRs, home shares
    # plus a foreign certificate); they share country, industry and margin.
    # Keep the primary listing where there is one, and an ADR ahead of a
    # Canadian depositary receipt (Cboe Canada, "NEO").
    out.sort(key=lambda x: (x["primary_listing"], not x["symbol"].startswith("NEO:"),
                            x["market_cap_usd_m"]), reverse=True)
    seen, deduped = set(), []
    for r in out:
        key = (r["country"], r["industry"], round(r["operating_margin_ttm_pct"], margin_digits), r["last_fy_end"])
        if key not in seen:
            seen.add(key)
            deduped.append(r)
    out = sorted(deduped, key=lambda x: x["operating_margin_ttm_pct"], reverse=True)
    for i, r in enumerate(out, 1):
        r["rank"] = i
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out_path = args[0] if args else "results.csv"
    north_america = "--north-america" in sys.argv
    rows, total = fetch_universe(NA_EXCHANGES if north_america else None)
    print(f"listings with analyst revenue estimates and mcap > $5M: {len(rows)} (server count {total})")
    # ADR figures drift slightly from the home listing after currency
    # conversion, so match margins more loosely when ADRs are in scope.
    res = screen(rows, margin_digits=1 if north_america else 2)
    fields = ["rank"] + [k for k in res[0] if k != "rank"]
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(res)
    print(f"{len(res)} companies pass -> {out_path}")


if __name__ == "__main__":
    main()
