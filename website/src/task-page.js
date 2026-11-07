import '@fontsource/inter/latin-400.css';
import '@fontsource/inter/latin-500.css';
import '@fontsource/inter/latin-600.css';
import '@fontsource/ibm-plex-mono/latin-400.css';
import 'katex/dist/katex.min.css';
import './style.css';
import './research-design.css';
import './catalogue/catalogue.css';
import './catalogue/task-page.css';
import './binary-code-case.css';
import './lite-results.css';
import {mountOptionalExample} from './labs/optional.js';
import {mountPreviewMotion} from './previews/motion.js';
import {createElasticMotion} from './previews/elastic.js';
import {linkArrow} from './link-arrow.js';
import {mountConjectureNotes} from './conjecture-note-interactions.js';
import './conjecture-note.css';

mountConjectureNotes();

const header = document.querySelector('.header');
const headerSize = new ResizeObserver(() => {
  document.documentElement.style.scrollPaddingTop = `${header.getBoundingClientRect().height + 12}px`;
});
headerSize.observe(header);

const button=document.querySelector('[data-copy-page]');
button?.addEventListener('click',async()=>{
  try {
    await navigator.clipboard.writeText(location.href);
    button.textContent='Link copied ✓';
    document.querySelector('#page-copy-status').textContent='Task link copied to clipboard.';
    setTimeout(()=>{button.innerHTML=`Copy link ${linkArrow}`;},2200);
  } catch {
    document.querySelector('#page-copy-status').textContent='Copy the address from your browser to share this task.';
  }
});
mountPreviewMotion(document.querySelector('.task-concept'), {
  itemSelector: '.task-figure', surfaceSelector: '.task-figure-art', tilt: false,
  createDisturbance: createElasticMotion,
});
const resultSwitch=document.querySelector('[data-task-results-switch]');
if(resultSwitch){
  const panels=[...document.querySelectorAll('[data-result-panel]')];
  const showResults=value=>{
    panels.forEach(panel=>{panel.hidden=panel.dataset.resultPanel!==value;});
    resultSwitch.querySelectorAll('button').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.taskResultSet===value)));
    const target=new URL(location.href);
    target.hash='task-results';
    target.searchParams.set('results',value);
    document.querySelector('.task-page-actions a').href=target.href;
  };
  const restoreResults=()=>showResults(location.hash==='#full-task-results'||new URL(location.href).searchParams.get('results')==='full'?'full':'lite');
  resultSwitch.hidden=false;
  resultSwitch.addEventListener('click',event=>{
    const button=event.target.closest('[data-task-result-set]');
    if(!button)return;
    const url=new URL(location.href);
    url.searchParams.set('results',button.dataset.taskResultSet);
    url.hash='task-results';
    history.replaceState(history.state,'',url);
    showResults(button.dataset.taskResultSet);
  });
  window.addEventListener('popstate',restoreResults);
  restoreResults();
}
document.documentElement.dataset.ready='true';
mountOptionalExample({id:document.querySelector('[data-task-id]').dataset.taskId});

// Load the submitted-code reader only when its task-page example is in view.
const codeFigure = document.querySelector('#binary-code-case');
if (codeFigure) {
  const observer = new IntersectionObserver(entries => {
    if (!entries.some(entry => entry.isIntersecting)) return;
    observer.disconnect();
    import('./binary-code-case.js')
      .then(module => module.mountBinaryCode(codeFigure))
      .catch(() => {}); // The source-backed static illustration stays available.
  }, {rootMargin: '300px'});
  observer.observe(codeFigure);
}
