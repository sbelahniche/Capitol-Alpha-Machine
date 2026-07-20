#!/usr/bin/env python3
"""Run the unattended weekly data refresh, publication, and verification."""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


SITE_URL = "https://capitolalpha.app/updates/latest"
REPORT_RE = re.compile(r"Weekly report - (\d{4}-\d{2}-\d{2})")
DEFAULT_TARGET_HOUR_UTC = 8
DEFAULT_TARGET_MINUTE_UTC = 20


def run(command: list[str], repo: Path, env: dict[str, str] | None = None) -> None:
    print(f"+ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=repo, env=env, check=True)


def output(command: list[str], repo: Path) -> str:
    return subprocess.check_output(command, cwd=repo, text=True).strip()


def monday_for(value: dt.datetime) -> dt.date:
    return value.date() - dt.timedelta(days=value.weekday())


def scheduled_at(
    value: dt.datetime, hour: int, minute: int
) -> tuple[dt.date, dt.datetime]:
    monday = monday_for(value)
    scheduled = dt.datetime.combine(
        monday,
        dt.time(hour=hour, minute=minute, tzinfo=dt.timezone.utc),
    )
    return monday, scheduled


def report_date(text: str) -> dt.date | None:
    match = REPORT_RE.search(text)
    return dt.date.fromisoformat(match.group(1)) if match else None


def local_report_date(repo: Path) -> dt.date | None:
    path = repo / "updates" / "latest" / "index.html"
    if not path.exists():
        return None
    return report_date(path.read_text(encoding="utf-8"))


def live_report_date(url: str, timeout: float) -> dt.date | None:
    separator = "&" if "?" in url else "?"
    request = urllib.request.Request(
        f"{url}{separator}automation_check={int(time.time())}",
        headers={
            "Accept": "text/html,application/xhtml+xml",
            "Cache-Control": "no-cache",
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 Chrome/125.0 Safari/537.36"
            ),
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return report_date(response.read().decode("utf-8", errors="replace"))


def clean_managed_clone(repo: Path) -> None:
    status = output(["git", "status", "--porcelain", "--untracked-files=no"], repo)
    if not status:
        return
    print("Discarding incomplete generated changes in the managed automation clone.")
    run(["git", "restore", "--staged", "--worktree", "."], repo)


def sync_repository(repo: Path, managed_clone: bool) -> None:
    if not (repo / ".git").exists():
        raise RuntimeError(f"Not a Git clone: {repo}")
    if managed_clone:
        clean_managed_clone(repo)
    elif output(["git", "status", "--porcelain", "--untracked-files=no"], repo):
        raise RuntimeError("The repository has tracked changes; refusing to overwrite them.")

    run(["git", "switch", "main"], repo)
    run(["git", "fetch", "origin", "main"], repo)

    counts = output(
        ["git", "rev-list", "--left-right", "--count", "origin/main...main"], repo
    ).split()
    behind, ahead = (int(value) for value in counts)
    if ahead and not behind:
        print(f"Retrying push of {ahead} local automation commit(s).")
        run(["git", "push", "origin", "main"], repo)
    elif ahead and behind:
        if not managed_clone:
            raise RuntimeError("Local main has diverged from origin/main.")
        print("Managed clone diverged; dropping its unpublished generated commit.")
        run(["git", "reset", "--hard", "origin/main"], repo)

    run(["git", "pull", "--ff-only", "origin", "main"], repo)


def publish_latest_data(repo: Path, args: argparse.Namespace) -> None:
    command = [
        sys.executable,
        "scripts/publish_latest_data.py",
        "--incremental-pages",
        str(args.incremental_pages),
        "--timeout",
        str(args.timeout),
        "--delay",
        str(args.delay),
        "--price-delay",
        str(args.price_delay),
        "--publish",
    ]
    run(command, repo)


def verify_publication(
    url: str,
    target: dt.date,
    timeout: float,
    attempts: int,
    interval: float,
) -> None:
    last_result = "no report date"
    for attempt in range(1, attempts + 1):
        try:
            published = live_report_date(url, timeout)
            last_result = published.isoformat() if published else "no report date"
            if published and published >= target:
                print(f"Verified live weekly report {published} at {url}")
                return
        except (OSError, urllib.error.URLError) as error:
            last_result = str(error)
        print(
            f"Live verification attempt {attempt}/{attempts} is not current: {last_result}",
            flush=True,
        )
        if attempt < attempts:
            time.sleep(interval)
    raise RuntimeError(
        f"Production did not publish the {target} weekly report: {last_result}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the weekly Capitol Alpha refresh and production publication."
    )
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=Path.home() / "Library" / "Application Support" / "CapitolAlphaWeekly",
    )
    parser.add_argument("--site-url", default=SITE_URL)
    parser.add_argument("--target-hour-utc", type=int, default=DEFAULT_TARGET_HOUR_UTC)
    parser.add_argument("--target-minute-utc", type=int, default=DEFAULT_TARGET_MINUTE_UTC)
    parser.add_argument("--incremental-pages", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--delay", type=float, default=4.0)
    parser.add_argument("--price-delay", type=float, default=0.5)
    parser.add_argument("--verify-attempts", type=int, default=12)
    parser.add_argument("--verify-interval", type=float, default=15.0)
    parser.add_argument("--managed-clone", action="store_true")
    parser.add_argument("--skip-verify", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo = args.repo.expanduser().resolve()
    state_dir = args.state_dir.expanduser().resolve()
    state_dir.mkdir(parents=True, exist_ok=True)

    lock_path = state_dir / "weekly-refresh.lock"
    with lock_path.open("a+", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Another weekly refresh is already running; exiting.")
            return

        now = dt.datetime.now(dt.timezone.utc)
        monday, scheduled = scheduled_at(
            now, args.target_hour_utc, args.target_minute_utc
        )
        print(
            f"Weekly target: {monday} after {scheduled.isoformat()} "
            f"(now {now.isoformat()})",
            flush=True,
        )
        if not args.force and now < scheduled:
            print("The weekly refresh window has not opened yet.")
            return

        if args.dry_run:
            print("Dry run: schedule gate passed; no repository or network changes made.")
            return

        sync_repository(repo, args.managed_clone)

        try:
            live_date = live_report_date(args.site_url, args.timeout)
        except (OSError, urllib.error.URLError) as error:
            live_date = None
            print(f"Could not read the live report before refresh: {error}")
        if not args.force and live_date and live_date >= monday:
            print(f"Weekly report {live_date} is already live; nothing to do.")
            return

        local_date = local_report_date(repo)
        if args.force or not local_date or local_date < monday:
            publish_latest_data(repo, args)
            local_date = local_report_date(repo)
            if not local_date or local_date < monday:
                raise RuntimeError(
                    f"Refresh completed without generating the {monday} weekly report."
                )
        else:
            print(
                f"Local report {local_date} is current; retrying production deployment only."
            )

        if not args.skip_verify:
            print("Waiting for Vercel's Git deployment to publish the pushed commit.")
            verify_publication(
                args.site_url,
                monday,
                args.timeout,
                args.verify_attempts,
                args.verify_interval,
            )


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Weekly refresh failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
