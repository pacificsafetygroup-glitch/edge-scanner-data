"""Fetch fundamentals for all US-listed stocks >= $250M market cap.

Universe comes from the daily-updated rreichel3/US-Stock-Symbols repo.
Output: data/fundamentals.parquet — one row per symbol with valuation,
quality, and growth fields, stamped with the fetch date (point-in-time
records accumulate in data/history/ for future backtesting).
"""
import io, json, os, time, datetime
import urllib.request
import pandas as pd
import numpy as np
import yfinance as yf

UNIVERSE_URL = ("https://raw.githubusercontent.com/rreichel3/"
                "US-Stock-Symbols/main/{ex}/{ex}_full_tickers.json")
MIN_MCAP = 250e6

FIELDS = [
    # valuation
    "trailingPE", "forwardPE", "priceToBook", "enterpriseToEbitda",
    "enterpriseToRevenue", "priceToSalesTrailing12Months", "trailingPegRatio",
    "freeCashflow", "enterpriseValue", "marketCap", "dividendYield",
    # quality
    "returnOnEquity", "returnOnAssets", "grossMargins", "operatingMargins",
    "profitMargins", "debtToEquity", "currentRatio", "totalCash", "totalDebt",
    # growth
    "revenueGrowth", "earningsGrowth", "earningsQuarterlyGrowth",
    # misc
    "beta", "shortPercentOfFloat", "heldPercentInsiders", "sector",
]


def universe():
    syms = []
    for ex in ["nasdaq", "nyse", "amex"]:
        with urllib.request.urlopen(UNIVERSE_URL.format(ex=ex), timeout=60) as r:
            rows = json.load(r)
        for x in rows:
            s = (x.get("symbol") or "").strip()
            try:
                mc = float(x.get("marketCap") or 0)
            except ValueError:
                continue
            if s and "^" not in s and "/" not in s and mc >= MIN_MCAP:
                syms.append(s)
    return sorted(set(syms))


def main():
    syms = universe()
    print(f"{len(syms)} symbols >= ${MIN_MCAP/1e6:.0f}M")
    out, failed = [], 0
    t0 = time.time()
    for i, s in enumerate(syms):
        try:
            info = yf.Ticker(s).info
            row = {"symbol": s}
            for f in FIELDS:
                row[f] = info.get(f)
            out.append(row)
        except Exception:
            failed += 1
            time.sleep(1.0)
        if i % 25 == 24:
            time.sleep(0.5)          # be polite
        if i % 250 == 249:
            el = time.time() - t0
            print(f"  {i+1}/{len(syms)}  ok={len(out)} fail={failed} "
                  f"({el/60:.1f} min)")
    df = pd.DataFrame(out)
    # Yahoo sometimes returns strings like 'Infinity' in numeric fields;
    # coerce everything numeric and drop infinities so parquet can save.
    for c in df.columns:
        if c not in ("symbol", "sector"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.replace([np.inf, -np.inf], np.nan)
    df["sector"] = df["sector"].astype(str)
    today = datetime.date.today().isoformat()
    df["asof"] = today
    os.makedirs("data/history", exist_ok=True)
    df.to_parquet("data/fundamentals.parquet", index=False)
    # keep a point-in-time weekly archive (Mondays) for future backtests
    if datetime.date.today().weekday() == 0:
        df.to_parquet(f"data/history/fundamentals_{today}.parquet", index=False)
    print(f"wrote data/fundamentals.parquet: {len(df)} rows, {failed} failures")


if __name__ == "__main__":
    main()
