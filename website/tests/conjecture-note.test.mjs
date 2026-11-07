import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {conjectureDetails, conjectureSources} from '../src/conjecture-note.js';
import {renderPaperTrack} from '../src/paper.js';
import {renderLiteOverview, renderLiteTrack, renderLiteIndex} from '../src/lite-results.js';
import {renderTaskResults} from '../src/catalogue/task-results.js';
import viteConfig from '../vite.config.js';

const read = name => JSON.parse(readFileSync(new URL(`../public/data/${name}.json`, import.meta.url)));
const full = read('full-results'), index = read('full-index'), benchmark = read('benchmark'), lite = read('lite-results');

test('Source notes accompany each Full conjecture results view and leave Lite unchanged', () => {
  for (const [track, view] of [['index', 'chart'], ['open', 'chart'], ['index', 'table'], ['open', 'table']]) {
    const html = renderPaperTrack(benchmark, track, view, index);
    assert.match(html, /data-conjecture-note/);
    for (const button of html.matchAll(/<button\b[^>]*>([\s\S]*?)<\/button>/g)) assert.doesNotMatch(button[1], /<a\b/);
  }
  for (const html of [renderLiteOverview(lite, benchmark.tracks, 'index'), renderLiteTrack(lite, benchmark.tracks.find(t => t.id === 'open')), renderLiteIndex(lite, benchmark.tracks)]) {
    assert.doesNotMatch(html, /data-conjecture-note/);
  }
});

test('Accepted attempt counts come from results and link to the corresponding site tasks', () => {
  const html = conjectureDetails(full);
  const rows = [...html.matchAll(/<tr><th scope="row">(.*?)<\/th><td><a href="(.*?)"[^>]*>(.*?)<\/a><\/td><td>(.*?)<\/td><\/tr>/g)];
  assert.deepEqual(rows.map(row => [row[1], row[3], row[4]]), [
    ['Kimi K3.1 Pro', 'Ryser', '1 / 3'],
    ['DeepSeek V4.1 Flash 1017', 'Ryser', '2 / 3'],
    ['DeepSeek V4.1 Flash 1017', 'MIRUP', '3 / 3'],
  ]);
  assert.deepEqual(new Set(rows.map(row => row[2])), new Set(Object.values(conjectureSources).map(source => source.url)));
  assert(rows.every(row => /^tasks\/(ryser-conjecture|bin-packing-mirup)\/$/.test(row[2])));
});

test('Only Ryser and MIRUP task results link to their local source explanation', () => {
  const catalogue = read('catalogue');
  for (const task of catalogue.tasks.filter(task => task.track === 'open')) {
    const html = renderTaskResults(task, full.tasks.find(row => row.id === task.id), full);
    if (Object.hasOwn(conjectureSources, task.id)) {
      assert.match(html, new RegExp(`href="tasks/${task.id}/#open-conjecture-details"`));
      assert.equal((html.match(/id="open-conjecture-details"/g) || []).length, 1);
    } else assert.doesNotMatch(html, /data-conjecture-note|id="open-conjecture-details"/);
  }
});

test('The static homepage provides the source explanation before JavaScript runs', () => {
  const source = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  const html = viteConfig.plugins.find(plugin => plugin.name === 'site-html').transformIndexHtml(source);
  assert.doesNotMatch(html, /MaxSAT and radiation-planning scores|<!-- conjecture-(?:note|details) -->/);
  assert.equal((html.match(/id="open-conjecture-details"/g) || []).length, 1);
  assert.match(html, /were evaluated afterward, with Internet access/);
  assert.doesNotMatch(html, /See details\./);
});
