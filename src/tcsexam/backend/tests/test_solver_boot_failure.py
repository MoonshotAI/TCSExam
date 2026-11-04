"""A terminal worker boot failure aborts the shard group and frees workers."""
import asyncio
from tcsexam.backend.config import Config, BackendConfig, JudgeSessionsConfig
from tcsexam.backend.sessions import JudgeSessionStore
from test_async_create import FakeExecutor, FakeTunnels


def test_sharded_worker_boot_failure_does_not_wait_for_readiness_deadline():
    async def scenario():
        executor = FakeExecutor()
        config = Config(backend=BackendConfig(judge_sessions=JudgeSessionsConfig(
            ready_timeout_seconds=1800, shard_boot_retries=3)))
        store = JudgeSessionStore(executor, config)
        store.attach_tunnels(FakeTunnels(mode='refuse'))
        session = store.begin_create_group(None, 'registry.example.com/worker:v1', None, None, None, 2)
        async def finish():
            while len(executor.sandboxes) < 2:
                await asyncio.sleep(0)
            for worker in executor.sandboxes:
                worker.ctrl.files[f'{store.cfg.work_dir}/agent.log'] = b'BOOT-FATAL: public instance tree missing\n'
            await store._provision_tasks[session.session_id]
        await asyncio.wait_for(finish(), 3)
        assert session.status == 'failed'
        assert 'judge server failed during boot: public instance tree missing' in session.error
        assert 'please try again' not in session.error
        assert len(executor.calls) == 2
        assert all(worker.deleted == 1 for worker in executor.sandboxes)
        assert not executor.registered
    asyncio.run(scenario())


def test_shard_agent_receives_owning_run_id():
    import json
    async def scenario():
        executor=FakeExecutor();store=JudgeSessionStore(executor,Config())
        store.attach_tunnels(FakeTunnels(mode='connect'))
        session=store.begin_create_group(None,'registry.example.com/worker:v1',None,None,None,2,run_id='accepted-run-261029')
        await store._provision_tasks[session.session_id]
        assert session.status=='ready'
        for worker in executor.sandboxes:
            config=json.loads(worker.ctrl.files[f'{store.cfg.work_dir}/agent_config.json'])
            assert config['run_id']=='accepted-run-261029'
        await store.destroy(session.session_id)
    asyncio.run(scenario())


def test_worker_agent_sends_run_identity_to_required_auth(monkeypatch,tmp_path):
    import json
    from aiohttp import web,ClientSession
    from tcsexam.backend.agent_files import judge_session_agent as agent
    from tcsexam.backend.config import BaseServiceConfig
    from tcsexam.backend.auth import make_auth_middleware
    config={'app_name':'worker','service_ws_url':'ws://unused/v1/tunnel/worker','command':'','token_id':'test-id','token_secret':'test-secret','run_id':'accepted-run-261029','agent_name':'attributed-agent'}
    (tmp_path/'agent_config.json').write_text(json.dumps(config));monkeypatch.chdir(tmp_path)
    captured={}
    def loop(config,proc,port,read_timeout,app_name,ready_label,headers):
        captured.update(headers);return 0
    monkeypatch.setattr(agent,'_tunnel_serve_loop',loop)
    assert agent.main()==0
    assert captured['X-TCSEXAM-Agent-Name']=='attributed-agent'
    async def scenario():
        app=web.Application(middlewares=[make_auth_middleware()]);app['config']=BaseServiceConfig(token_id='test-id',token_secret='test-secret',run_id_mode='required')
        async def endpoint(request):return web.json_response({'run_id':request['run_id']})
        app.router.add_get('/v1/tunnel/worker',endpoint)
        runner=web.AppRunner(app);await runner.setup();site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
        port=site._server.sockets[0].getsockname()[1]
        try:
            async with ClientSession() as client:
                async with client.get(f'http://127.0.0.1:{port}/v1/tunnel/worker',headers=captured) as response:
                    assert response.status==200
                    assert await response.json()=={'run_id':'accepted-run-261029'}
                async with client.get(f'http://127.0.0.1:{port}/v1/tunnel/worker',headers={k:v for k,v in captured.items() if k!='X-TCSEXAM-Run-Id'}) as response:
                    assert response.status==400
        finally:await runner.cleanup()
    asyncio.run(scenario())
