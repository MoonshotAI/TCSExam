// Motion explains the existing drawing: follow a path, inspect a column or
// emphasize a mathematical object. It never changes the example or its values.
const path = (selector) => ({ mode: "trace", selector });
const inspect = (selector) => ({ mode: "inspect", selector });
const columns = (selector = "rect.di-cell, rect.di-tile, rect[class*='di-color-']") =>
  ({ mode: "columns", selector });
const rows = (selector) => ({ mode: "rows", selector });

const motions = {
  corners: path("path.di-hot"),
  bidding: path("path.di-hot"),
  folded: columns(),
  arithmetic: path("path.di-line"),
  spectrum: columns("rect"),
  bins: columns("rect"),
  schedule: columns(),
  cut: path("path.di-hot"),
  assignment: columns("rect[class*='di-color-']"),
  qbf: path("path.di-line"),
  binarycode: columns(),
  c5: path(".di-flow"),
  kissing: inspect("circle.di-region"),
  ramsey: { ...path("path.di-ramsey-red, path.di-ramsey-blue"), sourceColor: true },
  integrality: path("path.di-hot"),
  communication: columns(),
  "edge-query": path("path.di-hot"),
  frege: rows("rect"),
  matching: path("path.di-hot"),
  branching: path("path.di-dash"),
  path: path(".di-flow"),
  "sparse-matrix": columns(),
  proximity: path(".di-flow"),
  "local-code": path("path.di-hot"),
  cube: path("path.di-danger"),
  chase: path(".di-flow"),
  cactus: path("path.di-line"),
  subspace: inspect("path.di-region, path.di-tile, path.di-hot"),
  independent: path("path.di-hot"),
  halfspace: path(".di-flow"),
  quantum: path("path.di-line"),
  parity: path("path.di-line"),
  taxis: path("path.di-hot, path.di-dash"),
  query: columns(),
  xor: path("path.di-line"),
  factory: columns("rect.di-tile"),
  cluster: path("path.di-hot, path.di-danger"),
  frequency: inspect("circle.di-solid"),
  forest: path("path.di-line"),
  coloring: inspect("circle"),
  routing: path("path.di-hot, path.di-secondary"),
  feedback: path("path.di-line"),
  dominating: inspect("circle.di-region"),
  cutting: inspect("rect.di-tile, rect.di-cell"),
  partition: path("path.di-hot"),
  hypergraph: inspect("path.di-region"),
  sports: columns(),
  jobs: rows("rect"),
  circuit: path("path.di-line"),
  clique: path("path.di-hot"),
  sat: rows("rect"),
  nurse: columns(),
  crossing: path("path.di-hot"),
  qap: path("path.di-dash"),
  radiation: columns("rect"),
  setcover: columns(),
  synthesis: path("path.di-line"),
  tour: path(".di-flow"),
  treewidth: inspect("rect.di-tile"),
  vertexcover: inspect("circle.di-solid"),
  progression: inspect("circle.di-outline"),
  cap: path("path.di-danger"),
  covercode: inspect("circle.di-outline"),
  stabilizer: rows("rect"),
  latin: rows("rect"),
  cage: path("path.di-line"),
  sort: columns("circle.di-solid"),
  circles: columns("circle.di-region"),
  sphere: rows("circle.di-solid"),
  "graph-gap": path("path.di-line"),
  rectilinear: path("path.di-hot"),
  influence: inspect("rect"),
  nonzero: rows("rect.di-tile, rect.di-cell"),
  "directed-cycle": path("path.di-hot"),
  decision: path("path.di-line"),
  paley: inspect("circle.di-node"),
  rigidity: columns(),
  extension: path("path.di-line"),
  composition: path("path.di-line"),
  hamilton: path(".di-flow"),
  mds: columns("rect.di-tile"),
  threshold: path("path.di-line, path.di-hot"),
  modular: path("path.di-line, path.di-hot"),
  multiply: columns(),
  "online-bins": columns("rect"),
  permanent: columns(),
  sumset: inspect("circle.di-solid, circle.di-node"),
  embedding: path("path.di-hot"),
  polar: path("path.di-line"),
  ryser: path("path.di-hot, path.di-secondary"),
  totalcolor: inspect("circle"),
  triangles: path("path.di-hot"),
  "parity-tree": path("path.di-line"),
};

export function prepareIllustrationMotion(row) {
  const preview = row.querySelector(".catalogue-preview, .task-figure-art[data-preview-family]");
  if (!preview) return;
  const spec = motions[preview.dataset.previewFamily];
  if (!spec) throw new Error(`Missing preview motion: ${preview.dataset.previewFamily}`);
  const shapes = [...preview.querySelectorAll(spec.selector)]
    // Arrowheads share the line's class, but don't need a separate moving trace.
    .filter(shape => spec.mode !== "trace" || shape.getTotalLength() > 18);
  if (!shapes.length) throw new Error(`Empty preview motion: ${preview.dataset.previewFamily}`);
  const grouped = spec.mode === "columns" || spec.mode === "rows";
  const coordinate = shape => {
    const box = shape.getBBox();
    return Math.round(spec.mode === "rows" ? box.y + box.height / 2 : box.x + box.width / 2);
  };
  // Keep the pace readable even for dense matrices and sphere point sets.
  const coordinates = [...new Set(shapes.map(coordinate))].sort((a, b) => a - b);
  const steps = Math.min(8, grouped ? coordinates.length : shapes.length);
  shapes.forEach((shape, index) => {
    const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    group.dataset.previewPiece = "";
    // The emphasis travels with its original element during local disturbance.
    shape.before(group);
    group.append(shape);
    const highlight = shape.cloneNode(false);
    highlight.removeAttribute("class");
    highlight.classList.add("pv-ambient", "pv-emphasis");
    highlight.setAttribute("fill", "none");
    highlight.setAttribute("stroke", spec.sourceColor ? getComputedStyle(shape).stroke : "var(--accent)");
    highlight.setAttribute("stroke-width", spec.mode === "trace" ? "3.5" : "2.5");
    if (shape.tagName === "circle" && spec.mode !== "trace") {
      highlight.setAttribute("r", Number(shape.getAttribute("r")) + 3);
    }
    const sourceIndex = grouped ? coordinates.indexOf(coordinate(shape)) : index;
    const sourceCount = grouped ? coordinates.length : shapes.length;
    const step = Math.min(steps - 1, Math.floor(sourceIndex * steps / sourceCount));
    const begin = step * .76 / steps;
    const peak = begin + .1;
    const end = Math.min(.99, begin + .24);
    let frames;
    if (spec.mode === "trace") {
      highlight.setAttribute("pathLength", "1");
      highlight.style.strokeDasharray = "1";
      frames = [
        { opacity: 0, strokeDashoffset: 1, offset: 0 },
        { opacity: 0, strokeDashoffset: 1, offset: begin },
        { opacity: .9, strokeDashoffset: 0, offset: peak },
        { opacity: 0, strokeDashoffset: 0, offset: end },
        { opacity: 0, strokeDashoffset: 1, offset: 1 },
      ];
    } else {
      frames = [
        { opacity: 0, offset: 0 },
        { opacity: 0, offset: begin },
        { opacity: .85, offset: peak },
        { opacity: 0, offset: end },
        { opacity: 0, offset: 1 },
      ];
    }
    group.append(highlight);
    const animation = highlight.animate(frames, {
      duration: 4800, iterations: Infinity, easing: "linear", fill: "both",
    });
    animation.pause();
    animation.currentTime = 0;
  });
}
