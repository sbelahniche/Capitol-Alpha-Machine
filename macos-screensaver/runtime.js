/* Shared by the native savers and their isolated website previews. */
(() => {
  'use strict';
  const preview = __CAPITOL_PREVIEW__;
  const controlled = preview && parent !== window;
  const nativeRAF = window.requestAnimationFrame.bind(window);
  const nativeCancel = window.cancelAnimationFrame.bind(window);
  const pending = new Map();
  const interval = 1000 / 30;
  let playing = !controlled, initialFrame = controlled, nativeId = 0, nextId = 0;
  let lastRendered = null, lastTick = null, animationTime = 0;
  const visible = () => !preview || !document.hidden;
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
    lastRendered = timestamp;
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
  if (preview) {
    document.addEventListener('visibilitychange', () => {
      lastTick = null;
      lastRendered = null;
      if (document.hidden && nativeId) { nativeCancel(nativeId); nativeId = 0; }
      schedule();
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
})();
