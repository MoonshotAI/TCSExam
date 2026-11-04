import test from 'node:test';
import assert from 'node:assert/strict';
import {readSiteData,validateSiteData} from '../tools/check-data.mjs';

const data=readSiteData();
test('Every task and model has consistent results and Index inputs',()=>validateSiteData(data));

test('Data validation rejects missing scores, duplicate tasks and attempts, and changed results',()=>{
  for(const change of [
    d=>d.catalogue.tasks.pop(),
    d=>d.catalogue.tasks[1]=d.catalogue.tasks[0],
    d=>d['lite-results'].records.push({...d['lite-results'].records[0],id:'duplicate'}),
    d=>d['full-results'].tasks[0].results[0].attempts.pop(),
    d=>d['full-results'].tasks[0].results[0].mean+=0.1,
    d=>d['lite-index'].models[0].index+=0.1,
    d=>d['full-index'].models[0].index+=0.1,
  ]) {
    const changed=structuredClone(data);change(changed);
    assert.throws(()=>validateSiteData(changed));
  }
});

test('Website inputs exclude internal evaluation settings and source paths',()=>{
  for(const change of [
    d=>d['full-results'].model_settings={agent:'internal'},
    d=>d['lite-results'].records[0].source={file:'internal'},
    d=>d.catalogue.tasks[0].note='/home/private/results.json',
  ]) {
    const changed=structuredClone(data);change(changed);
    assert.throws(()=>validateSiteData(changed));
  }
});
