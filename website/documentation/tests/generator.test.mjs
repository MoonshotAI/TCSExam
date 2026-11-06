import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { createMarkdownRenderer } from 'vitepress';
import MiniSearch from 'minisearch';
import { createPages, routeFor, rewriteMarkdown, makeLinkResolver, stripLanguageBars, titleFirst, preserveGithubAnchors, inspectHtml, checkLinks, sourceDirectory } from '../scripts/generate.mjs';
import { getSettings, sourceUrl } from '../scripts/settings.mjs';
import { searchOptions, tokenizeSearch } from '../scripts/search.mjs';
import { sidebar } from '../scripts/navigation.mjs';

const settings = getSettings({ SITE_BASE_PATH: '/research/', SITE_REPOSITORY_REF: 'abc123' });

test('documentation requires an explicit benchmark source checkout', () => {
  assert.throws(() => sourceDirectory({}), /TCSEXAM_SOURCE_DIR/);
  assert.equal(sourceDirectory({ TCSEXAM_SOURCE_DIR: '/tmp/benchmark-source' }), '/tmp/benchmark-source');
});
const pairs = [
  { en: 'README.md', zh: 'README.zh-CN.md' },
  { en: 'docs/index.md', zh: 'docs/index.zh-CN.md' },
  { en: 'docs/running.md', zh: 'docs/running.zh-CN.md' },
  { en: 'docs/backend/docker.md', zh: 'docs/backend/docker.zh-CN.md' },
];
const pages = createPages(pairs);
const resolve = (source = 'docs/index.zh-CN.md', lang = 'zh') => makeLinkResolver({ pages, source, lang, settings, exists: target => ['src/example.py', 'tasks', 'assets/config.json'].includes(target.replace(/\/$/, '')), isDirectory: target => target.replace(/\/$/, '') === 'tasks' });

test('base paths and source revisions are explicit and configurable', () => {
  assert.equal(settings.docsBase, '/research/docs/');
  assert.equal(getSettings({ SITE_BASE_PATH: '/' }).docsBase, '/docs/');
  assert.equal(getSettings({}).repositoryRef, 'master');
  assert.equal(sourceUrl('docs/a b.md', settings), 'https://github.com/MoonshotAI/TCSExam/blob/abc123/docs/a%20b.md');
  assert.throws(() => getSettings({ SITE_BASE_PATH: 'relative' }));
});

test('the bilingual pairs have unique directory routes and matching languages', async () => {
  const manifest = JSON.parse(await fs.readFile(new URL('../sources.json', import.meta.url), 'utf8'));
  const routes = createPages(manifest);
  assert.equal(manifest.length, 34);
  assert.equal(new Set(routes.map(page => page.output)).size, 68);
  for (const page of routes) assert.ok(routes.some(other => other.lang !== page.lang && other.route === page.route));
  assert.equal(routeFor('docs/licenses/README.md'), 'licenses');
  assert.equal(routeFor('assets/environments/lean-base/README.md'), 'environments/lean-base');
  assert.equal(routeFor('README.md'), 'overview');
  assert.ok(routes.some(page => page.output === 'zh/backend/docker/index.md'));
  const sidebarRoutes = new Set();
  const walk = items => items.forEach(item => { if (item.link) sidebarRoutes.add(item.link); if (item.items) walk(item.items); });
  walk(sidebar('en'));
  assert.deepEqual([...sidebarRoutes].sort(), routes.filter(page => page.lang === 'en').map(page => page.url).sort());
});

test('Markdown links use the current language and retain fragments, queries and titles', () => {
  const output = rewriteMarkdown('[配置](running.md#choose-an-agent) [后端](backend/docker.md?mode=all#host-requirements "Details") [概览](../README.md)', resolve());
  assert.equal(output, '[配置](/zh/running/#choose-an-agent) [后端](/zh/backend/docker/?mode=all#host-requirements "Details") [概览](/zh/overview/)');
});

test('source links go to the configured revision, and missing files fail', () => {
  assert.equal(resolve()('../src/example.py#L12'), 'https://github.com/MoonshotAI/TCSExam/blob/abc123/src/example.py#L12');
  assert.equal(resolve()('../tasks/'), 'https://github.com/MoonshotAI/TCSExam/tree/abc123/tasks');
  assert.throws(() => resolve()('missing.md'), /missing repository link/);
});

test('README badge images use site assets while their clickable destinations remain intact', () => {
  const known = target => target === 'assets/badges/arxiv.svg';
  for (const [source, lang, prefix] of [['README.md', 'en', ''], ['docs/README.zh-CN.md', 'zh', '../']]) {
    const resolver = makeLinkResolver({pages, source, lang, settings, exists: known});
    const markdown = `[![arXiv](${prefix}assets/badges/arxiv.svg)](https://arxiv.org/abs/2611.07962)`;
    assert.equal(rewriteMarkdown(markdown, resolver),
      '[![arXiv](/badges/arxiv.svg)](https://arxiv.org/abs/2611.07962)');
    assert.throws(() => resolver(`${prefix}assets/badges/missing.svg`), /missing repository link/);
  }
});

test('site introductions follow the title while anchors and commands are preserved', () => {
  const source = 'An introduction.\nFor new users.\n\n<a id="old-title"></a>\n\n# Quickstart\n\n```sh\necho "unchanged"\n```\n';
  const output = titleFirst(source);
  assert.ok(output.indexOf('# Quickstart') < output.indexOf('An introduction.'));
  assert.ok(output.indexOf('id="old-title"') < output.indexOf('# Quickstart'));
  assert.ok(output.includes('```sh\necho "unchanged"\n```'));
  assert.equal(titleFirst('# Title\n\nAlready below.'), '# Title\n\nAlready below.');
});

test('paper links follow the configured project path on preview and public hosts', () => {
  const resolver = makeLinkResolver({pages:createPages(pairs),source:'docs/index.md',lang:'en',settings});
  assert.equal(resolver('https://moonshotai.github.io/TCSExam/paper/tcsexam.pdf'), '/research/paper/tcsexam.pdf');
});

test('fenced and inline code remain byte-for-byte intact; real reference and HTML links change', () => {
  const code = '```md\n[code](running.md)\n[English](README.md) | [简体中文](README.zh-CN.md)\n```\n\n`[inline](running.md)`';
  const source = code + '\n\n[real][config]\n\n[config]: running.md#settings-and-budgets "Settings"\n\n<a href="backend/docker.md#host-requirements">Docker</a>';
  const result = rewriteMarkdown(stripLanguageBars(source), resolve());
  assert.ok(result.startsWith(code));
  assert.ok(result.includes('[config]: /zh/running/#settings-and-budgets "Settings"'));
  assert.ok(result.includes('href="/zh/backend/docker/#host-requirements"'));
  for (const prefix of ['', 'Language: ', '语言：']) {
    assert.equal(stripLanguageBars(prefix + '[English](README.md) | [简体中文](README.zh-CN.md)\n\nBody'), '\n\nBody');
  }
});

test('GitHub numeric section links and custom translated anchors remain valid', async () => {
  const md = await createMarkdownRenderer(process.cwd(), {}, settings.docsBase);
  const original = '# Guide\n\n## 3. Configure the model\n\n<a id="shared-section"></a>\n\n## 中文章节\n';
  const content = preserveGithubAnchors(original, inspectHtml(md.render(original)).ids);
  const result = inspectHtml(md.render(content));
  assert.ok(result.ids.includes('3-configure-the-model'));
  assert.ok(result.ids.includes('_3-configure-the-model'));
  assert.ok(result.ids.includes('shared-section'));
  assert.equal(result.ids.filter(id => id === 'shared-section').length, 1);
  const ownPage = { source: 'guide.md', url: '/', ids: result.ids, links: [settings.docsBase + '#3-configure-the-model'] };
  assert.doesNotThrow(() => checkLinks([ownPage], settings));
  assert.doesNotThrow(() => checkLinks([{ ...ownPage, links: [settings.docsBase + '?mode=all#3-configure-the-model'] }], settings));
  assert.throws(() => checkLinks([{ ...ownPage, links: [settings.docsBase + '#missing'] }], settings), /missing section/);
  assert.throws(() => checkLinks([{ ...ownPage, links: [settings.docsBase + 'missing/'] }], settings), /missing site route/);
});

test('Chinese local search finds phrases inside unspaced sentences and keeps Latin identifiers', () => {
  const index = new MiniSearch({ fields: ['title', 'titles', 'text'], storeFields: ['title'], ...searchOptions.miniSearch.options });
  index.addAll([
    { id: 'run', title: '运行配置', titles: '选择 agent', text: '运行之前请检查判分隔离和主机要求；使用 TCSEXAM_CACHE 保存资源。' },
    { id: 'score', title: '计分说明', titles: '结果', text: '汇总评测分数。' },
  ]);
  for (const query of ['判分隔离', '主机要求', '运行配置', 'TCSEXAM_CACHE']) {
    assert.equal(index.search(query, searchOptions.miniSearch.searchOptions)[0]?.id, 'run', query);
  }
  assert.equal(index.search('计分', searchOptions.miniSearch.searchOptions)[0]?.id, 'score');
  const clientTokenizer = new Function(`return (${tokenizeSearch.toString()})`)();
  assert.deepEqual(clientTokenizer('判分隔离 TCSEXAM_CACHE'), tokenizeSearch('判分隔离 TCSEXAM_CACHE'));
  const loaded = MiniSearch.loadJSON(JSON.stringify(index), { fields: ['title', 'titles', 'text'], ...searchOptions.miniSearch.options });
  assert.equal(loaded.search('判分隔离', searchOptions.miniSearch.searchOptions)[0]?.id, 'run');
});
