import {readFileSync,writeFileSync} from 'node:fs';
const root=new URL('../public/data/',import.meta.url);
const data=JSON.parse(readFileSync(new URL('lite-results.json',root)));
const {validateIndex} = await import('./check-lite-index.mjs');
const {indexResultsCsv} = await import('../src/lite-index.js');
const index = JSON.parse(readFileSync(new URL('lite-index.json',root)));
validateIndex(index,data);
writeFileSync(new URL('lite-index.csv',root),indexResultsCsv(index));
console.log(`Exported the ${index.models.length}-model Lite Index and track contributions.`);
