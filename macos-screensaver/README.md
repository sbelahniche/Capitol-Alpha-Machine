# Capitol Alpha screensavers for macOS

Three separate native screensavers using the existing Policy Proximity, The Ledger, and Returns Spectrum canvas animations. Each has its own saved dataset and weekly update state. Built for Apple Silicon and Intel Macs, macOS 12 or later. Rendering was checked on macOS 15.6.1; other OS versions and the locked-screen host require separate verification.

Build all three with `python3 macos-screensaver/build.py`, or append `policy`, `ledger`, or `returns` to build individual screensavers. Local builds are ad-hoc signed by default; pass `--sign-identity` or set `CODESIGN_IDENTITY` for Developer ID signing. Open the corresponding `.saver` bundle in `build/` to install, then choose **Policy Proximity**, **The Ledger**, or **Returns Spectrum** in **System Settings → Screen Saver → Other**. Public v1.5 bundles are Developer ID signed and notarized by Apple.

The animation starts immediately from its last successful dataset, or the bundled dataset on first use. It checks for data once per weekly publication, scheduled for Monday at 12:00 in the Mac’s local time zone. If it is not running then, it catches up on the next full-screen start. First use fetches the latest available publication. Successful checks are remembered across sessions; failed checks retry on the next start, without periodic polling. It downloads `https://capitolalpha.app/capitoltrades_data.js`, parses only the selected scene’s JSON assignment, and replaces the scene only when the data differs. Failed requests leave the existing animation running. The small settings preview uses cached or bundled data and does not poll the network. No local server or open browser is needed.

**Data freshness:** the website's refresh pipeline currently reads Scene 05 from `data/scene05_real_payload.json`. It does not regenerate those policy-event links from the latest trades. Updating and publishing that source payload is necessary for new Policy Proximity content. The screensaver does not scrape or invent new data. Website design changes require rebuilding the screensaver; data changes do not.

Remove the corresponding installed `.saver` bundle from `~/Library/Screen Savers/` to uninstall. Screen-lock and sleep settings are not modified.

The guarded WebKit occlusion workaround follows the approach documented by [WebViewScreenSaver](https://github.com/liquidx/webviewscreensaver), necessary for canvas animation in recent macOS screensaver hosts.

## Showcase page

The one-page showcase lives at `/screensavers`. Run a local static server from the repository root to preview it. Its canonical URL currently uses the verified production host, `https://capitolalpha.app/screensavers`. If the project moves to `.com`, update canonical and social metadata together.

The live browser previews are exported from `index.html` by `python3 scripts/build_screensaver_previews.py`. Each contains only its selected scene's data, so it makes no additional request for the full data bundle. The weekly refresh runs this export automatically and commits both preview paths and the showcase's counts, date windows, hero points, and structured metadata. Run it manually after changing a scene's design. Both `/screensavers/preview/` and the older `/screensavers/previews/` paths are generated. Only one preview runs at a time, including full-screen mode; it pauses outside the viewport and when the tab is hidden. Reduced-motion visitors start with a still frame and can explicitly play an animation.

## Performance

Version 1.4 draws the scenes on the GPU (1.5 adds smooth subpixel motion for The Ledger's moving text and GPU-blurred text glows). `gpu-canvas.js` implements the 2D canvas subset the scenes use on WebGL2, so the thousands of rects, lines and glyphs in each frame become a few GPU draw calls at full Retina resolution, on WebKit's own frame cadence. Scenes keep the website's drawing code (plus the existing saver patches). Without WebGL2 the saver falls back to the 1.3 CPU canvas path (label atlas, four-million-pixel budget). The native host disables WebKit's inactive-page throttling (macOS 14+) and holds a latency-critical activity while the full-screen saver runs, so `legacyScreenSaver` is not App-Napped; sleep settings are unaffected. Website previews keep their paced CPU canvas. Weekly downloaded data is parsed and validated on the URL session's background queue; unchanged data does not reload the animation.

To check real frame timing inside the screensaver, build with `python3 macos-screensaver/build.py --stats`, install, and read the overlay; rebuild without `--stats` afterwards.

Run `node macos-screensaver/test-performance.cjs` after building to verify the frame cadence, the CPU fallback, and drawing commands against the original scenes. See [PERFORMANCE_AUDIT.md](PERFORMANCE_AUDIT.md) for measured operation counts, checks, and limitations.

Build 7 includes individual System Settings thumbnails. The build converts each scene's matching JPG in `screensavers/assets/` into `thumbnail.png` (480 × 312) and `thumbnail@2x.png` (960 × 624), preserving the scene's proportions with a black border, and sets `ScreenSaverThumbnail` in Info.plist. To change a preview, replace its source JPG and rebuild before signing and notarizing. Reopen System Settings after installing updated bundles to refresh the tiles.

To update public downloads, rebuild with Developer ID, submit the updated bundles for notarization and staple their tickets, then run `python3 macos-screensaver/package.py`. Copy the ZIPs and `SHA256SUMS.txt` from `build/downloads/` into `screensavers/downloads/`. These public ZIPs are explicitly allowed by the Git and Vercel ignore rules. Native source and temporary builds stay out of the website deployment.
