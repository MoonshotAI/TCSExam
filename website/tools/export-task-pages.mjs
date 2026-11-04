import {readFileSync,writeFileSync,mkdirSync,rmSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {resolve,dirname} from 'node:path';
import assert from 'node:assert/strict';
import {Marked} from 'marked';
import katex from 'katex';
import {enrichTask,editorialIds} from '../src/catalogue/editorial.js';
import {orderTasksForBrowsing} from '../src/catalogue/browse-order.js';
import {explanationIds} from '../src/catalogue/explanations.js';
import {renderIllustration} from '../src/catalogue/illustrations.js';
import {taskSource} from '../src/catalogue/sources.js';
import {publishedExamples} from '../src/labs/catalogue.js';
import {renderTaskResults} from '../src/catalogue/task-results.js';
import {renderLiteTaskResults} from '../src/lite-results.js';
import {repositoryConfig,withRepositoryLinks} from './repository-config.mjs';
import {linkArrow} from '../src/link-arrow.js';

const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const read=p=>JSON.parse(readFileSync(resolve(root,p),'utf8'));
const catalogue=read('public/data/catalogue.json');
const benchmark=read('public/data/benchmark.json');
const repository=repositoryConfig();
const resultData=read('public/data/full-results.json');
const liteData=read('public/data/lite-results.json');
const resultsByTask=new Map(resultData.tasks.map(t=>[t.id,t]));
const tasks=orderTasksForBrowsing(catalogue.tasks.map(enrichTask));
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const heading=s=>esc(s).replace(/\p{L}+[–-]\p{L}+/gu,term=>`<span class="task-title-term">${term}</span>`);
assert.equal(tasks.length,100);
assert.deepEqual(new Set(tasks.map(t=>t.id)),new Set(editorialIds));
assert.deepEqual(new Set(tasks.filter(t=>['construction','open'].includes(t.track)).map(t=>t.id)),new Set(explanationIds));
assert.equal(tasks.filter(t=>t.lite).length,20);
const counts={theorem:20,solver:30,construction:20,open:30};
for(const [key,n] of Object.entries(counts))assert.equal(tasks.filter(t=>t.track===key).length,n);
for(const t of tasks){
  if(t.track==='solver'||t.track==='theorem') assert(taskSource(t)?.url,`Missing source link: ${t.id}`);
  assert.match(t.id,/^[a-z0-9-]+$/);
  assert(t.title.length>5&&t.summary.length>40&&t.diagramCaption.length>80);
  assert(!/\/home\/|\/app\/|msh\.team|TCSBENCH_|token_secret/.test(t.question_markdown));
}
const md=new Marked({renderer:{
  html({text}) {return esc(text);},
  image({text}) {return esc(text);},
  link({href,tokens}) {
    const label=this.parser.parseInline(tokens);
    return /^https?:\/\//.test(href)?`<a href="${esc(href)}" rel="noopener noreferrer">${label}</a>`:label;
  },
  codespan({text}) {return `<span class="math-inline">${esc(text)}</span>`;},
}});
const math=(source)=>katex.renderToString(source,{throwOnError:true,displayMode:true,output:'htmlAndMathml',strict:'error'});
const path=t=>`tasks/${t.id}/`;
const track=t=>benchmark.tracks.find(x=>x.id===t.track);
const trackOutput={
  theorem:['Complete the proof','Prove the fixed main theorem in Lean 4, using the supplied definitions and any explicitly permitted hypotheses.','The Lean kernel checks the proof. Axiom checks reject unsupported assumptions and unfinished proof placeholders.'],
  solver:['Build a reusable solver','Submit a program that computes solutions for the instances it receives, within the task’s time and resource limits.','The task checker validates each answer or certificate and computes the score from verified results. Hidden instances test whether the program generalizes beyond practice inputs.'],
  construction:['Construct and certify','Submit an explicit mathematical object or a bound, together with the required Lean proof or certificate of its properties.','The verifier checks the submitted object or bound against the fixed definitions and computes the score from the verified result.'],
  open:['Prove or refute','Complete either the conjecture or its formal negation in Lean 4, following the task’s fixed definitions.','The Lean kernel checks a complete proof of the conjecture or its negation.'],
};

function page(task,i){
  const tr=track(task),prev=tasks[i-1],next=tasks[i+1],out=trackOutput[task.track];
  const sameTrack=tasks.filter(t=>t.track===task.track),trackIndex=sameTrack.indexOf(task);
  const related=[1,2,3].map(offset=>sameTrack[(trackIndex+offset)%sameTrack.length]);
  const source=taskSource(task);
  const referenceLine=source?`<p class="task-source-link"><a href="${esc(source.url)}" rel="noopener noreferrer">${esc(task.reference)} ${linkArrow}</a></p>`:`<p>${esc(task.reference)}</p>`;
  // These are paragraph boundaries only; preserve the statement word for word.
  const statement=task.id==='dijkstra-universal'
    ? task.question_markdown.replace('distance order. The\ntheorem states:', 'distance order.\n\nThe theorem states:').replace('arc lengths. In other\nwords,', 'arc lengths.\n\nIn other words,')
    : task.question_markdown;
  const detail=`<section class="task-statement"><h2>The research question</h2><div class="prose">${md.parse(statement)}</div></section>${Object.hasOwn(publishedExamples,task.id)?'<details class="task-example" id="task-example"><summary>Illustrative example</summary><div id="task-lab-root"></div></details>':''}`;
  return `<a class="skip-link" href="${path(task)}#main">Skip to content</a>
  <header class="header"><div class="header-inner wrap"><a class="wordmark" href="./" aria-label="TCSExam home"><img src="brand/tcsexam-wordmark.svg" alt="TCSExam" width="146" height="26"></a><nav aria-label="Main navigation"><a href="./#overview">Overview</a><a href="./#lite">Lite</a><a href="./#full">Full</a><a href="./#outcomes">Outcomes</a><a href="./#problems" aria-current="page">Task explorer</a><a href="./#start">Get started</a><a href="./#resources">Citation</a><a href="${esc(repository.documentation)}">Documentation</a></nav></div></header>
  <main id="main" class="task-document wrap" data-task-id="${task.id}" data-track="${task.track}">
    <div class="task-back"><a href="./?filter=${task.track}#problems"><span aria-hidden="true">←</span> Back to ${tr.short.toLowerCase()}</a><span class="task-number">Problem ${String(task.number).padStart(3,'0')}</span></div>
    <header class="task-page-intro">
      <p class="task-category"><a href="./?filter=${task.track}#problems">${tr.label}</a><span>${esc(task.domain)}</span>${task.lite?'<span class="lite-badge">Lite</span>':''}</p>
      <h1 id="task-page-title">${heading(task.title)}</h1><p class="task-lede">${esc(task.summary)}</p>
      <div class="task-page-actions"><a href="${path(task)}#task-results">Task results <span aria-hidden="true">↓</span></a><button type="button" data-copy-page>Copy link ${linkArrow}</button></div><p id="page-copy-status" role="status" class="sr-only"></p>
    </header>
    <div class="task-concept">
      <div class="task-math-band"><span>Mathematical setting</span><div tabindex="0" role="region" aria-label="Mathematical notation">${math(task.diagramMath)}</div></div>
      <figure class="task-figure"><div class="task-figure-art" data-preview-family="${task.drawing}" tabindex="0" role="group" aria-label="Task illustration">${renderIllustration(task,{motion:true})}</div><figcaption>${esc(task.diagramCaption)}</figcaption></figure>
    </div>
    <article class="task-reading" aria-labelledby="task-page-title">
      ${detail}
      ${task.lite ? `<div id="task-results" class="task-result-sets"><div class="task-result-switch" data-task-results-switch role="group" aria-label="Result set for this task" hidden><button type="button" data-task-result-set="lite" aria-controls="lite-task-results" aria-pressed="true">TCSExam-Lite</button><button type="button" data-task-result-set="full" aria-controls="full-task-results" aria-pressed="false">TCSExam-Full</button></div>${renderLiteTaskResults(task,liteData)}${renderTaskResults(task,resultsByTask.get(task.id),resultData,true)}</div>` : renderTaskResults(task,resultsByTask.get(task.id),resultData)}
      ${task.id === 'binary-code-a22-10' ? `<section class="task-code-demo" id="code-demonstration" aria-labelledby="code-demonstration-title">
        <h2 id="code-demonstration-title">Explore error correction</h2>
        <div class="task-code-layout">
          <div class="task-code-intro"><p>Astra also supplied this 64-word code. Every word has 22 bits, and any two differ in at least 10 positions. Recovery is guaranteed for every pattern of up to four flips.</p><p>Select a codeword and flip its bits to inspect recovery. This construction attains the existing lower bound of 64; the improved upper bound of 82 comes from a separate proof.</p></div>
          <figure id="binary-code-case"><img class="binary-code-fallback" src="paper/binary-code.svg" width="360" height="410" loading="lazy" alt="The submitted 64-word code. A 22-bit word with four flipped bits is still closest to its original codeword." /><figcaption>64 words · 22 bits each · At least 10 bits apart.</figcaption></figure>
        </div>
      </section>` : ''}
      <section class="task-deliverable"><div><h2>${out[0]}</h2><p>${out[1]}</p></div><div><h2>How it is checked</h2><p>${out[2]}</p></div></section>
      <section class="task-facts" aria-label="Task context"><dl><div><dt>Scope</dt><dd>${task.lite?'TCSExam-Lite · ':''}TCSExam-Full</dd></div><div><dt>Task ID</dt><dd class="task-id">${task.id}</dd></div></dl></section>
      <section class="task-reference"><h2>Source &amp; acknowledgement</h2>${referenceLine}</section>
    </article>
    <nav class="page-pager" aria-label="Previous and next tasks">${prev?`<a href="${path(prev)}" rel="prev"><span>← Previous task</span><strong>${esc(prev.title)}</strong></a>`:'<div></div>'}${next?`<a href="${path(next)}" rel="next"><span>Next task →</span><strong>${esc(next.title)}</strong></a>`:'<div></div>'}</nav>
    <section class="related-problems"><div class="related-heading"><h2>More ${tr.short.toLowerCase()}</h2><a href="./?filter=${task.track}#problems">Browse the track →</a></div><div class="related-task-grid">${related.map(t=>`<a class="related-task" data-track="${t.track}" href="${path(t)}"><span class="related-number">${String(t.number).padStart(3,'0')}</span><h3>${esc(t.title)}</h3><span aria-hidden="true">→</span></a>`).join('')}</div></section>
  </main><footer class="footer wrap"><a class="wordmark" href="./"><img src="brand/tcsexam-wordmark.svg" alt="TCSExam" width="146" height="26"></a><p>A benchmark for the full range of <span class="brand-tcs">TCS</span> research.</p><a href="LICENSE.txt">CC BY 4.0</a><a href="./#problems">All 100 tasks ↑</a></footer>`;
}

const template=readFileSync(resolve(root,'dist/task.html'),'utf8');
assert(template.includes('<!--TASK_PAGE-->'),'Vite task template marker missing');
const base=process.env.SITE_BASE_PATH||'./';
const pageBase=base==='./'?'../../':base.endsWith('/')?base:`${base}/`;
for(const [i,task] of tasks.entries()){
  const canonical=process.env.SITE_URL?`<link rel="canonical" href="${esc(new URL(path(task),process.env.SITE_URL.replace(/\/?$/,'/')).href)}">`:'';
  const html=template.replace('<!--TASK_BASE-->',`<base href="${esc(pageBase)}">${canonical}`)
    .replaceAll('__TASK_TITLE__',esc(task.title)).replaceAll('__TASK_DESCRIPTION__',esc(task.summary))
    .replace('<!--TASK_PAGE-->',()=>page(task,i));
  const dir=resolve(root,'dist',path(task));mkdirSync(dir,{recursive:true});writeFileSync(resolve(dir,'index.html'),html);

}
rmSync(resolve(root,'dist/task.html'));
writeFileSync(resolve(root,'dist/data/catalogue.json'),JSON.stringify(catalogue,null,2)+'\n');
writeFileSync(resolve(root,'dist/data/benchmark.json'),JSON.stringify(withRepositoryLinks(benchmark,repository),null,2)+'\n');
if(process.env.SITE_URL){
  const url=process.env.SITE_URL.replace(/\/?$/,'/');
  writeFileSync(resolve(root,'dist/sitemap.xml'),`<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${['',...tasks.map(path)].map(p=>`<url><loc>${esc(new URL(p,url).href)}</loc></url>`).join('')}</urlset>`);
}
console.log(`Exported ${tasks.length} static task pages; all diagrams and formulas rendered.`);
