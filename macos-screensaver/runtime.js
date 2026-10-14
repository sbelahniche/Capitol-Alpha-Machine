/* Shared by the native savers and their isolated website previews. */
(() => {
  'use strict';
  const preview = __CAPITOL_PREVIEW__;
  // Native savers use WebKit's own vsync-driven requestAnimationFrame, like
  // the website. A pacing layer here skipped frames whenever a callback
  // arrived a fraction of a millisecond early, producing 16/33 ms judder.
  if (preview) {
    const controlled = parent !== window;
    const nativeRAF = window.requestAnimationFrame.bind(window);
    const nativeCancel = window.cancelAnimationFrame.bind(window);
    const pending = new Map();
    const interval = 1000 / 60;
    let playing = !controlled, initialFrame = controlled, nativeId = 0, nextId = 0;
    let lastRendered = null, lastTick = null, animationTime = 0;
    const visible = () => !document.hidden;
    function schedule() {
      if (!nativeId && pending.size && visible() && (playing || initialFrame)) {
        nativeId = nativeRAF(tick);
      }
    }
    function tick(timestamp) {
      nativeId = 0;
      if (!visible() || (!playing && !initialFrame)) return;
      if (lastRendered !== null && timestamp - lastRendered < interval - 0.5) {
        schedule();
        return;
      }
      if (lastTick !== null) animationTime += timestamp - lastTick;
      lastTick = timestamp;
      // Preserve the cadence across slightly late vsyncs. Resetting to each
      // timestamp can turn 60 Hz into 30 Hz when a callback is just late.
      lastRendered = lastRendered === null ? timestamp :
        timestamp - ((timestamp - lastRendered + 0.5) % interval) + 0.5;
      initialFrame = false;
      const callbacks = [...pending.values()];
      pending.clear();
      for (const callback of callbacks) callback(animationTime);
      if (!playing) lastTick = null;
      schedule();
    }
    window.requestAnimationFrame = callback => {
      const id = ++nextId;
      pending.set(id, callback);
      schedule();
      return id;
    };
    window.cancelAnimationFrame = id => {
      pending.delete(id);
      if (!pending.size && nativeId) { nativeCancel(nativeId); nativeId = 0; }
    };
    function setPlaying(value) {
      if (playing === value) return;
      playing = value;
      lastTick = null;
      lastRendered = null;
      if (nativeId) { nativeCancel(nativeId); nativeId = 0; }
      schedule();
    }
    window.__capitolSetPlaying = setPlaying;
    if (controlled) {
      window.addEventListener('message', event => {
        if (event.source !== parent || event.origin !== location.origin) return;
        if (event.data === 'cam:play') setPlaying(true);
        else if (event.data === 'cam:pause') setPlaying(false);
        else if (event.data?.type === 'capitol-preview-control') setPlaying(event.data.playing === true);
      });
      window.addEventListener('load', () => parent.postMessage({type:'capitol-preview-ready'}, location.origin));
    }
    document.addEventListener('visibilitychange', () => {
      lastTick = null;
      lastRendered = null;
      if (document.hidden && nativeId) { nativeCancel(nativeId); nativeId = 0; }
      schedule();
    });
  }
  // Diagnostics builds (build.py --stats) overlay live frame timing measured
  // inside the real screensaver host.
  if (!preview && window.__capitolStats) {
    const raf = window.requestAnimationFrame.bind(window), intervals = [], work = [];
    let last = 0;
    window.requestAnimationFrame = callback => raf(ts => {
      const start = performance.now();
      callback(ts);
      work.push(performance.now() - start);
      if (last) intervals.push(ts - last);
      last = ts;
    });
    const pct = (values, p) => values.slice().sort((a, b) => a - b)[Math.min(values.length - 1, Math.floor(values.length * p))] || 0;
    window.addEventListener('load', () => {
      const box = document.createElement('div');
      box.style.cssText = 'position:fixed;right:12px;bottom:64px;z-index:9;padding:4px 6px;background:rgba(0,0,0,.75);' +
        'color:#fff;font:11px ui-monospace,Menlo,monospace;white-space:pre;pointer-events:none';
      document.body.appendChild(box);
      setInterval(() => {
        const frames = intervals.length, slow = intervals.filter(v => v > 20).length;
        box.textContent = (frames ? (1000 * frames / intervals.reduce((a, b) => a + b, 0)).toFixed(1) : '0') + ' fps  ' +
          'frame p95 ' + pct(intervals, .95).toFixed(1) + ' max ' + pct(intervals, 1).toFixed(1) + ' ms  ' +
          'late ' + slow + '\nscript p95 ' + pct(work, .95).toFixed(1) + ' ms  ' + (window.__capitolGPU ? 'GPU' : 'CPU') +
          ' ' + (document.querySelector('canvas') || {}).width + '\u00d7' + (document.querySelector('canvas') || {}).height;
        intervals.length = 0; work.length = 0;
      }, 2000);
    });
  }
  // Text fitting repeatedly measures the same ticker/member labels. Bound the
  // cache so weekly data updates cannot cause unlimited retained metrics.
  window.__capitolCacheText = ctx => {
    const measure = ctx.measureText.bind(ctx), metrics = new Map();
    ctx.measureText = text => {
      const key = JSON.stringify([ctx.font, ctx.direction, ctx.fontKerning, ctx.letterSpacing, String(text)]);
      if (metrics.has(key)) return metrics.get(key);
      const value = measure(text);
      if (metrics.size >= 2048) metrics.clear();
      metrics.set(key, value);
      return value;
    };
  };

  // Rasterize ticker labels once per resize, then composite the same glyphs
  // at fractional positions. One bounded atlas avoids hundreds of canvases.
  window.__capitolCreateLabelAtlas = (labels, font, maxWidth, dpr) => {
    const cellW = Math.ceil(maxWidth) + 4, cellH = 28, columns = 8;
    const rows = Math.max(1, Math.ceil(labels.length / columns));
    let scale = Math.min(dpr, Math.sqrt(4000000 / (columns * cellW * rows * cellH)));
    // Include cell rounding in the allocation budget, not just ideal area.
    while (columns * Math.ceil(cellW * scale) * rows * Math.ceil(cellH * scale) > 4000000) scale *= 0.99;
    const atlas = document.createElement('canvas');
    const pw = Math.ceil(cellW * scale), ph = Math.ceil(cellH * scale);
    atlas.width = columns * pw; atlas.height = rows * ph;
    const paint = atlas.getContext('2d');
    paint.scale(scale, scale); paint.font = font; paint.fillStyle = '#fff';
    const widths = [];
    for (let i = 0; i < labels.length; i++) {
      widths.push(paint.measureText(labels[i]).width);
      paint.fillText(labels[i], (i % columns) * pw / scale + 2,
        Math.floor(i / columns) * ph / scale + 20, maxWidth);
    }
    return {
      widths,
      draw(ctx, index, x, y, alpha) {
        const previous = ctx.globalAlpha;
        ctx.globalAlpha = previous * alpha;
        ctx.drawImage(atlas, (index % columns) * pw, Math.floor(index / columns) * ph,
          pw, ph, x - 2, y - 20, pw / scale, ph / scale);
        ctx.globalAlpha = previous;
      }
    };
  };
})();
