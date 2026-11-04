import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
import {validateIndex} from './check-lite-index.mjs';
import {validateFullIndex} from './check-full-index.mjs';

export function readSiteData() {
  return Object.fromEntries(['benchmark','catalogue','lite-results','full-results','lite-index','full-index']
    .map(name => [name, JSON.parse(readFileSync(new URL(`../public/data/${name}.json`, import.meta.url)))]));
}

export function validateSiteData(data) {
  const benchmark=data.benchmark, catalogue=data.catalogue;
  const lite=data['lite-results'], full=data['full-results'];
  const counts={theorem:20,solver:30,construction:20,open:30};
  const unique=(items,key)=>assert.equal(new Set(items.map(item=>item[key])).size,items.length,`Duplicate ${key}`);
  const same=(a,b)=>assert.deepEqual(new Set(a),new Set(b));
  same(benchmark.tracks.map(t=>t.id),Object.keys(counts));
  assert.equal(catalogue.tasks.length,100); unique(catalogue.tasks,'id');
  assert.equal(benchmark.tasks.length,20); unique(benchmark.tasks,'id');
  same(benchmark.tasks.map(t=>t.id),catalogue.tasks.filter(t=>t.lite).map(t=>t.id));
  same(lite.tasks.map(t=>t.id),benchmark.tasks.map(t=>t.id));
  assert.equal(lite.tasks.length,20); unique(lite.tasks,'id');
  for(const [track,count] of Object.entries(counts)) {
    assert.equal(catalogue.tasks.filter(t=>t.track===track).length,count);
    assert.equal(benchmark.tracks.find(t=>t.id===track).full_count,count);
    assert.equal(lite.tasks.filter(t=>t.track===track).length,5);
  }
  const tasks=new Map(catalogue.tasks.map(t=>[t.id,t]));
  for(const t of [...benchmark.tasks,...lite.tasks]) assert.equal(t.track,tasks.get(t.id)?.track);
  for(const task of catalogue.tasks) {
    assert.match(task.id,/^[a-z0-9-]+$/);
    assert(task.title.length>0 && task.question_markdown.length>0);
  }
  assert.equal(lite.protocol,'lite-v0.1-final-once');
  assert.equal(full.protocol,'full-development-feedback-v1');
  assert.equal(benchmark.development_hours,12);
  assert.equal(lite.development_hours,12); assert.equal(full.development_hours,12);
  assert.equal(lite.models.length,8); unique(lite.models,'id'); unique(full.models,'id');
  for(const model of [...lite.models,...full.models]) assert([1,2,3].includes(model.attempts_per_task));
  unique(lite.records,'id');
  const models=new Set(lite.models.map(m=>m.id)), liteTasks=new Set(lite.tasks.map(t=>t.id));
  const chosen=new Set();
  for(const record of lite.records) {
    assert(models.has(record.model)); assert(liteTasks.has(record.task));
    assert.equal(record.track,tasks.get(record.task)?.track);
    assert(record.score===null || Number.isFinite(record.score));
    if(['selected','selected_provisional'].includes(record.adoption)) {
      assert.equal(record.judge_status,'completed');
      assert(Number.isInteger(record.attempt) && record.attempt>0);
      assert(record.attempt<=lite.models.find(m=>m.id===record.model).attempts_per_task);
      assert(Number.isFinite(record.score) && record.score>=0);
      if(['theorem','open'].includes(record.track)) assert([0,1].includes(record.score));
      if(record.track==='solver') assert(record.score<=1);
      const key=[record.model,record.task,record.attempt].join('/');
      assert(!chosen.has(key),'Duplicate adopted attempt');chosen.add(key);
    }
  }
  assert.equal(full.tasks.length,100); unique(full.tasks,'id');
  same(full.tasks.map(t=>t.id),catalogue.tasks.map(t=>t.id));
  for(const task of full.tasks) {
    assert.equal(task.track,tasks.get(task.id)?.track);
    same(task.results.map(r=>r.model),full.models.map(m=>m.id)); unique(task.results,'model');
    for(const row of task.results) {
      const model=full.models.find(m=>m.id===row.model);
      assert.deepEqual(row.attempts.map(a=>a.attempt),Array.from({length:model.attempts_per_task},(_,i)=>i+1));
    }
    if(task.coverage) {
      assert(Number.isInteger(task.coverage.scored_instances) && task.coverage.scored_instances>=0);
      assert(Number.isInteger(task.coverage.total_instances) && task.coverage.total_instances>=task.coverage.scored_instances);
    }
  }
  validateIndex(data['lite-index'],lite);
  validateFullIndex(data['full-index'],full);
  for(const value of Object.values(data)) {
    const json=JSON.stringify(value);
    assert.doesNotMatch(json,/"(?:source|settings|model_settings|evaluations|runtime_notes|exception_type|agent_seconds|source_commit|instruction_sha256)":/);
    assert.doesNotMatch(json,/\/home\/|\/mnt\/|msh\.team|TCSBENCH_TOKEN|container_id|provider_id/);
  }
}

if(process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href) {
  validateSiteData(readSiteData());
  console.log('Website data valid: 100 tasks, eight Lite models, seven Full models, and both weighted indices.');
}
