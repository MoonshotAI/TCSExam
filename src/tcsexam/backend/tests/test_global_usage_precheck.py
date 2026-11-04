"""Global usage pre-check tests (dual-dimension real-time accounting; no
service, no real workers).

Covers:
- config: max_sandbox_memory_mb parsing; the session-level quotas default to
  0 (disabled)
- session quotas disabled by default (a big shape x big n_shards passes the
  static lines), re-enabled by a positive value (400 wording)
- the dual-dimension pre-check: memory binds first (8 GiB/worker default),
  instances second, under both passes
- in-flight accounting: charged on both dimensions at create-accept, back to
  zero once every shard settles
- ready-flip: min_ready_ratio=1.0 fails the whole session on any dead shard
  (partial provisioning never produces a score); the TTL anchors at ready
  (queueing must not eat the judging-life budget); the degraded-ready
  mechanism stays available below 1.0
"""
from __future__ import annotations

import asyncio
import time
from pathlib import Path

import pytest

from tcsexam.backend.config import (
    BackendConfig,
    Config,
    JudgeSessionsConfig,
)
from tcsexam.backend.sessions import (
    GlobalSandboxCapError,
    JudgeSessionStore,
)


def _config(state_dir, **backend_overrides) -> Config:
    judge_overrides = backend_overrides.pop("judge_sessions", {})
    judge = dict(max_sessions=64, shard_boot_retries=0, ready_timeout_seconds=0.1)
    judge.update(judge_overrides)
    return Config(
        host="127.0.0.1",
        port=0,
        public_base_url="http://test",
        token_id="t",
        token_secret="s",
        state_dir=Path(state_dir),
        backend=BackendConfig(
            judge_sessions=JudgeSessionsConfig(**judge),
            **backend_overrides,
        ),
    )


def test_config_defaults(tmp_path) -> None:
    cfg = _config(tmp_path)
    assert cfg.backend.max_sandbox_memory_mb == 32768000
    assert cfg.backend.judge_sessions.max_session_cpu_count == 0
    assert cfg.backend.judge_sessions.max_session_memory_mb == 0


def test_config_yaml_explicit_values(tmp_path) -> None:
    cfg = _config(
        tmp_path,
        max_sandboxes_global=50,
        max_sandbox_memory_mb=100000,
        judge_sessions={"max_session_cpu_count": 100, "max_session_memory_mb": 200000},
    )
    assert cfg.backend.max_sandboxes_global == 50
    assert cfg.backend.max_sandbox_memory_mb == 100000
    assert cfg.backend.judge_sessions.max_session_cpu_count == 100
    assert cfg.backend.judge_sessions.max_session_memory_mb == 200000


class _FakeExecutor:
    """Creates fake workers instantly; the attached tunnels refuse every
    connection so boots fail fast (ready_timeout 0.1s, no retries)."""

    def __init__(self) -> None:
        self.ready_timeout_seconds = 30.0

    async def create_sandbox(self, profile, image, *, ttl_seconds=None, spec=None, **kwargs):
        from types import SimpleNamespace

        ctrl = SimpleNamespace(
            write_bytes=lambda *a, **kw: asyncio.sleep(0),
            read_text=lambda *a, **kw: asyncio.sleep(0, result=""),
            run=lambda *a, **kw: asyncio.sleep(0, result=SimpleNamespace(stdout="")),
        )
        return SimpleNamespace(ctrl=ctrl, delete=lambda: asyncio.sleep(0))

    async def stop_app(self, app_name: str) -> None:
        pass

    def register_long_lived(self, app_name: str, worker) -> None:
        pass

    def long_lived_count(self) -> int:
        return 0

    def long_lived_memory_mb(self) -> int:
        return 0


class _RefuseTunnels:
    def __init__(self) -> None:
        self.closed: set[str] = set()

    async def wait_connected(self, app_name: str, timeout: float) -> bool:
        return False

    def is_connected(self, app_name: str) -> bool:
        return False

    def in_flight(self, app_name: str) -> int:
        return 0

    async def close(self, app_name: str) -> None:
        self.closed.add(app_name)


def _make_store(config) -> JudgeSessionStore:
    store = JudgeSessionStore(executor=_FakeExecutor(), config=config)
    store.attach_tunnels(_RefuseTunnels())
    return store


def _precheck_error(store, n_shards, resources=None, ttl=600.0, settle=False):
    """Run _register_group far enough to hit the accept-time checks; return
    the exception raised (or the session if accepted). With settle=True the
    group-create task is awaited (in-flight counters back to zero)."""
    async def go():
        try:
            session, task = store._register_group(
                "reg/x-judge:1", None, resources, ttl, n_shards
            )
            if settle:
                try:
                    await task
                except Exception:  # noqa: BLE001
                    pass
            return session
        except Exception as exc:  # noqa: BLE001
            return exc

    return asyncio.run(go())


def test_session_quota_disabled_by_default(tmp_path) -> None:
    # 100 shards x 32c is NOT stopped by the static per-session line.
    r = _precheck_error(_make_store(_config(tmp_path)), 100, {"cpu_count": 32, "memory_mb": 8192})
    assert not (isinstance(r, ValueError) and "session cpu total" in str(r))


def test_session_quota_reenabled_by_positive_value(tmp_path) -> None:
    cfg = _config(tmp_path, judge_sessions={"max_session_cpu_count": 100})
    r = _precheck_error(_make_store(cfg), 4, {"cpu_count": 32, "memory_mb": 8192})
    assert isinstance(r, ValueError) and "session cpu total" in str(r)


def test_precheck_passes_under_both_dimensions(tmp_path) -> None:
    cfg = _config(tmp_path, max_sandboxes_global=50, max_sandbox_memory_mb=100000)
    store = _make_store(cfg)
    r = _precheck_error(store, 2, {"memory_mb": 8192}, settle=True)
    assert not isinstance(r, GlobalSandboxCapError)
    if not isinstance(r, Exception):
        # After the (refused-tunnel) boots settle, both in-flight dimensions
        # are back to zero.
        assert store._inflight_shards == 0 and store._inflight_memory_mb == 0


def test_memory_dimension_binds_first(tmp_path) -> None:
    cfg = _config(tmp_path, max_sandboxes_global=50, max_sandbox_memory_mb=10000)
    r = _precheck_error(_make_store(cfg), 2, {"memory_mb": 8192})
    assert isinstance(r, GlobalSandboxCapError) and "16384" in str(r)


def test_instance_dimension_binds(tmp_path) -> None:
    cfg = _config(tmp_path, max_sandboxes_global=2, max_sandbox_memory_mb=999999999)
    r = _precheck_error(_make_store(cfg), 3, {"memory_mb": 1024})
    assert isinstance(r, GlobalSandboxCapError)


# --------------------------------------------------------------------------- #
# ready-flip: min_ready_ratio + TTL ready anchoring
# --------------------------------------------------------------------------- #
def _flip(tmp_path, n_shards, failed_indexes, queued_seconds=0.0, min_ready_ratio=None):
    """Flip semantics at group-create settle time: _boot_shard_with_retry
    no-op'd, failed_shards pre-set, _provision_group run directly.
    queued_seconds simulates provisioning-queue time (created/expires dialed
    into the past). Returns (session, flip_at)."""
    async def go():
        judge = {}
        if min_ready_ratio is not None:
            judge["min_ready_ratio"] = min_ready_ratio
        store = _make_store(_config(tmp_path, judge_sessions=judge))
        session, task = store._register_group(
            "reg/x-judge:1", None, {"memory_mb": 1024}, 3600.0, n_shards
        )
        task.cancel()
        try:
            await task
        except BaseException:  # noqa: BLE001
            pass
        session.created -= queued_seconds
        session.expires = session.created + 3600.0  # registration: expires = created + ttl

        async def _noop_boot(session, shard, image, payload_files, spec, ttl, gate):
            return None

        store._boot_shard_with_retry = _noop_boot
        session.failed_shards = {i: "boom" for i in failed_indexes}
        flip_at = time.time()
        await store._provision_group(
            session, "reg/x-judge:1", None, {"memory_mb": 1024}, 3600.0
        )
        return session, flip_at

    return asyncio.run(go())


def test_ratio_1_any_dead_shard_fails_the_whole_session(tmp_path) -> None:
    s, _ = _flip(tmp_path, 4, [2])
    assert s.status == "failed" and "judge session create failed" in (s.error or ""), \
        "ratio=1.0: one dead shard of four -> the whole session fails (no partial credit)"


def test_ttl_anchors_at_ready_not_created(tmp_path) -> None:
    s, flip_at = _flip(tmp_path, 4, [], queued_seconds=10800.0)
    assert s.status == "ready"
    # 3h of queueing: expires ~= ready+ttl (in the future), not created+ttl (past).
    assert abs(s.expires - (flip_at + 3600.0)) < 5.0 and s.expires > time.time()


def test_ttl_anchor_is_a_noop_without_queueing(tmp_path) -> None:
    s, flip_at = _flip(tmp_path, 4, [], queued_seconds=0.0)
    assert abs(s.expires - (s.created + 3600.0)) < 5.0


def test_degraded_ready_mechanism_kept_below_ratio_1(tmp_path) -> None:
    s, _ = _flip(tmp_path, 10, [7], min_ready_ratio=0.9)
    assert s.status == "ready" and len(s.failed_shards) == 1, \
        "ratio=0.9: one dead shard of ten -> degraded ready (floor 9)"
