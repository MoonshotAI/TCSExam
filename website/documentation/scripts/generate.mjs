import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { fromMarkdown } from 'mdast-util-from-markdown';
import GithubSlugger from 'github-slugger';
import { createMarkdownRenderer } from 'vitepress';
import { getSettings, sourceUrl } from './settings.mjs';

export const siteRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

export function sourceDirectory(env = process.env) {
  if (!env.TCSEXAM_SOURCE_DIR) {
    throw new Error('Set TCSEXAM_SOURCE_DIR to a checkout of the benchmark master branch.');
  }
  return path.resolve(env.TCSEXAM_SOURCE_DIR);
}

export function routeFor(source) {
  if (/^(?:docs\/)?README(?:\.zh-CN)?\.md$/.test(source)) return 'overview';
  if (/^(?:\.github\/)?CONTRIBUTING(?:\.zh-CN)?\.md$/.test(source)) return 'contributing';
  let route = source.replace(/^docs\//, '').replace(/^assets\//, '');
  if (source.startsWith('assets/README')) return 'resources/assets';
  route = route.replace(/\.zh-CN(?=\.md$)/, '').replace(/\.md$/, '');
  return route.replace(/(?:^|\/)(?:README|index)$/, '').replace(/\/$/, '');
}

export function createPages(pairs) {
  return pairs.flatMap(pair => ['en', 'zh'].map(lang => {
    const route = routeFor(pair.en);
    const url = `/${lang === 'zh' ? 'zh/' : ''}${route ? `${route}/` : ''}`;
    return { source: pair[lang], lang, route, url, output: `${url.slice(1)}index.md` };
  }));
}

function visit(node, callback) {
  callback(node);
  for (const child of node.children || []) visit(child, callback);
}

export function stripLanguageBars(markdown) {
  const edits = [];
  visit(fromMarkdown(markdown), node => {
    if (node.type !== 'paragraph') return;
    const raw = markdown.slice(node.position.start.offset, node.position.end.offset);
    if (/^(?:(?:Language\s*:|语言\s*：)\s*)?\[English\]\([^\n]+\)\s*\|\s*\[简体中文\]\([^\n]+\)\s*$/.test(raw)) {
      edits.push({ start: node.position.start.offset, end: node.position.end.offset, value: '' });
    }
  });
  return applyEdits(markdown, edits);
}

// Repository guides can introduce their audience before the title. On the site,
// show the title first while retaining the introduction and explicit anchors.
export function titleFirst(markdown) {
  const nodes = fromMarkdown(markdown).children;
  const heading = nodes.find(node => node.type === 'heading' && node.depth === 1);
  if (!heading) return markdown;
  const leading = nodes.slice(0, nodes.indexOf(heading));
  if (leading.some(node => !['paragraph', 'html'].includes(node.type))) return markdown;
  const paragraphs = leading.filter(node => node.type === 'paragraph' && node.children.some(child => child.type !== 'html'));
  if (!paragraphs.length) return markdown;
  const introduction = paragraphs.map(node => markdown.slice(node.position.start.offset, node.position.end.offset)).join('\n\n');
  return applyEdits(markdown, [
    ...paragraphs.map(node => ({ start: node.position.start.offset, end: node.position.end.offset, value: '' })),
    { start: heading.position.end.offset, end: heading.position.end.offset, value: `\n\n${introduction}` },
  ]);
}

export function preserveGithubAnchors(markdown, existingIds) {
  const slugger = new GithubSlugger();
  const ids = new Set(existingIds);
  const edits = [];
  const text = node => node.type === 'html' ? '' : (node.value || (node.children || []).map(text).join(''));
  visit(fromMarkdown(markdown), node => {
    if (node.type !== 'heading') return;
    const id = slugger.slug(text(node));
    if (!ids.has(id)) {
      edits.push({ start: node.position.start.offset, end: node.position.start.offset, value: `<a id="${id}"></a>\n\n` });
      ids.add(id);
    }
  });
  return applyEdits(markdown, edits);
}

function applyEdits(markdown, edits) {
  for (const edit of edits.sort((a, b) => b.start - a.start)) {
    markdown = markdown.slice(0, edit.start) + edit.value + markdown.slice(edit.end);
  }
  return markdown;
}

export function makeLinkResolver({ pages, source, lang, settings, exists = () => true, isDirectory = () => false }) {
  const bySource = new Map(pages.map(page => [page.source, page]));
  return href => {
    if (href === 'https://moonshotai.github.io/TCSExam/paper/tcsexam.pdf') return `${settings.projectBase}paper/tcsexam.pdf`;
    if (!href || /^(?:[a-z][a-z\d+.-]*:|\/\/|#)/i.test(href)) return href;
    const match = href.match(/^([^?#]*)([?#].*)?$/);
    const target = path.posix.normalize(path.posix.join(path.posix.dirname(source), decodeURIComponent(match[1])));
    if (target.startsWith('../') || path.posix.isAbsolute(target)) throw new Error(`${source}: link escapes source tree: ${href}`);
    let page = bySource.get(target) || bySource.get(`${target.replace(/\/$/, '')}/README.md`);
    if (page) {
      // Every guide has both languages, including English source links written
      // before a translation existed. Keep readers in their current language.
      page = pages.find(candidate => candidate.route === page.route && candidate.lang === lang);
      return `${page.url}${match[2] || ''}`;
    }
    if (!exists(target)) throw new Error(`${source}: missing repository link target: ${href} (${target})`);
    return `${sourceUrl(target.replace(/\/$/, ''), settings, isDirectory(target))}${match[2] || ''}`;
  };
}

export function rewriteMarkdown(markdown, resolveLink) {
  const edits = [];
  visit(fromMarkdown(markdown), node => {
    const start = node.position?.start.offset;
    const end = node.position?.end.offset;
    if (['link', 'image', 'definition'].includes(node.type)) {
      const next = resolveLink(node.url);
      if (next === node.url) return;
      const raw = markdown.slice(start, end);
      let offset;
      if (node.type === 'definition') offset = raw.indexOf(':') + 1;
      else offset = raw.lastIndexOf('](') + 2;
      while (/\s/.test(raw[offset])) offset++;
      const angle = raw[offset] === '<';
      if (angle) offset++;
      let stop = offset;
      let depth = 0;
      for (; stop < raw.length; stop++) {
        const character = raw[stop];
        if (character === '\\') { stop++; continue; }
        if (angle ? character === '>' : /\s/.test(character) || (character === ')' && depth === 0)) break;
        if (character === '(') depth++;
        if (character === ')') depth--;
      }
      edits.push({ start: start + offset, end: start + stop, value: next });
    } else if (node.type === 'html') {
      const raw = markdown.slice(start, end);
      for (const match of raw.matchAll(/\b(?:href|src)\s*=\s*(["'])(.*?)\1/gi)) {
        const offset = match.index + match[0].indexOf(match[2]);
        edits.push({ start: start + offset, end: start + offset + match[2].length, value: resolveLink(match[2]) });
      }
    }
  });
  return applyEdits(markdown, edits);
}

export function inspectHtml(html) {
  const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]);
  const headings = [...html.matchAll(/<h[1-6]\b[^>]*\bid="([^"]+)"/g)].map(match => match[1]);
  const links = [...html.matchAll(/\bhref="([^"]+)"/g)].map(match => match[1].replaceAll('&amp;', '&'));
  return { ids, headings, links };
}

export function checkLinks(pages, settings) {
  const pagesByUrl = new Map(pages.map(page => [`${settings.docsBase.replace(/\/$/, '')}${page.url}`, page]));
  const errors = [];
  for (const page of pages) {
    const selfUrl = `${settings.docsBase.replace(/\/$/, '')}${page.url}`;
    for (const href of page.links) {
      if (!href.startsWith(settings.docsBase) && !href.startsWith('#')) continue;
      const parsed = new URL(href, `https://docs.invalid${selfUrl}`);
      const fragment = parsed.hash.slice(1);
      const target = pagesByUrl.get(parsed.pathname);
      if (!target) errors.push(`${page.source}: missing site route ${href}`);
      else if (fragment && !target.ids.includes(decodeURIComponent(fragment))) errors.push(`${page.source}: missing section ${href}`);
    }
  }
  if (errors.length) throw new Error(errors.join('\n'));
}

export async function generate() {
  const repositoryRoot = sourceDirectory();
  const settings = getSettings();
  const pairs = JSON.parse(await fs.readFile(path.join(siteRoot, 'sources.json'), 'utf8'));
  const pages = createPages(pairs);
  const renderer = await createMarkdownRenderer(repositoryRoot, { html: true }, settings.docsBase);
  const existing = new Map();
  // Only stat linked paths. No task answers or other source files are read.
  const sourceTexts = await Promise.all(pages.map(page => fs.readFile(path.join(repositoryRoot, page.source), 'utf8')));
  for (let index = 0; index < pages.length; index++) {
    const page = pages[index];
    const stripped = titleFirst(stripLanguageBars(sourceTexts[index]));
    const content = preserveGithubAnchors(stripped, inspectHtml(renderer.render(stripped)).ids);
    const targets = [];
    visit(fromMarkdown(content), node => {
      const links = node.url ? [node.url] : node.type === 'html'
        ? [...node.value.matchAll(/\b(?:href|src)\s*=\s*(["'])(.*?)\1/gi)].map(match => match[2]) : [];
      for (const href of links) {
        if (!/^(?:[a-z][a-z\d+.-]*:|\/\/|#)/i.test(href)) targets.push(href.split(/[?#]/)[0]);
      }
    });
    for (const target of targets) {
      const file = path.posix.normalize(path.posix.join(path.posix.dirname(page.source), decodeURIComponent(target)));
      if (!existing.has(file)) {
        try { existing.set(file, await fs.stat(path.join(repositoryRoot, file))); }
        catch { existing.set(file, null); }
      }
    }
    page.content = rewriteMarkdown(content, makeLinkResolver({
      pages, source: page.source, lang: page.lang, settings,
      exists: target => Boolean(existing.get(target)), isDirectory: target => existing.get(target)?.isDirectory(),
    }));
    Object.assign(page, inspectHtml(renderer.render(page.content)));
  }
  checkLinks(pages, settings);
  const output = path.join(siteRoot, '.generated');
  await fs.rm(output, { recursive: true, force: true });
  await fs.mkdir(output, { recursive: true });
  await fs.mkdir(path.join(output, 'public', 'brand'), { recursive: true });
  for (const name of ['tcsexam-wordmark.svg', 'favicon.svg']) {
    await fs.copyFile(path.join(siteRoot, '..', 'public', 'brand', name),
      path.join(output, 'public', 'brand', name));
  }
  for (const page of pages) {
    const alternate = pages.find(candidate => candidate.route === page.route && candidate.lang !== page.lang);
    const anchorMap = Object.fromEntries(page.headings.map((heading, index) => [heading, alternate.headings[index]]).filter(([, value]) => value));
    for (const id of page.ids) if (alternate.ids.includes(id)) anchorMap[id] = id;
    const frontmatter = {
      sourcePath: page.source,
      sourceUrl: sourceUrl(page.source, settings),
      alternateUrl: `${settings.docsBase.replace(/\/$/, '')}${alternate.url}`,
      alternateAnchors: anchorMap,
    };
    const dest = path.join(output, page.output);
    await fs.mkdir(path.dirname(dest), { recursive: true });
    await fs.writeFile(dest, `---\n${Object.entries(frontmatter).map(([key, value]) => `${key}: ${JSON.stringify(value)}`).join('\n')}\n---\n\n${page.content}`);
  }
  await fs.writeFile(path.join(output, 'routes.json'), JSON.stringify(pages.map(({ content, links, ...page }) => page), null, 2));
  console.log(`Generated ${pages.length} documentation pages; checked all local routes, sections and repository targets.`);
  return pages;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) await generate();
