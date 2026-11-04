import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
import {INDEX_METRIC,INDEX_WEIGHTS,weightedIndex} from '../src/lite-index.js';

export function validateFullIndex(data, results) {
  assert.equal(data.schema_version,1);
  assert.equal(data.metric_id,INDEX_METRIC);
  assert.equal(data.benchmark,'TCSExam-Full');
  assert.equal(data.suite,'full');
  assert.equal(data.solver_protocol,'solver-development-feedback-v1');
  assert.equal(data.solver_reference_id,'paper-k3-fixed-260925');
  assert.equal(data.formula,'30P + 30S + 30C + 10O');
  assert.equal(data.construction_transform,'identity');
  assert.equal(data.aggregation,'mean_adopted_attempts_within_task_then_equal_task_mean_within_track');
  assert.equal(data.missing_policy,'no_zero_imputation_no_weight_renormalization');
  assert.equal(data.display_unit,'index_points_not_success_percentage');
  assert.equal(data.upper_bound,null);
  assert.equal(data.input_scope,'adopted_paper_snapshot_and_published_full_supplements');
  assert.deepEqual(data.weights,INDEX_WEIGHTS);
  assert.equal(results.protocol,'full-development-feedback-v1');
  assert.equal(data.models.length,7);
  assert.deepEqual(new Set(data.models.map(m=>m.model)),new Set(results.models.map(m=>m.id)));
  const counts={theorem:20,solver:30,construction:20,open:30};
  const mean=values=>values.reduce((a,b)=>a+b,0)/values.length;
  const near=(a,b)=>assert(Number.isFinite(a)&&Number.isFinite(b)&&Math.abs(a-b)<1e-12,`${a} != ${b}`);
  for(const [track,count] of Object.entries(counts)) {
    const items=data.selected_items[track];
    assert.equal(items.length,count);
    assert.equal(new Set(items).size,count);
    assert.deepEqual(new Set(items),new Set(results.tasks.filter(t=>t.track===track).map(t=>t.id)));
  }
  let attempts=0;
  for(const row of data.models) {
    const model=results.models.find(m=>m.id===row.model);
    assert.equal(row.model_label,model.label);
    assert.equal(row.tasks,100);
    assert.equal(row.repetitions_per_task,model.attempts_per_task);
    assert.equal(row.attempts,100*model.attempts_per_task);
    assert.equal(row.status,'adopted');
    assert.equal(row.result_status,'complete_for_this_cohort');
    assert.equal(row.solver_protocol,data.solver_protocol);
    for(const [track,weight] of Object.entries(INDEX_WEIGHTS)) {
      const scores=results.tasks.filter(t=>t.track===track).map(task=>{
        const cell=task.results.find(r=>r.model===row.model);
        assert(cell,`Missing ${row.model}/${task.id}`);
        assert.equal(cell.attempts.length,model.attempts_per_task);
        const values=cell.attempts.map(a=>a.score);
        assert(values.every(v=>Number.isFinite(v)&&v>=0));
        if(track==='theorem'||track==='open')assert(values.every(v=>v===0||v===1));
        if(track==='solver')assert(values.every(v=>v<=1));
        attempts+=values.length;
        near(cell.mean,mean(values));
        return mean(values);
      });
      near(row[track],mean(scores));
      near(row[`${track}_points`],weight*row[track]);
    }
    near(row.index,weightedIndex(row));
  }
  assert.equal(attempts,1300);
  assert.equal(data.source_attempts,attempts);
  assert(!/\/home\/|\/mnt\/|msh\.team|experimental_|container_id|provider_id|Flash1017|opus55/.test(JSON.stringify(data)),'Full includes only the adopted paper and Full supplement models');
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href) {
  const read=name=>JSON.parse(readFileSync(new URL(`../public/data/${name}.json`,import.meta.url)));
  const index=read('full-index');validateFullIndex(index,read('full-results'));
  console.log(`Full Index valid: ${index.models.length} models, 100 tasks, ${index.source_attempts} attempts; all track means and contributions match Full results.`);
}
