export const INDEX_METRIC = 'tcsexam-index-original-30303010-v0.1';
export const INDEX_WEIGHTS = {theorem:30, solver:30, construction:30, open:10};

const points = new Intl.NumberFormat('en-US', {
  minimumFractionDigits:1, maximumFractionDigits:1, useGrouping:false,
});
export const formatIndex = value => value == null ? '—' : points.format(value);

// Inputs are the original track means, before percentage formatting or rounding.
// Missing tracks invalidate the Index; weights are never redistributed.
export function weightedIndex(scores) {
  const entries = Object.entries(INDEX_WEIGHTS);
  if (entries.some(([track]) => !Number.isFinite(scores[track]))) return null;
  return entries.reduce((sum, [track, weight]) => sum + weight * scores[track], 0);
}

export function indexResultsCsv(data) {
  const tracks = Object.keys(INDEX_WEIGHTS);
  const protocolFields = ['suite','solver_protocol','solver_reference_id'];
  const header = ['model','model_label','index',...tracks.map(t=>`${t}_percent`),
    ...tracks.map(t=>`${t}_points`),'tasks','attempts','repetitions_per_task','status','metric_id','snapshot',...protocolFields];
  const rows = [...data.models].sort((a,b)=>b.index-a.index).map(row => [
    row.model,row.model_label,row.index,...tracks.map(t=>100*row[t]),
    ...tracks.map(t=>row[`${t}_points`]),row.tasks,row.attempts,row.repetitions_per_task,
    row.status,data.metric_id,data.generated_at,...protocolFields.map(key=>data[key]),
  ]);
  return [header,...rows].map(row=>row.map(value=>`"${String(value).replaceAll('"','""')}"`).join(',')).join('\r\n')+'\r\n';
}
