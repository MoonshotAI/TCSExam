// Publish the data used by the browser. Full task results also build static pages.
const pick = (value, keys) => Object.fromEntries(keys.filter(key => key in value).map(key => [key, value[key]]));
export const publicDataFiles = ['benchmark.json', 'catalogue.json', 'lite-results.json', 'full-index.json', 'lite-index.csv', 'full-index.csv'];

export function publicData(name, data) {
  if (name === 'benchmark.json') return {
    ...pick(data, ['benchmark', 'development_hours', 'citation']),
    tracks: data.tracks.map(track => pick(track, ['id', 'label', 'short', 'color', 'full_count', 'description', 'output', 'verification', 'score'])),
    tasks: data.tasks.map(task => pick(task, ['id', 'track', 'title', 'domain', 'summary', 'formula', 'note'])),
  };
  if (name === 'catalogue.json') return {tasks: data.tasks.map(({instruction_sha256, ...task}) => task)};
  if (name === 'lite-results.json') return {
    ...pick(data, ['protocol', 'development_hours', 'models', 'tasks']),
    records: data.records.map(record => pick(record, ['id', 'model', 'task', 'track', 'attempt', 'score', 'judge_status', 'adoption'])),
  };
  if (name === 'full-index.json') return {models: data.models.map(model => pick(model, [
    'model', 'model_label', 'index', 'theorem', 'solver', 'construction', 'open',
    'theorem_points', 'solver_points', 'construction_points', 'open_points',
  ]))};
  if (name === 'research-graph.json') return pick(data, ['vertices', 'edges', 'highlighted_cycle']);
  if (name === 'quantum-code.json') return pick(data, ['reference', 'astra', 'examples']);
  if (name === 'binary-code.json') return pick(data, ['word_length', 'word_count', 'minimum_distance', 'correctable_bit_flips', 'words']);
  throw new Error(`No public data format for ${name}`);
}
