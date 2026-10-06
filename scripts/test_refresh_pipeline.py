"""Regression checks for stale local caches and weekly screensaver exports."""
import argparse
import gzip
import json
import re
import tempfile
import unittest
from pathlib import Path

import build_screensaver_previews as previews
import refresh_data_and_seo as refresh
import publish_latest_data as publish


class RefreshTests(unittest.TestCase):
    def test_newer_publication_wins_over_cache_file_preference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache, seed = root / 'cache.json', root / 'seed.json.gz'
            def payload(day, identity):
                return {'data': [{'_txId': identity, 'pubDate': day + 'T12:00:00Z', 'txDate': day}]}
            cache.write_text(json.dumps(payload('2026-08-14', 1)))
            seed.write_bytes(gzip.compress(json.dumps(payload('2026-10-02', 2)).encode()))
            args = argparse.Namespace(historical_seed=seed, incremental_pages=0,
                pages=10, page_size=100, start_page=1, sort='-pubDate')
            result = refresh.load_incremental_historical(args, cache)
            self.assertEqual([r['_txId'] for r in result['data']], [2])
            cache.write_text(json.dumps(payload('2026-10-05', 3)))
            result = refresh.load_incremental_historical(args, cache)
            self.assertEqual([r['_txId'] for r in result['data']], [3])

    def test_showcase_metadata_tracks_data_and_is_idempotent(self):
        root = Path(__file__).resolve().parents[1]
        bundle = (root / 'capitoltrades_data.js').read_text()
        payloads = {n: json.JSONDecoder().raw_decode(bundle.split('window.CAPITOL_TRADES_SCENE' + n + '=', 1)[1])[0]
                    for n in ['01', '02', '04', '05']}
        payloads['02']['meta']['to'] = '2026-10-06'
        source = (root / 'screensavers/index.html').read_text()
        output = previews.render_showcase(source, payloads)
        self.assertEqual(previews.render_showcase(output, payloads), output)
        self.assertIn('Live preview · data through 2026.10.06', output)
        hero = json.loads(re.search(r'const HERO=(.*?);\n', output)[1])
        self.assertEqual(len(hero), sum(len(previews.scene_records(payloads[n], n)) for _, n in previews.SCENES))
        self.assertNotIn('new data every Monday', output)
        self.assertNotIn('now beating the market', output)
        graph = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', output, re.S)[1])
        ledger = next(item for item in graph['@graph'] if item.get('name') == 'The Ledger')
        self.assertIn('2026-10-06', ledger['description'])
        self.assertIn('function syncAll()', output)
        self.assertIn('bucketCursor.set(BC)', output)

    def test_weekly_commit_includes_showcase_and_both_preview_paths(self):
        paths = publish.generated_files(include_seed=True)
        self.assertIn('screensavers/index.html', paths)
        self.assertIn('screensavers/preview/the-ledger.html', paths)
        self.assertIn('screensavers/previews/the-ledger.html', paths)
        self.assertNotIn('marketing/screensavers-launch.md', paths)


if __name__ == '__main__':
    unittest.main()
