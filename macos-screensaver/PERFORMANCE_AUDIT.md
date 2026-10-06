# Screensaver performance audit

Audited and optimized on 2026-10-06. Native packages are version 1.2, build 3.

## Findings and changes

| Finding | Implemented change |
| --- | --- |
| Animations draw at the display's refresh rate and allocate unrestricted Retina canvas backing stores. | Shared runtime caps drawing at 30 fps and backing stores at 4,000,000 pixels, with CSS coordinates preserved. |
| The Ledger visits every tape row and repeatedly measures labels and clips visible rows. | Visit only visible rows, cache up to 2,048 text measurements, clip once per column, and reuse dome buckets. Original row order and lock tie-breaking remain intact. |
| Returns Spectrum recomputes static trade positions, heights, and total volume every frame. | Cache trade geometry on resize and calculate total volume once. |
| Offscreen/hidden previews and fullscreen transitions can leave multiple scenes running. | Parent chooses one visible preview; fullscreen takes priority. Hidden tabs cancel animation work, including standalone previews. Parent control messages require the same origin and matching iframe source. |
| Animation time jumps after a pause. | Count only active rendering time and reset the clock reference on resume. |
| Flooring fractional trade progress each frame freezes Returns Spectrum's counter and slows Policy Proximity's counter. | Accumulate fractional progress and round only the displayed number. |
| Weekly download processing repeats JSON validation on the main thread and allocates every line separately. | Scan lines until the selected assignment is found, validate on the URL session background queue, and avoid rewriting/reloading unchanged data. |
| Preview copies differ and some fetch the complete site data bundle. | Generate both preview paths from the authoritative root scenes, embedding only the selected dataset and the shared runtime. |
| Public checksums no longer match rebuilt packages. | Rebuild all universal bundles and ZIPs, verify signatures after extraction, and regenerate public checksums and size labels. |

The exported screensavers and previews receive the drawing optimizations; the root site's scene animations are unchanged. The showcase header and layout are preserved.

## Measurements

Deterministic canvas recorder: same dataset, seeded randomness, ten frame timestamps spanning 0–20 seconds, and matching dimensions. These are operation counts, not CPU/GPU timings.

| The Ledger at 1512 × 982 | Original | Optimized | Reduction |
| --- | ---: | ---: | ---: |
| Native text measurements | 6,105 | 786 | 87.1% |
| Canvas state saves | 5,944 | 140 | 97.6% |

At 2560 × 1440, text measurements fall from 14,552 to 934 and state saves from 14,477 to 200. Policy Proximity at 1512 × 982 drops from 106 to 38 text measurements.

At 2560 × 1440 with device pixel ratio 2, the previous backing store held 14.75 million pixels. The new budget limits it to at most 4 million (about 73% fewer pixels). This trades some Retina sharpness for less rendering work. The 30 fps cap reduces rendered frames by half on a 60 Hz display and by three quarters on a 120 Hz display. Native RAF may still wake at display cadence to decide whether a frame is due.

## Verification

- Scheduler regression checks: 120 Hz input produces at most 30 rendered frames per second; paused and hidden previews schedule no frames; resume excludes inactive time; cancellation and message provenance work. Standalone browser previews sleep when hidden, while native savers remain active in an occluded host.
- Canvas drawing commands match the originals at 1512 × 982, 320 × 360, and 2560 × 1440 for all three scenes, except the intentional counter correction. The comparison covers tape wrapping and lock transitions. It is a geometry/state comparison, not pixel-level raster equivalence.
- All three native bundles compile for Apple Silicon and Intel. Each bundle and its extracted ZIP copy passes strict signature verification.
- Ten weekly scheduling checks pass, including exact Monday noon and both daylight-saving transitions.
- Browser smoke checks cover rendered previews and pause controls; no browser errors were reported.
- Public download checksums match the rebuilt ZIPs.

Reproduce:

```sh
python3 scripts/build_screensaver_previews.py
python3 macos-screensaver/build.py
node macos-screensaver/test-performance.cjs
python3 macos-screensaver/package.py
xcrun clang -fobjc-arc -framework Foundation macos-screensaver/test-schedule.m -o build/test-schedule
build/test-schedule
```

## Remaining limits

Actual CPU, GPU, memory, energy usage, and locked-screen rendering were not benchmarked in the macOS screensaver host during this audit. Existing installed copies require reinstalling the rebuilt version to receive these changes. Packages remain locally signed rather than Apple-notarized. Policy Proximity freshness still depends on publishing its separately prepared law/event dataset; this audit does not regenerate that data.
