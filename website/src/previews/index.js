import { pairs, fourier, petersenEdges, matchNeighbors } from "../labs/math.js";
import "./previews.css";
import "./ambient.css";
import { renderIllustration } from "../catalogue/illustrations.js";

// Small, synthetic illustrations of the task definitions. No benchmark scores.
const circle = (x, y, r = 3.4, cls = "") =>
  `<circle cx="${x}" cy="${y}" r="${r}" class="${cls}"/>`;
const line = (a, b, cls = "") =>
  `<path d="M${a.join(" ")}L${b.join(" ")}" class="${cls}"/>`;
const rect = (x, y, w, h, cls = "", rx = 2) =>
  `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${rx}" class="${cls}"/>`;
const text = (x, y, value, cls = "") =>
  `<text x="${x}" y="${y}" class="${cls}">${value}</text>`;
const ring = (n, radius = 38, cx = 88, cy = 56, phase = -Math.PI / 2) =>
  Array.from({ length: n }, (_, i) => [
    cx + radius * Math.cos(phase + (i * Math.PI * 2) / n),
    cy + radius * Math.sin(phase + (i * Math.PI * 2) / n),
  ]);
const nodes = (ps, active = []) =>
  ps
    .map(([x, y], i) =>
      circle(x, y, 4, active.includes(i) ? "pv-solid" : "pv-node"),
    )
    .join("");
const edges = (ps, es, cls = "") =>
  es.map(([a, b]) => line(ps[a], ps[b], cls)).join("");
const group = (content, cls) => `<g class="${cls}">${content}</g>`;
const drawings = {};

// A translated corner remains a corner. All highlighted points belong to the grid.
drawings["corners-quasipoly"] = () =>
  Array.from({ length: 25 }, (_, i) =>
    circle(44 + (i % 5) * 22, 12 + Math.floor(i / 5) * 22, 2, "pv-dot"),
  ).join("") +
  group(
    '<path d="M44 56V34H66" class="pv-accent"/>' +
      [
        [44, 56],
        [44, 34],
        [66, 34],
      ]
        .map((p) => circle(...p, 4, "pv-solid"))
        .join(""),
    "pv-corner",
  );

drawings["discrete-bidding-games"] = () =>
  '<path d="M57 51Q88 19 119 51M119 65Q88 96 57 65" class="pv-line"/>' +
  nodes(
    [
      [48, 58],
      [128, 58],
    ],
    [0],
  ) +
  text(48, 78, "A") +
  text(128, 78, "B") +
  [0, 1, 2].map((i) => rect(32 + i * 8, 21, 5, 13, "pv-tint")).join("") +
  [0, 1, 2].map((i) => rect(112 + i * 8, 21, 5, 13, "pv-tint")).join("") +
  group(
    circle(58, 34, 5, "pv-solid") + circle(58, 34, 2, "pv-white"),
    "pv-transfer",
  );

drawings["folded-rs-gsb"] = () =>
  [0, 1, 2, 3]
    .map(
      (v, i) =>
        rect(27 + i * 32, 30, 27, 33, "pv-cell") + text(40.5 + i * 32, 52, v),
    )
    .join("") +
  '<path d="M27 71V78H86V71M91 71V78H150V71" class="pv-line"/>' +
  group(rect(26, 29, 61, 35, "pv-outline", 3), "pv-fold") +
  text(57, 97, "block 1") +
  text(121, 97, "block 2");

drawings["negations-small-depth"] = () => {
  const ps = [
      [44, 24],
      [126, 24],
      [44, 70],
      [126, 70],
    ],
    es = [
      [0, 1],
      [0, 2],
      [1, 2],
      [2, 3],
    ];
  return (
    edges(ps, es, "pv-line") +
    group(
      edges(
        ps,
        [
          [0, 2],
          [1, 2],
        ],
        "pv-trace",
      ),
      "pv-tracing",
    ) +
    nodes(ps, [0, 1, 2]) +
    text(88, 100, "(e − 1)²", "pv-formula")
  );
};

drawings["quantum-crypto-algorithmica"] = () => {
  const spectrum = fourier([1, 1, 1, -1, 1, -1, -1, -1]);
  return (
    '<path d="M24 58H152" class="pv-line"/>' +
    spectrum
      .map((v, i) =>
        group(
          rect(
            27 + i * 16,
            Math.min(58, 58 - v * 72),
            8,
            Math.max(2, Math.abs(v) * 72),
            "pv-solid",
          ),
          `pv-spectrum pv-delay-${i % 3}`,
        ),
      )
      .join("") +
    group(
      rect(24, 17, 14, 73, "pv-outline", 2),
      "pv-code-scan pv-spectrum-scan",
    ) +
    text(88, 100, "f  →  f̂", "pv-formula")
  );
};

drawings["bpp-bpplib"] = () =>
  '<path d="M42 20V93H80V20M97 20V93H135V20" class="pv-line"/>' +
  rect(45, 50, 32, 40, "pv-tint") +
  group(rect(45, 22, 32, 26, "pv-solid"), "pv-drop") +
  rect(100, 57, 32, 33, "pv-tint") +
  rect(100, 36, 32, 19, "pv-fill") +
  rect(100, 22, 32, 12, "pv-solid");

drawings["curriculum-itc2007"] = () =>
  Array.from({ length: 12 }, (_, i) =>
    rect(33 + (i % 4) * 28, 17 + Math.floor(i / 4) * 27, 24, 23, "pv-cell"),
  ).join("") +
  [0, 5, 10]
    .map((i) =>
      rect(35 + (i % 4) * 28, 20 + Math.floor(i / 4) * 27, 20, 17, "pv-tint"),
    )
    .join("") +
  group(rect(63, 20, 20, 17, "pv-solid"), "pv-timetable") +
  [0, 1, 2, 3].map((i) => circle(45 + i * 28, 106, 1.5, "pv-dot")).join("");

drawings["maxcut-mqlib"] = () => {
  const ps = ring(6),
    es = [
      [0, 1],
      [1, 2],
      [2, 3],
      [3, 4],
      [4, 5],
      [5, 0],
      [0, 3],
      [1, 4],
      [2, 5],
    ];
  return (
    '<path d="M88 10V102" class="pv-guide"/>' +
    edges(ps, es, "pv-line") +
    group(
      edges(
        ps,
        [
          [0, 3],
          [1, 4],
          [2, 5],
        ],
        "pv-trace",
      ),
      "pv-tracing",
    ) +
    nodes(ps, [3, 4, 5])
  );
};

drawings["mr-roadef2012"] = () =>
  [0, 1, 2]
    .map(
      (i) =>
        rect(29 + i * 43, 22, 32, 68, "pv-cell") +
        [0, 1, 2]
          .map((j) =>
            rect(
              34 + i * 43,
              30 + j * 17,
              22,
              11,
              (i + j) % 3 === 0 ? "pv-tint" : "pv-empty",
            ),
          )
          .join(""),
    )
    .join("") + group(rect(34, 64, 22, 11, "pv-solid"), "pv-migrate");

drawings["qbf-qbfeval"] = () => {
  const ps = [
      [88, 18],
      [52, 52],
      [124, 52],
      [30, 86],
      [70, 86],
      [106, 86],
      [146, 86],
    ],
    es = [
      [0, 1],
      [0, 2],
      [1, 3],
      [1, 4],
      [2, 5],
      [2, 6],
    ];
  return (
    edges(ps, es, "pv-line") +
    group(
      edges(
        ps,
        [
          [0, 1],
          [1, 4],
        ],
        "pv-trace",
      ),
      "pv-tracing",
    ) +
    ps
      .map(([x, y], i) =>
        circle(
          x,
          y,
          i < 3 ? 10 : 8,
          [0, 1, 2, 4, 5].includes(i) ? "pv-tint" : "pv-node",
        ),
      )
      .join("") +
    text(88, 22, "∀") +
    text(52, 56, "∃") +
    text(124, 56, "∃") +
    [0, 1, 1, 0].map((v, i) => text(ps[i + 3][0], 90, v)).join("")
  );
};

drawings["binary-code-a24-10"] = () =>
  [
    [0, 0, 0, 0, 0, 0],
    [1, 1, 1, 0, 0, 0],
    [0, 0, 1, 1, 1, 0],
    [1, 1, 0, 1, 1, 1],
  ]
    .map((row, y) =>
      row
        .map(
          (v, x) =>
            rect(32 + x * 19, 14 + y * 22, 16, 18, v ? "pv-tint" : "pv-cell") +
            text(40 + x * 19, 27 + y * 22, v),
        )
        .join(""),
    )
    .join("") + group(rect(30, 12, 20, 87, "pv-outline", 3), "pv-code-scan");

drawings["ex-c3c4-maxedges"] = () => {
  const ps = ring(7),
    es = ps.map((_, i) => [i, (i + 1) % 7]);
  return (
    edges(ps, es, "pv-line") +
    group(edges(ps, es, "pv-trace"), "pv-tracing") +
    nodes(ps)
  );
};

drawings["kissing-d13"] = () =>
  circle(88, 56, 18, "pv-center") +
  group(
    ring(6, 36, 88, 56, 0)
      .map(([x, y]) => circle(x, y, 18, "pv-orbit-circle"))
      .join(""),
    "pv-orbit",
  );

drawings["ramsey-r46"] = () => {
  const ps = ring(6);
  return (
    pairs(6)
      .map(([a, b], i) =>
        line(ps[a], ps[b], i % 3 === 0 ? "pv-red" : "pv-blue"),
      )
      .join("") +
    nodes(ps) +
    `<g class="pv-walker" style="${ps.map(([x, y], i) => `--walk-${i}:translate(${x}px,${y}px)`).join(";")}">${circle(0, 0, 4.5, "pv-signal")}</g>`
  );
};

drawings["tsp-gap"] = () => {
  // Expand the final metric edge 6 → 0 through vertex 1, following the visible graph.
  const ps = [...ring(5, 45), ...ring(5, 21)],
    walk = [0, 1, 2, 3, 4, 9, 7, 5, 8, 6, 1, 0];
  return (
    edges(ps, petersenEdges, "pv-line") +
    group(
      `<path d="${walk.map((i, n) => `${n ? "L" : "M"}${ps[i].join(" ")}`).join("")}" class="pv-trace"/>`,
      "pv-tracing",
    ) +
    nodes(ps)
  );
};

drawings["log-rank-conjecture"] = () =>
  '<path d="M49 15H125M120 11L125 15L120 19" class="pv-line"/>' +
  text(36, 19, "A") +
  text(140, 19, "B") +
  group(circle(55, 15, 3, "pv-solid"), "pv-message") +
  Array.from(
    { length: 16 },
    (_, i) =>
      rect(
        50 + (i % 4) * 19,
        32 + Math.floor(i / 4) * 18,
        19,
        18,
        i % 5 === 0 ? "pv-tint" : "pv-cell",
        0,
      ) +
      text(
        59.5 + (i % 4) * 19,
        45 + Math.floor(i / 4) * 18,
        i % 5 === 0 ? 1 : 0,
      ),
  ).join("");

drawings["evasiveness-graph-properties"] = () => {
  const ps = [
    [47, 25],
    [129, 25],
    [47, 87],
    [129, 87],
  ];
  return (
    edges(ps, pairs(4), "pv-guide") +
    group(edges(ps, [[0, 3]], "pv-trace"), "pv-tracing") +
    nodes(ps) +
    text(88, 61, "?", "pv-question")
  );
};

drawings["frege-not-pbounded"] = () =>
  '<path d="M52 25L73 56M99 25L73 56M73 56L99 85M132 56L99 85" class="pv-line"/>' +
  group(
    '<path d="M52 25L73 56L99 85M99 25L73 56M132 56L99 85" class="pv-trace"/>',
    "pv-tracing",
  ) +
  [
    [52, 25],
    [99, 25],
    [73, 56],
    [132, 56],
  ]
    .map(
      (p, i) =>
        circle(...p, 9, "pv-node") + text(p[0], p[1] + 4, i === 2 ? "MP" : "A"),
    )
    .join("") +
  rect(73, 77, 52, 20, "pv-tint", 3) +
  text(99, 91, "p → p");

drawings["online-matching-random-order"] = () => {
  const left = [
      [43, 23],
      [43, 56],
      [43, 89],
    ],
    right = [
      [133, 23],
      [133, 56],
      [133, 89],
    ];
  return (
    matchNeighbors
      .map((neighbors, a) =>
        neighbors.map((b) => line(left[a], right[b], "pv-line")).join(""),
      )
      .join("") +
    [1, 0, 2]
      .map((b, a) =>
        group(line(left[a], right[b], "pv-trace"), `pv-tracing pv-delay-${a}`),
      )
      .join("") +
    nodes(left, [0, 1, 2]) +
    nodes(right)
  );
};

drawings["prg-constant-width-robp"] = () => {
  const cols = Array.from({ length: 5 }, (_, i) =>
      Array.from({ length: 4 }, (_, j) => [24 + i * 32, 31 + j * 20]),
    ),
    states = [0, 0, 1, 1, 2];
  return (
    cols
      .slice(0, 4)
      .map((ps, i) =>
        ps
          .map(
            (p, j) =>
              line(p, cols[i + 1][j], "pv-line") +
              line(p, cols[i + 1][(j + 1) % 4], "pv-faint"),
          )
          .join(""),
      )
      .join("") +
    group(
      `<path d="${states.map((s, i) => `${i ? "L" : "M"}${cols[i][s].join(" ")}`).join("")}" class="pv-trace"/>`,
      "pv-tracing",
    ) +
    cols.map((ps, i) => nodes(ps, [states[i]])).join("") +
    [0, 1, 0, 1].map((v, i) => text(40 + i * 32, 17, v)).join("")
  );
};

// Choose by mathematical family, not by membership in the Lite subset.
// These are schematic examples; the title and statement carry the task parameters.
const sharedDrawings = {
  corners: "corners-quasipoly", bidding: "discrete-bidding-games",
  folded: "folded-rs-gsb", arithmetic: "negations-small-depth",
  spectrum: "quantum-crypto-algorithmica", bins: "bpp-bpplib",
  schedule: "curriculum-itc2007", cut: "maxcut-mqlib",
  assignment: "mr-roadef2012", qbf: "qbf-qbfeval",
  binarycode: "binary-code-a24-10", c5: "ex-c3c4-maxedges",
  kissing: "kissing-d13", ramsey: "ramsey-r46", integrality: "tsp-gap",
  communication: "log-rank-conjecture", "edge-query": "evasiveness-graph-properties",
  frege: "frege-not-pbounded", matching: "online-matching-random-order",
  branching: "prg-constant-width-robp",
};

export function renderTaskPreview(task) {
  const family = task.drawing;
  const draw = drawings[sharedDrawings[family]];
  const svg = draw
    ? `<svg viewBox="0 0 176 112" focusable="false"><g class="pv-scene">${draw()}</g></svg>`
    : renderIllustration(task, { thumbnail: true, motion: true });
  return `<div class="task-preview${draw ? '' : ' catalogue-preview'}" data-preview-family="${family}" aria-hidden="true"><div class="preview-tilt"><div class="preview-float">${svg}</div></div></div>`;
}

export { mountPreviewMotion } from "./motion.js";
