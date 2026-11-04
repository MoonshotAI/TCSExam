import { defineConfig } from "vite";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import graph from './public/paper/research-graph.json' with { type: 'json' };
import benchmark from './public/data/benchmark.json' with { type: 'json' };
import { renderGraphCase } from './src/graph-case-markup.js';
import { renderQuantumCode } from './src/quantum-code-case.js';
import { renderPlate } from "./src/hero-plates.js";
import { linkArrow } from "./src/link-arrow.js";
import { repositoryConfig } from "./tools/repository-config.mjs";
import { publicDataFiles, publicData } from "./tools/public-data.mjs";

const repository = repositoryConfig();
const escapeHtml = value => value.replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
const renderTrackProtocol = id => {
  const track = benchmark.tracks.find(track => track.id === id);
  if (!track) throw new Error(`Unknown protocol track: ${id}`);
  return `<p class="protocol-track-label" aria-hidden="true">${escapeHtml(track.label)}</p>
    <dl class="protocol-fields">
      <div class="protocol-field"><dt>Submit</dt><dd>${escapeHtml(track.output)}</dd></div>
      <div class="protocol-field"><dt>Verify</dt><dd>${escapeHtml(track.verification)}</dd></div>
    </dl>
    <p class="protocol-count">5 Lite / ${track.full_count} Full tasks</p>`;
};

// build:pages supplies the project path and public URL for GitHub Pages.
const publicUrl = process.env.SITE_URL;
const socialCardUrl = publicUrl
  ? new URL("brand/social-card.png", `${publicUrl.replace(/\/$/, "")}/`).href
  : "./brand/social-card.png";
const dataVersions = Object.fromEntries(publicDataFiles.map(name => {
  const bytes = readFileSync(new URL(`./public/data/${name}`, import.meta.url));
  const content = name.endsWith('.json')
    ? JSON.stringify(publicData(name, JSON.parse(bytes)), null, 2) + '\n'
    : bytes;
  return [name, createHash("sha256").update(content).digest("hex").slice(0, 16)];
}));

export default defineConfig({
  base: process.env.SITE_BASE_PATH || "./",
  define: { __SITE_DATA_VERSIONS__: JSON.stringify(dataVersions), __SITE_REPOSITORY__: JSON.stringify(repository) },
  plugins: [{
    name: "site-html",
    transformIndexHtml(html) {
      return html
        .replaceAll('<!-- link-arrow -->', linkArrow)
        .replace(/<!-- track-protocol:(\w+) -->/g, (_, id) => renderTrackProtocol(id))
        .replace('<!-- outcome:graph -->', () => renderGraphCase(graph))
        .replace('<!-- outcome:quantum -->', () => renderQuantumCode())
        .replaceAll('%REPOSITORY_URL%', escapeHtml(repository.url))
        .replaceAll('%DOCUMENTATION_URL%', escapeHtml(repository.documentation))
        .replace(/%REPOSITORY_(CLONE|GUIDE|RUNNING|REQUIREMENTS|BACKEND)_URL%/g,
          (_, key) => escapeHtml(repository[{CLONE:'cloneUrl', GUIDE:'guide', RUNNING:'running', REQUIREMENTS:'requirements', BACKEND:'backend'}[key]]))
        .replace('content="./brand/social-card.png"', `content="${socialCardUrl}"`)
        .replace(/<!-- hero-art:(theorem|solver|construction|open) -->/g,
          (_, track) => renderPlate(track));
    },
  }],
  build: { target: "es2022", assetsInlineLimit: 0, rollupOptions: { input: { main: "index.html", task: "task.html" } } },
});
