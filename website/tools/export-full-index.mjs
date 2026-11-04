import {readFileSync,writeFileSync} from 'node:fs';
import {validateFullIndex} from './check-full-index.mjs';
import {indexResultsCsv} from '../src/lite-index.js';
const root=new URL('../public/data/',import.meta.url);
const index=JSON.parse(readFileSync(new URL('full-index.json',root)));
validateFullIndex(index,JSON.parse(readFileSync(new URL('full-results.json',root))));
writeFileSync(new URL('full-index.csv',root),indexResultsCsv(index));
console.log(`Exported the ${index.models.length}-model Full Index, track contributions and Solver protocol.`);
