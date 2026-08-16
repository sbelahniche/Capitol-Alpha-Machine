# Capitol Alpha Machine — Traffic & Distribution Kit

**Goal:** drive qualified traffic to https://capitolalpha.app/ without getting accounts or the domain banned.

> **How to use this:** Post from **your own accounts** (you can keep the handle "Silven" if you like — just use it consistently as a real identity, not as a throwaway). Every draft below is **value-first**: it leads with something interesting from the data, and the link is secondary. This is what survives Reddit/HN spam filters and what actually converts. Autonomous bot-posting of promo under a fake persona gets domains shadowbanned across Reddit — which would kill the traffic you're trying to build. Don't do it.

---

## The one rule that matters

Communities ban **link-dropping**, not **sharing**. The difference:

- ❌ "Check out my congressional trading tracker [link]" → removed as spam
- ✅ "I pulled every Capitol Trades disclosure and Congress's most-bought sector last quarter was [X]. Chart + method here [link]. Curious what people make of the timing." → upvoted

Lead with a finding. Make the link optional. Reply to comments. That's the whole game.

---

## Channel map (ranked by fit)

| Channel | Why it fits | Self-promo rule | Cadence |
|---|---|---|---|
| **r/dataisbeautiful** | Your site IS data-art. Perfect fit. | Must be OC, cite source/tool in comment | 1×/2 weeks (high effort posts) |
| **HN "Show HN"** | Loves interactive data viz + open data | One Show HN per project; be present in comments | Once, then "Show HN" for major updates |
| **r/wallstreetbets** | Pelosi/Congress trades are a meme there | No referral/promo spam; data posts OK | When you have a spicy finding |
| **r/investing, r/SecurityAnalysis** | Serious congressional-trading interest | 9:1 rule (9 normal comments per 1 self-post) | 1×/2 weeks |
| **r/dataisbeautiful, r/visualization** | Aesthetic appreciation | OC flair | rotate |
| **X / Twitter** | Cards render your og-image; Pelosi-trade niche is active | None — your account | every other day |
| **Bluesky / Threads** | Finance + data communities migrating | None | every other day |
| **Hacker News (regular submit)** | For methodology / writeups | No rule, but quality bar high | occasional |

**Subreddit homework before posting:** read each sub's rules tab once. r/investing requires a certain account age/karma; r/wallstreetbets filters new accounts. Build 50–100 comment karma first by genuinely participating.

---

## Ready-to-post drafts

### 1 — r/dataisbeautiful (flagship post)
**Title:** `[OC] I visualized $2.27B of disclosed congressional stock trades as interactive black-and-white data sculptures`

**Body:**
> I scraped every Capitol Trades disclosure (34,800 filings, 2023–2026) and built five interactive scenes — capital flow, a live ledger, committee exposure, returns spectrum, and a trade-timing lattice. It's deliberately monochrome: no red/green, just the shape of the money.
>
> Tools: Python for the scrape/clean, vanilla JS + canvas for rendering. Data source is public STOCK Act disclosures via Capitol Trades.
>
> Link in comments to keep this rule-friendly.

**First comment:** `Interactive version: https://capitolalpha.app/ — method writeup: https://capitolalpha.app/methodology`

---

### 2 — Show HN
**Title:** `Show HN: Capitol Alpha Machine – congressional stock trades as interactive data art`

**Body:**
> I turned public Capitol Trades disclosures into five interactive visualizations of how Congress trades — $2.27B in disclosed volume across ~34.8k filings. No login, no paywall, works on mobile. Stack is Python (ETL) + plain canvas/JS, hosted static on Vercel. Data + methodology pages are open.
>
> https://capitolalpha.app/
>
> Happy to talk about the scraping, the de-duplication of amended filings, or why I dropped color entirely.

---

### 3 — r/wallstreetbets (finding-led)
**Title:** `Pulled every congressional stock disclosure since 2023 — here's the most-traded sector and the timing pattern`

**Body:**
> Not financial advice, just data. I aggregated all Capitol Trades disclosures ($2.27B disclosed). [Insert this cycle's top finding — e.g. "Tech + semis dominate net buys; biggest clusters land right before committee weeks."] Made it into an interactive thing if you want to poke at it — link in comments.

**First comment:** link + one-line method.

---

### 4 — X / Twitter (thread starter)
> Congress disclosed $2.27B in stock trades since 2023.
>
> I turned all 34,800 filings into interactive data art — no red/green, just the shape of the money. 🧵
>
> Who trades most, what sectors, and the timing. 👇
> https://capitolalpha.app/

(Follow with 1 image per scene — your og-image and scene screenshots render great as cards.)

---

### 5 — X / Twitter (single, finding-led, for the every-other-day cadence)
> The Policy Proximity: each dot is a congressional trade plotted against when it landed relative to committee activity.
>
> Patterns you can see with your own eyes 👇
> https://capitolalpha.app/scenes/timing-lattice

---

### 6 — r/investing / r/SecurityAnalysis (discussion-led, no hard sell)
**Title:** `How useful is congressional trading disclosure data, really? I aggregated all of it and I'm skeptical`

**Body:**
> I built a full pipeline over Capitol Trades disclosures ($2.27B, 34.8k filings) and visualized flows/timing/returns. My honest take: the signal is noisier than the headlines suggest because of disclosure lag and amended filings. Curious how this community weighs it. Data + method are open if useful (will drop in a comment if allowed by the mods).

---

### 7 — Niche forums / communities
Post the finding-led version (#3 style) in: Bogleheads forum (data threads only), Stocktwits, finance Discords, and relevant Lemmy/Mastodon finance groups. Always: finding first, link optional, answer replies.

---

## Posting calendar (every other day, sustainable)

Rotate so no single platform sees promo too often:

- **Day 1:** X/Bluesky finding-led post (draft #5 style) + 1 scene image
- **Day 3:** Reply/engage in 2–3 finance threads (build karma, drop link only if directly relevant)
- **Day 5:** X thread or a fresh data finding
- **Day 7:** One high-effort Reddit post (rotate sub from the map)
- **Day 9:** X/Bluesky finding-led post
- **Day 11:** Engage + answer comments
- **Day 13:** New finding / scene spotlight
- repeat, swapping in Show HN / r/dataisbeautiful for milestones

The **scheduled task** I set up generates a fresh, ready-to-paste draft on this every-other-day cadence using your latest data, so you just review and post.

---

## Compliance / don't-get-banned checklist

- Use one consistent real identity per platform. No multiple accounts upvoting each other (vote manipulation = sitewide Reddit ban).
- Keep a >9:1 ratio of genuine participation to self-promotion on Reddit.
- Never post the same text across many subs the same day (Reddit flags cross-posting spam).
- Disclose it's your project when asked. Honesty converts better and avoids mod removal.
- Don't buy upvotes/traffic. It poisons analytics and risks bans.
