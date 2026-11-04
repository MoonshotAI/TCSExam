import {cpSync, existsSync, mkdirSync, mkdtempSync, renameSync, rmSync, statSync} from 'node:fs';
import {dirname, join, resolve} from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {spawnSync} from 'node:child_process';

export function stagePages(dist, docs, documentationDir) {
  // Check the completed build before replacing the published directory.
  if (!statSync(join(dist, 'index.html')).isFile()) {
    throw new Error('The website build must contain index.html.');
  }
  if (documentationDir) {
    for (const file of ['index.html', 'zh/index.html']) {
      if (!statSync(join(documentationDir, file)).isFile()) {
        throw new Error(`The documentation build must contain ${file}.`);
      }
    }
  }
  mkdirSync(dirname(docs), {recursive: true});
  const staging = mkdtempSync(join(dirname(docs), '.pages-stage-'));
  const backup = join(staging, 'previous');
  const candidate = join(staging, 'site');
  try {
    cpSync(dist, candidate, {recursive: true});
    const paper = join('paper', 'tcsexam.pdf');
    // A PDF uploaded directly through GitHub remains available after a rebuild.
    // The paper copied from master by build:site takes precedence.
    if (!existsSync(join(candidate, paper)) && existsSync(join(docs, paper))) {
      mkdirSync(dirname(join(candidate, paper)), {recursive: true});
      cpSync(join(docs, paper), join(candidate, paper));
    }
    // A homepage-only rebuild retains the previously published documentation.
    // An explicit documentation build replaces it, including removed pages.
    const previousDocs = join(docs, 'docs');
    if (documentationDir) {
      rmSync(join(candidate, 'docs'), {recursive: true, force: true});
      cpSync(documentationDir, join(candidate, 'docs'), {recursive: true});
    } else if (!existsSync(join(candidate, 'docs')) && existsSync(previousDocs)) {
      cpSync(previousDocs, join(candidate, 'docs'), {recursive: true});
    }
    if (existsSync(docs)) renameSync(docs, backup);
    try {
      renameSync(candidate, docs);
    } catch (error) {
      if (existsSync(backup)) renameSync(backup, docs);
      throw error;
    }
  } finally {
    rmSync(staging, {recursive: true, force: true});
  }
}

if (process.argv[1] && pathToFileURL(resolve(process.argv[1])).href === import.meta.url) {
  const root = fileURLToPath(new URL('../', import.meta.url));
  const result = spawnSync('npm', ['run', 'build'], {
    cwd: root,
    stdio: 'inherit',
    env: {
      ...process.env,
      SITE_BASE_PATH: process.env.SITE_BASE_PATH || '/TCSExam/',
      SITE_URL: process.env.SITE_URL || 'https://moonshotai.github.io/TCSExam/',
    },
  });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status || 1);
  stagePages(join(root, 'dist'), join(root, '..', 'docs'),
    process.env.SITE_DOCS_DIR ? resolve(process.env.SITE_DOCS_DIR) : undefined);
  console.log('GitHub Pages files prepared in ../docs/.');
}
