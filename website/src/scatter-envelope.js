// A short outward movement follows the pointer; the longer return stays gentle.
export const SCATTER_ATTACK_MS = 140;
export const SCATTER_RETRIGGER_MS = 32;

export function scatterEnvelope(elapsed, duration) {
  if (elapsed <= SCATTER_ATTACK_MS) {
    const t = Math.max(0, elapsed / SCATTER_ATTACK_MS);
    return 1 - (1 - t) ** 2;
  }
  const t = Math.min(1, (elapsed - SCATTER_ATTACK_MS) / (duration - SCATTER_ATTACK_MS));
  return (1 - t) ** 3 * (1 + 3 * t);
}
