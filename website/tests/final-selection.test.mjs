import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {readSiteData,validateSiteData} from '../tools/check-data.mjs';
import {publicData} from '../tools/public-data.mjs';
import {indexResultsCsv} from '../src/lite-index.js';
import {renderTaskResults,taskResultsCsv} from '../src/catalogue/task-results.js';

const data=readSiteData(),full=data['full-results'],index=data['full-index'];
const selected=new Set(['maxsat-mse','radiation-mznchallenge']);
const digest=value=>createHash('sha256').update(value).digest('hex');
const scores=(tasks,key='score')=>tasks.flatMap(task=>task.results.flatMap(row=>row.attempts.map(attempt=>[task.id,row.model,attempt.attempt,attempt[key]])));

test('Final selection preserves the other 98 tasks and the original reported scores',()=>{
  const unaffected=scores(full.tasks.filter(task=>!selected.has(task.id)));
  assert.equal(unaffected.length,1274);
  assert.equal(digest(JSON.stringify(unaffected)),'be1f40ad764d00b9a9dffa071ffd0617a978d7cd68312e75a3d65e5995e38f81');
  const original=scores(full.tasks.filter(task=>selected.has(task.id)),'original_reported_score');
  assert.equal(original.length,26);
  assert.equal(digest(JSON.stringify(original)),'9877f7dcd793c5ed05bf9c802cb092e914953e14efc8d8a1e1d93bab072dc36e');
  const raw=full.tasks.filter(task=>selected.has(task.id)).flatMap(task=>task.results.flatMap(row=>row.attempts)).filter(attempt=>'raw_platform_score' in attempt);
  assert.equal(raw.length,12);
  assert(raw.every(attempt=>attempt.raw_platform_score!==attempt.score));
});

test('The Lite data and CSV retain their published bytes',()=>{
  for(const [name,sha] of Object.entries({
    'lite-results.json':'14c8c912ae6aea70c944bdbd67bbdda10f04e1f175034f7cd28f0a19104a0212',
    'lite-index.json':'26cb0ee2a1a503f44cca5b536201abf1ccd53e3fb57b68f0e362317c785cdd0e',
    'lite-index.csv':'ca21b85653ebe69ea77e2a650967a736b4e5e9ddb7ccda76d477263c158875ff',
  }))assert.equal(digest(readFileSync(new URL(`../public/data/${name}`,import.meta.url))),sha);
});

test('Full exports retain the selection identity without disclosing internal evidence',()=>{
  const published=publicData('full-index.json',index);
  assert.equal(published.evaluation_selection_id,'public-disjoint-final-261105');
  assert.equal(published.solver_reference_id,'paper-k3-fixed-260925-public-disjoint-261105');
  assert.equal(data['lite-index'].solver_reference_id,'paper-k3-fixed-260925');
  assert.equal(published.models.length,7);
  assert(!published.models.some(row=>row.model==='deepseek'));
  const csv=indexResultsCsv(index);
  assert.match(csv,/"evaluation_selection_id"/);
  assert.equal(csv.match(/public-disjoint-final-261105/g).length,7);
  assert.equal(csv.match(/paper-k3-fixed-260925-public-disjoint-261105/g).length,7);
  const attempt=full.tasks.find(task=>task.id==='maxsat-mse').results.find(row=>row.model==='k31_pro').attempts[0];
  assert.deepEqual(Object.keys(attempt).sort(),['attempt','evaluation_selection','original_reported_score','raw_platform_score','score','selected_ratio_score']);
});

test('Selected task pages and CSVs identify the final set and retain both score scales',()=>{
  for(const [id,total,scored] of [['maxsat-mse',200,177],['radiation-mznchallenge',36,36]]){
    const record=full.tasks.find(task=>task.id===id);
    const task=data.catalogue.tasks.find(task=>task.id===id);
    const html=renderTaskResults(task,record,full);
    assert.match(html,new RegExp(`Final evaluation uses ${total} instances with no overlap with public development instances; ${scored} contribute to the relative score`));
    const csv=taskResultsCsv(record,full);
    assert.match(csv,/original_reported_score/);
    assert.match(csv,/selected_ratio_score/);
    assert.match(csv,/raw_platform_score/);
    assert.equal(csv.match(/public-disjoint-final-261105/g).length,13);
    const lines=csv.trim().split('\r\n').map(line=>line.split(',').map(cell=>cell.slice(1,-1)));
    const header=lines[0],first=record.results[0].attempts[0];
    assert.equal(Number(lines[1][header.indexOf('original_reported_score')]),first.original_reported_score*100);
    assert.equal(Number(lines[1][header.indexOf('selected_ratio_score')]),first.selected_ratio_score);
  }
});

test('Validation rejects selection mismatches, missing provenance and internal attempt fields',()=>{
  for(const change of [
    d=>d['full-index'].solver_reference_id='paper-k3-fixed-260925',
    d=>d['full-index'].evaluation_selection_id='other-selection',
    d=>d['full-results'].evaluation_selection.selected_tasks.pop(),
    d=>d['full-results'].tasks.find(t=>t.id==='maxsat-mse').coverage.total_instances=211,
    d=>delete d['full-results'].tasks.find(t=>t.id==='maxsat-mse').results[0].attempts[0].original_reported_score,
    d=>d['full-results'].tasks.find(t=>t.id==='maxsat-mse').results[0].attempts[0].evaluation_selection='other-selection',
    d=>d['full-results'].tasks.find(t=>t.id==='maxsat-mse').results[0].attempts[0].run_id=123,
    d=>d['full-results'].tasks.find(t=>t.id==='maxsat-mse').results[0].attempts[0].selected_ratio_score=NaN,
  ]){const changed=structuredClone(data);change(changed);assert.throws(()=>validateSiteData(changed));}
  // Valid ratio scores may be negative or exceed one; only the relative score is bounded.
  validateSiteData(data);
  assert(full.tasks.find(t=>t.id==='maxsat-mse').results.some(row=>row.attempts.some(a=>a.selected_ratio_score<0)));
  assert(full.tasks.find(t=>t.id==='radiation-mznchallenge').results.some(row=>row.attempts.some(a=>a.selected_ratio_score>1)));
});
