"""B1 acceptance: the platform-adapter contract, as a pytest suite.

The contract itself lives in ``tcsexam.backend.adapter``'s module docstring
(creation honors the request verbatim or raises — never a silent downgrade;
error classification by class name with ValueError always non-transient;
idempotent stop/delete; scoped cleanup). This suite turns those points into
executable checks against one adapter instance.

The suite is a reusable async function — ``run_adapter_contract(make_adapter)``
— so any adapter can be run through the same caliber (a thin factory is all
an adapter needs to provide). The pytest cases below run it against the
bundled :class:`LocalProcessAdapter`. It complements
``tcsexam.backend.contracttest`` (the user-facing CLI twin of this caliber):
that CLI prints a report for operators; these cases are the CI acceptance
gate and additionally pin the resource-refusal and error-classification
matrix (NON_TRANSIENT_ERROR_NAMES / transient / ValueError).

Nothing leaves loopback: the local adapter's "workers" are temp directories
on this machine.
"""
from __future__ import annotations

import asyncio
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tcsexam.backend.adapter import NON_TRANSIENT_ERROR_NAMES, is_transient_platform_error  # noqa: E402
from tcsexam.backend.testing.local_adapter import LocalProcessAdapter  # noqa: E402

from helpers_b import (  # noqa: E402
    FactoryAdapter,
    InsufficientCreditsError,
    PermissionDeniedError,
    free_port,
    make_config,
)


@dataclass
class ContractResult:
    name: str
    ok: bool
    detail: str = ""


def _make_local_adapter() -> LocalProcessAdapter:
    config = make_config(free_port(), Path(tempfile.mkdtemp(prefix="tcsexam-b1-state-")))
    return LocalProcessAdapter(config)


async def run_adapter_contract(make_adapter: Callable[[], Any]) -> list[ContractResult]:
    """Run the platform-adapter contract checks against one fresh adapter.

    ``make_adapter`` is a zero-argument factory returning the adapter under
    test. Returns one ContractResult per check (a failing check never aborts
    the suite; dependent checks report their prerequisite's failure).
    """
    results: list[ContractResult] = []

    def record(name: str, ok: bool, detail: str = "") -> None:
        results.append(ContractResult(name=name, ok=ok, detail=detail))

    adapter = make_adapter()

    # ------------------------------------------------------------------ #
    # 1. Surface: every member the session stores call exists.
    # ------------------------------------------------------------------ #
    required = (
        "create_sandbox",
        "register_long_lived",
        "sandbox_for_app",
        "long_lived_count",
        "long_lived_memory_mb",
        "stop_app",
        "ready_timeout_seconds",
    )
    missing = [name for name in required if not hasattr(adapter, name)]
    record(
        "surface",
        not missing,
        "all store-facing members present" if not missing else f"missing: {missing}",
    )
    if missing:
        return results

    # ------------------------------------------------------------------ #
    # 2. Creation: the adapter receives image/profile/ttl/spec/ready_timeout/
    #    group_name/labels exactly as requested (boundary recording), and
    #    returns a worker with the ctrl/name surface.
    # ------------------------------------------------------------------ #
    spec = {"cpu_count": 3, "memory_mb": 4096, "storage_mb": 8192}
    labels = {"run_id": "b1-contract-run", "token_id": "b1-contract"}
    worker = None
    recorded: dict[str, Any] = {}
    original_create = adapter.create_sandbox

    async def _recording_create(profile, image_url, **kwargs):
        nonlocal recorded
        recorded = {"profile": profile, "image_url": image_url, **kwargs}
        return await original_create(profile, image_url, **kwargs)

    try:
        adapter.create_sandbox = _recording_create
        try:
            worker = await adapter.create_sandbox(
                "b1-profile",
                "registry.example.com/b1-judge:1",
                ttl_seconds=4321.0,
                spec=dict(spec),
                ready_timeout_seconds=222.0,
                group_name="b1--group",
                labels=dict(labels),
            )
        finally:
            adapter.create_sandbox = original_create
        verbatim = (
            recorded.get("profile") == "b1-profile"
            and recorded.get("image_url") == "registry.example.com/b1-judge:1"
            and recorded.get("ttl_seconds") == 4321.0
            and recorded.get("spec") == spec
            and recorded.get("ready_timeout_seconds") == 222.0
            and recorded.get("group_name") == "b1--group"
            and recorded.get("labels") == labels
        )
        surface_ok = (
            worker is not None
            and hasattr(worker, "ctrl")
            and isinstance(getattr(worker, "name", None), str)
            and bool(worker.name)
        )
        record(
            "create_honors_request",
            verbatim and surface_ok,
            "create_sandbox received profile/image/ttl/spec/ready_timeout/group_name/labels "
            "verbatim; worker has ctrl + name"
            if verbatim and surface_ok
            else f"boundary call or worker surface drifted: {recorded!r}",
        )
    except Exception as exc:  # noqa: BLE001
        record("create_honors_request", False, f"creation raised: {type(exc).__name__}: {exc}")
    if worker is None:
        return results

    # ------------------------------------------------------------------ #
    # 3. Unique worker identity (and, when the adapter hands out per-worker
    #    judge ports like the local double does, distinct ports).
    # ------------------------------------------------------------------ #
    try:
        worker2 = None
        try:
            worker2 = await adapter.create_sandbox("b1-profile", "registry.example.com/b1-judge:1")
            ok = worker2.name != worker.name
            detail = f"worker names {worker.name!r} vs {worker2.name!r}"
            port1, port2 = getattr(worker, "judge_port", None), getattr(worker2, "judge_port", None)
            if port1 is not None and port2 is not None:
                ok = ok and port1 != port2
                detail += f"; judge ports {port1} vs {port2}"
            record("unique_worker_identity", ok, detail)
        finally:
            if worker2 is not None:
                await worker2.delete()
    except Exception as exc:  # noqa: BLE001
        record("unique_worker_identity", False, f"{type(exc).__name__}: {exc}")

    # ------------------------------------------------------------------ #
    # 4. File preparation: write_bytes (parents=True) lands byte-for-byte;
    #    the file stays inside the worker's own area.
    # ------------------------------------------------------------------ #
    payload = "contract-bytes-中文\n".encode()  # valid UTF-8: read_text round-trips it
    try:
        await worker.ctrl.write_bytes("/tcsexam-backend/nested/dir/probe.txt", payload, parents=True)
        back = await worker.ctrl.read_text("/tcsexam-backend/nested/dir/probe.txt")
        ok = back == payload.decode()
        detail = "write_bytes + read_text round trip byte-exact"
        # Where the adapter exposes its local root (the local double does),
        # the bytes on the mirror must be identical and confined underneath it.
        root = getattr(worker, "root", None)
        if root is not None:
            mirrored = Path(root) / "tcsexam-backend/nested/dir/probe.txt"
            confined = mirrored.is_relative_to(Path(root)) if hasattr(mirrored, "is_relative_to") else True
            ok = ok and mirrored.read_bytes() == payload and confined
            detail += f"; mirrored under worker root ({mirrored})"
        record("file_preparation", ok, detail if ok else f"read back {back!r}")
    except Exception as exc:  # noqa: BLE001
        record("file_preparation", False, f"{type(exc).__name__}: {exc}")

    # ------------------------------------------------------------------ #
    # 5. Path handling at the worker boundary. Contract expectation: worker
    #    paths are in-worker absolute paths resolved INSIDE the worker — the
    #    service never reaches the host filesystem. The local test double
    #    mirrors absolute paths under its temp root (confined, asserted
    #    here); it does NOT sandbox ".." (a ".." segment resolves outside the
    #    mirror — pinned as the actual behavior). That is a fidelity gap of
    #    the test double only: real adapters resolve paths inside an
    #    isolated worker, where "/../x" == "/x" and nothing escapes. The
    #    stores only ever write work_dir-relative paths, so the gap is
    #    unreachable in service use.
    # ------------------------------------------------------------------ #
    try:
        root = getattr(worker, "root", None)
        if root is None:
            record(
                "path_confinement",
                True,
                "adapter exposes no local root; confinement is platform-internal (not probed)",
            )
        else:
            await worker.ctrl.write_bytes("/abs-confined/b1-probe", b"abs", parents=True)
            confined = (Path(root) / "abs-confined/b1-probe").exists()
            escape_probe = Path(root).parent / "tcsexam-b1-escape-probe"
            try:
                await worker.ctrl.write_bytes("/../tcsexam-b1-escape-probe", b"esc", parents=True)
                escaped = escape_probe.exists()
            finally:
                escape_probe.unlink(missing_ok=True)
            ok = confined and escaped
            record(
                "path_confinement",
                ok,
                "absolute paths mirror under the worker root; '..' resolves outside the mirror "
                "(test-double fidelity gap, documented — real workers resolve it internally)"
                if ok
                else f"confined={confined} escaped={escaped}",
            )
    except Exception as exc:  # noqa: BLE001
        record("path_confinement", False, f"{type(exc).__name__}: {exc}")

    # ------------------------------------------------------------------ #
    # 6. Command start: run() returns an object with stdout; a failing
    #    command is REPORTED (returncode + stderr), not raised — the
    #    WorkerControl protocol documents "a non-zero exit code is reported,
    #    not raised"; a raise is reserved for transport failure.
    # ------------------------------------------------------------------ #
    try:
        proc = await worker.ctrl.run("echo b1-marker", shell=True, text=True, timeout=30)
        stdout = getattr(proc, "stdout", None)
        ok_run = stdout is not None and "b1-marker" in str(stdout) and proc.returncode == 0
        proc_fail = await worker.ctrl.run(
            "echo b1-err-detail >&2; exit 3", shell=True, text=True, timeout=30
        )
        ok_fail = (
            proc_fail.returncode == 3
            and "b1-err-detail" in str(getattr(proc_fail, "stderr", ""))
        )
        record(
            "command_start",
            ok_run and ok_fail,
            "run() returned stdout; failing command reported rc=3 with a readable stderr"
            if ok_run and ok_fail
            else f"stdout={stdout!r} fail_rc={getattr(proc_fail, 'returncode', None)!r} "
            f"stderr={getattr(proc_fail, 'stderr', None)!r}",
        )
    except Exception as exc:  # noqa: BLE001
        record("command_start", False, f"{type(exc).__name__}: {exc}")

    # ------------------------------------------------------------------ #
    # 7. Reachability/readiness: the worker answers at the process level,
    #    and the local double hands each worker a distinct judge port (the
    #    port level the store relays to).
    # ------------------------------------------------------------------ #
    try:
        proc = await worker.ctrl.run("true", shell=True, text=True, timeout=30)
        port = getattr(worker, "judge_port", None)
        ok = proc.returncode == 0 and isinstance(port, int) and port > 0
        record(
            "worker_reachable",
            ok,
            f"process level: run(true) rc={proc.returncode}; port level: judge_port={port}"
            if ok
            else f"run(true) rc={proc.returncode}, judge_port={port!r}",
        )
    except Exception as exc:  # noqa: BLE001
        record("worker_reachable", False, f"{type(exc).__name__}: {exc}")

    # ------------------------------------------------------------------ #
    # 8. Status diagnostics: read_text reads back what was written; a
    #    missing path raises (a diagnosable error, never a silent empty read).
    # ------------------------------------------------------------------ #
    try:
        await worker.ctrl.write_bytes("/tcsexam-backend/diag.txt", b"diag-content", parents=True)
        back = await worker.ctrl.read_text("/tcsexam-backend/diag.txt")
        raised = False
        try:
            await worker.ctrl.read_text("/tcsexam-backend/definitely-missing-b1.txt")
        except Exception:  # noqa: BLE001
            raised = True
        record(
            "status_diagnostics",
            back == "diag-content" and raised,
            "read_text round trip; missing path raises"
            if back == "diag-content" and raised
            else f"back={back!r} missing_raised={raised}",
        )
    except Exception as exc:  # noqa: BLE001
        record("status_diagnostics", False, f"{type(exc).__name__}: {exc}")

    # ------------------------------------------------------------------ #
    # 9. Stop/delete idempotence: stop twice, stop an unknown app, delete
    #    after stop — all silent no-ops; nothing stays on the long-lived
    #    table afterwards.
    # ------------------------------------------------------------------ #
    try:
        adapter.register_long_lived("b1-contract-app", worker)
        registered = adapter.sandbox_for_app("b1-contract-app") is worker
        await adapter.stop_app("b1-contract-app")
        gone = adapter.sandbox_for_app("b1-contract-app") is None
        await adapter.stop_app("b1-contract-app")  # repeat: silent no-op
        await adapter.stop_app("b1-never-registered")  # unknown: silent no-op
        await worker.delete()  # delete after stop: idempotent
        count_zero = adapter.long_lived_count() == 0
        record(
            "idempotent_stop_delete",
            registered and gone and count_zero,
            "stop_app removed the worker; repeat/unknown stop and re-delete were no-ops; "
            f"long_lived_count={adapter.long_lived_count()}"
            if registered and gone and count_zero
            else f"registered={registered} gone={gone} count={adapter.long_lived_count()}",
        )
    except Exception as exc:  # noqa: BLE001
        record("idempotent_stop_delete", False, f"{type(exc).__name__}: {exc}")
    try:
        await worker.delete()
    except Exception:  # noqa: BLE001 - best-effort suite cleanup
        pass

    # ------------------------------------------------------------------ #
    # 10. Scoped cleanup: stop_app destroys exactly the named worker, never
    #     siblings (the partial-shard-failure shape at adapter granularity).
    # ------------------------------------------------------------------ #
    created = []
    try:
        for i in range(3):
            w = await adapter.create_sandbox("b1-profile", "registry.example.com/b1-judge:1")
            created.append(w)
            adapter.register_long_lived(f"b1-scope-{i}", w)
        await adapter.stop_app("b1-scope-1")
        remaining = {
            name
            for name in ("b1-scope-0", "b1-scope-1", "b1-scope-2")
            if adapter.sandbox_for_app(name) is not None
        }
        record(
            "scoped_cleanup",
            remaining == {"b1-scope-0", "b1-scope-2"},
            f"remaining after stopping one of three: {sorted(remaining)}",
        )
    except Exception as exc:  # noqa: BLE001
        record("scoped_cleanup", False, f"{type(exc).__name__}: {exc}")
    finally:
        for i in (0, 1, 2):
            try:
                await adapter.stop_app(f"b1-scope-{i}")
            except Exception:  # noqa: BLE001
                pass
        for w in created:
            try:
                await w.delete()
            except Exception:  # noqa: BLE001
                pass

    # ------------------------------------------------------------------ #
    # 11. Unsupported capability fails clearly: a platform that cannot
    #     provide the requested resources must raise a readable error —
    #     never silently boot a smaller worker (judging assumes the declared
    #     resources). Probed with a purpose-built adapter that refuses
    #     oversized memory.
    # ------------------------------------------------------------------ #
    try:

        def _memory_gated_hook(*, resources, **kwargs):
            if resources.memory_mb > 16384:
                raise InsufficientCreditsError(
                    f"cannot provide memory_mb={resources.memory_mb}: pool maximum is 16384 MB"
                )
            return None  # a FakeWorker from the factory

        gated = FactoryAdapter(_memory_gated_hook, create_retries=2)
        refused = False
        try:
            await gated.create_sandbox(
                "b1-profile", "registry.example.com/b1-judge:1", spec={"memory_mb": 32768}
            )
        except InsufficientCreditsError as exc:
            refused = True
            readable = "16384" in str(exc) and "memory_mb" in str(exc)
        within = await gated.create_sandbox(
            "b1-profile", "registry.example.com/b1-judge:1", spec={"memory_mb": 8192}
        )
        single_attempt = len(gated.worker_calls) == 2  # 1 refused + 1 served, no retries
        record(
            "unsupported_capability_fails_clearly",
            refused and readable and single_attempt and within is not None,
            "oversized memory raised InsufficientCreditsError (readable, no retry, no "
            "silent downgrade); an in-budget request was served"
            if refused and readable and single_attempt
            else f"refused={refused} calls={len(gated.worker_calls)}",
        )
    except Exception as exc:  # noqa: BLE001
        record("unsupported_capability_fails_clearly", False, f"{type(exc).__name__}: {exc}")

    # ------------------------------------------------------------------ #
    # 12. Error classification: names in NON_TRANSIENT_ERROR_NAMES are
    #     non-transient, everything else is transient (retried with
    #     backoff), and ValueError is NEVER retried (a caller bug) — the
    #     adapter module docstring's rule, applied to the creation path.
    # ------------------------------------------------------------------ #
    try:
        by_name_ok = True
        for name in sorted(NON_TRANSIENT_ERROR_NAMES):
            cls = type(name, (Exception,), {})
            if is_transient_platform_error(cls("probe")):
                by_name_ok = False
        transient_ok = is_transient_platform_error(RuntimeError("pool busy")) is True

        def _raise_value_error(**kwargs):
            raise ValueError("caller bug: malformed spec")

        value_error_adapter = FactoryAdapter(
            _raise_value_error, create_retries=2, create_retry_delay_seconds=0.01
        )
        value_error_raised = False
        try:
            await value_error_adapter.create_sandbox("b1-profile", "registry.example.com/b1-judge:1")
        except ValueError:
            value_error_raised = True
        value_error_single = len(value_error_adapter.worker_calls) == 1

        def _raise_transient(**kwargs):
            raise RuntimeError("pool temporarily full")

        transient_adapter = FactoryAdapter(
            _raise_transient, create_retries=2, create_retry_delay_seconds=0.01
        )
        transient_raised = False
        try:
            await transient_adapter.create_sandbox("b1-profile", "registry.example.com/b1-judge:1")
        except RuntimeError:
            transient_raised = True
        transient_retried = len(transient_adapter.worker_calls) == 3

        def _raise_non_transient(**kwargs):
            raise PermissionDeniedError("quota exhausted")

        nt_adapter = FactoryAdapter(_raise_non_transient, create_retries=2, create_retry_delay_seconds=0.01)
        nt_raised = False
        try:
            await nt_adapter.create_sandbox("b1-profile", "registry.example.com/b1-judge:1")
        except PermissionDeniedError:
            nt_raised = True
        nt_single = len(nt_adapter.worker_calls) == 1

        ok = (
            by_name_ok
            and transient_ok
            and value_error_raised
            and value_error_single
            and transient_raised
            and transient_retried
            and nt_raised
            and nt_single
        )
        record(
            "error_classification",
            ok,
            "NON_TRANSIENT names non-transient; RuntimeError transient and retried "
            f"({len(transient_adapter.worker_calls)} attempts); ValueError raised after "
            f"{len(value_error_adapter.worker_calls)} attempt (never retried); "
            f"PermissionDeniedError after {len(nt_adapter.worker_calls)} attempt"
            if ok
            else (
                f"by_name={by_name_ok} transient_fn={transient_ok} "
                f"value_error_attempts={len(value_error_adapter.worker_calls)} "
                f"transient_attempts={len(transient_adapter.worker_calls)} "
                f"nt_attempts={len(nt_adapter.worker_calls)}"
            ),
        )
    except Exception as exc:  # noqa: BLE001
        record("error_classification", False, f"{type(exc).__name__}: {exc}")

    return results


_CHECK_NAMES = [
    "surface",
    "create_honors_request",
    "unique_worker_identity",
    "file_preparation",
    "path_confinement",
    "command_start",
    "worker_reachable",
    "status_diagnostics",
    "idempotent_stop_delete",
    "scoped_cleanup",
    "unsupported_capability_fails_clearly",
    "error_classification",
]

_SUITE_CACHE: list[ContractResult] | None = None


def _suite() -> list[ContractResult]:
    global _SUITE_CACHE
    if _SUITE_CACHE is None:
        _SUITE_CACHE = asyncio.run(run_adapter_contract(_make_local_adapter))
    return _SUITE_CACHE


@pytest.mark.parametrize("check", _CHECK_NAMES)
def test_local_process_adapter_contract(check: str) -> None:
    """One contract check of run_adapter_contract against LocalProcessAdapter."""
    results = {r.name: r for r in _suite()}
    assert check in results, f"contract check {check!r} did not run"
    result = results[check]
    assert result.ok, f"contract check {result.name} failed: {result.detail}"
