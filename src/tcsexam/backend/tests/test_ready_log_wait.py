"""A diagnostic control read must not prevent tunnel readiness or cancellation."""
import asyncio
import time
from types import SimpleNamespace

import pytest

from tcsexam.backend import sessions_base
from tcsexam.backend.sessions_base import JudgeBootError, JudgeSessionStore


class Tunnels:
    def __init__(self):
        self.connected = asyncio.Event()

    async def wait_connected(self, app_name, timeout):
        try:
            await asyncio.wait_for(self.connected.wait(), timeout)
            return True
        except asyncio.TimeoutError:
            return False

    async def close(self, app_name):
        pass


class HangingLog:
    def __init__(self):
        self.started = asyncio.Event()
        self.cancelled = asyncio.Event()

    async def read_text(self, path):
        self.started.set()
        try:
            await asyncio.Event().wait()
        finally:
            self.cancelled.set()


def wait_ready(tunnels, ctrl, timeout):
    store = SimpleNamespace(cfg=SimpleNamespace(work_dir='/unused'), _tunnels=tunnels)
    return JudgeSessionStore._wait_tunnel_or_boot_failure(
        store, SimpleNamespace(app_name='worker'), ctrl, timeout
    )


def test_ready_interrupts_pending_log_read(monkeypatch):
    monkeypatch.setattr(sessions_base, '_AGENT_LOG_POLL_SECONDS', 0.01)

    async def scenario():
        tunnels, ctrl = Tunnels(), HangingLog()
        pending = asyncio.create_task(wait_ready(tunnels, ctrl, 10))
        await asyncio.wait_for(ctrl.started.wait(), 0.2)
        tunnels.connected.set()
        assert await asyncio.wait_for(pending, 0.2)
        assert ctrl.cancelled.is_set()

    asyncio.run(scenario())


def test_log_read_cannot_exceed_remaining_ready_budget(monkeypatch):
    monkeypatch.setattr(sessions_base, '_AGENT_LOG_POLL_SECONDS', 0.01)

    async def scenario():
        ctrl = HangingLog()
        started = time.monotonic()
        assert not await asyncio.wait_for(wait_ready(Tunnels(), ctrl, 0.05), 0.2)
        assert time.monotonic() - started < 0.2
        assert ctrl.started.is_set() and ctrl.cancelled.is_set()

    asyncio.run(scenario())


def test_cancel_during_log_read_releases_both_waiters(monkeypatch):
    monkeypatch.setattr(sessions_base, '_AGENT_LOG_POLL_SECONDS', 0.01)

    async def scenario():
        ctrl = HangingLog()
        pending = asyncio.create_task(wait_ready(Tunnels(), ctrl, 10))
        await asyncio.wait_for(ctrl.started.wait(), 0.2)
        pending.cancel()
        with pytest.raises(asyncio.CancelledError):
            await pending
        assert ctrl.cancelled.is_set()
        assert asyncio.all_tasks() == {asyncio.current_task()}

    asyncio.run(scenario())


def test_boot_fatal_still_fails_fast(monkeypatch):
    monkeypatch.setattr(sessions_base, '_AGENT_LOG_POLL_SECONDS', 0.01)

    async def scenario():
        class Log:
            async def read_text(self, path):
                return 'BOOT-FATAL: required file missing\n'

        with pytest.raises(JudgeBootError, match='required file missing'):
            await asyncio.wait_for(wait_ready(Tunnels(), Log(), 10), 0.2)

    asyncio.run(scenario())


def test_two_sessions_register_all_workers_when_log_reads_hang(monkeypatch):
    monkeypatch.setattr(sessions_base, '_AGENT_LOG_POLL_SECONDS', 0.01)

    async def scenario():
        registered = []
        tunnels = [Tunnels() for _ in range(20)]
        controls = [HangingLog() for _ in range(20)]

        async def boot(i):
            assert await wait_ready(tunnels[i], controls[i], 10)
            registered.append(i)

        async def group(start):
            await asyncio.gather(*(boot(i) for i in range(start, start + 10)))
            return 'ready'

        groups = [asyncio.create_task(group(start)) for start in (0, 10)]
        await asyncio.wait_for(asyncio.gather(*(c.started.wait() for c in controls)), 0.2)
        for tunnel in tunnels:
            tunnel.connected.set()
        assert await asyncio.wait_for(asyncio.gather(*groups), 0.2) == ['ready', 'ready']
        assert len(registered) == 20
        assert all(c.cancelled.is_set() for c in controls)

    asyncio.run(scenario())


def test_sharded_sessions_register_when_launch_exit_notification_is_missing():
    from tcsexam.backend.config import Config
    from tcsexam.backend.sessions import JudgeSessionStore as GroupStore
    from test_async_create import FakeExecutor

    async def scenario():
        executor = FakeExecutor()
        original_create = executor.create_sandbox
        controls = []
        all_started = asyncio.Event()

        class Control(HangingLog):
            async def write_bytes(self, *args, **kwargs):
                pass

            async def run(self, *args, **kwargs):
                controls.append(self)
                if len(controls) == 20:
                    all_started.set()
                try:
                    await asyncio.Event().wait()  # remote shell exited; no SDK exit frame
                finally:
                    self.launch_cancelled = True

        async def create(*args, **kwargs):
            worker = await original_create(*args, **kwargs)
            worker.ctrl = Control()
            worker.ctrl.launch_cancelled = False
            return worker

        executor.create_sandbox = create
        tunnels = Tunnels()
        store = GroupStore(executor, Config())
        store.attach_tunnels(tunnels)
        sessions = [store.begin_create_group(None, f'registry/task-{i}', None, None, None, 10)
                    for i in range(2)]
        await asyncio.wait_for(all_started.wait(), 0.5)
        tunnels.connected.set()
        await asyncio.wait_for(asyncio.gather(*(
            store._provision_tasks[s.session_id] for s in sessions
        )), 0.5)
        assert [s.status for s in sessions] == ['ready', 'ready']
        assert len(executor.registered) == 20
        assert all(c.launch_cancelled for c in controls)
        assert all(w.deleted == 0 for w in executor.sandboxes)
        for session in sessions:
            await store.destroy(session.session_id)

    asyncio.run(scenario())


def test_missing_exit_and_missing_ready_still_exhausts_original_budget(monkeypatch):
    from tcsexam.backend.config import Config, BackendConfig, JudgeSessionsConfig
    from tcsexam.backend.sessions import JudgeSessionStore as GroupStore
    from test_async_create import FakeExecutor

    monkeypatch.setattr(sessions_base, '_AGENT_LOG_POLL_SECONDS', 0.005)

    async def scenario():
        executor = FakeExecutor()
        original_create = executor.create_sandbox
        ctrl = HangingLog()
        cancelled = asyncio.Event()

        async def run(*args, **kwargs):
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        ctrl.run = run
        ctrl.write_bytes = lambda *args, **kwargs: asyncio.sleep(0)

        async def create(*args, **kwargs):
            worker = await original_create(*args, **kwargs)
            worker.ctrl = ctrl
            return worker

        executor.create_sandbox = create
        config = Config(backend=BackendConfig(judge_sessions=JudgeSessionsConfig(
            ready_timeout_seconds=0.02, shard_boot_retries=0)))
        store = GroupStore(executor, config)
        store.attach_tunnels(Tunnels())
        session = store.begin_create_group(None, 'registry/no-ready', None, None, None, 1)
        await asyncio.wait_for(store._provision_tasks[session.session_id], 0.3)
        assert session.status == 'failed'
        assert 'did not connect within 0.02s' in session.error
        assert cancelled.is_set() and ctrl.cancelled.is_set()
        assert not executor.registered
        assert executor.sandboxes[0].deleted == 1

    asyncio.run(scenario())


def test_launcher_error_before_ready_propagates():
    async def scenario():
        async def run(*args, **kwargs):
            raise RuntimeError('launch transport failed')

        store = JudgeSessionStore(None, sessions_base.JudgeSessionsConfig(),
                                  sessions_base.BaseServiceConfig())
        store.attach_tunnels(Tunnels())
        with pytest.raises(RuntimeError, match='launch transport failed'):
            await store._launch_agent_and_wait(
                SimpleNamespace(app_name='worker'), SimpleNamespace(run=run), 'unused', 10)
        assert asyncio.all_tasks() == {asyncio.current_task()}

    asyncio.run(scenario())
