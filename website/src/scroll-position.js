// Wait for the catalogue and fonts before restoring a reload or a shared anchor.
// A freshly reconstructed Back/Forward page also waits for its async catalogue.
// Pages restored from the browser's memory cache retain their native position.
export function preserveReloadPosition() {
  const key = 'tcsexam:reading-position';
  let saved;
  try { saved = JSON.parse(sessionStorage.getItem(key)); } catch { /* Storage can be disabled. */ }
  const navigation = performance.getEntriesByType('navigation')[0]?.type;
  let pending = ['reload', 'back_forward'].includes(navigation)
    && saved?.url === location.href
    && Number.isFinite(saved.left) && Number.isFinite(saved.top) ? saved : null;
  if (!pending && navigation === 'navigate' && location.hash.length > 1) {
    try { pending = { anchor: decodeURIComponent(location.hash.slice(1)) }; } catch { /* Invalid fragment. */ }
  }
  const restoration = history.state?.tcsexamScrollRestoration || history.scrollRestoration;
  const root = document.documentElement;
  const scrollBehavior = root.style.scrollBehavior;
  if (pending) {
    history.scrollRestoration = 'manual';
    root.style.scrollBehavior = 'auto';
  }

  const remember = () => {
    if (pending) return; // Do not replace the saved position during loading.
    try {
      const catalogue = document.getElementById('catalogue-scroll');
      sessionStorage.setItem(key, JSON.stringify({
        url: location.href, left: scrollX, top: scrollY,
        catalogue: catalogue ? { left: catalogue.scrollLeft, top: catalogue.scrollTop } : null,
      }));
    } catch { /* Keep native navigation when storage is unavailable. */ }
  };
  window.addEventListener('pagehide', remember);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') remember();
  });

  const inputs = ['wheel', 'touchstart', 'pointerdown', 'keydown'];
  const cancel = () => {
    if (!pending) return;
    pending = null;
    root.style.scrollBehavior = scrollBehavior;
    if (!document.querySelector('#task-dialog')?.open) history.scrollRestoration = restoration;
    inputs.forEach(type => window.removeEventListener(type, cancel));
  };
  if (pending) inputs.forEach(type => window.addEventListener(type, cancel, { passive: true }));

  return {
    cancel,
    async restore(prepareLayout) {
      if (!pending) return null;
      await prepareLayout?.();
      await Promise.all([
        document.fonts.ready,
        document.readyState === 'complete' ? Promise.resolve()
          : new Promise(resolve => window.addEventListener('load', resolve, { once: true })),
      ]);
      // Run after native fragment navigation and layout, cancelling any anchor scroll.
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
      if (!pending) return null; // Respect navigation or scrolling during a slow load.
      const position = pending.anchor ? null : { left: pending.left, top: pending.top };
      if (position) {
        const catalogue = document.getElementById('catalogue-scroll');
        if (catalogue && Number.isFinite(pending.catalogue?.left) && Number.isFinite(pending.catalogue?.top))
          catalogue.scrollTo({ ...pending.catalogue, behavior: 'instant' });
        window.scrollTo({ ...position, behavior: 'instant' });
      }
      else document.getElementById(pending.anchor)?.scrollIntoView({ block: 'start', behavior: 'instant' });
      cancel();
      return position;
    },
  };
}
