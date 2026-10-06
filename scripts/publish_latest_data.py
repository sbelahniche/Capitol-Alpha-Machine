#!/usr/bin/env python3
"""Fetch updated Capitol Trades data locally, validate, and optionally publish."""

from __future__ import annotations

import argparse
import gzip
import json
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_JSON = ROOT / "data" / "capitoltrades_historical.json"
HISTORICAL_SEED = ROOT / "data" / "capitoltrades_historical_seed.json.gz"

GENERATED_PATHS = [
    "capitoltrades_data.js",
    "index.html",
    "robots.txt",
    "sitemap.xml",
    "sitemap.txt",
    "rss.xml",
    "og-image.svg",
    "og-image.png",
    "prototypes/scene03_exposure_index.html",
    "methodology/index.html",
    "data/index.html",
    "datasets/committee-risk/index.html",
    "updates/latest/index.html",
    "faq/index.html",
]


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("Expected a positive integer")
    return parsed


def non_negative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("Expected a non-negative number")
    return parsed


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print(f"+ {shlex.join(command)}", file=sys.stderr)
    return subprocess.run(
        command,
        cwd=ROOT,
        check=check,
        text=True,
    )


def git_output(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def ensure_clean_worktree() -> None:
    status = git_output(["status", "--porcelain"])
    if status:
        raise SystemExit(
            "Working tree has existing tracked changes. Commit, stash, or rerun with "
            "--allow-dirty if you intentionally want to refresh on top of them.\n"
            f"{status}"
        )


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def historical_summary() -> str:
    if not HISTORICAL_JSON.exists():
        return "Historical cache missing"
    payload = load_json(HISTORICAL_JSON)
    rows = payload.get("data", [])
    pub_dates = sorted((row.get("pubDate") or "")[:10] for row in rows if row.get("pubDate"))
    tx_dates = sorted((row.get("txDate") or "")[:10] for row in rows if row.get("txDate"))
    return (
        f"{len(rows):,} disclosures; "
        f"pubDate through {pub_dates[-1] if pub_dates else 'n/a'}; "
        f"txDate through {tx_dates[-1] if tx_dates else 'n/a'}"
    )


def write_seed() -> None:
    if not HISTORICAL_JSON.exists():
        raise FileNotFoundError(f"Missing historical cache: {HISTORICAL_JSON}")
    HISTORICAL_SEED.parent.mkdir(parents=True, exist_ok=True)
    with HISTORICAL_JSON.open("rb") as source, HISTORICAL_SEED.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as target:
            shutil.copyfileobj(source, target)
    print(
        f"Updated {HISTORICAL_SEED.relative_to(ROOT)} "
        f"({HISTORICAL_SEED.stat().st_size:,} bytes)",
        file=sys.stderr,
    )


def generated_files(include_seed: bool) -> list[str]:
    paths = [path for path in GENERATED_PATHS if (ROOT / path).exists()]
    paths.extend(str(path.relative_to(ROOT)) for path in sorted((ROOT / "scenes").glob("*/index.html")))
    for directory in ('preview', 'previews'):
        paths.extend(str(path.relative_to(ROOT)) for path in sorted((ROOT / 'screensavers' / directory).glob('*.html')))
    if (ROOT / 'screensavers/index.html').exists():
        paths.append('screensavers/index.html')
    if include_seed and HISTORICAL_SEED.exists():
        paths.append(str(HISTORICAL_SEED.relative_to(ROOT)))
    return sorted(dict.fromkeys(paths))


def refresh_command(args: argparse.Namespace) -> list[str]:
    command = [
        sys.executable,
        "scripts/refresh_data_and_seo.py",
        "--incremental-pages",
        str(args.incremental_pages),
        "--timeout",
        str(args.timeout),
        "--delay",
        str(args.delay),
        "--scene03-member-delay",
        str(args.scene03_member_delay),
        "--price-delay",
        str(args.price_delay),
    ]
    if not args.refresh_scene03:
        command.append("--skip-scene03")
    if not args.refresh_scene04:
        command.append("--reuse-scene04")
    return command


def publish(args: argparse.Namespace, include_seed: bool) -> None:
    paths = generated_files(include_seed)
    if not paths:
        raise SystemExit("No generated files found to stage.")
    run(["git", "add", *paths])
    if run(["git", "diff", "--cached", "--quiet"], check=False).returncode == 0:
        print("No generated changes to commit.", file=sys.stderr)
        return
    run(["git", "commit", "-m", args.message])
    if args.push:
        run(["git", "push", "origin", "main"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Local Capitol Trades refresh path. Use this from a network that can reach "
            "capitoltrades.com when GitHub-hosted runners are rate-limited."
        )
    )
    parser.add_argument("--incremental-pages", type=positive_int, default=10)
    parser.add_argument("--timeout", type=non_negative_float, default=30.0)
    parser.add_argument("--delay", type=non_negative_float, default=2.0)
    parser.add_argument("--scene03-member-delay", type=non_negative_float, default=2.0)
    parser.add_argument("--price-delay", type=non_negative_float, default=0.5)
    parser.add_argument(
        "--refresh-scene03",
        action="store_true",
        help="Also refresh the heavy committee-risk Scene 3 dataset.",
    )
    parser.add_argument(
        "--refresh-scene04",
        action="store_true",
        help="Also refresh the rate-limit-sensitive Scene 04 price dataset.",
    )
    parser.add_argument(
        "--no-update-seed",
        action="store_true",
        help="Do not refresh data/capitoltrades_historical_seed.json.gz.",
    )
    parser.add_argument("--publish", action="store_true", help="Commit refreshed outputs.")
    parser.add_argument(
        "--push",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Push after committing with --publish.",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Refresh even if tracked files already have local changes.",
    )
    parser.add_argument(
        "--message",
        default="Refresh Capitol Trades data and SEO pages",
        help="Commit message used with --publish.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.allow_dirty:
        ensure_clean_worktree()
    print(f"Before refresh: {historical_summary()}", file=sys.stderr)
    run(refresh_command(args))
    if not args.no_update_seed:
        write_seed()
    run([sys.executable, "scripts/validate_static_site.py"])
    print(f"After refresh: {historical_summary()}", file=sys.stderr)
    if args.publish:
        publish(args, include_seed=not args.no_update_seed)


if __name__ == "__main__":
    main()
