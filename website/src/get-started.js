const agents = {
  'kimi-code': { endpoint: 'https://YOUR_KIMI_PROVIDER.example/v1', model: 'kimi-k3', key: 'YOUR_KIMI_API_KEY' },
  'claude-code': { endpoint: 'https://YOUR_ANTHROPIC_PROVIDER.example', model: 'YOUR_CLAUDE_MODEL_ID', key: 'YOUR_CLAUDE_API_KEY' },
  codex: { endpoint: 'https://YOUR_RESPONSES_PROVIDER.example/v1', model: 'YOUR_CODEX_MODEL_ID', key: 'YOUR_CODEX_API_KEY' },
  'grok-build': { endpoint: 'https://YOUR_GROK_PROVIDER.example/v1', model: 'YOUR_GROK_MODEL_ID', key: 'YOUR_GROK_API_KEY' },
};
const quote = (value) => `'${String(value).replaceAll("'", "'\\''")}'`;
export const defaultState = { suite: 'lite', protocol: 'offline', agent: 'kimi-code', step: 'run' };

export function selectOption(state, field, value) {
  return { ...state, [field]: value, ...(field === 'suite' ? { protocol: value === 'full' ? 'online' : 'offline' } : {}) };
}

export function generateCommands(state, repository) {
  const { suite, protocol, agent } = { ...defaultState, ...state };
  if (!['lite', 'full'].includes(suite) || !['online', 'offline'].includes(protocol) || !Object.hasOwn(agents, agent)) {
    throw new Error('Unsupported getting-started selection');
  }
  const provider = agents[agent];
  const selection = `--suite ${suite} --solver-protocol ${protocol}`;
  const imageManifest = `build/${suite}-${protocol}-images.json`;
  const continued = ' \\\n  ';
  const backend = protocol === 'online' ? `${continued}--backend-plan "$TCSEXAM_BACKEND_PLAN"` : '';
  const commitRef = /^[0-9a-f]{40}$/i.test(repository.ref || '');
  return {
    install: [
      `git clone${repository.ref && repository.ref !== 'HEAD' && !commitRef ? ` --branch ${quote(repository.ref)}` : ''} -- ${quote(repository.cloneUrl)} TCSExam`,
      'cd TCSExam',
      ...(commitRef ? [`git checkout --detach ${quote(repository.ref)}`] : []),
      'python3 -m venv .venv', 'source .venv/bin/activate',
      `python -m pip install -e '.[${protocol === 'online' ? 'runtime,backend' : 'runtime'}]'`,
    ].join('\n'),
    configure: [
      '# Replace placeholders before running; keep credentials private.',
      'unset TCSEXAM_AGENT_VERSION TCSEXAM_REASONING_EFFORT TCSEXAM_MAX_CONTEXT_TOKENS',
      'unset TCSEXAM_MAX_OUTPUT_TOKENS TCSEXAM_MAX_TURNS TCSEXAM_GROK_API_BACKEND',
      'unset CLAUDE_CODE_EFFORT_LEVEL CLAUDE_CODE_MAX_OUTPUT_TOKENS CLAUDE_CODE_MAX_TURNS',
      'unset GROK_BUILD_MAX_TURNS',
      `export TCSEXAM_AGENT="${agent}"`,
      `export TCSEXAM_API_BASE_URL="${provider.endpoint}"`,
      `export TCSEXAM_MODEL="${provider.model}"`,
      `export TCSEXAM_API_KEY="${provider.key}"`,
      ...(agent === 'grok-build' ? ['export TCSEXAM_GROK_API_BACKEND="responses"'] : []),
      ...(protocol === 'online' ? [
        '', '# Use credentials and a plan from your running Online backend.',
        'export TCSEXAM_BASE_URL="https://YOUR_RUNNING_BACKEND.example"',
        'export TCSEXAM_TOKEN_ID="YOUR_BACKEND_TOKEN_ID"',
        'export TCSEXAM_TOKEN_SECRET="YOUR_BACKEND_TOKEN_SECRET"',
        'export TCSEXAM_ARCHIVE_TOKEN="YOUR_BACKEND_ARCHIVE_TOKEN"',
        `export TCSEXAM_BACKEND_PLAN="/PATH/TO/${suite}-online-backend.plan.json"`,
      ] : []),
    ].join('\n'),
    run: [
      '# After Install and Configure, in the same shell:',
      'tcsexam source-inputs',
      `tcsexam build ${selection}${continued}--output ${imageManifest}`,
      ...(protocol === 'online' ? ['# Prepare and start your Online backend using the backend guide.', `# Its plan must match ${suite.toUpperCase()} / Online and the image manifest above.`] : []),
      `tcsexam doctor ${selection}${continued}--agent ${agent} --artifacts ${imageManifest}${backend}${continued}--output build/${suite}-${protocol}-readiness.json`,
      '# Resolve doctor blockers before starting model API usage.',
      `tcsexam run ${selection}${continued}--agent ${agent} --artifacts ${imageManifest}${backend}${continued}--attempts 1 --concurrency 1${continued}--output build/${suite}-${protocol}-job.json`,
    ].join('\n'),
  };
}

export function mountGetStarted(root, repository) {
  if (!root) return;
  root.querySelector('[data-start-source]').href = repository.url;
  let state = { ...defaultState };
  const code = root.querySelector('[data-start-code]');
  const status = root.querySelector('[data-start-status]');
  const render = () => {
    root.querySelectorAll('[data-start-field]').forEach((button) => {
      button.setAttribute('aria-pressed', String(state[button.dataset.startField] === button.dataset.startValue));
    });
    code.textContent = generateCommands(state, repository)[state.step];
    root.querySelector('[data-start-summary]').textContent = `${state.suite === 'lite' ? 'Lite · 20 tasks' : 'Full · 100 tasks'} / ${state.protocol === 'online' ? 'Online' : 'Offline'} / ${Object.keys(agents).includes(state.agent) ? { 'kimi-code': 'Kimi Code', 'claude-code': 'Claude Code', codex: 'Codex', 'grok-build': 'Grok Build' }[state.agent] : ''}`;
    root.querySelector('[data-start-backend]').hidden = state.protocol !== 'online';
    status.textContent = '';
  };
  root.querySelectorAll('[data-start-field]').forEach((button) => {
    button.disabled = false;
    button.addEventListener('click', () => {
      state = selectOption(state, button.dataset.startField, button.dataset.startValue);
      render();
    });
  });
  const copy = root.querySelector('[data-start-copy]');
  copy.disabled = false;
  copy.addEventListener('click', async () => {
    const text = code.textContent;
    try {
      await navigator.clipboard.writeText(text);
      status.textContent = 'Commands copied.';
    } catch {
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(code);
      selection.removeAllRanges();
      selection.addRange(range);
      status.textContent = 'Copy unavailable. Commands selected; press Ctrl+C or ⌘C to copy.';
    }
  });
  render();
}
