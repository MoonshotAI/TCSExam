import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {repositoryConfig,withRepositoryLinks} from '../tools/repository-config.mjs';
import {generateCommands} from '../src/get-started.js';
import viteConfig from '../vite.config.js';

test('public source links and clone commands follow the default branch or configured ref', () => {
  const current = repositoryConfig({});
  assert.equal(current.cloneUrl,'https://github.com/MoonshotAI/TCSExam.git');
  assert.equal(current.guide,'/docs/getting-started/');
  assert.doesNotMatch(generateCommands({},current).install,/--branch/);
  const github = repositoryConfig({SITE_REPOSITORY_URL:'https://github.com/example/TCSExam.git',SITE_REPOSITORY_REF:'main'});
  assert.equal(github.guide,'/docs/getting-started/');
  assert.equal(github.tasks,'https://github.com/example/TCSExam/tree/main/tasks');
  assert.match(generateCommands({},github).install,/--branch 'main'/);
  const commit = '6056121dd56574c1d531e29c3366a4e71863668d';
  const pinned = generateCommands({}, repositoryConfig({SITE_REPOSITORY_REF: commit})).install;
  assert.doesNotMatch(pinned, /git clone --branch/);
  assert.ok(pinned.includes(`cd TCSExam\ngit checkout --detach '${commit}'`));
  const data = {models:[{score:51.1}],links:{paper:null,repository:current.url}};
  const published = withRepositoryLinks(data,github);
  assert.equal(published.links.repository,github.url);
  assert.equal(published.links.documentation,github.documentation);
  assert.equal(published.links.paper,null);
  assert.deepEqual(published.models,data.models);
  assert.equal(data.links.repository,current.url);
});

test('documentation resolves to the same site from home and nested task pages at every deployment base', () => {
  const cases = [
    [{}, 'https://preview.example/', '/docs/'],
    [{SITE_BASE_PATH:'./'}, 'https://preview.example/', '/docs/'],
    [{SITE_BASE_PATH:'/'}, 'https://preview.example/', '/docs/'],
    [{SITE_BASE_PATH:'/TCSExam/'}, 'https://moonshotai.github.io/TCSExam/', '/TCSExam/docs/'],
    [{SITE_BASE_PATH:'research/bench'}, 'https://example.org/research/bench/', '/research/bench/docs/'],
    [{SITE_URL:'https://bench.example/research/'}, 'https://bench.example/research/', '/research/docs/'],
    [{SITE_URL:'https://bench.example/',SITE_BASE_PATH:'/TCSExam/'}, 'https://bench.example/TCSExam/', '/TCSExam/docs/'],
  ];
  const routes = {documentation:'', guide:'getting-started/', running:'running/', requirements:'runtime-availability/', backend:'backend/docker/', scoring:'scoring/', citation:'citation/'};
  for (const [env, siteRoot, docsPath] of cases) {
    const links = repositoryConfig(env);
    for (const page of [siteRoot, new URL('tasks/example/',siteRoot).href]) {
      for (const [key, route] of Object.entries(routes)) {
        const target = new URL(links[key], page);
        assert.equal(target.origin, new URL(siteRoot).origin, `${key} origin from ${page}`);
        assert.equal(target.pathname, `${docsPath}${route}`, `${key} path from ${page}`);
        assert.equal(target.search,'');
        assert.equal(target.hash,'');
      }
    }
    for (const [key, route] of Object.entries(routes)) {
      const preview = new URL(links[key], 'https://preview.example/TCSExam/tasks/example/');
      assert.equal(preview.origin, 'https://preview.example');
      assert.equal(preview.pathname, `${docsPath}${route}`);
    }
    assert.match(links.tasks,/^https:\/\/github\.com\/MoonshotAI\/TCSExam\/tree\/HEAD\/tasks$/);
  }
});

test('homepage publishes documentation links in navigation and hero while preserving existing entry points', () => {
  const source = readFileSync(new URL('../index.html',import.meta.url),'utf8');
  const html = viteConfig.plugins.find(plugin => plugin.name === 'site-html').transformIndexHtml(source);
  const nav = html.match(/<nav aria-label="Main navigation">([\s\S]*?)<\/nav>/)[1];
  const hero = html.match(/<div class="hero-actions">([\s\S]*?)<\/div>/)[1];
  for (const [content, label] of [[nav, 'Documentation'], [hero, 'Docs']]) {
    const link = [...content.matchAll(/<a[^>]*href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/g)]
      .find(match => match[2].replace(/<[^>]*>/g,'').trim() === label);
    assert.ok(link,'Documentation link exists');
    const href = link[1];
    assert.equal(new URL(href,'https://preview.example/').pathname,
      new URL(repositoryConfig().documentation,'https://preview.example/').pathname);
  }
  for (const fragment of ['#overview','#lite','#full','#outcomes','#problems','#start']) assert.ok(nav.includes(`href="${fragment}"`));
  assert.ok(hero.includes('href="https://arxiv.org/abs/2611.07962"'));
  assert.ok(html.includes('>Source code '));
  assert.doesNotMatch(html,/%(?:DOCUMENTATION|REPOSITORY)[A-Z_]*%/);
});

test('task protocols are present and expandable in the initial static HTML', () => {
  const source = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
  const html = viteConfig.plugins.find(plugin => plugin.name === 'site-html').transformIndexHtml(source);
  const details = html.match(/<details[^>]*id="submission-rules"[^>]*>([\s\S]*?)<\/details>/);
  assert.ok(details);
  assert.doesNotMatch(details[0].slice(0, details[0].indexOf('>')), /\bhidden\b/);
  assert.match(details[1], /<summary[^>]*>[\s\S]*?Task protocols<\/summary>/);
  assert.equal((details[1].match(/<dt>Submit<\/dt>/g) || []).length, 4);
  assert.equal((details[1].match(/<dt>Verify<\/dt>/g) || []).length, 4);
  assert.equal((details[1].match(/5 Lite \/ (20|30) Full tasks/g) || []).length, 4);
  assert.doesNotMatch(details[1], /<!-- track-protocol:/);
});

test('repository configuration rejects credential-bearing or ambiguous URLs', () => {
  for (const url of ['https://user:secret@github.com/example/TCSExam','https://github.com/example/TCSExam?token=secret','https://github.com/example/TCSExam#main','file:///tmp/repository']) {
    assert.throws(() => repositoryConfig({SITE_REPOSITORY_URL:url}));
  }
  for (const url of ['https://user:secret@bench.example/','https://bench.example/?token=secret','https://bench.example/#docs','file:///tmp/site']) {
    assert.throws(() => repositoryConfig({SITE_URL:url}));
  }
  for (const base of ['/../site/','/site?query/','/site#fragment/']) {
    assert.throws(() => repositoryConfig({SITE_BASE_PATH:base}));
  }
});
