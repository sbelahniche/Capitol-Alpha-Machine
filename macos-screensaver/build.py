#!/usr/bin/env python3
"""Build self-contained universal macOS screensavers."""
import argparse
import json
import os
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
parser.add_argument('--stats', action='store_true', help='diagnostics: overlay live frame timing')
parser.add_argument('--sign-identity', default=os.environ.get('CODESIGN_IDENTITY', '-'),
                    help='codesign identity or SHA-1 hash (default: CODESIGN_IDENTITY or ad hoc)')
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
    (resources / 'scene.html').write_text(optimize_scene(scene, number, stats=args.stats))
    (resources / 'fallback.json').write_text(json.dumps(payload, separators=(',', ':')))
    # System Settings reads these previews from the signed bundle resources.
    thumbnail_source = root / 'screensavers' / 'assets' / (name.lower().replace(' ', '-') + '.jpg')
    for scale, filename in [(1, 'thumbnail.png'), (2, 'thumbnail@2x.png')]:
        thumbnail = resources / filename
        subprocess.run(['sips', '-s', 'format', 'png', '--resampleWidth', str(480 * scale),
                        str(thumbnail_source), '--out', str(thumbnail)], check=True,
                       stdout=subprocess.DEVNULL)
        subprocess.run(['sips', '--padToHeightWidth', str(312 * scale), str(480 * scale),
                        '--padColor', '000000', str(thumbnail)], check=True,
                       stdout=subprocess.DEVNULL)
    with (contents / 'Info.plist').open('wb') as f:
        plistlib.dump(dict(CFBundleDevelopmentRegion='en', CFBundleExecutable=identifier,
            CFBundleIdentifier=f'app.capitolalpha.{identifier}', CFBundleInfoDictionaryVersion='6.0',
            CFBundleName=name, CFBundlePackageType='BNDL', CFBundleShortVersionString='1.5',
            CFBundleVersion='7', NSPrincipalClass=f'{identifier}View', LSMinimumSystemVersion='12.0',
            ScreenSaverThumbnail='thumbnail.png',
            CapitolScene=f'SCENE{number}', CapitolRequiredArrays=arrays,
            NSHumanReadableCopyright=f'{name} — Capitol Alpha Machine'), f)
    subprocess.run(['xcrun', 'clang', '-fobjc-arc', '-fmodules', '-fmodules-cache-path=' + str(root / 'build' / 'module-cache'),
        f'-DSAVER_VIEW={identifier}View', '-bundle', '-arch', 'arm64', '-arch', 'x86_64',
        '-mmacosx-version-min=12.0', '-framework', 'Cocoa', '-framework', 'ScreenSaver', '-framework', 'WebKit',
        str(root / 'macos-screensaver' / 'PolicyProximity.m'), '-o', str(contents / 'MacOS' / identifier)], check=True)
    sign = ['codesign', '--force', '--sign', args.sign_identity]
    if args.sign_identity != '-':
        sign += ['--options', 'runtime', '--timestamp']
    subprocess.run(sign + [str(bundle)], check=True)
    print(bundle)
