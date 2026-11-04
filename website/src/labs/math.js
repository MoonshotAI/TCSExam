// Bounded, synthetic teaching examples. No benchmark instances or result records.
export const pairs = (n) =>
  Array.from({ length: n }, (_, i) =>
    Array.from({ length: n - i - 1 }, (_, j) => [i, i + j + 1]),
  ).flat();
export const combinations = (xs, k) =>
  k === 0
    ? [[]]
    : xs.flatMap((x, i) =>
        combinations(xs.slice(i + 1), k - 1).map((rest) => [x, ...rest]),
      );
export const permutations = (xs) =>
  xs.length
    ? xs.flatMap((x, i) =>
        permutations(xs.filter((_, j) => i !== j)).map((rest) => [x, ...rest]),
      )
    : [[]];
export const mod = (x, n) => ((x % n) + n) % n;
export const sum = (xs) => xs.reduce((a, b) => a + b, 0);
export function corners(cells, n = 5) {
  const out = [];
  for (let y = 0; y < n; y++)
    for (let x = 0; x < n; x++)
      for (let d = 1; d < n; d++) {
        const ids = [y * n + x, y * n + mod(x + d, n), mod(y + d, n) * n + x];
        if (ids.every((i) => cells[i])) out.push({ x, y, d, ids });
      }
  return out;
}
export function foldedWords() {
  return Array.from({ length: 25 }, (_, i) => {
    const a = i % 5,
      b = Math.floor(i / 5);
    return { a, b, values: [1, 2, 4, 3].map((x) => (a + b * x) % 5) };
  });
}
export const blockDistance = (a, b) =>
  Number(a[0] !== b[0] || a[1] !== b[1]) +
  Number(a[2] !== b[2] || a[3] !== b[3]);
export function fourier(f) {
  return f.map(
    (_, k) =>
      sum(
        f.map(
          (x, i) =>
            x * ((i & k).toString(2).split("1").length % 2 === 1 ? 1 : -1),
        ),
      ) / f.length,
  );
}
export const forrelationBias = (f) =>
  fourier(f).map((x) =>
    Math.max(
      -1,
      Math.min(1, Math.sqrt(f.length / (100 * Math.log2(f.length))) * x),
    ),
  );
export const cutWeight = (edges, side) =>
  sum(edges.map(([a, b, w]) => (side[a] !== side[b] ? w : 0)));
export const hamming = (a, b) => sum(a.map((v, i) => Number(v !== b[i])));
export function shortCycles(n, edges) {
  const has = (a, b) =>
    edges.some(([u, v]) => (u === a && v === b) || (u === b && v === a));
  const triangles = combinations(
    Array.from({ length: n }, (_, i) => i),
    3,
  ).filter((v) => pairs(3).every(([a, b]) => has(v[a], v[b])));
  const squares = [];
  for (const [a, b, c, d] of combinations(
    Array.from({ length: n }, (_, i) => i),
    4,
  ))
    for (const vs of [
      [a, b, c, d],
      [a, b, d, c],
      [a, c, b, d],
    ])
      if (vs.every((v, i) => has(v, vs[(i + 1) % 4]))) squares.push(vs);
  return { triangles, squares };
}
export const monoCliques = (n, colors, k, color) =>
  combinations(
    Array.from({ length: n }, (_, i) => i),
    k,
  ).filter((vs) =>
    pairs(k).every(
      ([a, b]) =>
        colors[
          pairs(n).findIndex(
            ([u, v]) =>
              u === Math.min(vs[a], vs[b]) && v === Math.max(vs[a], vs[b]),
          )
        ] === color,
    ),
  );
export function matrixRank(matrix) {
  const a = matrix.map((row) => [...row]);
  let rank = 0;
  for (let c = 0; c < a[0].length && rank < a.length; c++) {
    const p = a.findIndex((row, i) => i >= rank && Math.abs(row[c]) > 1e-9);
    if (p < 0) continue;
    [a[p], a[rank]] = [a[rank], a[p]];
    const v = a[rank][c];
    a[rank] = a[rank].map((x) => x / v);
    for (let r = 0; r < a.length; r++)
      if (r !== rank) {
        const t = a[r][c];
        a[r] = a[r].map((x, j) => x - t * a[rank][j]);
      }
    rank++;
  }
  return rank;
}
export const scheduleCourses = [
  { name: "A", students: 35, group: 0, minDays: 2 },
  { name: "B", students: 20, group: 0, minDays: 2 },
  { name: "C", students: 25, group: 1, minDays: 2 },
];
export function scheduleScore(slots) {
  const rooms = [40, 20],
    hard = [];
  let capacity = 0,
    days = 0,
    compact = 0,
    stability = 0;
  for (let i = 0; i < 6; i++) {
    const c = scheduleCourses[Math.floor(i / 2)],
      period = Math.floor(slots[i] / 2),
      room = slots[i] % 2;
    if (c.name === "C" && period === 0)
      hard.push("C is unavailable in the first period");
    capacity += Math.max(0, c.students - rooms[room]);
    for (let j = 0; j < i; j++) {
      if (slots[j] === slots[i]) hard.push("Two lectures occupy one room");
      if (
        Math.floor(slots[j] / 2) === period &&
        scheduleCourses[Math.floor(j / 2)].group === c.group
      )
        hard.push("Curriculum conflict");
    }
    const adjacent = slots.some(
      (v, j) =>
        j !== i &&
        scheduleCourses[Math.floor(j / 2)].group === c.group &&
        Math.floor(Math.floor(v / 2) / 3) === Math.floor(period / 3) &&
        Math.abs(Math.floor(v / 2) - period) === 1,
    );
    if (!adjacent) compact += 2;
  }
  for (let c = 0; c < 3; c++) {
    const vs = slots.slice(c * 2, c * 2 + 2);
    days += 5 * Math.max(0, 2 - new Set(vs.map((v) => Math.floor(v / 6))).size);
    stability += new Set(vs.map((v) => v % 2)).size - 1;
  }
  return {
    hard,
    capacity,
    days,
    compact,
    stability,
    penalty: capacity + days + compact + stability,
  };
}
export const processWeights = [4, 3, 3, 2, 2, 1],
  processServices = ["A", "B", "A", "C", "B", "C"],
  initialMachines = [0, 0, 1, 1, 2, 2];
export function machineScore(assignment) {
  const loads = [0, 0, 0];
  assignment.forEach((m, i) => (loads[m] += processWeights[i]));
  const conflicts = pairs(6).filter(
    ([i, j]) =>
      assignment[i] === assignment[j] &&
      processServices[i] === processServices[j],
  ).length;
  const moves = assignment.filter((m, i) => m !== initialMachines[i]).length,
    load = sum(loads.map((v) => Math.max(0, v - 5)));
  return {
    loads,
    conflicts,
    overloads: loads.filter((v) => v > 8).length,
    moves,
    load,
    cost: moves + load,
  };
}
export const matchNeighbors = [[0, 1], [0], [1, 2]];
export function greedyMatching(order) {
  const used = [];
  for (const v of order) {
    const u = matchNeighbors[v].find((u) => !used.includes(u));
    if (u !== undefined) used.push(u);
  }
  return used.length;
}
export function programPath(bits) {
  const path = [0];
  for (const b of bits) path.push((path.at(-1) + b) % 4);
  return path;
}
export function prgWords(kind) {
  return Array.from({ length: kind === 0 ? 4 : 8 }, (_, i) => {
    const [a, b, c] = i
      .toString(2)
      .padStart(kind === 0 ? 2 : 3, "0")
      .split("")
      .map(Number);
    return kind === 0 ? [a, b, a, b] : [a, b, c, a ^ b ^ c];
  });
}
export function programStats(kind, accept) {
  const all = Array.from({ length: 16 }, (_, i) =>
    Array.from({ length: 4 }, (_, j) => (i >> j) & 1),
  );
  const test = (b) => accept.includes(programPath(b).at(-1));
  const uniform = all.filter(test).length / 16,
    generated = prgWords(kind).filter(test).length / prgWords(kind).length;
  return { uniform, generated, error: Math.abs(uniform - generated) };
}
export const petersenEdges = [
  ...Array.from({ length: 5 }, (_, i) => [i, (i + 1) % 5]),
  ...Array.from({ length: 5 }, (_, i) => [i, i + 5]),
  ...Array.from({ length: 5 }, (_, i) => [i + 5, ((i + 2) % 5) + 5]),
];
export function metricClosure(n, edges) {
  const d = Array.from({ length: n }, (_, i) =>
    Array.from({ length: n }, (_, j) => (i === j ? 0 : Infinity)),
  );
  for (const [a, b] of edges) d[a][b] = d[b][a] = 1;
  for (let k = 0; k < n; k++)
    for (let i = 0; i < n; i++)
      for (let j = 0; j < n; j++)
        d[i][j] = Math.min(d[i][j], d[i][k] + d[k][j]);
  return d;
}
export function fractionalCuts(n, edges, weight = 2 / 3) {
  let min = Infinity;
  for (let mask = 1; mask < (1 << n) - 1; mask++) {
    const size = mask.toString(2).replaceAll("0", "").length;
    if (size < 2 || size > n - 2) continue;
    min = Math.min(
      min,
      sum(
        edges.map(([a, b]) =>
          ((mask >> a) & 1) !== ((mask >> b) & 1) ? weight : 0,
        ),
      ),
    );
  }
  return min;
}
// A standard five-line Frege derivation, represented as an AST so size is computed.
export const atom = "p",
  imp = (a, b) => [a, b];
const pp = imp(atom, atom),
  one = imp(atom, imp(pp, atom)),
  two = imp(atom, pp),
  four = imp(two, pp);
export const fregeProof = [
  { f: one, rule: "Axiom 1", deps: [] },
  { f: two, rule: "Axiom 1", deps: [] },
  { f: imp(one, four), rule: "Axiom 2", deps: [] },
  { f: four, rule: "Modus ponens · 1, 3", deps: [0, 2] },
  { f: pp, rule: "Modus ponens · 2, 4", deps: [1, 3] },
];
export const formulaSize = (f) =>
  Array.isArray(f) ? 1 + formulaSize(f[0]) + formulaSize(f[1]) : 1;
export const formulaText = (f) =>
  Array.isArray(f) ? `(${formulaText(f[0])} → ${formulaText(f[1])})` : f;
