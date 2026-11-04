import {readdirSync, readFileSync, writeFileSync, rmSync} from 'node:fs';
import {publicDataFiles, publicData} from './public-data.mjs';

const root = new URL('../dist/', import.meta.url);
for (const name of readdirSync(new URL('data/', root))) {
  const path = new URL(`data/${name}`, root);
  if (!publicDataFiles.includes(name)) rmSync(path, {recursive: true});
  else if (name.endsWith('.json')) writeFileSync(path, JSON.stringify(publicData(name, JSON.parse(readFileSync(path))), null, 2) + '\n');
}
for (const name of ['research-graph.json', 'quantum-code.json', 'binary-code.json']) {
  const path = new URL(`paper/${name}`, root);
  writeFileSync(path, JSON.stringify(publicData(name, JSON.parse(readFileSync(path))), null, 2) + '\n');
}
for (const name of ['paper/case-study-sources.json', 'paper/figure-1.pdf', 'paper/figure-1.png']) {
  rmSync(new URL(name, root), {force: true});
}
console.log('Public release: two leaderboard CSVs and page data prepared.');
