"""Fetch options metrics for the ~600 most liquid US stocks.

For each name: 30-45d at-the-money implied volatility, put/call open
interest ratio, and total option volume. Output: data/options.parquet.
"""
import json, os, time, datetime
import urllib.request
import numpy as np
import pandas as pd
import yfinance as yf

UNIVERSE_URL = ("https://raw.githubusercontent.com/rreichel3/"
                "US-Stock-Symbols/main/{ex}/{ex}_full_tickers.json")
TOP_N = 600


def liquid_universe():
    rows_all = []
    for ex in ["nasdaq", "nyse", "amex"]:
        with urllib.request.urlopen(UNIVERSE_URL.format(ex=ex), timeout=60) as r:
            rows_all += json.load(r)
    recs = []
    for x in rows_all:
        s = (x.get("symbol") or "").strip()
        try:
            price = float((x.get("lastsale") or "0").replace("$", "").replace(",", ""))
            vol = float(x.get("volume") or 0)
            mc = float(x.get("marketCap") or 0)
        except ValueError:
            continue
        if s and "^" not in s and "/" not in s and mc > 1e9:
            recs.append((s, price * vol))
    recs.sort(key=lambda t: -t[1])
    return [s for s, _ in recs[:TOP_N]]


def atm_iv(tk, spot):
    """IV of the expiry closest to 37 days, averaged over the 4 strikes
    nearest the money (calls and puts)."""
    target = datetime.date.today() + datetime.timedelta(days=37)
    exps = tk.options
    if not exps:
        return np.nan, np.nan, 0
    exp = min(exps, key=lambda e: abs(
        (datetime.date.fromisoformat(e) - target).days))
    ch = tk.option_chain(exp)
    ivs, pc_oi, tot_vol = [], np.nan, 0
    for side in (ch.calls, ch.puts):
        side = side.dropna(subset=["impliedVolatility"])
        near = side.iloc[(side["strike"] - spot).abs().argsort()[:4]]
        ivs += list(near["impliedVolatility"])
        tot_vol += int(side["volume"].fillna(0).sum())
    call_oi = ch.calls["openInterest"].fillna(0).sum()
    put_oi = ch.puts["openInterest"].fillna(0).sum()
    if call_oi > 0:
        pc_oi = put_oi / call_oi
    return (float(np.median(ivs)) if ivs else np.nan), pc_oi, tot_vol


def main():
    syms = liquid_universe()
    print(f"{len(syms)} liquid names")
    out, failed = [], 0
    for i, s in enumerate(syms):
        try:
            tk = yf.Ticker(s)
            spot = tk.fast_info["lastPrice"]
            iv, pc, vol = atm_iv(tk, spot)
            out.append({"symbol": s, "atm_iv_30d": iv, "put_call_oi": pc,
                        "opt_volume": vol})
        except Exception:
            failed += 1
        time.sleep(0.25)
        if i % 100 == 99:
            print(f"  {i+1}/{len(syms)} ok={len(out)} fail={failed}")
    df = pd.DataFrame(out)
    df["asof"] = datetime.date.today().isoformat()
    os.makedirs("data", exist_ok=True)
    df.to_parquet("data/options.parquet", index=False)
    print(f"wrote data/options.parquet: {len(df)} rows")


if __name__ == "__main__":
    main()
