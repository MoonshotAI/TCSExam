import { scatterEnvelope, SCATTER_ATTACK_MS, SCATTER_RETRIGGER_MS } from '../scatter-envelope.js';

// Decorative motion only: the task definitions and interactive lab states are untouched.
const between = (a, b) => a + Math.random() * (b - a);
const clamp = (value, a, b) => Math.max(a, Math.min(b, value));
const pose = (x, y, angle = 0) =>
  `translate(${x.toFixed(2)}px, ${y.toFixed(2)}px) rotate(${angle.toFixed(2)}deg)`;

export function createScatterMotion({ surfaceSelector = ".task-preview" } = {}) {
  const prepared = new Map(),
    running = new Map();
  let activeRow = null,
    lastPoint = null;

  function prepare(row) {
    if (prepared.has(row)) return prepared.get(row);
    const scene = row.querySelector(".pv-scene");
    const viewport = scene.ownerSVGElement.viewBox.baseVal;
    const units = viewport.width / 176;
    const pieces = [
      ...scene.querySelectorAll("[data-preview-piece], circle:not(.pv-white), rect, path, ellipse"),
    ].filter(shape => !shape.parentElement.closest("[data-preview-piece]")).map((shape) => {
      const bounds = shape.getBBox();
      const parent = shape.parentNode;
      const element = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "g",
      );
      element.classList.add("pv-fragment");
      parent.insertBefore(element, shape);
      element.append(shape);
      return { element, shape, parent, bounds, units, viewport };
    });
    // Keep cell values, node labels and the centre of a token with their own shape.
    for (const label of [...scene.querySelectorAll("text, .pv-white")]) {
      const x = Number(
        label.getAttribute(label.tagName === "text" ? "x" : "cx"),
      );
      const y = Number(
        label.getAttribute(label.tagName === "text" ? "y" : "cy"),
      );
      const owner = pieces
        .filter((p) => {
          const b = p.bounds;
          return (
            p.parent === label.parentNode &&
            (p.shape.matches("circle, rect") || p.shape.querySelector("circle, rect")) &&
            x >= b.x &&
            x <= b.x + b.width &&
            y >= b.y &&
            y <= b.y + b.height
          );
        })
        .sort(
          (a, b) =>
            a.bounds.width * a.bounds.height - b.bounds.width * b.bounds.height,
        )[0];
      if (owner) owner.element.append(label);
    }
    for (const piece of pieces) {
      piece.bounds = piece.element.getBBox();
      piece.x = piece.bounds.x + piece.bounds.width / 2;
      piece.y = piece.bounds.y + piece.bounds.height / 2;
      piece.weight =
        piece.shape.tagName === "path" || piece.shape.querySelector("path")
          ? 0.42
          : piece.bounds.width * piece.bounds.height > 900 * units * units
            ? 0.7
            : 1;
    }
    prepared.set(row, pieces);
    return pieces;
  }

  function start(piece, frames, duration, delay = 0, easing = "linear") {
    running.get(piece.element)?.cancel();
    const animation = piece.element.animate(frames, {
      duration,
      delay,
      easing,
      fill: "both",
    });
    running.set(piece.element, animation);
    animation.finished
      .then(() => {
        if (running.get(piece.element) === animation) {
          running.delete(piece.element);
          animation.cancel(); // Every sequence ends at the unmodified original geometry.
        }
      })
      .catch(() => {}); // Pointer input, reduced motion and cleanup cancel pending motion.
  }

  function disturb(piece, dx, dy) {
    const b = piece.bounds;
    const { units, viewport } = piece;
    // Allow a little overhang inside the row's whitespace, keeping fragments close to the figure.
    const limit = (x, y, a) =>
      pose(
        clamp(x, viewport.x - 12 * units - b.x, viewport.x + viewport.width + 12 * units - b.x - b.width),
        clamp(y, viewport.y - 12 * units - b.y, viewport.y + viewport.height + 12 * units - b.y - b.height),
        a,
      );
    const angle = between(-5, 5) * piece.weight;
    const current = new DOMMatrixReadOnly(
      getComputedStyle(piece.element).transform,
    );
    const currentAngle = (Math.atan2(current.b, current.a) * 180) / Math.PI;
    // Retarget from the visible pose, with a short attack and a longer return.
    const duration = between(1150, 1500);
    const times = [...new Set([...Array.from({ length: 61 }, (_, i) => i / 60), SCATTER_ATTACK_MS / duration])].sort((a, b) => a - b);
    const frames = times.map(t => {
      const elapsed = t * duration;
      const pulse = scatterEnvelope(elapsed, duration);
      const remainder = elapsed < SCATTER_ATTACK_MS ? 1 - pulse : 0;
      return {
        transform: limit(
          current.e * remainder + dx * pulse,
          current.f * remainder + dy * pulse,
          currentAngle * remainder + angle * pulse,
        ),
        offset: t,
      };
    });
    start(
      piece,
      frames,
      duration,
      0,
    );
  }

  function cancelAll() {
    for (const animation of running.values()) animation.cancel();
    running.clear();
  }

  return {
    prepare,
    get activeRow() {
      return activeRow;
    },
    setActive(row, immediate = false) {
      if (row === activeRow) {
        if (!row && immediate) cancelAll();
        return;
      }
      // On pointer exit, an existing burst completes its own return to rest.
      if (immediate) cancelAll();
      activeRow = row;
      lastPoint = null;
      // Entering a drawing only enables hit testing; nudge touches nearby pieces.
    },
    nudge(row, x, y) {
      if (row !== activeRow) return;
      const surface = row.querySelector(surfaceSelector);
      const box = surface.getBoundingClientRect();
      if (
        x < box.left - 8 ||
        x > box.right + 8 ||
        y < box.top - 8 ||
        y > box.bottom + 8
      )
        return;
      const now = performance.now();
      if (
        (lastPoint && Math.hypot(x - lastPoint.x, y - lastPoint.y) < 3)
      )
        return;
      lastPoint = { x, y };
      const svg = surface.querySelector("svg");
      const svgBox = svg.getBoundingClientRect();
      const viewport = svg.viewBox.baseVal;
      const units = viewport.width / 176;
      const scale = Math.min(svgBox.width / viewport.width, svgBox.height / viewport.height);
      for (const piece of prepare(row)) {
        if (now - (piece.lastNudge ?? -Infinity) < SCATTER_RETRIGGER_MS) continue;
        // Screen bounds include both normal motion and CSS perspective. SVG screen
        // matrices omit parts of that projection in some browser engines.
        const bounds = piece.element.getBoundingClientRect();
        const dx = (bounds.x + bounds.width / 2 - x) / scale;
        const dy = (bounds.y + bounds.height / 2 - y) / scale;
        const distance = Math.hypot(dx, dy);
        if (distance >= 28 * units) continue;
        const direction =
          Math.atan2(dy, dx) + between(-0.35, 0.35);
        const strength = (1 - distance / (28 * units)) * 9.6 * units * piece.weight;
        piece.lastNudge = now;
        disturb(
          piece,
          Math.cos(direction) * strength + between(-0.5, 0.5) * units,
          Math.sin(direction) * strength + between(-0.5, 0.5) * units,
        );
      }
    },
    dispose() {
      cancelAll();
      prepared.clear();
      activeRow = null;
      lastPoint = null;
    },
  };
}
