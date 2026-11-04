"""Memory-accounting regression (261024 review fix): long_lived_memory_mb.

The review probe loaded the shipped minimal example adapter AS-IS and
registered a 4096 MiB worker: long_lived_count was 1 but
long_lived_memory_mb was 0 (the base class read a duck-chain the example
never provides). The fix: BasePlatformAdapter keeps the creation-time
resources (worker.resources authoritative when exposed, else the base's
own create record, else the legacy duck-chain), resolves them into the
accounting table at register time, and drops them at stop_app. Covers:

- the shipped example (docs/backend/examples/adapter_minimal.py), loaded
  by file path AS-IS: a 4096 MiB worker reports exactly 4096, then 0 after
  stop — the review probe's shape;
- the base class's own record path (a worker WITHOUT any resources
  metadata still accounts the create spec) and the worker.resources
  preference;
- LocalProcessAdapter (not a base subclass: keeps its own creation
  records, with the configured default spec for spec-less creates);
- the contract suite's memory_accounting check passes on local-test — a
  fixed-zero statistics method can no longer pass the self-check.
"""
from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tcsexam.backend.adapter import BasePlatformAdapter, WorkerResources  # noqa: E402
from tcsexam.backend.config import BackendConfig, Config, JudgeSessionsConfig  # noqa: E402
from tcsexam.backend.contracttest import run_contract_suite  # noqa: E402
from tcsexam.backend.testing.local_adapter import LocalProcessAdapter  # noqa: E402

_EXAMPLE = (
    Path(__file__).resolve().parents[4] / "docs" / "backend" / "examples" / "adapter_minimal.py"
)


def _load_minimal_adapter():
    """Import the shipped example by file path (docs/ is not a package)."""
    assert _EXAMPLE.is_file(), f"the shipped example moved: {_EXAMPLE}"
    spec = importlib.util.spec_from_file_location("tcsexam_adapter_minimal_example", _EXAMPLE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.make_adapter()


def test_minimal_example_adapter_accounts_4096() -> None:
    """The review probe's shape: the example adapter, a 4096 MiB worker."""
    adapter = _load_minimal_adapter()

    async def main() -> None:
        worker = await adapter.create_sandbox(
            "example-profile", "registry.example.com/example-judge:1",
            spec={"cpu_count": 2, "memory_mb": 4096},
        )
        assert adapter.long_lived_memory_mb() == 0
        adapter.register_long_lived("example-app", worker)
        assert adapter.long_lived_count() == 1
        assert adapter.long_lived_memory_mb() == 4096
        await adapter.stop_app("example-app")
        assert adapter.long_lived_count() == 0
        assert adapter.long_lived_memory_mb() == 0

    asyncio.run(main())


class _BareCtrl:
    async def read_text(self, path: str) -> str:
        raise FileNotFoundError(path)


class _BareWorker:
    """No resources metadata at all (the pre-fix blind spot)."""

    def __init__(self) -> None:
        self.name = "bare"
        self.ctrl = _BareCtrl()

    async def delete(self) -> None:
        pass


class _ResWorker(_BareWorker):
    """Exposes the optional worker.resources metadata member."""

    def __init__(self, resources: WorkerResources) -> None:
        super().__init__()
        self.resources = resources


class _FactoryAdapter(BasePlatformAdapter):
    def __init__(self, worker) -> None:
        super().__init__(create_retries=0, ready_timeout_seconds=30.0)
        self._worker = worker

    async def _create_worker(self, profile, image_url, **kwargs):
        return self._worker


def test_base_adapter_uses_its_create_record_for_bare_workers() -> None:
    adapter = _FactoryAdapter(_BareWorker())

    async def main() -> None:
        worker = await adapter.create_sandbox(
            "p", "img", spec={"cpu_count": 1, "memory_mb": 4096}
        )
        adapter.register_long_lived("app", worker)
        assert adapter.long_lived_memory_mb() == 4096, (
            "the base's own create record must account a metadata-less worker"
        )
        await adapter.stop_app("app")
        assert adapter.long_lived_memory_mb() == 0

    asyncio.run(main())


def test_base_adapter_prefers_worker_resources_attribute() -> None:
    adapter = _FactoryAdapter(_ResWorker(WorkerResources(cpu_count=1, memory_mb=2048)))

    async def main() -> None:
        # Created with a 4096 spec, but the worker exposes 2048: the
        # worker's own attribute is authoritative (a platform may account
        # differently from the request).
        worker = await adapter.create_sandbox(
            "p", "img", spec={"cpu_count": 1, "memory_mb": 4096}
        )
        adapter.register_long_lived("app", worker)
        assert adapter.long_lived_memory_mb() == 2048
        await adapter.stop_app("app")
        assert adapter.long_lived_memory_mb() == 0

    asyncio.run(main())


def _local_config(memory_mb: int) -> Config:
    return Config(
        state_dir=Path("/tmp/tcsexam-memory-accounting-test"),
        backend=BackendConfig(
            judge_sessions=JudgeSessionsConfig(
                spec={"cpu_count": 1, "memory_mb": memory_mb, "storage_mb": 1024}
            )
        ),
    )


def test_local_process_adapter_keeps_creation_records() -> None:
    adapter = LocalProcessAdapter(_local_config(512))

    async def main() -> None:
        explicit = await adapter.create_sandbox(
            "p", "img", spec={"cpu_count": 1, "memory_mb": 4096}
        )
        defaulted = await adapter.create_sandbox("p", "img")
        adapter.register_long_lived("explicit", explicit)
        adapter.register_long_lived("defaulted", defaulted)
        # The explicit spec wins for its worker; the spec-less create falls
        # back to the configured default spec (512).
        assert adapter.long_lived_memory_mb() == 4096 + 512
        await adapter.stop_app("explicit")
        assert adapter.long_lived_memory_mb() == 512
        await adapter.stop_app("defaulted")
        assert adapter.long_lived_memory_mb() == 0

    asyncio.run(main())


def test_contract_suite_memory_check_passes_on_local_test() -> None:
    """The self-check must not let a fixed-zero statistics method through."""
    adapter = LocalProcessAdapter(_local_config(512))
    results = asyncio.run(run_contract_suite(adapter))
    by_name = {r.name: r for r in results}
    assert "memory_accounting" in by_name, "the contract suite grew a memory check"
    assert by_name["memory_accounting"].ok, by_name["memory_accounting"].detail
