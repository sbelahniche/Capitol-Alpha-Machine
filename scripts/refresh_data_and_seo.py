#!/usr/bin/env python3
"""Refresh Capitol Trades scene data and regenerate the crawlable SEO surface."""

from __future__ import annotations

import argparse
import gzip
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import capitoltrades_scrape


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PUBLIC_VOLUME_TOTAL = 2_273_000_000
DEFAULT_PUBLIC_VOLUME_SOURCE = "Capitol Trades public 3-year volume total, read 2026-06-14"


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("Expected a positive integer")
    return parsed


def non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("Expected a non-negative integer")
    return parsed


def root_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def read_json(path: Path) -> Any:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            return json.load(handle)
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def js_assignment(name: str, payload: Any) -> str:
    return f"window.{name}={json.dumps(payload, separators=(',', ':'), ensure_ascii=False)};\n"


def load_scene05(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Scene 05 input does not exist: {path}")
    payload = read_json(path)
    missing = {"meta", "events", "trades"} - set(payload)
    if missing:
        raise ValueError(f"Scene 05 input is missing required keys: {', '.join(sorted(missing))}")
    return payload


def fetch_historical(args: argparse.Namespace) -> dict[str, Any]:
    fetch_args = SimpleNamespace(
        input=None,
        pages=args.pages,
        start_page=args.start_page,
        delay=args.delay,
        sort=args.sort,
        param=[f"pageSize={args.page_size}"],
        timeout=args.timeout,
        progress=True,
        scene01_js=False,
        scene02_js=False,
        scene04_js=False,
        prototype_js=False,
        scene01_tape_limit=args.scene01_tape_limit,
    )
    return capitoltrades_scrape.fetch_trades(fetch_args)


def tx_id_key(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def trade_sort_key(trade: dict[str, Any]) -> tuple[str, str, int]:
    return (
        str(trade.get("pubDate") or ""),
        str(trade.get("txDate") or ""),
        tx_id_key(trade.get("_txId")),
    )


def merge_historical_payloads(
    args: argparse.Namespace,
    seed_payload: dict[str, Any],
    recent_payload: dict[str, Any],
    seed_path: Path,
) -> dict[str, Any]:
    rows_by_id: dict[Any, dict[str, Any]] = {}
    for trade in seed_payload.get("data", []):
        tx_id = trade.get("_txId")
        if tx_id is not None:
            rows_by_id[tx_id] = trade
    for trade in recent_payload.get("data", []):
        tx_id = trade.get("_txId")
        if tx_id is not None:
            rows_by_id[tx_id] = trade

    rows = sorted(rows_by_id.values(), key=trade_sort_key, reverse=True)
    max_records = args.pages * args.page_size
    if max_records > 0:
        rows = rows[:max_records]

    try:
        seed_label = str(seed_path.relative_to(ROOT))
    except ValueError:
        seed_label = str(seed_path)

    return {
        "source": seed_payload.get("source") or recent_payload.get("source") or "https://www.capitoltrades.com/trades",
        "pages": args.pages,
        "startPage": args.start_page,
        "sort": args.sort,
        "params": [["pageSize", str(args.page_size)]],
        "count": len(rows),
        "data": rows,
        "refresh": {
            "mode": "incremental",
            "seed": seed_label,
            "seedCount": len(seed_payload.get("data", [])),
            "recentPages": recent_payload.get("pages", 0),
            "recentCount": len(recent_payload.get("data", [])),
        },
    }


def load_incremental_historical(args: argparse.Namespace, historical_path: Path) -> dict[str, Any]:
    historical_seed = getattr(args, "historical_seed", Path("data/capitoltrades_historical_seed.json.gz"))
    seed_path = historical_path if historical_path.exists() else root_path(historical_seed)
    if not seed_path.exists():
        raise FileNotFoundError(
            f"Incremental refresh needs a cached historical payload at {historical_path} "
            f"or a seed payload at {root_path(historical_seed)}"
        )
    seed_payload = read_json(seed_path)
    if not isinstance(seed_payload.get("data"), list) or not seed_payload["data"]:
        raise ValueError(f"Historical seed does not contain trade rows: {seed_path}")
    if args.incremental_pages > 0:
        recent_args = argparse.Namespace(**vars(args))
        recent_args.pages = args.incremental_pages
        recent_payload = fetch_historical(recent_args)
    else:
        recent_payload = {"source": seed_payload.get("source"), "pages": 0, "data": []}
    return merge_historical_payloads(args, seed_payload, recent_payload, seed_path)


def load_historical(args: argparse.Namespace) -> dict[str, Any]:
    historical_path = root_path(args.historical_output)
    if args.skip_scrape:
        if not historical_path.exists():
            raise FileNotFoundError(
                f"--skip-scrape needs an existing historical payload at {historical_path}"
            )
        payload = read_json(historical_path)
    elif getattr(args, "incremental_pages", None) is not None:
        payload = load_incremental_historical(args, historical_path)
    else:
        payload = fetch_historical(args)
        write_json(historical_path, payload)
        if not isinstance(payload.get("data"), list) or not payload["data"]:
            raise ValueError("Historical payload does not contain trade rows")
        return payload
    if not args.skip_scrape:
        write_json(historical_path, payload)
    if not isinstance(payload.get("data"), list) or not payload["data"]:
        raise ValueError("Historical payload does not contain trade rows")
    return payload


def scene02_payload(payload: dict[str, Any], record_limit: int) -> dict[str, Any]:
    rows = payload["data"][:record_limit] if record_limit > 0 else payload["data"]
    return {
        **payload,
        "count": len(rows),
        "data": rows,
    }


def build_bundle(args: argparse.Namespace, payload: dict[str, Any]) -> str:
    scene01 = capitoltrades_scrape.build_scene01_data(payload, args.scene01_tape_limit)
    scene01.setdefault("meta", {})
    scene01["meta"]["publicVolumeTotal"] = args.public_volume_total
    scene01["meta"]["publicVolumeSource"] = args.public_volume_source

    scene02 = capitoltrades_scrape.build_scene02_data(
        scene02_payload(payload, args.scene02_record_limit)
    )

    scene04_args = SimpleNamespace(
        scene04_start=args.scene04_start,
        scene04_end=args.scene04_end,
        scene04_member_limit=args.scene04_member_limit,
        scene04_trade_limit=args.scene04_trade_limit,
        timeout=args.timeout,
        price_delay=args.price_delay,
        progress=True,
    )
    scene04 = capitoltrades_scrape.build_scene04_data(payload, scene04_args)
    if len(scene04["TR"]) < args.require_priced_trades:
        raise ValueError(
            f"Only {len(scene04['TR'])} priced Scene 04 disclosures were available; "
            f"required {args.require_priced_trades}."
        )
    if len(scene04["MEM"]) < args.require_priced_members:
        raise ValueError(
            f"Only {len(scene04['MEM'])} priced Scene 04 politicians were available; "
            f"required {args.require_priced_members}."
        )

    scene05 = load_scene05(root_path(args.scene05_input))

    return "".join(
        [
            js_assignment("CAPITOL_TRADES_SCENE01", scene01),
            js_assignment("CAPITOL_TRADES_SCENE02", scene02),
            js_assignment("CAPITOL_TRADES_SCENE04", scene04),
            js_assignment("CAPITOL_TRADES_SCENE05", scene05),
        ]
    )


def run_seo_generator() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "generate_seo.py")],
        cwd=ROOT,
        check=True,
    )


def run_scene03_refresh(args: argparse.Namespace, historical_path: Path) -> None:
    risk_output = root_path(args.scene03_risk_output)
    csv_output = root_path(args.scene03_csv_output)
    command = [
        sys.executable,
        str(ROOT / "scripts" / "capitoltrades_committee_risk.py"),
        "--input",
        str(historical_path),
        "--output",
        str(risk_output),
        "--csv-output",
        str(csv_output),
        "--timeout",
        str(args.timeout),
        "--member-delay",
        str(args.scene03_member_delay),
        "--progress",
    ]
    if args.scene03_end:
        command.extend(["--end-date", args.scene03_end])
    subprocess.run(command, cwd=ROOT, check=True)
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "generate_scene03.py"),
            "--input",
            str(risk_output),
            "--member-limit",
            str(args.scene03_member_limit),
        ],
        cwd=ROOT,
        check=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Refresh Capitol Trades data, rebuild scene payloads, and run SEO generation."
        )
    )
    parser.add_argument("--skip-scrape", action="store_true", help="Reuse the historical JSON file.")
    parser.add_argument("--skip-scene03", action="store_true", help="Skip committee-risk and Scene 03 generation.")
    parser.add_argument("--skip-seo", action="store_true", help="Skip crawlable SEO generation.")
    parser.add_argument("--historical-output", type=Path, default=Path("data/capitoltrades_historical.json"))
    parser.add_argument(
        "--historical-seed",
        type=Path,
        default=Path("data/capitoltrades_historical_seed.json.gz"),
        help="Compressed historical payload used when incremental refresh has no cache.",
    )
    parser.add_argument(
        "--incremental-pages",
        type=non_negative_int,
        help="Fetch only the newest N pages and merge them into cached or seeded history.",
    )
    parser.add_argument(
        "--scene03-risk-output",
        type=Path,
        default=Path("data/capitoltrades_committee_risk_2y.json"),
    )
    parser.add_argument(
        "--scene03-csv-output",
        type=Path,
        default=Path("data/capitoltrades_committee_risk_2y.csv"),
    )
    parser.add_argument("--scene05-input", type=Path, default=Path("data/scene05_real_payload.json"))
    parser.add_argument("--bundle-output", type=Path, default=Path("capitoltrades_data.js"))
    parser.add_argument("--pages", type=positive_int, default=348)
    parser.add_argument("--start-page", type=positive_int, default=1)
    parser.add_argument("--page-size", type=positive_int, default=100)
    parser.add_argument("--delay", type=float, default=1.25)
    parser.add_argument("--sort", default="-pubDate")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--scene01-tape-limit", type=positive_int, default=900)
    parser.add_argument("--scene02-record-limit", type=int, default=1800)
    parser.add_argument("--scene03-end", help="YYYY-MM-DD upper bound; defaults to today.")
    parser.add_argument("--scene03-member-limit", type=positive_int, default=40)
    parser.add_argument("--scene03-member-delay", type=float, default=0.75)
    parser.add_argument("--scene04-start", default="2023-06-01")
    parser.add_argument("--scene04-end")
    parser.add_argument("--scene04-member-limit", type=int, default=60)
    parser.add_argument("--scene04-trade-limit", type=int, default=6000)
    parser.add_argument("--price-delay", type=float, default=0.15)
    parser.add_argument("--require-priced-trades", type=int, default=1500)
    parser.add_argument("--require-priced-members", type=int, default=25)
    parser.add_argument("--public-volume-total", type=int, default=DEFAULT_PUBLIC_VOLUME_TOTAL)
    parser.add_argument("--public-volume-source", default=DEFAULT_PUBLIC_VOLUME_SOURCE)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = load_historical(args)
    bundle = build_bundle(args, payload)
    bundle_path = root_path(args.bundle_output)
    bundle_path.write_text(bundle, encoding="utf-8")
    print(f"Wrote {bundle_path.relative_to(ROOT)}")
    if not args.skip_scene03:
        run_scene03_refresh(args, root_path(args.historical_output))
    if not args.skip_seo:
        run_seo_generator()


if __name__ == "__main__":
    main()
