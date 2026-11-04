import graph from '../public/paper/research-graph.json' with { type: 'json' };
import { renderGraphCase, graphEdgeKey } from './graph-case-markup.js';
import { mountCaseScatter } from './case-motion.js';
import { mountQuantumCode } from './quantum-code-case.js';
import './quantum-code-case.css';

// Inspect the submitted construction; settled highlights use its actual edge set.
async function mountGraph(figure) {
  if (!figure || figure.dataset.ready) return;
  const vertices = graph.vertices;
  const neighbors = vertices.map(() => []);
  for (const [a, b] of graph.edges) { neighbors[a].push(b); neighbors[b].push(a); }
  const positions = vertices.map(({x, y}) => ({x, y}));
  const cycle = graph.highlighted_cycle;
  if (!figure.querySelector('.inspect-graph')) figure.innerHTML = renderGraphCase(graph);
  const svg = figure.querySelector('svg');
  const overlay = figure.querySelector('.graph-highlight');
  const status = figure.querySelector('.graph-status');
  const slider = figure.querySelector('input');
  const output = figure.querySelector('output');
  const backgroundNodes = [...svg.querySelectorAll('.graph-vertices circle')];
  const backgroundEdges = [...svg.querySelectorAll('.graph-edges path')];
  // Retain the same elements so CSS can blend from the current state even when
  // input arrives faster than a transition finishes. Every edge stays real.
  const highlightNodes = [...overlay.querySelectorAll('circle')];
  const highlightEdges = [...overlay.querySelectorAll('path')];
  const cycleEdges = new Set(cycle.map((v,i) => graphEdgeKey(v,cycle[(i+1)%cycle.length])));
  let mode = 'cycle', selected = 0, hovered = null;
  function draw() {
    const id = hovered ?? (mode === 'neighbors' ? selected : null);
    scatter.setEnabled(id === null);
    const visibleNodes = new Set(id === null ? cycle : [id, ...neighbors[id]]);
    for (const circle of highlightNodes) {
      const vertex = Number(circle.dataset.vertex);
      circle.toggleAttribute('data-highlighted', visibleNodes.has(vertex));
      circle.style.r = `${id === null ? 3.3 : vertex === id ? 4.5 : 3}px`;
    }
    for (const path of highlightEdges) {
      const a = Number(path.dataset.a), b = Number(path.dataset.b);
      path.toggleAttribute('data-highlighted', id === null ? cycleEdges.has(graphEdgeKey(a,b)) : a === id || b === id);
    }
    if (id === null) {
      svg.classList.remove('show-neighbors');
      svg.setAttribute('aria-label', '124-vertex, 630-edge graph. A five-cycle is highlighted.');
      status.textContent = 'A shortest cycle has five edges.';
    } else {
      svg.classList.add('show-neighbors');
      status.textContent = `Vertex ${id} · ${neighbors[id].length} neighbors`;
      svg.setAttribute('aria-label', `Vertex ${id} and its ${neighbors[id].length} neighbors in the submitted graph.`);
    }
    slider.setAttribute('aria-valuetext', `Vertex ${selected}, ${neighbors[selected].length} neighbors`);
    slider.value = selected;
    output.textContent = selected;
    figure.querySelector('label').hidden = mode !== 'neighbors';
    figure.querySelectorAll('[data-graph-mode]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.graphMode === mode)));
  }
  function nearest(event) {
    const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(svg.getScreenCTM().inverse());
    let closest = null, distance = 81;
    for (const [id, vertex] of positions.entries()) {
      const squared = (point.x-vertex.x)**2 + (point.y-vertex.y)**2;
      if (squared < distance) { distance = squared; closest = id; }
    }
    return closest;
  }
  svg.addEventListener('pointermove', event => {
    if (event.pointerType === 'touch') return;
    const id = nearest(event);
    if (id !== hovered) { hovered = id; draw(); }
  });
  svg.addEventListener('pointerleave', () => { hovered = null; draw(); });
  svg.addEventListener('click', event => {
    const id = nearest(event);
    if (id !== null) { selected = id; mode = 'neighbors'; hovered = null; draw(); }
  });
  slider.addEventListener('input', () => { selected = Number(slider.value); hovered = null; draw(); });
  figure.querySelectorAll('[data-graph-mode]').forEach(button => button.addEventListener('click', () => { mode = button.dataset.graphMode; hovered = null; draw(); }));
  const scatter = mountCaseScatter(svg, {
    points: () => vertices,
    toLocal: event => new DOMPoint(event.clientX, event.clientY).matrixTransform(svg.getScreenCTM().inverse()),
    paint: offsets => {
      offsets.forEach((offset, i) => {
        positions[i].x = vertices[i].x + offset.x;
        positions[i].y = vertices[i].y + offset.y;
      });
      for (const circle of [...backgroundNodes, ...highlightNodes]) {
        const point = positions[circle.dataset.vertex];
        circle.setAttribute('cx', point.x);
        circle.setAttribute('cy', point.y);
      }
      for (const path of [...backgroundEdges, ...highlightEdges]) {
        const a = positions[path.dataset.a], b = positions[path.dataset.b];
        path.setAttribute('d', `M${a.x} ${a.y}L${b.x} ${b.y}`);
      }
    },
  });
  draw();
  // Show the initial five-cycle in full; only subsequent selections transition.
  overlay.getBoundingClientRect();
  overlay.classList.add('is-ready');
  figure.querySelectorAll('button, input').forEach(control => { control.disabled = false; });
  figure.dataset.ready = 'true';
}

export function mountResearchCases() {
  const figures = new Map([
    [document.querySelector('#construction-case'), mountGraph],
    [document.querySelector('#quantum-code-case'), mountQuantumCode],
  ]);
  const pending = new Map();
  const load = figure => {
    if (!pending.has(figure)) {
      observer.unobserve(figure);
      // The initial figure remains visible if interaction setup fails.
      pending.set(figure, figures.get(figure)(figure).catch(() => {}));
    }
    return pending.get(figure);
  };
  const observer = new IntersectionObserver(entries => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      load(entry.target);
    }
  }, { rootMargin: '300px' });
  for (const figure of figures.keys()) if (figure) observer.observe(figure);
  // Restored reading positions must account for the full interactive figures.
  return () => Promise.all([...figures.keys()].filter(Boolean).map(load));
}
