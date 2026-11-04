import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {pauliMasks, quantumChecks, quantumOutcome, stabilizerContains} from '../src/quantum-code-case.js';
const data=JSON.parse(await readFile(new URL('../public/paper/quantum-code.json',import.meta.url),'utf8'));
const asWord=([x,z])=>Array.from({length:25},(_,i)=>'IXZY'[(x>>i&1)+2*(z>>i&1)]).join('');

test('The reference and submitted generator sets commute and have 18 independent rows',()=>{
 for(const code of [data.reference,data.astra]) {
  const rows=code.generators_xz;
  assert.equal(rows.length,18);
  rows.forEach((row,i)=>{
   const word=asWord(row);
   assert.deepEqual(quantumChecks(rows,word),Array(18).fill(0));
   assert(stabilizerContains(rows,word));
   assert(!stabilizerContains(rows.filter((_,j)=>i!==j),word));
  });
 }
});
test('The same weight-five logical error is missed by the reference and detected by Astra',()=>{
 const example=data.examples.five;
 assert.deepEqual(pauliMasks(example.paulis),{x:example.x,z:example.z});
 assert.equal([...example.paulis].filter(p=>p!=='I').length,5);
 for(const id of ['reference','astra'])assert.deepEqual(quantumChecks(data[id].generators_xz,example.paulis),example[`${id}_checks`]);
 assert.equal(quantumOutcome(data.reference.generators_xz,example.paulis),'undetected');
 assert.equal(quantumOutcome(data.astra.generators_xz,example.paulis),'detected');
});
test('The six-error example is logical, and removing any one of its errors is detected',()=>{
 const word=data.examples.six.paulis,rows=data.astra.generators_xz;
 assert.equal([...word].filter(p=>p!=='I').length,6);
 assert.equal(quantumOutcome(rows,word),'undetected');
 [...word].forEach((op,i)=>{
  if(op!=='I')assert.equal(quantumOutcome(rows,word.slice(0,i)+'I'+word.slice(i+1)),'detected');
 });
});
test('All 75 single-qubit errors in Astra are detected; harmless operations are not called missed errors',()=>{
 const clean='I'.repeat(25);
 assert.equal(quantumOutcome(data.astra.generators_xz,clean),'clear');
 for(let i=0;i<25;i++)for(const op of ['X','Y','Z'])assert.equal(quantumOutcome(data.astra.generators_xz,clean.slice(0,i)+op+clean.slice(i+1)),'detected');
 for(const code of [data.reference,data.astra])for(const row of code.generators_xz)assert.equal(quantumOutcome(code.generators_xz,asWord(row)),'harmless');
});
