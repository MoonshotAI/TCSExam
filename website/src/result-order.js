// Keep ties in source order and place missing scores after every measured score.
export function sortByScore(rows, score) {
  return [...rows].sort((a, b) => {
    const left = score(a), right = score(b);
    if (left == null) return right == null ? 0 : 1;
    if (right == null) return -1;
    return right - left;
  });
}
