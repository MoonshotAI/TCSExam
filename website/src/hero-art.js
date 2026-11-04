import "./hero-art.css";

export function mountHeroArt(root) {
  const cards = [...root.querySelectorAll("[data-explore]")];
  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  const dialog = document.querySelector("#task-dialog");
  const visible = new Set();
  const controller = new AbortController();
  const { signal } = controller;
  const stop = (card) => card.classList.remove("is-illustrating");
  const blocked = () => reduced.matches || document.hidden || dialog.open;
  const sync = () => {
    for (const card of cards) {
      card.classList.toggle("is-illustrating", visible.has(card) && !blocked());
    }
  };
  // The drawings are rendered into the HTML at build time. Only attach motion;
  // initial paint, slow connections and pages without JavaScript use the same SVGs.
  // Watch the drawing itself so its animation follows what the reader can see.
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        const card = entry.target.closest("[data-explore]");
        if (entry.isIntersecting && entry.intersectionRatio >= 0.15) {
          visible.add(card);
        } else {
          visible.delete(card);
        }
      }
      sync();
    },
    { threshold: [0, 0.15] },
  );
  cards.forEach((card) => observer.observe(card.querySelector(".research-art")));
  document.addEventListener("visibilitychange", sync, { signal });
  reduced.addEventListener("change", sync, { signal });
  const modalObserver = new MutationObserver(sync);
  modalObserver.observe(dialog, {
    attributes: true,
    attributeFilter: ["open"],
  });
  return () => {
    controller.abort();
    observer.disconnect();
    modalObserver.disconnect();
    cards.forEach(stop);
  };
}
