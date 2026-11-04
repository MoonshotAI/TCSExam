import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {weightedIndex,formatIndex,indexResultsCsv} from '../src/lite-index.js';
import {summarizeLiteIndex,renderLiteIndex} from '../src/lite-results.js';
import {validateIndex} from '../tools/check-lite-index.mjs';
import {readResultsLocation,writeResultsLocation} from '../src/results-location.js';
const read=n=>JSON.parse(readFileSync(new URL(`../public/data/${n}.json`,import.meta.url)));
const lite=read('lite-results'), index=read('lite-index'), tracks=read('benchmark').tracks;

test('The eight public Index scores match the handoff and adopted per-task means',()=>{
  validateIndex(index,lite);
  const rows=summarizeLiteIndex(lite).sort((a,b)=>b.score-a.score);
  assert.deepEqual(rows.map(r=>[r.model.label,formatIndex(r.score)]),[
    ['Opus 5.5','72.3'],['GPT-6 Astra','67.0'],['Kimi K3.1 Pro','53.5'],['Kimi K3','48.6'],['GLM-5.3','47.0'],
    ['Qwen3.8 Max (0902)','45.4'],['DeepSeek V4.1 Flash 1017','42.4'],['Grok 4.6','42.1'],
  ]);
  for(const r of rows) assert(Math.abs(r.score-index.models.find(m=>m.model===r.model.id).index)<1e-12);
  assert.equal(indexResultsCsv(index).trim().split('\r\n').length,9);
  assert.equal(indexResultsCsv(index),readFileSync(new URL('../public/data/lite-index.csv',import.meta.url),'utf8'));
});

test('Index is not capped or calculated from rounded display values; missing tracks remain unavailable',()=>{
  assert.equal(weightedIndex({theorem:1,solver:1,construction:2,open:1}),130);
  assert.equal(weightedIndex({theorem:1,solver:null,construction:2,open:1}),null);
  assert.equal(weightedIndex({theorem:1,solver:1,construction:1}),null);
  const changed=structuredClone(lite);
  changed.records=changed.records.filter(r=>!(r.model==='astra'&&r.task===changed.tasks[0].id));
  assert.equal(summarizeLiteIndex(changed).find(r=>r.model.id==='astra').score,null);
  assert.equal(formatIndex(null),'—');
  const row=summarizeLiteIndex(lite).find(r=>r.model.id==='opus55');
  assert.notEqual(row.score,72.27);
  const large=structuredClone(lite);
  for(const r of large.records.filter(r=>r.model==='astra'&&r.track==='construction'))r.score=4;
  const html=renderLiteIndex(large,tracks);
  const widths=[...html.matchAll(/class="index-segment"[^>]+style="width:([\d.]+)%/g)].map(m=>Number(m[1]));
  assert(widths.every(w=>w>=0&&w<=100));
  assert.equal(widths.length,32);
  assert.match(html,/>160<\/span>/);
});

test('Import validation rejects altered scores, weights, task selections, and extra models',()=>{
  for(const mutate of [
    d=>d.models[0].index+=.01,
    d=>d.weights.open=0,
    d=>delete d.suite,
    d=>d.solver_protocol='solver-development-feedback-v1',
    d=>d.selected_items.solver.pop(),
    d=>d.models.push({...d.models[0],model:'experimental_11471'}),
    d=>d.models[0].solver_points+=1,
  ]){const d=structuredClone(index);mutate(d);assert.throws(()=>validateIndex(d,lite));}
});

test('DeepSeek 1017 retains three attempts per task and the adopted R(4,6) judgment',()=>{
  const row=index.models.find(r=>r.model==='deepseek_flash_1017');
  assert.equal(row.index,42.37257998257034);
  const records=lite.records.filter(r=>r.model===row.model);
  assert.equal(records.length,60);
  assert.deepEqual(records.filter(r=>r.task==='ramsey-r46').map(r=>r.score),[1,1,1]);
  for(const task of lite.tasks) assert.deepEqual(records.filter(r=>r.task===task.id).map(r=>r.attempt),[1,2,3]);
  assert(!index.models.some(r=>r.model==='deepseek'));
  assert.match(renderLiteIndex(lite,tracks),/deepseek\.svg[^]*DeepSeek V4\.1 Flash 1017/);
});

test('Kimi K3.1 Pro Lite includes all three runs with unbounded construction rewards',()=>{
  const row=index.models.find(r=>r.model==='k31_pro');
  assert.equal(row.index,53.493003909240194);
  const records=lite.records.filter(r=>r.model===row.model);
  assert.equal(records.length,60);
  for(const task of lite.tasks) assert.deepEqual(records.filter(r=>r.task===task.id).map(r=>r.attempt),[1,2,3]);
  assert.equal(records.find(r=>r.task==='binary-code-a24-10' && r.attempt===3).score,1.19001);
  assert.equal(records.find(r=>r.task==='ramsey-r46' && r.attempt===2).score,0);
});

test('Index is the Lite default; explicit theorem and Full tracks persist independently',()=>{
  const url=new URL('https://example.com/?release=abc#lite');
  const states=readResultsLocation(url);
  assert.deepEqual(states,{lite:{view:'chart',track:'index'},full:{view:'chart',track:'index'}});
  states.lite={view:'table',track:'theorem'};states.full={view:'chart',track:'solver'};
  writeResultsLocation(url,states);
  assert.equal(url.searchParams.get('lite-track'),'theorem');
  assert.equal(url.searchParams.get('lite-view'),'table');
  assert.equal(url.searchParams.get('release'),'abc');
  assert.deepEqual(readResultsLocation(url),states);
  assert.equal(readResultsLocation(new URL('https://example.com/?full-track=index#full')).full.track,'index');
  assert.equal(readResultsLocation(new URL('https://example.com/?protocol=lite-v0.1-final-once&track=solver&view=chart#results')).lite.track,'solver');
});

test('Lite and Full Index exports identify their suite, Solver protocol and fixed reference',()=>{
  for(const [data,suite,protocol] of [
    [index,'lite','solver-final-once-v1'],
    [read('full-index'),'full','solver-development-feedback-v1'],
  ]) {
    const csv=indexResultsCsv(data).trim().split('\r\n').map(line=>line.split(',').map(cell=>cell.slice(1,-1)));
    const header=csv[0];
    for(const row of csv.slice(1)) {
      assert.equal(row[header.indexOf('suite')],suite);
      assert.equal(row[header.indexOf('solver_protocol')],protocol);
      assert.equal(row[header.indexOf('solver_reference_id')],'paper-k3-fixed-260925');
    }
  }
  assert.equal(read('full-results').protocol,'full-development-feedback-v1');
});
