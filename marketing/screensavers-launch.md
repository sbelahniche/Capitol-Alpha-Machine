# Screensavers launch plan

Promotion plan for **capitolalpha.app/screensavers**: three free Mac screensavers, framed as data sculptures and visualization experiments. Written 2026-10-06.

**Posting approach.** Post from your own accounts, disclose that you made the project, and check each community’s current rules. Lead with the moving image, put the link second, and allow time to answer comments. Post to Reddit and Hacker News by hand; avoid repeated promotional submissions.

**Assets.** The loop videos are in `marketing/loops/`. Each scene has `*-16x9.mp4` for X, Bluesky, Reddit and LinkedIn, `*-1x1.mp4` for Mastodon and Instagram, and a small `*.gif` for Are.na, GitHub and emails.

---

## 1. Before launch (this week)

- [x] **Push and deploy.** Website, optimized downloads, updated copy and share image pushed to GitHub; Vercel reported the production deployment READY for `capitolalpha.app` on 2026-10-06.
- [ ] **Search Console.** Resubmit `sitemap.xml`, then use URL Inspection on `/screensavers` and request indexing.
- [x] **Share image.** Rebuilt `screensavers/og-screensavers.png` with the new H1, full brand name, and current point/member counts.
- [x] **Data freshness.** Synced the newer GitHub history and fetched filings published through 2026-10-05, covering trades through 2026-09-28. Weekly refreshes now regenerate the previews and showcase metadata. The page separately states the older returns and policy study windows; native savers check weekly for published updates.
- [ ] **Notarize the screensavers.** No Developer ID signing identity is available on this Mac. The current builds are ad-hoc signed, not notarized; disclose that clearly until notarized downloads are available.
- [ ] **Show HN check.** Search [hn.algolia.com](https://hn.algolia.com/?q=capitolalpha) for `capitolalpha`. If the main site already had a Show HN, use the "alternate HN" title below.
- [ ] **Repo link.** Decide whether the GitHub repo is public. If it is, link it from the Show HN and Reddit comments, because it sharply raises trust.
- [ ] **Measure downloads.** The zips are static files, so Vercel Analytics doesn't count them. Add a `track('download', {scene})` call on the download buttons.

## 2. Two-week sequence

These are proposed times in Berlin, chosen to overlap the US East Coast morning. Adjust them to audience response rather than assuming an optimal posting time.

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
| From Mon Oct 26 | Weekly | After confirming the existing Claude task, review weekly drafts and post 1–2 a week. | rotate loops |

On the days between posts, spend 10 minutes replying in r/creativecoding, on vis.social and in dataviz threads on Bluesky, without links.

## 3. Hacker News and Reddit (post by hand)

### 3a. Show HN
**Title:** `Show HN: Mac screensavers made from Congress's stock trades`
**Alternate title (if the site already had a Show HN):** `Show HN: Data sculptures from congressional trading disclosures, as free Mac screensavers`
**URL:** `https://capitolalpha.app/screensavers?utm_source=hn&utm_medium=social&utm_campaign=ss_launch`
**First comment:**
> I make black-and-white data sculptures from U.S. congressional stock trading disclosures (STOCK Act filings via Capitol Trades). Three of the scenes now run as native macOS screensavers: a ticker tape of Congress's own trades, a returns spectrum against SPY, and a timeline linking trades to new public laws.
>
> Individual ZIP downloads are 46–89 KB: a WKWebView hosting the same canvas scene as the site, with the WebKit occlusion workaround from WebViewScreenSaver. Once a week (Monday 12:00 local) it checks the latest published data bundle; price and law studies have separate update windows; offline it keeps the last set. No server, no tracking in the saver.
>
> Caveat up front: the builds are ad-hoc signed and not notarized, so macOS may block installation until you explicitly allow it. Happy to talk about the data pipeline, de-duplicating amended filings, or rendering in the screensaver host.

### 3b. r/generative and r/creativecoding (video post)
**Title:** `Data sculpture from 7,793 congressional stock trades, running as a Mac screensaver`
**First comment:**
> Each line is one disclosed trade: bright for purchases, dim for sales, and the bar shows the amount. Canvas 2D at 30 fps, monochrome only. The data comes from public STOCK Act disclosures via Capitol Trades. Three scenes in total, free for macOS: https://capitolalpha.app/screensavers?utm_source=reddit&utm_medium=social&utm_campaign=ss_generative

### 3c. r/macapps
Read the subreddit rules first. Use the Free flair and disclose that you're the developer.
**Title:** `[Free] Three monochrome screensavers built from real congressional stock trades`
**Body:**
> I'm the developer. Three native .saver files (universal, macOS 12+, ZIP downloads 46–89 KB each) made from public STOCK Act disclosures. They check for published updates once a week and run offline on the last set. Ad-hoc signed but not notarized yet, so macOS may block the first installation (System Settings → Privacy & Security → Open Anyway). Checksums are on the page.
> https://capitolalpha.app/screensavers?utm_source=reddit&utm_medium=social&utm_campaign=ss_macapps

### 3d. r/dataisbeautiful
**Title:** `[OC] 5,621 congressional stock trades by 58 members, plotted against 90-day excess return vs. the S&P 500`
**First comment (required for OC posts):**
> Source: STOCK Act disclosures via Capitol Trades, with daily closing prices against SPY. Tools: Python for the data, Canvas 2D for rendering. Each row is a member and each tick is a trade; taller, brighter ticks are stocks with higher 90-day excess returns in the published historical dataset. It's a visual heuristic, not evidence of anything. It also runs as a free Mac screensaver: https://capitolalpha.app/screensavers?utm_source=reddit&utm_medium=social&utm_campaign=ss_dib

## 4. X, Bluesky and Mastodon

These are the same text everywhere. Each one fits Bluesky's 300-character limit. Attach the loop video natively instead of relying on the link card. On Mastodon, post from vis.social or tag `#dataviz #generative #creativecoding`.

### 4a. Launch
> Data sculptures for an idle screen.
>
> Three free Mac screensavers built from 7,793 congressional stock trades. Pelosi, Tuberville, Khanna, McCaul and 91 more. Monochrome, no commentary.
>
> capitolalpha.app/screensavers?utm_source=social&utm_medium=social&utm_campaign=ss_launch

### 4b. Returns Spectrum
> Returns Spectrum. Each row is a member of Congress, each tick a disclosed trade. Taller and brighter means higher 90-day excess returns in the published historical dataset.
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
> Hi, I’m Sylvain Belahniche, a designer. Capitol Alpha Machine turns U.S. congressional stock trading disclosures into black-and-white data sculptures: 7,793 trade records by 95 members, reduced to points, lines and intervals. Three of the scenes now ship as free native Mac screensavers that check weekly for published data updates.
>
> Live page: https://capitolalpha.app/screensavers?utm_source=press&utm_medium=email&utm_campaign=ss_press
> Three 12-second loops attached. Happy to send stills, process notes or a short text on the method.

Submit through CAN's submission form and It's Nice That's "submit work" page. Add the loops and stills to a public Are.na channel ("Capitol Alpha — data sculptures") and connect it to existing channels on generative and data art.

### 5b. Nightingale (Data Visualization Society)
Pitch an essay: **"Designing without color: data sculptures from congressional disclosures."** Cover the choice to drop red and green, value ranges as representative values, why proximity is presented as a heuristic, and moving a canvas scene into the macOS screensaver host.

## 6. Weekly automation

The shared Claude conversation reports a draft-only task scheduled **every Monday at 16:47 Berlin time**. Confirm its status in Claude before relying on it. It is intended to read `/updates/latest` and save 3–4 post ideas to a Gmail draft; it must not send or post anything. This continuation has not created a duplicate task in Codex or verified Gmail access.

## 7. Tracking links (UTM scheme)

- `utm_source`: `hn` · `reddit` · `social` · `press` (or `x`, `bluesky`, `mastodon` if you want them split out)
- `utm_medium`: `social` · `email`
- `utm_campaign`: `ss_launch` · `ss_generative` · `ss_macapps` · `ss_dib` · `ss_returns` · `ss_policy` · `ss_press` · `ss_weekly_YYYYMMDD`

Check available visit and download measurements each week, and do more of whatever brought visits and downloads.
