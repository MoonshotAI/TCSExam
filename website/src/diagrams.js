export const symbols = {
  theorem:
    '<path d="M9 28L22 9l13 19M22 9v33M22 27L9 42m13-15 13 15"/><circle cx="9" cy="28" r="3"/><circle cx="35" cy="28" r="3"/>',
  solver: '<path d="M8 12h12v9H8zm18 15h12v9H26zM20 16h14v11M8 36h10v-9h8"/>',
  construction:
    '<path d="M22 5L5 17l6 22h22l6-22zM22 5l-5 23-6 11m6-11 16 11M5 17l28 22M5 17l34 0M39 17L11 39m6-11 22-11"/>',
  open: '<path d="M15 16a8 8 0 1 1 13 6c-5 3-6 5-6 9"/><circle cx="22" cy="39" r="1.5"/>',
};
export const icon = (track, cls = "") =>
  `<svg class="track-icon ${cls}" aria-hidden="true" viewBox="0 0 44 48" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round">${symbols[track]}</svg>`;
