import { scatterEnvelope, SCATTER_ATTACK_MS, SCATTER_RETRIGGER_MS } from './scatter-envelope.js';

// One finite pulse per pointer gesture, with an immediate start and a longer return.
// Coordinates are offsets only; submitted graph edges and circuit groups never change.
export function mountCaseScatter(element, { points, paint, toLocal }) {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const fine = matchMedia('(any-pointer: fine)');
  let origins = [], offsets = [], pulses = [], frame = 0, lastPoint, enabled = true;
  const allowed = event => enabled && !reduced.matches && fine.matches && !document.hidden && event.pointerType !== 'touch';
  const reset = () => {
    cancelAnimationFrame(frame);
    frame = 0;
    pulses = [];
    offsets = origins.map(() => ({ x: 0, y: 0, angle: 0 }));
    if (origins.length) paint(offsets);
    delete element.dataset.scatter;
  };
  const tick = now => {
    let running = false;
    offsets = origins.map((_, i) => {
      const p = pulses[i];
      if (!p) return { x: 0, y: 0, angle: 0 };
      const elapsed = Math.max(0, now - p.start);
      const amount = scatterEnvelope(elapsed, p.duration);
      const remainder = elapsed < SCATTER_ATTACK_MS ? 1 - amount : 0;
      running ||= elapsed < p.duration;
      return {
        x: p.from.x * remainder + p.x * amount,
        y: p.from.y * remainder + p.y * amount,
        angle: p.from.angle * remainder + p.angle * amount,
      };
    });
    paint(offsets);
    frame = running ? requestAnimationFrame(tick) : 0;
    if (!running) delete element.dataset.scatter;
  };
  const disturb = cursor => {
    const now = performance.now();
    let touched = false;
    for (const [i, point] of origins.entries()) {
      const distance = Math.hypot(point.x + offsets[i].x - cursor.x, point.y + offsets[i].y - cursor.y);
      if (distance >= 48 || (pulses[i] && now - pulses[i].start < SCATTER_RETRIGGER_MS)) continue;
      const direction = Math.atan2(point.y - cursor.y, point.x - cursor.x) + (Math.random() - .5) * 1.2;
      const strength = (1 - distance / 48) * 9;
      pulses[i] = {
        from: { ...offsets[i] }, x: Math.cos(direction) * strength,
        y: Math.sin(direction) * strength, angle: (Math.random() - .5) * 8,
        start: now, duration: 1450 + Math.random() * 300,
      };
      touched = true;
    }
    if (!touched) return;
    element.dataset.scatter = 'active';
    if (!frame) frame = requestAnimationFrame(tick);
  };
  const enter = event => {
    if (!allowed(event)) return;
    origins = points();
    if (offsets.length !== origins.length) offsets = origins.map(() => ({ x: 0, y: 0, angle: 0 }));
    lastPoint = toLocal(event);
    disturb(lastPoint);
  };
  const move = event => {
    if (!allowed(event)) return;
    if (!origins.length) { enter(event); return; }
    const point = toLocal(event);
    if (lastPoint && Math.hypot(point.x - lastPoint.x, point.y - lastPoint.y) < 3) return;
    lastPoint = point;
    disturb(point);
  };
  const preference = () => { if (reduced.matches || !fine.matches) reset(); };
  const visibility = () => { if (document.hidden) reset(); };
  const observer = new IntersectionObserver(entries => {
    if (!entries[0].isIntersecting) reset();
  });
  observer.observe(element);
  element.addEventListener('pointerenter', enter);
  element.addEventListener('pointermove', move);
  // Pointer exit leaves the finite pulse to finish naturally at its original coordinates.
  reduced.addEventListener('change', preference);
  fine.addEventListener('change', preference);
  document.addEventListener('visibilitychange', visibility);
  return {
    setEnabled(value) {
      if (enabled === value) return;
      enabled = value;
      lastPoint = null;
      if (enabled) return;
      if (reduced.matches || !offsets.some(p => p.x || p.y || p.angle)) { reset(); return; }
      // Inspection stops new impulses. Existing displacement settles directly
      // from its current pose, without a jump or another outward movement.
      const start = performance.now();
      pulses = offsets.map(from => ({ from: { ...from }, x: 0, y: 0, angle: 0, start, duration: SCATTER_ATTACK_MS }));
      if (!frame) frame = requestAnimationFrame(tick);
    },
    dispose() {
      reset(); observer.disconnect();
      element.removeEventListener('pointerenter', enter);
      element.removeEventListener('pointermove', move);
      reduced.removeEventListener('change', preference);
      fine.removeEventListener('change', preference);
      document.removeEventListener('visibilitychange', visibility);
    },
  };
}
