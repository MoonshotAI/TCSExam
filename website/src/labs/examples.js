import * as M from "./math.js";
const { sum, pairs, mod } = M;
const esc = (s) =>
  String(s).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const btn = (action, label, active = false, disabled = false) =>
  `<button type="button" data-action="${action}" ${disabled ? "disabled" : ""}>${label}</button>`;
const select = (key, label, options, value) =>
  `<label>${label}<select data-control="${key}">${options.map((t, i) => `<option value="${i}" ${i === value ? "selected" : ""}>${esc(t)}</option>`).join("")}</select></label>`;
const range = (key, label, value, min, max) =>
  `<label class="lab-range">${label} <output>${value}</output><input aria-label="${esc(label)}" data-control="${key}" type="range" min="${min}" max="${max}" value="${value}" /></label>`;
const stats = (...xs) =>
  xs
    .map(([label, value]) => `<div><dt>${label}</dt><dd>${value}</dd></div>`)
    .join("");
const svg = (body, label, h = 250) =>
  `<svg class="lab-svg" viewBox="0 0 520 ${h}" role="group" aria-label="${esc(label)}">${body}</svg>`;
const text = (x, y, t, cls = "") =>
  `<text x="${x}" y="${y}" class="${cls}" text-anchor="middle">${esc(t)}</text>`;
const line = (a, b, cls = "", label = "", color = "", fraction = 0.5) =>
  `<line x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}" class="lab-edge ${cls}" ${color ? `style="stroke:${color}"` : ""}/>${label !== "" ? text(a[0] + (b[0] - a[0]) * fraction, a[1] + (b[1] - a[1]) * fraction - 6, label, "lab-weight") : ""}`;
const node = (p, label, action = "", active = false, extra = "") =>
  `<g ${action ? `role="button" tabindex="0" data-action="${action}" aria-label="${esc(extra || label)}" aria-pressed="${active}"` : ""} class="lab-node ${active ? "is-active" : ""}">${action ? `<circle class="lab-node-hit" cx="${p[0]}" cy="${p[1]}" r="36"/>` : ""}<circle cx="${p[0]}" cy="${p[1]}" r="19"/>${text(p[0], p[1] + 5, label)}</g>`;
const ring = (n, r = 94, cx = 260, cy = 126, phase = -Math.PI / 2) =>
  Array.from({ length: n }, (_, i) => [
    cx + r * Math.cos(phase + (i * 2 * Math.PI) / n),
    cy + r * Math.sin(phase + (i * 2 * Math.PI) / n),
  ]);
function graph(
  n,
  edges,
  {
    sides = [],
    edgeAction = "",
    nodeAction = "",
    activeEdges = [],
    labels = [],
    edgeColors = [],
    edgeStates = [],
    points = ring(n),
  } = {},
) {
  return svg(
    edges
      .map(
        ([a, b, w], i) =>
          `<g ${edgeAction ? `role="button" tabindex="0" data-action="${edgeAction}:${i}" aria-label="Edge ${a + 1} to ${b + 1}${edgeStates[i] ? `, ${edgeStates[i]}` : edgeColors[i] === "var(--lab-red)" ? ", red" : edgeColors[i] === "var(--lab-blue)" ? ", blue" : ""}">` : ">"}${edgeAction ? `<line class="lab-hit" x1="${points[a][0]}" y1="${points[a][1]}" x2="${points[b][0]}" y2="${points[b][1]}"/>` : ""}${line(points[a], points[b], activeEdges.includes(i) ? "is-active" : "", w ?? "", edgeColors[i], 0.35 + (i % 3) * 0.15)}</g>`,
      )
      .join("") +
      points
        .map((p, i) =>
          node(
            p,
            labels[i] ?? i + 1,
            nodeAction ? `${nodeAction}:${i}` : "",
            !!sides[i],
            `Vertex ${i + 1}${sides.length ? `, group ${sides[i] ? "B" : "A"}` : ""}`,
          ),
        )
        .join(""),
    "Interactive graph",
  );
}
const cell = (action, label, active, extra = "") =>
  `<button class="lab-cell ${active ? "is-active" : ""} ${extra}" type="button" data-action="${action}" aria-label="${esc(action.startsWith("bit:") ? `Word ${+action.split(":")[1] + 1}, bit ${+action.split(":")[2] + 1}, value ${label}` : action.startsWith("entry:") ? `Alice ${action.split(":")[1]}, Bob ${action.split(":")[2]}, value ${label}` : action.startsWith("symbol:") ? `Received symbol ${+action.split(":")[1] + 1}, value ${label}` : action.startsWith("flip:") ? `Function entry ${+action.split(":")[1]}, value ${label}` : `Point ${label}`)}" aria-pressed="${active}">${label}</button>`;
export const examples = {};
examples["corners-quasipoly"] = {
  title: "Find a corner",
  scope:
    "A 5 × 5 example in (ℤ/5ℤ)². The theorem concerns all finite abelian groups.",
  instruction:
    "Toggle points. Step through the corners that remain; coordinates wrap modulo 5.",
  initial: () => ({
    cells: Array.from(
      { length: 25 },
      (_, i) => i % 6 === 0 || [1, 5, 2, 10].includes(i),
    ),
    index: 0,
  }),
  render(s) {
    const cs = M.corners(s.cells),
      c = cs[s.index % cs.length];
    return {
      figure: `<div class="lab-grid grid-five">${s.cells.map((v, i) => cell(`point:${i}`, `${i % 5},${Math.floor(i / 5)}`, v, c?.ids.includes(i) ? "is-marked" : "")).join("")}</div>`,
      controls: btn("step", "Next corner", false, !cs.length),
      stats: stats(
        ["Selected points", sum(s.cells.map(Number)) + "/25"],
        ["Corners", cs.length],
        ["Current step d", c?.d ?? "—"],
      ),
      caption: c
        ? `Highlighted: (${c.x}, ${c.y}), (${mod(c.x + c.d, 5)}, ${c.y}), (${c.x}, ${mod(c.y + c.d, 5)}).`
        : "No nontrivial corner remains in this small set.",
    };
  },
  update(s, a) {
    if (a.startsWith("point:")) {
      s.cells[+a.split(":")[1]] = !s.cells[+a.split(":")[1]];
      s.index = 0;
    }
    if (a === "step") s.index++;
  },
  step(s) {
    s.index++;
  },
};
examples["discrete-bidding-games"] = {
  title: "Budgets change who controls the move",
  scope:
    "A two-vertex energy game. Equal bids are excluded here; the formal task includes a tie-breaking advantage.",
  instruction:
    "Choose a bid. The higher bidder pays the other player and selects an edge. Track both the budget and the energy.",
  initial: () => ({
    budget: 5,
    energy: 3,
    bid: 2,
    turn: 0,
    vertex: 0,
    history: [],
    message: "Pres starts with 5 of the 10 coins and 3 energy.",
  }),
  render(s) {
    const opp = Math.min(1, 10 - s.budget);
    return {
      figure: svg(
        `<path class="lab-edge" d="M180 116 Q260 30 340 116"/><path class="lab-edge is-active" d="M340 136 Q260 220 180 136"/><path class="lab-edge is-active" d="M144 112 C60 0 60 230 144 139"/><path class="lab-edge" d="M376 112 C460 0 460 230 376 139"/>${text(260, 65, "→ B: −2")}${text(260, 211, "A: +2 ←")}${text(90, 125, "+2")}${text(430, 125, "−2")}${node([160, 125], "A", "", s.vertex === 0)}${node([360, 125], "B", "", s.vertex === 1)}${text(260, 128, `Energy ${s.energy}`, "lab-big")}`,
        "Budget and energy game",
      ),
      controls:
        range("bid", "Your bid", s.bid, 0, s.budget) +
        btn("bid", "Run this turn", false, s.bid === opp || s.energy < 0) +
        `<span class="lab-control-note">Opponent bids ${opp}. ${s.bid === opp ? "Choose an unequal bid." : ""}</span>`,
      stats: stats(
        ["Pres budget", s.budget],
        ["Opponent budget", 10 - s.budget],
        ["Energy", s.energy],
      ),
      caption: s.message,
    };
  },
  update(s, a, v) {
    if (a === "bid" && v !== undefined) s.bid = +v;
    else if (a === "bid") this.step(s);
  },
  step(s) {
    if (s.energy < 0) return;
    const opp = Math.min(1, 10 - s.budget);
    if (s.bid === opp) return;
    const win = s.bid > opp;
    s.budget += win ? -s.bid : opp;
    s.energy += win ? 2 : -2;
    s.vertex = win ? 0 : 1;
    s.turn++;
    s.message = `Turn ${s.turn}: ${win ? "Pres" : "Opponent"} paid ${win ? s.bid : opp} coins and took the ${win ? "+2" : "−2"} edge.${s.energy < 0 ? " Energy is negative: this play has failed." : ""}`;
    s.bid = Math.min(s.bid, s.budget);
  },
};
examples["folded-rs-gsb"] = {
  title: "A list of nearby codewords",
  scope:
    "Degree-at-most-1 polynomials over ℤ/5ℤ, evaluated at 1, 2, 4, 3 and folded into two blocks. These small parameters illustrate the definition only.",
  instruction:
    "Click a received symbol to cycle its value. Change the block-error radius to see which of the 25 codewords remain in the list.",
  initial: () => ({ received: [1, 2, 4, 3], radius: 1 }),
  render(s) {
    const list = M.foldedWords().filter(
      (w) => M.blockDistance(w.values, s.received) <= s.radius,
    );
    return {
      figure: `<div class="lab-code-received"><span>Received word</span>${s.received.map((v, i) => cell(`symbol:${i}`, v, true, i === 2 ? "block-start" : "")).join("")}</div><div class="lab-code-list">${M.foldedWords()
        .map(
          (w) =>
            `<div class="lab-codeword ${list.includes(w) ? "is-active" : ""}"><span>f(x) = ${w.a} + ${w.b}x</span><code>${w.values.slice(0, 2).join(" ")} | ${w.values.slice(2).join(" ")}</code></div>`,
        )
        .join("")}</div>`,
      controls: range("radius", "Allowed block errors", s.radius, 0, 2),
      stats: stats(
        ["Codewords in list", list.length + "/25"],
        ["Block length", 2],
        ["Radius", s.radius + "/2 blocks"],
      ),
      caption:
        "A folded block counts as one error if either of its two entries differs. The actual task proves a parameter-dependent list-size bound.",
    };
  },
  update(s, a, v) {
    if (a === "radius") s.radius = +v;
    if (a.startsWith("symbol:")) {
      const i = +a.split(":")[1];
      s.received[i] = (s.received[i] + 1) % 5;
    }
  },
  step(s) {
    s.radius = (s.radius + 1) % 3;
  },
};
const polyEdges = [
  [0, 1],
  [1, 2],
  [2, 3],
  [3, 0],
  [0, 2],
];
examples["negations-small-depth"] = {
  title: "Inspect a graph-polynomial coefficient",
  scope:
    "A four-vertex example of the polynomial definition. It is not a spectral-expander example or a lower-bound proof.",
  instruction:
    "Toggle vertices to choose the support of a bit string. The induced edge count determines the coefficient of its monomial.",
  initial: () => ({ chosen: [true, true, false, false] }),
  render(s) {
    const e = polyEdges.filter(([a, b]) => s.chosen[a] && s.chosen[b]).length;
    return {
      figure: graph(4, polyEdges, {
        sides: s.chosen,
        nodeAction: "vertex",
        activeEdges: polyEdges.map(([a, b], i) =>
          s.chosen[a] && s.chosen[b] ? i : -1,
        ),
      }),
      controls: btn("step", "Next support"),
      stats: stats(
        ["Induced edges e", e],
        ["Coefficient (e − 1)²", (e - 1) ** 2],
        ["Expanded expression", `${e * e} − ${2 * e} + 1`],
      ),
      caption: `The monomial x₁,${+s.chosen[0]} x₂,${+s.chosen[1]} x₃,${+s.chosen[2]} x₄,${+s.chosen[3]} has coefficient ${(e - 1) ** 2}. Subtraction appears in the expression, while the final coefficient is nonnegative.`,
    };
  },
  update(s, a) {
    if (a.startsWith("vertex:")) {
      const i = +a.split(":")[1];
      s.chosen[i] = !s.chosen[i];
    } else this.step(s);
  },
  step(s) {
    const x = (sum(s.chosen.map((v, i) => +v * 2 ** i)) + 1) % 16;
    s.chosen = s.chosen.map((_, i) => !!(x & (1 << i)));
  },
};
examples["quantum-crypto-algorithmica"] = {
  title: "From Boolean values to Fourier bias",
  scope:
    "n = 3, N = 8, ε = 1/300. This computes the task’s Fourier coefficients and Forrelation biases exactly up to floating-point display.",
  instruction:
    "Flip an entry of f. Its Walsh–Fourier coefficients determine the probability that each g entry is +1.",
  initial: () => ({ f: [1, 1, -1, 1, -1, 1, -1, -1] }),
  render(s) {
    const fhat = M.fourier(s.f),
      bias = M.forrelationBias(s.f);
    return {
      figure: `<div class="lab-spectrum">${s.f.map((v, i) => `<div><span>${i.toString(2).padStart(3, "0")}</span>${cell(`flip:${i}`, v > 0 ? "+1" : "−1", v > 0)}<div class="lab-spectrum-bar"><i style="height:${Math.abs(fhat[i]) * 75}px;${fhat[i] < 0 ? "top:50%;background:var(--lab-red)" : "bottom:50%"}"></i></div><code>${fhat[i].toFixed(2)}</code><small>${((1 + bias[i]) * 50).toFixed(1)}%</small></div>`).join("")}</div>`,
      controls: btn("step", "Flip next entry"),
      stats: stats(
        ["Fourier energy Σ f̂²", sum(fhat.map((x) => x * x)).toFixed(3)],
        ["Largest |bias|", Math.max(...bias.map(Math.abs)).toFixed(3)],
        ["Uniform reference P(g = +1)", "50%"],
      ),
      caption:
        "Columns show the input index, f value, Fourier coefficient and P(g = +1). Each g entry would be sampled independently with bias clip(√(εN) f̂). This visual does not prove pseudorandomness.",
    };
  },
  update(s, a) {
    if (a.startsWith("flip:")) s.f[+a.split(":")[1]] *= -1;
    else this.step(s);
  },
  step(s) {
    s.cursor = ((s.cursor ?? -1) + 1) % 8;
    s.f[s.cursor] *= -1;
  },
};
const items = [6, 5, 4, 3, 2];
examples["bpp-bpplib"] = {
  title: "Pack the next item",
  scope:
    "Five synthetic items, each bin has capacity 10. No released or hidden benchmark instance is used.",
  instruction:
    "Choose a bin for the next item. A full bin rejects the move. Use Play to watch first-fit place the items in order.",
  initial: () => ({
    bins: [[]],
    next: 0,
    message: "Next item: 6. Try filling a bin before opening another.",
  }),
  render(s) {
    return {
      figure: `<div class="lab-items">${items.map((w, i) => `<span class="${i < s.next ? "is-done" : i === s.next ? "is-next" : ""}">${w}</span>`).join("")}</div><div class="lab-bins">${s.bins.map((bin, i) => `<button type="button" data-action="bin:${i}" aria-label="Place next item in bin ${i + 1}"><div class="lab-bin-stack">${bin.map((w) => `<span style="height:${w * 10}%">${w}</span>`).join("")}</div><span>Bin ${i + 1} · ${sum(bin)}/10</span></button>`).join("")}</div>`,
      controls:
        btn("new", "New bin", false, s.next === items.length) +
        btn("step", "First-fit step", false, s.next === items.length),
      stats: stats(
        ["Items placed", s.next + "/5"],
        ["Bins used", s.bins.filter((b) => b.length).length],
        ["Volume lower bound", 2],
      ),
      caption: s.message,
    };
  },
  update(s, a) {
    if (a === "new" && s.next < 5) {
      s.bins.push([]);
      this.update(s, `bin:${s.bins.length - 1}`);
    }
    if (a.startsWith("bin:") && s.next < 5) {
      const i = +a.split(":")[1],
        w = items[s.next];
      if (sum(s.bins[i]) + w > 10) {
        s.message = `Bin ${i + 1} has only ${10 - sum(s.bins[i])} free. Item ${w} does not fit.`;
        return;
      }
      s.bins[i].push(w);
      s.next++;
      s.message =
        s.next === 5
          ? `All items fit in ${s.bins.filter((b) => b.length).length} bins. The total weight gives a lower bound of 2.`
          : `Placed ${w} in bin ${i + 1}. Next item: ${items[s.next]}.`;
    }
    if (a === "step") this.step(s);
  },
  step(s) {
    if (s.next === 5) return;
    let i = s.bins.findIndex((b) => sum(b) + items[s.next] <= 10);
    if (i < 0) {
      i = s.bins.length;
      s.bins.push([]);
    }
    this.update(s, `bin:${i}`);
  },
  done: (s) => s.next === 5,
};
examples["curriculum-itc2007"] = {
  title: "Build a small timetable",
  scope:
    "Six lectures, two rooms (40 and 20 seats), two days with three periods each. A and B share a curriculum; C has its own.",
  instruction:
    "Select a lecture, then click its new room and period. C is unavailable in the first period. Each course should span both days.",
  initial: () => ({ slots: [0, 6, 2, 8, 4, 10], lecture: 0 }),
  render(s) {
    const r = M.scheduleScore(s.slots);
    return {
      figure: `<div class="lab-timetable"><span></span><b>Room 1 · 40 seats</b><b>Room 2 · 20 seats</b>${Array.from({ length: 6 }, (_, p) => `<span>Day ${Math.floor(p / 3) + 1}<small>Period ${(p % 3) + 1}</small></span>${[0, 1].map((room) => `<button type="button" data-action="slot:${p * 2 + room}" aria-label="Day ${Math.floor(p / 3) + 1}, period ${(p % 3) + 1}, room ${room + 1}">${s.slots.map((v, i) => (v === p * 2 + room ? `<i class="${s.lecture === i ? "is-active" : ""}">${"ABC"[Math.floor(i / 2)]}${(i % 2) + 1}</i>` : "")).join("") || "—"}</button>`).join("")}`).join("")}</div>`,
      controls: select(
        "lecture",
        "Lecture",
        [
          "A1 · 35 students",
          "A2 · 35 students",
          "B1 · 20 students",
          "B2 · 20 students",
          "C1 · 25 students",
          "C2 · 25 students",
        ],
        s.lecture,
      ),
      stats: stats(
        ["Hard violations", r.hard.length],
        ["Soft penalties", r.penalty],
        ["Valid timetable", r.hard.length ? "No" : "Yes"],
      ),
      caption: `${r.hard[0] ?? "All hard constraints hold."} Penalties: room capacity ${r.capacity}, working days ${r.days}, isolated lectures ${r.compact}, room changes ${r.stability}.`,
    };
  },
  update(s, a, v) {
    if (a === "lecture") s.lecture = +v;
    if (a.startsWith("slot:")) s.slots[s.lecture] = +a.split(":")[1];
  },
  step(s) {
    s.slots[s.lecture] = (s.slots[s.lecture] + 1) % 12;
  },
};
const cutEdges = [
  [0, 1, 3],
  [1, 2, 2],
  [2, 3, 4],
  [3, 4, 2],
  [4, 5, 3],
  [5, 0, 1],
  [0, 3, 2],
  [1, 4, 1],
  [2, 5, 2],
];
examples["maxcut-mqlib"] = {
  title: "Move a vertex across the cut",
  scope:
    "A synthetic six-vertex weighted graph. The displayed objective is recomputed from the partition.",
  instruction:
    "Click a vertex to switch its group. Colored edges cross the cut; their weights add to the objective.",
  initial: () => ({ side: [0, 0, 0, 1, 1, 1] }),
  render(s) {
    const value = M.cutWeight(cutEdges, s.side),
      best = Math.max(
        ...Array.from({ length: 64 }, (_, mask) =>
          M.cutWeight(
            cutEdges,
            Array.from({ length: 6 }, (_, i) => (mask >> i) & 1),
          ),
        ),
      );
    return {
      figure: graph(6, cutEdges, {
        sides: s.side,
        nodeAction: "vertex",
        activeEdges: cutEdges.map(([a, b], i) =>
          s.side[a] !== s.side[b] ? i : -1,
        ),
      }),
      controls: btn("step", "Best single-vertex move"),
      stats: stats(
        ["Cut weight", value],
        ["Total edge weight", sum(cutEdges.map((e) => e[2]))],
        ["Toy optimum", best],
      ),
      caption:
        "Checking all 64 partitions gives the optimum for this example. The benchmark requires a reusable solver for much larger unseen graphs.",
    };
  },
  update(s, a) {
    if (a.startsWith("vertex:")) s.side[+a.split(":")[1]] ^= 1;
    else this.step(s);
  },
  step(s) {
    let best = M.cutWeight(cutEdges, s.side),
      chosen = -1;
    for (let i = 0; i < 6; i++) {
      const trial = [...s.side];
      trial[i] ^= 1;
      const score = M.cutWeight(cutEdges, trial);
      if (score > best) {
        best = score;
        chosen = i;
      }
    }
    if (chosen >= 0) s.side[chosen] ^= 1;
  },
  done: (s) =>
    Array.from({ length: 6 }, (_, i) => {
      const t = [...s.side];
      t[i] ^= 1;
      return M.cutWeight(cutEdges, t);
    }).every((v) => v <= M.cutWeight(cutEdges, s.side)),
};
examples["mr-roadef2012"] = {
  title: "Move a process, inspect the cost",
  scope:
    "A simplified CPU-only example: capacity 8, safety capacity 5, unit migration cost, and same-service conflicts. Other ROADEF constraints are omitted.",
  instruction:
    "Select a process, then its destination machine. Moving a process may lower load cost but adds migration cost.",
  initial: () => ({ assignment: [...M.initialMachines], process: 0 }),
  render(s) {
    const r = M.machineScore(s.assignment);
    return {
      figure: `<div class="lab-machines">${r.loads
        .map(
          (load, m) =>
            `<button data-action="machine:${m}" type="button" aria-label="Move selected process to machine ${m + 1}"><strong>Machine ${m + 1}</strong><div class="lab-load"><i style="height:${Math.min(100, (load / 8) * 100)}%;${load > 8 ? "background:var(--lab-red)" : ""}"></i><span class="lab-safety"></span></div><span>${load}/8 CPU</span><small>${
              s.assignment
                .map((v, i) =>
                  v === m ? `${M.processServices[i]}${i + 1}` : "",
                )
                .filter(Boolean)
                .join(" · ") || "Empty"
            }</small></button>`,
        )
        .join("")}</div>`,
      controls: select(
        "process",
        "Process",
        M.processWeights.map(
          (w, i) => `${M.processServices[i]}${i + 1} · ${w} CPU`,
        ),
        s.process,
      ),
      stats: stats(
        ["Load + move cost", r.cost],
        ["Capacity violations", r.overloads],
        ["Service conflicts", r.conflicts],
      ),
      caption: `Load penalty ${r.load} + migration penalty ${r.moves}. The dashed line is safety capacity; it affects the objective. Exceeding total capacity makes the assignment invalid.`,
    };
  },
  update(s, a, v) {
    if (a === "process") s.process = +v;
    if (a.startsWith("machine:")) s.assignment[s.process] = +a.split(":")[1];
  },
  step(s) {
    s.assignment[s.process] = (s.assignment[s.process] + 1) % 3;
  },
};
examples["qbf-qbfeval"] = {
  title: "Quantifier order changes the answer",
  scope:
    "A two-variable formula: (x ∨ y) ∧ (¬x ∨ ¬y), equivalently x ≠ y. This visual illustrates truth evaluation, not a Q-resolution certificate.",
  instruction:
    "Compare “for every x, choose y” with “choose y, for every x”. Step upward from the leaves to evaluate the quantifiers.",
  initial: () => ({ order: 0, step: 0 }),
  render(s) {
    const universalFirst = s.order === 0,
      leaves = [0, 1, 1, 0],
      middle = universalFirst ? [1, 1] : [0, 0],
      root = universalFirst;
    const pts = [
      [260, 32],
      [135, 108],
      [385, 108],
      [70, 202],
      [190, 202],
      [330, 202],
      [450, 202],
    ];
    return {
      figure: svg(
        [
          [0, 1],
          [0, 2],
          [1, 3],
          [1, 4],
          [2, 5],
          [2, 6],
        ]
          .map(([a, b], i) =>
            line(pts[a], pts[b], s.step > 0 ? "is-active" : "", i % 2),
          )
          .join("") +
          node(
            pts[0],
            s.step >= 2 ? (root ? "T" : "F") : "?",
            "",
            s.step >= 2 && root,
          ) +
          pts
            .slice(1, 3)
            .map((p, i) =>
              node(
                p,
                s.step >= 1 ? (middle[i] ? "T" : "F") : "?",
                "",
                s.step >= 1 && !!middle[i],
              ),
            )
            .join("") +
          pts
            .slice(3)
            .map((p, i) => node(p, leaves[i] ? "T" : "F", "", !!leaves[i]))
            .join("") +
          text(470, 37, universalFirst ? "∀x · AND" : "∃y · OR") +
          text(470, 112, universalFirst ? "∃y · OR" : "∀x · AND"),
        "Quantified formula evaluation tree",
      ),
      controls:
        select("order", "Quantifier prefix", ["∀x ∃y", "∃y ∀x"], s.order) +
        btn("step", "Evaluate next level", false, s.step >= 2),
      stats: stats(
        ["Leaf assignments", 4],
        ["Quantifier levels evaluated", s.step + "/2"],
        [
          "Formula truth",
          s.step >= 2 ? (root ? "True" : "False") : "Step to evaluate",
        ],
      ),
      caption: universalFirst
        ? "Each x has a suitable y: choose the opposite bit. The existential choice can depend on x."
        : "A single y must work for both values of x. Neither choice works.",
    };
  },
  update(s, a, v) {
    if (a === "order") {
      s.order = +v;
      s.step = 0;
    } else this.step(s);
  },
  step(s) {
    s.step = Math.min(2, s.step + 1);
  },
  done: (s) => s.step >= 2,
};
examples["binary-code-a24-10"] = {
  title: "Keep codewords separated",
  scope:
    "Four editable 6-bit words with target distance 3. The actual task asks for 24-bit words at distance at least 10.",
  instruction:
    "Flip a bit. Every pair must differ in at least the target number of positions. Highlight a pair to inspect its differing bits.",
  initial: () => ({
    words: [
      [0, 0, 0, 0, 0, 0],
      [1, 1, 1, 0, 0, 0],
      [1, 0, 0, 1, 1, 0],
      [0, 1, 1, 1, 1, 0],
    ],
    pair: 0,
    target: 3,
  }),
  render(s) {
    const ps = pairs(4),
      [a, b] = ps[s.pair],
      distances = ps.map(([a, b]) => M.hamming(s.words[a], s.words[b]));
    return {
      figure: `<div class="lab-bit-rows">${s.words.map((word, r) => `<div><span>Word ${r + 1}</span>${word.map((v, c) => cell(`bit:${r}:${c}`, v, !!v, (r === a || r === b) && s.words[a][c] !== s.words[b][c] ? "is-marked" : "")).join("")}</div>`).join("")}</div>`,
      controls:
        select(
          "pair",
          "Inspect pair",
          ps.map(([a, b]) => `Words ${a + 1} and ${b + 1}`),
          s.pair,
        ) + range("target", "Required distance", s.target, 1, 6),
      stats: stats(
        ["Selected pair distance", distances[s.pair]],
        ["Minimum pair distance", Math.min(...distances)],
        ["Violating pairs", distances.filter((d) => d < s.target).length],
      ),
      caption: `Highlighted positions are exactly the disagreements of words ${a + 1} and ${b + 1}. A repeated word has distance zero and cannot add a new codeword.`,
    };
  },
  update(s, a, v) {
    if (a === "pair") s.pair = +v;
    if (a === "target") s.target = +v;
    if (a.startsWith("bit:")) {
      const [, r, c] = a.split(":");
      s.words[+r][+c] ^= 1;
    }
  },
  step(s) {
    s.pair = (s.pair + 1) % 6;
  },
};
const allSeven = pairs(7),
  cycleSeven = allSeven.map(([a, b]) => b === a + 1 || (a === 0 && b === 6));
examples["ex-c3c4-maxedges"] = {
  title: "Add edges without short cycles",
  scope:
    "Seven vertices for inspection. The formal construction task fixes 124 vertices.",
  instruction:
    "Click a candidate edge to add or remove it. The checker here enumerates every triangle and every 4-cycle in this small graph.",
  initial: () => ({ edges: [...cycleSeven] }),
  render(s) {
    const es = allSeven.filter((_, i) => s.edges[i]),
      r = M.shortCycles(7, es),
      bad = r.triangles[0] ?? r.squares[0] ?? [],
      badEdges = allSeven.map(([a, b], i) =>
        bad.some(
          (v, j) =>
            (v === a && bad[(j + 1) % bad.length] === b) ||
            (v === b && bad[(j + 1) % bad.length] === a),
        )
          ? i
          : -1,
      );
    return {
      figure: graph(7, allSeven, {
        edgeAction: "edge",
        edgeStates: s.edges.map((value) => (value ? "present" : "absent")),
        activeEdges: badEdges,
        edgeColors: s.edges.map((yes, i) =>
          badEdges.includes(i)
            ? "var(--lab-red)"
            : yes
              ? "var(--accent)"
              : "#d8dbe2",
        ),
      }),
      controls:
        btn("cycle", "Restore 7-cycle") + btn("dense", "Show a dense graph"),
      stats: stats(
        ["Edges", es.length],
        ["Triangles", r.triangles.length],
        ["4-cycles", r.squares.length],
      ),
      caption: bad.length
        ? `One forbidden ${bad.length}-cycle is highlighted. Remove an edge of that cycle to break it.`
        : "No triangle or 4-cycle is present. Try adding another edge.",
    };
  },
  update(s, a) {
    if (a.startsWith("edge:")) {
      const i = +a.split(":")[1];
      s.edges[i] = !s.edges[i];
    }
    if (a === "cycle") s.edges = [...cycleSeven];
    if (a === "dense") s.edges = s.edges.map(() => true);
  },
  step(s) {
    const i = allSeven.findIndex((_, i) => !s.edges[i]);
    if (i >= 0) s.edges[i] = true;
  },
  done: (s) => s.edges.every(Boolean),
};
examples["kissing-d13"] = {
  title: "Separate points on a sphere",
  scope:
    "A two-dimensional unit circle, shown without projection. The benchmark requires an exact certificate in 13 dimensions.",
  instruction:
    "Drag a point, or select it and change its angle. All pairs must be separated by at least 60°. Add a seventh point to see why spacing matters.",
  initial: () => ({ angles: [0, 60, 120, 180, 240, 300], selected: 0 }),
  render(s) {
    const ps = pairs(s.angles.length),
      seps = ps.map(([a, b]) =>
        Math.min(
          mod(s.angles[a] - s.angles[b], 360),
          mod(s.angles[b] - s.angles[a], 360),
        ),
      ),
      pts = s.angles.map((a) => [
        260 + 94 * Math.cos((a * Math.PI) / 180),
        125 - 94 * Math.sin((a * Math.PI) / 180),
      ]),
      bad = ps.filter((_, i) => seps[i] < 60 - 1e-8),
      maxdot = Math.cos((Math.min(...seps) * Math.PI) / 180);
    return {
      figure: svg(
        `<circle class="lab-unit-circle" cx="260" cy="125" r="94"/>${bad.map(([a, b]) => line(pts[a], pts[b], "", "", "var(--lab-red)")).join("")}${line([260, 125], pts[s.selected], "is-active")}${node([260, 125], "0")}${pts.map((p, i) => node(p, i + 1, `point:${i}`, i === s.selected, `Select point ${i + 1}`)).join("")}`,
        "Points on the unit circle",
      ),
      controls:
        range("angle", "Selected point angle", s.angles[s.selected], 0, 359) +
        btn("add", "Add a seventh point", false, s.angles.length >= 7),
      stats: stats(
        ["Minimum separation", Math.min(...seps).toFixed(1) + "°"],
        ["Largest dot product", maxdot.toFixed(3)],
        ["Pairs below 60°", bad.length],
      ),
      caption:
        "For unit vectors, an angle of at least 60° is equivalent to a dot product of at most 1/2. The red segments identify violations in this 2D example.",
    };
  },
  update(s, a, v) {
    if (a === "angle") s.angles[s.selected] = +v;
    if (a.startsWith("point:")) s.selected = +a.split(":")[1];
    if (a === "add" && s.angles.length < 7) {
      s.angles.push(30);
      s.selected = 6;
    }
  },
  step(s) {
    s.angles[s.selected] = (s.angles[s.selected] + 15) % 360;
  },
};
const ramseyEdges = pairs(6);
examples["ramsey-r46"] = {
  title: "Color edges, avoid forbidden cliques",
  scope:
    "A complete graph on six vertices. The forbidden patterns remain a red K₄ and a blue K₆; this is only a small example.",
  instruction:
    "Click an edge to switch red and blue. Each color is also distinguished by its line style. Inspect the first forbidden clique when one appears.",
  initial: () => ({
    colors: ramseyEdges.map(([a, b]) =>
      a < 5 && b < 5 && (b === a + 1 || (a === 0 && b === 4)) ? 0 : 1,
    ),
  }),
  render(s) {
    const red = M.monoCliques(6, s.colors, 4, 0),
      blue = M.monoCliques(6, s.colors, 6, 1);
    const bad = red[0] ?? blue[0] ?? [];
    let figure = graph(6, ramseyEdges, {
      edgeAction: "edge",
      activeEdges: ramseyEdges.map(([a, b], i) =>
        bad.includes(a) && bad.includes(b) ? i : -1,
      ),
      edgeColors: s.colors.map((c) =>
        c ? "var(--lab-blue)" : "var(--lab-red)",
      ),
    });
    figure = figure.replaceAll(
      'style="stroke:var(--lab-blue)"',
      'style="stroke:var(--lab-blue);stroke-dasharray:7 4"',
    );
    return {
      figure,
      controls: btn("red", "All red") + btn("blue", "All blue"),
      stats: stats(
        ["Red K₄", red.length],
        ["Blue K₆", blue.length],
        ["Valid small coloring", red.length + blue.length ? "No" : "Yes"],
      ),
      caption:
        "Red is solid; blue is dashed. A valid n-vertex coloring establishes R(4,6) > n, but this small n does not approach the research target.",
    };
  },
  update(s, a) {
    if (a.startsWith("edge:")) s.colors[+a.split(":")[1]] ^= 1;
    if (a === "red") s.colors.fill(0);
    if (a === "blue") s.colors.fill(1);
  },
  step(s) {
    s.cursor = ((s.cursor ?? -1) + 1) % 15;
    s.colors[s.cursor] ^= 1;
  },
};
const pdist = M.metricClosure(10, M.petersenEdges),
  tour = [0, 1, 2, 3, 4, 9, 7, 5, 8, 6],
  ppts = [...ring(5, 103), ...ring(5, 49)],
  tourCost = sum(tour.map((v, i) => pdist[v][tour[(i + 1) % 10]]));
examples["tsp-gap"] = {
  title: "A fractional solution and a tour",
  scope:
    "The ten-vertex Petersen graph with shortest-path metric costs. This standard small example has LP value 10 and shortest-tour value 11.",
  instruction:
    "Compare fractional edge weights with a tour visiting every vertex. Step through the tour; its final shortcut costs 2.",
  initial: () => ({ mode: 0, step: 0 }),
  render(s) {
    const body =
      M.petersenEdges
        .map(([a, b]) =>
          line(
            ppts[a],
            ppts[b],
            s.mode === 0 ? "is-active" : "",
            s.mode === 0 ? "⅔" : "",
          ),
        )
        .join("") +
      (s.mode === 1
        ? tour
            .slice(0, s.step)
            .map((v, i) =>
              line(
                ppts[v],
                ppts[tour[(i + 1) % 10]],
                "is-active",
                pdist[v][tour[(i + 1) % 10]],
                "var(--accent)",
              ),
            )
            .join("")
        : "") +
      ppts
        .map((p, i) =>
          node(
            p,
            i + 1,
            "",
            s.mode === 1 && tour.slice(0, s.step + 1).includes(i),
          ),
        )
        .join("");
    return {
      figure: svg(body, "Petersen graph metric and tour"),
      controls:
        select("mode", "View", ["Fractional solution", "Tour"], s.mode) +
        btn(
          "step",
          "Trace next tour edge",
          false,
          s.mode === 1 && s.step === 10,
        ),
      stats: stats(
        ["LP optimum", 10],
        ["Shortest tour", tourCost],
        ["Tour / LP", (tourCost / 10).toFixed(2)],
      ),
      caption:
        s.mode === 0
          ? "Each support edge has x = 2/3: degree sums are 2 and all subtour cuts have weight at least 2. Since every metric edge costs at least 1, the degree constraints also give LP cost ≥ 10."
          : "The highlighted tour has cost 11. A cost-10 tour would be a Hamiltonian cycle in the Petersen graph, which has none.",
    };
  },
  update(s, a, v) {
    if (a === "mode") {
      s.mode = +v;
      s.step = s.mode ? 10 : 0;
    } else this.step(s);
  },
  step(s) {
    if (s.mode === 0) {
      s.mode = 1;
      s.step = 0;
    }
    s.step = Math.min(10, s.step + 1);
  },
  done: (s) => s.mode === 1 && s.step === 10,
};
const matrices = [
  Array.from({ length: 4 }, (_, a) =>
    Array.from({ length: 4 }, (_, b) => +(a === b)),
  ),
  Array.from({ length: 4 }, (_, a) =>
    Array.from(
      { length: 4 },
      (_, b) => ((a & b).toString(2).split("1").length - 1) % 2,
    ),
  ),
  Array.from({ length: 4 }, (_, a) =>
    Array.from({ length: 4 }, (_, b) => +!!(a & b)),
  ),
];
examples["log-rank-conjecture"] = {
  title: "Read a communication matrix",
  scope:
    "Two-bit inputs for Alice and Bob. The displayed three-bit protocol is an upper bound, not a computation of minimum communication complexity.",
  instruction:
    "Choose an input pair, then reveal the protocol one bit at a time: Alice sends her two bits; Bob returns the answer.",
  initial: () => ({ matrix: 1, row: 2, col: 3, step: 0 }),
  render(s) {
    const mat = matrices[s.matrix],
      answer = mat[s.row][s.col],
      rank = M.matrixRank(mat);
    return {
      figure: `<div class="lab-matrix"><span>Alice ↓ / Bob →</span>${[0, 1, 2, 3].map((v) => `<b>${v.toString(2).padStart(2, "0")}</b>`).join("")}${mat.map((row, a) => `<b>${a.toString(2).padStart(2, "0")}</b>${row.map((v, b) => cell(`entry:${a}:${b}`, v, a === s.row && b === s.col, (s.step === 1 && Math.floor(a / 2) === Math.floor(s.row / 2)) || (s.step === 2 && a === s.row) || (s.step === 3 && a === s.row && v === answer) ? "is-marked" : "")).join("")}`).join("")}</div><div class="lab-transcript">${[s.row >> 1, s.row & 1, answer].map((v, i) => `<span class="${s.step > i ? "is-active" : ""}">${i < 2 ? "Alice" : "Bob"}: ${s.step > i ? v : "?"}</span>`).join("")}</div>`,
      controls:
        select(
          "matrix",
          "Boolean function",
          ["Equality", "Two-bit inner product", "Nonempty bit intersection"],
          s.matrix,
        ) + btn("step", "Send next bit", false, s.step === 3),
      stats: stats(
        ["Real matrix rank", rank],
        ["log₂ rank", Math.log2(rank).toFixed(2)],
        ["Bits sent", s.step + "/3"],
      ),
      caption:
        s.step === 3
          ? `The transcript ends at answer ${answer}. The shaded cells are a monochromatic rectangle for this protocol leaf.`
          : "Each message narrows the possible inputs. Matrix rank is computed over the reals, not over the two-element field.",
    };
  },
  update(s, a, v) {
    if (a === "matrix") {
      s.matrix = +v;
      s.step = 0;
    }
    if (a.startsWith("entry:")) {
      const [, r, c] = a.split(":");
      s.row = +r;
      s.col = +c;
      s.step = 0;
    }
    if (a === "step") this.step(s);
  },
  step(s) {
    s.step = Math.min(3, s.step + 1);
  },
  done: (s) => s.step === 3,
};
const queryEdges = pairs(4);
examples["evasiveness-graph-properties"] = {
  title: "Does the hidden graph have any edge?",
  scope:
    "Four labeled vertices and the monotone, relabeling-invariant property “has at least one edge”. One property illustrates the query model; it does not settle the conjecture.",
  instruction:
    "Query an unknown edge by clicking it. One present edge establishes Yes; to establish No on the empty graph, all six pairs must be queried.",
  initial: () => ({ present: -1, queried: [] }),
  render(s) {
    const yes = s.queried.includes(s.present),
      done = yes || s.queried.length === 6;
    return {
      figure: graph(
        4,
        queryEdges.map(([a, b], i) => [
          a,
          b,
          s.queried.includes(i) ? (i === s.present ? "Yes" : "No") : "?",
        ]),
        {
          edgeAction: "query",
          edgeStates: queryEdges.map((_, i) =>
            s.queried.includes(i)
              ? i === s.present
                ? "present"
                : "absent"
              : "unqueried",
          ),
          activeEdges: queryEdges.map((_, i) =>
            s.queried.includes(i) ? i : -1,
          ),
          edgeColors: queryEdges.map((_, i) =>
            s.queried.includes(i)
              ? i === s.present
                ? "var(--accent)"
                : "#969ca7"
              : "#d8dbe2",
          ),
        },
      ),
      controls:
        select(
          "example",
          "Hidden graph",
          ["Empty graph", "One edge"],
          s.present < 0 ? 0 : 1,
        ) + btn("step", "Query next unknown pair", false, done),
      stats: stats(
        ["Queries", s.queried.length + "/6"],
        ["Property determined", done ? "Yes" : "No"],
        ["Answer", yes ? "Has an edge" : done ? "No edges" : "Undetermined"],
      ),
      caption: yes
        ? "A present edge is a witness, so this input allows an early answer."
        : "An unqueried pair could still be present. In the empty-graph case, the sixth query is necessary.",
    };
  },
  update(s, a, v) {
    if (a === "example") {
      s.present = +v ? 5 : -1;
      s.queried = [];
    }
    if (a.startsWith("query:") && !s.queried.includes(s.present)) {
      const i = +a.split(":")[1];
      if (!s.queried.includes(i)) s.queried.push(i);
    }
    if (a === "step") this.step(s);
  },
  step(s) {
    const i = queryEdges.findIndex((_, i) => !s.queried.includes(i));
    if (i >= 0) this.update(s, `query:${i}`);
  },
  done: (s) => s.queried.length === 6 || s.queried.includes(s.present),
};
examples["frege-not-pbounded"] = {
  title: "Follow a Frege proof",
  scope:
    "A five-line derivation of p → p using the first two axiom schemes and modus ponens from the task’s fixed system. It makes no proof-length lower-bound claim.",
  instruction:
    "Reveal one line at a time. Select a revealed line to highlight the earlier lines used by modus ponens. Proof size counts formula-tree nodes.",
  initial: () => ({ step: 1, selected: 0 }),
  render(s) {
    const proof = M.fregeProof,
      refs = proof[s.selected].deps;
    return {
      figure: `<ol class="lab-proof">${proof.map((p, i) => `<li class="${i >= s.step ? "unrevealed" : ""} ${refs.includes(i) ? "is-marked" : ""}"><button type="button" data-action="line:${i}" ${i >= s.step ? "disabled" : ""} aria-pressed="${s.selected === i}"><span class="lab-proof-formula">${i < s.step ? esc(M.formulaText(p.f)) : "…"}</span><small>${i < s.step ? `${p.rule} · ${M.formulaSize(p.f)} symbols` : "Unrevealed"}</small></button></li>`).join("")}</ol>`,
      controls: btn("step", "Reveal next line", false, s.step === 5),
      stats: stats(
        ["Lines revealed", s.step + "/5"],
        [
          "Total symbols",
          sum(proof.slice(0, s.step).map((p) => M.formulaSize(p.f))),
        ],
        ["Target formula size", 3],
      ),
      caption: refs.length
        ? `Line ${s.selected + 1} applies modus ponens to lines ${refs.map((x) => x + 1).join(" and ")}. Every line is a tautology.`
        : "An axiom instance is allowed directly. The research question concerns shortest proofs for whole families of tautologies, far beyond this example.",
    };
  },
  update(s, a) {
    if (a.startsWith("line:")) s.selected = +a.split(":")[1];
    else this.step(s);
  },
  step(s) {
    s.step = Math.min(5, s.step + 1);
    s.selected = s.step - 1;
  },
  done: (s) => s.step === 5,
};
const arrivalOrders = M.permutations([0, 1, 2]),
  meanGreedy = sum(arrivalOrders.map(M.greedyMatching)) / 6;
examples["online-matching-random-order"] = {
  title: "Match arrivals without undoing a decision",
  scope:
    "Three online and three offline vertices. The arrival order is one of all six permutations. The mean below is for fixed-priority greedy on this one graph.",
  instruction:
    "For the current arrival, choose an available offline neighbor or skip. Future edges stay hidden. Play uses the lowest-numbered available neighbor.",
  initial: () => ({
    order: 0,
    step: 0,
    matches: [],
    used: [],
    message: "The first arrival has revealed its neighbors.",
  }),
  render(s) {
    const order = arrivalOrders[s.order],
      current = order[s.step],
      ptsL = [0, 1, 2].map((i) => [125, 55 + i * 75]),
      ptsR = [0, 1, 2].map((i) => [395, 55 + i * 75]);
    const visible = order.slice(0, Math.min(3, s.step + 1));
    return {
      figure: svg(
        visible
          .flatMap((v) =>
            M.matchNeighbors[v].map((u) =>
              line(
                ptsL[u],
                ptsR[order.indexOf(v)],
                s.matches.some(([a, b]) => a === u && b === v)
                  ? "is-active"
                  : "",
              ),
            ),
          )
          .join("") +
          ptsL
            .map((p, u) =>
              node(
                p,
                String(u + 1),
                `match:${u}`,
                s.used.includes(u),
                `Match to offline vertex ${u + 1}`,
              ),
            )
            .join("") +
          ptsR
            .map((p, i) => node(p, `v${order[i] + 1}`, "", i === s.step))
            .join("") +
          text(125, 244, "Offline vertices") +
          text(395, 244, "Arrival order"),
        "Online bipartite matching",
      ),
      controls:
        btn("step", "Greedy step", false, s.step === 3) +
        btn("skip", "Leave unmatched", false, s.step === 3) +
        btn("order", "Next arrival order"),
      stats: stats(
        ["Your matching", s.matches.length + "/3"],
        ["Offline optimum", 3],
        ["Greedy mean over 6 orders", meanGreedy.toFixed(3)],
      ),
      caption:
        s.step === 3
          ? `This run matched ${s.matches.length} vertices. The mean for fixed-priority greedy is ${meanGreedy.toFixed(3)} on this graph; a single graph or order gives no all-graph competitive guarantee.`
          : `Arrival v${current + 1}: ${s.message}`,
    };
  },
  update(s, a) {
    if (a === "order") {
      s.order = (s.order + 1) % 6;
      s.step = 0;
      s.matches = [];
      s.used = [];
      s.message = "Choose an available neighbor.";
    }
    if (s.step >= 3) return;
    if (a.startsWith("match:")) {
      const u = +a.split(":")[1],
        v = arrivalOrders[s.order][s.step];
      if (s.used.includes(u) || !M.matchNeighbors[v].includes(u)) {
        s.message = "That vertex is unavailable or is not a neighbor.";
        return;
      }
      s.matches.push([u, v]);
      s.used.push(u);
      s.step++;
      s.message = "The previous match is now fixed.";
    }
    if (a === "skip") {
      s.step++;
      s.message = "The previous arrival was left unmatched.";
    }
    if (a === "step") this.step(s);
  },
  step(s) {
    if (s.step >= 3) return;
    const v = arrivalOrders[s.order][s.step],
      u = M.matchNeighbors[v].find((u) => !s.used.includes(u));
    this.update(s, u === undefined ? "skip" : `match:${u}`);
  },
  done: (s) => s.step === 3,
};
examples["prg-constant-width-robp"] = {
  title: "Trace a width-4 branching program",
  scope:
    "Four input bits, four states tracking the number of 1s modulo 4. Two tiny generators are tested against this particular program only.",
  instruction:
    "Choose a seed and trace its generated bits through the layers. Compare acceptance under uniform inputs and uniform seeds.",
  initial: () => ({ kind: 0, seed: 0, accept: 0, step: 0 }),
  render(s) {
    const words = M.prgWords(s.kind),
      bits = words[s.seed],
      path = M.programPath(bits),
      accept = s.accept ? [0, 2] : [0],
      r = M.programStats(s.kind, accept),
      point = (i, q) => [55 + i * 102, 62 + q * 46];
    let body = "";
    for (let i = 0; i < 4; i++)
      for (let q = 0; q < 4; q++)
        for (let b = 0; b < 2; b++)
          body += line(
            point(i, q),
            point(i + 1, (q + b) % 4),
            i < s.step && path[i] === q && bits[i] === b ? "is-active" : "",
          );
    body += Array.from(
      { length: 5 },
      (_, i) =>
        Array.from(
          { length: 4 },
          (_, q) =>
            `<g class="lab-state ${i <= s.step && path[i] === q ? "is-active" : ""}"><circle cx="${point(i, q)[0]}" cy="${point(i, q)[1]}" r="14"/>${i === 4 && accept.includes(q) ? `<circle cx="${point(i, q)[0]}" cy="${point(i, q)[1]}" r="19" class="lab-accept"/>` : ""}${text(point(i, q)[0], point(i, q)[1] + 4, q)}</g>`,
        ).join("") +
        text(55 + i * 102, 27, i === 0 ? "Start" : `Read ${bits[i - 1]}`),
    ).join("");
    return {
      figure: svg(body, "Width-four branching program"),
      controls:
        select(
          "kind",
          "Generator",
          [
            "Repeat two seed bits: a b a b",
            "Even-parity generator: a b c (a⊕b⊕c)",
          ],
          s.kind,
        ) +
        select(
          "seed",
          "Seed",
          words.map((_, i) => i.toString(2).padStart(s.kind ? 3 : 2, "0")),
          s.seed,
        ) +
        select(
          "accept",
          "Accepting states",
          ["State 0", "States 0 and 2"],
          s.accept,
        ) +
        btn("step", "Read next bit", false, s.step === 4),
      stats: stats(
        ["Uniform acceptance", (r.uniform * 100).toFixed(1) + "%"],
        ["Generator acceptance", (r.generated * 100).toFixed(1) + "%"],
        ["Absolute error", r.error.toFixed(3)],
      ),
      caption: `Generated word: ${bits.join("")}. Error ${r.error <= 0.25 ? "≤" : ">"} 1/n = 0.25 for this program. The open problem requires one efficient family to fool every width-4 program, at every length.`,
    };
  },
  update(s, a, v) {
    if (a === "kind") {
      s.kind = +v;
      s.seed = 0;
      s.step = 0;
    }
    if (a === "seed") {
      s.seed = +v;
      s.step = 0;
    }
    if (a === "accept") s.accept = +v;
    if (a === "step") this.step(s);
  },
  step(s) {
    s.step = Math.min(4, s.step + 1);
  },
  done: (s) => s.step === 4,
};
