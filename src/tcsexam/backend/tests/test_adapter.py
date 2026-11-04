"""Adapter lifecycle tests (stub factory, in-memory workers): creation
retry/backoff, the long-lived table, stop_app teardown and the agent.log
recovery, the warm-pool discard hook.
"""
from __future__ import annotations

import asyncio
import logging
import time
import types

import pytest

from tcsexam.backend.adapter import BasePlatformAdapter


class ResourceExhaustedError(Exception):
    """Name matches a transient platform error (mapped by name)."""


class AuthenticationError(Exception):
    """Name matches a non-transient platform error."""


class FakeCtrl:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    async def read_text(self, path: str) -> str:
        if path not in self.files:
            raise FileNotFoundError(path)
        return self.files[path].decode()


class FakeWorker:
    def __init__(self) -> None:
        self.ctrl = FakeCtrl()
        self.deleted = 0

    async def delete(self) -> None:
        self.deleted += 1


class FakeFactory:
    def __init__(self, fail_sequence: list[BaseException] | None = None) -> None:
        self.calls: list[dict] = []
        self.workers: list[FakeWorker] = []
        self.fail_sequence = list(fail_sequence or [])

    async def __call__(self, **kwargs):
        self.calls.append(kwargs)
        if self.fail_sequence:
            raise self.fail_sequence.pop(0)
        worker = FakeWorker()
        self.workers.append(worker)
        return worker


class _Adapter(BasePlatformAdapter):
    """BasePlatformAdapter driven by the in-memory fake factory."""

    def __init__(self, factory, **kwargs) -> None:
        defaults = dict(
            create_retries=1,
            create_retry_delay_seconds=0.01,
            ready_timeout_seconds=30.0,
            default_ttl_seconds=7200.0,
            default_spec={"cpu_count": 4, "memory_mb": 8192},
        )
        defaults.update(kwargs)
        super().__init__(**defaults)
        self.factory = factory

    async def _create_worker(self, profile, image_url, **kwargs):
        return await self.factory(profile=profile, image_url=image_url, **kwargs)


def _adapter(factory, **kwargs) -> _Adapter:
    return _Adapter(factory, **kwargs)


def test_create_sandbox_happy_path() -> None:
    factory = FakeFactory()
    adapter = _adapter(factory)
    worker = asyncio.run(adapter.create_sandbox("cpu-pool", "registry/image:1"))
    assert worker is factory.workers[0]
    call = factory.calls[0]
    assert call["profile"] == "cpu-pool"
    assert call["image_url"] == "registry/image:1"
    assert call["ttl_seconds"] == 7200  # the default TTL
    assert call["ready_timeout_seconds"] == 30
    assert call["resources"].cpu_count == 4  # the default spec


def test_create_sandbox_overrides() -> None:
    factory = FakeFactory()
    adapter = _adapter(factory)
    asyncio.run(
        adapter.create_sandbox(
            "p", "img", ttl_seconds=600, spec={"cpu_count": 8, "memory_mb": 16384}
        )
    )
    call = factory.calls[0]
    assert call["ttl_seconds"] == 600
    assert call["resources"].cpu_count == 8


def test_transient_creation_failure_retried_with_backoff() -> None:
    factory = FakeFactory(
        [ResourceExhaustedError("busy"), ResourceExhaustedError("still busy")]
    )
    adapter = _adapter(factory, create_retries=2)
    t0 = time.monotonic()
    worker = asyncio.run(adapter.create_sandbox("p", "img"))
    elapsed = time.monotonic() - t0
    assert worker is factory.workers[0]
    assert len(factory.calls) == 3
    assert elapsed >= 0.01 * (1 + 2)  # base * 2^attempt after attempts 0 and 1


def test_persistent_transient_failure_reraises() -> None:
    factory = FakeFactory([ResourceExhaustedError("busy"), ResourceExhaustedError("busy")])
    adapter = _adapter(factory, create_retries=1)
    with pytest.raises(ResourceExhaustedError):
        asyncio.run(adapter.create_sandbox("p", "img"))
    assert len(factory.calls) == 2


def test_non_transient_failure_not_retried() -> None:
    factory = FakeFactory([AuthenticationError("bad token")])
    adapter = _adapter(factory, create_retries=3)
    with pytest.raises(AuthenticationError):
        asyncio.run(adapter.create_sandbox("p", "img"))
    assert len(factory.calls) == 1


def test_legacy_private_alias() -> None:
    factory = FakeFactory()
    adapter = _adapter(factory)
    worker = asyncio.run(adapter._create_sandbox("p", "img"))
    assert worker is factory.workers[0]


def test_create_sandbox_ready_timeout_override() -> None:
    factory = FakeFactory()
    adapter = _adapter(factory)  # ready_timeout_seconds=30.0
    # A per-call override (routed readiness budget) reaches the creation ...
    asyncio.run(adapter.create_sandbox("p", "img", ready_timeout_seconds=99))
    assert factory.calls[0]["ready_timeout_seconds"] == 99
    # ... also through the legacy alias (it is the same function) ...
    asyncio.run(adapter._create_sandbox("p", "img", ready_timeout_seconds=55))
    assert factory.calls[1]["ready_timeout_seconds"] == 55
    # ... while None keeps the adapter's configured value.
    asyncio.run(adapter.create_sandbox("p", "img", ready_timeout_seconds=None))
    assert factory.calls[2]["ready_timeout_seconds"] == 30


def test_long_lived_table_and_stop_app(caplog) -> None:
    factory = FakeFactory()
    adapter = _adapter(factory)
    worker = asyncio.run(adapter.create_sandbox("p", "img"))
    adapter.register_long_lived("app-1", worker)
    assert adapter.sandbox_for_app("app-1") is worker

    worker.ctrl.files["/tcsexam-backend/agent.log"] = b"boot\nfinal-words-marker\n"
    with caplog.at_level(logging.INFO, logger=adapter.logger_name):
        asyncio.run(adapter.stop_app("app-1"))
    assert worker.deleted == 1
    assert adapter.sandbox_for_app("app-1") is None
    assert "agent.log tail for app-1" in caplog.text
    assert "final-words-marker" in caplog.text

    # stop_app is idempotent.
    asyncio.run(adapter.stop_app("app-1"))
    assert worker.deleted == 1


def test_stop_app_recovers_from_unreadable_log(caplog) -> None:
    factory = FakeFactory()
    adapter = _adapter(factory)
    worker = asyncio.run(adapter.create_sandbox("p", "img"))
    adapter.register_long_lived("app-2", worker)
    with caplog.at_level(logging.INFO, logger=adapter.logger_name):
        asyncio.run(adapter.stop_app("app-2"))
    assert worker.deleted == 1
    assert "could not read agent.log for app-2" in caplog.text


def test_stop_app_kicks_pool_discard() -> None:
    factory = FakeFactory()
    adapter = _adapter(factory)
    discarded: list[str] = []
    adapter.judge_pool = types.SimpleNamespace(discard=discarded.append)
    worker = asyncio.run(adapter.create_sandbox("p", "img"))
    adapter.register_long_lived("app-3", worker)
    asyncio.run(adapter.stop_app("app-3"))
    assert discarded == ["app-3"]


def test_subclass_logger_name(caplog) -> None:
    class NamedAdapter(_Adapter):
        logger_name = "project.adapter"

    factory = FakeFactory()
    adapter = NamedAdapter(factory)
    worker = asyncio.run(adapter.create_sandbox("p", "img"))
    adapter.register_long_lived("app-4", worker)
    with caplog.at_level(logging.INFO, logger="project.adapter"):
        asyncio.run(adapter.stop_app("app-4"))
    assert "could not read agent.log for app-4" in caplog.text
