#!/usr/bin/env python3
"""Forward-looking version of the growth screen, US and Canadian listings.

Criteria
  * market cap > USD 5M
  * revenue (TTM) / market cap > 0.7
  * forward revenue growth > 25%
      = analyst consensus revenue for the next two unreported quarters
        vs. the same two quarters a year earlier
Ranking
  * forward net margin, best first
      = consensus EPS x shares / consensus revenue, same two quarters

The data source carries consensus revenue and EPS only, so there is no
consensus operating profit: the forward margin is a net (usually adjusted)
margin. TTM operating margin is kept alongside for reference.
"""
import csv
import json
import sys
import time
import urllib.request

from screen_growth_value import (MAX_SANE_MARGIN, MIN_GROWTH, MIN_MCAP,
                                 MIN_REV_TO_MCAP, NA_EXCHANGES, PAGE, URL)

COLUMNS = [
    "name", "description", "exchange", "country", "sector", "industry", "is_primary",
    "currency", "close", "market_cap_basic", "total_shares_outstanding",
    "total_revenue_ttm", "total_revenue_fq", "total_revenue_fq_h",
    "revenue_forecast_next_fq", "revenue_forecast_next_fh",
    "earnings_per_share_forecast_next_fh",
    "operating_margin_ttm", "net_margin_ttm", "fiscal_period_current",
]


def fetch():
    rows, start = [], 0
    while True:
        body = {
            "columns": COLUMNS,
            "filter": [
                {"left": "exchange", "operation": "in_range", "right": NA_EXCHANGES},
                {"left": "type", "operation": "in_range", "right": ["stock", "dr"]},
                {"left": "market_cap_basic", "operation": "greater", "right": MIN_MCAP},
                {"left": "revenue_forecast_next_fh", "operation": "nempty"},
            ],
            "sort": {"sortBy": "market_cap_basic", "sortOrder": "desc"},
            "range": [start, start + PAGE],
        }
        req = urllib.request.Request(
            URL, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
        for attempt in range(4):
            try:
                data = json.load(urllib.request.urlopen(req, timeout=120))
                break
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(2 ** (attempt + 1))
        batch = data.get("data") or []
        rows += [dict(zip(COLUMNS, r["d"]), symbol=r["s"]) for r in batch]
        start += PAGE
        if start >= data.get("totalCount", 0) or not batch:
            return rows


def screen(rows):
    out, skipped = [], 0
    for r in rows:
        mcap, rev = r["market_cap_basic"], r["total_revenue_ttm"]
        hist, last_q = r["total_revenue_fq_h"] or [], r["total_revenue_fq"]
        fwd_rev, fwd_eps = r["revenue_forecast_next_fh"], r["earnings_per_share_forecast_next_fh"]
        if not mcap or not rev or rev / mcap <= MIN_REV_TO_MCAP:
            continue
        # Needs quarterly history: the two quarters a year before the forecast
        # window are the 3rd and 4th most recent reported quarters.
        if (len(hist) < 4 or not hist[0] or not last_q or not fwd_rev or fwd_eps is None
                or not r["next_fq"] or None in hist[:4] or hist[2] + hist[3] <= 0):
            skipped += 1
            continue
        # History is in reporting currency, forecasts in USD: convert at the
        # rate implied by the latest quarter.
        fx = last_q / hist[0]
        base = (hist[2] + hist[3]) * fx
        # The "next half" figure only means the next two quarters when it is
        # clearly more than one quarter's worth.
        if fwd_rev < 1.3 * r["next_fq"]:
            skipped += 1
            continue
        growth = (fwd_rev / base - 1) * 100
        if growth <= MIN_GROWTH:
            continue
        # US-listed lines quote in USD, so cap / price gives the count of traded
        # units (right for ADRs too); elsewhere use the share count.
        units = mcap / r["close"] if r["currency"] == "USD" and r["close"] else r["total_shares_outstanding"]
        if not units:
            skipped += 1
            continue
        margin = fwd_eps * units / fwd_rev * 100
        if abs(margin) > MAX_SANE_MARGIN:
            skipped += 1
            continue
        out.append({
            "symbol": r["symbol"],
            "primary_listing": bool(r["is_primary"]),
            "company": r["description"],
            "country": r["country"],
            "sector": r["sector"],
            "industry": r["industry"],
            "market_cap_usd_m": round(mcap / 1e6, 1),
            "revenue_ttm_usd_m": round(rev / 1e6, 1),
            "revenue_to_mcap": round(rev / mcap, 2),
            "next_2q_revenue_est_usd_m": round(fwd_rev / 1e6, 1),
            "same_2q_year_ago_usd_m": round(base / 1e6, 1),
            "forward_growth_pct": round(growth, 1),
            "forward_net_margin_pct": round(margin, 2),
            "net_margin_ttm_pct": round(r["net_margin_ttm"], 2) if r["net_margin_ttm"] is not None else "",
            "operating_margin_ttm_pct": (round(r["operating_margin_ttm"], 2)
                                         if r["operating_margin_ttm"] is not None else ""),
            "last_reported_period": r["fiscal_period_current"] or "",
        })
    # One row per company: prefer the primary listing, then an ADR over a
    # Canadian depositary receipt, then the larger line.
    out.sort(key=lambda x: (x["primary_listing"], not x["symbol"].startswith("NEO:"),
                            x["market_cap_usd_m"]), reverse=True)
    seen, dedup = set(), []
    for r in out:
        # Lines of the same company share its trailing margins.
        key = (r["country"], r["industry"], r["net_margin_ttm_pct"], r["operating_margin_ttm_pct"])
        if key not in seen:
            seen.add(key)
            dedup.append(r)
    dedup.sort(key=lambda x: x["forward_net_margin_pct"], reverse=True)
    for i, r in enumerate(dedup, 1):
        r["rank"] = i
    return dedup, skipped


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else "results_us_canada_forward.csv"
    rows = fetch()
    for r in rows:
        r["next_fq"] = r["revenue_forecast_next_fq"]
    res, skipped = screen(rows)
    print(f"{len(rows)} listings with forward estimates; {skipped} cheap-on-sales names skipped for missing or unusable data")
    fields = ["rank"] + [k for k in res[0] if k != "rank"]
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(res)
    print(f"{len(res)} companies pass -> {out_path}")


if __name__ == "__main__":
    main()
