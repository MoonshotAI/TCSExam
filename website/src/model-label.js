const marks = {
  'GPT-6 Astra': 'openai', 'Kimi K3': 'kimi', 'GLM-5.3': 'zai',
  'Qwen3.8 Max (0902)': 'qwen', 'Grok 4.6': 'grok',
  'DeepSeek V4.1 Flash 1017': 'deepseek',
  'Opus 5.5': 'claude', 'Kimi K3.1 Pro': 'kimi',
};
const esc = text => String(text).replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));

export function modelLabel(name, base = './') {
  const mark = marks[name];
  const logo = mark ? `<img class="model-logo" src="${esc(base)}brand/models/${mark}.svg" width="20" height="20" alt="" aria-hidden="true">` : '';
  return `<span class="model-name">${logo}<span>${esc(name)}</span></span>`;
}
