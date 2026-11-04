import {existsSync, readFileSync, readdirSync, writeFileSync} from 'node:fs';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const lock = JSON.parse(readFileSync(join(root, 'package-lock.json'), 'utf8'));
const licenseName = /^(licen[cs]e|notice|copying)(?:$|[._-])/i;
const sections = [
  'Third-party dependency notices',
  '',
  'This document includes locally installed dependencies and build tools from',
  'the documentation package lock. Inclusion does not imply that every package',
  'is distributed in the browser bundle. License declarations below are package',
  'metadata; original license and notice files are reproduced where available.',
];
let packages = 0;
let files = 0;
let withoutFiles = 0;

// Read only license material, including packages that keep it in a LICENSES directory.
function noticeFiles(directory, prefix = '') {
  const result = [];
  for (const entry of readdirSync(directory, {withFileTypes: true}).sort((a, b) => a.name.localeCompare(b.name, 'en'))) {
    const relative = prefix ? `${prefix}/${entry.name}` : entry.name;
    if (entry.isFile() && (prefix || licenseName.test(entry.name))) result.push(relative);
    else if (entry.isDirectory() && /^(licen[cs]es?|notices?|copying)$/i.test(entry.name)) {
      result.push(...noticeFiles(join(directory, entry.name), relative));
    }
  }
  return result;
}

for (const [location, pinned] of Object.entries(lock.packages).sort(([a], [b]) => a.localeCompare(b, 'en'))) {
  if (!location.startsWith('node_modules/')) continue;
  const directory = join(root, location);
  const manifest = join(directory, 'package.json');
  // Platform-specific optional packages need not be installed on this host.
  if (!existsSync(manifest)) continue;
  const installed = JSON.parse(readFileSync(manifest, 'utf8'));
  if (installed.version !== pinned.version) {
    throw new Error(`Installed version differs from package-lock.json for ${installed.name}; run npm ci.`);
  }
  packages++;
  sections.push('', '='.repeat(72), `${installed.name}@${pinned.version}`);
  if (typeof installed.license === 'string') sections.push(`Declared license: ${installed.license}`);
  const notices = noticeFiles(directory);
  if (!notices.length) {
    withoutFiles++;
    sections.push('No LICENSE, NOTICE or COPYING file is included in this installed package.');
  }
  for (const name of notices) {
    files++;
    sections.push('', `--- ${name} ---`, readFileSync(join(directory, name), 'utf8').trimEnd());
  }
}
if (!packages) throw new Error('No installed dependencies found; run npm ci before building notices.');
writeFileSync(join(root, '.vitepress/dist/THIRD_PARTY_NOTICES.txt'), `${sections.join('\n')}\n`);
console.log(`Dependency notices: ${packages} packages, ${files} files; ${withoutFiles} packages have no bundled notice file.`);
