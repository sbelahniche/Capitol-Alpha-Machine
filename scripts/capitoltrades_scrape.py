#!/usr/bin/env python3
"""Fetch recent Capitol Trades data from the site's public browser surface."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from bisect import bisect_left
from pathlib import Path
from typing import Any

SITE_URL = "https://www.capitoltrades.com"
BFF_URL = "https://bff.capitoltrades.com"
NEXT_CHUNK_RE = re.compile(
    r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', re.DOTALL
)
DEFAULT_HEADERS = {
    "Accept-Language": "en-US,en;q=0.9",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
}


def urlopen_with_retries(
    url: str, timeout: float, accept: str, attempts: int = 5
) -> Any:
    for attempt in range(attempts):
        request = urllib.request.Request(
            url,
            headers={
                **DEFAULT_HEADERS,
                "Accept": accept,
            },
        )
        try:
            return urllib.request.urlopen(request, timeout=timeout)
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt + 1 >= attempts:
                raise
            retry_after = error.headers.get("Retry-After")
            delay = float(retry_after) if retry_after and retry_after.isdigit() else 5 * (attempt + 1)
            time.sleep(min(delay, 60))
        except urllib.error.URLError:
            if attempt + 1 >= attempts:
                raise
            time.sleep(min(2 * (attempt + 1), 20))


def get_json(url: str, timeout: float) -> Any:
    with urlopen_with_retries(url, timeout, "application/json") as response:
        return json.load(response)


def get_html(url: str, timeout: float) -> str:
    with urlopen_with_retries(url, timeout, "text/html,application/xhtml+xml") as response:
        return response.read().decode("utf-8")


def extract_trades(html: str) -> list[dict[str, Any]]:
    for raw_chunk in NEXT_CHUNK_RE.findall(html):
        chunk = json.loads(f'"{raw_chunk}"')
        marker = '"data":['
        if marker not in chunk or '"_txId"' not in chunk:
            continue
        start = chunk.index("[", chunk.index(marker))
        trades, _ = json.JSONDecoder().raw_decode(chunk[start:])
        if trades and isinstance(trades, list) and "_txId" in trades[0]:
            return trades
    raise ValueError("Could not find structured trade data in the rendered page")


def parse_extra_params(values: list[str]) -> list[tuple[str, str]]:
    params: list[tuple[str, str]] = []
    for value in values:
        if "=" not in value:
            raise ValueError(f"Expected KEY=VALUE for --param, got: {value}")
        params.append(tuple(value.split("=", 1)))
    return params


def fetch_trades(args: argparse.Namespace) -> dict[str, Any]:
    if args.input:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        trades = payload["data"]
    else:
        extra_params = parse_extra_params(args.param)
        seen: set[int] = set()
        trades: list[dict[str, Any]] = []

        for offset in range(args.pages):
            page = args.start_page + offset
            query = [("page", str(page)), ("sort", args.sort), *extra_params]
            url = f"{SITE_URL}/trades?{urllib.parse.urlencode(query)}"
            page_trades = extract_trades(get_html(url, args.timeout))
            for trade in page_trades:
                tx_id = trade["_txId"]
                if tx_id not in seen:
                    seen.add(tx_id)
                    trades.append(trade)
            if args.progress and ((offset + 1) % 25 == 0 or offset + 1 == args.pages):
                print(
                    f"Fetched {offset + 1}/{args.pages} trade pages: {len(trades)} disclosures",
                    file=sys.stderr,
                )
            if offset + 1 < args.pages:
                time.sleep(args.delay)

        payload = {
            "source": f"{SITE_URL}/trades",
            "pages": args.pages,
            "startPage": args.start_page,
            "sort": args.sort,
            "params": extra_params,
            "count": len(trades),
            "data": trades,
        }
    if args.scene01_js:
        return build_scene01_data(payload, args.scene01_tape_limit)
    if args.scene04_js:
        return build_scene04_data(payload, args)
    if args.prototype_js:
        scene04 = build_scene04_data(payload, args)
        if len(scene04["TR"]) < args.require_priced_trades:
            raise ValueError(
                f"Only {len(scene04['TR'])} priced disclosures were available; "
                f"required {args.require_priced_trades}. Increase --pages."
            )
        if len(scene04["MEM"]) < args.require_priced_members:
            raise ValueError(
                f"Only {len(scene04['MEM'])} priced politicians were available; "
                f"required {args.require_priced_members}. Increase --pages."
            )
        return {
            "CAPITOL_TRADES_SCENE02": build_scene02_data(payload),
            "CAPITOL_TRADES_SCENE04": scene04,
        }
    return build_scene02_data(payload) if args.scene02_js else payload


def build_scene01_data(payload: dict[str, Any], tape_limit: int = 900) -> dict[str, Any]:
    trades = payload["data"]
    if not trades:
        raise ValueError("No trades were returned")

    signed_rows: list[tuple[dt.date, int, bool]] = []
    skipped_types: dict[str, int] = {}
    skipped_anomalous_dates = 0
    for trade in trades:
        tx_type = (trade.get("txType") or "").lower()
        if tx_type == "buy":
            sign = 1
        elif tx_type == "sell":
            sign = -1
        else:
            skipped_types[tx_type or "unknown"] = skipped_types.get(tx_type or "unknown", 0) + 1
            continue
        try:
            tx_date = dt.date.fromisoformat(trade["txDate"])
        except (KeyError, ValueError):
            continue
        pub_date_value = (trade.get("pubDate") or "")[:10]
        if pub_date_value:
            try:
                pub_date = dt.date.fromisoformat(pub_date_value)
            except ValueError:
                pub_date = None
            if pub_date and tx_date > pub_date:
                skipped_anomalous_dates += 1
                continue
        amount = max(0, round(float(trade.get("value") or 0)))
        if amount <= 0:
            continue
        signed_rows.append((tx_date, sign * amount, sign > 0))

    if not signed_rows:
        raise ValueError("No buy/sell trades with positive disclosed values were available")

    first_date = min(row[0] for row in signed_rows)
    last_date = max(row[0] for row in signed_rows)
    first_week = first_date - dt.timedelta(days=first_date.weekday())
    last_week = last_date - dt.timedelta(days=last_date.weekday())

    weekly: dict[dt.date, dict[str, int]] = {}
    for tx_date, signed_amount, _buy in signed_rows:
        week = tx_date - dt.timedelta(days=tx_date.weekday())
        bucket = weekly.setdefault(week, {"net": 0, "gross": 0, "buy": 0, "sell": 0})
        amount = abs(signed_amount)
        bucket["net"] += signed_amount
        bucket["gross"] += amount
        if signed_amount > 0:
            bucket["buy"] += amount
        else:
            bucket["sell"] += amount

    weeks: list[dict[str, Any]] = []
    cum = 0
    max_abs = 0
    max_gross = 0
    total_gross = 0
    total_buy = 0
    total_sell = 0
    week = first_week
    index = 0
    while week <= last_week:
        bucket = weekly.get(week, {"net": 0, "gross": 0, "buy": 0, "sell": 0})
        net = bucket["net"]
        gross = bucket["gross"]
        buy = bucket["buy"]
        sell = bucket["sell"]
        cum += net
        max_abs = max(max_abs, abs(net))
        max_gross = max(max_gross, gross)
        total_gross += gross
        total_buy += buy
        total_sell += sell
        weeks.append(
            {
                "i": index,
                "t": round(
                    dt.datetime.combine(week, dt.time(), tzinfo=dt.timezone.utc).timestamp()
                    * 1000
                ),
                "net": net,
                "gross": gross,
                "buy": buy,
                "sell": sell,
                "cum": cum,
            }
        )
        index += 1
        week += dt.timedelta(days=7)

    cums = [row["cum"] for row in weeks]
    tape_rows = sorted(signed_rows, key=lambda row: row[0])
    if tape_limit > 0 and len(tape_rows) > tape_limit:
        step = len(tape_rows) / tape_limit
        tape_rows = [tape_rows[int(i * step)] for i in range(tape_limit)]

    return {
        "meta": {
            "from": first_date.isoformat(),
            "to": last_date.isoformat(),
            "source": "CAPITOL TRADES",
            "pages": payload.get("pages"),
            "count": len(trades),
            "buySellCount": len(signed_rows),
            "valueBasis": "disclosed value; gross volume sums buys and sells; net flow uses buys positive and sells negative",
            "skippedTypes": skipped_types,
            "skippedAnomalousDates": skipped_anomalous_dates,
            "totalGross": total_gross,
            "totalBuy": total_buy,
            "totalSell": total_sell,
        },
        "weeks": weeks,
        "N": len(weeks),
        "minCum": min(cums),
        "maxCum": max(cums),
        "maxAbs": max_abs or 1,
        "maxGross": max_gross or 1,
        "trades": [{"buy": buy, "amt": abs(amount)} for _date, amount, buy in tape_rows],
    }


def build_scene02_data(payload: dict[str, Any]) -> dict[str, Any]:
    trades = payload["data"]
    if not trades:
        raise ValueError("No trades were returned")

    def unique_index(values: list[str], value: str) -> int:
        try:
            return values.index(value)
        except ValueError:
            values.append(value)
            return len(values) - 1

    dates = [dt.date.fromisoformat(trade["txDate"]) for trade in trades]
    first_date = min(dates)
    last_date = max(dates)
    amounts: list[int] = []
    tickers: list[str] = []
    members: list[str] = []
    rows: list[list[int]] = []
    for trade, trade_date in sorted(zip(trades, dates), key=lambda item: item[1]):
        issuer = trade.get("issuer") or {}
        politician = trade.get("politician") or {}
        ticker = (issuer.get("issuerTicker") or issuer.get("issuerName") or "UNKNOWN")
        ticker = ticker.removesuffix(":US")
        member = " ".join(
            part for part in [politician.get("firstName"), politician.get("lastName")] if part
        ).upper() or trade.get("_politicianId", "UNKNOWN")
        amount = max(0, round(float(trade.get("value") or 0)))
        rows.append(
            [
                (trade_date - first_date).days,
                unique_index(tickers, ticker),
                1 if trade.get("txType") == "buy" else 0,
                unique_index(amounts, amount),
                unique_index(members, member),
            ]
        )

    return {
        "meta": {
            "minMs": round(
                dt.datetime.combine(first_date, dt.time(), tzinfo=dt.timezone.utc).timestamp()
                * 1000
            ),
            "from": first_date.isoformat(),
            "to": last_date.isoformat(),
            "source": "CAPITOL TRADES",
        },
        "AMT": amounts,
        "TICK": tickers,
        "MEM": members,
        "TR": rows,
    }


def search_issuer(query: str, timeout: float) -> list[dict[str, Any]]:
    encoded = urllib.parse.urlencode({"search": query})
    return get_json(f"{BFF_URL}/issuers?{encoded}", timeout).get("data", [])


def price_series(
    issuers: list[dict[str, Any]], ticker: str
) -> list[tuple[dt.date, float]]:
    ticker_upper = ticker.upper()
    for issuer in issuers:
        issuer_ticker = (issuer.get("issuerTicker") or "").removesuffix(":US").upper()
        if issuer_ticker != ticker_upper:
            continue
        prices = (issuer.get("performance") or {}).get("eodPrices") or []
        return sorted((dt.date.fromisoformat(day), float(price)) for day, price in prices)
    return []


def issuer_performance(
    issuers: list[dict[str, Any]], ticker: str
) -> dict[str, Any] | None:
    ticker_upper = ticker.upper()
    for issuer in issuers:
        issuer_ticker = (issuer.get("issuerTicker") or "").removesuffix(":US").upper()
        if issuer_ticker == ticker_upper:
            return issuer.get("performance")
    return None


def forward_return(
    prices: list[tuple[dt.date, float]], trade_date: dt.date, days: int = 90
) -> float | None:
    if not prices:
        return None
    dates = [row[0] for row in prices]
    start_index = bisect_left(dates, trade_date)
    end_index = bisect_left(dates, trade_date + dt.timedelta(days=days))
    if start_index >= len(prices) or end_index >= len(prices):
        return None
    start_price = prices[start_index][1]
    end_price = prices[end_index][1]
    return (end_price / start_price) - 1 if start_price else None


def date_arg(value: str | None) -> dt.date | None:
    return dt.date.fromisoformat(value) if value else None


def select_scene04_trades(
    trades: list[dict[str, Any]], args: argparse.Namespace
) -> list[dict[str, Any]]:
    start_date = date_arg(args.scene04_start)
    end_date = date_arg(args.scene04_end)
    rows: list[tuple[dt.date, dict[str, Any]]] = []
    for trade in trades:
        issuer = trade.get("issuer") or {}
        ticker = (issuer.get("issuerTicker") or "").removesuffix(":US")
        if not ticker:
            continue
        tx_type = (trade.get("txType") or "").lower()
        if tx_type not in {"buy", "sell"}:
            continue
        try:
            trade_date = dt.date.fromisoformat(trade["txDate"])
        except (KeyError, ValueError):
            continue
        if start_date and trade_date < start_date:
            continue
        if end_date and trade_date > end_date:
            continue
        if max(0, round(float(trade.get("value") or 0))) <= 0:
            continue
        rows.append((trade_date, trade))

    if args.scene04_member_limit > 0:
        counts: dict[str, int] = {}
        for _trade_date, trade in rows:
            politician = trade.get("politician") or {}
            member = " ".join(
                part for part in [politician.get("firstName"), politician.get("lastName")] if part
            ).upper() or trade.get("_politicianId", "UNKNOWN")
            counts[member] = counts.get(member, 0) + 1
        allowed = {
            name
            for name, _count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[
                : args.scene04_member_limit
            ]
        }
        rows = [
            (trade_date, trade)
            for trade_date, trade in rows
            if (
                " ".join(
                    part
                    for part in [
                        (trade.get("politician") or {}).get("firstName"),
                        (trade.get("politician") or {}).get("lastName"),
                    ]
                    if part
                ).upper()
                or trade.get("_politicianId", "UNKNOWN")
            )
            in allowed
        ]

    rows.sort(key=lambda item: (item[0], item[1].get("_txId", 0)))
    if args.scene04_trade_limit > 0 and len(rows) > args.scene04_trade_limit:
        by_month: dict[str, list[tuple[dt.date, dict[str, Any]]]] = {}
        for row in rows:
            by_month.setdefault(row[0].isoformat()[:7], []).append(row)
        months = sorted(by_month)
        quota = max(1, args.scene04_trade_limit // max(1, len(months)))
        selected: list[tuple[dt.date, dict[str, Any]]] = []
        leftovers: list[tuple[dt.date, dict[str, Any]]] = []
        for month in months:
            month_rows = sorted(
                by_month[month],
                key=lambda item: (
                    -float(item[1].get("value") or 0),
                    item[0],
                    item[1].get("_txId", 0),
                ),
            )
            selected.extend(month_rows[:quota])
            leftovers.extend(month_rows[quota:])
        remaining = args.scene04_trade_limit - len(selected)
        if remaining > 0 and leftovers:
            leftovers.sort(key=lambda item: (item[0], item[1].get("_txId", 0)))
            step = len(leftovers) / remaining
            selected.extend(leftovers[int(i * step)] for i in range(remaining))
        rows = sorted(selected[: args.scene04_trade_limit], key=lambda item: (item[0], item[1].get("_txId", 0)))

    return [trade for _trade_date, trade in rows]


def build_scene04_data(payload: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    scene_trades = select_scene04_trades(payload["data"], args)
    if not scene_trades:
        raise ValueError("No Scene 04 trades matched the requested filters")

    spy_issuers = search_issuer("SPY", args.timeout)
    spy_performance = issuer_performance(spy_issuers, "SPY") or {}
    spy_trailing90 = spy_performance.get("trailing90Change")
    if spy_trailing90 is None:
        raise ValueError("Could not fetch SPY trailing-90-day performance for Scene 04")

    ticker_performance: dict[str, dict[str, Any] | None] = {}
    for trade in scene_trades:
        ticker = ((trade.get("issuer") or {}).get("issuerTicker") or "").removesuffix(":US")
        if not ticker or ticker in ticker_performance:
            continue
        try:
            ticker_performance[ticker] = issuer_performance(
                search_issuer(ticker, args.timeout), ticker
            )
        except urllib.error.URLError:
            ticker_performance[ticker] = None
        if args.progress and len(ticker_performance) % 50 == 0:
            print(
                f"Priced {len(ticker_performance)} issuer tickers",
                file=sys.stderr,
            )
        time.sleep(args.price_delay)

    members: list[str] = []
    tickers: list[str] = []
    rows: list[dict[str, Any]] = []
    for trade in scene_trades:
        issuer = trade.get("issuer") or {}
        politician = trade.get("politician") or {}
        ticker = (issuer.get("issuerTicker") or "").removesuffix(":US")
        performance = ticker_performance.get(ticker) or {}
        ret90 = performance.get("trailing90Change")
        market = spy_trailing90
        if not ticker or ret90 is None:
            continue
        member = " ".join(
            part for part in [politician.get("firstName"), politician.get("lastName")] if part
        ).upper() or trade.get("_politicianId", "UNKNOWN")
        if member not in members:
            members.append(member)
        if ticker not in tickers:
            tickers.append(ticker)
        excess = ret90 - market
        amount = max(0, round(float(trade.get("value") or 0)))
        rows.append(
            {
                "member": members.index(member),
                "ticker": tickers.index(ticker),
                "date": trade["txDate"],
                "amount": amount,
                "buy": trade.get("txType") == "buy",
                "ret90": round(ret90, 6),
                "market": round(market, 6),
                "excess": round(excess, 6),
            }
        )

    if not rows:
        raise ValueError("No priced Scene 04 trades were available")
    return {
        "meta": {
            "from": min(row["date"] for row in rows),
            "to": max(row["date"] for row in rows),
            "source": "CAPITOL TRADES + EOD PRICES",
            "count": len(rows),
            "sourceCount": len(payload["data"]),
            "memberLimit": args.scene04_member_limit,
            "tradeLimit": args.scene04_trade_limit,
        },
        "MEM": members,
        "TICK": tickers,
        "TR": rows,
    }


def fetch_issuers(args: argparse.Namespace) -> Any:
    query = urllib.parse.urlencode({"search": args.search})
    return get_json(f"{BFF_URL}/issuers?{query}", args.timeout)


def write_output(
    payload: Any, output: Path | None, js_variable: str | None, js_assignments: bool
) -> None:
    if js_assignments:
        rendered = "".join(
            f"window.{name}={json.dumps(value, separators=(',', ':'))};\n"
            for name, value in payload.items()
        )
    elif js_variable:
        rendered = f"window.{js_variable}={json.dumps(payload, separators=(',', ':'))};\n"
    else:
        rendered = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--js-variable")
    subparsers = parser.add_subparsers(dest="command", required=True)

    trades = subparsers.add_parser("trades", help="Scrape rendered trade pages")
    trades.add_argument(
        "--input",
        type=Path,
        help="Use an existing scraped trade payload instead of fetching pages",
    )
    trades.add_argument("--pages", type=int, default=1)
    trades.add_argument("--start-page", type=int, default=1)
    trades.add_argument("--delay", type=float, default=1.0)
    trades.add_argument("--sort", default="-pubDate")
    trades.add_argument(
        "--scene02-js",
        action="store_true",
        help="Export the compact payload expected by the HTML prototype's Scene 02",
    )
    trades.add_argument(
        "--scene01-js",
        action="store_true",
        help="Export weekly net capital-flow data expected by the HTML prototype's Scene 01",
    )
    trades.add_argument(
        "--scene01-tape-limit",
        type=int,
        default=900,
        help="Maximum sampled trades used for Scene 01's bottom tape",
    )
    trades.add_argument(
        "--prototype-js",
        action="store_true",
        help="Export Scene 02 and real-price Scene 04 payloads for the HTML prototype",
    )
    trades.add_argument(
        "--scene04-js",
        action="store_true",
        help="Export only the compact payload expected by the HTML prototype's Scene 04",
    )
    trades.add_argument(
        "--scene04-start",
        help="Scene 04 trade-date lower bound in YYYY-MM-DD format",
    )
    trades.add_argument(
        "--scene04-end",
        help="Scene 04 trade-date upper bound in YYYY-MM-DD format",
    )
    trades.add_argument(
        "--scene04-member-limit",
        type=int,
        default=0,
        help="Keep only the N most active Scene 04 politicians after date filtering",
    )
    trades.add_argument(
        "--scene04-trade-limit",
        type=int,
        default=0,
        help="Cap Scene 04 trades with a month-balanced sample after date/member filtering",
    )
    trades.add_argument(
        "--price-delay",
        type=float,
        default=0.1,
        help="Delay between public issuer-price searches used for Scene 04",
    )
    trades.add_argument(
        "--require-priced-trades",
        type=int,
        default=0,
        help="Fail unless Scene 04 contains at least this many priced disclosures",
    )
    trades.add_argument(
        "--require-priced-members",
        type=int,
        default=0,
        help="Fail unless Scene 04 contains at least this many politicians",
    )
    trades.add_argument(
        "--progress",
        action="store_true",
        help="Report progress while scraping larger prototype datasets",
    )
    trades.add_argument(
        "--param",
        action="append",
        default=[],
        help="Repeatable site filter in KEY=VALUE form, for example txType=buy",
    )
    trades.set_defaults(fetch=fetch_trades)

    issuers = subparsers.add_parser("issuer-search", help="Call public issuer search")
    issuers.add_argument("search")
    issuers.set_defaults(fetch=fetch_issuers)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        payload = args.fetch(args)
    except (ValueError, urllib.error.URLError) as error:
        parser.error(str(error))
    write_output(payload, args.output, args.js_variable, args.prototype_js)


if __name__ == "__main__":
    main()
