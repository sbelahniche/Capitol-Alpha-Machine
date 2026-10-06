#!/usr/bin/env python3
"""Export self-contained, optimized previews from the authoritative scene sources."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'macos-screensaver'))
from scene_runtime import optimize_scene


def build_previews():
    source = (ROOT / 'index.html').read_text()
    bundle = (ROOT / 'capitoltrades_data.js').read_text()
    for slug, number in [('policy-proximity', '05'), ('the-ledger', '02'), ('returns-spectrum', '04')]:
        encoded = re.search(rf'<script id="scene{number}-html" type="application/json">(.*?)</script>', source, re.S).group(1)
        marker = f'window.CAPITOL_TRADES_SCENE{number}='
        payload, _ = json.JSONDecoder().raw_decode(bundle[bundle.index(marker) + len(marker):])
        data = json.dumps(payload, separators=(',', ':')).replace('</', '<\\/')
        html = json.loads(encoded).replace(f'window.__CAPITOL_TRADES_SCENE{number}__', data)
        html = optimize_scene(html, number, preview=True)
        html = html.replace('</head>', '<meta name="robots" content="noindex">\n</head>')
        # Both URLs exist in older page versions; keep their runtime identical.
        for directory in ('preview', 'previews'):
            target = ROOT / 'screensavers' / directory
            target.mkdir(exist_ok=True)
            (target / f'{slug}.html').write_text(html)
        print(f'Built {slug} preview')


if __name__ == '__main__':
    build_previews()
