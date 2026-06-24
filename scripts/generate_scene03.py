#!/usr/bin/env python3
"""Generate the compact Exposure Index payload from committee-risk data."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SECTORS = [
    "communication-services",
    "consumer-discretionary",
    "consumer-staples",
    "energy",
    "financials",
    "health-care",
    "industrials",
    "information-technology",
    "materials",
    "real-estate",
    "utilities",
]
SECTOR_CODES = ["COMM", "DISC", "STPL", "ENGY", "FIN", "HLTH", "INDU", "TECH", "MATL", "RE", "UTIL"]
COMMITTEE_CODES = {
    "Aging": "AGING",
    "Agriculture": "AGRIC",
    "Agriculture, Nutrition & Forestry": "AGNUTR",
    "Appropriations": "APPROP",
    "Armed Services": "ARMSVC",
    "Banking, Housing & Urban Affairs": "BANKNG",
    "Budget": "BUDGET",
    "Commission on Security and Cooperation in Europe": "CSCE",
    "Commerce, Science & Transportation": "COMMSC",
    "Education & Labor": "EDLABR",
    "Energy & Commerce": "E&COMM",
    "Energy & Natural Resources": "ENRGNR",
    "Environment & Public Works": "ENVPW",
    "Finance": "FINANC",
    "Financial Services": "FINSVC",
    "Foreign Affairs": "FORAFF",
    "Foreign Relations": "FORREL",
    "Health, Education, Labor & Pensions": "HELP",
    "Homeland Security": "HMLAND",
    "Homeland Security & Gov. Affairs": "HMLAND",
    "House Administration": "HSEADM",
    "Indian Affairs": "INDAFF",
    "Intelligence": "INTEL",
    "International Narcotics Control": "NARCO",
    "Joint Committee on Printing": "JTPRNT",
    "Joint Committee on Taxation": "JTAX",
    "Joint Committee on the Library": "JTLIB",
    "Joint Economic Committee": "JEC",
    "Judiciary": "JUDIC",
    "Natural Resources": "NATRES",
    "Oversight and Reform": "OVRSGT",
    "Rules and Administration": "RULES",
    "Science, Space and Technology": "SCITEC",
    "Small business": "SMLBIZ",
    "Small Business & Entrepreneurship": "SMLBIZ",
    "Strategic Competition between US and CCP": "CCP",
    "Transportation & Infrastructure": "TRANSP",
    "Veteran’s Affairs": "VETAFF",
    "Ways & Means": "W&MEANS",
}


def root_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def committee_code(name: str) -> str:
    if name in COMMITTEE_CODES:
        return COMMITTEE_CODES[name]
    words = [
        word
        for word in name.replace("&", " ").replace("’", "").replace("'", "").split()
        if word.lower() not in {"and", "on", "the", "of"}
    ]
    initials = "".join(word[0] for word in words if word)
    return (initials or name.replace(" ", ""))[:7].upper()


def party_code(value: str | None) -> str:
    return {
        "democrat": "D",
        "republican": "R",
        "independent": "I",
        "D": "D",
        "R": "R",
        "I": "I",
    }.get(value or "", "?")


def chamber_code(value: str | None) -> str:
    return {
        "house": "H",
        "senate": "S",
        "H": "H",
        "S": "S",
    }.get(value or "", "?")


def member_rank(summary: dict[str, Any]) -> tuple[Any, ...]:
    return (
        -int(summary.get("maxRiskScore") or 0),
        -int(summary.get("suspiciousRows") or 0),
        -int(summary.get("suspiciousValue") or 0),
        str(summary.get("politician") or ""),
    )


def build_member(
    summary: dict[str, Any],
    rows: list[dict[str, Any]],
    committee_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    committee_ids = sorted(
        {row["committeeId"] for row in rows},
        key=lambda committee_id: (
            not bool(committee_lookup[committee_id]["jurisdictionSectors"]),
            -len(committee_lookup[committee_id]["jurisdictionSectors"]),
            committee_lookup[committee_id]["name"],
        ),
    )
    committees = []
    for committee_id in committee_ids:
        committee = committee_lookup[committee_id]
        jurisdictions = set(committee["jurisdictionSectors"])
        committees.append(
            {
                "c": committee_code(committee["name"]),
                "n": committee["name"],
                "j": [int(sector in jurisdictions) for sector in SECTORS],
            }
        )

    unique_trades: dict[Any, dict[str, Any]] = {}
    for row in rows:
        unique_trades.setdefault(row["tradeId"], row)

    counts = [0] * len(SECTORS)
    values = [0] * len(SECTORS)
    for row in unique_trades.values():
        sector = row.get("sector")
        if sector not in SECTORS:
            continue
        sector_index = SECTORS.index(sector)
        counts[sector_index] += 1
        values[sector_index] += int(row.get("value") or 0)

    response = []
    for sector_index, sector in enumerate(SECTORS):
        committee_index = next(
            (
                index
                for index, committee_id in enumerate(committee_ids)
                if sector in committee_lookup[committee_id]["jurisdictionSectors"]
            ),
            -1,
        )
        response.append(committee_index if counts[sector_index] else -1)
    locks = [int(response[index] >= 0) for index in range(len(SECTORS))]

    worst = rows[0]
    worst_sector = worst["sector"]
    worst_sector_index = SECTORS.index(worst_sector)
    worst_committee_index = committee_ids.index(worst["committeeId"])

    return {
        "name": summary["politician"],
        "party": party_code(summary.get("party")),
        "chamber": chamber_code(summary.get("chamber")),
        "state": str(summary.get("state") or "").upper(),
        "coms": committees,
        "jur": [int(any(committee["j"][index] for committee in committees)) for index in range(len(SECTORS))],
        "cnt": counts,
        "val": values,
        "lock": locks,
        "resp": response,
        "nlock": sum(locks),
        "riskMax": int(summary["maxRiskScore"]),
        "conflictVal": sum(values[index] for index, locked in enumerate(locks) if locked),
        "trades": len(unique_trades),
        "worst": {
            "ticker": worst.get("ticker") or "N/A",
            "issuer": worst.get("issuerName") or "Unknown issuer",
            "sector": SECTOR_CODES[worst_sector_index],
            "si": worst_sector_index,
            "ci": worst_committee_index,
            "value": int(worst.get("value") or 0),
            "side": str(worst.get("txType") or "unknown").upper(),
            "txDate": str(worst.get("txDate") or "")[:10],
            "pub": str(worst.get("pubDate") or "")[:10],
            "gap": int(worst.get("reportingGap") or 0),
            "rep": int(worst.get("repeat90dCount") or 0),
            "risk": int(worst.get("riskScore") or 0),
            "committee": worst["committee"],
            "flags": worst.get("riskFlags") or [],
        },
    }


def build_scene_payload(dataset: dict[str, Any], member_limit: int) -> dict[str, Any]:
    committee_lookup = {
        committee["committeeId"]: committee for committee in dataset["committees"]
    }
    rows_by_member: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in dataset["rows"]:
        rows_by_member[row["politicianId"]].append(row)

    summaries = sorted(dataset["memberSummaries"], key=member_rank)[:member_limit]
    members = [
        build_member(summary, rows_by_member[summary["politicianId"]], committee_lookup)
        for summary in summaries
    ]
    meta = dataset["meta"]
    return {
        "sectors": SECTORS,
        "codes": SECTOR_CODES,
        "members": members,
        "meta": {
            "window": f"{meta['from']} / {meta['to']}",
            "note": "Triage heuristic. Not an allegation of unlawful conduct.",
            "nPol": len(dataset["memberSummaries"]),
            "nTrades": int(meta["tradeCountInWindow"]),
            "generatedAt": meta["generatedAt"],
        },
    }


def replace_prototype_data(path: Path, payload: dict[str, Any]) -> str:
    content = path.read_text(encoding="utf-8")
    marker = "const DATA = "
    json_start = content.index(marker) + len(marker)
    _, consumed = json.JSONDecoder().raw_decode(content[json_start:])
    json_end = json_start + consumed
    compact = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    updated = content[:json_start] + compact + content[json_end:]
    path.write_text(updated, encoding="utf-8")
    return updated


def replace_index_scene(path: Path, scene_html: str) -> None:
    content = path.read_text(encoding="utf-8")
    opening = '<script id="scene03-html" type="application/json">'
    start = content.index(opening) + len(opening)
    end = content.index("</script>", start)
    encoded = json.dumps(scene_html, ensure_ascii=True).replace("</", r"<\/")
    path.write_text(content[:start] + encoded + content[end:], encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Scene 03 Exposure Index data and embed it in the site."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/capitoltrades_committee_risk_2y.json"),
    )
    parser.add_argument(
        "--prototype",
        type=Path,
        default=Path("prototypes/scene03_exposure_index.html"),
    )
    parser.add_argument("--index", type=Path, default=Path("index.html"))
    parser.add_argument("--member-limit", type=int, default=40)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = root_path(args.input)
    prototype_path = root_path(args.prototype)
    index_path = root_path(args.index)
    dataset = json.loads(input_path.read_text(encoding="utf-8"))
    payload = build_scene_payload(dataset, args.member_limit)
    scene_html = replace_prototype_data(prototype_path, payload)
    replace_index_scene(index_path, scene_html)
    print(
        f"Generated Scene 03 with {len(payload['members'])} members, "
        f"{payload['meta']['nTrades']:,} trades, and window {payload['meta']['window']}"
    )


if __name__ == "__main__":
    main()
