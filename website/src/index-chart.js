import {modelLabel} from './model-label.js';
import {brandWordmark} from './brand.js';
import {sortByScore} from './result-order.js';
import {formatScore} from './score-format.js';
import {INDEX_WEIGHTS,formatIndex} from './lite-index.js';
const esc = text => String(text).replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));

export function bindIndexInteractions(root) {
  let hovered = null, focused = null, pinned = null;
  const control = target => target?.closest?.('[data-index-track]');
  const update = () => {
    const chart = root.querySelector('.tcsexam-index-chart');
    if (!chart) return;
    const track = hovered || focused || pinned || '';
    if (chart.dataset.activeTrack === track) return;
    chart.dataset.activeTrack = track;
    chart.querySelectorAll('[data-index-track]').forEach(button => {
      button.setAttribute('aria-pressed', String(button.dataset.indexTrack === track));
    });
    chart.querySelectorAll('.index-track-score').forEach(label => {
      label.hidden = label.dataset.track !== track;
    });
    const caption = chart.querySelector('.index-active-caption');
    caption.textContent = track ? chart.querySelector(`.index-legend [data-index-track="${track}"]`).dataset.scoreLabel : '';
    caption.dataset.track = track;
  };
  root.addEventListener('pointerover', event => {
    if (event.pointerType === 'touch') return;
    hovered = control(event.target)?.dataset.indexTrack || null;
    update();
  });
  root.addEventListener('pointerout', event => {
    if (event.pointerType === 'touch') return;
    hovered = control(event.relatedTarget)?.dataset.indexTrack || null;
    update();
  });
  root.addEventListener('focusin', event => {
    focused = control(event.target)?.dataset.indexTrack || null;
    update();
  });
  root.addEventListener('focusout', event => {
    focused = control(event.relatedTarget)?.dataset.indexTrack || null;
    update();
  });
  root.addEventListener('click', event => {
    const button = control(event.target);
    if (!button) { hovered = focused = pinned = null; update(); return; }
    const track = button.dataset.indexTrack;
    pinned = pinned === track ? null : track;
    focused = null;
    if (event.pointerType === 'touch') hovered = null;
    update();
  });
  root.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    hovered = focused = pinned = null;
    update();
  });
}

export function renderIndexChart(summaries, tracks, {scope = 'lite', taskCount = 20} = {}) {
  const rows = sortByScore(summaries, r => r.score);
  const maximum = Math.max(100, Math.ceil(Math.max(0, ...rows.map(r => r.score ?? 0)) / 10) * 10);
  return `<div class="score-chart tcsexam-index-chart ${scope}-index-chart" data-track="index" data-active-track="" role="group" aria-label="${taskCount}-task Index chart"><div class="score-chart-heading"><h3 class="brand-heading" tabindex="-1" aria-label="TCSExam Index, higher is better">${brandWordmark()} Index <span class="score-direction" aria-hidden="true">(↑)</span></h3></div>
    <div class="index-legend" role="group" aria-label="Track weights. Hover or select a track to compare scores.">${tracks.map(t => `<button type="button" data-index-track="${t.id}" data-track="${t.id}" data-score-label="${esc(t.label)} (%)" aria-pressed="false" aria-label="Show all models’ ${esc(t.label)} scores"><span>${esc(t.short)}</span> <b>${INDEX_WEIGHTS[t.id]}%</b></button>`).join('')}</div>
    <p class="sr-only index-active-caption" aria-live="polite" aria-atomic="true"></p>
    <div class="model-bars">${rows.map(r => {
      let offset = 0;
      const labels = [];
      const segments = tracks.map(t => {
        const width = r.score == null ? 0 : 100 * Math.max(0, r.contributions[t.id]) / maximum;
        const first = offset === 0 && width > 0;
        const center = Math.min(94, Math.max(6, offset + width / 2));
        offset += width;
        labels.push(`<span class="index-track-score" data-track="${t.id}" style="left:clamp(24px, ${center}%, calc(100% - 24px))" hidden>${formatScore(r.scores[t.id].score)}</span>`);
        return `<button type="button" class="index-segment" data-first="${first}" data-index-track="${t.id}" data-track="${t.id}" style="width:${width}%" aria-pressed="false" aria-label="${esc(r.model.label)}, ${esc(t.label)}: ${formatScore(r.scores[t.id].score)} percent. Show all models’ scores." tabindex="-1"></button>`;
      }).join('');
      return `<div class="model-row" data-${scope}-model="${r.model.id}">${modelLabel(r.model.label)}<div class="index-bar" role="group" aria-label="${esc(r.model.label)} track contributions"><div class="index-stack" style="--result-fill:${Math.min(100, offset)}%">${segments}</div>${labels.join('')}</div><strong class="index-value">${formatIndex(r.score)}</strong></div>`;
    }).join('')}</div>
    <div class="index-axis" aria-hidden="true"><span>0</span><span>${maximum / 2}</span><span>${maximum}</span></div></div>`;
}
