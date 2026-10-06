#!/usr/bin/env python3
"""Build self-contained, locally signed universal macOS screensavers."""
import argparse
import json
import plistlib
import re
import subprocess
from pathlib import Path
from scene_runtime import optimize_scene

SAVERS = {
    'policy': ('Policy Proximity', 'PolicyProximity', '05', ['events', 'trades']),
    'ledger': ('The Ledger', 'TheLedger', '02', ['AMT', 'MEM', 'TICK', 'TR']),
    'returns': ('Returns Spectrum', 'ReturnsSpectrum', '04', ['MEM', 'TICK', 'TR']),
}
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('savers', nargs='*', help='policy, ledger, returns (default: all)')
args = parser.parse_args()
if any(key not in SAVERS for key in args.savers):
    parser.error('Choose policy, ledger, or returns')
root = Path(__file__).resolve().parents[1]
html = (root / 'index.html').read_text()
data_lines = (root / 'capitoltrades_data.js').read_text().splitlines()
for key in args.savers or SAVERS:
    name, identifier, number, arrays = SAVERS[key]
    bundle = root / 'build' / f'{name}.saver'
    contents = bundle / 'Contents'
    resources = contents / 'Resources'
    resources.mkdir(parents=True, exist_ok=True)
    (contents / 'MacOS').mkdir(exist_ok=True)
    scene = json.loads(re.search(rf'<script id="scene{number}-html" type="application/json">(.*?)</script>', html, re.S).group(1))
    prefix = f'window.CAPITOL_TRADES_SCENE{number}='
    line = next(line for line in data_lines if line.startswith(prefix))
    payload = json.loads(line[len(prefix):].rstrip(';'))
    assert all(isinstance(payload.get(k), list) and payload[k] for k in arrays), f'Missing {name} data'
    assert f'window.__CAPITOL_TRADES_SCENE{number}__' in scene
    (resources / 'scene.html').write_text(optimize_scene(scene, number))
    (resources / 'fallback.json').write_text(json.dumps(payload, separators=(',', ':')))
    with (contents / 'Info.plist').open('wb') as f:
        plistlib.dump(dict(CFBundleDevelopmentRegion='en', CFBundleExecutable=identifier,
            CFBundleIdentifier=f'app.capitolalpha.{identifier}', CFBundleInfoDictionaryVersion='6.0',
            CFBundleName=name, CFBundlePackageType='BNDL', CFBundleShortVersionString='1.2',
            CFBundleVersion='3', NSPrincipalClass=f'{identifier}View', LSMinimumSystemVersion='12.0',
            CapitolScene=f'SCENE{number}', CapitolRequiredArrays=arrays,
            NSHumanReadableCopyright=f'{name} — Capitol Alpha Machine'), f)
    subprocess.run(['xcrun', 'clang', '-fobjc-arc', '-fmodules', '-fmodules-cache-path=' + str(root / 'build' / 'module-cache'),
        f'-DSAVER_VIEW={identifier}View', '-bundle', '-arch', 'arm64', '-arch', 'x86_64',
        '-mmacosx-version-min=12.0', '-framework', 'Cocoa', '-framework', 'ScreenSaver', '-framework', 'WebKit',
        str(root / 'macos-screensaver' / 'PolicyProximity.m'), '-o', str(contents / 'MacOS' / identifier)], check=True)
    subprocess.run(['codesign', '--force', '--sign', '-', str(bundle)], check=True)
    print(bundle)
