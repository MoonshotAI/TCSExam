export const resultScopes = ['lite', 'full'];
const fullProtocol = 'paper-submitted-2026';
const tracks = ['index', 'theorem', 'solver', 'construction', 'open'];

// Older shared links used one #results section and a protocol selector.
export function normalizeResultsAnchor(url) {
  if (url.hash === '#results') {
    url.hash = url.searchParams.get('protocol') === fullProtocol ? 'full' : 'lite';
  }
  return url;
}

export function readResultsLocation(url) {
  const params = url.searchParams;
  const legacyScope = params.has('protocol')
    ? params.get('protocol') === fullProtocol ? 'full' : 'lite'
    : url.hash === '#full' ? 'full' : 'lite';
  return Object.fromEntries(resultScopes.map(scope => {
    const view = params.get(`${scope}-view`) ?? (scope === legacyScope ? params.get('view') : null);
    const track = params.get(`${scope}-track`) ?? (scope === legacyScope ? params.get('track') : null);
    return [scope, {view: ['chart', 'table'].includes(view) ? view : 'chart', track: tracks.includes(track) ? track : 'index'}];
  }));
}

export function writeResultsLocation(url, states) {
  ['protocol', 'view', 'track'].forEach(key => url.searchParams.delete(key));
  for (const scope of resultScopes) {
    for (const [key, fallback] of [['view', 'chart'], ['track', 'index']]) {
      const name = `${scope}-${key}`, value = states[scope][key];
      if (value === fallback) url.searchParams.delete(name);
      else url.searchParams.set(name, value);
    }
  }
  return url;
}
