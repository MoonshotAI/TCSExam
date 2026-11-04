import {renderIndexChart} from './index-chart.js';
import {renderResultsTable, renderTrackChart} from './results-presentation.js';

export function renderPaperTrack(data, trackId, view = 'chart', index) {
  const summaries = index.models.map(row => ({
    model: {id:row.model, label:row.model_label}, score:row.index,
    scores: Object.fromEntries(data.tracks.map(t => [t.id, {score:row[t.id], complete:true}])),
    contributions: Object.fromEntries(data.tracks.map(t => [t.id, row[`${t.id}_points`]])),
  }));
  const taskCounts = Object.fromEntries(data.tracks.map(t => [t.id, t.full_count]));
  if (view === 'table') return renderResultsTable(summaries, data.tracks, trackId, {scope:'full', taskCounts});
  if (trackId === 'index') return renderIndexChart(summaries, data.tracks, {
    scope:'full', taskCount:Object.values(taskCounts).reduce((sum, n) => sum + n, 0),
  });
  return renderTrackChart(summaries.map(s => ({model:s.model, ...s.scores[trackId]})),
    data.tracks.find(t => t.id === trackId), {scope:'full', taskCount:taskCounts[trackId]});
}
