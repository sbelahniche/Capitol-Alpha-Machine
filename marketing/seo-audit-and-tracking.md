# SEO Audit + Traffic Tracking — capitolalpha.app

_Audited 2026-06-26._

## Audit scores (brutal, 1–10)

| Area | Score | Notes |
|---|---|---|
| Technical SEO | **9** | Canonical, robots, sitemap.xml + .txt, RSS, theme-color, viewport, valid hreflang-free single-locale. Clean. |
| Structured data (GEO/AEO) | **9** | Full JSON-LD graph: Organization, WebSite, WebApplication, Dataset, Person, ImageObject, DataDownload. Scene pages have CreativeWork + BreadcrumbList. FAQ page has FAQPage. This is excellent — exactly what AI search engines parse. |
| On-page keyword targeting | **8** (was 5) | **Fixed today:** meta description + crawler fallback copy now include the high-volume terms "congressional stock trading tracker," "Nancy Pelosi," "track Congress stock trades." Previously the site only said "data sculpture/art" — invisible to the queries that actually have search volume. |
| Indexable content depth | **7** | It's a canvas/JS app, so body text is thin by nature. The `<noscript>` + sr-only headings carry the load and are now keyword-rich. Biggest remaining lever (optional): a real text article/blog per scene. |
| Off-page / authority | **6** | New domain, few backlinks. This is what the distribution kit + post queue are for. Backlinks from a Show HN, r/dataisbeautiful OC post, and data-journalist pickups move this fastest. |

**Weakest remaining:** off-page authority (backlinks) — solved by execution of the post queue, not more code. Indexable depth is the only code lever left and it's optional given the art-first design.

## What was changed in the repo today
- `index.html` meta description rewritten to lead with high-intent keywords (truthful).
- `index.html` `<noscript>` fallback expanded into two keyword-rich, accurate paragraphs ("congressional stock trading tracker," STOCK Act, Nancy Pelosi, $2.27B / 34,800 disclosures).
- Validated with your own `scripts/validate_static_site.py` → **passed**. Visual canvas art untouched.

## Do these 3 things this week (high ROI, ~30 min)
1. **Google Search Console** — you already have the `googleaa6621ef741fc84e.html` verification file, so the property is verified. Submit `sitemap.xml` under Sitemaps, then use "URL Inspection → Request indexing" on the homepage + each scene. This is the single fastest way to get indexed.
2. **Bing Webmaster Tools** — import from GSC in two clicks. Bing also feeds ChatGPT search.
3. **One backlink** — post the Show HN (in the queue). A front-page-adjacent HN post alone can get you indexed and linked within a day.

## UTM tracking scheme (already baked into the post queue)
Pattern: `?utm_source=<platform>&utm_medium=social&utm_campaign=<theme>`
- `utm_source`: twitter | reddit | hn | bluesky | linkedin
- `utm_medium`: social (or `referral` for forum links)
- `utm_campaign`: launch, committee, timing, showhn, etc.

You have Vercel Web Analytics installed (`/_vercel/insights/script.js`) — UTM'd referrers will show up there under referrers/campaigns. Check weekly: which `utm_source` converts, double down there.

## How to measure "is it working"
- **Week 1–2:** GSC "Pages" indexed count goes up; Vercel Analytics shows referral spikes on post-days.
- **Week 3–4:** GSC "Performance" → impressions for "congressional trading tracker" / "pelosi stock" queries start appearing.
- **Leading indicator:** any post that gets >20 upvotes or HN front page = a backlink = compounding SEO.
