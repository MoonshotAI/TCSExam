"""Adapter contract suite: run a platform-adapter implementation through the
contract checks the session stores rely on (see ``adapter.py``'s module
docstring for the contract itself).

Two consumers share this one caliber:

* the CLI — ``python -m tcsexam.backend.contracttest --adapter module:attr
  [--config PATH] [--image IMAGE] [--profile PROFILE]`` prints one line per
  check and exits nonzero on any failure (``--adapter docker`` exercises the
  bundled Docker adapter; ``--adapter local-test`` exercises the local-process
  test double). ``--image``/``--profile``
  default to placeholders: the default run only verifies contract BEHAVIOR,
  so self-checking a production adapter should pass a real, pullable image
  and the profile the platform expects;
* the pytest acceptance test ``tests/test_b1_adapter_contract.py``.

The checks (creation honoring the request verbatim, file preparation,
command start, status diagnostics, memory accounting, idempotent
stop/delete, creation-failure cleanup, scoped cleanup) are intentionally
platform-neutral: they never require a real judging boot, only the
adapter's own machinery.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from typing import Any

from .adapter import (
    _REQUIRED_MEMBERS,
    BasePlatformAdapter,
    WorkerResources,
    load_adapter,
)
from .config import Config

__all__ = ["CheckResult", "run_contract_suite", "main"]


@dataclass
class CheckResult:
    """One contract-check outcome (``skipped`` = the check does not apply to
    this adapter shape, e.g. the retry-loop probe on an adapter that does
    not subclass BasePlatformAdapter)."""

    name: str
    ok: bool
    detail: str = ""
    skipped: bool = False


class _Recorder:
    """Boundary recorder: wraps ``create_sandbox`` to capture exactly what
    the store would hand the adapter, and — for BasePlatformAdapter
    subclasses — ``_create_worker`` to capture what the retry layer
    forwards. Both are restored afterwards."""

    def __init__(self, adapter: Any) -> None:
        self.adapter = adapter
        self.create_calls: list[dict] = []
        self.worker_calls: list[dict] = []
        self._orig_create = None
        self._orig_worker = None

    def __enter__(self) -> "_Recorder":
        self._orig_create = self.adapter.create_sandbox

        async def _record_create(profile, image_url, **kwargs):
            self.create_calls.append(
                {"profile": profile, "image_url": image_url, **kwargs}
            )
            return await self._orig_create(profile, image_url, **kwargs)

        self.adapter.create_sandbox = _record_create
        if isinstance(self.adapter, BasePlatformAdapter):
            self._orig_worker = self.adapter._create_worker

            async def _record_worker(profile, image_url, **kwargs):
                self.worker_calls.append(
                    {"profile": profile, "image_url": image_url, **kwargs}
                )
                return await self._orig_worker(profile, image_url, **kwargs)

            self.adapter._create_worker = _record_worker
        return self

    def __exit__(self, *exc) -> None:
        self.adapter.create_sandbox = self._orig_create
        if self._orig_worker is not None:
            self.adapter._create_worker = self._orig_worker


async def run_contract_suite(
    adapter: Any,
    *,
    image: str = "registry.example.com/contract-judge:1",
    profile: str = "contract-profile",
) -> list[CheckResult]:
    """Run every contract check against one adapter instance.

    The adapter is used as-is (it may create real resources — point it at a
    test environment). Every created worker is destroyed inside the suite.
    ``image``/``profile`` are what the checks pass to ``create_sandbox``;
    the defaults are placeholders that only verify contract BEHAVIOR — a
    self-check of a production adapter should pass a real, pullable image
    and the profile the platform expects.
    """
    results: list[CheckResult] = []

    def record(name: str, ok: bool, detail: str = "", skipped: bool = False) -> None:
        results.append(CheckResult(name=name, ok=ok, detail=detail, skipped=skipped))

    # ------------------------------------------------------------------ #
    # 1. Surface: every member the stores call is present.
    # ------------------------------------------------------------------ #
    missing = [name for name in _REQUIRED_MEMBERS if not hasattr(adapter, name)]
    record(
        "surface",
        not missing,
        "all required members present" if not missing else f"missing: {', '.join(missing)}",
    )
    if missing:
        return results  # nothing else can run

    # ------------------------------------------------------------------ #
    # 2. Creation honors the request verbatim (image / resources / ttl /
    #    identity tags), and each worker carries a unique identifier.
    # ------------------------------------------------------------------ #
    spec = {"cpu_count": 3, "memory_mb": 4096, "storage_mb": 8192}
    labels = {"run_id": "contract-run", "token_id": "contract"}
    worker = None
    try:
        with _Recorder(adapter) as rec:
            worker = await adapter.create_sandbox(
                profile,
                image,
                ttl_seconds=4321,
                spec=dict(spec),
                ready_timeout_seconds=222,
                group_name="contract--group",
                labels=dict(labels),
            )
        boundary = rec.create_calls[0]
        verbatim = (
            boundary.get("profile") == profile
            and boundary.get("image_url") == image
            and boundary.get("ttl_seconds") == 4321
            and boundary.get("spec") == spec
            and boundary.get("ready_timeout_seconds") == 222
            and boundary.get("group_name") == "contract--group"
            and boundary.get("labels") == labels
        )
        detail = (
            "create_sandbox received profile/image/ttl/spec/ready_timeout/"
            "group_name/labels verbatim"
            if verbatim
            else f"boundary call drifted: {boundary!r}"
        )
        if isinstance(adapter, BasePlatformAdapter):
            fwd = rec.worker_calls[0]
            res = fwd.get("resources")
            forwarded = (
                fwd.get("profile") == profile
                and fwd.get("image_url") == image
                and fwd.get("ttl_seconds") == 4321
                and fwd.get("ready_timeout_seconds") == 222
                and fwd.get("group_name") == "contract--group"
                and fwd.get("labels") == labels
                and isinstance(res, WorkerResources)
                and (res.cpu_count, res.memory_mb, res.storage_mb) == (3, 4096, 8192)
            )
            verbatim = verbatim and forwarded
            if not forwarded:
                detail = f"_create_worker forwarding drifted: {fwd!r}"
        record("create_honors_request", verbatim, detail)
    except Exception as exc:  # noqa: BLE001
        record("create_honors_request", False, f"creation raised: {type(exc).__name__}: {exc}")
    if worker is None:
        return results
    try:
        name = getattr(worker, "name", None)
        worker2 = None
        try:
            worker2 = await adapter.create_sandbox(profile, image)
            name2 = getattr(worker2, "name", None)
        finally:
            if worker2 is not None:
                await worker2.delete()
        record(
            "unique_worker_identity",
            isinstance(name, str) and bool(name) and name != name2,
            f"worker names: {name!r} vs {name2!r}",
        )
    except Exception as exc:  # noqa: BLE001
        record("unique_worker_identity", False, f"{type(exc).__name__}: {exc}")

    # ------------------------------------------------------------------ #
    # 3. File preparation: write_bytes with parents lands; read_text round
    #    trips; a missing path raises (status diagnostics).
    # ------------------------------------------------------------------ #
    try:
        await worker.ctrl.write_bytes("/contracttest/nested/dir/probe.txt", b"probe-bytes", parents=True)
        text = await worker.ctrl.read_text("/contracttest/nested/dir/probe.txt")
        record(
            "file_preparation",
            text == "probe-bytes",
            "write_bytes(parents=True) + read_text round trip" if text == "probe-bytes"
            else f"read back {text!r}",
        )
    except Exception as exc:  # noqa: BLE001
        record("file_preparation", False, f"{type(exc).__name__}: {exc}")
    try:
        raised = False
        try:
            await worker.ctrl.read_text("/contracttest/definitely-missing.txt")
        except Exception:  # noqa: BLE001
            raised = True
        record(
            "status_diagnostics",
            raised,
            "read_text on a missing path raises (diagnosable)" if raised
            else "read_text on a missing path did NOT raise",
        )
    except Exception as exc:  # noqa: BLE001
        record("status_diagnostics", False, f"{type(exc).__name__}: {exc}")

    # ------------------------------------------------------------------ #
    # 4. Command start: run() returns an object with stdout.
    # ------------------------------------------------------------------ #
    try:
        proc = await worker.ctrl.run("echo contract-marker", shell=True, text=True, timeout=30)
        stdout = getattr(proc, "stdout", None)
        record(
            "command_start",
            stdout is not None and "contract-marker" in str(stdout),
            "run() returned stdout" if stdout is not None else "run() result has no stdout",
        )
    except Exception as exc:  # noqa: BLE001
        record("command_start", False, f"{type(exc).__name__}: {exc}")

    # ------------------------------------------------------------------ #
    # 5. Idempotent stop/delete: stop_app twice + delete again never raise.
    # ------------------------------------------------------------------ #
    try:
        adapter.register_long_lived("contract-app", worker)
        if adapter.sandbox_for_app("contract-app") is not worker:
            raise AssertionError("sandbox_for_app did not return the registered worker")
        await adapter.stop_app("contract-app")
        gone = adapter.sandbox_for_app("contract-app") is None
        await adapter.stop_app("contract-app")  # second call: silent no-op
        await worker.delete()  # direct delete after stop: idempotent
        record(
            "idempotent_stop_delete",
            gone,
            "stop_app removed the worker; repeat stop/delete were no-ops" if gone
            else "worker still registered after stop_app",
        )
    except Exception as exc:  # noqa: BLE001
        record("idempotent_stop_delete", False, f"{type(exc).__name__}: {exc}")

    # ------------------------------------------------------------------ #
    # 5b. Memory accounting: a worker created with a known memory_mb and
    #     registered long-lived must be reflected in long_lived_memory_mb;
    #     after stop_app the total returns to the baseline. A fixed-zero
    #     implementation (or one that cannot see the workers it created
    #     itself) fails this check — the global memory usage pre-check
    #     would silently under-count.
    # ------------------------------------------------------------------ #
    try:
        before_mb = adapter.long_lived_memory_mb()
        mem_worker = None
        try:
            mem_worker = await adapter.create_sandbox(
                profile, image, spec={"cpu_count": 1, "memory_mb": 4096}
            )
            adapter.register_long_lived("contract-memory", mem_worker)
            registered_mb = adapter.long_lived_memory_mb()
        finally:
            await adapter.stop_app("contract-memory")
            if mem_worker is not None:
                try:
                    await mem_worker.delete()
                except Exception:  # noqa: BLE001
                    pass
        after_mb = adapter.long_lived_memory_mb()
        ok = registered_mb >= before_mb + 4096 and after_mb == before_mb
        record(
            "memory_accounting",
            ok,
            f"4096 MiB worker accounted: {before_mb} -> {registered_mb} -> {after_mb}"
            if ok
            else f"long_lived_memory_mb {before_mb} -> {registered_mb} -> {after_mb}: "
            f"a registered 4096 MiB worker must add >= 4096 and stop_app must "
            f"return the total to the baseline",
        )
    except Exception as exc:  # noqa: BLE001
        record("memory_accounting", False, f"{type(exc).__name__}: {exc}")

    # ------------------------------------------------------------------ #
    # 6. Creation failure leaves no live worker (and, for
    #    BasePlatformAdapter, the transient retry loop engaged first).
    # ------------------------------------------------------------------ #
    before = adapter.long_lived_count()
    if isinstance(adapter, BasePlatformAdapter):
        orig_worker = adapter._create_worker
        attempts = {"n": 0}

        class _ContractTransientError(Exception):
            """Unknown name -> classified transient by the contract."""

        async def _failing(profile, image_url, **kwargs):
            attempts["n"] += 1
            raise _ContractTransientError("injected creation failure")

        orig_retries, orig_delay = adapter.create_retries, adapter.create_retry_delay_seconds
        adapter._create_worker = _failing
        adapter.create_retries, adapter.create_retry_delay_seconds = 2, 0.01
        try:
            raised = False
            try:
                await adapter.create_sandbox(profile, image)
            except _ContractTransientError:
                raised = True
            ok = (
                raised
                and attempts["n"] == 3
                and adapter.long_lived_count() == before
            )
            record(
                "creation_failure_cleanup",
                ok,
                f"transient failure retried {attempts['n']}x then raised; "
                f"long_lived {before} -> {adapter.long_lived_count()}",
            )
        finally:
            adapter._create_worker = orig_worker
            adapter.create_retries, adapter.create_retry_delay_seconds = orig_retries, orig_delay
    else:
        orig_create = adapter.create_sandbox

        class _ContractBoom(Exception):
            pass

        async def _failing_create(profile, image_url, **kwargs):
            raise _ContractBoom("injected creation failure")

        adapter.create_sandbox = _failing_create
        try:
            raised = False
            try:
                await adapter.create_sandbox(profile, image)
            except _ContractBoom:
                raised = True
            record(
                "creation_failure_cleanup",
                raised and adapter.long_lived_count() == before,
                f"creation failure propagated; long_lived {before} -> {adapter.long_lived_count()}",
            )
        finally:
            adapter.create_sandbox = orig_create

    # ------------------------------------------------------------------ #
    # 7. Scoped cleanup: stop_app removes exactly the named workers (the
    #    store-level "partial shard failure" shape at adapter granularity).
    # ------------------------------------------------------------------ #
    created = []
    try:
        for i in range(3):
            w = await adapter.create_sandbox(profile, image)
            created.append(w)
            adapter.register_long_lived(f"contract-scope-{i}", w)
        await adapter.stop_app("contract-scope-1")
        remaining = {
            name
            for name in ("contract-scope-0", "contract-scope-1", "contract-scope-2")
            if adapter.sandbox_for_app(name) is not None
        }
        record(
            "scoped_cleanup",
            remaining == {"contract-scope-0", "contract-scope-2"},
            f"remaining after stopping one of three: {sorted(remaining)}",
        )
    except Exception as exc:  # noqa: BLE001
        record("scoped_cleanup", False, f"{type(exc).__name__}: {exc}")
    finally:
        for i in (0, 1, 2):
            try:
                await adapter.stop_app(f"contract-scope-{i}")
            except Exception:  # noqa: BLE001
                pass
        for w in created:
            try:
                await w.delete()
            except Exception:  # noqa: BLE001
                pass
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tcsexam.backend.contracttest",
        description="Run the platform-adapter contract suite against an adapter.",
    )
    parser.add_argument(
        "--adapter",
        required=True,
        help="adapter spec: `docker`, `local-test` or `module:factory` (see adapter.load_adapter)",
    )
    parser.add_argument(
        "--config",
        help="YAML config the adapter factory receives (defaults to an empty Config)",
    )
    parser.add_argument(
        "--image",
        default="registry.example.com/contract-judge:1",
        help="judge image the checks request (default: %(default)s — a placeholder "
        "that only verifies contract behavior; pass a real, pullable image when "
        "self-checking a production adapter)",
    )
    parser.add_argument(
        "--profile",
        default="contract-profile",
        help="creation profile the checks request (default: %(default)s; pass the "
        "profile your platform expects when self-checking a production adapter)",
    )
    args = parser.parse_args(argv)
    if args.config:
        from .config import load_config

        config = load_config(args.config)
    else:
        config = Config()
    try:
        adapter = load_adapter(args.adapter, config)
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL adapter load: {type(exc).__name__}: {exc}")
        return 2
    results = asyncio.run(run_contract_suite(adapter, image=args.image, profile=args.profile))
    failed = 0
    for result in results:
        if result.skipped:
            verdict = "SKIP"
        elif result.ok:
            verdict = "PASS"
        else:
            verdict = "FAIL"
            failed += 1
        print(f"{verdict} {result.name}: {result.detail}")
    total = len(results)
    if failed:
        print(f"CONTRACT SUITE: {failed}/{total} checks FAILED")
        return 1
    print(f"CONTRACT SUITE: all {total} checks passed")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
