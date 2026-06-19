#!/usr/bin/env python3
"""Generate the crawlable SEO surface for Capitol Alpha Machine.

The project is intentionally visual-first, but search engines and link previews
need stable text, feeds, and structured metadata. This script generates those
assets from the bundled public disclosure data without creating thin pages.
"""

from __future__ import annotations

import datetime as dt
import email.utils
import html
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SITE_URL = "https://capitolalpha.app"
AUTHOR = "Sylvain Belahniche"
TODAY = dt.date.today()
TODAY_ISO = TODAY.isoformat()
NOW_UTC = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
RSS_DATE = email.utils.format_datetime(NOW_UTC)
DATA_LICENSE_URL = f"{SITE_URL}/data#data-use-notes"
DATA_LICENSE = {
    "@type": "CreativeWork",
    "name": "Capitol Alpha Machine data use notes",
    "url": DATA_LICENSE_URL,
}

# Entity / E-E-A-T configuration.
# sameAs links strengthen the brand entity graph for AI and search engines.
# Add verified social/profile URLs here (X, LinkedIn, etc.) as they exist.
AUTHOR_URL = "https://github.com/sbelahniche"
SOCIAL_PROFILES = [
    "https://github.com/sbelahniche/Capitol-Alpha-Machine",
    AUTHOR_URL,
]
OG_IMAGE_URL = f"{SITE_URL}/og-image.png"
LOGO_URL = f"{SITE_URL}/favicon-ct.png"

PERSON = {
    "@type": "Person",
    "@id": f"{SITE_URL}/#author",
    "name": AUTHOR,
    "url": AUTHOR_URL,
    "sameAs": SOCIAL_PROFILES,
}

ORGANIZATION = {
    "@type": "Organization",
    "@id": f"{SITE_URL}/#org",
    "name": "Capitol Alpha Machine",
    "url": f"{SITE_URL}/",
    "logo": {"@type": "ImageObject", "url": LOGO_URL},
    "image": OG_IMAGE_URL,
    "sameAs": SOCIAL_PROFILES,
    "founder": {"@id": f"{SITE_URL}/#author"},
}

ORG_REF = {"@id": f"{SITE_URL}/#org"}
PERSON_REF = {"@id": f"{SITE_URL}/#author"}


def breadcrumb_schema(trail: list[tuple[str, str]]) -> dict[str, Any]:
    """Build BreadcrumbList JSON-LD from (name, path) pairs."""
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i + 1,
                "name": name,
                "item": url_for(path),
            }
            for i, (name, path) in enumerate(trail)
        ],
    }

SCENES = [
    {
        "id": "scene01",
        "order": "01",
        "slug": "capital-flow",
        "title": "Capital Flow",
        "description": "Capital Flow shows total disclosed trading volume as a cumulative line climbing to the full public total, with net cumulative flow snaking faintly underneath.",
        "dek": "A single cumulative line climbs through disclosed trading volume, every buy and sell added together, while net cumulative flow snakes faintly beneath it.",
        "metric": "Total disclosed trading volume",
        "note": "Careful wording: this scene shows disclosed trading volume, not proven profit, intent, or unlawful conduct.",
    },
    {
        "id": "scene02",
        "order": "02",
        "slug": "the-ledger",
        "title": "The Ledger",
        "description": "A congressional trading tape built from Capitol Trades disclosures, showing tickers, transaction direction, member names, and disclosed value bands.",
        "dek": "A disclosure tape where ticker symbols fall as records, bright purchases and dimmer sales forming a mechanical ledger of congressional trading activity.",
        "metric": "Disclosure records, ticker lanes, and amount bands",
        "note": "Transaction values are disclosed as public reporting ranges; the scene uses representative values for visualization.",
    },
    {
        "id": "scene03",
        "order": "03",
        "slug": "exposure-index",
        "title": "Exposure Index",
        "description": "A black-and-white data sculpture mapping disclosed congressional trades into a dense exposure field from Capitol Trades data.",
        "dek": "Disclosed congressional trades become a living exposure field: density, motion, and intensity turn transaction records into a navigable market signal.",
        "metric": "34,771 disclosures in the current data window",
        "note": "The visualization is based on public disclosure data and should be read as editorial data art, not as an allegation of wrongdoing.",
    },
    {
        "id": "scene04",
        "order": "04",
        "slug": "returns-spectrum",
        "title": "Returns Spectrum",
        "description": "A returns spectrum visualization comparing disclosed congressional trades with trailing excess-return signals across members and sectors.",
        "dek": "Member rows and return traces organize disclosed trades into a spectrum of trailing market performance, scanning for distance from a baseline.",
        "metric": "Member rows x trailing 90-day excess return",
        "note": "Return signals are calculated for visualization and should not be interpreted as investment advice.",
    },
    {
        "id": "scene05",
        "order": "05",
        "slug": "timing-lattice",
        "title": "Timing Lattice",
        "description": "A timing lattice linking public-law events with disclosed congressional trades through sector and date proximity heuristics.",
        "dek": "Public-law events and disclosed trades form a timing lattice, connecting sector lanes and dates as a visual heuristic rather than a claim of causation.",
        "metric": "Congress.gov public-law events x Capitol Trades disclosures",
        "note": "Links are timing and sector proximity heuristics only, not evidence of causation or unlawful conduct.",
    },
]


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def money(value: float | int | None) -> str:
    if value is None:
        return "not available"
    value = float(value)
    sign = "-" if value < 0 else ""
    value = abs(value)
    if value >= 1_000_000_000:
        return f"{sign}${value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"{sign}${value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{sign}${value / 1_000:.0f}K"
    return f"{sign}${value:,.0f}"


def number(value: int | float | None) -> str:
    if value is None:
        return "not available"
    return f"{int(value):,}"


def url_for(path: str) -> str:
    if path == "/":
        return SITE_URL + "/"
    return SITE_URL + path.rstrip("/")


def scene_path(scene: dict[str, str]) -> str:
    return f"/scenes/{scene['slug']}"


def read_js_object(bundle: str, name: str) -> dict[str, Any]:
    marker = f"window.{name}="
    start = bundle.index(marker) + len(marker)
    obj, _ = json.JSONDecoder().raw_decode(bundle[start:])
    return obj


def load_data() -> dict[str, Any]:
    bundle = (ROOT / "capitoltrades_data.js").read_text(encoding="utf-8")
    return {
        "scene01": read_js_object(bundle, "CAPITOL_TRADES_SCENE01"),
        "scene04": read_js_object(bundle, "CAPITOL_TRADES_SCENE04"),
        "scene05": read_js_object(bundle, "CAPITOL_TRADES_SCENE05"),
    }


def top_from_scene04(scene04: dict[str, Any]) -> tuple[list[tuple[str, int, int]], list[tuple[str, int, int]]]:
    tickers = scene04.get("TICK", [])
    members = scene04.get("MEM", [])
    ticker_stats: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    member_stats: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for trade in scene04.get("TR", []):
        amount = int(trade.get("amount") or 0)
        ticker_index = trade.get("ticker")
        member_index = trade.get("member")
        if isinstance(ticker_index, int) and 0 <= ticker_index < len(tickers):
            row = ticker_stats[tickers[ticker_index]]
            row[0] += 1
            row[1] += amount
        if isinstance(member_index, int) and 0 <= member_index < len(members):
            row = member_stats[members[member_index]]
            row[0] += 1
            row[1] += amount
    top_tickers = sorted(
        ((name, vals[0], vals[1]) for name, vals in ticker_stats.items()),
        key=lambda row: (row[2], row[1]),
        reverse=True,
    )[:8]
    top_members = sorted(
        ((name, vals[0], vals[1]) for name, vals in member_stats.items()),
        key=lambda row: (row[2], row[1]),
        reverse=True,
    )[:8]
    return top_tickers, top_members


def committee_risk_summary(scene05: dict[str, Any]) -> dict[str, Any]:
    committees: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "count": 0,
            "value": 0,
            "risk_sum": 0,
            "timing_sum": 0,
            "overlap": 0,
            "flagged": 0,
            "members": set(),
            "sectors": Counter(),
            "events": set(),
        }
    )
    members: set[str] = set()
    flags: Counter[str] = Counter()
    total_value = 0
    overlap_count = 0
    for trade in scene05.get("trades", []):
        committee = str(trade.get("committee") or "Unknown")
        value = int(trade.get("value") or 0)
        risk = int(trade.get("riskScore") or 0)
        timing = int(trade.get("timingScore") or 0)
        row = committees[committee]
        row["count"] += 1
        row["value"] += value
        row["risk_sum"] += risk
        row["timing_sum"] += timing
        row["sectors"][str(trade.get("sector") or "unknown")] += 1
        if trade.get("eventId"):
            row["events"].add(str(trade["eventId"]))
        if trade.get("member"):
            member = str(trade["member"])
            row["members"].add(member)
            members.add(member)
        trade_flags = [str(flag) for flag in trade.get("riskFlags", [])]
        flags.update(trade_flags)
        if "committee-sector-overlap" in trade_flags:
            row["overlap"] += 1
            overlap_count += 1
        if risk >= 75 or timing >= 75:
            row["flagged"] += 1

    rows = []
    for committee, row in committees.items():
        count = row["count"] or 1
        rows.append(
            {
                "committee": committee,
                "count": row["count"],
                "value": row["value"],
                "avg_risk": round(row["risk_sum"] / count),
                "avg_timing": round(row["timing_sum"] / count),
                "overlap": row["overlap"],
                "flagged": row["flagged"],
                "member_count": len(row["members"]),
                "event_count": len(row["events"]),
                "top_sectors": row["sectors"].most_common(3),
            }
        )
    rows.sort(key=lambda row: (row["value"], row["count"]), reverse=True)
    meaningful_min = 10
    return {
        "committee_count": len(rows),
        "committee_record_count": len(scene05.get("trades", [])),
        "committee_total_value": total_value or sum(row["value"] for row in rows),
        "committee_member_count": len(members),
        "committee_overlap_count": overlap_count,
        "committee_meaningful_min": meaningful_min,
        "committee_meaningful_count": sum(1 for row in rows if row["count"] >= meaningful_min),
        "committee_top": rows[:10],
        "risk_flags": flags.most_common(8),
    }


def build_metrics(data: dict[str, Any]) -> dict[str, Any]:
    scene01 = data["scene01"]
    scene04 = data["scene04"]
    scene05 = data["scene05"]
    meta01 = scene01.get("meta", {})
    meta04 = scene04.get("meta", {})
    meta05 = scene05.get("meta", {})
    total_volume = (
        meta01.get("publicVolumeTotal")
        or meta01.get("totalGross")
        or sum(int(w.get("gross") or abs(w.get("net") or 0)) for w in scene01.get("weeks", []))
    )
    top_tickers, top_members = top_from_scene04(scene04)
    committee_summary = committee_risk_summary(scene05)
    event_count = meta05.get("eventCount") or len(scene05.get("events", []))
    timing_trade_count = meta05.get("tradeCount") or len(scene05.get("trades", []))
    return {
        "source_from": meta01.get("from"),
        "source_to": meta01.get("to"),
        "source": meta01.get("source", "Capitol Trades"),
        "source_pages": meta01.get("pages"),
        "disclosure_count": meta01.get("count"),
        "buy_sell_count": meta01.get("buySellCount"),
        "value_basis": meta01.get("valueBasis"),
        "skipped_types": meta01.get("skippedTypes", {}),
        "skipped_anomalous_dates": meta01.get("skippedAnomalousDates"),
        "total_volume": total_volume,
        "volume_source": meta01.get("publicVolumeSource"),
        "returns_from": meta04.get("from"),
        "returns_to": meta04.get("to"),
        "returns_source": meta04.get("source"),
        "returns_count": meta04.get("count"),
        "returns_source_count": meta04.get("sourceCount"),
        "event_from": meta05.get("from"),
        "event_to": meta05.get("to"),
        "event_source": meta05.get("source"),
        "event_source_urls": meta05.get("eventSourceUrls", []),
        "trade_source_url": meta05.get("tradeSource"),
        "timing_generated_at": meta05.get("generatedAt"),
        "event_count": event_count,
        "timing_trade_count": timing_trade_count,
        "top_tickers": top_tickers,
        "top_members": top_members,
        **committee_summary,
    }


def json_script(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


COMMON_CSS = """
:root { color-scheme: dark; --fg:#fff; --muted:rgba(255,255,255,.62); --dim:rgba(255,255,255,.38); --line:rgba(255,255,255,.18); }
* { box-sizing: border-box; }
html, body { margin:0; background:#000; color:var(--fg); font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,"Liberation Mono","Courier New",monospace; }
a { color:inherit; }
.topbar { position:sticky; top:0; z-index:5; display:flex; justify-content:space-between; align-items:center; gap:24px; padding:18px clamp(18px,5vw,72px); background:#000; border-bottom:1px solid var(--line); }
.brand { text-decoration:none; font-weight:700; font-size:13px; letter-spacing:.16em; text-transform:uppercase; white-space:nowrap; }
.nav { display:flex; gap:18px; flex-wrap:wrap; color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.08em; }
main { min-height:100svh; }
.hero, .band { padding:clamp(42px,8vw,104px) clamp(18px,6vw,96px); border-bottom:1px solid var(--line); }
.hero { min-height:58svh; display:grid; align-content:end; }
.eyebrow { margin:0 0 14px; color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.14em; }
h1 { margin:0; max-width:1100px; font-size:clamp(36px,7vw,96px); line-height:.92; letter-spacing:0; }
h2 { margin:0 0 24px; font-size:clamp(22px,3.2vw,44px); line-height:1.05; letter-spacing:0; }
p { max-width:900px; color:rgba(255,255,255,.75); font-size:clamp(14px,1.65vw,19px); line-height:1.6; }
.dek { margin:24px 0 0; max-width:920px; font-size:clamp(16px,2vw,24px); color:rgba(255,255,255,.80); }
.facts { display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:1px; margin-top:34px; border:1px solid var(--line); background:var(--line); max-width:1100px; }
.fact { min-height:118px; padding:18px; background:#000; }
.label { color:var(--dim); font-size:10px; text-transform:uppercase; letter-spacing:.12em; }
.value { margin-top:16px; font-size:clamp(20px,3vw,36px); line-height:1; }
.table { width:100%; max-width:1100px; border-collapse:collapse; margin-top:26px; font-size:13px; }
.table th, .table td { padding:12px 0; border-bottom:1px solid rgba(255,255,255,.14); text-align:left; vertical-align:top; }
.table th { color:var(--dim); font-size:10px; text-transform:uppercase; letter-spacing:.12em; font-weight:400; }
.table td:last-child, .table th:last-child { text-align:right; }
.note { max-width:980px; color:rgba(255,255,255,.50); font-size:12px; line-height:1.7; }
.callout { max-width:980px; margin-top:28px; padding:20px; border:1px solid var(--line); color:rgba(255,255,255,.72); font-size:13px; line-height:1.65; }
.list { max-width:980px; margin:24px 0 0; padding-left:20px; color:rgba(255,255,255,.72); font-size:14px; line-height:1.7; }
.list li { margin:10px 0; }
.kicker { margin-top:28px; color:rgba(255,255,255,.45); font-size:11px; line-height:1.6; text-transform:uppercase; letter-spacing:.12em; }
.links { display:flex; flex-wrap:wrap; gap:12px 22px; margin-top:28px; color:rgba(255,255,255,.66); font-size:12px; text-transform:uppercase; letter-spacing:.08em; }
.footer { padding:28px clamp(18px,6vw,96px); color:rgba(255,255,255,.36); font-size:11px; }
@media (max-width:720px) { .topbar { align-items:flex-start; flex-direction:column; } .table { font-size:12px; } }
""".strip()


def render_schemas(schema: dict[str, Any] | list[dict[str, Any]]) -> str:
    blocks = schema if isinstance(schema, list) else [schema]
    return "\n".join(
        f'<script type="application/ld+json">{json_script(block)}</script>'
        for block in blocks
    )


def base_page(title: str, description: str, path: str, body: str,
              schema: dict[str, Any] | list[dict[str, Any]]) -> str:
    canonical = url_for(path)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<meta name="author" content="{esc(AUTHOR)}">
<meta name="robots" content="index,follow">
<link rel="canonical" href="{canonical}">
<link rel="alternate" type="application/rss+xml" title="Capitol Alpha Machine updates" href="{SITE_URL}/rss.xml">
<link rel="icon" type="image/png" href="/favicon-ct.png?v=20260604">
<meta name="theme-color" content="#000000">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Capitol Alpha Machine">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{OG_IMAGE_URL}">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(description)}">
<meta name="twitter:image" content="{OG_IMAGE_URL}">
{render_schemas(schema)}
<style>{COMMON_CSS}</style>
</head>
<body>
<header class="topbar">
  <a class="brand" href="/">Capitol Alpha Machine</a>
  <nav class="nav" aria-label="Primary">
    <a href="/methodology">Methodology</a>
    <a href="/data">Data</a>
    <a href="/datasets/committee-risk">Committee Risk</a>
    <a href="/updates/latest">Latest</a>
    <a href="/faq">FAQ</a>
    <a href="/scenes/capital-flow">Capital Flow</a>
  </nav>
</header>
{body}
<footer class="footer">By <a href="{AUTHOR_URL}" rel="author">{esc(AUTHOR)}</a> &middot; Capitol Alpha Machine. Public disclosure data is used for visualization and research context only. Not investment advice, not an allegation of unlawful conduct.</footer>
</body>
</html>
"""


def methodology_page(metrics: dict[str, Any]) -> str:
    event_links = "\n      ".join(
        f'<a href="{esc(url)}">Congress.gov public laws</a>' for url in metrics.get("event_source_urls", [])
    )
    schema = {
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "headline": "Capitol Alpha Machine methodology",
        "url": url_for("/methodology"),
        "dateModified": TODAY_ISO,
        "author": PERSON,
        "publisher": ORGANIZATION,
        "about": ["congressional trading disclosures", "data visualization", "Capitol Trades"],
    }
    crumbs = breadcrumb_schema([
        ("Capitol Alpha Machine", "/"),
        ("Methodology", "/methodology"),
    ])
    body = f"""
<main>
  <section class="hero">
    <p class="eyebrow">Methodology</p>
    <h1>How the machine reads disclosed congressional trading data.</h1>
    <p class="dek">Capitol Alpha Machine turns public disclosure records into cinematic data scenes: disclosed trading volume, member exposure, market movement, and timing proximity to public-law events.</p>
  </section>
  <section class="band">
    <h2>Sources</h2>
    <p>The primary trading source is Capitol Trades public disclosure data. Returns Spectrum combines the disclosure bundle with end-of-day market price signals. Timing Lattice also uses Congress.gov public-law listings for the 118th and 119th Congresses.</p>
    <div class="facts">
      <div class="fact"><div class="label">Disclosure window</div><div class="value">{esc(metrics["source_from"])} to {esc(metrics["source_to"])}</div></div>
      <div class="fact"><div class="label">Disclosures read</div><div class="value">{number(metrics["disclosure_count"])}</div></div>
      <div class="fact"><div class="label">Buy/sell rows</div><div class="value">{number(metrics["buy_sell_count"])}</div></div>
      <div class="fact"><div class="label">Disclosed volume</div><div class="value">{money(metrics["total_volume"])}</div></div>
    </div>
    <div class="links">
      <a href="https://www.capitoltrades.com/trades">Capitol Trades source</a>
      {event_links}
      <a href="/data/">Current dataset summary</a>
    </div>
  </section>
  <section class="band">
    <h2>Value ranges and volume</h2>
    <p>Congressional financial disclosures use reported value ranges, not exact order sizes. The project uses representative disclosed values for visual weight and ranking. Capital Flow separates scale from direction: gross disclosed volume sums buys and sells, while net flow treats buys as positive and sells as negative.</p>
    <table class="table"><thead><tr><th>Input</th><th>How it is used</th><th>Caveat</th></tr></thead><tbody>
      <tr><td>Disclosed value ranges</td><td>Representative values drive visual weight and summary tables.</td><td>Not exact transaction accounting.</td></tr>
      <tr><td>Gross disclosed volume</td><td>Shows total public trading scale across buys and sells.</td><td>Not profit, performance, or intent.</td></tr>
      <tr><td>Net cumulative flow</td><td>Buys are positive and sells are negative.</td><td>Directional visualization only.</td></tr>
    </tbody></table>
    <p class="note">{esc(metrics.get("value_basis") or "Gross volume sums buys and sells; net flow uses buys positive and sells negative.")}</p>
  </section>
  <section class="band">
    <h2>Timing and sector heuristics</h2>
    <p>Committee exposure and Timing Lattice are triage heuristics. They are designed to help readers inspect patterns, not to make claims about motive or inside information.</p>
    <ul class="list">
      <li>Committee-sector exposure compares a member's committee context with sectors represented in disclosed trades.</li>
      <li>Timing Lattice links public-law events to trades by date proximity and sector proximity.</li>
      <li>Returns Spectrum compares disclosed trades with trailing market movement for visualization context only.</li>
      <li>Reporting dates can lag transaction dates, and some disclosures include spouse, dependent, or joint transactions.</li>
    </ul>
    <div class="callout">These links are not allegations. They are not evidence of causation, intent, privileged information, or unlawful conduct. The project is data art and research context, not investment advice or a legal conclusion.</div>
  </section>
  <section class="band">
    <h2>Caveats</h2>
    <p>Congressional financial disclosures are incomplete as a market dataset. Some transaction types are excluded from buy/sell flow, reported values are ranges, and disclosure timing can vary. The current bundle skipped exchange and received transaction types for flow math because they are not clean buy/sell signals.</p>
    <table class="table"><thead><tr><th>Known limitation</th><th>Current handling</th></tr></thead><tbody>
      <tr><td>Value ranges</td><td>Use representative values for visualization.</td></tr>
      <tr><td>Exchange / received rows</td><td>Excluded from buy/sell flow when not directionally comparable.</td></tr>
      <tr><td>Anomalous dates</td><td>{number(metrics.get("skipped_anomalous_dates"))} rows skipped in the current flow bundle.</td></tr>
      <tr><td>Timing links</td><td>Presented as proximity heuristics only.</td></tr>
    </tbody></table>
    <div class="links">
      <a href="/data/">Read the data summary</a>
      <a href="/updates/latest/">Latest update</a>
    </div>
  </section>
</main>
"""
    return base_page(
        "Methodology | Capitol Alpha Machine",
        "Methodology for Capitol Alpha Machine, a data-art intelligence project visualizing congressional trading disclosures, committee exposure, timing patterns, and market movement.",
        "/methodology",
        body,
        [schema, crumbs],
    )


def data_page(metrics: dict[str, Any]) -> str:
    top_ticker_rows = "\n".join(
        f"<tr><td>{esc(name)}</td><td>{number(count)}</td><td>{money(total)}</td></tr>"
        for name, count, total in metrics["top_tickers"]
    )
    top_member_rows = "\n".join(
        f"<tr><td>{esc(name.title())}</td><td>{number(count)}</td><td>{money(total)}</td></tr>"
        for name, count, total in metrics["top_members"]
    )
    event_source_rows = "\n".join(
        f'<tr><td>Congress.gov public laws</td><td><a href="{esc(url)}">{esc(url)}</a></td></tr>'
        for url in metrics.get("event_source_urls", [])
    )
    schema = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": "Capitol Alpha Machine disclosure data summary",
        "description": "Crawlable summary of the public congressional trading disclosure bundle behind Capitol Alpha Machine, including disclosure windows, disclosed volume, returns rows, and timing-lattice public-law event links.",
        "url": url_for("/data"),
        "dateModified": TODAY_ISO,
        "creator": PERSON,
        "publisher": ORGANIZATION,
        "temporalCoverage": f"{metrics['source_from']}/{metrics['source_to']}",
        "isAccessibleForFree": True,
        "license": DATA_LICENSE,
        "usageInfo": DATA_LICENSE_URL,
        "variableMeasured": [
            "disclosed trading volume",
            "buy and sell disclosure count",
            "trailing excess return",
            "timing and sector proximity",
        ],
        "distribution": {
            "@type": "DataDownload",
            "encodingFormat": "application/javascript",
            "contentUrl": f"{SITE_URL}/capitoltrades_data.js",
        },
    }
    crumbs = breadcrumb_schema([
        ("Capitol Alpha Machine", "/"),
        ("Data", "/data"),
    ])
    body = f"""
<main>
  <section class="hero">
    <p class="eyebrow">Data</p>
    <h1>The current disclosure bundle behind the machine.</h1>
    <p class="dek">A crawlable summary of the public data currently bundled into the interactive scenes, generated on {TODAY_ISO}.</p>
  </section>
  <section class="band">
    <h2>Current dataset summary</h2>
    <div class="facts">
      <div class="fact"><div class="label">Trading disclosure window</div><div class="value">{esc(metrics["source_from"])} to {esc(metrics["source_to"])}</div></div>
      <div class="fact"><div class="label">Disclosures</div><div class="value">{number(metrics["disclosure_count"])}</div></div>
      <div class="fact"><div class="label">Buy/sell disclosures</div><div class="value">{number(metrics["buy_sell_count"])}</div></div>
      <div class="fact"><div class="label">Total disclosed volume</div><div class="value">{money(metrics["total_volume"])}</div></div>
      <div class="fact"><div class="label">Returns rows</div><div class="value">{number(metrics["returns_count"])}</div></div>
      <div class="fact"><div class="label">Public-law events</div><div class="value">{number(metrics["event_count"])}</div></div>
    </div>
    <p class="note">{esc(metrics.get("volume_source") or "Volume is derived from disclosed transaction values in the bundled data.")}</p>
  </section>
  <section class="band">
    <h2>Dataset windows</h2>
    <table class="table"><thead><tr><th>Bundle</th><th>Window</th><th>Rows / events</th></tr></thead><tbody>
      <tr><td>Trading disclosures</td><td>{esc(metrics["source_from"])} to {esc(metrics["source_to"])}</td><td>{number(metrics["disclosure_count"])} disclosures from {number(metrics.get("source_pages"))} source pages</td></tr>
      <tr><td>Buy/sell flow</td><td>{esc(metrics["source_from"])} to {esc(metrics["source_to"])}</td><td>{number(metrics["buy_sell_count"])} directionally comparable rows</td></tr>
      <tr><td>Returns Spectrum</td><td>{esc(metrics["returns_from"])} to {esc(metrics["returns_to"])}</td><td>{number(metrics["returns_count"])} rows from {number(metrics.get("returns_source_count"))} source disclosures</td></tr>
      <tr><td>Timing Lattice</td><td>{esc(metrics["event_from"])} to {esc(metrics["event_to"])}</td><td>{number(metrics["event_count"])} public-law events linked to {number(metrics["timing_trade_count"])} trades</td></tr>
      <tr><td>Generated page date</td><td>{TODAY_ISO}</td><td>Static trust page regenerated from bundled data</td></tr>
    </tbody></table>
  </section>
  <section class="band">
    <h2>Sources</h2>
    <table class="table"><thead><tr><th>Source</th><th>Use</th></tr></thead><tbody>
      <tr><td>{esc(metrics.get("source") or "Capitol Trades")}</td><td>Public congressional trading disclosures and disclosed volume.</td></tr>
      <tr><td>{esc(metrics.get("returns_source") or "Capitol Trades + EOD prices")}</td><td>Returns Spectrum rows and trailing market movement context.</td></tr>
      <tr><td>{esc(metrics.get("event_source") or "Congress.gov public laws + Capitol Trades")}</td><td>Timing Lattice event spine and sector/date proximity links.</td></tr>
      {event_source_rows}
      <tr><td>Timing bundle generated</td><td>{esc(metrics.get("timing_generated_at") or "not available")}</td></tr>
    </tbody></table>
    <div class="callout">The headline number is total disclosed trading volume. It is not profit, loss, market impact, intent, or an allegation of unlawful conduct.</div>
  </section>
  <section class="band" id="data-use-notes">
    <h2>Data use notes</h2>
    <p>This generated dataset page describes an editorial visualization bundle derived from public disclosure sources. Original source records remain subject to their publishers' terms. Reuse should cite Capitol Alpha Machine and the underlying public sources, preserve the caveats about disclosure ranges and timing heuristics, and avoid presenting representative values as exact holdings, profit, intent, or evidence of wrongdoing.</p>
  </section>
  <section class="band">
    <h2>Top tickers in the returns bundle</h2>
    <table class="table"><thead><tr><th>Ticker</th><th>Rows</th><th>Representative disclosed value</th></tr></thead><tbody>{top_ticker_rows}</tbody></table>
  </section>
  <section class="band">
    <h2>Top members in the returns bundle</h2>
    <table class="table"><thead><tr><th>Member</th><th>Rows</th><th>Representative disclosed value</th></tr></thead><tbody>{top_member_rows}</tbody></table>
    <p class="note">These rankings use representative disclosed values inside the returns scene bundle. They are not a complete accounting of holdings, profit, or intent.</p>
    <div class="links">
      <a href="/methodology/">Methodology and caveats</a>
      <a href="/datasets/committee-risk/">Committee-risk dataset</a>
      <a href="/updates/latest/">Latest weekly report</a>
      <a href="/scenes/capital-flow">Capital Flow scene</a>
    </div>
  </section>
</main>
"""
    return base_page(
        "Data | Capitol Alpha Machine",
        "Current data summary for Capitol Alpha Machine, including disclosure windows, disclosed trading volume, scene rows, and public-law event counts.",
        "/data",
        body,
        [schema, crumbs],
    )


def committee_risk_page(metrics: dict[str, Any]) -> str:
    committee_rows = "\n".join(
        "<tr>"
        f"<td>{esc(row['committee'])}</td>"
        f"<td>{number(row['count'])}</td>"
        f"<td>{money(row['value'])}</td>"
        f"<td>{number(row['member_count'])}</td>"
        f"<td>{number(row['avg_risk'])}</td>"
        f"<td>{number(row['avg_timing'])}</td>"
        f"<td>{esc(', '.join(sector for sector, _ in row['top_sectors']))}</td>"
        "</tr>"
        for row in metrics["committee_top"]
    )
    flag_rows = "\n".join(
        f"<tr><td>{esc(flag.replace('-', ' '))}</td><td>{number(count)}</td></tr>"
        for flag, count in metrics["risk_flags"]
    )
    event_source_rows = "\n".join(
        f'<tr><td>Congress.gov public laws</td><td><a href="{esc(url)}">{esc(url)}</a></td></tr>'
        for url in metrics.get("event_source_urls", [])
    )
    schema = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": "Capitol Alpha Machine committee-risk dataset",
        "url": url_for("/datasets/committee-risk"),
        "dateModified": TODAY_ISO,
        "creator": PERSON,
        "publisher": ORGANIZATION,
        "temporalCoverage": f"{metrics['event_from']}/{metrics['event_to']}",
        "description": "Controlled aggregate dataset page for committee-sector and timing proximity heuristics used by Capitol Alpha Machine.",
        "isAccessibleForFree": True,
        "license": DATA_LICENSE,
        "usageInfo": DATA_LICENSE_URL,
        "variableMeasured": [
            "committee-sector proximity",
            "public-law event proximity",
            "representative disclosed value",
            "timing score",
            "risk score",
            "reporting gap",
        ],
        "isBasedOn": [
            "https://www.capitoltrades.com/trades",
            *metrics.get("event_source_urls", []),
        ],
    }
    crumbs = breadcrumb_schema([
        ("Capitol Alpha Machine", "/"),
        ("Committee-Risk Dataset", "/datasets/committee-risk"),
    ])
    body = f"""
<main>
  <section class="hero">
    <p class="eyebrow">Dataset</p>
    <h1>Committee-risk proximity dataset.</h1>
    <p class="dek">A controlled aggregate page for the Timing Lattice dataset: committee context, sector proximity, public-law timing, and representative disclosed values. No individual member, ticker, or committee pages are generated yet.</p>
  </section>
  <section class="band">
    <h2>Current dataset</h2>
    <div class="facts">
      <div class="fact"><div class="label">Event window</div><div class="value">{esc(metrics["event_from"])} to {esc(metrics["event_to"])}</div></div>
      <div class="fact"><div class="label">Public-law events</div><div class="value">{number(metrics["event_count"])}</div></div>
      <div class="fact"><div class="label">Linked trade rows</div><div class="value">{number(metrics["timing_trade_count"])}</div></div>
      <div class="fact"><div class="label">Committees</div><div class="value">{number(metrics["committee_count"])}</div></div>
      <div class="fact"><div class="label">Members represented</div><div class="value">{number(metrics["committee_member_count"])}</div></div>
      <div class="fact"><div class="label">Representative value</div><div class="value">{money(metrics["committee_total_value"])}</div></div>
    </div>
    <p class="note">Generated from the bundled Timing Lattice data on {TODAY_ISO}. Source bundle generated at {esc(metrics.get("timing_generated_at") or "not available")}.</p>
  </section>
  <section class="band">
    <h2>Sources and method</h2>
    <p>This page summarizes the committee-risk dataset used by the Timing Lattice scene. It links public-law events to disclosed trade rows using date proximity and sector proximity. Committee-sector overlap is a heuristic flag, not a claim of causation.</p>
    <table class="table"><thead><tr><th>Source</th><th>Use</th></tr></thead><tbody>
      <tr><td>{esc(metrics.get("event_source") or "Congress.gov public laws + Capitol Trades")}</td><td>Event spine, disclosed trades, committee labels, sectors, and proximity flags.</td></tr>
      <tr><td>Capitol Trades</td><td><a href="{esc(metrics.get("trade_source_url") or "https://www.capitoltrades.com/trades")}">{esc(metrics.get("trade_source_url") or "https://www.capitoltrades.com/trades")}</a></td></tr>
      {event_source_rows}
    </tbody></table>
    <div class="callout">This dataset page is not an allegation page. Scores and links are visualization heuristics only. They are not evidence of intent, privileged information, causation, profit, or unlawful conduct.</div>
  </section>
  <section class="band">
    <h2>Top committees in the current aggregate</h2>
    <table class="table"><thead><tr><th>Committee</th><th>Rows</th><th>Representative value</th><th>Members</th><th>Avg risk</th><th>Avg timing</th><th>Top sectors</th></tr></thead><tbody>{committee_rows}</tbody></table>
    <p class="note">Rows are aggregate only. This page intentionally does not create individual committee pages yet.</p>
  </section>
  <section class="band">
    <h2>Risk flags</h2>
    <table class="table"><thead><tr><th>Flag</th><th>Rows</th></tr></thead><tbody>{flag_rows}</tbody></table>
    <p class="note">Flags describe why a row became visually prominent inside the Timing Lattice. They should be read as triage labels for inspection, not conclusions.</p>
  </section>
  <section class="band">
    <h2>Generation policy</h2>
    <p>Programmatic pages stay controlled. The site currently publishes this aggregate dataset page and the weekly update only. Later, individual pages should be generated only when the row count and source context are strong enough to avoid thin or misleading pages.</p>
    <table class="table"><thead><tr><th>Future page type</th><th>Current rule</th></tr></thead><tbody>
      <tr><td>Top ticker pages</td><td>Generate only for the top 10 tickers by representative disclosed volume, with enough rows and source context.</td></tr>
      <tr><td>Top member pages</td><td>Generate only for the top 10 members by representative disclosed volume, with careful caveats and no allegation framing.</td></tr>
      <tr><td>Committee pages</td><td>Generate only for committees with at least {number(metrics["committee_meaningful_min"])} linked rows and meaningful sector/event context. Current qualifying committees: {number(metrics["committee_meaningful_count"])}.</td></tr>
    </tbody></table>
    <div class="links">
      <a href="/methodology/">Methodology</a>
      <a href="/data/">Data summary</a>
      <a href="/updates/latest/">Latest update</a>
      <a href="/scenes/timing-lattice">Timing Lattice</a>
    </div>
  </section>
</main>
"""
    return base_page(
        "Committee-Risk Dataset | Capitol Alpha Machine",
        "Controlled aggregate dataset page for Capitol Alpha Machine committee-sector and timing proximity heuristics, with sources, caveats, and generation policy.",
        "/datasets/committee-risk",
        body,
        [schema, crumbs],
    )


def latest_update_page(metrics: dict[str, Any]) -> str:
    ticker_rows = "\n".join(
        f"<tr><td>{esc(name)}</td><td>{number(count)}</td><td>{money(total)}</td></tr>"
        for name, count, total in metrics["top_tickers"][:5]
    )
    member_rows = "\n".join(
        f"<tr><td>{esc(name.title())}</td><td>{number(count)}</td><td>{money(total)}</td></tr>"
        for name, count, total in metrics["top_members"][:5]
    )
    schema = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": "Latest Capitol Alpha Machine data update",
        "url": url_for("/updates/latest"),
        "datePublished": TODAY_ISO,
        "dateModified": TODAY_ISO,
        "author": PERSON,
        "publisher": ORGANIZATION,
        "image": OG_IMAGE_URL,
        "description": "Latest crawlable update for Capitol Alpha Machine congressional trading disclosure visualizations.",
    }
    crumbs = breadcrumb_schema([
        ("Capitol Alpha Machine", "/"),
        ("Latest Update", "/updates/latest"),
    ])
    body = f"""
<main>
  <section class="hero">
    <p class="eyebrow">Weekly report - {TODAY_ISO}</p>
    <h1>{money(metrics["total_volume"])} in total disclosed trading volume.</h1>
    <p class="dek">The current machine bundle reads {number(metrics["disclosure_count"])} public disclosures from {esc(metrics["source_from"])} to {esc(metrics["source_to"])} and renders them across five interactive data scenes.</p>
  </section>
  <section class="band">
    <h2>This week at a glance</h2>
    <div class="facts">
      <div class="fact"><div class="label">Total disclosed volume</div><div class="value">{money(metrics["total_volume"])}</div></div>
      <div class="fact"><div class="label">Buy/sell disclosures</div><div class="value">{number(metrics["buy_sell_count"])}</div></div>
      <div class="fact"><div class="label">Returns records</div><div class="value">{number(metrics["returns_count"])}</div></div>
      <div class="fact"><div class="label">Timing events</div><div class="value">{number(metrics["event_count"])}</div></div>
      <div class="fact"><div class="label">Timing-linked trades</div><div class="value">{number(metrics["timing_trade_count"])}</div></div>
    </div>
    <p class="note">Generated from the bundled data on {TODAY_ISO}. {esc(metrics.get("volume_source") or "Total volume is derived from disclosed transaction values.")}</p>
  </section>
  <section class="band">
    <h2>Report notes</h2>
    <table class="table"><thead><tr><th>Signal</th><th>Current read</th></tr></thead><tbody>
      <tr><td>Capital Flow</td><td>A cumulative total-flow line climbs to the full disclosed volume while net cumulative flow snakes underneath.</td></tr>
      <tr><td>Disclosure coverage</td><td>{number(metrics["disclosure_count"])} public disclosures across {esc(metrics["source_from"])} to {esc(metrics["source_to"])}.</td></tr>
      <tr><td>Returns coverage</td><td>{number(metrics["returns_count"])} rows in the current returns bundle.</td></tr>
      <tr><td>Timing Lattice coverage</td><td>{number(metrics["event_count"])} public-law events and {number(metrics["timing_trade_count"])} proximity-linked trades.</td></tr>
    </tbody></table>
  </section>
  <section class="band">
    <h2>Largest ticker rows in the current returns bundle</h2>
    <table class="table"><thead><tr><th>Ticker</th><th>Rows</th><th>Representative disclosed value</th></tr></thead><tbody>{ticker_rows}</tbody></table>
  </section>
  <section class="band">
    <h2>Largest member rows in the current returns bundle</h2>
    <table class="table"><thead><tr><th>Member</th><th>Rows</th><th>Representative disclosed value</th></tr></thead><tbody>{member_rows}</tbody></table>
    <p class="note">Rows use representative disclosed values from public disclosure ranges. They are not exact holdings, profit, or intent.</p>
  </section>
  <section class="band">
    <h2>Read the scenes</h2>
    <p>Capital Flow emphasizes total disclosed trading volume as a cumulative climb while net cumulative flow snakes underneath. Exposure Index frames committee-sector overlap as a triage signal. Returns Spectrum compares disclosed trades to trailing market movement. Timing Lattice links public laws and trades through date and sector proximity only.</p>
    <div class="callout">This weekly report is a crawlable editorial layer over the visualization data. It does not accuse any member of wrongdoing and does not claim causation between trades and public-law events.</div>
    <div class="links">
      <a href="/scenes/capital-flow">Capital Flow</a>
      <a href="/scenes/exposure-index">Exposure Index</a>
      <a href="/scenes/returns-spectrum">Returns Spectrum</a>
      <a href="/scenes/timing-lattice">Timing Lattice</a>
      <a href="/methodology/">Methodology</a>
      <a href="/data/">Data summary</a>
      <a href="/datasets/committee-risk/">Committee-risk dataset</a>
    </div>
  </section>
</main>
"""
    return base_page(
        "Latest Update | Capitol Alpha Machine",
        "Latest data update for Capitol Alpha Machine, including disclosed trading volume, disclosure counts, returns rows, and timing-lattice event counts.",
        "/updates/latest",
        body,
        [schema, crumbs],
    )


def faq_items(metrics: dict[str, Any]) -> list[tuple[str, str]]:
    """Question/answer pairs. Answers are kept to ~40-60 words and lead with a
    direct response so they are eligible for featured snippets, People Also Ask,
    and voice answers. Live metrics keep them in sync with the data bundle."""
    volume = money(metrics["total_volume"])
    disclosures = number(metrics["disclosure_count"])
    return [
        (
            "What is Capitol Alpha Machine?",
            "Capitol Alpha Machine is an interactive data-art project that visualizes disclosed "
            "U.S. congressional stock trading. It turns public disclosure records from Capitol "
            "Trades into five cinematic scenes covering trading volume, member exposure, market "
            "returns, and timing relative to public-law events. It is research context and data "
            "art, not investment advice.",
        ),
        (
            "Where does the congressional trading data come from?",
            f"The primary source is Capitol Trades public disclosure data. Returns Spectrum adds "
            f"end-of-day market prices, and Timing Lattice uses Congress.gov public-law listings "
            f"for the 118th and 119th Congresses. The current bundle reads {disclosures} "
            f"disclosures from {esc(metrics['source_from'])} to {esc(metrics['source_to'])}.",
        ),
        (
            "What does disclosed trading volume mean?",
            f"Disclosed trading volume is the sum of buy and sell transaction values reported in "
            f"congressional financial disclosures, currently {volume} in total. It measures "
            f"reported trading scale only. It is not profit, loss, market impact, intent, or an "
            f"allegation of unlawful conduct.",
        ),
        (
            "Is Capitol Alpha Machine investment advice?",
            "No. The project is editorial data visualization and research context only. It does "
            "not recommend securities, predict returns, or provide financial advice. Disclosed "
            "values are reported ranges used for visualization, not exact holdings, and should "
            "not be the basis for any trading decision.",
        ),
        (
            "Does the data prove insider trading or wrongdoing?",
            "No. Committee-sector overlap and timing links are proximity heuristics designed to "
            "help readers inspect patterns. They are not evidence of causation, intent, "
            "privileged information, or unlawful conduct, and the project makes no allegations "
            "against any member of Congress.",
        ),
        (
            "What are representative disclosed values?",
            "Congressional disclosures report value ranges, not exact amounts. Capitol Alpha "
            "Machine assigns a single representative value within each reported range to drive "
            "visual weight and ranking. These figures support visualization and comparison only "
            "and are not exact transaction accounting.",
        ),
        (
            "How is the Timing Lattice built?",
            f"Timing Lattice links public-law events to disclosed trades using date proximity and "
            f"sector proximity. The current bundle connects {number(metrics['event_count'])} "
            f"public-law events to {number(metrics['timing_trade_count'])} trades. Links are "
            f"visualization heuristics for inspection, not claims that any law caused any trade.",
        ),
        (
            "How often is the data updated?",
            f"A crawlable weekly report records each data snapshot, and the latest bundle runs "
            f"through {esc(metrics['source_to'])}. The most recent figures, including {volume} in "
            f"disclosed volume across {disclosures} disclosures, are always shown on the Latest "
            f"update page.",
        ),
    ]


def faq_page(metrics: dict[str, Any]) -> str:
    items = faq_items(metrics)
    schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "url": url_for("/faq"),
        "name": "Capitol Alpha Machine FAQ",
        "dateModified": TODAY_ISO,
        "author": PERSON,
        "publisher": ORGANIZATION,
        "mainEntity": [
            {
                "@type": "Question",
                "name": question,
                "acceptedAnswer": {"@type": "Answer", "text": answer},
            }
            for question, answer in items
        ],
    }
    crumbs = breadcrumb_schema([
        ("Capitol Alpha Machine", "/"),
        ("FAQ", "/faq"),
    ])
    qa_blocks = "\n".join(
        f"""  <section class="band">
    <h2>{esc(question)}</h2>
    <p>{esc(answer)}</p>
  </section>"""
        for question, answer in items
    )
    body = f"""
<main>
  <section class="hero">
    <p class="eyebrow">FAQ</p>
    <h1>Questions about congressional trading data and this project.</h1>
    <p class="dek">Plain answers about what Capitol Alpha Machine shows, where its data comes from, and the careful limits on how disclosed congressional trading should be read.</p>
  </section>
{qa_blocks}
  <section class="band">
    <div class="links">
      <a href="/methodology">Methodology and caveats</a>
      <a href="/data">Data summary</a>
      <a href="/datasets/committee-risk">Committee-risk dataset</a>
      <a href="/updates/latest">Latest update</a>
    </div>
  </section>
</main>
"""
    return base_page(
        "FAQ | Capitol Alpha Machine",
        "Frequently asked questions about Capitol Alpha Machine: what disclosed congressional trading volume means, where the data comes from, and why the project is research context, not investment advice or an allegation of wrongdoing.",
        "/faq",
        body,
        [schema, crumbs],
    )


def scene_page(scene: dict[str, str], metrics: dict[str, Any]) -> str:
    metric = scene["metric"]
    description = scene["description"]
    dek = scene["dek"]
    if scene["slug"] == "capital-flow":
        metric = f"{money(metrics['total_volume'])} total disclosed trading volume"
        description = f"Capital Flow shows {money(metrics['total_volume'])} in total disclosed trading volume as a single cumulative line climbs to the full total - buys and sells combined - with net cumulative flow snaking faintly underneath."
        dek = f"A single cumulative line climbs to {money(metrics['total_volume'])} in total disclosed trading volume - every buy and sell added together - while net cumulative flow snakes faintly beneath it, making the sheer scale of congressional trading impossible to miss."
    if scene["slug"] == "exposure-index":
        metric = f"{number(metrics['disclosure_count'])} disclosures in the current data window"
    canonical = url_for(scene_path(scene))
    schema = {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "name": f"{scene['title']} - Capitol Alpha Machine",
        "url": canonical,
        "isPartOf": {"@type": "WebSite", "name": "Capitol Alpha Machine", "url": SITE_URL + "/"},
        "description": description,
        "creator": PERSON,
        "publisher": ORGANIZATION,
        "image": OG_IMAGE_URL,
        "about": ["congressional trading disclosures", "Capitol Trades data", "financial data visualization"],
        "dateModified": TODAY_ISO,
    }
    crumbs = breadcrumb_schema([
        ("Capitol Alpha Machine", "/"),
        (scene["title"], scene_path(scene)),
    ])
    links = "\n        ".join(
        f'<a href="{scene_path(s)}">{esc(s["order"])} - {esc(s["title"])}</a>' for s in SCENES
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(scene["title"])} | Capitol Alpha Machine</title>
<meta name="description" content="{esc(description)}">
<meta name="author" content="{esc(AUTHOR)}">
<meta name="robots" content="index,follow">
<link rel="canonical" href="{canonical}">
<link rel="alternate" type="application/rss+xml" title="Capitol Alpha Machine updates" href="{SITE_URL}/rss.xml">
<link rel="icon" type="image/png" href="/favicon-ct.png?v=20260604">
<meta name="theme-color" content="#000000">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Capitol Alpha Machine">
<meta property="og:title" content="{esc(scene["title"])} | Capitol Alpha Machine">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{OG_IMAGE_URL}">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(scene["title"])} | Capitol Alpha Machine">
<meta name="twitter:description" content="{esc(description)}">
<meta name="twitter:image" content="{OG_IMAGE_URL}">
{render_schemas([schema, crumbs])}
<style>
{COMMON_CSS}
.scene-hero {{ min-height:100svh; position:relative; background:#000; border-bottom:1px solid var(--line); }}
.scene-hero iframe {{ position:absolute; inset:0; width:100%; height:100%; border:0; background:#000; display:block; }}
</style>
</head>
<body>
<main>
  <section class="scene-hero" aria-label="Interactive {esc(scene["title"])} visualization">
    <iframe src="/index.html?scene={esc(scene["id"])}&embed=1" title="{esc(scene["title"])} interactive visualization" loading="eager"></iframe>
  </section>
  <section class="band">
    <p class="eyebrow">Scene {esc(scene["order"])} - Capitol Alpha Machine</p>
    <h1>{esc(scene["title"])}</h1>
    <p class="dek">{esc(dek)}</p>
    <p class="value">{esc(metric)}</p>
    <p class="note">{esc(scene["note"])}</p>
    <nav class="links" aria-label="Scene pages">
        {links}
    </nav>
    <div class="links">
      <a href="/index.html?scene={esc(scene["id"])}">Open in the full interactive machine</a>
      <a href="/methodology/">Methodology</a>
      <a href="/data/">Data summary</a>
    </div>
  </section>
</main>
</body>
</html>
"""


def robots_txt() -> str:
    return f"""User-agent: *
Allow: /
Sitemap: {SITE_URL}/sitemap.xml
Sitemap: {SITE_URL}/sitemap.txt
"""


def sitemap_urls() -> list[tuple[str, str, str]]:
    return [
        ("/", "1.0", "weekly"),
        ("/methodology", "0.9", "monthly"),
        ("/data", "0.9", "weekly"),
        ("/updates/latest", "0.9", "weekly"),
        ("/datasets/committee-risk", "0.85", "weekly"),
        ("/faq", "0.7", "monthly"),
        *[(scene_path(scene), "0.8", "monthly") for scene in SCENES],
    ]


def sitemap_xml() -> str:
    urls = sitemap_urls()
    entries = "\n".join(
        f"""  <url>
    <loc>{url_for(path)}</loc>
    <lastmod>{TODAY_ISO}</lastmod>
    <changefreq>{freq}</changefreq>
    <priority>{priority}</priority>
  </url>"""
        for path, priority, freq in urls
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{entries}
</urlset>
"""


def sitemap_txt() -> str:
    return "\n".join(url_for(path) for path, _priority, _freq in sitemap_urls()) + "\n"


def rss_xml(metrics: dict[str, Any]) -> str:
    items = [
        {
            "title": "Latest Capitol Alpha Machine data update",
            "link": url_for("/updates/latest"),
            "description": f"{money(metrics['total_volume'])} in total disclosed trading volume across {number(metrics['disclosure_count'])} public disclosures.",
        },
        {
            "title": "Capital Flow",
            "link": url_for("/scenes/capital-flow"),
            "description": "A cumulative total-flow line climbs to total disclosed trading volume while net cumulative flow snakes underneath.",
        },
        {
            "title": "Committee-risk dataset",
            "link": url_for("/datasets/committee-risk"),
            "description": f"Aggregate committee-sector and timing-proximity dataset with {number(metrics['timing_trade_count'])} linked trade rows and {number(metrics['event_count'])} public-law events.",
        },
        {
            "title": "Methodology",
            "link": url_for("/methodology"),
            "description": "Sources, caveats, and heuristics behind Capitol Alpha Machine.",
        },
    ]
    item_xml = "\n".join(
        f"""    <item>
      <title>{esc(item["title"])}</title>
      <link>{item["link"]}</link>
      <guid>{item["link"]}</guid>
      <pubDate>{RSS_DATE}</pubDate>
      <description>{esc(item["description"])}</description>
    </item>"""
        for item in items
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Capitol Alpha Machine Updates</title>
    <link>{SITE_URL}/</link>
    <description>Data-art updates from Capitol Alpha Machine, a congressional trading disclosure visualization project.</description>
    <language>en-us</language>
    <lastBuildDate>{RSS_DATE}</lastBuildDate>
{item_xml}
  </channel>
</rss>
"""


def og_image_svg(metrics: dict[str, Any]) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <rect width="1200" height="630" fill="#000"/>
  <g opacity="0.20" fill="#fff">
    <rect x="78" y="74" width="2" height="2"/><rect x="184" y="112" width="2" height="2"/><rect x="322" y="82" width="2" height="2"/><rect x="488" y="146" width="2" height="2"/><rect x="710" y="96" width="2" height="2"/><rect x="945" y="132" width="2" height="2"/><rect x="1080" y="88" width="2" height="2"/>
    <rect x="96" y="468" width="2" height="2"/><rect x="242" y="520" width="2" height="2"/><rect x="414" y="476" width="2" height="2"/><rect x="638" y="536" width="2" height="2"/><rect x="826" y="486" width="2" height="2"/><rect x="1018" y="522" width="2" height="2"/>
  </g>
  <path d="M70 420 C180 380, 248 458, 356 410 S560 330, 690 388 S920 464, 1130 360" fill="none" stroke="#fff" stroke-opacity="0.24" stroke-width="2"/>
  <g fill="#fff" opacity="0.36">
    <rect x="78" y="514" width="9" height="26"/><rect x="103" y="492" width="9" height="48"/><rect x="128" y="506" width="9" height="34"/><rect x="153" y="468" width="9" height="72"/><rect x="178" y="500" width="9" height="40"/><rect x="203" y="442" width="9" height="98"/><rect x="228" y="486" width="9" height="54"/><rect x="253" y="462" width="9" height="78"/><rect x="278" y="510" width="9" height="30"/>
    <rect x="920" y="500" width="9" height="40"/><rect x="945" y="430" width="9" height="110"/><rect x="970" y="472" width="9" height="68"/><rect x="995" y="448" width="9" height="92"/><rect x="1020" y="515" width="9" height="25"/><rect x="1045" y="394" width="9" height="146"/><rect x="1070" y="486" width="9" height="54"/><rect x="1095" y="456" width="9" height="84"/>
  </g>
  <text x="72" y="120" fill="#fff" fill-opacity="0.52" font-family="SFMono-Regular, Menlo, Consolas, monospace" font-size="22" letter-spacing="4">CAPITOL ALPHA MACHINE</text>
  <text x="72" y="245" fill="#fff" font-family="SFMono-Regular, Menlo, Consolas, monospace" font-size="76" font-weight="700">Congressional</text>
  <text x="72" y="326" fill="#fff" font-family="SFMono-Regular, Menlo, Consolas, monospace" font-size="76" font-weight="700">Trading Signals</text>
  <text x="76" y="386" fill="#fff" fill-opacity="0.68" font-family="SFMono-Regular, Menlo, Consolas, monospace" font-size="24">{esc(money(metrics["total_volume"]))} disclosed volume - {esc(number(metrics["disclosure_count"]))} disclosures</text>
</svg>
"""


def index_schema(metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "@context": "https://schema.org",
        "@graph": [
            PERSON,
            ORGANIZATION,
            {
                "@type": "WebSite",
                "@id": f"{SITE_URL}/#website",
                "name": "Capitol Alpha Machine",
                "url": f"{SITE_URL}/",
                "description": "A cinematic visualization of U.S. congressional trading disclosures, committee exposure, timing patterns, and market movement.",
                "inLanguage": "en-US",
                "creator": PERSON_REF,
                "publisher": ORG_REF,
            },
            {
                "@type": "WebApplication",
                "@id": f"{SITE_URL}/#app",
                "name": "Capitol Alpha Machine",
                "url": f"{SITE_URL}/",
                "applicationCategory": "DataVisualizationApplication",
                "operatingSystem": "Any",
                "browserRequirements": "Requires a modern browser with canvas and iframe support.",
                "description": "Interactive data-art intelligence project visualizing congressional trading disclosures.",
                "creator": PERSON_REF,
                "publisher": ORG_REF,
            },
            {
                "@type": "Dataset",
                "@id": f"{SITE_URL}/#dataset",
                "name": "Capitol Alpha Machine disclosure visualization bundle",
                "url": f"{SITE_URL}/data",
                "dateModified": TODAY_ISO,
                "temporalCoverage": f"{metrics['source_from']}/{metrics['source_to']}",
                "creator": PERSON_REF,
                "publisher": ORG_REF,
                "description": f"Bundled public disclosure data used to visualize {number(metrics['disclosure_count'])} congressional trading disclosures and {money(metrics['total_volume'])} in disclosed trading volume.",
                "isAccessibleForFree": True,
                "license": DATA_LICENSE,
                "usageInfo": DATA_LICENSE_URL,
                "variableMeasured": [
                    "disclosed trading volume",
                    "buy and sell disclosure count",
                    "net cumulative disclosed flow",
                    "committee-sector exposure",
                    "timing and sector proximity",
                    "trailing excess return",
                ],
                "distribution": {
                    "@type": "DataDownload",
                    "encodingFormat": "application/javascript",
                    "contentUrl": f"{SITE_URL}/capitoltrades_data.js",
                },
            },
        ],
    }


def index_scene_nav() -> str:
    links = "\n  ".join(
        f'<a href="{scene_path(scene)}">{esc(scene["title"])} congressional trading visualization</a>'
        for scene in SCENES
    )
    return f"""<nav class="seo-links" aria-label="Scene pages">
  {links}
</nav>"""


def index_noscript(metrics: dict[str, Any]) -> str:
    items = "\n      ".join(
        f'<li><a href="{scene_path(scene)}">{esc(scene["title"])}</a></li>'
        for scene in SCENES
    )
    return f"""<noscript>
  <section>
    <h2>Capitol Alpha Machine scenes</h2>
    <p>Interactive visualizations of disclosed congressional trading data from Capitol Trades, including {money(metrics["total_volume"])} in total disclosed trading volume.</p>
    <ul>
      {items}
    </ul>
  </section>
</noscript>"""


def inject_index_metadata(metrics: dict[str, Any]) -> None:
    path = ROOT / "index.html"
    text = path.read_text(encoding="utf-8")
    head_block = f"""<!-- SEO GENERATED HEAD START -->
<link rel="alternate" type="application/rss+xml" title="Capitol Alpha Machine updates" href="{SITE_URL}/rss.xml">
<meta name="author" content="{esc(AUTHOR)}">
<meta property="og:image" content="{OG_IMAGE_URL}">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:image" content="{OG_IMAGE_URL}">
<!-- SEO GENERATED HEAD END -->"""
    schema_block = f"""<!-- SEO JSON-LD START -->
<script type="application/ld+json">{json_script(index_schema(metrics))}</script>
<!-- SEO JSON-LD END -->"""

    text = replace_or_insert(
        text,
        "<!-- SEO GENERATED HEAD START -->",
        "<!-- SEO GENERATED HEAD END -->",
        head_block,
        before="<script>\n  if (new URLSearchParams(location.search).get('embed') === '1')",
    )
    text = replace_or_insert(
        text,
        "<!-- SEO JSON-LD START -->",
        "<!-- SEO JSON-LD END -->",
        schema_block,
        before="</head>" if "</head>" in text else '<script id="scene01-html"',
    )
    text = replace_or_insert(
        text,
        '<nav class="seo-links"',
        "</nav>",
        index_scene_nav(),
        before="<noscript>",
    )
    text = replace_or_insert(
        text,
        "<noscript>",
        "</noscript>",
        index_noscript(metrics),
        before='<header class="app-menu">',
    )
    path.write_text(text, encoding="utf-8")


def replace_or_insert(text: str, start_marker: str, end_marker: str, block: str, before: str) -> str:
    pattern = re.compile(re.escape(start_marker) + r".*?" + re.escape(end_marker), re.DOTALL)
    if pattern.search(text):
        return pattern.sub(block, text)
    index = text.find(before)
    if index == -1:
        raise ValueError(f"Could not find insertion point: {before!r}")
    return text[:index] + block + "\n" + text[index:]


def normalize_internal_slashes(text: str) -> str:
    """Drop trailing slashes from root-relative hrefs to match vercel.json
    (trailingSlash:false, cleanUrls:true) and the canonical URLs, removing
    needless 301 redirect hops. External (https://) hrefs are untouched."""
    return re.sub(r'href="(/[^"#?]+?)/"', r'href="\1"', text)


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    if path.endswith(".html"):
        content = normalize_internal_slashes(content)
    target.write_text(content, encoding="utf-8")


def write_og_png(metrics: dict[str, Any]) -> bool:
    """Render a 1200x630 PNG Open Graph card. SVG og:images are not rendered
    by Facebook, LinkedIn, X/Twitter, Slack, etc., so a raster card is required
    for working link previews. Falls back gracefully if Pillow is unavailable."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        print("  ! Pillow not installed - kept existing og-image.png (run: pip install pillow)")
        return False

    W, H = 1200, 630
    img = Image.new("RGB", (W, H), "#000000")
    draw = ImageDraw.Draw(img)

    font_candidates = [
        "/usr/share/fonts/truetype/liberation/LiberationMono-{w}.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono{w2}.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/Library/Fonts/Arial.ttf",
    ]

    def load_font(size: int, bold: bool = False):
        for tmpl in font_candidates:
            path = tmpl.format(w=("Bold" if bold else "Regular"),
                               w2=("-Bold" if bold else ""))
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
        return ImageFont.load_default()

    # Decorative bar clusters (echoing the on-site data sculpture).
    bars_left = [(78, 514, 26), (103, 492, 48), (128, 506, 34), (153, 468, 72),
                 (178, 500, 40), (203, 442, 98), (228, 486, 54), (253, 462, 78)]
    bars_right = [(920, 500, 40), (945, 430, 110), (970, 472, 68), (995, 448, 92),
                  (1020, 515, 25), (1045, 394, 146), (1070, 486, 54), (1095, 456, 84)]
    for x, y, h in bars_left + bars_right:
        draw.rectangle([x, y, x + 9, y + h], fill=(255, 255, 255), outline=None)

    eyebrow = load_font(22, bold=False)
    title = load_font(74, bold=True)
    sub = load_font(24, bold=False)

    draw.text((72, 96), "CAPITOL ALPHA MACHINE", font=eyebrow, fill=(150, 150, 150))
    draw.text((72, 180), "Congressional", font=title, fill=(255, 255, 255))
    draw.text((72, 264), "Trading Signals", font=title, fill=(255, 255, 255))
    subtitle = f"{money(metrics['total_volume'])} disclosed volume  -  {number(metrics['disclosure_count'])} disclosures"
    draw.text((76, 372), subtitle, font=sub, fill=(176, 176, 176))

    img.save(ROOT / "og-image.png", "PNG", optimize=True)
    return True


def main() -> None:
    data = load_data()
    metrics = build_metrics(data)

    for scene in SCENES:
        content = scene_page(scene, metrics)
        write(f"scenes/{scene['slug']}/index.html", content)
    write("methodology/index.html", methodology_page(metrics))
    write("data/index.html", data_page(metrics))
    write("datasets/committee-risk/index.html", committee_risk_page(metrics))
    write("updates/latest/index.html", latest_update_page(metrics))
    write("faq/index.html", faq_page(metrics))
    write("robots.txt", robots_txt())
    write("sitemap.xml", sitemap_xml())
    write("sitemap.txt", sitemap_txt())
    write("rss.xml", rss_xml(metrics))
    write("og-image.svg", og_image_svg(metrics))
    write_og_png(metrics)
    inject_index_metadata(metrics)

    print("Generated SEO assets:")
    for item in [
        "robots.txt",
        "sitemap.xml",
        "sitemap.txt",
        "rss.xml",
        "og-image.svg",
        "og-image.png",
        "methodology/index.html",
        "data/index.html",
        "datasets/committee-risk/index.html",
        "updates/latest/index.html",
        "faq/index.html",
        "scenes/capital-flow/index.html",
    ]:
        print(f"  - {item}")


if __name__ == "__main__":
    main()
