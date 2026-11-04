import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdirSync, mkdtempSync, rmSync, writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {benchmarkInputs} from '../tools/build-site.mjs';

function source(t) {
  const root = mkdtempSync(join(tmpdir(), 'tcsexam-source-'));
  t.after(() => rmSync(root, {recursive: true, force: true}));
  mkdirSync(join(root, 'docs'));
  mkdirSync(join(root, 'suites'));
  for (const file of ['README.md', 'docs/index.md', 'docs/index.zh-CN.md', 'suites/tasks.json']) {
    writeFileSync(join(root, file), 'fixture');
  }
  writeFileSync(join(root, 'paper.pdf'), '%PDF-1.7\nfixture');
  return root;
}

test('a complete site uses documentation and paper from the selected benchmark source', t => {
  const root = source(t);
  assert.deepEqual(benchmarkInputs({TCSEXAM_SOURCE_DIR: root, SITE_REPOSITORY_REF: 'fixed-commit'}),
    {source: root, paper: join(root, 'paper.pdf'), ref: 'fixed-commit'});
});

test('missing source, missing paper and a non-PDF input fail before any build', t => {
  assert.throws(() => benchmarkInputs({}), /TCSEXAM_SOURCE_DIR/);
  const root = source(t);
  const env = {TCSEXAM_SOURCE_DIR: root, SITE_REPOSITORY_REF: 'fixed-commit'};
  rmSync(join(root, 'paper.pdf'));
  assert.throws(() => benchmarkInputs(env), /missing paper.pdf/);
  writeFileSync(join(root, 'paper.pdf'), 'an error page');
  assert.throws(() => benchmarkInputs(env), /must be a PDF/);
});

test('an exported source needs an explicit revision for its source links', t => {
  assert.throws(() => benchmarkInputs({TCSEXAM_SOURCE_DIR: source(t)}), /SITE_REPOSITORY_REF/);
});
