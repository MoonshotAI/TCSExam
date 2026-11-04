"""Exercise real Harbor schemas, CLI adapters and phase-policy resolution, offline."""
from argparse import Namespace
import asyncio
import copy
import json
import os
from pathlib import Path
import tomllib
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from harbor.agents.factory import AgentFactory
from harbor.models.agent.context import AgentContext
from harbor.models.agent.name import AgentName
from harbor.models.job.config import JobConfig
from harbor.models.task.config import TaskConfig
from harbor.models.task.verifier_mode import resolve_task_verifier_mode
from harbor.models.trial.config import AgentConfig, EnvironmentConfig
from harbor.trial.network_policy import resolve_trial_network_plan

from tcsexam.agent_config import AGENTS, INSTALL_HOSTS, configure_agent
from tcsexam.cli import main
from tcsexam.layout import repository, selection
from tcsexam.runtime import native_config, prepare_agent_install_network
from tcsexam.setup import cache_path

ROOT = repository()
SECRET = 'fixture-secret-not-for-generated-files'


def args(agent='kimi-code', **values):
    return Namespace(agent=agent, **values)


def test_kimi_defaults_remain_explicit_and_do_not_serialize_the_key():
    settings = configure_agent(args(), {'TCSEXAM_API_KEY': SECRET})
    config = settings.config
    assert config['model_name'] == 'kimi-k3'
    assert config['kwargs'] == {'version': '0.43.0'}
    assert config['env']['KIMI_MODEL_MAX_CONTEXT_SIZE'] == '1048576'
    assert config['env']['KIMI_MODEL_THINKING_EFFORT'] == 'max'
    assert config['env']['KIMI_MODEL_API_KEY'] == '${TCSEXAM_API_KEY}'
    assert config['extra_allowed_hosts'] == ['api.kimi.com']
    assert settings.provenance['max_turns'] is None
    assert config['override_timeout_sec'] == 43200
    assert SECRET not in json.dumps([config, settings.provenance])


@pytest.mark.parametrize('agent,key,model,base', [
    ('kimi-code', 'KIMI_MODEL_API_KEY', 'kimi-k3', 'https://api.kimi.com/coding/v1'),
    ('claude-code', 'ANTHROPIC_API_KEY', 'claude-fixture', 'https://api.anthropic.com'),
    ('codex', 'OPENAI_API_KEY', 'codex-fixture', 'https://api.openai.com/v1'),
    ('grok-build', 'XAI_API_KEY', 'grok-fixture', 'https://api.x.ai/v1'),
])
def test_native_connection_key_and_unpinned_version_policy(agent, key, model, base):
    settings = configure_agent(args(agent, model=model), {key: SECRET})
    settings.require_credentials({key: SECRET})
    assert settings.config['env'][key] == '${' + key + '}'
    assert settings.provenance['api_base_url'] == base
    assert settings.provenance['credential_environment_variable'] == key
    if agent != 'kimi-code':
        assert 'version' not in settings.config['kwargs']
        assert settings.provenance['agent_version'] is None
        assert settings.provenance['agent_version_policy'] == 'harbor_default_reuse_or_install'
        assert settings.provenance['max_context_tokens'] is None
    with pytest.raises(ValueError, match=key):
        settings.require_credentials({})


@pytest.mark.parametrize('agent', AGENTS[1:])
def test_non_kimi_models_are_never_invented(agent):
    with pytest.raises(ValueError, match='explicitly'):
        configure_agent(args(agent), {})


@pytest.mark.parametrize('agent,key,model', [
    ('kimi-code', 'KIMI_MODEL_API_KEY', 'model-a'),
    ('claude-code', 'ANTHROPIC_API_KEY', 'model-b'),
    ('codex', 'OPENAI_API_KEY', 'model-c'),
    ('grok-build', 'XAI_API_KEY', 'xai/model-d'),
])
def test_common_settings_override_native_variables_without_exposing_secrets(agent, key, model):
    settings = configure_agent(args(agent, model=model, base_url='https://custom.example/v1',
        agent_version='0.43.1', grok_api_backend='responses' if agent=='grok-build' else None),
        {'TCSEXAM_API_KEY':SECRET, key:'native-secret'})
    assert settings.config['env'][key] == '${TCSEXAM_API_KEY}'
    assert settings.provenance['agent_version'] == '0.43.1'
    assert settings.config['extra_allowed_hosts'] == ['custom.example']
    assert SECRET not in json.dumps([settings.config, settings.provenance])
    JobConfig.model_validate({'agents':[settings.config]})


@pytest.mark.parametrize('model,key,backend,slug', [
    ('openai/sample-model', 'OPENAI_API_KEY', 'responses', 'sample-model'),
    ('anthropic/sample-model', 'ANTHROPIC_API_KEY', 'messages', 'sample-model'),
    ('openrouter/org/sample-model', 'OPENROUTER_API_KEY', 'chat_completions', 'org/sample-model'),
])
def test_grok_real_harbor_custom_provider_tables(tmp_path, model, key, backend, slug):
    settings = configure_agent(args('grok-build', model=model, base_url='https://custom.example/v1'), {key: SECRET})
    with patch.dict(os.environ, {key:SECRET}, clear=True):
        agent = AgentFactory.create_agent_from_config(AgentConfig(**settings.config), tmp_path)
        config = tomllib.loads(agent._build_config_toml())
    assert config['model'][slug] == {'name':slug, 'model':slug, 'base_url':'https://custom.example/v1', 'env_key':key, 'api_backend':backend}
    assert set(config['models'].values()) == {slug}
    assert config['features']['telemetry'] is False
    assert config['harness']['disable_codebase_upload'] is True
    assert config['disable_web_search'] is True


@pytest.mark.parametrize('settings,message', [
    ({'agent':'unknown'}, 'Choose an agent'),
    ({'agent':'codex','model':'model','reasoning_effort':'max'}, 'reasoning effort'),
    ({'model':'model','agent_version':'0.43.0; echo unsafe'}, 'exact numeric'),
    ({'model':'model','base_url':'https://user:secret@provider.example/v1'}, 'without embedded'),
    ({'model':'model','base_url':'https://provider.example/v1?key=secret'}, 'without embedded'),
    ({'model':'model','base_url':'https://provider.example:bad/v1'}, 'port'),
    ({'agent':'codex','model':'model','max_context_tokens':1024}, 'only by kimi'),
    ({'agent':'grok-build','model':'model','max_output_tokens':1024}, 'only by claude'),
    ({'agent':'kimi-code','model':'model','max_turns':3}, 'only by claude'),
    ({'model':'model','max_context_tokens':0}, 'positive integer'),
    ({'model':'model','max_context_tokens':True}, 'positive integer'),
    ({'model':'model','max_context_tokens':'1.5'}, 'positive integer'),
    ({'agent':'grok-build','model':'model','base_url':'https://custom.example/v1'}, 'requires --grok-api-backend'),
    ({'agent':'grok-build','model':'unknown/model'}, 'prefixes'),
    ({'agent':'codex','model':'org/custom/model'}, 'bare model'),
    ({'agent':'claude-code','model':'org/custom/model'}, 'bare Claude'),
    ({'agent':'codex','model':'model','grok_api_backend':'responses'}, 'requires grok-build'),
    ({'model':'bad model'}, 'Model ID'),
])
def test_invalid_agent_connections_fail_before_any_execution(settings, message):
    with pytest.raises(ValueError, match=message):
        configure_agent(Namespace(**settings), {})


def test_requested_limits_and_native_claude_fallbacks_are_reported():
    settings = configure_agent(args('claude-code',model='model',max_turns=9,max_output_tokens=1234),
        {'CLAUDE_CODE_EFFORT_LEVEL':'max','CLAUDE_CODE_MAX_TURNS':'80','CLAUDE_CODE_MAX_OUTPUT_TOKENS':'9000'})
    assert settings.config['kwargs']['reasoning_effort'] == 'max'
    assert settings.config['kwargs']['max_turns'] == 9
    assert settings.config['env']['CLAUDE_CODE_MAX_OUTPUT_TOKENS'] == '1234'
    assert settings.host_overrides == {'CLAUDE_CODE_MAX_OUTPUT_TOKENS':'1234'}
    assert settings.provenance['max_turns'] == 9
    assert settings.provenance['max_output_tokens'] == 1234
    inherited = configure_agent(args('claude-code',model='model'), {'CLAUDE_CODE_MAX_TURNS':'80','CLAUDE_CODE_MAX_OUTPUT_TOKENS':'9000'})
    assert inherited.provenance['max_turns'] == 80
    assert inherited.provenance['max_output_tokens'] == 9000


@pytest.mark.parametrize('agent_name', AGENTS)
def test_all_130_task_policies_preserved_for_each_real_agent(agent_name):
    agent = AgentConfig(name=agent_name,extra_allowed_hosts=['model.example.invalid'])
    for path in (ROOT/'tasks').rglob('task.toml'):
        data=tomllib.loads(path.read_text());before=TaskConfig.model_validate(data)
        original=resolve_trial_network_plan(before,agent,EnvironmentConfig(type='docker'),None,verifier_mode=resolve_task_verifier_mode(before))
        prepare_agent_install_network(data, agent_name)
        _, prepared=native_config(data)
        effective=resolve_trial_network_plan(prepared,agent,EnvironmentConfig(type='docker'),None,verifier_mode=resolve_task_verifier_mode(prepared))
        assert effective.agent_phase == original.agent_phase, path
        assert effective.verifier_phase == original.verifier_phase, path
        assert effective.verifier_env_baseline == original.verifier_env_baseline, path
        assert set(effective.agent_env_baseline.allowed_hosts)==set(INSTALL_HOSTS[agent_name])
        assert prepared.agent.timeout_sec==43200
        assert '/app' in prepared.artifacts


@pytest.mark.parametrize('agent_name,model', [(name,'model-fixture') for name in AGENTS])
def test_real_harbor_run_commands_and_connections_are_generated_without_execution(tmp_path,agent_name,model):
    settings=configure_agent(args(agent_name,model=model,base_url='https://custom.example/v1',reasoning_effort='high',
        grok_api_backend='responses'if agent_name=='grok-build'else None),{'TCSEXAM_API_KEY':SECRET})
    captured=[]
    async def capture(*a,**kw):
        captured.append(kw);return SimpleNamespace(return_code=0,stdout='',stderr='')
    with patch.dict(os.environ,{'TCSEXAM_API_KEY':SECRET},clear=True):
        agent=AgentFactory.create_agent_from_config(AgentConfig(**settings.config),tmp_path)
        agent.exec_as_agent=capture
        agent.exec_as_root=capture
        # These transfer a generated config file through a real container API.
        # Inspect their pure generated content above/below instead of any IO.
        if agent_name=='codex':
            assert agent._build_effective_config('https://custom.example/v1')['openai_base_url']=='https://custom.example/v1'
            agent._upload_effective_config=AsyncMock()
        elif agent_name=='claude-code':
            assert agent._resolve_auth_env()['ANTHROPIC_BASE_URL']=='https://custom.example/v1'
            agent._upload_base_settings=AsyncMock()
        asyncio.run(agent.run('Synthetic instruction',SimpleNamespace(default_user='agent'),AgentContext()))
    commands='\n'.join(x.get('command','')for x in captured)
    assert {'kimi-code':'kimi ','claude-code':'claude --verbose','codex':'codex exec','grok-build':'grok --no-auto-update'}[agent_name] in commands
    if agent_name!='kimi-code':assert 'reasoning' in commands or '--effort high' in commands
    assert any(x.get('env',{}).get({'kimi-code':'KIMI_MODEL_API_KEY','claude-code':'ANTHROPIC_API_KEY','codex':'OPENAI_API_KEY','grok-build':'XAI_API_KEY'}[agent_name])==SECRET for x in captured) or agent_name=='kimi-code'
    assert SECRET not in commands


@pytest.mark.parametrize('agent_name',AGENTS)
def test_prepare_records_actual_agent_and_keeps_secrets_out_of_all_generated_files(tmp_path,monkeypatch,agent_name):
    monkeypatch.setenv('TCSEXAM_API_KEY',SECRET)
    output=tmp_path/'job.json'
    argv=['prepare','--root',str(ROOT),'--suite','lite','--task','discrete-bidding-games','--agent',agent_name,
          '--model','model-fixture','--output',str(output)]
    assert main(argv)==0
    job=json.loads(output.read_text());meta=json.loads(output.with_suffix('.selection.json').read_text())
    JobConfig.model_validate(job)
    assert job['agents'][0]['name']==meta['agent']==agent_name
    assert job['agents'][0]['override_timeout_sec']==meta['agent_timeout_sec']==43200
    assert job['timeout_multiplier']==1
    assert meta['model']=='model-fixture'
    if agent_name!='kimi-code':assert meta['agent_version'] is None and meta['max_context_tokens'] is None
    for path in tmp_path.rglob('*'):
        if path.is_file():assert SECRET not in path.read_text(errors='replace')


@pytest.mark.parametrize('value',['','   ','\n'])
def test_empty_cache_uses_home_default_and_does_not_use_current_directory(monkeypatch,value):
    monkeypatch.setenv('TCSEXAM_CACHE',value)
    assert cache_path(Namespace(cache=None))==Path.home()/'.cache/tcsexam'
    assert cache_path(Namespace(cache=Path('explicit-cache')))==Path('explicit-cache')


@pytest.mark.parametrize('agent_name,key', [('kimi-code','KIMI_MODEL_API_KEY'),('claude-code','ANTHROPIC_API_KEY'),('codex','OPENAI_API_KEY'),('grok-build','XAI_API_KEY')])
def test_run_uses_selected_native_credentials_and_passes_claude_host_limit(tmp_path,agent_name,key):
    output=tmp_path/'job.json'
    argv=['run','--root',str(ROOT),'--suite','lite','--task','discrete-bidding-games',
          '--agent',agent_name,'--model','model-fixture','--output',str(output),'--yes']
    if agent_name=='claude-code':argv+=['--max-output-tokens','1234']
    with patch.dict(os.environ,{key:SECRET,'TCSEXAM_CACHE':'   '},clear=True), \
         patch('tcsexam.setup.setup_selection',return_value={}), \
         patch('tcsexam.cli.doctor',return_value=0), \
         patch('tcsexam.cli.subprocess.call',return_value=0) as launch:
        assert main(argv)==0
    command=launch.call_args.args[0];env=launch.call_args.kwargs['env']
    assert command[-1]=='--yes'
    assert env['TCSEXAM_CACHE']==str(Path.home()/'.cache/tcsexam')
    job=json.loads(output.read_text());assert job['agents'][0]['name']==agent_name
    assert job['agents'][0]['env'][key]=='${'+key+'}'
    if agent_name=='claude-code':assert env['CLAUDE_CODE_MAX_OUTPUT_TOKENS']=='1234'
    assert SECRET not in output.read_text()


def test_missing_run_key_fails_before_setup_or_any_docker_command(tmp_path):
    with patch.dict(os.environ,{},clear=True), patch('tcsexam.setup.setup_selection') as setup:
        with pytest.raises(SystemExit) as error:
            main(['run','--root',str(ROOT),'--suite','lite','--task','discrete-bidding-games',
                  '--agent','codex','--model','fixture','--output',str(tmp_path/'job.json')])
        assert error.value.code == 2
    setup.assert_not_called()


def test_doctor_reports_selected_agent_and_key_presence_without_contacting_provider(tmp_path):
    from tcsexam.diagnostics import prerequisites
    _,rows=selection(ROOT,'lite',task='discrete-bidding-games')
    actual=args('codex',model='fixture',cache=tmp_path/'cache',artifacts=None,image_map=None)
    with patch.dict(os.environ,{'OPENAI_API_KEY':SECRET},clear=True), \
         patch('tcsexam.diagnostics.host_support_targets',return_value=[]):
        report=prerequisites(ROOT,rows,actual)
    assert report['agent_configuration']['ok'] is True
    assert report['agent_configuration']['agent']=='codex'
    assert report['agent_configuration']['credential_environment_variable']=='OPENAI_API_KEY'
    assert SECRET not in json.dumps(report)
    with patch.dict(os.environ,{},clear=True),patch('tcsexam.diagnostics.host_support_targets',return_value=[]):
        report=prerequisites(ROOT,rows,actual)
    assert report['agent_configuration']['ok'] is False
    assert any(x['kind']=='agent_configuration'for x in report['blockers'])


def test_empty_cache_is_resolved_for_resources_and_source_inputs_CLI(tmp_path):
    with patch.dict(os.environ,{'TCSEXAM_CACHE':''}), \
         patch('tcsexam.resources.prepare_resource',return_value=tmp_path/'data') as prepare:
        assert main(['resources','--root',str(ROOT),'--resource','fixture'])==0
        assert prepare.call_args.args[2].expanduser()==Path.home()/'.cache/tcsexam'
    with patch.dict(os.environ,{'TCSEXAM_CACHE':'   '}), \
         patch('tcsexam.source_inputs.prepare_source_inputs',return_value={}) as prepare:
        assert main(['source-inputs','--root',str(ROOT)])==0
        assert prepare.call_args.args[1]==Path.home()/'.cache/tcsexam'


@pytest.mark.parametrize('agent_name',AGENTS)
def test_installer_is_harbor_implementation_and_requested_version_is_used(tmp_path,agent_name):
    settings=configure_agent(args(agent_name,model='fixture',agent_version='0.43.1'),{})
    calls=[]
    async def capture(*a,**kw):
        calls.append(kw.get('command',''));return SimpleNamespace(return_code=0,stdout='',stderr='')
    agent=AgentFactory.create_agent_from_name(AgentName(agent_name),tmp_path,model_name='fixture',**settings.config['kwargs'])
    agent.exec_as_agent=capture;agent.exec_as_root=capture
    agent.ensure_system_dependencies=AsyncMock()
    if agent_name=='codex':agent._installed_codex_satisfies_version=AsyncMock(return_value=False)
    if agent_name=='claude-code':agent._installed_claude_satisfies_version=AsyncMock(return_value=False)
    asyncio.run(agent.install(SimpleNamespace(default_user='agent')))
    commands='\n'.join(calls)
    assert '0.43.1' in commands
    expected={'kimi-code':'@moonshot-ai/kimi-code@0.43.1','claude-code':'https://downloads.claude.ai/claude-code-releases/bootstrap.sh','codex':'@openai/codex@0.43.1','grok-build':'https://x.ai/cli/install.sh'}
    assert expected[agent_name] in commands
