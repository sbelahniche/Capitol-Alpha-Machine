#!/usr/bin/env python3
"""Validate generated static SEO and data assets before committing them."""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_PAGES = [
    "index.html",
    "methodology/index.html",
    "data/index.html",
    "updates/latest/index.html",
    "datasets/committee-risk/index.html",
    "scenes/capital-flow/index.html",
    "scenes/the-ledger/index.html",
    "scenes/exposure-index/index.html",
    "scenes/returns-spectrum/index.html",
    "scenes/timing-lattice/index.html",
]
REQUIRED_XML = ["sitemap.xml", "rss.xml", "og-image.svg"]
REQUIRED_TEXT = ["sitemap.txt"]
REQUIRED_SCENES = [
    "CAPITOL_TRADES_SCENE01",
    "CAPITOL_TRADES_SCENE02",
    "CAPITOL_TRADES_SCENE04",
    "CAPITOL_TRADES_SCENE05",
]


def read_js_object(bundle: str, name: str) -> dict[str, Any]:
    marker = f"window.{name}="
    start = bundle.index(marker) + len(marker)
    obj, _ = json.JSONDecoder().raw_decode(bundle[start:])
    return obj


def json_ld_blocks(html_text: str) -> list[Any]:
    blocks: list[Any] = []
    pattern = re.compile(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        re.DOTALL | re.IGNORECASE,
    )
    for match in pattern.finditer(html_text):
        blocks.append(json.loads(match.group(1)))
    return blocks


def validate_bundle(errors: list[str]) -> None:
    path = ROOT / "capitoltrades_data.js"
    if not path.exists():
        errors.append("Missing capitoltrades_data.js")
        return
    text = path.read_text(encoding="utf-8")
    scenes: dict[str, dict[str, Any]] = {}
    for name in REQUIRED_SCENES:
        try:
            scenes[name] = read_js_object(text, name)
        except Exception as exc:
            errors.append(f"Could not parse {name}: {exc}")
    if errors:
        return

    scene01 = scenes["CAPITOL_TRADES_SCENE01"]
    meta01 = scene01.get("meta", {})
    weeks = scene01.get("weeks", [])
    if meta01.get("publicVolumeTotal", 0) < 2_000_000_000:
        errors.append("Scene 01 is missing the headline public disclosed-volume total")
    if not weeks:
        errors.append("Scene 01 is missing weekly flow rows")
    elif not any("gross" in week for week in weeks) and not scene01.get("trades"):
        errors.append("Scene 01 needs gross weekly volume or tape trades for derived gross volume")
    if not scene01.get("trades"):
        errors.append("Scene 01 is missing the bottom tape trades")

    scene02 = scenes["CAPITOL_TRADES_SCENE02"]
    if not scene02.get("TR") or not scene02.get("TICK") or not scene02.get("MEM"):
        errors.append("Scene 02 compact payload is incomplete")

    scene04 = scenes["CAPITOL_TRADES_SCENE04"]
    if len(scene04.get("TR", [])) < 500 or len(scene04.get("MEM", [])) < 10:
        errors.append("Scene 04 has too few priced rows for production")

    scene05 = scenes["CAPITOL_TRADES_SCENE05"]
    if not scene05.get("events") or not scene05.get("trades"):
        errors.append("Scene 05 needs events and proximity-linked trades")


def validate_pages(errors: list[str]) -> None:
    for rel_path in REQUIRED_PAGES:
        path = ROOT / rel_path
        if not path.exists():
            errors.append(f"Missing page: {rel_path}")
            continue
        text = path.read_text(encoding="utf-8")
        if "<title>" not in text:
            errors.append(f"Page has no title: {rel_path}")
        if "meta name=\"description\"" not in text:
            errors.append(f"Page has no meta description: {rel_path}")
        try:
            blocks = json_ld_blocks(text)
        except Exception as exc:
            errors.append(f"Invalid JSON-LD in {rel_path}: {exc}")
            continue
        if not blocks:
            errors.append(f"Page has no JSON-LD: {rel_path}")


def validate_xml(errors: list[str]) -> None:
    for rel_path in REQUIRED_XML:
        path = ROOT / rel_path
        if not path.exists():
            errors.append(f"Missing XML/SVG asset: {rel_path}")
            continue
        try:
            ET.parse(path)
        except ET.ParseError as exc:
            errors.append(f"Invalid XML/SVG in {rel_path}: {exc}")

    robots = ROOT / "robots.txt"
    if not robots.exists():
        errors.append("Missing robots.txt")
    elif "Sitemap:" not in robots.read_text(encoding="utf-8"):
        errors.append("robots.txt does not advertise the sitemap")


def validate_text_assets(errors: list[str]) -> None:
    for rel_path in REQUIRED_TEXT:
        path = ROOT / rel_path
        if not path.exists():
            errors.append(f"Missing text asset: {rel_path}")
            continue
        lines = [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if not lines:
            errors.append(f"Text sitemap is empty: {rel_path}")
        if any(not line.startswith("https://capitol-alpha-machine.vercel.app/") for line in lines):
            errors.append(f"Text sitemap contains non-canonical URLs: {rel_path}")


def main() -> None:
    errors: list[str] = []
    validate_bundle(errors)
    validate_pages(errors)
    validate_xml(errors)
    validate_text_assets(errors)
    if errors:
        print("Static site validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        raise SystemExit(1)
    print("Static site validation passed.")


if __name__ == "__main__":
    main()
