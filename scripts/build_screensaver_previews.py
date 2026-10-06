#!/usr/bin/env python3
"""Export self-contained, optimized previews from the authoritative scene sources."""
import json
import html as html_tools
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'macos-screensaver'))
from scene_runtime import optimize_scene


SCENES = [('policy-proximity', '05'), ('the-ledger', '02'), ('returns-spectrum', '04')]


def replace_one(text, pattern, replacement):
    text, count = re.subn(pattern, lambda match: replacement(match), text, flags=re.S)
    if count != 1:
        raise ValueError(f'Showcase markup changed: expected one {pattern[:80]!r}, found {count}')
    return text


def scene_records(payload, number):
    if number == '02':
        return [(payload['MEM'][r[4]], bool(r[2]), payload['AMT'][r[3]]) for r in payload['TR']]
    if number == '04':
        return [(payload['MEM'][r['member']], r['buy'], r['amount']) for r in payload['TR']]
    return [(r['member'], r['buy'], r['value']) for r in payload['trades']]


def render_showcase(text, payloads):
    records = [record for _, number in SCENES for record in scene_records(payloads[number], number)]
    members = {r[0].strip().upper() for r in records}
    count, member_count = len(records), len(members)
    count_text = f'{count:,}'
    title = 'Free Mac Screensavers & Data Sculptures | Capitol Alpha'
    description = f'Three free Mac screensavers: data sculptures made from {count_text} congressional stock trades. Monochrome experiments in disclosure, public laws and returns.'
    text = replace_one(text, r'(<title>).*?(</title>)', lambda m: m[1] + html_tools.escape(title) + m[2])
    text = replace_one(text, r'(<meta name="description" content=").*?(">)', lambda m: m[1] + html_tools.escape(description, quote=True) + m[2])
    for attribute in ['property="og:description"', 'name="twitter:description"']:
        text = replace_one(text, r'(<meta ' + attribute + r' content=").*?(">)', lambda m: m[1] + html_tools.escape(description, quote=True) + m[2])
    text = re.sub(r'The U.S. Capitol drawn as a point cloud of [\d,]+ congressional stock trades',
                  f'The U.S. Capitol drawn as a point cloud of {count_text} congressional stock trades', text)
    text = re.sub(r'A point cloud of the U.S. Capitol made from [\d,]+ disclosed congressional trades.',
                  f'A point cloud of the U.S. Capitol made from {count_text} disclosed congressional trades.', text)
    text = replace_one(text, r'(<div>Points )\d+(</div>)', lambda m: m[1] + str(count).zfill(5) + m[2])
    text = replace_one(text, r'(<div>Members )\d+(</div>)', lambda m: m[1] + str(member_count).zfill(3) + m[2])
    text = replace_one(text, r'(<h1 id="hero-title">.*?</h1>\s*<p>).*?(</p>)', lambda m: m[1] +
        f'Three visualization experiments built from {count_text} congressional stock trades. Free Mac screensavers. Every point in the Capitol is a disclosed trade. Your Mac checks for newly published data each Monday; each study shows its own data window.' + m[2])
    text = re.sub(r'and \d+ other members appear', 'and other members appear', text)
    for label, value in [('Disclosures scanned', payloads['01']['meta']['count']), ('Trades on screen', count),
                         ('Members of Congress', member_count), ('Public laws linked', len(payloads['05']['events']))]:
        text = replace_one(text, rf'(<dt>{label}</dt><dd>).*?(</dd>)', lambda m, value=value: m[1] + f'{value:,}' + m[2])

    summaries = {}
    for slug, number in SCENES:
        payload = payloads[number]
        rows = scene_records(payload, number)
        n, n_members = len(rows), len({r[0] for r in rows})
        meta = payload['meta']
        ratio = sum(r[1] for r in rows) / max(1, n)
        def update_room(match):
            room = match[0]
            room = replace_one(room, r'(<p class="screen-cap">).*?(</p>)', lambda m: m[1] + 'Live preview · data through ' + meta['to'].replace('-', '.') + m[2])
            room = replace_one(room, r'(<dt>Trades</dt><dd>).*?(</dd>)', lambda m: m[1] + f'{n:,} by {n_members} members' + m[2])
            if number != '05':
                room = replace_one(room, r'(<dt>Period</dt><dd>).*?(</dd>)', lambda m: m[1] + meta['from'][:7].replace('-', '.') + '–' + meta['to'][:7].replace('-', '.') + m[2])
            if number == '04':
                room = replace_one(room, r'(<dt>Updates</dt><dd>).*?(</dd>)', lambda m: m[1] + 'When new prices are published' + m[2])
            room = replace_one(room, r'(<div class="meter"><span>Purchases</span><b>).*?(</b><i style="--v:).*?(" aria-hidden="true"></i></div>)',
                lambda m: m[1] + str(round(ratio * 100)) + '%' + m[2] + f'{ratio:.3f}' + m[3])
            return room
        text = replace_one(text, rf'<section class="room" id="{slug}".*?</section>', update_room)
        summaries[slug] = (n, n_members, meta)

    text = text.replace('Which stocks Congress traded are now beating the market?', 'A study of disclosed trades and historical market returns.')
    text = text.replace('stocks that have beaten the S&amp;P 500 (SPY) by more over the last 90 days', 'stocks that outperformed the S&amp;P 500 (SPY) over the 90-day window in this dataset')
    text = text.replace('<h3>New data every Monday</h3>', '<h3>Weekly checks, separate data windows</h3>')
    text = replace_one(text, r'(<h3>Weekly checks, separate data windows</h3>\s*<p>).*?(</p>)', lambda m: m[1] +
        'Each Monday at 12:00 local time each screensaver checks capitolalpha.app for newly published data. If it isn’t running then, it checks on its next start. Offline, it uses saved or bundled data. The Ledger receives new filings weekly. Returns Spectrum and Policy Proximity change when new price and law datasets are published. Their coverage dates appear beside each preview. Design changes need a new download.' + m[2])
    # Correct the FAQ's membership count without altering its editorial voice.
    text = re.sub(r'\d+ members from both parties and both chambers, including', f'{member_count} members from both parties and both chambers, including', text)
    for slug in ['capitol-alpha-screensavers', *(slug for slug, _ in SCENES)]:
        archive = ROOT / 'screensavers/downloads' / (slug + '-mac.zip')
        if archive.exists():
            size = f'{round(archive.stat().st_size / 1000)} KB'
            text = replace_one(text, rf'(<a class="pill solid" href="/screensavers/downloads/{slug}-mac.zip" download>).*?(</a>)',
                lambda m, slug=slug, size=size: m[1] + ('Download all · Free · ' + size if slug=='capitol-alpha-screensavers' else 'Download <small>' + size + '</small>') + m[2])
            if slug == 'capitol-alpha-screensavers':
                text = re.sub(r'Free · one \d+ KB zip', f'Free · one {size} zip', text)

    graph_match = re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)
    graph = json.loads(graph_match[1])
    for entity in graph['@graph']:
        if entity['@type'] == 'WebPage':
            entity.update(name=title, description=description)
        elif entity['@type'] == 'SoftwareApplication':
            slug = entity['@id'].split('#')[-1]
            n, n_members, meta = summaries[slug]
            entity['description'] = f'A free Mac screensaver and data sculpture: {n:,} congressional trade records by {n_members} members. Data window: {meta["from"]} to {meta["to"]}. Links and scores are visual heuristics.'
            entity['softwareVersion'] = '1.2'
        elif entity['@type'] == 'FAQPage':
            for item in entity['mainEntity']:
                if item['name'] == 'Which members of Congress appear?':
                    item['acceptedAnswer']['text'] = re.sub(r'^\d+ members', f'{member_count} members', item['acceptedAnswer']['text'])
    text = text[:graph_match.start(1)] + json.dumps(graph, separators=(',', ':')).replace('</', '<\\/') + text[graph_match.end(1):]
    hero = ''.join(chr(48 + min(9, max(0, round((math.log10(max(1, r[2])) - 3) * 2))) * 2 + int(r[1])) for r in records)
    text = replace_one(text, r'const HERO=.*?;\n', lambda _: 'const HERO=' + json.dumps(hero) + ';\n')
    ledger = payloads['02']
    tape = {'k': ledger['TICK'], 't': [v for r in ledger['TR'] for v in (r[1], r[2], r[3])], 'a': ledger['AMT']}
    text = replace_one(text, r'const TAPE=.*?;\n', lambda _: 'const TAPE=' + json.dumps(tape, separators=(',', ':')).replace('</', '<\\/') + ';\n')
    return text


def build_previews():
    source = (ROOT / 'index.html').read_text()
    bundle = (ROOT / 'capitoltrades_data.js').read_text()
    payloads = {}
    for number in ['01', '02', '04', '05']:
        marker = f'window.CAPITOL_TRADES_SCENE{number}='
        payloads[number], _ = json.JSONDecoder().raw_decode(bundle[bundle.index(marker) + len(marker):])
    for slug, number in SCENES:
        encoded = re.search(rf'<script id="scene{number}-html" type="application/json">(.*?)</script>', source, re.S).group(1)
        payload = payloads[number]
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
    page = ROOT / 'screensavers/index.html'
    page.write_text(render_showcase(page.read_text(), payloads))
    print('Updated showcase counts, dates, metadata and hero data')


if __name__ == '__main__':
    build_previews()
