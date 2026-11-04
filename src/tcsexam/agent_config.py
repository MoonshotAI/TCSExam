"""Explicit model connections for Harbor's four supported installed agents.

Credentials are referenced by host environment-variable name only. Resolving a
configuration never reads a key into the serialized job or provenance object.
The agent clock remains 43,200 seconds; optional turn/token limits are recorded
separately and may cause a CLI to finish before that wall-clock limit.
"""
from dataclasses import dataclass
import os
import re
from urllib.parse import urlsplit

AGENTS = ('kimi-code', 'claude-code', 'codex', 'grok-build')
AGENT_TIMEOUT_SEC = 43200
PACKAGE_HOSTS = ('archive.ubuntu.com', 'security.ubuntu.com', 'ports.ubuntu.com',
                 'deb.debian.org', 'security.debian.org', 'dl-cdn.alpinelinux.org',
                 'mirrors.aliyun.com')
NODE_HOSTS = ('github.com', 'raw.githubusercontent.com', 'nodejs.org', 'registry.npmjs.org',
              'objects.githubusercontent.com', 'release-assets.githubusercontent.com')
INSTALL_HOSTS = {
    'kimi-code': (*NODE_HOSTS, *PACKAGE_HOSTS),
    'claude-code': ('downloads.claude.ai', 'registry.npmjs.org', *PACKAGE_HOSTS),
    'codex': (*NODE_HOSTS, *PACKAGE_HOSTS),
    'grok-build': ('x.ai', 'storage.googleapis.com', *PACKAGE_HOSTS),
}
# These are the provider prefixes and API backends implemented by Harbor 0.22.
GROK_PROVIDERS = {
    'xai': ('XAI_API_KEY', 'https://api.x.ai/v1', None),
    'openai': ('OPENAI_API_KEY', 'https://api.openai.com/v1', 'responses'),
    'anthropic': ('ANTHROPIC_API_KEY', 'https://api.anthropic.com/v1', 'messages'),
    'openrouter': ('OPENROUTER_API_KEY', 'https://openrouter.ai/api/v1', 'chat_completions'),
}
EFFORTS = {
    'kimi-code': ('low', 'medium', 'high', 'max'),
    'claude-code': ('low', 'medium', 'high', 'xhigh', 'max', 'ultracode'),
    'codex': ('none', 'minimal', 'low', 'medium', 'high', 'xhigh'),
    'grok-build': ('none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max'),
}


def _value(args, field, env, environ):
    value = getattr(args, field, None)
    if value is None:
        value = environ.get(env)
    if value is None or isinstance(value, str) and not value.strip():
        return None
    return value.strip() if isinstance(value, str) else value


def _first(environ, names):
    return next((name for name in names if environ.get(name, '').strip()), None)


def _positive(value, label):
    if value is None:
        return None
    if isinstance(value, bool) or not re.fullmatch(r'[0-9]+', str(value)) or int(value) < 1:
        raise ValueError(label + ' must be a positive integer')
    return int(value)


def _url(value):
    parsed = urlsplit(value)
    try:
        parsed.port
    except ValueError:
        raise ValueError('Invalid model API port') from None
    if (parsed.scheme not in ('https', 'http') or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment or any(c.isspace() for c in value)
            or any(ord(c) < 32 for c in value)):
        raise ValueError('Use an HTTP(S) API base URL without embedded credentials, query or fragment')
    return parsed.hostname


@dataclass(frozen=True)
class AgentSettings:
    config: dict
    provenance: dict
    credential_env: str
    host_overrides: dict

    def require_credentials(self, environ=None):
        configured = (os.environ.get(self.credential_env, '') if environ is None
                      else environ.get(self.credential_env, ''))
        if not configured.strip():
            raise ValueError('Set ' + self.credential_env + ' before starting ' + self.config['name'])


def selected_agent(args, environ=None):
    environ = os.environ if environ is None else environ
    name = _value(args, 'agent', 'TCSEXAM_AGENT', environ) or 'kimi-code'
    if name not in AGENTS:
        raise ValueError('Choose an agent from: ' + ', '.join(AGENTS))
    return name


def configure_agent(args, environ=None):
    """Produce a secret-free Harbor AgentConfig and requested-setting provenance.

    TCSEXAM_* overrides the selected CLI's native connection variables. Kimi
    alone has a default model/version. Other CLIs retain Harbor's install policy
    unless an exact version is supplied, and always require an explicit model.
    OAuth, auth.json and Bedrock modes are deliberately outside this API-key
    interface; host auth-mode switches are disabled in the generated execution.
    """
    environ = os.environ if environ is None else environ
    name = selected_agent(args, environ)
    model = _value(args, 'model', 'TCSEXAM_MODEL', environ)
    if not model:
        if name != 'kimi-code':
            raise ValueError('Set --model or TCSEXAM_MODEL explicitly for ' + name)
        model = 'kimi-k3'
    if not isinstance(model, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:/@+-]*', model):
        raise ValueError('Model ID must be nonempty and contain no whitespace or shell metacharacters')
    if name == 'codex' and '/' in model and (not model.startswith('openai/') or model.count('/') != 1):
        raise ValueError('Harbor Codex accepts a bare model ID or openai/MODEL; other prefixes are stripped by its CLI adapter')
    if name == 'claude-code' and '/' in model and (not model.startswith('anthropic/') or model.count('/') != 1):
        raise ValueError('Use a bare Claude Code model ID or anthropic/MODEL')
    version = _value(args, 'agent_version', 'TCSEXAM_AGENT_VERSION', environ)
    if version is not None and (not isinstance(version, str) or not re.fullmatch(
            r'[0-9]+(?:\.[0-9]+){1,3}(?:[-+][A-Za-z0-9_.-]+)?', version)):
        raise ValueError('--agent-version must be an exact numeric CLI version')
    version_policy = 'requested_pin' if version is not None else 'harbor_default_reuse_or_install'
    if version is None and name == 'kimi-code':
        version = '0.43.0'
        version_policy = 'tcsexam_default_pin'
    effort = _value(args, 'reasoning_effort', 'TCSEXAM_REASONING_EFFORT', environ)
    if effort is None and name == 'claude-code':
        effort = environ.get('CLAUDE_CODE_EFFORT_LEVEL', '').strip() or None
    if effort is None:
        effort = {'kimi-code': 'max', 'codex': 'high', 'grok-build': 'high'}.get(name)
    if effort is not None and effort not in EFFORTS[name]:
        raise ValueError('Unsupported reasoning effort for ' + name + ': choose ' + ', '.join(EFFORTS[name]))
    context = _positive(_value(args, 'max_context_tokens', 'TCSEXAM_MAX_CONTEXT_TOKENS', environ), '--max-context-tokens')
    output = _positive(_value(args, 'max_output_tokens', 'TCSEXAM_MAX_OUTPUT_TOKENS', environ), '--max-output-tokens')
    turns = _positive(_value(args, 'max_turns', 'TCSEXAM_MAX_TURNS', environ), '--max-turns')
    if name == 'claude-code' and output is None:
        output = _positive(environ.get('CLAUDE_CODE_MAX_OUTPUT_TOKENS', '').strip() or None, 'CLAUDE_CODE_MAX_OUTPUT_TOKENS')
    if turns is None and name in ('claude-code', 'grok-build'):
        native_turns = 'CLAUDE_CODE_MAX_TURNS' if name == 'claude-code' else 'GROK_BUILD_MAX_TURNS'
        turns = _positive(environ.get(native_turns, '').strip() or None, native_turns)
    if context is not None and name != 'kimi-code':
        raise ValueError('--max-context-tokens is supported only by kimi-code')
    if output is not None and name != 'claude-code':
        raise ValueError('--max-output-tokens is supported only by claude-code')
    if turns is not None and name not in ('claude-code', 'grok-build'):
        raise ValueError('--max-turns is supported only by claude-code and grok-build')
    backend = _value(args, 'grok_api_backend', 'TCSEXAM_GROK_API_BACKEND', environ)
    if backend is not None and (name != 'grok-build' or backend not in ('responses', 'chat_completions', 'messages')):
        raise ValueError('--grok-api-backend requires grok-build and responses, chat_completions or messages')
    provider = None
    if name == 'kimi-code':
        target_key = 'KIMI_MODEL_API_KEY'
        key_names = ('KIMI_MODEL_API_KEY', 'KIMI_API_KEY', 'MOONSHOT_API_KEY')
        base_names = ('KIMI_MODEL_BASE_URL', 'KIMI_BASE_URL')
        native_url = 'https://api.kimi.com/coding/v1'
    elif name == 'claude-code':
        target_key = 'ANTHROPIC_API_KEY'; key_names = ('ANTHROPIC_API_KEY',)
        base_names = ('ANTHROPIC_BASE_URL',); native_url = 'https://api.anthropic.com'
    elif name == 'codex':
        target_key = 'OPENAI_API_KEY'; key_names = ('OPENAI_API_KEY',)
        base_names = ('OPENAI_BASE_URL',); native_url = 'https://api.openai.com/v1'
    else:
        prefix, separator, remainder = model.partition('/')
        if separator and prefix not in GROK_PROVIDERS:
            raise ValueError('Grok Build model prefixes supported here: xai, openai, anthropic, openrouter')
        provider = prefix if separator else 'xai'
        slug = remainder if separator else model
        if not slug:
            raise ValueError('Grok Build requires a model ID after the provider prefix')
        target_key, native_url, native_backend = GROK_PROVIDERS[provider]
        key_names = (target_key,); base_names = ({
            'xai': ('XAI_BASE_URL',), 'openai': ('OPENAI_BASE_URL',),
            'anthropic': ('ANTHROPIC_BASE_URL',), 'openrouter': ('OPENROUTER_BASE_URL',),
        })[provider]
    credential = _first(environ, ('TCSEXAM_API_KEY', *key_names)) or 'TCSEXAM_API_KEY'
    base = _value(args, 'base_url', 'TCSEXAM_API_BASE_URL', environ)
    if base is None:
        native_base = _first(environ, base_names)
        base = environ[native_base].strip() if native_base else None
    explicit_base = base is not None
    base = base or native_url
    hostname = _url(base)
    kwargs = {'version': version} if version is not None else {}
    env = {target_key: '${' + credential + '}'}
    host_overrides = {}
    if name == 'kimi-code':
        context = context or 1048576
        env.update(KIMI_MODEL_BASE_URL=base, KIMI_MODEL_MAX_CONTEXT_SIZE=str(context),
                   KIMI_MODEL_CAPABILITIES='image_in,thinking', KIMI_MODEL_THINKING_EFFORT=effort,
                   KIMI_CODE_EXPERIMENTAL_FLAG='true')
    else:
        if effort is not None:
            kwargs['reasoning_effort'] = effort
        if turns is not None:
            kwargs['max_turns'] = turns
        if name == 'claude-code':
            kwargs['disallowed_tools'] = 'WebSearch'
            env.update(ANTHROPIC_BASE_URL=base, CLAUDE_FORCE_OAUTH='0', CLAUDE_CODE_USE_BEDROCK='0',
                       AWS_BEARER_TOKEN_BEDROCK='', CLAUDE_CODE_OAUTH_TOKEN='')
            if output is not None:
                env['CLAUDE_CODE_MAX_OUTPUT_TOKENS'] = str(output)
                # Harbor's Claude adapter also reads this value from its host.
                host_overrides['CLAUDE_CODE_MAX_OUTPUT_TOKENS'] = str(output)
        elif name == 'codex':
            env.update(OPENAI_BASE_URL=base, CODEX_FORCE_AUTH_JSON='0', CODEX_AUTH_JSON_PATH='')
            kwargs['web_search'] = 'disabled'
        else:
            if backend is None:
                backend = native_backend
            if explicit_base and backend is None:
                raise ValueError('A custom Grok endpoint requires --grok-api-backend (responses, chat_completions or messages)')
            if backend is not None:
                kwargs['grok_config'] = {
                    'models': {role: slug for role in ('default', 'session_summary', 'image_description', 'web_search')},
                    'model': {slug: {'name': slug, 'model': slug, 'base_url': base,
                                     'env_key': target_key, 'api_backend': backend}},
                }
            kwargs['disable_web_search'] = True
    config = {'name': name, 'model_name': model, 'kwargs': kwargs,
              'override_timeout_sec': float(AGENT_TIMEOUT_SEC),
              'extra_allowed_hosts': [hostname], 'env': env}
    provenance = {'agent': name, 'agent_version': version,
        'agent_version_policy': version_policy,
        'model': model, 'effective_model_id': model if name == 'kimi-code' else model.split('/', 1)[-1],
        'api_base_url': base, 'api_backend': backend,
        'credential_environment_variable': credential, 'reasoning_effort': effort,
        'max_context_tokens': context, 'max_output_tokens': output, 'max_turns': turns,
        'agent_timeout_sec': AGENT_TIMEOUT_SEC, 'validation_scope': 'configuration_only',
        'model_endpoint_contacted': False, 'install_allowed_hosts': list(INSTALL_HOSTS[name]),
        'requested_cli_kwargs': kwargs}
    return AgentSettings(config, provenance, credential, host_overrides)


def add_agent_arguments(parser):
    parser.add_argument('--agent', choices=AGENTS, help='Installed agent (default TCSEXAM_AGENT or kimi-code)')
    parser.add_argument('--base-url', help='Model API base URL (otherwise selected provider native endpoint)')
    parser.add_argument('--model', help='Explicit model ID; only Kimi has a default model')
    parser.add_argument('--agent-version', help='Exact CLI version (Kimi default 0.43.0; others Harbor install policy)')
    parser.add_argument('--reasoning-effort', help='Reasoning effort supported by the selected agent and model')
    parser.add_argument('--max-context-tokens', type=int, help='Kimi model context size (default 1048576)')
    parser.add_argument('--max-output-tokens', type=int, help='Claude Code output token limit (optional)')
    parser.add_argument('--max-turns', type=int, help='Claude Code/Grok turn limit; may finish before the time budget')
    parser.add_argument('--grok-api-backend', choices=('responses', 'chat_completions', 'messages'),
                        help='Grok custom endpoint wire protocol; required for a custom xAI endpoint')
