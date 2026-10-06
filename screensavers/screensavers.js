(() => {
  const names = { 'the-ledger': 'The Ledger', 'policy-proximity': 'Policy Proximity', 'returns-spectrum': 'Returns Spectrum' };
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const works = Array.from(document.querySelectorAll('[data-artwork]'), element => ({
    element, slug: element.dataset.artwork, surface: element.querySelector('.art-surface'),
    mount: element.querySelector('.animation-mount'), status: element.querySelector('.art-state'),
    toggle: element.querySelector('.motion-toggle'), fullscreen: element.querySelector('.fullscreen-toggle'),
    ratio: 0, wantsMotion: !reduced.matches, frame: null, ready: false, timer: null, failed: false
  }));
  let active = null;
  function resize(work) {
    if (!work.frame) return;
    const width = work.surface.clientWidth;
    const height = work.surface.clientHeight;
    // Keep the complete composition in view, including on narrow screens.
    const scale = Math.min(width / 1280, height / 800);
    work.frame.style.transform = `translate(${-1280 * scale / 2}px, ${-800 * scale / 2}px) scale(${scale})`;
  }
  function controls(work) {
    const playing = work === active && work.wantsMotion && !document.hidden;
    work.toggle.textContent = work.wantsMotion ? 'Pause' : 'Play';
    work.toggle.setAttribute('aria-label', `${work.wantsMotion ? 'Pause' : 'Play'} ${names[work.slug]}`);
    work.status.textContent = work.failed ? 'Still image · play to retry' : !work.wantsMotion ? 'Still image' : playing && work.ready ? 'In motion' : playing ? 'Loading' : 'Moving image';
  }
  function unload(work) {
    clearTimeout(work.timer);
    work.frame?.remove();
    work.frame = null;
    work.ready = false;
  }
  function load(work) {
    work.frame = document.createElement('iframe');
    work.frame.title = `${names[work.slug]} animated artwork`;
    work.frame.setAttribute('sandbox', 'allow-scripts');
    work.frame.setAttribute('tabindex', '-1');
    work.frame.setAttribute('aria-hidden', 'true');
    work.frame.src = `/screensavers/previews/${work.slug}.html`;
    work.mount.append(work.frame);
    resize(work);
    work.timer = setTimeout(() => {
      if (work.ready) return;
      unload(work);
      work.failed = true;
      work.wantsMotion = false;
      controls(work);
    }, 18000);
  }
  function sync(preferred) {
    const full = works.find(work => work.element === document.fullscreenElement);
    const candidate = document.hidden ? null : full || preferred || works.filter(work => work.ratio > .08 && work.wantsMotion).sort((a, b) => b.ratio - a.ratio)[0] || null;
    if (active !== candidate) {
      if (active) unload(active);
      active = candidate;
    }
    if (active?.wantsMotion && !active.frame) load(active);
    if (active?.ready) active.frame.contentWindow.postMessage({type: 'capitol-preview-control', playing: active.wantsMotion && !document.hidden}, '*');
    works.forEach(controls);
  }
  const observer = new IntersectionObserver(entries => {
    for (const entry of entries) works.find(work => work.element === entry.target).ratio = entry.isIntersecting ? entry.intersectionRatio : 0;
    sync();
  }, {threshold: [0, .08, .25, .5, .75, 1]});
  for (const work of works) {
    observer.observe(work.element);
    new ResizeObserver(() => resize(work)).observe(work.surface);
    work.toggle.addEventListener('click', () => {
      work.wantsMotion = !work.wantsMotion;
      work.failed = false;
      sync(work.wantsMotion ? work : undefined);
    });
    if (!document.fullscreenEnabled) work.fullscreen.hidden = true;
    work.fullscreen.addEventListener('click', async () => {
      try {
        if (document.fullscreenElement) await document.exitFullscreen();
        else await work.element.requestFullscreen();
      } catch { work.status.textContent = 'Full screen unavailable'; }
    });
    controls(work);
  }
  window.addEventListener('message', event => {
    const work = works.find(work => work.frame?.contentWindow === event.source);
    if (!work || event.data?.type !== 'capitol-preview-ready') return;
    clearTimeout(work.timer);
    work.ready = true;
    work.frame.classList.add('ready');
    work.frame.contentWindow.postMessage({type: 'capitol-preview-control', playing: work === active && work.wantsMotion && !document.hidden}, '*');
    controls(work);
  });
  document.addEventListener('visibilitychange', () => sync());
  document.addEventListener('fullscreenchange', () => {
    works.forEach(work => {
      work.fullscreen.textContent = work.element === document.fullscreenElement ? 'Exit full screen' : 'Full screen ⤢';
      work.fullscreen.setAttribute('aria-label', `${work.element === document.fullscreenElement ? 'Exit' : 'View'} ${names[work.slug]} full screen`);
      resize(work);
    });
    sync();
  });
  reduced.addEventListener('change', () => { works.forEach(work => { work.wantsMotion = !reduced.matches; }); sync(); });
})();
