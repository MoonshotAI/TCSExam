import {modelLabel} from '../model-label.js';
import {sortByScore} from '../result-order.js';
import {brandWordmark} from '../brand.js';
import {formatScore} from '../score-format.js';

const esc = text => String(text).replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
export const taskMetrics = {
  theorem: 'complete-proof-rate', solver: 'kimi-relative-score',
  construction: 'task-score', open: 'complete-resolution-rate',
};
const headings = {
  theorem: ['Success rate (%)', 'Proved / attempted'],
  solver: ['Relative score (%)', 'Attempts'],
  construction: ['Mean task score (%)', 'Attempts'],
  open: ['Resolution rate (%)', 'Resolved / attempted'],
};
const notes = {
  theorem: 'Success means a complete Lean proof of the main theorem.',
  solver: 'Scores are averaged over instances, then attempts. On each instance, 50 represents a valid result equal to the Kimi K3 reference mean. This experiment allowed intermediate evaluation feedback.',
  construction: '100 represents the task’s reference result; higher scores indicate an improvement.',
  open: 'Resolution means a complete Lean proof or refutation of the conjecture.',
};

export function resultScale(record) {
  return record.track === 'construction'
    ? Math.ceil(Math.max(1.1, ...record.results.map(r => r.mean)) * 2) / 2
    : 1;
}

export function renderTaskResults(task, record, data, hasLiteResults = false) {
  const binary = ['theorem', 'open'].includes(task.track);
  const [metricHeading, attemptsHeading] = headings[task.track];
  const maximum = resultScale(record);
  const reference = task.track === 'construction' ? 1 : task.track === 'solver' ? .5 : null;
  const models = new Map(data.models.map(m => [m.id, m.label]));
  const rows = sortByScore(record.results, row => row.mean).map(row => {
    const value = formatScore(row.mean);
    const attempts = binary ? `${row.attempts.reduce((sum, a) => sum + a.score, 0)} / ${row.attempts.length}` : row.attempts.length;
    return `<tr data-model="${row.model}"><th scope="row">${modelLabel(models.get(row.model))}</th><td><div class="task-score"><span class="task-score-meter" aria-hidden="true"><i style="width:${100 * row.mean / maximum}%"></i>${reference === null ? '' : `<b style="left:${100 * reference / maximum}%"></b>`}</span><span class="task-score-value">${value}</span></div></td><td class="task-attempt-count">${attempts}</td></tr>`;
  }).join('');
  const coverage = record.coverage;
  const supplemented = data.protocol === 'full-development-feedback-v1';
  const coverageNote = coverage && coverage.scored_instances < coverage.total_instances ? ` ${supplemented ? 'Reference coverage for the original paper models' : 'Reference coverage'}: ${coverage.scored_instances} of ${coverage.total_instances} instances.` : '';
  return `<section class="task-results" id="${hasLiteResults ? 'full-task-results' : 'task-results'}" aria-labelledby="task-results-title" data-result-panel="full" data-protocol="${data.protocol}" data-metric="${record.metric}">
    <div class="task-results-heading"><h2 class="brand-heading" id="task-results-title">${hasLiteResults || supplemented ? `${brandWordmark()}-Full results` : 'Results on this task'}</h2><span>${supplemented ? '' : 'Submitted paper · '}${data.development_hours} h per attempt</span></div>
    <table class="task-results-table" aria-describedby="task-result-note"><caption class="sr-only">${esc(task.title)}: ${data.models.length} models evaluated under the ${supplemented ? 'Full' : 'original paper'} protocol. Sorted by score, highest first. ${metricHeading}.</caption><thead><tr><th scope="col">Model</th><th scope="col" aria-sort="descending">${metricHeading}</th><th scope="col">${attemptsHeading}</th></tr></thead><tbody>${rows}</tbody></table>
    <p class="task-result-note" id="task-result-note">${notes[task.track]}${coverageNote}</p>
  </section>`;
}

export function taskResultsCsv(record, data) {
  const names = new Map(data.models.map(m => [m.id, m.label]));
  // Export units follow the source data contract; task scores retain
  // their original scale independently of the display format. Numeric precision is not rounded for export.
  const factor = record.track === 'construction' ? 1 : 100;
  const unit = record.track === 'construction' ? 'task score' : record.track === 'solver' ? 'relative score / 100' : 'percent';
  const extra = data.model_settings ? ['judge_status','raw_reward','run_outcome','exception_type','source_group','agent_seconds','note'] : [];
  const rows = [['protocol', 'task', 'track', 'model', 'attempt', 'score', 'task_mean', 'metric', 'unit', 'scored_instances', 'total_instances',...extra]];
  for (const row of record.results) for (const attempt of row.attempts) {
    rows.push([data.protocol, record.id, record.track, names.get(row.model), attempt.attempt,
      factor * attempt.score, factor * row.mean, record.metric, unit,
      data.model_settings?.[row.model] ? '' : record.coverage?.scored_instances ?? '', data.model_settings?.[row.model] ? '' : record.coverage?.total_instances ?? '', ...extra.map(key=>attempt[key] ?? '')]);
  }
  return rows.map(row => row.map(cell => `"${String(cell).replaceAll('"', '""')}"`).join(',')).join('\r\n') + '\r\n';
}
