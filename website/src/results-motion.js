const observers = new WeakMap();

// Start each row when it is visible, including charts further down the page.
export function mountResultsMotion(root) {
  observers.get(root)?.disconnect();
  observers.delete(root);
  if (matchMedia('(prefers-reduced-motion: reduce)').matches || !('IntersectionObserver' in window)) return;
  const rows = root.querySelectorAll('.score-chart .model-row');
  if (!rows.length) return;
  const observer = new IntersectionObserver(entries => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      entry.target.dataset.chartMotion = 'ready';
      observer.unobserve(entry.target);
    }
  }, {threshold: .2});
  observers.set(root, observer);
  rows.forEach((row, i) => {
    row.style.setProperty('--result-delay', `${Math.min(i, 6) * 32}ms`);
    row.dataset.chartMotion = 'waiting';
    observer.observe(row);
  });
}
