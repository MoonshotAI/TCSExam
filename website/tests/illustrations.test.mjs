import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import katex from 'katex';
import {enrichTask} from '../src/catalogue/editorial.js';
import {renderIllustration, radiationExample, communicationExample} from '../src/catalogue/illustrations.js';

const tasks = JSON.parse(readFileSync(new URL('../public/data/catalogue.json', import.meta.url))).tasks.map(enrichTask);

test('All 100 task formulas and illustrations render', () => {
  assert.equal(tasks.length, 100);
  for (const task of tasks) {
    assert.doesNotThrow(() => katex.renderToString(task.diagramMath, {throwOnError: true, strict: 'error'}), task.id);
    const svg = renderIllustration(task);
    assert.match(svg, /<svg /, task.id);
    assert.doesNotMatch(svg, /NaN|undefined/, task.id);
  }
});

test('The illustrated radiation shapes reproduce the dose at minimum beam-on time', () => {
  const {intensity, shapes, times} = radiationExample;
  assert.equal(shapes.length, times.length);
  assert(times.every(t => Number.isInteger(t) && t > 0));
  for (const shape of shapes) {
    assert.equal(shape.length, intensity.length);
    shape.forEach((row, r) => {
      assert.equal(row.length, intensity[r].length);
      assert(row.every(v => v === 0 || v === 1));
      assert.match(row.join(''), /^0*1*0*$/);
    });
  }
  intensity.forEach((row, r) => row.forEach((value, c) => {
    assert.equal(shapes.reduce((sum, shape, j) => sum + times[j] * shape[r][c], 0), value);
  }));
  const lowerBound = Math.max(...intensity.map(row => row.reduce((sum, value, c) => sum + Math.max(0, value - (row[c - 1] ?? 0)), 0)));
  assert.equal(times.reduce((a, b) => a + b, 0), lowerBound);
});

test('The communication matrix satisfies the displayed rank assumption', () => {
  assert(communicationExample.flat().every(v => v === 0 || v === 1));
  const a = communicationExample;
  // A nonzero 2 by 2 minor proves rank at least two over the reals.
  const minors = [];
  for (let r = 0; r < a.length; r++) for (let s = r + 1; s < a.length; s++) {
    for (let c = 0; c < a[0].length; c++) for (let d = c + 1; d < a[0].length; d++) {
      minors.push(a[r][c] * a[s][d] - a[r][d] * a[s][c]);
    }
  }
  assert(minors.some(value => value !== 0));
});
