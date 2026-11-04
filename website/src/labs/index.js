import { examples } from "./examples.js";
import { publishedExamples } from "./catalogue.js";
import "./labs.css";

export function mountTaskLab(root, task) {
  const example = examples[task.id];
  const options = publishedExamples[task.id];
  if (!example || !options) return () => {};
  let state = example.initial(),
    timer = null,
    ticks = 0,
    disposed = false;
  root.innerHTML = `<section class="task-lab" aria-labelledby="lab-title" data-lab="${task.id}"><div class="lab-heading"><div><h3 id="lab-title">${example.title}</h3></div><div class="lab-playback">${options.playback ? '<button type="button" data-lab-play aria-pressed="false">Play</button>' : ""}<button type="button" data-lab-reset>Reset</button></div></div><p class="lab-instruction">${example.instruction}</p><div class="lab-content"></div><p class="lab-scope">${example.scope}</p></section>`;
  const content = root.querySelector(".lab-content"),
    play = root.querySelector("[data-lab-play]");
  content.innerHTML =
    '<div class="lab-figure"></div><div class="lab-controls"></div><dl class="lab-stats" aria-live="polite" aria-atomic="true"></dl><p class="lab-caption"></p>';
  function draw(keepControls = false) {
    const active = document.activeElement,
      focusKey = root.contains(active)
        ? (active.dataset.action ?? active.dataset.control)
        : null,
      selection = active?.selectionStart;
    const r = example.render(state);
    content.querySelector(".lab-figure").innerHTML = r.figure;
    if (!keepControls)
      content.querySelector(".lab-controls").innerHTML = r.controls ?? "";
    else
      content
        .querySelectorAll(".lab-range")
        .forEach(
          (label) =>
            (label.querySelector("output").textContent =
              label.querySelector("input").value),
        );
    content.querySelector(".lab-stats").innerHTML = r.stats;
    content.querySelector(".lab-caption").textContent = r.caption;
    if (focusKey) {
      const target = [
        ...content.querySelectorAll("[data-action],[data-control]"),
      ].find((e) => (e.dataset.action ?? e.dataset.control) === focusKey);
      target?.focus({ preventScroll: true });
      if (typeof selection === "number" && target?.type === "text")
        target.setSelectionRange(selection, selection);
    }
    if (play) play.disabled = !!example.done?.(state);
  }
  function stop() {
    clearInterval(timer);
    timer = null;
    ticks = 0;
    if (play) {
      play.textContent = "Play";
      play.setAttribute("aria-pressed", "false");
    }
  }
  function tick() {
    const dialog = root.closest("dialog");
    if (disposed || document.hidden || !root.isConnected || (dialog && !dialog.open)) {
      stop();
      return;
    }
    const before = JSON.stringify(state);
    example.step(state);
    draw();
    ticks++;
    if (
      example.done?.(state) ||
      ticks >= 12 ||
      JSON.stringify(state) === before
    )
      stop();
  }
  const click = (e) => {
    if (e.target.closest("[data-lab-play]")) {
      if (timer) {
        stop();
        return;
      }
      play.textContent = "Pause";
      play.setAttribute("aria-pressed", "true");
      ticks = 0;
      timer = setInterval(tick, 900);
      tick();
      return;
    }
    if (e.target.closest("[data-lab-reset]")) {
      stop();
      state = example.initial();
      draw();
      return;
    }
    const target = e.target.closest("[data-action]");
    if (!target || target.disabled) return;
    stop();
    example.update(state, target.dataset.action);
    draw();
  };
  const input = (e) => {
    if (!e.target.matches("[data-control]")) return;
    stop();
    example.update(state, e.target.dataset.control, e.target.value);
    draw(e.target.type === "range");
  };
  const keyboard = (e) => {
    const target = e.target.closest("svg [data-action]");
    if (target && ["Enter", " "].includes(e.key)) {
      e.preventDefault();
      target.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    }
  };
  let dragging = false;
  const dragMove = (e) => {
    if (!dragging) return;
    const drawing = root.querySelector("svg");
    const point = drawing.createSVGPoint();
    point.x = e.clientX;
    point.y = e.clientY;
    const local = point.matrixTransform(drawing.getScreenCTM().inverse());
    const angle = Math.round(
      ((Math.atan2(125 - local.y, local.x - 260) * 180) / Math.PI + 360) % 360,
    );
    example.update(state, "angle", angle);
    draw();
  };
  const dragStart = (e) => {
    const point = e.target.closest('[data-action^="point:"]');
    if (task.id !== "kissing-d13" || !point || e.button !== 0) return;
    stop();
    example.update(state, point.dataset.action);
    dragging = true;
    root.setPointerCapture(e.pointerId);
    e.preventDefault();
    dragMove(e);
  };
  const dragEnd = (e) => {
    dragging = false;
    if (root.hasPointerCapture(e.pointerId))
      root.releasePointerCapture(e.pointerId);
  };
  root.addEventListener("pointerdown", dragStart);
  root.addEventListener("pointermove", dragMove);
  root.addEventListener("pointerup", dragEnd);
  root.addEventListener("pointercancel", dragEnd);
  const visibility = () => {
    if (document.hidden) stop();
  };
  root.addEventListener("click", click);
  root.addEventListener("input", input);
  root.addEventListener("keydown", keyboard);
  document.addEventListener("visibilitychange", visibility);
  draw();
  return () => {
    disposed = true;
    stop();
    root.removeEventListener("click", click);
    root.removeEventListener("input", input);
    root.removeEventListener("keydown", keyboard);
    document.removeEventListener("visibilitychange", visibility);
    root.removeEventListener("pointerdown", dragStart);
    root.removeEventListener("pointermove", dragMove);
    root.removeEventListener("pointerup", dragEnd);
    root.removeEventListener("pointercancel", dragEnd);
  };
}
