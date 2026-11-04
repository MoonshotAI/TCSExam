import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import * as M from "../src/labs/math.js";
import { examples } from "../src/labs/examples.js";

test("historical example prototypes remain bounded and resettable", () => {
  const data = JSON.parse(
    readFileSync(new URL("../public/data/benchmark.json", import.meta.url)),
  );
  assert.deepEqual(
    Object.keys(examples).sort(),
    data.tasks.map((t) => t.id).sort(),
  );
  for (const e of Object.values(examples)) {
    assert(e.scope.length > 30);
    const original = e.initial(),
      s = e.initial();
    for (let i = 0; i < 15; i++) {
      const r = e.render(s);
      assert(r.figure && r.stats && r.caption);
      assert(!r.figure.includes("NaN"));
      e.step(s);
    }
    assert.deepEqual(e.initial(), original);
  }
});
test("corner enumeration uses nonzero modular steps", () => {
  assert.equal(M.corners(Array(25).fill(true)).length, 100);
  assert.equal(M.corners(Array(25).fill(false)).length, 0);
  const cells = Array(25).fill(false);
  [0, 1, 5].forEach((i) => (cells[i] = true));
  assert.equal(M.corners(cells).length, 1);
  const wrap = Array(25).fill(false);
  [24, 20, 4].forEach((i) => (wrap[i] = true));
  assert(M.corners(wrap).some((c) => c.x === 4 && c.y === 4 && c.d === 1));
});
test("folded code evaluates generator powers and counts whole-block errors", () => {
  const words = M.foldedWords();
  assert.equal(new Set(words.map((w) => w.values.join(","))).size, 25);
  assert.deepEqual(
    words.find((w) => w.a === 0 && w.b === 1).values,
    [1, 2, 4, 3],
  );
  assert.equal(M.blockDistance([1, 2, 4, 3], [0, 0, 4, 3]), 1);
  assert.equal(M.blockDistance([1, 2, 4, 3], [0, 2, 4, 0]), 2);
});
test("Walsh normalization satisfies Parseval; Forrelation probability is bounded", () => {
  assert.deepEqual(M.fourier(Array(8).fill(1)), [1, 0, 0, 0, 0, 0, 0, 0]);
  const f = [1, 1, -1, 1, -1, 1, -1, -1];
  assert.equal(M.sum(M.fourier(f).map((x) => x * x)), 1);
  assert.equal(M.forrelationBias(Array(8).fill(1))[0], Math.sqrt(8 / 300));
  assert(M.forrelationBias(f).every((b) => b >= -1 && b <= 1));
});
test("packing rejects overflow and first-fit completes the synthetic example", () => {
  const e = examples["bpp-bpplib"],
    s = e.initial();
  e.update(s, "bin:0");
  e.update(s, "bin:0");
  assert.equal(s.next, 1);
  assert.deepEqual(s.bins, [[6]]);
  while (!e.done(s)) e.step(s);
  assert(s.bins.every((b) => M.sum(b) <= 10));
  assert.equal(s.bins.length, 2);
  assert.deepEqual(s.bins.flat().sort(), [2, 3, 4, 5, 6]);
});
test("bidding transfers coins between players and applies the selected edge weight", () => {
  const e = examples["discrete-bidding-games"],
    s = e.initial();
  e.step(s);
  assert.equal(s.budget, 3);
  assert.equal(s.energy, 5);
  assert.equal(s.vertex, 0);
  s.bid = 0;
  e.step(s);
  assert.equal(s.budget, 4);
  assert.equal(s.energy, 3);
  assert.equal(s.vertex, 1);
  s.bid = 1;
  const before = structuredClone(s);
  e.step(s);
  assert.deepEqual(s, before);
});
test("timetable distinguishes infeasibility from all four soft penalties", () => {
  const base = [0, 6, 2, 8, 4, 10],
    r = M.scheduleScore(base);
  assert.equal(r.hard.length, 0);
  assert.equal(r.penalty, 4);
  assert.equal(r.days, 0);
  assert.equal(r.capacity, 0);
  const a = [...base];
  a[0] = 1;
  const cap = M.scheduleScore(a);
  assert.equal(cap.capacity, 15);
  assert.equal(cap.stability, 1);
  const b = [...base];
  b[2] = 0;
  assert(M.scheduleScore(b).hard.length >= 2);
  const c = [...base];
  c[1] = 4;
  assert.equal(M.scheduleScore(c).days, 5);
});
test("machine assignment uses capacity, conflict, load and move costs independently", () => {
  const original = M.machineScore(M.initialMachines);
  assert.equal(original.cost, 2);
  assert.equal(original.conflicts, 0);
  assert.equal(original.overloads, 0);
  const moved = [...M.initialMachines];
  moved[2] = 0;
  const r = M.machineScore(moved);
  assert.equal(r.moves, 1);
  assert.equal(r.conflicts, 1);
  assert.equal(r.overloads, 1);
});
test("cut objective and Hamming distance recompute from the actual object", () => {
  assert.equal(
    M.cutWeight(
      [
        [0, 1, 3],
        [1, 2, 2],
        [0, 2, 4],
      ],
      [0, 1, 0],
    ),
    5,
  );
  assert.equal(M.hamming([0, 1, 1, 0], [0, 0, 1, 1]), 2);
  const s = examples["binary-code-a24-10"].initial();
  assert.equal(
    Math.min(...M.pairs(4).map(([a, b]) => M.hamming(s.words[a], s.words[b]))),
    3,
  );
});
test("short cycles are counted once and clique checks use the correct color and size", () => {
  const k4 = M.shortCycles(4, M.pairs(4));
  assert.equal(k4.triangles.length, 4);
  assert.equal(k4.squares.length, 3);
  const c7 = Array.from({ length: 7 }, (_, i) => [i, (i + 1) % 7]);
  assert.deepEqual(M.shortCycles(7, c7), { triangles: [], squares: [] });
  assert.equal(M.monoCliques(6, Array(15).fill(0), 4, 0).length, 15);
  assert.equal(M.monoCliques(6, Array(15).fill(1), 6, 1).length, 1);
  const s = examples["ramsey-r46"].initial();
  assert.equal(M.monoCliques(6, s.colors, 4, 0).length, 0);
  assert.equal(M.monoCliques(6, s.colors, 6, 1).length, 0);
});
test("Petersen LP point satisfies every subtour cut; metric tour has cost 11", () => {
  const d = M.metricClosure(10, M.petersenEdges),
    tour = [0, 1, 2, 3, 4, 9, 7, 5, 8, 6];
  assert.equal(M.sum(tour.map((v, i) => d[v][tour[(i + 1) % 10]])), 11);
  assert(M.fractionalCuts(10, M.petersenEdges) >= 2 - 1e-9);
  for (let v = 0; v < 10; v++)
    assert.equal(M.petersenEdges.filter((e) => e.includes(v)).length, 3);
  for (let a = 0; a < 10; a++)
    for (let b = 0; b < 10; b++)
      for (let c = 0; c < 10; c++) assert(d[a][c] <= d[a][b] + d[b][c]);
  // Exhaustive finite validation of the educational graph's non-Hamiltonicity.
  const nbr = Array.from({ length: 10 }, (_, v) =>
    M.petersenEdges
      .filter((e) => e.includes(v))
      .map((e) => (e[0] === v ? e[1] : e[0])),
  );
  const cycle = (v, mask) =>
    mask === 1023
      ? nbr[v].includes(0)
      : nbr[v].some((u) => !(mask & (1 << u)) && cycle(u, mask | (1 << u)));
  assert.equal(cycle(0, 1), false);
});
test("communication matrices use real rank, and an empty graph requires all queries", () => {
  assert.equal(
    M.matrixRank([
      [0, 0, 0, 0],
      [0, 1, 0, 1],
      [0, 0, 1, 1],
      [0, 1, 1, 0],
    ]),
    3,
  );
  const e = examples["evasiveness-graph-properties"],
    s = e.initial();
  for (let i = 0; i < 5; i++) e.step(s);
  assert.equal(e.done(s), false);
  e.step(s);
  assert.equal(e.done(s), true);
});
test("Frege derivation has correct modus-ponens dependencies and all lines are tautologies", () => {
  const equal = (a, b) => JSON.stringify(a) === JSON.stringify(b),
    ev = (f, p) => (Array.isArray(f) ? !ev(f[0], p) || ev(f[1], p) : p);
  for (const [i, line] of M.fregeProof.entries()) {
    assert(ev(line.f, false) && ev(line.f, true));
    if (line.deps.length) {
      const [a, b] = line.deps;
      assert(a < i && b < i);
      assert(equal(M.fregeProof[b].f[0], M.fregeProof[a].f));
      assert(equal(M.fregeProof[b].f[1], line.f));
    }
  }
  assert.equal(M.formulaSize(M.fregeProof.at(-1).f), 3);
});
test("online matching decisions are irrevocable and averaging uses all six orders", () => {
  assert.equal(M.permutations([0, 1, 2]).length, 6);
  assert.equal(
    M.sum(M.permutations([0, 1, 2]).map(M.greedyMatching)) / 6,
    13 / 6,
  );
  const e = examples["online-matching-random-order"],
    s = e.initial();
  e.update(s, "match:0");
  assert.equal(s.matches.length, 1);
  e.update(s, "match:0");
  assert.equal(s.matches.length, 1);
  assert.equal(s.step, 1);
});
test("PRG comparison uses exact finite uniform input and seed distributions", () => {
  assert.deepEqual(M.programPath([1, 0, 1, 1]), [0, 1, 1, 2, 3]);
  assert.deepEqual(M.programStats(0, [0]), {
    uniform: 1 / 8,
    generated: 1 / 2,
    error: 3 / 8,
  });
  assert.deepEqual(M.programStats(1, [0]), {
    uniform: 1 / 8,
    generated: 1 / 4,
    error: 1 / 8,
  });
  assert.deepEqual(M.programStats(1, [0, 2]), {
    uniform: 1 / 2,
    generated: 1,
    error: 1 / 2,
  });
});
