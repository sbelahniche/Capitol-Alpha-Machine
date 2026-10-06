# Capitol Alpha Machine

An ominous visualization of political trading signals, sourced from CapitolTrades.com.

## Live Project

- Production URL: https://capitolalpha.app/
- Vercel preview URL: https://capitol-alpha-machine.vercel.app/ (redirects to the custom domain)
- Vercel project: `capitol-trades-data-visualization`
- GitHub repo: `sbelahniche/Capitol-Alpha-Machine`

## Files

- `index.html` - the complete five-scene static visualization.
- `capitoltrades_data.js` - current bundled data used by the visualization.
- `favicon-ct.png` - project favicon.
- `scripts/` - scraper and committee-risk dataset builders.
- `data/scene05_real_payload.json` - real congressional bill/event payload used while wiring scene 5.
- `prototypes/scene03_exposure_index.html` - generated Scene 03 source snapshot used by the embedding and validation pipeline.

## Local Preview

Because this is a static project, you can preview it with any simple local server:

```bash
python3 -m http.server 8765
```

Then open:

```text
http://127.0.0.1:8765/
```

## Vercel

Vercel can deploy this repo directly from the root. The Analytics loader is already included in `index.html` and loads on Vercel from:

```text
/_vercel/insights/script.js
```

Do not commit `.vercel/` or `.env.local`; those are local machine/project-link files.

## Data and SEO Refresh

A macOS LaunchAgent runs the weekly refresh from a dedicated clean clone. It
checks every hour at minute 25, starts after Monday 08:20 UTC, and retries until
the current Monday's report is live. The normal run refreshes recent trade data
and SEO pages without rebuilding Scene 03, validates the site, pushes `main`,
waits for the linked Vercel Git deployment, and verifies the live report.

Install or update the unattended job with:

```bash
./scripts/install_weekly_refresh_launchd.sh
```

GitHub Actions independently waits for the Monday publication and reports a
failure if the live report remains stale. It does not scrape Capitol Trades,
because GitHub-hosted runner IPs are rate-limited by the source.

Run the same pipeline locally with:

```bash
python3 scripts/refresh_data_and_seo.py
python3 scripts/validate_static_site.py
```
