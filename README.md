# Edge Scanner — data pipeline

Nightly GitHub Action that fetches fundamentals and options data for all US
stocks ≥ $250M market cap and commits it to `data/`. This feeds the Edge
Scanner stock-analysis system.

## Setup (one time, ~2 minutes)

1. Create a new **public** repo on your GitHub account named `edge-scanner-data`
2. Upload everything in this folder to it (drag-and-drop works on github.com:
   "uploading an existing file" link — include the `.github` folder*, `scripts`
   folder, `requirements.txt`, and this README)
3. Go to the repo's **Actions** tab → enable workflows if prompted →
   open **"Nightly data fetch"** → **Run workflow** to do the first fetch
   (takes ~1-2 hours; after that it runs automatically every night after
   the US close)

*If the drag-and-drop won't take the `.github` folder, create the file
`.github/workflows/fetch.yml` manually with "Add file → Create new file" and
paste the contents in.

## Outputs

- `data/fundamentals.parquet` — valuation, quality, growth fields per symbol
- `data/options.parquet` — 30d ATM implied vol, put/call OI ratio for the
  600 most liquid names
- `data/history/` — weekly point-in-time archives, which accumulate into a
  bias-free fundamentals history for backtesting

## Notes

- Free GitHub Actions minutes are unlimited for public repos
- Data source: Yahoo Finance via yfinance; universe from
  [rreichel3/US-Stock-Symbols](https://github.com/rreichel3/US-Stock-Symbols)
- For personal research use
