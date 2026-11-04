import {modelLabel} from './model-label.js';
import {sortByScore} from './result-order.js';
import {formatScore} from './score-format.js';
import {formatIndex} from './lite-index.js';

const esc = text => String(text).replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
export const trackMetric = track => ({theorem:'Complete-proof success', solver:'Relative score', construction:'Mean task score', open:'Resolution rate'})[track];
export const solverNoteRef = scope => `<sup class="solver-protocol-ref"><a href="#${scope}-solver-protocol-note" aria-label="Note 1: Full and Lite Solver protocols">1</a></sup>`;
const quality = summary => summary.complete === false ? '<span class="lite-status pending">Pending</span>' : '';

// Both suites supply exact scores and task counts to the same presentation.
export function renderResultsTable(summaries, tracks, sortTrack, {scope, taskCounts}) {
  const rows = sortByScore(summaries, r => sortTrack === 'index' ? r.score : r.scores[sortTrack].score);
  const suite = scope === 'lite' ? 'Lite' : 'Full';
  const taskCount = Object.values(taskCounts).reduce((sum, n) => sum + n, 0);
  const columns = [{id:'index', label:'Index', detail:'Weighted score'}, ...tracks.map(t => ({
    id:t.id, label:`${t.short} (%)`, detail:`${taskCounts[t.id]} tasks · ${trackMetric(t.id)}`,
  }))];
  return `<div class="paper-table-scroll results-overview ${scope}-overview index-overview" role="region" aria-label="${suite} results, horizontally scrollable" tabindex="0"><table class="paper-main-table">
    <caption class="sr-only">TCSExam-${suite}: ${rows.length} models, ${taskCount} tasks. Sorted by ${esc(sortTrack)}, highest first.</caption>
    <thead><tr><th scope="col">Model</th>${columns.map(c => `<th scope="col" data-track="${c.id}" aria-sort="${c.id === sortTrack ? 'descending' : 'none'}"><button type="button" data-result-sort="${c.id}" aria-label="Sort by ${esc(c.label)}, highest first">${esc(c.label)} <i aria-hidden="true">${c.id === sortTrack ? '↓' : '↕'}</i></button>${c.id === 'solver' ? solverNoteRef(scope) : ''}<span>${esc(c.detail)}</span></th>`).join('')}</tr></thead>
    <tbody>${rows.map(({model,scores,score}) => `<tr data-${scope}-model="${esc(model.id)}"><th scope="row">${modelLabel(model.label)}</th><td data-track="index"><strong>${formatIndex(score)}</strong></td>${tracks.map(t => `<td data-track="${t.id}"><strong>${formatScore(scores[t.id].score)}</strong>${quality(scores[t.id])}</td>`).join('')}</tr>`).join('')}</tbody>
  </table></div>`;
}

export function renderTrackChart(summaries, track, {scope, taskCount}) {
  const rows = sortByScore(summaries, s => s.score);
  const maximum = Math.max(1, ...rows.map(s => Math.abs(s.score ?? 0)));
  return `<div class="score-chart track-score-chart ${scope === 'lite' ? 'lite' : 'paper'}-score-chart" data-track="${track.id}">
    <div class="score-chart-heading"><div><h3 tabindex="-1">${esc(track.label)} (%)${track.id === 'solver' ? solverNoteRef(scope) : ''}</h3><p>${trackMetric(track.id)} · ${taskCount} tasks</p></div></div>
    <div class="model-bars">${rows.map(s => `<div class="model-row" data-${scope}-model="${esc(s.model.id)}">${modelLabel(s.model.label)}<div class="bar-track"><div class="bar ${s.score < 0 ? 'negative' : ''}" style="width:${100 * Math.abs(s.score ?? 0) / maximum}%"></div></div><strong>${formatScore(s.score)}${quality(s)}</strong></div>`).join('')}</div>
  </div>`;
}
