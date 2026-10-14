# Screensaver performance audit

## Version 1.5 (build 6) — smooth Ledger motion, 2026-10-07

Version 1.4 still felt jerky in The Ledger, the only scene with moving text.

- **Whole-pixel text stepping.** Canvas text engines snap each glyph's baseline to a whole pixel. Measured on a label scrolling 1.33 px per frame (the tape speed at 2x), it moved 1, 2, 1, 1, 2 px per frame, while the bars and dome beside it moved smoothly. Version 1.4 copied that snapping exactly; 1.3's label atlas had hidden it with blurrier text. The website shows the same steps.
- **Glow re-rasterization.** The lock panel's name pulses its shadow blur about 13 times a second. 1.4 rasterized a blurred copy of each glyph for each blur level on the CPU, and in the first seconds of each new lock this could stall frames.
- **Per-row color strings.** Each visible tape row built two new color strings per frame, which then had to be hashed for lookup.

Fixes:

- Text the scene marks as moving (`ctx.capitolMovingText`: tape labels and the locked ticker) is placed at 1/4 px horizontally and 1/8 px vertically, plus the remaining fraction through linear filtering. Where the text engine snaps, those offsets are rasterized at 4x/8x and box-filtered down. Measured steps for the same label: 1.30–1.38 px per frame against 1.33 ideal. Static text still snaps like the 2D canvas, so it stays crisp.
- Text shadows are blurred on the GPU from the sharp glyph (Gaussian, σ = shadowBlur / 2). No blurred glyphs are rasterized on the CPU.
- New glyphs are drawn into one CPU staging canvas and uploaded together: one pixel readback per frame with new glyphs instead of one per glyph.
- The dot grid is recorded once per canvas size and copied into each frame. Ledger row colors reuse cached strings (identical values).
- `python3 macos-screensaver/build.py --stats` builds diagnostics savers that overlay live fps, frame interval p95/max, late frames (>20 ms) and script time inside the real screensaver host.

Verification (Chromium, 2560 × 1440 points at 2x = 5120 × 2880 pixels): The Ledger script time 2.3 ms median / 3.9 ms p95 per frame after warm-up (2.7 / 4.1 in 1.4), no frames over 15 ms in two 30-second runs, no shadow rasterizations, no atlas resets in 2 minutes. Startup rasterizes about 1,200 glyph variants in the first two frames. Pixel comparison with the website: Returns Spectrum and Policy Proximity unchanged (mean difference ≈ 0.05); The Ledger 0.41, because its moving labels now sit at their true fractional positions instead of whole pixels.

## Version 1.4 (build 5) — GPU rendering, 2026-10-06

Version 1.3 still stuttered full screen on a Mac Studio. Root causes:

- **CPU rasterization of thousands of commands per frame.** WebKit draws each 2D canvas command with CoreGraphics on the CPU. Per frame at 2560 × 1440: The Ledger ≈ 8,600 commands, Returns Spectrum ≈ 11,400, Policy Proximity ≈ 4,900 (more on larger displays, and once per display). The 1.3 benchmark already dropped frames at that size (56 fps, 32 ms p95 interval). Chrome runs the same website canvas on the GPU, which is why the website looks smooth there.
- **The 60 fps pacing layer dropped frames.** It skipped any callback that arrived more than 0.5 ms early. WebKit's frame timestamps jitter and are rounded to whole milliseconds, so early callbacks produced irregular 16/33 ms frames (judder) even when rendering kept up.
- **Reduced resolution.** The four-million-pixel budget rendered Retina displays at roughly half resolution and upscaled.

Fixes:

- `gpu-canvas.js` implements the canvas subset the three scenes use on WebGL2. Scene drawing code is not rewritten; every rect, line and glyph becomes one instance in a buffer, drawn in order with three or four GPU draw calls per frame. Coverage is computed per pixel (box filter for rects and butt lines, distance for round caps, Gaussian for shadows), translucent polylines are drawn as one mitered strip so joints are not doubled, and glyphs are rasterized once by the real 2D canvas at device size and cached in a 2048² atlas. The text engine's pixel snapping is probed at startup so cached glyphs land where the 2D canvas would place them.
- Native savers render at the website's resolution (up to 2×) on WebKit's own requestAnimationFrame cadence. The pacing layer now applies only to the website previews, whose output is unchanged.
- If WebGL2 is unavailable, the saver falls back to the 1.3 CPU canvas path (atlas, four-million-pixel budget) automatically.
- Native host: `WKPreferences.inactiveSchedulingPolicy = none` (macOS 14+) so WebKit never suspends or throttles the saver's page as inactive, and an `NSProcessInfo` activity (user-initiated, latency-critical, idle system sleep still allowed) keeps `legacyScreenSaver` out of App Nap and timer coalescing while the full-screen saver runs. Display and system sleep remain under the user's settings.

Verification (Chromium/SwiftShader, website scenes as reference, deterministic timestamps and random seeds, 1280 × 800 and 1512 × 982 at 2×, 0–9 s):

| Scene | Mean pixel difference (0–255) | Pixels differing by > 16 |
| --- | ---: | ---: |
| The Ledger | 0.18–0.20 | 0.32–0.37 % |
| Returns Spectrum | 0.05–0.07 | 0.08–0.10 % |
| Policy Proximity | 0.05–0.07 | 0.06–0.09 % |

Remaining differences are glyph resampling where long labels are compressed to the column width, and quarter-pixel text placement. The trade counters intentionally keep the 1.3 accumulation fix, so they differ from the website.

JavaScript time per frame at 2560 × 1440 points (5120 × 2880 pixels), steady state after warm-up, GPU execution excluded: The Ledger 2.7 ms median / 4.1 ms p95 (≈16,500 instances), Returns Spectrum 1.6 / 2.2 ms (≈11,400), Policy Proximity 0.7 / 1.1 ms (≈3,900). New glyphs are rasterized on first use (≈560 for The Ledger's first second); later frames reuse the atlas. These numbers come from Chromium, not WebKit; GPU frame time and the locked-screen host still need confirming on a Mac with the native benchmark.

`node macos-screensaver/test-performance.cjs` covers the CPU fallback, resolution policy and native frame cadence in addition to the 1.3 checks.

## Version 1.3 (build 4)

Audited on 2026-10-06.

### Findings and fixes

- Version 1.2 deliberately capped all scenes at 30 fps. Version 1.3 targets 60 fps. The scheduler retains its phase across late callbacks instead of resetting the deadline, avoiding unnecessary skipped frames when vsync timing fluctuates.
- The Ledger issued hundreds of text rasterization commands each frame, even though the labels never changed. It now rasterizes all tickers once per resize into one white-text atlas and draws cached images with each row's opacity. The atlas is capped at four million pixels including cell rounding (up to approximately 16 MB of pixel storage, excluding compositor copies). Fractional scrolling positions remain intact; glyph antialiasing can differ from directly rendered text.
- The Ledger built a selection object and measured every visible label even while a trade was already locked. Selection objects are now created only for eligible candidates when acquiring a lock; widths are measured once with the atlas.
- Returns Spectrum allocated a color string for every trade on every frame. It now reuses a 1,001-entry opacity palette with the same colors.
- Existing optimizations remain: four-million-pixel main canvas budget, visible-row traversal, one clip per column, reusable dome buckets, cached trade geometry, hidden-preview suspension, pause-safe clocks, and background validation of downloaded data.

Changes apply to all native bundles and both generated preview paths. The root site's embedded scenes remain the reference source. Public ZIPs, checksums, and displayed download sizes have been rebuilt locally; nothing has been deployed or installed automatically.

### Native WebKit measurements

Measured on this Mac Studio, Apple M1 Max, 64 GB RAM, using a visible WKWebView. Each run lasts 12 seconds and discards its first 60 frames. At a 1512 × 982 CSS viewport the main canvas is 2481 × 1611 pixels. Results measure callback cadence and JavaScript/canvas command submission, not GPU completion or display presentation.

| Scene / build | Average callback fps | Median submission | p95 submission | p95 frame interval |
| --- | ---: | ---: | ---: | ---: |
| Ledger 1.2, 1512 × 982 | 27.7 | 5 ms | 8 ms | 50 ms |
| Ledger 1.3, 1512 × 982 | 60.0 | 2 ms | 3 ms | 18 ms |
| Policy Proximity 1.3, 1512 × 982 | 60.0 | 1 ms | 4 ms | 18 ms |
| Returns Spectrum 1.3, 1512 × 982 | 60.0 | 4 ms | 5 ms | 18 ms |
| Ledger 1.3, 2560 × 1440 | 56.2 | 2 ms | 3 ms | 32 ms |

These are individual runs, not guaranteed sustained frame rates. Interim Returns Spectrum runs varied (approximately 45–57 fps); the final palette build measured 60 fps. Random highlight selection and concurrent system load are not controlled in this timing harness. Larger viewports and the locked-screen screensaver host can behave differently. No energy, GPU utilization, or locked-screen-host benchmark was performed. The 60 fps target trades increased frame frequency for smoother motion.

### Verification

- Scheduler tests exercise 60, 120, 144, and 59.94 Hz callback sources, including jitter; each delivers approximately 60 rendered frames per second. Pause, visibility, cancellation, origin checks, and native-host occlusion behavior pass.
- Atlas tests check rounded memory bounds, opacity multiplication/restoration, and no repeated label rasterization during steady frames.
- Deterministic geometry/style regression checks pass for all three scenes at 320 × 360, 1512 × 982, and 2560 × 1440 over timestamps spanning 0–20 seconds. The recorder expands atlas draws into semantic label commands; it does not assert pixel equivalence. Existing counter corrections remain intentional.
- WebKit snapshots of all three scenes were inspected for rendering errors.
- All three universal Apple Silicon/Intel bundles compile; packaging verifies strict signatures both before and after ZIP extraction.
- Static-site validation and public ZIP checksum verification pass.

Reproduce builds and regression checks:

```sh
python3 macos-screensaver/build.py
node macos-screensaver/test-performance.cjs
python3 macos-screensaver/package.py
python3 scripts/build_screensaver_previews.py
python3 scripts/validate_static_site.py
```

Run the visible native WebKit timing harness (requires desktop access):

```sh
xcrun clang -fobjc-arc -framework Cocoa -framework WebKit macos-screensaver/benchmark.m -o build/benchmark
build/benchmark 'build/The Ledger.saver/Contents/Resources' build/ledger.png 02 1512 982
build/benchmark 'build/Returns Spectrum.saver/Contents/Resources' build/returns.png 04 1512 982
build/benchmark 'build/Policy Proximity.saver/Contents/Resources' build/policy.png 05 1512 982
```

Install the rebuilt version to receive the rendering changes. The weekly data update does not update installed screensaver code. Public v1.5 packages are Developer ID signed and notarized by Apple.
