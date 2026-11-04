const percentage = new Intl.NumberFormat('en-US', {
  style: 'percent',
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
  useGrouping: false,
});

// Keep the unit in the heading. Intl scales before rounding, including ties
// such as 1.0495 → 105.0, without an intermediate floating-point multiplication.
export function formatScore(score) {
  return score === null || score === undefined ? '—' : percentage.formatToParts(score)
    .filter(part => part.type !== 'percentSign').map(part => part.value).join('');
}
