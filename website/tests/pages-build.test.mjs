import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {stagePages} from '../tools/build-pages.mjs';

function fixture(t) {
  const root = mkdtempSync(join(tmpdir(), 'tcsexam-pages-'));
  t.after(() => rmSync(root, {recursive: true, force: true}));
  const dist = join(root, 'dist');
  const docs = join(root, 'docs');
  mkdirSync(join(dist, 'paper'), {recursive: true});
  mkdirSync(join(docs, 'paper'), {recursive: true});
  writeFileSync(join(dist, 'index.html'), '<html>new site</html>');
  writeFileSync(join(dist, '.nojekyll'), '');
  writeFileSync(join(docs, 'obsolete.js'), 'old asset');
  return {dist, docs};
}

test('stages a complete site without requiring a paper', t => {
  const {dist, docs} = fixture(t);
  stagePages(dist, docs);
  assert.equal(readFileSync(join(docs, 'index.html'), 'utf8'), '<html>new site</html>');
  assert.ok(existsSync(join(docs, '.nojekyll')));
  assert.ok(!existsSync(join(docs, 'obsolete.js')));
  assert.ok(!existsSync(join(docs, 'paper/tcsexam.pdf')));
});

test('preserves a paper uploaded directly to the published directory', t => {
  const {dist, docs} = fixture(t);
  writeFileSync(join(docs, 'paper/tcsexam.pdf'), 'uploaded paper');
  stagePages(dist, docs);
  assert.equal(readFileSync(join(docs, 'paper/tcsexam.pdf'), 'utf8'), 'uploaded paper');
});

test('publishes a replacement paper from the source directory', t => {
  const {dist, docs} = fixture(t);
  writeFileSync(join(docs, 'paper/tcsexam.pdf'), 'old paper');
  writeFileSync(join(dist, 'paper/tcsexam.pdf'), 'replacement paper');
  stagePages(dist, docs);
  assert.equal(readFileSync(join(docs, 'paper/tcsexam.pdf'), 'utf8'), 'replacement paper');
});

test('keeps the published site when the build is missing', t => {
  const {dist, docs} = fixture(t);
  rmSync(join(dist, 'index.html'));
  assert.throws(() => stagePages(dist, docs));
  assert.equal(readFileSync(join(docs, 'obsolete.js'), 'utf8'), 'old asset');
});

test('homepage updates preserve the complete published documentation', t => {
  const {dist, docs} = fixture(t);
  mkdirSync(join(docs, 'docs', 'zh'), {recursive: true});
  writeFileSync(join(docs, 'docs', 'index.html'), 'English guide');
  writeFileSync(join(docs, 'docs', 'zh', 'index.html'), 'Chinese guide');
  stagePages(dist, docs);
  assert.equal(readFileSync(join(docs, 'docs', 'index.html'), 'utf8'), 'English guide');
  assert.equal(readFileSync(join(docs, 'docs', 'zh', 'index.html'), 'utf8'), 'Chinese guide');
});

test('a fresh bilingual docs build replaces old pages without changing homepage or paper', t => {
  const {dist, docs} = fixture(t);
  const incoming = join(dist, '..', 'incoming-docs');
  mkdirSync(join(incoming, 'zh'), {recursive: true});
  writeFileSync(join(incoming, 'index.html'), 'New English guide');
  writeFileSync(join(incoming, 'zh', 'index.html'), 'New Chinese guide');
  mkdirSync(join(docs, 'docs'), {recursive: true});
  writeFileSync(join(docs, 'docs', 'removed.html'), 'Old article');
  writeFileSync(join(docs, 'paper', 'tcsexam.pdf'), 'Uploaded PDF');
  stagePages(dist, docs, incoming);
  assert.equal(readFileSync(join(docs, 'index.html'), 'utf8'), '<html>new site</html>');
  assert.equal(readFileSync(join(docs, 'docs', 'index.html'), 'utf8'), 'New English guide');
  assert.equal(readFileSync(join(docs, 'docs', 'zh', 'index.html'), 'utf8'), 'New Chinese guide');
  assert.equal(readFileSync(join(docs, 'paper', 'tcsexam.pdf'), 'utf8'), 'Uploaded PDF');
  assert.ok(!existsSync(join(docs, 'docs', 'removed.html')));
});

test('an incomplete docs build leaves the published site untouched', t => {
  const {dist, docs} = fixture(t);
  const incoming = join(dist, '..', 'incomplete-docs');
  mkdirSync(incoming);
  writeFileSync(join(incoming, 'index.html'), 'Missing Chinese site');
  assert.throws(() => stagePages(dist, docs, incoming));
  assert.equal(readFileSync(join(docs, 'obsolete.js'), 'utf8'), 'old asset');
});
