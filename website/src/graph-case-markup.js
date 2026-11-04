// Build-time and interactive views share the same initial graph and controls.
export const graphEdgeKey = (a, b) => a < b ? `${a}:${b}` : `${b}:${a}`;

export function renderGraphCase(graph) {
  const {vertices, edges, highlighted_cycle: cycle} = graph;
  const cycleNodes = new Set(cycle);
  const cycleEdges = new Set(cycle.map((v, i) => graphEdgeKey(v, cycle[(i + 1) % cycle.length])));
  const node = ({id, x, y}, highlight = false) => `<circle data-vertex="${id}" cx="${x}" cy="${y}" r="${highlight ? 3.3 : 2}"${highlight && cycleNodes.has(id) ? ' data-highlighted' : ''}/>`;
  const edge = ([a, b], highlight = false) => `<path data-a="${a}" data-b="${b}" d="M${vertices[a].x} ${vertices[a].y}L${vertices[b].x} ${vertices[b].y}"${highlight && cycleEdges.has(graphEdgeKey(a, b)) ? ' data-highlighted' : ''}/>`;
  return `<div class="case-graph"><svg class="inspect-graph" viewBox="0 0 320 264" role="img" aria-label="124-vertex, 630-edge graph. A five-cycle is highlighted."><g class="graph-background"><g class="graph-edges">${edges.map(e => edge(e)).join('')}</g><g class="graph-vertices">${vertices.map(v => node(v)).join('')}</g></g><g class="graph-highlight"><g class="highlight-edges">${edges.map(e => edge(e, true)).join('')}</g><g class="highlight-nodes">${vertices.map(v => node(v, true)).join('')}</g></g></svg></div><figcaption>124 vertices. No triangles or four-cycles.</figcaption><div class="graph-modes" role="group" aria-label="Inspect the construction"><button type="button" data-graph-mode="cycle" aria-pressed="true" disabled>5-cycle</button><button type="button" data-graph-mode="neighbors" aria-pressed="false" disabled>Neighbors</button></div><div class="graph-selection"><p class="graph-status">A shortest cycle has five edges.</p><label hidden>Vertex <output>0</output><input type="range" min="0" max="123" value="0" aria-label="Graph vertex" disabled /></label></div>`;
}
