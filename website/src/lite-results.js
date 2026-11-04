import {modelLabel} from './model-label.js';
import {brandWordmark} from './brand.js';
import {renderIndexChart} from './index-chart.js';
import {renderResultsTable, renderTrackChart, trackMetric} from './results-presentation.js';
import {sortByScore} from './result-order.js';
import {formatScore} from './score-format.js';
import {INDEX_WEIGHTS, weightedIndex} from './lite-index.js';

export const LITE_PROTOCOL = 'lite-v0.1-final-once';
export const adoptedStatuses = new Set(['selected', 'selected_provisional']);
const esc = text => String(text).replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
const mean = values => values.length ? values.reduce((a, b) => a + b, 0) / values.length : null;
const binary = track => ['theorem', 'open'].includes(track);
export const liteMetric = trackMetric;
export const liteValue = formatScore;

export function liteTaskSummary(data, modelId, taskId) {
  const model = data.models.find(m => m.id === modelId);
  const records = data.records.filter(r => r.model === modelId && r.task === taskId);
  const adopted = records.filter(r => adoptedStatuses.has(r.adoption) && r.judge_status === 'completed');
  const unresolved = records.filter(r => ['pending_selection', 'pending_rejudge'].includes(r.adoption));
  return {
    model, task: data.tasks.find(t => t.id === taskId), records, adopted, unresolved,
    score: mean(adopted.map(r => r.score)),
    complete: adopted.length === model.attempts_per_task && !unresolved.length,
    provisional: adopted.some(r => r.adoption === 'selected_provisional'),
    origin: [...new Set(adopted.map(r => r.origin))],
  };
}

export function summarizeLite(data, track) {
  const tasks = data.tasks.filter(t => t.track === track);
  return data.models.map(model => {
    const rows = tasks.map(t => liteTaskSummary(data, model.id, t.id));
    const covered = rows.filter(r => r.score !== null).length;
    const complete = rows.every(r => r.complete);
    return {model, rows, covered, total: tasks.length, complete,
      score: complete ? mean(rows.map(r => r.score)) : null,
      attempts: rows.reduce((n, r) => n + r.adopted.length, 0),
      provisional: rows.some(r => r.provisional),
    };
  });
}

export function liteResultsCsv(data, {taskId, adoptedOnly = false} = {}) {
  const names = new Map(data.models.map(m => [m.id, m.label]));
  const header = ['record', 'protocol', 'task', 'track', 'model', 'attempt', 'score', 'judge_status', 'adoption', 'included_in_mean', 'adopted_task_mean', 'origin', 'settings', 'note', 'raw_task_score', 'effective_raw_task_score'];
  const rows = data.records.filter(r => (!taskId || r.task === taskId) && (!adoptedOnly || adoptedStatuses.has(r.adoption))).map(r => {
    const summary = liteTaskSummary(data, r.model, r.task);
    return [r.id, data.protocol, r.task, r.track, names.get(r.model), r.attempt ?? '', r.score ?? '', r.judge_status,
      r.adoption, adoptedStatuses.has(r.adoption), summary.score ?? '', r.origin, r.settings, r.note, r.raw_task_score ?? '', r.effective_raw_task_score ?? ''];
  });
  return [header, ...rows].map(row => row.map(x => `"${String(x).replaceAll('"','""')}"`).join(',')).join('\r\n') + '\r\n';
}

function quality(summary) {
  if (!summary.complete) return '<span class="lite-status pending">Pending</span>';
  return '';
}
const taskNotes = {
  theorem: 'Success means a complete Lean proof of the main theorem.',
  solver: 'Development uses public instances, followed by one final evaluation on hidden instances. A score of 50 matches the fixed Kimi K3 reference.',
  construction: '100 represents the task’s reference result; higher scores indicate an improvement.',
  open: 'Resolution means a complete Lean proof or refutation of the conjecture.',
};
function taskCount(row) {
  const count = binary(row.task.track) && row.complete
    ? `${row.adopted.reduce((n,r) => n + r.score, 0)} / ${row.adopted.length} successful`
    : `${row.adopted.length} / ${row.model.attempts_per_task} attempts`;
  return `${count}${row.unresolved.length ? ' · pending' : ''}`;
}
export function summarizeLiteIndex(data) {
  const tracks = Object.keys(INDEX_WEIGHTS);
  const summaries = Object.fromEntries(tracks.map(t => [t, summarizeLite(data, t)]));
  return data.models.map((model, i) => {
    const scores = Object.fromEntries(tracks.map(t => [t, summaries[t][i]]));
    const means = Object.fromEntries(tracks.map(t => [t, scores[t].score]));
    return {model, scores, score: weightedIndex(means),
      contributions: Object.fromEntries(tracks.map(t => [t, means[t] == null ? null : INDEX_WEIGHTS[t] * means[t]])),
      attempts: tracks.reduce((n, t) => n + scores[t].attempts, 0)};
  });
}

export function renderLiteOverview(data, tracks, sortTrack = 'index') {
  const taskCounts = Object.fromEntries(tracks.map(t => [t.id, data.tasks.filter(task => task.track === t.id).length]));
  return renderResultsTable(summarizeLiteIndex(data), tracks, sortTrack, {scope:'lite', taskCounts});
}

export {bindIndexInteractions as bindLiteIndexInteractions} from './index-chart.js';

export function renderLiteIndex(data, tracks) {
  return renderIndexChart(summarizeLiteIndex(data), tracks, {scope:'lite', taskCount:data.tasks.length});
}

export function renderLiteTrack(data, track) {
  return renderTrackChart(summarizeLite(data, track.id), track, {
    scope:'lite', taskCount:data.tasks.filter(t => t.track === track.id).length,
  });
}

export function renderLiteTaskResults(task, data) {
  const rows = sortByScore(data.models.map(m => liteTaskSummary(data,m.id,task.id)), r => r.score);
  const minimum = Math.min(0, ...rows.map(r => r.score ?? 0));
  const maximum = Math.max(1, ...rows.map(r => r.score ?? 0));
  const zero = 100 * -minimum / (maximum - minimum);
  return `<section class="lite-task-results" id="lite-task-results" aria-labelledby="lite-task-results-title" data-protocol="${data.protocol}" data-result-panel="lite"><div class="task-results-heading"><h2 class="brand-heading" id="lite-task-results-title">${brandWordmark()}-Lite results</h2><span>12 h per attempt</span></div>
    <table class="task-results-table"><caption class="sr-only">${esc(task.title)}: ${data.models.length} models on the Lite subset, sorted by score, highest first. ${liteMetric(task.track)} (%).</caption><thead><tr><th scope="col">Model</th><th scope="col" aria-sort="descending">${liteMetric(task.track)} (%)</th><th scope="col">Attempts</th></tr></thead><tbody>${rows.map(r => `<tr data-lite-model="${r.model.id}"><th scope="row">${modelLabel(r.model.label)}</th><td><div class="task-score"><span class="task-score-meter" aria-hidden="true"><i style="left:${zero + 100 * Math.min(0, r.score ?? 0) / (maximum - minimum)}%;width:${100 * Math.abs(r.score ?? 0) / (maximum - minimum)}%"></i>${minimum < 0 ? `<b style="left:${zero}%"></b>` : ''}</span><span class="task-score-value">${liteValue(r.score,task.track)}</span></div>${quality(r)}</td><td>${taskCount(r)}</td></tr>`).join('')}</tbody></table>
    <p class="task-result-note">${taskNotes[task.track]}</p>
  </section>`;
}
