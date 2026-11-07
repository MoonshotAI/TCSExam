const esc = text => String(text).replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));

export const conjectureTooltip = 'Nonzero scores come from adapting OpenAI’s published counterexamples and Lean proofs.';
export const conjectureSources = {
  'ryser-conjecture': {label: 'Ryser', url: 'tasks/ryser-conjecture/', publication: 'https://github.com/openai/math/blob/main/lean/docs/162.md'},
  'bin-packing-mirup': {label: 'MIRUP', url: 'tasks/bin-packing-mirup/', publication: 'https://github.com/openai/math/blob/main/lean/docs/118.md'},
};

export function conjecturePublicationNote(taskId) {
  const source = conjectureSources[taskId];
  if (!source) return '';
  return `<p class="task-published-result">After this task was selected, OpenAI reported <a href="${source.publication}" rel="noopener noreferrer">counterexamples to this conjecture and accompanying Lean formalizations</a>.</p>`;
}

export function conjectureNoteRef(href = '#open-conjecture-details') {
  return `<sup class="conjecture-note-ref"><a href="${esc(href)}" data-conjecture-note aria-label="About the nonzero conjecture scores">*</a></sup>`;
}

export function conjectureNote() {
  return `<p class="conjecture-score-note"><span aria-hidden="true">*</span> Nonzero conjecture scores use <a href="https://openai.com/index/sharing-ai-progress-in-mathematics/" rel="noopener noreferrer">OpenAI’s published results</a>.</p>`;
}

export function conjectureDetails(data) {
  const models = new Map(data.models.map(model => [model.id, model.label]));
  const rows = Object.entries(conjectureSources).flatMap(([id, source]) => {
    const task = data.tasks.find(task => task.id === id);
    return task.results.flatMap(row => {
      const accepted = row.attempts.filter(attempt => attempt.score === 1).length;
      return accepted ? [`<tr><th scope="row">${esc(models.get(row.model))}</th><td><a href="${source.url}" rel="noopener noreferrer">${source.label}</a></td><td>${accepted} / ${row.attempts.length}</td></tr>`] : [];
    });
  });
  return `<details class="conjecture-details" id="open-conjecture-details">
    <summary>About the conjecture scores</summary>
    <div class="conjecture-details-body">
      <p>The tasks were selected before OpenAI released these results. Kimi K3.1 Pro and DeepSeek V4.1 Flash 1017 were evaluated afterward, with Internet access. Their successful submissions adapted the published counterexamples and Lean proofs to the task definitions and passed Lean verification.</p>
      <div class="conjecture-attempts" role="region" aria-label="Accepted conjecture submissions" tabindex="0"><table>
        <caption>Accepted submissions across three attempts per task</caption>
        <thead><tr><th scope="col">Model</th><th scope="col">Task</th><th scope="col">Accepted / attempted</th></tr></thead>
        <tbody>${rows.join('')}</tbody>
      </table></div>
    </div>
  </details>`;
}
