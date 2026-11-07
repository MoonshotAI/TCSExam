import "@fontsource/inter/latin-400.css";
import "@fontsource/inter/latin-500.css";
import "@fontsource/inter/latin-600.css";
import "@fontsource/dm-sans/latin-400.css";
import "@fontsource/dm-sans/latin-500.css";
import "@fontsource/dm-sans/latin-600.css";
import "@fontsource/ibm-plex-mono/latin-400.css";
import "./style.css";
import { publishedExamples } from "./labs/catalogue.js";
import { mountOptionalExample } from "./labs/optional.js";
import { renderTaskPreview, mountPreviewMotion } from "./previews/index.js";
import { icon } from "./diagrams.js";
import { linkArrow } from "./link-arrow.js";
import { mountHeroArt } from "./hero-art.js";
import { renderPaperTrack } from "./paper.js";
import { renderLiteOverview, renderLiteTrack, renderLiteIndex, bindLiteIndexInteractions } from './lite-results.js';
import { resultScopes, normalizeResultsAnchor, readResultsLocation, writeResultsLocation } from './results-location.js';
import { mountResultsMotion } from './results-motion.js';
import './lite-results.css';
import "./reading.css";
import "./research-design.css";
import "./get-started.css";
import { mountGetStarted } from "./get-started.js";
import "./lite-index.css";
import "./catalogue/catalogue.css";
import { enrichTask } from "./catalogue/editorial.js";
import { orderTasksForBrowsing } from "./catalogue/browse-order.js";
import { benchmarkSources } from "./catalogue/sources.js";
import { mountResearchCases } from "./cases.js";
import { preserveReloadPosition } from "./scroll-position.js";
import { dataUrl } from "./data-url.js";
import {conjectureNoteRef} from './conjecture-note.js';
import {mountConjectureNotes} from './conjecture-note-interactions.js';
import './conjecture-note.css';

mountConjectureNotes();

const initialUrl = normalizeResultsAnchor(new URL(location.href));
if (initialUrl.href !== location.href) history.replaceState(history.state, "", initialUrl);
const reloadPosition = preserveReloadPosition();

const $ = (selector) => document.querySelector(selector);
const escape = (value) =>
  String(value).replace(
    /[&<>"']/g,
    (character) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        character
      ],
  );
let data;
let liteData;
let fullIndexData;
let catalogue;
let taskScope = "full";
let catalogueView = "gallery";
let cataloguePage = 1;
const cataloguePageSize = 20;
let taskTrack = "all";
const resultStates = readResultsLocation(initialUrl);
let lastTaskButton;
let taskReturnPosition;
let taskScrollRestoration;
let currentTaskId;
let taskSequence = [];
let disposeTaskLab = () => {};
let disposePreviewMotion = () => {};

let equationModule;
async function renderMath(root = document) {
  const elements = [...root.querySelectorAll("[data-math]")]
    .filter((element) => !element.dataset.mathRendered && !element.closest("details:not([open]), dialog:not([open])") && element.getClientRects().length);
  if (!elements.length) return;
  let renderer;
  try {
    equationModule ||= import("./equations.js");
    renderer = await equationModule;
  } catch { equationModule = undefined; }
  for (const element of elements) {
    if (!element.isConnected || element.closest("details:not([open]), dialog:not([open])")) continue;
    try {
      if (!renderer) throw new Error("Formula renderer unavailable");
      renderer.renderEquation(element);
      element.dataset.mathRendered = "true";
      element.classList.remove("math-fallback");
    } catch {
      element.textContent = element.dataset.math;
      element.classList.add("math-fallback");
    }
  }
}

function syncLocation(section) {
  const url = new URL(location.href);
  if (section) url.hash = section;
  const values = {
    filter: taskTrack === "all" ? null : taskTrack,
    scope: taskScope === "lite" ? "lite" : null,
    layout: catalogueView === "list" ? "list" : null,
    page: catalogueView === "gallery" && cataloguePage > 1 ? String(cataloguePage) : null,
    q: $("#task-search").value.trim() || null,
  };
  for (const [key, value] of Object.entries(values)) {
    if (value) url.searchParams.set(key, value);
    else url.searchParams.delete(key);
  }
  history.replaceState(history.state, "", writeResultsLocation(url, resultStates));
}

function restoreLocation(initial = false) {
  const params = new URL(location.href).searchParams;
  const validTrack = (id, fallback) => data.tracks.some((track) => track.id === id) ? id : fallback;
  const filter = validTrack(params.get("filter"), "all");
  const query = (params.get("q") || "").slice(0, 256);
  const selectedResults = readResultsLocation(new URL(location.href));
  const scope = params.get("scope") === "lite" ? "lite" : "full";
  const layout = params.get("layout") === "list" ? "list" : "gallery";
  const page = layout === "gallery" && /^[1-9]\d{0,2}$/.test(params.get("page") || "") ? Number(params.get("page")) : 1;
  const tasksChanged = initial || taskTrack !== filter || $("#task-search").value !== query || taskScope !== scope || catalogueView !== layout || cataloguePage !== page;
  taskScope = scope; catalogueView = layout; cataloguePage = page;
  taskTrack = filter;
  $("#task-search").value = query;
  if (tasksChanged) renderTasks(false);
  for (const scope of resultScopes) {
    const changed = initial || resultStates[scope].view !== selectedResults[scope].view
      || resultStates[scope].track !== selectedResults[scope].track;
    resultStates[scope] = selectedResults[scope];
    if (changed) renderResults(scope);
  }
  history.replaceState(history.state, "", writeResultsLocation(new URL(location.href), resultStates));
  const id = params.get("task");
  if (data.tasks.some((task) => task.id === id)) {
    if (!$("#task-dialog").open || currentTaskId !== id) openTask(id, undefined, true);
  } else {
    if ($("#task-dialog").open) closeTask(true);
    if (currentTaskId) restoreTaskPosition();
  }
}

function updateTasks() { cataloguePage = 1; renderTasks(); syncLocation("problems"); }
function updateResults(scope) { renderResults(scope); syncLocation(scope); }

function trackById(id) {
  return data.tracks.find((track) => track.id === id);
}
function bindTrackLinks() {
  document.querySelectorAll("[data-explore]").forEach((link) =>
    link.addEventListener("click", () => {
      taskTrack = link.dataset.explore;
      taskScope = "full";
      $("#task-search").value = "";
      updateTasks();
    }),
  );
}

function filteredTasks() {
  const query = $("#task-search").value.trim().toLowerCase();
  return catalogue.tasks.filter((task) =>
    (taskScope === "full" || task.lite) &&
    (taskTrack === "all" || task.track === taskTrack) &&
    `${task.id} ${task.title} ${task.domain} ${task.summary}`.toLowerCase().includes(query),
  );
}

function renderTasks(returnToTop = true) {
  const controls = $(".catalogue-controls");
  const wasSticky = controls.getBoundingClientRect().top <= $(".header").getBoundingClientRect().bottom + 1;
  disposePreviewMotion();
  const tasks = filteredTasks();
  const pageCount = Math.max(1, Math.ceil(tasks.length / cataloguePageSize));
  cataloguePage = Math.min(cataloguePage, pageCount);
  const first = (cataloguePage - 1) * cataloguePageSize;
  const visibleTasks = catalogueView === "gallery" ? tasks.slice(first, first + cataloguePageSize) : tasks;
  $("#task-count").textContent =
    `${tasks.length} of ${taskScope === "lite" ? 20 : 100} tasks${taskTrack === "all" ? " · All tracks" : ` · ${trackById(taskTrack).label}`}${catalogueView === "gallery" && pageCount > 1 ? ` · Showing ${first + 1}–${first + visibleTasks.length}` : ""}`;
  document
    .querySelectorAll("[data-filter]")
    .forEach((button) =>
      button.setAttribute(
        "aria-pressed",
        String(button.dataset.filter === taskTrack),
      ),
    );
  $("#task-grid").dataset.layout = catalogueView;
  $("#problems").dataset.layout = catalogueView;
  $("#solver-source-note").hidden = taskTrack !== "solver";
  document.querySelectorAll("[data-scope]").forEach(button => button.setAttribute("aria-pressed", String(button.dataset.scope === taskScope)));
  document.querySelectorAll("[data-catalogue-view]").forEach(button => button.setAttribute("aria-pressed", String(button.dataset.catalogueView === catalogueView)));
  document.querySelectorAll("[data-filter]").forEach(button => {
    const id = button.dataset.filter;
    button.querySelector("span").textContent = catalogue.tasks.filter(t => (taskScope === "full" || t.lite) && (id === "all" || t.track === id)).length;
  });
  $("#task-grid").innerHTML = tasks.length
    ? visibleTasks.map(task => {
      const href = `${import.meta.env.BASE_URL}tasks/${task.id}/`;
      const preview = renderTaskPreview(task);
      if (catalogueView === "gallery") return `<article class="task-tile" data-track="${task.track}"><a href="${href}" data-task="${task.id}" aria-labelledby="task-title-${task.id}"><div class="catalogue-drawing">${preview}${task.lite ? '<span class="tile-lite">Lite</span>' : ''}</div><div class="tile-copy"><p class="tile-domain">${escape(task.domain)}</p><h3 id="task-title-${task.id}">${escape(task.title)}<span aria-hidden="true">${linkArrow}</span></h3><p class="tile-summary">${escape(task.summary)}</p></div></a></article>`;
      return `<article class="task-card" data-track="${task.track}">${preview}<div class="task-description"><h3 id="task-title-${task.id}">${escape(task.title)}</h3><p>${escape(task.summary)}</p></div><div class="task-metadata"><span class="track-label">${icon(task.track)}${escape(trackById(task.track).short)}</span><span class="task-domain">${escape(task.domain)}</span>${task.lite ? '<span class="lite-badge">Lite</span>':''}</div><a class="task-open task-action" data-task="${task.id}" href="${href}" aria-labelledby="task-action-${task.id} task-title-${task.id}"><span id="task-action-${task.id}">View task</span><span aria-hidden="true">→</span></a></article>`;
    }).join("")
    : '<div class="empty-state"><h3>No matching tasks</h3><p>Try another topic or select all tracks.</p><button id="reset-search" class="button" type="button">Clear filters</button></div>';
  disposePreviewMotion = mountPreviewMotion($("#task-grid"));
  const pagination = $("#catalogue-pagination");
  pagination.hidden = catalogueView !== "gallery" || pageCount <= 1;
  pagination.innerHTML = pagination.hidden ? "" : `<button type="button" data-page="${cataloguePage-1}" ${cataloguePage === 1 ? "disabled" : ""} aria-label="Previous page">←</button>${Array.from({length:pageCount},(_,i)=>`<button type="button" data-page="${i+1}" aria-label="Page ${i+1}" ${cataloguePage === i+1 ? 'aria-current="page"' : ""}>${i+1}</button>`).join("")}<button type="button" data-page="${cataloguePage+1}" ${cataloguePage === pageCount ? "disabled" : ""} aria-label="Next page">→</button>`;
  $("#clear-task-filters").hidden = taskTrack === "all" && !$("#task-search").value;

  if (returnToTop) $("#catalogue-scroll").scrollTo({ top: 0, left: 0, behavior: "instant" });
  if (returnToTop && wasSticky && !$("#task-dialog").open) {
    $("#catalogue-top").scrollIntoView({ block: "start", behavior: "instant" });
  }
  $("#reset-search")?.addEventListener("click", () => {
    taskTrack = "all";
    $("#task-search").value = "";
    updateTasks();
    $("#task-search").focus();
  });
}

function openTask(id, button, fromHistory = false) {
  const task = data.tasks.find((task) => task.id === id);
  if (!task) return;
  const wasOpen = $("#task-dialog").open;
  if (!wasOpen) {
    lastTaskButton = button || document.querySelector(`[data-task="${id}"]`);
    // A shared URL has no originating row; ordinary opens and Forward do.
    taskReturnPosition = button || history.state?.tcsexamModal
      ? { left: scrollX, top: scrollY } : null;
    taskScrollRestoration = history.state?.tcsexamScrollRestoration || history.scrollRestoration;
    history.scrollRestoration = "manual";
    const matching = filteredTasks();
    taskSequence = (matching.some((item) => item.id === id) ? matching : data.tasks)
      .filter((item) => data.tasks.some((original) => original.id === item.id))
      .map((item) => item.id);
  }
  disposeTaskLab();
  currentTaskId = id;
  const track = trackById(task.track);
  $("#dialog-content").innerHTML =
    `<article data-task-detail="${task.id}" data-track="${task.track}"><div class="dialog-task-meta"><p class="track-label">${icon(task.track)}${escape(track.label)}</p><p>${escape(task.domain)}</p></div><h2 id="dialog-title" tabindex="-1">${escape(task.title)}</h2><p class="dialog-summary">${escape(task.summary)}</p>
    <section class="task-specification" aria-labelledby="task-spec-title"><h3 id="task-spec-title">Task specification</h3><div class="formula task-formula" data-math="${escape(task.formula)}"></div>
    <dl class="detail-grid"><div><dt>Submission</dt><dd>${escape(track.output)}</dd></div><div><dt>Verification</dt><dd>${escape(track.verification)}</dd></div><div class="detail-scoring"><dt>Scoring · Lite protocol</dt><dd>${escape(track.score)}</dd></div></dl>
    <div class="detail-note"><h3>Scope &amp; assumptions</h3><p>${escape(task.note)}</p></div><p class="small"><a href="${import.meta.env.BASE_URL}tasks/${task.id}/">Read the full research question, results and source →</a></p></section>
    ${Object.hasOwn(publishedExamples, id) ? '<details class="task-example" id="task-example"><summary>Illustrative example</summary><div id="task-lab-root"></div></details>' : ""}
    </article>`;
  disposeTaskLab = mountOptionalExample(task);
  const index = taskSequence.indexOf(id);
  $("#task-position").textContent = `${index + 1} / ${taskSequence.length}`;
  $("#task-previous").disabled = index <= 0;
  $("#task-next").disabled = index >= taskSequence.length - 1;
  $("#copy-task-link").textContent = "Copy link";
  $("#task-copy-status").textContent = "";
  $("#task-link-fallback").hidden = true;
  if (!fromHistory) {
    syncLocation();
    const url = new URL(location.href);
    url.searchParams.set("task", id);
    if (wasOpen) history.replaceState(history.state, "", url);
    else history.pushState({ ...history.state, tcsexamModal: true, tcsexamScrollRestoration: taskScrollRestoration }, "", url);
  }
  if (!wasOpen) $("#task-dialog").showModal();
  renderMath($("#dialog-content"));
  $("#task-dialog").scrollTop = 0;
  if (wasOpen) $("#dialog-title").focus({ preventScroll: true });
}

function nextTask(direction) {
  const next = taskSequence[taskSequence.indexOf(currentTaskId) + direction];
  if (next) openTask(next);
}

async function copyText(text, focusTarget) {
  if (navigator.clipboard && window.isSecureContext) {
    try { await navigator.clipboard.writeText(text); return true; } catch { /* Use local selection below. */ }
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.className = "sr-only";
  ($("#task-dialog").open ? $("#task-dialog") : document.body).append(textarea);
  textarea.select();
  let copied = false;
  try { copied = document.execCommand("copy"); } catch { copied = false; } finally {
    textarea.remove();
    focusTarget.focus({ preventScroll: true });
  }
  return copied;
}

async function copyTaskLink() {
  const id = currentTaskId;
  const url = new URL(location.href);
  url.hash = "problems";
  const copied = await copyText(url.href, $("#copy-task-link"));
  if (currentTaskId !== id || !$("#task-dialog").open) return;
  $("#copy-task-link").textContent = copied ? "Copied" : "Copy link";
  $("#task-copy-status").textContent = copied ? "Task link copied." : "Select and copy the task link.";
  if (!copied) {
    $("#task-link-fallback").hidden = false;
    $("#task-link-input").value = url.href;
    $("#task-link-input").select();
  }
}

function closeTask(fromHistory = false) {
  if (!$("#task-dialog").open) return;
  disposeTaskLab();
  $("#task-dialog").close();
  if (!fromHistory) {
    if (history.state?.tcsexamModal) history.back();
    else {
      const url = new URL(location.href);
      url.searchParams.delete("task");
      history.replaceState(history.state, "", url);
      restoreTaskPosition();
    }
  }
}

function restoreTaskPosition() {
  const button = lastTaskButton, position = taskReturnPosition;
  const restoration = taskScrollRestoration;
  currentTaskId = null;
  // History traversal can restore an old hash after popstate. Finish afterwards,
  // cancelling any smooth anchor scroll before returning keyboard focus.
  requestAnimationFrame(() => {
    if ($("#task-dialog").open) return;
    if (position) window.scrollTo({ ...position, behavior: "instant" });
    else button?.scrollIntoView({ block: "center", behavior: "instant" });
    if (button?.isConnected) button.focus({ preventScroll: true });
    history.scrollRestoration = restoration || "auto";
  });
}

function renderResults(scope) {
  const root = $(`#${scope}`);
  const {view: paperView, track: resultTrack} = resultStates[scope];
  const isLite = scope === 'lite';
  root.querySelectorAll("[data-result-track]").forEach(button =>
    button.setAttribute("aria-pressed", String(button.dataset.resultTrack === resultTrack)));
  root.querySelectorAll("[data-paper-view]").forEach(button =>
    button.setAttribute("aria-pressed", String(button.dataset.paperView === paperView)));
  const notes = [
    `Scores are averaged over attempts for each task, then equally over ${isLite ? 'the five tasks' : 'all tasks'} in each track. Kimi K3, Kimi K3.1 Pro and DeepSeek V4.1 Flash 1017 have three attempts per task; other systems have one. Each attempt has a 12-hour budget.`,
    'Theorems and open conjectures measure complete proofs or refutations. Solver scores use the fixed Kimi K3 reference. For constructions, 100 represents the task’s reference result; higher scores indicate an improvement.',
  ];
  notes.push('Index = 0.3 × Theorems + 0.3 × Solvers + 0.3 × Constructions + 0.1 × Open conjectures, calculated from the unrounded percentage-scale scores.');
  root.querySelector(".protocol-note").innerHTML = notes.map(note => `<p>${escape(note)}</p>`).join('');
  const download = root.querySelector(".results-download");
  download.href = dataUrl(`${scope}-index.csv`);
  download.download = `tcsexam-${scope}-index.csv`;
  download.innerHTML = 'Download CSV <span aria-hidden="true">↓</span>';
  root.querySelector(".result-tabs").hidden = paperView === "table";
  if (!isLite) {
    root.querySelector(".result-detail").innerHTML = fullIndexData
      ? renderPaperTrack(data, resultTrack, paperView, fullIndexData)
      : '<p role="alert">Full Index results are unavailable. Please reload the page.</p>';
  } else root.querySelector(".result-detail").innerHTML = liteData
    ? paperView === 'table' ? renderLiteOverview(liteData, data.tracks, resultTrack) : resultTrack === 'index' ? renderLiteIndex(liteData, data.tracks) : renderLiteTrack(liteData, trackById(resultTrack))
    : '<p role="alert">Lite results are unavailable. Please reload the page.</p>';
  root.querySelector(".solver-protocol-note").hidden = !root.querySelector(".result-detail .solver-protocol-ref");
  mountResultsMotion(root);
}

function renderCitation() {
  $("#acknowledgements-links").innerHTML = benchmarkSources.map(source => `<a href="${escape(source.url)}" rel="noopener noreferrer">${escape(source.label)}</a>`).join("");
  $("#citation-text").innerHTML = escape(data.citation).replace(/\bTCS\b/g, '<span class="brand-tcs">TCS</span>');
}

async function copyCitation() {
  try {
    if (navigator.clipboard && window.isSecureContext)
      await navigator.clipboard.writeText(data.citation);
    else {
      const textarea = document.createElement("textarea");
      textarea.value = data.citation;
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.append(textarea);
      textarea.select();
      const copied = document.execCommand("copy");
      textarea.remove();
      $("#copy-citation").focus();
      if (!copied) throw new Error("Clipboard unavailable");
    }
    $("#copy-status").textContent = "BibTeX copied to clipboard";
    $("#copy-citation").textContent = "Copied ✓";
  } catch {
    $("#copy-status").textContent =
      "Clipboard unavailable. Select and copy the visible BibTeX.";
    $("#copy-citation").textContent = "Select text below";
  }
}

async function init() {
  const prepareCases = mountResearchCases();
  mountGetStarted($("#start"), __SITE_REPOSITORY__);
  mountHeroArt($(".research-tracks"));
  const response = await fetch(dataUrl("benchmark.json"), {cache:"no-store"});
  if (!response.ok) throw new Error("Catalogue could not be loaded");
  data = await response.json();
  const catalogueResponse = await fetch(dataUrl("catalogue.json"), {cache:"no-store"});
  if (!catalogueResponse.ok) throw new Error("Full task catalogue could not be loaded");
  catalogue = await catalogueResponse.json();
  try {
    const response = await fetch(dataUrl("lite-results.json"), {cache:"no-store"});
    if (response.ok) liteData = await response.json();
  } catch { /* The Full results remain available if the Lite file cannot load. */ }
  try {
    const response = await fetch(dataUrl("full-index.json"), {cache:"no-store"});
    if (response.ok) fullIndexData = await response.json();
  } catch { /* Lite results remain available if the Full Index file cannot load. */ }
  catalogue.tasks = orderTasksForBrowsing(catalogue.tasks.map(enrichTask));
  bindTrackLinks();
  $("#task-filters").innerHTML = [
    { id: "all", short: "All tasks" },
    ...data.tracks,
  ]
    .map(
      (track) =>
        `<button type="button" data-filter="${track.id}" aria-pressed="${track.id === "all"}">${track.id === "all" ? "" : '<i aria-hidden="true"></i>'}${escape(track.short)} <span>${track.id === "all" ? 100 : track.full_count}</span></button>`,
    )
    .join("");
  document.querySelectorAll("[data-filter]").forEach((button) =>
    button.addEventListener("click", () => {
      taskTrack = button.dataset.filter;
      updateTasks();
    }),
  );
  document.querySelectorAll("[data-scope]").forEach(button => button.addEventListener("click", () => {
    taskScope = button.dataset.scope;
    updateTasks();
  }));
  document.querySelectorAll("[data-catalogue-view]").forEach(button => button.addEventListener("click", () => {
    catalogueView = button.dataset.catalogueView;
    updateTasks();
  }));
  $("#task-search").addEventListener("input", updateTasks);
  $("#catalogue-pagination").addEventListener("click", event => {
    const button = event.target.closest("[data-page]");
    if (!button || button.disabled) return;
    cataloguePage = Number(button.dataset.page);
    renderTasks();
    syncLocation("problems");
    $("#catalogue-top").scrollIntoView({block:"start",behavior:"instant"});
    $("#task-grid a")?.focus({preventScroll:true});
  });
  $("#clear-task-filters").addEventListener("click", () => {
    taskTrack = "all";
    $("#task-search").value = "";
    updateTasks();
    $("#task-search").focus();
  });
  for (const scope of resultScopes) {
    const root = $(`#${scope}`);
    bindLiteIndexInteractions(root);
    root.querySelector(".result-tabs").innerHTML = '<button type="button" data-result-track="index" data-track="index" aria-pressed="false">Index</button>' + data.tracks.map(track => {
      const button = `<button type="button" data-result-track="${track.id}" data-track="${track.id}" aria-pressed="false">${icon(track.id)}${escape(track.label)}</button>`;
      return scope === 'full' && track.id === 'open' ? `<span class="conjecture-result-label">${button}${conjectureNoteRef()}</span>` : button;
    }).join("");
    root.querySelector(".results-workspace").addEventListener("click", event => {
      const viewButton = event.target.closest("[data-paper-view]");
      const trackButton = event.target.closest("[data-result-track]");
      const sortButton = event.target.closest("[data-result-sort]");
      if (viewButton || trackButton || sortButton) {
        if (viewButton) resultStates[scope].view = viewButton.dataset.paperView;
        else resultStates[scope].track = (trackButton || sortButton).dataset[trackButton ? 'resultTrack' : 'resultSort'];
        updateResults(scope);
        if (sortButton) root.querySelector(`[data-result-sort="${resultStates[scope].track}"]`).focus({preventScroll:true});
      }
      const related = event.target.closest("[data-related-track]");
      if (related) {
        taskTrack = related.dataset.relatedTrack;
        taskScope = scope;
        $("#task-search").value = "";
        updateTasks();
      }
    });
  }
  const updateStickySizes = () => {
    const root = document.documentElement;
    root.style.setProperty("--header-height", `${$(".header").getBoundingClientRect().height}px`);
    root.style.setProperty("--catalogue-controls-height", `${$(".catalogue-controls").getBoundingClientRect().height}px`);
  };
  const sizeObserver = new ResizeObserver(updateStickySizes);
  sizeObserver.observe($(".header"));
  sizeObserver.observe($(".catalogue-controls"));
  updateStickySizes();
  restoreLocation(true);
  renderCitation();
  renderMath();
  $("#copy-citation").addEventListener("click", copyCitation);
  $("#task-previous").addEventListener("click", () => nextTask(-1));
  $("#task-next").addEventListener("click", () => nextTask(1));
  $("#copy-task-link").addEventListener("click", copyTaskLink);
  $(".dialog-close").addEventListener("click", () => closeTask());
  $("#task-dialog").addEventListener("keydown", (event) => {
    if (event.key !== "Tab") return;
    const focusable = [
      ...$("#task-dialog").querySelectorAll(
        'button:not(:disabled), a[href], input, select, summary, [tabindex="0"]',
      ),
    ].filter((element) => element.getClientRects().length);
    const first = focusable[0],
      last = focusable.at(-1);
    if (
      (event.shiftKey && document.activeElement === first) ||
      (!event.shiftKey && document.activeElement === last)
    ) {
      event.preventDefault();
      (event.shiftKey ? last : first).focus();
    }
  });
  $("#task-dialog").addEventListener("close", () => {
    if (!$("#task-dialog").open) disposeTaskLab();
  });
  $("#task-dialog").addEventListener("cancel", (event) => {
    event.preventDefault();
    closeTask();
  });
  $("#task-dialog").addEventListener("click", (event) => {
    if (event.target === $("#task-dialog")) {
      const box = $("#task-dialog").getBoundingClientRect();
      if (
        event.clientX < box.left ||
        event.clientX > box.right ||
        event.clientY < box.top ||
        event.clientY > box.bottom
      )
        closeTask();
    }
  });
  window.addEventListener("popstate", () => restoreLocation());
  document.addEventListener("toggle", (event) => {
    if (event.target instanceof HTMLDetailsElement && event.target.open) renderMath(event.target);
  }, true);
  const navLinks = [...document.querySelectorAll('.header nav a[href^="#"]')];
  const updateActiveNav = () => {
    const active =
      navLinks
        .filter(
          (link) =>
            $(link.hash).getBoundingClientRect().top <= innerHeight * 0.35,
        )
        .at(-1) || navLinks[0];
    navLinks.forEach((link) => {
      if (link === active) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    });
  };
  const observer = new IntersectionObserver(updateActiveNav, {
    rootMargin: "-10% 0px -65% 0px",
  });
  navLinks.forEach((link) => observer.observe($(link.hash)));
  const restoredPosition = await reloadPosition.restore(prepareCases);
  if (restoredPosition && taskReturnPosition) taskReturnPosition = restoredPosition;
  updateActiveNav();
  document.documentElement.dataset.ready = "true";
}
init().catch((error) => {
  reloadPosition.cancel();
  $("#task-grid").innerHTML =
    `<div class="empty-state" role="alert"><h3>Task data is unavailable</h3><p>${escape(error.message)}. Please try loading the page again.</p><button type="button" id="retry-page" class="button">Reload page</button></div>`;
  $("#retry-page").addEventListener("click", () => location.reload());
  document.querySelectorAll(".benchmark-results .result-detail").forEach(element => {
    element.innerHTML = '<p role="alert">Results are unavailable. Please reload the page.</p>';
  });
});
