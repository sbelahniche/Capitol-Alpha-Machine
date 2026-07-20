# Capitol Trades refresh

Capitol Trades currently exposes two useful public browser surfaces:

- `https://www.capitoltrades.com/trades?page=1&sort=-pubDate`
  renders structured trade objects inside the page's React payload.
- `https://bff.capitoltrades.com/issuers?search=apple`
  returns JSON directly and allows cross-origin browser requests.

The direct `https://bff.capitoltrades.com/trades` route is not a public JSON API.
Unauthenticated requests currently return a CloudFront error. The scraper uses
ordinary `/trades` pages and does not request the `/_next/data/*` routes
disallowed by the site's `robots.txt`.

Fetch the latest 120 trades:

```sh
./scripts/capitoltrades_scrape.py \
  --output data/capitoltrades_recent.json \
  trades --pages 10 --delay 1
```

Fetch the full public rendered trade history currently exposed by the site, and
use it to generate Scene 01's weekly signed net capital-flow payload:

```sh
./scripts/capitoltrades_scrape.py \
  --output data/capitoltrades_historical.json \
  trades --pages 348 --delay 0.05 --progress --param pageSize=100

./scripts/capitoltrades_scrape.py \
  --output ~/Desktop/capitoltrades_scene01.js \
  --js-variable CAPITOL_TRADES_SCENE01 \
  trades --pages 348 --delay 0.05 --scene01-js --param pageSize=100
```

Generate the separate JavaScript data file used by the desktop HTML prototype:

```sh
./scripts/capitoltrades_scrape.py \
  --output ~/Desktop/capitoltrades_data.js \
  trades --pages 150 --delay 0.5 --prototype-js --price-delay 0.08 \
  --require-priced-trades 500 --require-priced-members 50 --progress
```

Keep `capitoltrades_data.js` beside
`index_scene5_no_pointer_no_top_event_box.html`. Scene 01 reads weekly signed
net capital flow from this sidecar, with buys positive and sells negative.
Scene 02 reads current trade records from this sidecar. Scene 04 reads current Capitol Trades issuer
trailing-90-day EOD performance and a real SPY trailing-90-day baseline. Its
brightness score is derived from those real values.

Refresh the production sidecar and generated SEO pages in one pass:

```sh
./scripts/refresh_data_and_seo.py
```

This fetches the historical public trade pages with a polite delay, rebuilds
Scene 01, a controlled recent Scene 02 window, the Scene 03 committee-risk
exposure payload, and Scene 04's priced returns payload. It preserves the
current Scene 05 event/trade payload, writes `capitoltrades_data.js`, updates
the embedded Scene 03 prototype, and runs `scripts/generate_seo.py`.

When GitHub-hosted runners are rate-limited by Capitol Trades, run the local
publisher from this Mac instead. It fetches the newest rendered trade pages,
merges them into the local historical cache, rebuilds the public bundle and SEO
pages, validates the site, refreshes the compressed historical seed, and can
commit/push the generated outputs:

```sh
./scripts/publish_latest_data.py --publish
```

For a normal weekly update, leave Scene 03 off; the command above preserves the
existing committee-risk payload. Use the heavier option only when the Scene 3
committee-risk dataset itself needs to be rebuilt:

```sh
./scripts/publish_latest_data.py --refresh-scene03 --publish
```

The production weekly schedule uses a macOS LaunchAgent and a separate managed
clone, so local branches and uncommitted work do not block publication. Install
or refresh it once with:

```sh
./scripts/install_weekly_refresh_launchd.sh
```

The job wakes every hour at minute 25. It exits immediately before Monday 08:20
UTC or when the current Monday is already live. Otherwise it updates ten recent
pages sequentially, preserves Scene 03, commits and pushes generated data/SEO
changes, deploys production, and verifies the live report. A failed source,
push, or deployment attempt is retried at the next `:25` run. Logs are written
to `~/Library/Logs/CapitolAlphaWeeklyRefresh.log` and the matching `.error.log`.

GitHub Actions now monitors the live Monday report instead of scraping from a
rate-limited hosted runner.

Apply site filters:

```sh
./scripts/capitoltrades_scrape.py \
  trades --pages 3 --sort=-txDate --param txType=buy
```

Search issuer metadata:

```sh
./scripts/capitoltrades_scrape.py issuer-search apple
```

Build the two-year committee/trade risk dataset. This joins the rendered trade
payload to committee membership scraped from `politicians?committee=...`, then
scores each committee/trade relationship with transparent research flags such as
committee-sector overlap, high disclosed value, late reporting gaps, and repeat
committee-sector trading in a 90-day window. The score is a triage heuristic,
not an allegation of unlawful conduct.

```sh
./scripts/capitoltrades_committee_risk.py \
  --input data/capitoltrades_historical.json \
  --output data/capitoltrades_committee_risk_2y.json \
  --csv-output data/capitoltrades_committee_risk_2y.csv \
  --all-csv-output data/capitoltrades_committee_relationships_2y.csv \
  --end-date 2026-06-04 --progress
```

Convert that dataset into the compact Scene 03 payload and embed it in the
homepage:

```sh
./scripts/generate_scene03.py
```

Add `--refresh-trades` to scrape the trade pages again before building the
dataset:

```sh
./scripts/capitoltrades_committee_risk.py \
  --refresh-trades --trade-pages 348 --trade-delay 0.05 \
  --output data/capitoltrades_committee_risk_2y.json \
  --csv-output data/capitoltrades_committee_risk_2y.csv \
  --progress
```

The rendered trade page currently returns 12 records per page by default and
honors `pageSize=100` for larger historical refreshes. Keep the delays when
refreshing multiple pages. The minimum-count options make the larger prototype
refresh fail clearly if the selected page range is too small.
