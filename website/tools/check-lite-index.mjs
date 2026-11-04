import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
import {INDEX_METRIC,INDEX_WEIGHTS,weightedIndex} from '../src/lite-index.js';
import {summarizeLite} from '../src/lite-results.js';

export function validateIndex(data, lite) {
  assert.equal(data.schema_version,1);
  assert.equal(data.metric_id,INDEX_METRIC);
  assert.equal(data.benchmark,'TCSExam-Lite');
  assert.equal(data.suite,'lite');
  assert.equal(data.solver_protocol,'solver-final-once-v1');
  assert.equal(data.formula,'30P + 30S + 30C + 10O');
  assert.equal(data.solver_reference_id,'paper-k3-fixed-260925');
  assert.equal(data.construction_transform,'identity');
  assert.deepEqual(data.weights,INDEX_WEIGHTS);
  assert.equal(data.models.length,lite.models.length);
  assert.deepEqual(new Set(data.models.map(m=>m.model)),new Set(lite.models.map(m=>m.id)));
  const near=(a,b)=>assert(Number.isFinite(a)&&Math.abs(a-b)<1e-12,`${a} != ${b}`);
  const summaries=Object.fromEntries(Object.keys(INDEX_WEIGHTS).map(t=>[t,summarizeLite(lite,t)]));
  for(const track of Object.keys(INDEX_WEIGHTS)) {
    assert.deepEqual(new Set(data.selected_items[track]),new Set(lite.tasks.filter(t=>t.track===track).map(t=>t.id)));
  }
  for(const row of data.models) {
    const model=lite.models.find(m=>m.id===row.model);
    assert.equal(row.model_label,model.label);
    assert.equal(row.tasks,20);assert.equal(row.repetitions_per_task,model.attempts_per_task);
    assert.equal(row.attempts,20*model.attempts_per_task);
    let provisional=false;
    for(const [track,weight] of Object.entries(INDEX_WEIGHTS)) {
      const summary=summaries[track].find(s=>s.model.id===row.model);
      assert(summary.complete);near(row[track],summary.score);
      near(row[`${track}_points`],weight*summary.score);
      provisional ||= summary.provisional;
    }
    assert.equal(row.status,provisional?'provisional':'adopted');
    near(row.index,weightedIndex(row));
  }
  assert(!/\/home\/|\/mnt\/|msh\.team|experimental_|11410|11471|11531/.test(JSON.stringify(data)),'Only the public models belong in this release');
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href) {
  const read=name=>JSON.parse(readFileSync(new URL(`../public/data/${name}.json`,import.meta.url)));
  const index=read('lite-index');validateIndex(index,read('lite-results'));
  console.log(`Lite Index valid: ${index.models.length} models; all track means and weighted contributions match adopted website results.`);
}
