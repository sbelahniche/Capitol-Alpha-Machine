# Screensavers launch plan

Promotion plan for **capitolalpha.app/screensavers**: three free Mac screensavers, framed as data sculptures and visualization experiments. Written 2026-10-06.

**Rules that keep the domain safe.** Post from your own accounts only. Lead with the moving image, put the link second, and stay in the comments for the first two hours. Reddit and Hacker News are always posted by hand. Automated or scheduled posting there gets the domain shadowbanned.

**Assets.** The loop videos are in `marketing/loops/`. Each scene has `*-16x9.mp4` for X, Bluesky, Reddit and LinkedIn, `*-1x1.mp4` for Mastodon and Instagram, and a small `*.gif` for Are.na, GitHub and emails.

---

## 1. Before launch (this week)

- [ ] **Push and deploy** the screensavers page, then check that `/screensavers` is live with the new copy.
- [ ] **Search Console.** Resubmit `sitemap.xml`, then use URL Inspection on `/screensavers` and request indexing.
- [ ] **Re-capture `screensavers/og-screensavers.png`.** It still shows the old H1 and the truncated brand name. Every share card uses this image.
- [ ] **Data freshness.** `/updates/latest` is dated 2026-10-05, but its data stops at 2026-08-14. Commenters on Hacker News will check "new data every Monday". Fix the scrape, or soften the claim before launch.
- [ ] **Notarize the screensavers if you can.** If you can't, say so up front in every post. The Gatekeeper warning is the first thing Mac commenters will bring up.
- [ ] **Show HN check.** Search [hn.algolia.com](https://hn.algolia.com/?q=capitolalpha) for `capitolalpha`. If the main site already had a Show HN, use the "alternate HN" title below.
- [ ] **Repo link.** Decide whether the GitHub repo is public. If it is, link it from the Show HN and Reddit comments, because it sharply raises trust.
- [ ] **Measure downloads.** The zips are static files, so Vercel Analytics doesn't count them. Add a `track('download', {scene})` call on the download buttons.

## 2. Two-week sequence

Times are Berlin time. Hacker News and Reddit perform best Tuesday to Thursday, 14:00–16:00 (morning on the US East Coast).

| Day | Channel | What | Asset |
|---|---|---|---|
| Tue Oct 13, 14:30 | Hacker News | Show HN (3a) | none |
| Tue Oct 13, 15:00 | X, Bluesky, Mastodon | Launch post (4a) | the-ledger 16x9 |
| Wed Oct 14 | r/generative, then r/creativecoding a day later | Video post (3b) | the-ledger 16x9 |
| Thu Oct 15 | Press | CreativeApplications.Net and It's Nice That pitch (5a), Are.na channel | all three loops |
| Fri Oct 16 | X, Bluesky, Mastodon | Returns Spectrum spotlight (4b) | returns-spectrum |
| Mon Oct 19 | r/macapps | Free app post (3c) | 16x9 grid or the-ledger |
| Tue Oct 20 | r/dataisbeautiful | [OC] video (3d) | returns-spectrum 16x9 |
| Wed Oct 21 | Press | Nightingale essay pitch (5b), Sidebar.io submission | none |
| Thu Oct 22 | X, Bluesky, Mastodon | Policy Proximity spotlight (4c) | policy-proximity |
| From Mon Oct 26 | Weekly | Gmail drafts arrive every Monday afternoon. Post 1–2 a week. | rotate loops |

On the days between posts, spend 10 minutes replying in r/creativecoding, on vis.social and in dataviz threads on Bluesky, without links.

## 3. Hacker News and Reddit (post by hand)

### 3a. Show HN
**Title:** `Show HN: Mac screensavers made from Congress's stock trades`
**Alternate title (if the site already had a Show HN):** `Show HN: Data sculptures from congressional trading disclosures, as 60 KB Mac screensavers`
**URL:** `https://capitolalpha.app/screensavers?utm_source=hn&utm_medium=social&utm_campaign=ss_launch`
**First comment:**
> I make black-and-white data sculptures from U.S. congressional stock trading disclosures (STOCK Act filings via Capitol Trades). Three of the scenes now run as native macOS screensavers: a ticker tape of Congress's own trades, a returns spectrum against SPY, and a timeline linking trades to new public laws.
>
> Each .saver is about 60 KB: a WKWebView hosting the same canvas scene as the site, with the WebKit occlusion workaround from WebViewScreenSaver. Once a week (Monday 12:00 local) it fetches the latest data bundle; offline it keeps the last set. No server, no tracking in the saver.
>
> Caveat up front: the builds are signed but not yet notarized, so Gatekeeper asks once. Happy to talk about the data pipeline, de-duplicating amended filings, or rendering in the screensaver host.

### 3b. r/generative and r/creativecoding (video post)
**Title:** `Data sculpture from 7,793 congressional stock trades, running as a Mac screensaver`
**First comment:**
> Each line is one disclosed trade: bright for purchases, dim for sales, and the bar shows the amount. Canvas 2D at 30 fps, monochrome only. The data comes from public STOCK Act disclosures via Capitol Trades. Three scenes in total, free for macOS: https://capitolalpha.app/screensavers?utm_source=reddit&utm_medium=social&utm_campaign=ss_generative

### 3c. r/macapps
Read the subreddit rules first. Use the Free flair and disclose that you're the developer.
**Title:** `[Free] Three monochrome screensavers built from real congressional stock trades`
**Body:**
> I'm the developer. Three native .saver files (universal, macOS 12+, about 60 KB each) made from public STOCK Act disclosures. They pull new data once a week and run offline on the last set. Signed but not notarized yet, so macOS asks once on install (System Settings → Privacy & Security → Open Anyway). Checksums are on the page.
> https://capitolalpha.app/screensavers?utm_source=reddit&utm_medium=social&utm_campaign=ss_macapps

### 3d. r/dataisbeautiful
**Title:** `[OC] 5,621 congressional stock trades by 58 members, plotted against 90-day excess return vs. the S&P 500`
**First comment (required for OC posts):**
> Source: STOCK Act disclosures via Capitol Trades, with daily closing prices against SPY. Tools: Python for the data, Canvas 2D for rendering. Each row is a member and each tick is a trade; taller, brighter ticks are stocks that have beaten SPY by more over the last 90 days. It's a visual heuristic, not evidence of anything. It also runs as a free Mac screensaver: https://capitolalpha.app/screensavers?utm_source=reddit&utm_medium=social&utm_campaign=ss_dib

## 4. X, Bluesky and Mastodon

These are the same text everywhere. Each one fits Bluesky's 300-character limit. Attach the loop video natively instead of relying on the link card. On Mastodon, post from vis.social or tag `#dataviz #generative #creativecoding`.

### 4a. Launch
> Data sculptures for an idle screen.
>
> Three free Mac screensavers built from 7,793 congressional stock trades. Pelosi, Tuberville, Khanna, McCaul and 95 more. Monochrome, no commentary.
>
> capitolalpha.app/screensavers?utm_source=social&utm_medium=social&utm_campaign=ss_launch

### 4b. Returns Spectrum
> Returns Spectrum. Each row is a member of Congress, each tick a disclosed trade. Taller and brighter means the stock beat the S&P 500 by more over the last 90 days.
>
> Free Mac screensaver:
> capitolalpha.app/screensavers?utm_source=social&utm_medium=social&utm_campaign=ss_returns

### 4c. Policy Proximity
> Policy Proximity. 31 public laws across the top, 372 congressional trades in sector lanes below. A reading head links each law to the nearest trades in time and sector.
>
> A visual heuristic, not an accusation.
> capitolalpha.app/screensavers?utm_source=social&utm_medium=social&utm_campaign=ss_policy

## 5. Art and design press

### 5a. Pitch for CreativeApplications.Net and It's Nice That
**Subject:** `Capitol Alpha: data sculptures from congressional stock trades (Mac screensavers)`
> Hi, I’m Sylvain Belahniche, a designer. Capitol Alpha Machine turns U.S. congressional stock trading disclosures into black-and-white data sculptures: 7,793 trades by 99 members, reduced to points, lines and intervals. Three of the scenes now ship as free native Mac screensavers that refresh weekly from public records.
>
> Live page: https://capitolalpha.app/screensavers?utm_source=press&utm_medium=email&utm_campaign=ss_press
> Three 12-second loops attached. Happy to send stills, process notes or a short text on the method.

Submit through CAN's submission form and It's Nice That's "submit work" page. Add the loops and stills to a public Are.na channel ("Capitol Alpha — data sculptures") and connect it to existing channels on generative and data art.

### 5b. Nightingale (Data Visualization Society)
Pitch an essay: **"Designing without color: data sculptures from congressional disclosures."** Cover the choice to drop red and green, value ranges as representative values, why proximity is presented as a heuristic, and moving a canvas scene into the macOS screensaver host.

## 6. Weekly automation

A scheduled task runs **every Monday at 16:47 Berlin time**, after the Monday data refresh. It reads `/updates/latest`, writes 3–4 new posts in this voice with tracking links, and saves them as a **Gmail draft** called "Capitol Alpha: posts for the week of …". It never sends or posts anything.

## 7. Tracking links (UTM scheme)

- `utm_source`: `hn` · `reddit` · `social` · `press` (or `x`, `bluesky`, `mastodon` if you want them split out)
- `utm_medium`: `social` · `email`
- `utm_campaign`: `ss_launch` · `ss_generative` · `ss_macapps` · `ss_dib` · `ss_returns` · `ss_policy` · `ss_press` · `ss_weekly_YYYYMMDD`

Check Vercel Analytics (Referrers and UTM) every Monday when the drafts arrive, and do more of whatever brought visits and downloads.
