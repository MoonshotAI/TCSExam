import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { getSettings } from './settings.mjs';
import MiniSearch from 'minisearch';
import { searchOptions } from './search.mjs';

async function walk(dir) {
  const files = [];
  for (const entry of await fs.readdir(dir, { withFileTypes: true })) {
    if (entry.isDirectory()) files.push(...await walk(path.join(dir, entry.name)));
    else if (entry.name.endsWith('.html')) files.push(path.join(dir, entry.name));
  }
  return files;
}

export async function checkBuilt(root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../.vitepress/dist'), settings = getSettings()) {
  const pages = new Map();
  for (const file of await walk(root)) {
    const html = await fs.readFile(file, 'utf8');
    pages.set(file, { html, ids: new Set([...html.matchAll(/\bid="([^"]*)"/g)].map(match => match[1])) });
  }
  const errors = [];
  let checked = 0;
  for (const [file, page] of pages) {
    const relative = path.relative(root, file).split(path.sep).join('/');
    const url = new URL(settings.docsBase + relative.replace(/index\.html$/, ''), 'https://docs.invalid');
    for (const match of page.html.matchAll(/<a\b[^>]*\bhref="([^"]*)"/g)) {
      const href = match[1].replaceAll('&amp;', '&');
      if (/^(?:[a-z][a-z\d+.-]*:|\/\/)/i.test(href)) continue;
      const target = new URL(href, url);
      if (!target.pathname.startsWith(settings.docsBase)) {
        if (![settings.projectBase, `${settings.projectBase}paper/tcsexam.pdf`].includes(target.pathname)) errors.push(`${relative}: unexpected off-site path ${href}`);
        continue;
      }
      const destination = target.pathname.slice(settings.docsBase.length);
      const targetFile = path.join(root, decodeURIComponent((!destination || destination.endsWith('/')) ? `${destination}index.html` : destination));
      const targetPage = pages.get(targetFile);
      if (!targetPage) errors.push(`${relative}: missing built route ${href}`);
      else if (target.hash && !targetPage.ids.has(decodeURIComponent(target.hash.slice(1)))) errors.push(`${relative}: missing built section ${href}`);
      checked++;
    }
  }
  if (errors.length) throw new Error(errors.join('\n'));
  const chunks = path.join(root, 'assets/chunks');
  for (const [locale, queries] of [['root', ['Docker', 'scoring']], ['zh', ['主机要求', '判分隔离', '计分']]]) {
    const filename = (await fs.readdir(chunks)).find(name => name.startsWith(`@localSearchIndex${locale}.`));
    if (!filename) throw new Error(`Missing ${locale} search index`);
    const { default: serialized } = await import(new URL(`file://${path.join(chunks, filename)}`));
    const index = MiniSearch.loadJSON(serialized, { fields: ['title', 'titles', 'text'], storeFields: ['title', 'titles'], ...searchOptions.miniSearch.options });
    for (const query of queries) {
      const results = index.search(query, searchOptions.miniSearch.searchOptions);
      if (!results.length) throw new Error(`${locale} search index has no results for ${query}`);
      const localePrefix = settings.docsBase + (locale === 'zh' ? 'zh/' : '');
      if (results.some(result => !result.id.startsWith(localePrefix))) throw new Error(`Search results escape ${locale} locale`);
    }
  }
  console.log(`Checked ${checked} rendered internal links across ${pages.size} built HTML pages; verified both built search indexes.`);
  return { pages: pages.size, checked };
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) await checkBuilt();
