import data from '../public/paper/quantum-code.json' with { type: 'json' };

const operators = ['I', 'X', 'Y', 'Z'];
export function pauliMasks(word) {
  let x = 0, z = 0;
  [...word].forEach((op, i) => {
    if (op === 'X' || op === 'Y') x |= 1 << i;
    if (op === 'Z' || op === 'Y') z |= 1 << i;
  });
  return { x, z };
}
function parity(n) { let p = 0; while (n) { p ^= 1; n &= n - 1; } return p; }
export function quantumChecks(generators, word) {
  const { x, z } = pauliMasks(word);
  return generators.map(([gx, gz]) => parity((x & gz) ^ (z & gx)));
}
export function stabilizerContains(generators, word) {
  const rows = new Map();
  const reduce = value => {
    for (let bit = 49; bit >= 0; bit--) if ((value & (1n << BigInt(bit))) && rows.has(bit)) value ^= rows.get(bit);
    return value;
  };
  for (const [x, z] of generators) {
    const row = reduce(BigInt(x) | BigInt(z) << 25n);
    if (row) rows.set(row.toString(2).length - 1, row);
  }
  const { x, z } = pauliMasks(word);
  return reduce(BigInt(x) | BigInt(z) << 25n) === 0n;
}
export function quantumOutcome(generators, word) {
  if (/^I+$/.test(word)) return 'clear';
  if (quantumChecks(generators, word).some(Boolean)) return 'detected';
  return stabilizerContains(generators, word) ? 'harmless' : 'undetected';
}
const labels = { clear: 'No error', detected: 'Error detected', harmless: 'Logical state unchanged', undetected: 'Error missed' };
const codes = [['reference', data.reference, 'Reference · distance 5'], ['astra', data.astra, 'Astra · distance 6']];

export function renderQuantumCode() {
  const word = data.examples.five.paulis;
  return `<div class="quantum-reader">
    <div class="quantum-qubits" role="group" aria-label="Choose errors on 25 qubits; arrow keys move between qubits">
      ${Array.from({length: 25}, (_, i) => `<button type="button" data-qubit="${i}" data-error="${word[i]}" aria-label="Qubit ${i + 1}: ${word[i] === 'I' ? 'no error' : word[i] + ' error'}." disabled><small aria-hidden="true">${i + 1}</small><span aria-hidden="true">${word[i] === 'I' ? '·' : word[i]}</span></button>`).join('')}
    </div>
    <p class="quantum-instruction">Select a cell to change its error.</p>
    <div class="quantum-presets" role="group" aria-label="Verified error examples"><button type="button" data-quantum-example="five" aria-pressed="true" disabled>5-qubit example</button><button type="button" data-quantum-example="six" aria-pressed="false" disabled>6-qubit limit</button><button type="button" data-quantum-reset disabled>Reset</button></div>
    <div class="quantum-comparison">
      ${codes.map(([id, code, label]) => `<div class="quantum-code-row" data-quantum-code="${id}" data-outcome="${quantumOutcome(code.generators_xz, word)}"><div class="quantum-code-label"><strong>${label}</strong><span class="quantum-outcome">${labels[quantumOutcome(code.generators_xz, word)]}</span></div></div>`).join('')}
    </div>
    <details class="quantum-details"><summary>How it works</summary>
      <p>Each cell is a physical qubit. Select it to cycle through no error (·), a bit flip (X), both flips (Y), and a phase flip (Z).</p>
      ${codes.map(([id, code, label]) => {
        const checks = quantumChecks(code.generators_xz, word);
        const count = checks.reduce((a, b) => a + b, 0);
        return `<div class="quantum-check-row" data-quantum-checks="${id}"><strong>${label}</strong><div class="quantum-checks" role="img" aria-label="${count} of 18 checks triggered: ${checks.join(' ')}">${checks.map(value => `<span aria-hidden="true" data-triggered="${value}">${value}</span>`).join('')}</div><p class="quantum-check-count">${count} of 18 checks triggered</p></div>`;
      }).join('')}
      <p class="quantum-explanation">The same five-qubit error is missed by the reference code and detected by Astra’s code.</p>
    </details>
    <p class="sr-only quantum-status" role="status" aria-live="polite" aria-atomic="true"></p>
  </div>`;
}

export async function mountQuantumCode(figure) {
  if (!figure || figure.dataset.ready) return;
  let word = data.examples.five.paulis;
  if (!figure.querySelector('.quantum-reader')) figure.innerHTML = renderQuantumCode();
  const buttons = [...figure.querySelectorAll('[data-qubit]')];
  function draw() {
    buttons.forEach((button, i) => {
      button.dataset.error = word[i];
      button.querySelector('span').textContent = word[i] === 'I' ? '·' : word[i];
      button.setAttribute('aria-label', `Qubit ${i + 1}: ${word[i] === 'I' ? 'no error' : word[i] + ' error'}. Click for ${operators[(operators.indexOf(word[i]) + 1) % 4] === 'I' ? 'no error' : operators[(operators.indexOf(word[i]) + 1) % 4] + ' error'}.`);
    });
    codes.forEach(([id, code]) => {
      const row = figure.querySelector(`[data-quantum-code="${id}"]`);
      const checks = quantumChecks(code.generators_xz, word);
      const outcome = quantumOutcome(code.generators_xz, word);
      row.dataset.outcome = outcome;
      row.querySelector('.quantum-outcome').textContent = labels[outcome];
      const detail = figure.querySelector(`[data-quantum-checks="${id}"]`);
      detail.querySelectorAll('.quantum-checks span').forEach((cell, i) => { cell.dataset.triggered = checks[i]; cell.textContent = checks[i]; });
      const count = checks.reduce((a, b) => a + b, 0);
      detail.querySelector('.quantum-checks').setAttribute('aria-label', `${count} of 18 checks triggered: ${checks.join(' ')}`);
      detail.querySelector('.quantum-check-count').textContent = `${count} of 18 checks triggered`;
    });
    const weight = [...word].filter(x => x !== 'I').length;
    let message;
    if (word === data.examples.five.paulis) message = 'The same five-qubit error is missed by the reference code and detected by Astra’s code.';
    else if (word === data.examples.six.paulis) message = 'This six-qubit error escapes Astra’s checks. Remove any one of its errors to make it detectable.';
    else if (!weight) message = 'No errors applied. Choose an example or click a qubit.';
    else message = `${weight} qubit${weight === 1 ? '' : 's'} affected. Reference: ${labels[quantumOutcome(data.reference.generators_xz, word)].toLowerCase()}; Astra: ${labels[quantumOutcome(data.astra.generators_xz, word)].toLowerCase()}.`;
    figure.querySelector('.quantum-status').textContent = message;
    figure.querySelector('.quantum-explanation').textContent = message;
    figure.querySelectorAll('[data-quantum-example]').forEach(button => button.setAttribute('aria-pressed', String(word === data.examples[button.dataset.quantumExample].paulis)));
    figure.dataset.weight = weight;
  }
  buttons.forEach((button, i) => {
    button.addEventListener('click', () => { word = word.slice(0, i) + operators[(operators.indexOf(word[i]) + 1) % 4] + word.slice(i + 1); draw(); });
    button.addEventListener('keydown', event => {
      const delta = { ArrowRight: 1, ArrowLeft: -1, ArrowUp: -5, ArrowDown: 5 }[event.key];
      if (delta) { event.preventDefault(); buttons[(i + delta + 25) % 25].focus(); }
    });
  });
  figure.querySelectorAll('[data-quantum-example]').forEach(button => button.addEventListener('click', () => { word = data.examples[button.dataset.quantumExample].paulis; draw(); }));
  figure.querySelector('[data-quantum-reset]').addEventListener('click', () => { word = 'I'.repeat(25); draw(); });
  draw();
  figure.querySelectorAll('button').forEach(button => { button.disabled = false; });
  figure.dataset.ready = 'true';
}
