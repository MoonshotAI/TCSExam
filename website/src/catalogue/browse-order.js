// A fixed reading order separates related construction variants. Original
// task numbers, identities and research areas remain those of the paper.
const constructionOrder = new Map([
  'ramsey-r55',
  'binary-code-a22-10',
  'kissing-d13',
  'ex-c3c4-maxedges',
  'tsp-gap',
  'capset-d7',
  'mols-n10',
  'sorting-network-size',
  'vdw-w27',
  'ramsey-r46',
  'quantum-code-25-7',
  'circles-in-square-n100',
  'cage-girth',
  'graph-tsp-gap',
  'covering-code-k10',
  'kissing-d9',
  'binary-code-a24-10',
  'rectilinear-tsp-gap',
  'ramsey-r3-10',
  'spherical-code-d3-n50',
].map((id, index) => [id, index]));

export function orderTasksForBrowsing(tasks) {
  const constructions = tasks.filter(task => task.track === 'construction').sort((a, b) =>
    (constructionOrder.get(a.id) ?? constructionOrder.size) -
    (constructionOrder.get(b.id) ?? constructionOrder.size) || a.number - b.number,
  );
  let index = 0;
  return tasks.map(task => task.track === 'construction' ? constructions[index++] : task);
}
