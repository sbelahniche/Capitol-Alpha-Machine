#!/usr/bin/env python3
"""Build a committee/trade risk dataset from Capitol Trades public pages."""

from __future__ import annotations

import argparse
import bisect
import csv
import datetime as dt
import html as html_module
import json
import re
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from capitoltrades_scrape import NEXT_CHUNK_RE, SITE_URL, extract_trades, get_html


POLITICIAN_ID_RE = re.compile(r"/politicians/([A-Z]\d{6})")
PAGE_COUNT_RE = re.compile(r"Page <b>\d+</b> of <b>(\d+)</b>")
COMMITTEE_ITEM_RE = re.compile(r'\{"id":"([^"]+)","label":"([^"]+)"\}')

CSV_FIELDS = [
    "riskScore",
    "riskFlags",
    "tradeId",
    "txDate",
    "pubDate",
    "reportingGap",
    "politicianId",
    "politician",
    "party",
    "chamber",
    "state",
    "committeeId",
    "committee",
    "committeeChamber",
    "txType",
    "owner",
    "value",
    "issuerId",
    "issuerName",
    "ticker",
    "sector",
    "committeeSectorMatch",
    "committeeJurisdictionSectors",
    "repeat90dCount",
    "price",
    "sourceUrl",
]


def parse_date(value: str | None) -> dt.date | None:
    if not value:
        return None
    try:
        return dt.date.fromisoformat(value[:10])
    except ValueError:
        return None


def subtract_years(value: dt.date, years: int) -> dt.date:
    try:
        return value.replace(year=value.year - years)
    except ValueError:
        return value.replace(month=2, day=28, year=value.year - years)


def decode_next_chunks(html: str) -> str:
    chunks: list[str] = []
    for raw_chunk in NEXT_CHUNK_RE.findall(html):
        chunks.append(json.loads(f'"{raw_chunk}"'))
    return "\n".join(chunks)


def scrape_committee_labels(timeout: float) -> dict[str, str]:
    html = get_html(f"{SITE_URL}/politicians?page=1&pageSize=100", timeout)
    text = decode_next_chunks(html)
    match = re.search(r'placeholder":"Committee".*?"filterName":"state"', text, re.DOTALL)
    segment = match.group(0) if match else text
    return {committee_id: label for committee_id, label in COMMITTEE_ITEM_RE.findall(segment)}


def committee_chamber(label: str) -> str | None:
    lowered = label.lower()
    if lowered.startswith("house"):
        return "house"
    if lowered.startswith("senate"):
        return "senate"
    if lowered.startswith("joint"):
        return "joint"
    return None


def committee_name(label: str) -> str:
    return re.sub(r"^\w+\s+-\s+", "", label).strip()


def scrape_sitemap_committee_ids(timeout: float) -> list[str]:
    xml = get_html(f"{SITE_URL}/committees/sitemap.xml", timeout)
    root = ET.fromstring(xml)
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    ids: list[str] = []
    for loc in root.findall(".//sm:loc", namespace):
        if loc.text:
            ids.append(loc.text.rstrip("/").split("/")[-1])
    return sorted(set(ids))


def scrape_committee_page_label(committee_id: str, timeout: float) -> str | None:
    html = get_html(f"{SITE_URL}/committees/{committee_id}", timeout)
    match = re.search(r"<title>(.*?) \| Committee Profile</title>", html)
    if not match:
        return None
    title = html_module.unescape(match.group(1)).strip()
    if committee_id.startswith("j"):
        if title.lower().startswith("joint "):
            return title
        return f"Joint - {title}"
    return title


def extract_page_count(html: str) -> int:
    match = PAGE_COUNT_RE.search(html)
    return int(match.group(1)) if match else 1


def scrape_committee_members(
    labels: dict[str, str],
    timeout: float,
    delay: float,
    page_size: int,
    progress: bool,
) -> dict[str, list[str]]:
    members: dict[str, list[str]] = {}
    committee_ids = sorted(labels)
    for index, committee_id in enumerate(committee_ids, 1):
        ids: set[str] = set()
        first_url = (
            f"{SITE_URL}/politicians?"
            f"{urllib.parse.urlencode({'committee': committee_id, 'pageSize': page_size, 'page': 1})}"
        )
        html = get_html(first_url, timeout)
        ids.update(POLITICIAN_ID_RE.findall(html))
        page_count = extract_page_count(html)
        for page in range(2, page_count + 1):
            if delay > 0:
                time.sleep(delay)
            url = (
                f"{SITE_URL}/politicians?"
                f"{urllib.parse.urlencode({'committee': committee_id, 'pageSize': page_size, 'page': page})}"
            )
            html = get_html(url, timeout)
            ids.update(POLITICIAN_ID_RE.findall(html))
        members[committee_id] = sorted(ids)
        if progress:
            print(
                f"Scraped {index}/{len(committee_ids)} committees: "
                f"{committee_id} has {len(ids)} trading members",
                file=sys.stderr,
            )
        if index < len(committee_ids) and delay > 0:
            time.sleep(delay)
    return members


def fetch_trade_pages(args: argparse.Namespace) -> dict[str, Any]:
    seen: set[int] = set()
    trades: list[dict[str, Any]] = []
    params = [("pageSize", str(args.trade_page_size))]
    for offset in range(args.trade_pages):
        page = args.trade_start_page + offset
        query = [("page", str(page)), ("sort", args.trade_sort), *params]
        url = f"{SITE_URL}/trades?{urllib.parse.urlencode(query)}"
        try:
            page_trades = extract_trades(get_html(url, args.timeout))
        except ValueError:
            if trades:
                if args.progress:
                    print(
                        f"No trade payload found on page {page}; stopping at {len(trades)} trades",
                        file=sys.stderr,
                    )
                break
            raise
        for trade in page_trades:
            tx_id = trade.get("_txId")
            if tx_id not in seen:
                seen.add(tx_id)
                trades.append(trade)
        if args.progress and ((offset + 1) % 25 == 0 or offset + 1 == args.trade_pages):
            print(
                f"Fetched {offset + 1}/{args.trade_pages} trade pages: {len(trades)} trades",
                file=sys.stderr,
            )
        if offset + 1 < args.trade_pages and args.trade_delay > 0:
            time.sleep(args.trade_delay)
    return {
        "source": f"{SITE_URL}/trades",
        "pages": args.trade_pages,
        "startPage": args.trade_start_page,
        "sort": args.trade_sort,
        "params": params,
        "count": len(trades),
        "data": trades,
    }


def load_trade_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.refresh_trades:
        return fetch_trade_pages(args)
    if not args.input:
        raise ValueError("Provide --input or use --refresh-trades")
    return json.loads(args.input.read_text(encoding="utf-8"))


def jurisdiction_sectors(label: str) -> list[str]:
    name = committee_name(label).lower()
    sectors: set[str] = set()

    def add(*values: str) -> None:
        sectors.update(values)

    if any(word in name for word in ["agriculture", "nutrition", "forestry"]):
        add("consumer-staples", "materials")
    if any(word in name for word in ["armed services", "homeland", "intelligence", "security"]):
        add("industrials", "information-technology", "communication-services")
    if any(word in name for word in ["banking", "financial", "finance", "small business"]):
        add("financials", "real-estate")
    if any(word in name for word in ["commerce", "transportation", "infrastructure"]):
        add("industrials", "consumer-discretionary", "communication-services")
    if any(word in name for word in ["energy", "natural resources", "environment", "climate"]):
        add("energy", "utilities", "materials")
    if any(word in name for word in ["health", "education", "labor", "veteran"]):
        add("health-care", "consumer-staples")
    if any(word in name for word in ["science", "space", "technology"]):
        add("information-technology", "communication-services", "industrials")
    if any(word in name for word in ["ways", "means", "tax", "budget"]):
        add("financials")
    if any(word in name for word in ["economic", "taxation"]):
        add("financials", "real-estate")
    if "security and cooperation" in name:
        add("industrials", "information-technology", "communication-services")
    if "appropriations" in name:
        add("industrials", "health-care", "information-technology", "energy")
    return sorted(sectors)


def trade_member_name(trade: dict[str, Any]) -> str:
    politician = trade.get("politician") or {}
    return (
        " ".join(
            part for part in [politician.get("firstName"), politician.get("lastName")] if part
        )
        or trade.get("_politicianId")
        or "UNKNOWN"
    )


def filter_trades(
    trades: list[dict[str, Any]],
    start_date: dt.date,
    end_date: dt.date,
    date_field: str,
    include_future_trades: bool,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    kept: list[dict[str, Any]] = []
    skipped = {"missingDate": 0, "outsideWindow": 0, "futureTxDate": 0}
    for trade in trades:
        filter_date = parse_date(trade.get(date_field))
        tx_date = parse_date(trade.get("txDate"))
        if not filter_date:
            skipped["missingDate"] += 1
            continue
        if filter_date < start_date or filter_date > end_date:
            skipped["outsideWindow"] += 1
            continue
        if tx_date and tx_date > end_date and not include_future_trades:
            skipped["futureTxDate"] += 1
            continue
        kept.append(trade)
    return kept, skipped


def percentile_score(sorted_values: list[int], value: int) -> float:
    if not sorted_values:
        return 0.0
    index = bisect.bisect_right(sorted_values, value)
    return index / len(sorted_values)


def score_row(row: dict[str, Any], amount_percentile: float) -> tuple[int, list[str]]:
    score = 0
    flags: list[str] = []
    if row["committeeSectorMatch"]:
        score += 45
        flags.append("committee-sector-overlap")

    value_score = round(amount_percentile * 25)
    score += value_score
    if amount_percentile >= 0.9:
        flags.append("top-10pct-value")
    elif amount_percentile >= 0.75:
        flags.append("top-25pct-value")

    reporting_gap = row.get("reportingGap")
    if isinstance(reporting_gap, int):
        if reporting_gap >= 180:
            score += 25
            flags.append("reporting-gap-180d-plus")
        elif reporting_gap >= 90:
            score += 20
            flags.append("reporting-gap-90d-plus")
        elif reporting_gap >= 45:
            score += 10
            flags.append("reporting-gap-45d-plus")

    repeat_count = row.get("repeat90dCount") or 0
    if repeat_count >= 3:
        score += min(15, (repeat_count - 2) * 5)
        flags.append("repeat-committee-sector-trades-90d")

    if row.get("owner") in {"spouse", "joint"}:
        score += 3
        flags.append(f"owner-{row['owner']}")

    return min(100, score), flags


def enrich_rows(
    trades: list[dict[str, Any]],
    labels: dict[str, str],
    members: dict[str, list[str]],
    score_threshold: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    member_committees: dict[str, list[str]] = defaultdict(list)
    for committee_id, politician_ids in members.items():
        for politician_id in politician_ids:
            member_committees[politician_id].append(committee_id)

    values = sorted(max(0, round(float(trade.get("value") or 0))) for trade in trades)
    raw_rows: list[dict[str, Any]] = []
    repeat_groups: dict[tuple[str, str, str], list[int]] = defaultdict(list)

    for trade in trades:
        politician_id = trade.get("_politicianId")
        if not politician_id or politician_id not in member_committees:
            continue
        tx_date = parse_date(trade.get("txDate"))
        if not tx_date:
            continue
        issuer = trade.get("issuer") or {}
        politician = trade.get("politician") or {}
        sector = issuer.get("sector") or "UNKNOWN"
        value = max(0, round(float(trade.get("value") or 0)))
        ticker = (issuer.get("issuerTicker") or "").removesuffix(":US")

        for committee_id in sorted(member_committees[politician_id]):
            label = labels.get(committee_id, committee_id)
            sectors = jurisdiction_sectors(label)
            row = {
                "tradeId": trade.get("_txId"),
                "txDate": trade.get("txDate"),
                "pubDate": trade.get("pubDate"),
                "reportingGap": trade.get("reportingGap"),
                "politicianId": politician_id,
                "politician": trade_member_name(trade),
                "party": politician.get("party"),
                "chamber": trade.get("chamber") or politician.get("chamber"),
                "state": politician.get("_stateId"),
                "committeeId": committee_id,
                "committee": committee_name(label),
                "committeeLabel": label,
                "committeeChamber": committee_chamber(label),
                "committeeJurisdictionSectors": sectors,
                "committeeSectorMatch": sector in sectors,
                "txType": trade.get("txType"),
                "owner": trade.get("owner"),
                "value": value,
                "issuerId": trade.get("_issuerId"),
                "issuerName": issuer.get("issuerName"),
                "ticker": ticker,
                "sector": sector,
                "price": trade.get("price"),
                "comment": trade.get("comment"),
                "sourceUrl": f"{SITE_URL}/trades?politician={politician_id}",
                "_txDateOrdinal": tx_date.toordinal(),
            }
            repeat_groups[(politician_id, committee_id, sector)].append(row["_txDateOrdinal"])
            raw_rows.append(row)

    for ordinals in repeat_groups.values():
        ordinals.sort()

    rows: list[dict[str, Any]] = []
    suspicious_rows: list[dict[str, Any]] = []
    for row in raw_rows:
        key = (row["politicianId"], row["committeeId"], row["sector"])
        ordinals = repeat_groups[key]
        start = row["_txDateOrdinal"] - 90
        repeat_count = bisect.bisect_right(ordinals, row["_txDateOrdinal"]) - bisect.bisect_left(
            ordinals, start
        )
        row["repeat90dCount"] = repeat_count
        amount_percentile = percentile_score(values, row["value"])
        row["valuePercentile"] = round(amount_percentile, 4)
        score, flags = score_row(row, amount_percentile)
        row["riskScore"] = score
        row["riskFlags"] = flags
        row["isSuspicious"] = score >= score_threshold
        row.pop("_txDateOrdinal", None)
        rows.append(row)
        if row["isSuspicious"]:
            suspicious_rows.append(row)

    rows.sort(key=lambda item: (-item["riskScore"], item["txDate"], item["tradeId"], item["committeeId"]))
    suspicious_rows.sort(
        key=lambda item: (-item["riskScore"], item["txDate"], item["tradeId"], item["committeeId"])
    )
    return rows, suspicious_rows


def summarize_by_committee(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_committee: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_committee[row["committeeId"]].append(row)
    summaries = []
    for committee_id, committee_rows in by_committee.items():
        suspicious = [row for row in committee_rows if row["isSuspicious"]]
        sector_counts = Counter(row["sector"] for row in suspicious)
        summaries.append(
            {
                "committeeId": committee_id,
                "committee": committee_rows[0]["committee"],
                "committeeChamber": committee_rows[0]["committeeChamber"],
                "relationshipRows": len(committee_rows),
                "suspiciousRows": len(suspicious),
                "uniquePoliticians": len({row["politicianId"] for row in committee_rows}),
                "uniqueTrades": len({row["tradeId"] for row in committee_rows}),
                "totalValue": sum(row["value"] for row in committee_rows),
                "suspiciousValue": sum(row["value"] for row in suspicious),
                "topSuspiciousSectors": [
                    {"sector": sector, "rows": count} for sector, count in sector_counts.most_common(5)
                ],
            }
        )
    return sorted(
        summaries,
        key=lambda item: (-item["suspiciousRows"], -item["suspiciousValue"], item["committee"]),
    )


def summarize_by_member(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_member: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_member[row["politicianId"]].append(row)
    summaries = []
    for politician_id, member_rows in by_member.items():
        suspicious = [row for row in member_rows if row["isSuspicious"]]
        summaries.append(
            {
                "politicianId": politician_id,
                "politician": member_rows[0]["politician"],
                "party": member_rows[0]["party"],
                "chamber": member_rows[0]["chamber"],
                "state": member_rows[0]["state"],
                "committees": sorted({row["committee"] for row in member_rows}),
                "relationshipRows": len(member_rows),
                "suspiciousRows": len(suspicious),
                "uniqueTrades": len({row["tradeId"] for row in member_rows}),
                "suspiciousValue": sum(row["value"] for row in suspicious),
                "maxRiskScore": max(row["riskScore"] for row in member_rows),
            }
        )
    return sorted(
        summaries,
        key=lambda item: (-item["suspiciousRows"], -item["suspiciousValue"], item["politician"]),
    )


def build_dataset(args: argparse.Namespace) -> dict[str, Any]:
    end_date = parse_date(args.end_date) or dt.date.today()
    start_date = parse_date(args.start_date) or subtract_years(end_date, args.years)
    if start_date > end_date:
        raise ValueError("start date must be before end date")

    payload = load_trade_payload(args)
    trades, skipped = filter_trades(
        payload["data"],
        start_date,
        end_date,
        args.date_field,
        args.include_future_trades,
    )

    labels = scrape_committee_labels(args.timeout)
    sitemap_ids = scrape_sitemap_committee_ids(args.timeout)
    for committee_id in sitemap_ids:
        if committee_id not in labels:
            labels[committee_id] = scrape_committee_page_label(committee_id, args.timeout) or committee_id

    members = scrape_committee_members(
        labels,
        args.timeout,
        args.member_delay,
        args.member_page_size,
        args.progress,
    )
    rows, suspicious_rows = enrich_rows(trades, labels, members, args.score_threshold)

    return {
        "meta": {
            "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
            "source": "Capitol Trades public rendered pages",
            "sourceUrls": {
                "trades": f"{SITE_URL}/trades",
                "politicians": f"{SITE_URL}/politicians",
                "committeesSitemap": f"{SITE_URL}/committees/sitemap.xml",
            },
            "inputTradeSource": payload.get("source"),
            "inputTradeCount": len(payload["data"]),
            "dateField": args.date_field,
            "from": start_date.isoformat(),
            "to": end_date.isoformat(),
            "years": args.years,
            "scoreThreshold": args.score_threshold,
            "tradeCountInWindow": len(trades),
            "committeeCount": len(labels),
            "committeeMemberEdges": sum(len(ids) for ids in members.values()),
            "relationshipRows": len(rows),
            "suspiciousRows": len(suspicious_rows),
            "skippedTrades": skipped,
            "note": (
                "Risk scores are heuristic flags for research triage, not allegations of "
                "wrongdoing or evidence of unlawful conduct."
            ),
        },
        "committees": [
            {
                "committeeId": committee_id,
                "label": label,
                "name": committee_name(label),
                "chamber": committee_chamber(label),
                "jurisdictionSectors": jurisdiction_sectors(label),
                "memberIds": members.get(committee_id, []),
            }
            for committee_id, label in sorted(labels.items())
        ],
        "committeeSummaries": summarize_by_committee(rows),
        "memberSummaries": summarize_by_member(rows),
        "rows": rows,
        "suspiciousRows": suspicious_rows,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def csv_value(value: Any) -> Any:
    if isinstance(value, list):
        return "|".join(str(item) for item in value)
    return value


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: csv_value(row.get(field)) for field in CSV_FIELDS})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/capitoltrades_historical.json"))
    parser.add_argument("--output", type=Path, default=Path("data/capitoltrades_committee_risk_2y.json"))
    parser.add_argument("--csv-output", type=Path, default=Path("data/capitoltrades_committee_risk_2y.csv"))
    parser.add_argument("--all-csv-output", type=Path)
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument("--years", type=int, default=2)
    parser.add_argument("--start-date", help="YYYY-MM-DD lower bound; defaults to --years before end")
    parser.add_argument("--end-date", help="YYYY-MM-DD upper bound; defaults to today")
    parser.add_argument("--date-field", choices=["txDate", "pubDate"], default="txDate")
    parser.add_argument("--include-future-trades", action="store_true")
    parser.add_argument("--score-threshold", type=int, default=60)
    parser.add_argument("--member-page-size", type=int, default=100)
    parser.add_argument("--member-delay", type=float, default=0.2)
    parser.add_argument("--progress", action="store_true")
    parser.add_argument("--refresh-trades", action="store_true")
    parser.add_argument("--trade-pages", type=int, default=348)
    parser.add_argument("--trade-start-page", type=int, default=1)
    parser.add_argument("--trade-page-size", type=int, default=100)
    parser.add_argument("--trade-sort", default="-pubDate")
    parser.add_argument("--trade-delay", type=float, default=0.05)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        payload = build_dataset(args)
    except Exception as error:
        parser.error(str(error))
    write_json(args.output, payload)
    if args.csv_output:
        write_csv(args.csv_output, payload["suspiciousRows"])
    if args.all_csv_output:
        write_csv(args.all_csv_output, payload["rows"])
    print(
        f"Wrote {payload['meta']['suspiciousRows']} suspicious rows "
        f"from {payload['meta']['relationshipRows']} committee/trade relationships",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
