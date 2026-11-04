// Nearest-word decoding of the submitted 64-word code. Ties stay explicit;
// beyond four bit flips there is no general correction guarantee.
export function hammingDistance(a, b) {
  let distance = 0;
  for (let i = 0; i < a.length; i++) distance += Number(a[i] !== b[i]);
  return distance;
}

export function nearestCodewords(words, received) {
  let distance = Infinity;
  const indices = [];
  words.forEach((word, index) => {
    const current = hammingDistance(word, received);
    if (current < distance) { distance = current; indices.length = 0; }
    if (current === distance) indices.push(index);
  });
  return { distance, indices };
}

// One tab stop per set of bits/words; arrow keys inspect the rest.
function arrowNavigation(group, buttons, columns = 1) {
  group.addEventListener('keydown', event => {
    const current = buttons.indexOf(event.target);
    if (current < 0) return;
    const moves = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -columns, ArrowDown: columns };
    let next;
    if (event.key === 'Home') next = 0;
    else if (event.key === 'End') next = buttons.length - 1;
    else if (event.key in moves) next = Math.max(0, Math.min(buttons.length - 1, current + moves[event.key]));
    else return;
    event.preventDefault();
    buttons.forEach((button, index) => { button.tabIndex = index === next ? 0 : -1; });
    buttons[next].focus();
  });
  group.addEventListener('click', event => {
    const selected = event.target.closest('button');
    if (buttons.includes(selected)) buttons.forEach(button => { button.tabIndex = button === selected ? 0 : -1; });
  });
}

export async function mountBinaryCode(figure) {
  const response = await fetch(`${import.meta.env.BASE_URL}paper/binary-code.json`);
  if (!response.ok) return;
  const code = await response.json();
  const { words } = code;
  if (words.length !== 64 || !words.every(word => /^[01]{22}$/.test(word))) return;

  let selected = 1;
  const flipped = new Set([2, 7, 12, 18]);
  const miniWord = word => `<svg viewBox="0 0 66 16" aria-hidden="true">${[...word].map((bit, i) => `<rect x="${i * 3}" y="2" width="2" height="12" class="codebook-bit-${bit}"/>`).join('')}</svg>`;
  figure.innerHTML = `<div class="binary-code-reader">
    <p class="binary-code-label">64 submitted codewords</p>
    <div class="binary-codebook" role="group" aria-label="Choose a submitted codeword; arrow keys move, Enter selects">
      ${words.map((word, i) => `<button type="button" data-codeword="${i}" tabindex="${i === selected ? 0 : -1}" aria-label="Codeword ${i + 1}: ${word}" aria-pressed="${i === selected}">${miniWord(word)}</button>`).join('')}
    </div>
    <div class="binary-comparison">
      <p class="binary-row-label">Original word <span class="binary-word-number"></span></p>
      <div class="binary-word binary-original" role="img">${'<span class="binary-bit" aria-hidden="true"></span>'.repeat(22)}</div>
      <div class="binary-row-label"><span>Received · <span class="binary-flip-count"></span></span><button type="button" class="binary-reset">Reset</button></div>
      <div class="binary-word binary-received" role="group" aria-label="Flip received bits; arrow keys move, Enter flips a bit">${Array.from({ length: 22 }, (_, i) => `<button type="button" class="binary-bit" data-bit="${i}" tabindex="${i === 0 ? 0 : -1}"></button>`).join('')}</div>
      <p class="binary-row-label binary-decoded-label">Recovered word</p>
      <div class="binary-word binary-decoded" role="img">${'<span class="binary-bit" aria-hidden="true"></span>'.repeat(22)}</div>
    </div>
    <p class="binary-outcome" role="status" aria-live="polite" aria-atomic="true"></p>
  </div><figcaption>64 words · 22 bits each · At least 10 bits apart.</figcaption>`;
  const wordButtons = [...figure.querySelectorAll('[data-codeword]')];
  const bitButtons = [...figure.querySelectorAll('[data-bit]')];
  const originalRow = figure.querySelector('.binary-original');
  const decodedRow = figure.querySelector('.binary-decoded');
  const status = figure.querySelector('.binary-outcome');
  function draw() {
    const original = words[selected];
    const received = [...original].map((bit, i) => flipped.has(i) ? String(1 - Number(bit)) : bit).join('');
    const nearest = nearestCodewords(words, received);
    const ambiguous = nearest.indices.length > 1;
    const recovered = !ambiguous && nearest.indices[0] === selected;
    const decoded = ambiguous ? '?'.repeat(22) : words[nearest.indices[0]];
    wordButtons.forEach((button, i) => button.setAttribute('aria-pressed', String(i === selected)));
    [...originalRow.children].forEach((bit, i) => { bit.textContent = original[i]; });
    originalRow.setAttribute('aria-label', `Original codeword ${selected + 1}: ${original}`);
    figure.querySelector('.binary-word-number').textContent = String(selected + 1).padStart(2, '0');
    figure.querySelector('.binary-flip-count').textContent = `${flipped.size} ${flipped.size === 1 ? 'bit' : 'bits'} flipped`;
    bitButtons.forEach((button, i) => {
      button.textContent = received[i];
      button.setAttribute('aria-pressed', String(flipped.has(i)));
      button.setAttribute('aria-label', `Bit ${i + 1}: ${received[i]}${flipped.has(i) ? ', flipped' : ''}. Click to flip.`);
    });
    [...decodedRow.children].forEach((bit, i) => { bit.textContent = decoded[i]; });
    decodedRow.setAttribute('aria-label', ambiguous ? 'No unique closest codeword.' : `Decoded codeword ${nearest.indices[0] + 1}: ${decoded}`);
    figure.querySelector('.binary-decoded-label').textContent = recovered ? 'Recovered word' : 'Nearest word';
    figure.dataset.recovery = ambiguous ? 'ambiguous' : recovered ? 'recovered' : 'different';
    status.textContent = ambiguous
      ? `${nearest.indices.length} equally close words · recovery is ambiguous.`
      : recovered
        ? flipped.size > 4 ? 'Recovered for this pattern · recovery is guaranteed for every pattern of up to four flips.' : 'Original word recovered.'
        : 'A different word is closer · recovery failed.';
    figure.querySelector('.binary-reset').disabled = flipped.size === 0;
  }
  wordButtons.forEach((button, i) => button.addEventListener('click', () => {
    selected = i; flipped.clear(); draw();
  }));
  bitButtons.forEach((button, i) => button.addEventListener('click', () => {
    if (flipped.has(i)) flipped.delete(i); else flipped.add(i);
    draw();
  }));
  figure.querySelector('.binary-reset').addEventListener('click', () => { flipped.clear(); draw(); });
  arrowNavigation(figure.querySelector('.binary-codebook'), wordButtons, 8);
  arrowNavigation(figure.querySelector('.binary-received'), bitButtons);
  draw();
}
