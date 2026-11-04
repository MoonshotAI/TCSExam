import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {formatIndex,indexResultsCsv} from '../src/lite-index.js';
import {renderPaperTrack} from '../src/paper.js';
import {validateFullIndex} from '../tools/check-full-index.mjs';
const read=name=>JSON.parse(readFileSync(new URL(`../public/data/${name}.json`,import.meta.url)));
const index=read('full-index'),results=read('full-results'),benchmark=read('benchmark');

test('Full Index matches every adopted paper task and the published Full supplements',()=>{
  validateFullIndex(index,results);
  const ordered=[...index.models].sort((a,b)=>b.index-a.index);
  assert.deepEqual(ordered.map(r=>[r.model,formatIndex(r.index)]),[
    ['astra','71.9'],['k31_pro','57.4'],['k3max','46.8'],['deepseek_flash_1017','46.0'],['glm53','45.5'],['qwen38max','44.8'],['grok46','40.5'],
  ]);
  assert.equal(ordered[2].theorem,7/60);
  assert.notEqual(ordered[2].index,.117*30+.4873*30+.9555*30);
  const csv=indexResultsCsv(index);
  assert.equal(csv,readFileSync(new URL('../public/data/full-index.csv',import.meta.url),'utf8'));
  assert.equal(csv.trim().split('\r\n').length,8);
  assert.match(csv,/suite.*solver_protocol.*solver_reference_id/);
  assert.match(csv,/solver-development-feedback-v1/);
});

test('Full import rejects protocol mixing, missing attempts, altered contributions and extra models',()=>{
  for(const mutate of [
    d=>d.suite='lite',d=>d.solver_protocol='lite-v0.1-final-once',d=>d.weights.open=0,
    d=>d.models[0].index+=.01,d=>d.models[0].solver_points+=1,
    d=>d.models[0].theorem=.6,d=>d.selected_items.theorem.pop(),
    d=>d.models.push({...d.models[0],model:'opus55'}),d=>d.models[0].attempts=20,
  ]){const copy=structuredClone(index);mutate(copy);assert.throws(()=>validateFullIndex(copy,results));}
  const missing=structuredClone(results);missing.tasks[0].results[0].attempts=[];
  assert.throws(()=>validateFullIndex(index,missing));
  const changed=structuredClone(results);changed.tasks[0].results[0].attempts[0].score=1;
  assert.throws(()=>validateFullIndex(index,changed));
});

test('DeepSeek 1017 Full scores retain three runs and nonzero conjecture results',()=>{
  const row=index.models.find(r=>r.model==='deepseek_flash_1017');
  assert.equal(row.index,45.97143380857449);
  assert.equal(row.open,5/90);
  assert.equal(row.attempts,300);
  assert.notEqual(row.solver,.5433479994190112);
  const chart=renderPaperTrack(benchmark,'open','chart',index);
  const ids=[...chart.matchAll(/data-full-model="([^"]+)"/g)].map(m=>m[1]);
  assert.equal(ids[0],row.model);
  assert.match(chart,/5\.6/);
  assert(!index.models.some(r=>r.model==='deepseek'));
});

test('Kimi K3.1 Pro Full includes the third run and its conjecture score',()=>{
  const row=index.models.find(r=>r.model==='k31_pro');
  assert.equal(row.index,57.419775870742306);
  assert.equal(row.attempts,300);
  assert(Math.abs(row.open-1/90)<1e-12);
  assert.equal(row.solver,0.5406602753210398);
  const ryser=results.tasks.find(t=>t.id==='ryser-conjecture').results.find(r=>r.model===row.model);
  assert.deepEqual(ryser.attempts.map(a=>a.score),[0,0,1]);
});

test('Full table ranks by exact Index and each track; chart retains unbounded construction scores and seven models',()=>{
  const ids=html=>[...html.matchAll(/data-full-model="([^"]+)"/g)].map(m=>m[1]);
  const table=renderPaperTrack(benchmark,'index','table',index);
  assert.deepEqual(ids(table),['astra','k31_pro','k3max','deepseek_flash_1017','glm53','qwen38max','grok46']);
  assert.match(table,/>71\.9<\/strong>/);
  const construction=renderPaperTrack(benchmark,'construction','table',index);
  assert.deepEqual(ids(construction),['astra','k31_pro','glm53','k3max','qwen38max','deepseek_flash_1017','grok46']);
  assert.match(table,/Theorems \(%\)/);
  const chart=renderPaperTrack(benchmark,'index','chart',index);
  assert.deepEqual(ids(chart),ids(table));
  assert.match(chart,/100-task Index chart/);
  assert.match(chart,/104\.9 percent/);
  assert(!/attempts|provisional/i.test(chart));
  for(const track of benchmark.tracks){
    const html=renderPaperTrack(benchmark,track.id,'table',index);
    const trackChart=renderPaperTrack(benchmark,track.id,'chart',index);
    assert.deepEqual(ids(trackChart),ids(html));
    assert(!/attempts|table-meter|successful/i.test(html + trackChart));
    assert.match(trackChart,new RegExp(`${track.full_count} tasks`));
    const values=ids(html).map(id=>index.models.find(m=>m.model===id)[track.id]);
    assert(values.every((n,i)=>i===0||values[i-1]>=n));
  }
});
