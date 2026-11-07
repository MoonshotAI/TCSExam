import {conjectureTooltip} from './conjecture-note.js';

export function mountConjectureNotes() {
  const tooltip = document.createElement('div');
  tooltip.id = 'conjecture-score-tooltip';
  tooltip.className = 'conjecture-tooltip';
  tooltip.setAttribute('role', 'tooltip');
  tooltip.textContent = conjectureTooltip;
  tooltip.hidden = true;
  document.body.append(tooltip);
  let active;
  const ref = target => target?.closest?.('[data-conjecture-note], [data-conjecture-hint]');
  const hide = () => {
    active?.removeAttribute('aria-describedby');
    active = null;
    tooltip.hidden = true;
  };
  const position = () => {
    if (!active?.isConnected) return hide();
    const box = active.getBoundingClientRect();
    if (box.bottom < 0 || box.top > innerHeight || box.right < 0 || box.left > innerWidth) return hide();
    const width = tooltip.offsetWidth, height = tooltip.offsetHeight;
    const left = Math.max(12, Math.min(box.left + box.width / 2 - width / 2, innerWidth - width - 12));
    const top = box.top > height + 16 ? box.top - height - 8 : box.bottom + 8;
    tooltip.style.left = `${left}px`;
    tooltip.style.top = `${top}px`;
  };
  const show = anchor => {
    hide();
    active = anchor;
    anchor.setAttribute('aria-describedby', tooltip.id);
    tooltip.hidden = false;
    position();
  };
  document.addEventListener('pointerover', event => {
    if (event.pointerType === 'touch') return;
    const anchor = ref(event.target);
    if (anchor && anchor !== active) show(anchor);
  });
  document.addEventListener('pointerout', event => {
    if (!active || active.contains(event.relatedTarget) || tooltip.contains(event.relatedTarget)) return;
    if (ref(event.target) || tooltip.contains(event.target)) hide();
  });
  document.addEventListener('focusin', event => {
    const anchor = ref(event.target);
    if (anchor) show(anchor);
    else hide();
  });
  document.addEventListener('focusout', event => {
    if (ref(event.target)) hide();
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') hide();
  });
  document.addEventListener('scroll', () => {
    if (active?.matches(':hover') || active === document.activeElement || tooltip.matches(':hover')) position();
    else hide();
  }, true);
  window.addEventListener('resize', () => { if (active) position(); });
  document.addEventListener('click', event => {
    const link = event.target.closest('[data-conjecture-note]');
    if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return;
    const details = document.querySelector('#open-conjecture-details');
    if (!details) return;
    event.preventDefault();
    hide();
    details.open = true;
    details.querySelector('summary').focus({preventScroll: true});
    details.scrollIntoView({block: 'nearest', behavior: 'instant'});
  });
}
