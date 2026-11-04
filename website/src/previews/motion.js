import { createScatterMotion } from "./scatter.js";
import { prepareIllustrationMotion } from "./illustration-motion.js";

export function mountPreviewMotion(grid, {
  itemSelector = ".task-card, .task-tile",
  surfaceSelector = ".task-preview",
  tilt = true,
  createDisturbance = createScatterMotion,
} = {}) {
  const rows = [...grid.querySelectorAll(itemSelector)].filter(row => row.querySelector(".pv-scene")),
    visible = new Set();
  const reduced = matchMedia("(prefers-reduced-motion: reduce)"),
    hover = matchMedia("(hover: hover)");
  const dialog = document.querySelector("#task-dialog");
  const scatter = createDisturbance({ surfaceSelector });
  const ambientGroups = [
    "corner",
    "transfer",
    "fold",
    "walker",
    "drop",
    "timetable",
    "migrate",
    "code-scan",
    "orbit",
    "message",
  ];
  rows.forEach((row) => {
    prepareIllustrationMotion(row);
    // Keep a visible point on every moving path, including short edges in a small thumbnail.
    row.querySelectorAll(".pv-tracing .pv-trace").forEach((el) => {
      el.setAttribute("pathLength", "1");
      const point = el.cloneNode(false);
      point.classList.replace("pv-trace", "pv-flow-head");
      el.after(point);
    });
    // Create additive wrappers before CSS motion starts; hover must not restart it.
    scatter.prepare(row);
    row
      .querySelectorAll(ambientGroups.map((name) => `.pv-${name}`).join(","))
      .forEach((el) => el.classList.add("pv-ambient"));
    row
      .querySelectorAll(".pv-tracing .pv-trace, .pv-tracing .pv-flow-head")
      .forEach((el) => el.classList.add("pv-ambient"));
  });

  const finishing = new Map();
  const normalAnimations = (row) =>
    [...row.querySelectorAll(".pv-ambient")].flatMap((el) =>
      el.getAnimations(),
    );
  const cancelFinish = (row) => {
    finishing.delete(row);
    row.classList.remove("is-preview-finishing");
  };
  const resetNormal = (row) => {
    cancelFinish(row);
    for (const animation of normalAnimations(row)) {
      animation.pause();
      animation.currentTime = 0;
      animation.effect.updateTiming({ iterations: Infinity });
    }
  };
  const playNormal = (row) => {
    cancelFinish(row);
    for (const animation of normalAnimations(row)) {
      if (animation.playState === "finished") animation.currentTime = 0;
      animation.effect.updateTiming({ iterations: Infinity });
      animation.play();
    }
  };
  const finishNormal = (row, immediate) => {
    if (immediate) {
      resetNormal(row);
      return;
    }
    const token = {};
    finishing.set(row, token);
    row.classList.add("is-preview-finishing");
    const motions = normalAnimations(row);
    // Finish the current cycle at its original speed and along its original path.
    // Each cycle begins and ends in the same canonical pose, independent of list order.
    for (const animation of motions) {
      const duration = animation.effect.getTiming().duration;
      animation.effect.updateTiming({
        iterations: Math.max(
          1,
          Math.ceil((animation.currentTime || 0) / duration),
        ),
      });
    }
    Promise.all(motions.map((animation) => animation.finished))
      .then(() => {
        if (finishing.get(row) === token) resetNormal(row);
      })
      .catch(() => {}); // Filtering, reduced motion and disposal cancel old animations.
  };

  let hovered = null,
    focused = null,
    keyboardFocus = false,
    lastPointer = null;
  let tilted = null,
    pointerFrame = null,
    pointerPosition = null;
  const resetTilt = () => {
    if (pointerFrame !== null) cancelAnimationFrame(pointerFrame);
    pointerFrame = null;
    pointerPosition = null;
    if (tilted) {
      tilted.style.removeProperty("--preview-rx");
      tilted.style.removeProperty("--preview-ry");
      tilted.classList.remove("is-pointer-tilting");
      tilted = null;
    }
  };
  const queueTilt = (e) => {
    if (e.pointerType === "touch" || !hover.matches || reduced.matches) return;
    const row = rowOf(e.target);
    if (keyboardFocus) {
      // Scrolling a focused row under a stationary pointer must not steal keyboard interaction.
      if (lastPointer?.x === e.clientX && lastPointer?.y === e.clientY) return;
      keyboardFocus = false;
      hovered = row;
      sync();
    }
    lastPointer = { x: e.clientX, y: e.clientY };
    if (!row?.classList.contains("is-preview-active")) return;
    const bounds = row.querySelector(surfaceSelector).getBoundingClientRect();
    if (
      e.clientX < bounds.left ||
      e.clientX > bounds.right ||
      e.clientY < bounds.top ||
      e.clientY > bounds.bottom
    ) {
      scatter.setActive(null);
      resetTilt();
      return;
    }
    scatter.setActive(row);
    pointerPosition = { row, x: e.clientX, y: e.clientY };
    if (pointerFrame !== null) return;
    // One update per pointer frame; no animation loop while the pointer rests.
    pointerFrame = requestAnimationFrame(() => {
      pointerFrame = null;
      const point = pointerPosition;
      pointerPosition = null;
      if (
        !point ||
        point.row !== hovered ||
        !point.row.classList.contains("is-preview-active")
      )
        return;
      scatter.nudge(point.row, point.x, point.y);
      if (!tilt) return;
      if (tilted && tilted !== point.row) resetTilt();
      tilted = point.row;
      const box = tilted.querySelector(surfaceSelector).getBoundingClientRect();
      const clamp = (value) => Math.max(-1, Math.min(1, value));
      const x = clamp((point.x - box.x - box.width / 2) / (box.width * 0.75));
      const y = clamp((point.y - box.y - box.height / 2) / (box.height * 0.75));
      tilted.style.setProperty("--preview-rx", `${(-y * 4.5).toFixed(2)}deg`);
      tilted.style.setProperty("--preview-ry", `${(x * 6).toFixed(2)}deg`);
      tilted.classList.add("is-pointer-tilting");
    });
  };
  const rowOf = (node) =>
    node instanceof Element ? node.closest(itemSelector) : null;
  const sync = () => {
    const suspended = document.hidden || dialog?.open || reduced.matches;
    const active = keyboardFocus ? focused : hovered;
    const next = active && visible.has(active) && !suspended ? active : null;
    for (const row of rows) {
      const wasRunning = row.classList.contains("is-preview-running");
      const immediate = suspended || !visible.has(row);
      if (row === next && !wasRunning) playNormal(row);
      row.classList.toggle("is-preview-running", row === next);
      row.classList.toggle("is-preview-active", row === next);
      row.classList.toggle("is-preview-suspended", immediate);
      if ((wasRunning && row !== next) || (finishing.has(row) && immediate))
        finishNormal(row, immediate);
    }
    if (suspended || (scatter.activeRow && !visible.has(scatter.activeRow)))
      scatter.setActive(null, true);
    else if (scatter.activeRow !== next || keyboardFocus)
      scatter.setActive(null);
    if (tilted && !tilted.classList.contains("is-preview-active")) resetTilt();
    if (!hovered || suspended) resetTilt();
  };
  const enter = (e) => {
    if (e.pointerType === "touch" || !hover.matches || keyboardFocus) return;
    hovered = rowOf(e.target);
    sync();
    queueTilt(e);
  };
  const leave = (e) => {
    if (keyboardFocus) return;
    hovered = rowOf(e.relatedTarget);
    if (hovered && !grid.contains(hovered)) hovered = null;
    sync();
  };
  const focus = (e) => {
    keyboardFocus = e.target.matches(":focus-visible");
    if (keyboardFocus) hovered = null;
    focused = rowOf(e.target);
    // Keep rapid Tab navigation visible even while an anchor scroll is still settling.
    if (keyboardFocus)
      focused?.scrollIntoView({ block: "nearest", behavior: "instant" });
    sync();
  };
  const blur = (e) => {
    focused = rowOf(e.relatedTarget);
    if (focused && !grid.contains(focused)) focused = null;
    sync();
  };
  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (entry.isIntersecting) visible.add(entry.target);
      else visible.delete(entry.target);
    }
    sync();
  });
  rows.forEach((row) => observer.observe(row));
  const modalObserver = new MutationObserver(sync);
  if (dialog) modalObserver.observe(dialog, {
    attributes: true,
    attributeFilter: ["open"],
  });
  sync();
  grid.addEventListener("pointermove", queueTilt);
  grid.addEventListener("pointerover", enter);
  grid.addEventListener("pointerout", leave);
  grid.addEventListener("focusin", focus);
  grid.addEventListener("focusout", blur);
  document.addEventListener("visibilitychange", sync);
  reduced.addEventListener("change", sync);
  return () => {
    scatter.dispose();
    resetTilt();
    observer.disconnect();
    modalObserver.disconnect();
    grid.removeEventListener("pointermove", queueTilt);
    grid.removeEventListener("pointerover", enter);
    grid.removeEventListener("pointerout", leave);
    grid.removeEventListener("focusin", focus);
    grid.removeEventListener("focusout", blur);
    document.removeEventListener("visibilitychange", sync);
    reduced.removeEventListener("change", sync);
    rows.forEach((row) => {
      cancelFinish(row);
      row.classList.remove(
        "is-preview-active",
        "is-preview-running",
        "is-preview-suspended",
      );
      row
        .querySelectorAll(".pv-ambient")
        .forEach((el) =>
          el.getAnimations().forEach((animation) => animation.cancel()),
        );
    });
  };
}
