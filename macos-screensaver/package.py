#!/usr/bin/env python3
"""Package the built screensavers for download without local data or settings."""
from pathlib import Path
import hashlib
import subprocess
import tempfile
import zipfile

root = Path(__file__).resolve().parents[1]
output = root / 'build' / 'downloads'
output.mkdir(parents=True, exist_ok=True)
names = ['Policy Proximity', 'The Ledger', 'Returns Spectrum']
readme = '''CAPITOL ALPHA MACHINE — MAC SCREENSAVERS

INSTALL
1. Unzip this download.
2. Double-click a .saver file and install it for your user account.
3. Open System Settings > Screen Saver > Other and select the screensaver.
4. If the screen saver start time is Never, choose a start time in Lock Screen settings.

COMPATIBILITY
Universal builds for Apple Silicon and Intel Macs, macOS 12 or later.
Animation rendering tested on macOS 15.6.1. Other macOS versions and
locked-screen behavior have not been verified.

These downloads are locally signed, but are not Apple-notarized. macOS
may block installation after downloading. For a download you trust,
review the message in System Settings > Privacy & Security and use
Open Anyway if offered. Do not disable Gatekeeper system-wide.

DATA UPDATES
Checks for published data on Monday at 12:00 in your Mac's local time zone.
If the screensaver is not running then, it checks on its next start.
The first run fetches the latest available data. Successful weekly checks
are remembered; failed downloads retry on the next start.
Offline, it uses saved data or the dataset bundled in this download.
No browser or local server needs to remain open.

The data comes from https://capitolalpha.app/capitoltrades_data.js.
Policy Proximity updates when its separately prepared event dataset is
published; it does not generate new event links itself.
Only data updates automatically. Design changes require a new download.

UNINSTALL
Remove the relevant .saver bundle from ~/Library/Screen Savers/.

PROJECT
https://capitolalpha.app/
'''
packages = [(name.lower().replace(' ', '-') + '-mac.zip', [name]) for name in names]
packages.append(('capitol-alpha-screensavers-mac.zip', names))
checksums = []
for filename, selected in packages:
    archive = output / filename
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr('INSTALL.txt', readme)
        for name in selected:
            bundle = root / 'build' / f'{name}.saver'
            subprocess.run(['codesign', '--verify', '--strict', str(bundle)], check=True)
            for path in sorted(bundle.rglob('*')):
                if path.is_file() and path.name != '.DS_Store':
                    z.write(path, path.relative_to(bundle.parent))
    with tempfile.TemporaryDirectory(prefix='verify-savers-', dir=root / 'build') as tmp:
        subprocess.run(['ditto', '-x', '-k', str(archive), tmp], check=True)
        for name in selected:
            subprocess.run(['codesign', '--verify', '--strict', str(Path(tmp) / f'{name}.saver')], check=True)
    checksums.append(hashlib.sha256(archive.read_bytes()).hexdigest() + '  ' + filename)
    print(f'{archive} ({archive.stat().st_size:,} bytes; extracted signatures verified)')
(output / 'SHA256SUMS.txt').write_text('\n'.join(checksums) + '\n')
