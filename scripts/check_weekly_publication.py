#!/usr/bin/env python3
"""Check that the live weekly report matches the current Monday."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
import time
import urllib.error
import urllib.request


REPORT_RE = re.compile(r"Weekly report - (\d{4}-\d{2}-\d{2})")


def current_monday() -> dt.date:
    today = dt.datetime.now(dt.timezone.utc).date()
    return today - dt.timedelta(days=today.weekday())


def fetch_report_date(url: str, timeout: float) -> dt.date | None:
    separator = "&" if "?" in url else "?"
    request = urllib.request.Request(
        f"{url}{separator}weekly_check={int(time.time())}",
        headers={
            "Accept": "text/html,application/xhtml+xml",
            "Cache-Control": "no-cache",
            "User-Agent": "CapitolAlphaWeeklyMonitor/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        text = response.read().decode("utf-8", errors="replace")
    match = REPORT_RE.search(text)
    return dt.date.fromisoformat(match.group(1)) if match else None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="https://capitolalpha.app/updates/latest")
    parser.add_argument("--attempts", type=int, default=1)
    parser.add_argument("--interval", type=float, default=300.0)
    parser.add_argument("--timeout", type=float, default=20.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    target = current_monday()
    last_result = "no response"
    for attempt in range(1, args.attempts + 1):
        try:
            published = fetch_report_date(args.url, args.timeout)
            last_result = published.isoformat() if published else "no report date found"
            if published and published >= target:
                print(f"Weekly report {published} matches current Monday {target}.")
                return
        except (OSError, urllib.error.URLError) as error:
            last_result = str(error)
        print(
            f"Attempt {attempt}/{args.attempts}: expected {target}, found {last_result}.",
            flush=True,
        )
        if attempt < args.attempts:
            time.sleep(args.interval)
    raise SystemExit(
        f"Weekly publication is stale: expected {target}, found {last_result}."
    )


if __name__ == "__main__":
    main()
