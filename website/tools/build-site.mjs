import {copyFileSync, existsSync, mkdirSync, readFileSync} from 'node:fs';
import {join, resolve} from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {execFileSync, spawnSync} from 'node:child_process';

export function benchmarkInputs(env = process.env) {
  if (!env.TCSEXAM_SOURCE_DIR) {
    throw new Error('Set TCSEXAM_SOURCE_DIR to a checkout of the benchmark master branch.');
  }
  const source = resolve(env.TCSEXAM_SOURCE_DIR);
  for (const name of ['README.md', 'docs/index.md', 'docs/index.zh-CN.md', 'suites/tasks.json', 'paper.pdf']) {
    if (!existsSync(join(source, name))) throw new Error(`Benchmark source is missing ${name}: ${source}`);
  }
  const paper = join(source, 'paper.pdf');
  if (readFileSync(paper).subarray(0, 5).toString() !== '%PDF-') {
    throw new Error('The benchmark paper.pdf must be a PDF file.');
  }
  let ref = env.SITE_REPOSITORY_REF;
  if (!ref) {
    try { ref = execFileSync('git', ['-C', source, 'rev-parse', 'HEAD'], {encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore']}).trim(); }
    catch { throw new Error('For an exported source directory, set SITE_REPOSITORY_REF to its source commit.'); }
  }
  return {source, paper, ref};
}

export function buildSite(env = process.env) {
  const root = fileURLToPath(new URL('../', import.meta.url));
  const inputs = benchmarkInputs(env);
  const buildEnv = {
    ...env,
    TCSEXAM_SOURCE_DIR: inputs.source,
    SITE_REPOSITORY_REF: inputs.ref,
    SITE_BASE_PATH: env.SITE_BASE_PATH || '/TCSExam/',
    SITE_URL: env.SITE_URL || 'https://moonshotai.github.io/TCSExam/',
    SITE_DOCS_DIR: join(root, 'documentation', '.vitepress', 'dist'),
  };
  const run = args => {
    const result = spawnSync('npm', args, {cwd: root, env: buildEnv, stdio: 'inherit'});
    if (result.error) throw result.error;
    if (result.status !== 0) throw new Error(`npm ${args.join(' ')} failed (${result.status ?? result.signal})`);
  };
  run(['--prefix', 'documentation', 'run', 'build']);
  mkdirSync(join(root, 'public', 'paper'), {recursive: true});
  copyFileSync(inputs.paper, join(root, 'public', 'paper', 'tcsexam.pdf'));
  run(['run', 'build:pages']);
  console.log(`Complete website built from benchmark ${inputs.ref}; paper copied from the same source.`);
}

if (process.argv[1] && pathToFileURL(resolve(process.argv[1])).href === import.meta.url) buildSite();
