// Large figures preserve their geometry: vertices move on damped springs and
// edges are redrawn from those same vertices. Frames and explanatory text stay
// fixed. Diagrams whose distances/angles carry meaning retain highlight motion.
const graphFamilies = new Set(`path bidding arithmetic cube cactus parity forest
  coloring routing feedback dominating partition clique cut qap qbf synthesis
  tour treewidth ramsey cage c5 integrality graph-gap directed-cycle decision
  edge-query paley extension composition hamilton branching matching ryser
  totalcolor triangles parity-tree crossing cluster vertexcover`.split(/\s+/));
const cellFamilies = new Set(`folded sparse-matrix schedule nurse sports binarycode
  stabilizer latin rigidity communication setcover radiation nonzero mds multiply
  permanent frege sat`.split(/\s+/));
const svgNS = "http://www.w3.org/2000/svg";
const number = /[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:e[-+]?\d+)?/ig;
const position = value => Number(value.toFixed(3));
const near = (a, b) => Math.hypot(a.x - b.x, a.y - b.y) < .1;

function straightPath(d) {
  // Only linear paths describe graph edges here. Curves, regions and axes are
  // deliberately left intact; this is not a general SVG shape deformation.
  if (/[^MLHVZ\s,]/.test(d.replace(number, ""))) return null;
  const tokens = d.match(/[MLHVZ]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:e[-+]?\d+)?/ig) || [];
  const points = [];
  let command, x = 0, y = 0, i = 0;
  while (i < tokens.length) {
    if (/^[MLHVZ]$/.test(tokens[i])) command = tokens[i++];
    if (command === "Z") { points.push({ command }); command = null; continue; }
    if (!command || i >= tokens.length) return null;
    if (command === "H") x = Number(tokens[i++]);
    else if (command === "V") y = Number(tokens[i++]);
    else { x = Number(tokens[i++]); y = Number(tokens[i++]); }
    if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
    points.push({ command: command === "M" ? "M" : "L", x, y });
    if (command === "M") command = "L";
  }
  return points;
}

export function createElasticMotion({ surfaceSelector }) {
  const systems = new Map(), running = new Set();
  let activeRow = null, frame = null, lastTime = null;

  function prepare(row) {
    if (systems.has(row)) return systems.get(row);
    const surface = row.querySelector(surfaceSelector), scene = surface.querySelector(".pv-scene");
    const family = surface.dataset.previewFamily, graph = graphFamilies.has(family);
    const enabled = graph || cellFamilies.has(family);
    const bodies = [], edges = [], connections = new Set();
    const matrixOf = el => scene.getCTM().inverse().multiply(el.getCTM());
    const pointInScene = (el, x, y) => new DOMPoint(x, y).matrixTransform(matrixOf(el));
    const originals = [...scene.querySelectorAll("circle, rect")].filter(el =>
      !el.matches(".pv-emphasis, .di-region, .di-outline") &&
      (graph || el.tagName === "rect"));
    if (enabled) for (const shape of originals) {
      const bounds = shape.getBBox();
      const center = pointInScene(shape, bounds.x + bounds.width / 2, bounds.y + bounds.height / 2);
      // Coincident node marks and filled centres share one displacement.
      let body = bodies.find(b => near(b, center));
      if (!body) {
        body = { x: center.x, y: center.y, ux: 0, uy: 0, vx: 0, vy: 0, parts: [], neighbors: new Set() };
        bodies.push(body);
      }
      const part = shape.closest("[data-preview-piece]") || shape;
      const parent = part.parentNode, wrapper = document.createElementNS(svgNS, "g");
      wrapper.classList.add("pv-elastic-body");
      part.before(wrapper); wrapper.append(part);
      const matrix = matrixOf(wrapper);
      body.parts.push({ wrapper, shape, parent, bounds, inverse: matrix.inverse(), matrix });
    }
    // Numbers and dot markers inside a cell or vertex remain attached to it.
    for (const label of scene.querySelectorAll("text, circle:not(.pv-emphasis):not(.di-region)")) {
      const x = Number(label.getAttribute(label.tagName === "text" ? "x" : "cx"));
      const y = Number(label.getAttribute(label.tagName === "text" ? "y" : "cy"));
      const part = bodies.flatMap(b => b.parts).filter(p => p.parent === label.parentNode &&
        x >= p.bounds.x && x <= p.bounds.x + p.bounds.width &&
        y >= p.bounds.y && y <= p.bounds.y + p.bounds.height)
        .sort((a, b) => a.bounds.width * a.bounds.height - b.bounds.width * b.bounds.height)[0];
      if (part) part.wrapper.append(label);
    }
    const bodyAt = pt => bodies.find(b => near(b, pt)) || bodies.find(b => b.parts.some(p => {
      const local = new DOMPoint(pt.x, pt.y).matrixTransform(p.inverse), box = p.bounds;
      if (p.shape.tagName === "circle") return Math.hypot(local.x - box.x - box.width / 2, local.y - box.y - box.height / 2) <= box.width / 2 + 1;
      return local.x >= box.x - 1 && local.x <= box.x + box.width + 1 && local.y >= box.y - 1 && local.y <= box.y + box.height + 1;
    }));
    if (graph) for (const element of scene.querySelectorAll("path")) {
      const original = element.getAttribute("d"), matrix = matrixOf(element), inverse = matrix.inverse();
      const arrow = element.getAttribute("data-motion-arrow");
      const coordinates = arrow?.match(number)?.map(Number);
      const points = arrow ? [
        { command: "M", x: coordinates[0], y: coordinates[1] },
        { command: "L", x: coordinates[2], y: coordinates[3] },
      ] : straightPath(original);
      if (!points) continue;
      points.forEach(p => {
        if (p.command !== "Z") p.body = bodyAt(new DOMPoint(p.x, p.y).matrixTransform(matrix));
      });
      if (!points.some(p => p.body)) continue;
      edges.push({ element, original, points, inverse, arrow: !!arrow });
      // Duplicate strokes and emphasis overlays must not duplicate spring forces.
      points.forEach((p, i) => {
        const a = points[i - 1]?.body, b = p.body;
        if (p.command !== "M" && a && b && a !== b) {
          const key = [bodies.indexOf(a), bodies.indexOf(b)].sort((a, b) => a - b).join(":");
          if (!connections.has(key)) { connections.add(key); a.neighbors.add(b); b.neighbors.add(a); }
        }
      });
    }
    const system = { row, scene, bodies, edges, pointer: null, graph, family };
    systems.set(row, system);
    return system;
  }

  function render(system) {
    for (const body of system.bodies) for (const part of body.parts) {
      const x = part.inverse.a * body.ux + part.inverse.c * body.uy;
      const y = part.inverse.b * body.ux + part.inverse.d * body.uy;
      if (x === 0 && y === 0) part.wrapper.removeAttribute("transform");
      else part.wrapper.setAttribute("transform", `translate(${position(x)} ${position(y)})`);
    }
    for (const edge of system.edges) {
      if (edge.points.every(p => !p.body || (p.body.ux === 0 && p.body.uy === 0))) {
        edge.element.setAttribute("d", edge.original); continue;
      }
      const points = edge.points.map(p => {
        const dx = p.body?.ux || 0, dy = p.body?.uy || 0;
        return { ...p, x: p.x + edge.inverse.a * dx + edge.inverse.c * dy,
          y: p.y + edge.inverse.b * dx + edge.inverse.d * dy };
      });
      let d;
      if (edge.arrow) {
        const [a, b] = points, angle = Math.atan2(b.y - a.y, b.x - a.x), size = 6;
        d = `M${position(b.x - size * Math.cos(angle - .6))} ${position(b.y - size * Math.sin(angle - .6))}L${position(b.x)} ${position(b.y)}L${position(b.x - size * Math.cos(angle + .6))} ${position(b.y - size * Math.sin(angle + .6))}`;
      } else d = points.map(p => p.command === "Z" ? "Z" : `${p.command}${position(p.x)} ${position(p.y)}`).join("");
      edge.element.setAttribute("d", d);
    }
  }

  function restore(system) {
    for (const b of system.bodies) b.ux = b.uy = b.vx = b.vy = 0;
    render(system);
    system.row.classList.remove("is-elastic-moving");
    running.delete(system);
  }

  function step(system, dt) {
    const radius = system.graph ? 42 : 31, amplitude = system.graph ? 7 : 2.6;
    let speed = 0, acceleration = 0, displacement = 0;
    const forces = system.bodies.map(body => {
      let tx = 0, ty = 0;
      if (system.pointer) {
        const dx = body.x - system.pointer.x, dy = body.y - system.pointer.y;
        const distance = Math.hypot(dx, dy), t = Math.min(1, distance / radius);
        const strength = amplitude * (1 - t) ** 2 * (1 + 2 * t);
        const length = Math.max(.01, distance);
        tx = strength * (distance < .01 ? system.pointer.dx : dx / length);
        ty = strength * (distance < .01 ? system.pointer.dy : dy / length);
      }
      // Strong restoring springs keep the layout readable; weaker edge springs
      // transmit a little of the same displacement to directly connected nodes.
      let ax = (tx - body.ux) * 150 - body.vx * 26;
      let ay = (ty - body.uy) * 150 - body.vy * 26;
      for (const n of body.neighbors) {
        ax += (n.ux - body.ux) * 14 / body.neighbors.size;
        ay += (n.uy - body.uy) * 14 / body.neighbors.size;
      }
      // Ordered layers and partite columns keep their defining alignment.
      if (["branching", "ryser", "matching", "qap"].includes(system.family)) ax = 0;
      if (system.family === "crossing") ay = 0;
      return [ax, ay];
    });
    system.bodies.forEach((b, i) => {
      const [ax, ay] = forces[i];
      b.vx += ax * dt; b.vy += ay * dt;
      b.ux += b.vx * dt; b.uy += b.vy * dt;
      speed = Math.max(speed, Math.hypot(b.vx, b.vy));
      acceleration = Math.max(acceleration, Math.hypot(ax, ay));
      displacement = Math.max(displacement, Math.hypot(b.ux, b.uy));
    });
    return { speed, acceleration, displacement };
  }

  function tick(time) {
    frame = null;
    // Use one clock: a frame timestamp can precede performance.now() from the
    // pointer event that requested it. Never integrate a negative time step.
    const elapsed = lastTime === null ? 1 / 60 : Math.max(0, Math.min((time - lastTime) / 1000, 1 / 30));
    lastTime = time;
    const steps = Math.max(1, Math.ceil(elapsed * 120)), dt = elapsed / steps;
    for (const system of running) {
      let state;
      for (let i = 0; i < steps; i++) state = step(system, dt);
      render(system);
      if (state.speed < .015 && state.acceleration < .2) {
        if (!system.pointer || state.displacement < .003) restore(system);
        else { system.row.classList.remove("is-elastic-moving"); running.delete(system); }
      }
    }
    if (running.size) frame = requestAnimationFrame(tick);
  }

  function wake(system) {
    if (!system.bodies.length) return;
    running.add(system); system.row.classList.add("is-elastic-moving");
    if (frame === null) { lastTime = null; frame = requestAnimationFrame(tick); }
  }

  return {
    prepare,
    get activeRow() { return activeRow; },
    setActive(row, immediate = false) {
      if (immediate) {
        if (frame !== null) cancelAnimationFrame(frame);
        frame = null;
        for (const system of systems.values()) { system.pointer = null; restore(system); }
      } else if (activeRow && activeRow !== row) {
        const previous = systems.get(activeRow);
        previous.pointer = null; wake(previous);
      }
      activeRow = row;
    },
    nudge(row, x, y) {
      if (row !== activeRow) return;
      const system = prepare(row);
      const point = new DOMPoint(x, y).matrixTransform(system.scene.getScreenCTM().inverse());
      const previous = system.pointer;
      const dx = point.x - (previous?.x ?? point.x - 1), dy = point.y - (previous?.y ?? point.y);
      const length = Math.hypot(dx, dy);
      system.pointer = { x: point.x, y: point.y,
        dx: length > .01 ? dx / length : previous?.dx ?? 1,
        dy: length > .01 ? dy / length : previous?.dy ?? 0 };
      wake(system);
    },
    dispose() {
      if (frame !== null) cancelAnimationFrame(frame);
      for (const system of systems.values()) { system.pointer = null; restore(system); }
      systems.clear(); running.clear(); activeRow = null; frame = null;
    },
  };
}
