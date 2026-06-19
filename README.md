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
- `prototypes/` - useful standalone scene source snapshots.

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

GitHub Actions runs a weekly refresh with `.github/workflows/refresh-data-and-seo.yml`.
It rebuilds `capitoltrades_data.js`, regenerates the crawlable SEO pages, validates the
static output, and commits generated changes. Vercel will auto-deploy that commit when
the GitHub repo is connected to the Vercel project.

Run the same pipeline locally with:

```bash
python3 scripts/refresh_data_and_seo.py
python3 scripts/validate_static_site.py
```
