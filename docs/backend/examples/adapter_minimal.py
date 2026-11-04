"""Minimal platform-adapter skeleton for the TCSExam judging backend.

This is a TEACHING SKELETON, not a working adapter: it shows the exact
shape the session stores rely on (see the module docstring of
``tcsexam.backend.adapter`` for the full contract). File uploads land in an
in-memory dict; command execution is left to the implementer. For a
runnable local reference see ``tcsexam.backend.testing.local_adapter``
(``adapter: local-test``).

Usage:

* Copy this file into your own importable package and reference its
  ``module:factory`` path in the backend config::

      adapter: "mypackage.cloud_adapter:make_adapter"

  (The shipped copy lives under docs/ as documentation; it is not an
  importable module path of the installed package.)

The factory is called with the loaded ``Config`` when it accepts one
positional argument, otherwise with no arguments
(``tcsexam.backend.adapter.load_adapter``). Check the shape against the
bundled contract suite::

    python -m tcsexam.backend.contracttest \
        --adapter mypackage.cloud_adapter:make_adapter

(command_start fails on this skeleton by design — ``run()`` is the part
you implement against your platform.)
"""
from __future__ import annotations

import itertools
from typing import Any

from tcsexam.backend.adapter import BasePlatformAdapter, WorkerResources


class InvalidArgumentError(Exception):
    """The platform cannot provide the requested image or resources.

    The class NAME is part of the error-classification contract: names in
    ``errors.NON_TRANSIENT_ERROR_NAMES`` are never retried (a retry cannot
    fix a request the platform can never satisfy). Any other exception
    class is treated as transient and retried with backoff.
    """


#: What this skeleton "platform" can provide. A real adapter asks its
#: platform; the point demonstrated here is the no-silent-downgrade rule:
#: creation must honor the requested image and resources AS GIVEN, or raise.
_MAX_CPU_COUNT = 64
_MAX_MEMORY_MB = 262144


class _InMemoryCtrl:
    """In-memory stand-in for the worker control channel.

    The stores use exactly three methods: ``write_bytes`` (upload the agent
    bundle), ``run`` (start it), ``read_text`` (status diagnostics and the
    agent.log tail on teardown).
    """

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    async def write_bytes(self, path: str, data: bytes, parents: bool = False) -> None:
        self.files[path] = data

    async def read_text(self, path: str) -> str:
        if path not in self.files:
            raise FileNotFoundError(path)
        return self.files[path].decode("utf-8", errors="replace")

    async def run(self, cmd: str, shell: bool = False, text: bool = False, timeout: float = 30) -> Any:
        raise NotImplementedError(
            "execute the command inside your worker and return an object "
            "with a `stdout` attribute (a non-zero exit code is reported, "
            "not raised; raise only on transport failure)"
        )


class _InMemoryWorker:
    """One fake worker: unique name, ctrl channel, idempotent delete."""

    _ids = itertools.count(1)

    def __init__(self, image_url: str, resources: WorkerResources) -> None:
        self.name = f"minimal-{next(self._ids)}"
        self.image_url = image_url
        self.resources = resources
        self.ctrl = _InMemoryCtrl()
        self._deleted = False

    async def delete(self) -> None:
        # Idempotent: destroying an unknown or already-destroyed worker is a
        # silent no-op. The caller treats a raised error as "teardown
        # failed" and moves on, so keep this best-effort.
        self._deleted = True


class MinimalAdapter(BasePlatformAdapter):
    """The skeleton adapter: base-class retry/gate/table + one creation attempt.

    Subclassing :class:`BasePlatformAdapter` provides the transient-retry
    loop under a creation concurrency gate, the long-lived worker table
    (``register_long_lived`` / ``sandbox_for_app`` / ``long_lived_count`` /
    ``long_lived_memory_mb``) and an idempotent ``stop_app`` with agent.log
    tail recovery. The only method left to implement is ``_create_worker``:
    ONE creation attempt against the concrete platform.
    """

    async def _create_worker(
        self,
        profile: str,
        image_url: str,
        *,
        ttl_seconds: float,
        resources: WorkerResources,
        ready_timeout_seconds: float,
        group_name: str | None,
        labels: dict[str, str] | None,
    ) -> _InMemoryWorker:
        # No silent downgrade: if the platform cannot provide the requested
        # resources, raise a clearly classified error instead of booting a
        # smaller worker (judging runs assume the declared resources).
        if resources.cpu_count > _MAX_CPU_COUNT or resources.memory_mb > _MAX_MEMORY_MB:
            raise InvalidArgumentError(
                f"requested {resources.cpu_count} CPUs / {resources.memory_mb} MiB "
                f"exceeds this platform's limits "
                f"({_MAX_CPU_COUNT} CPUs / {_MAX_MEMORY_MB} MiB)"
            )
        # A real adapter boots one isolated worker from ``image_url`` with
        # exactly ``resources`` and a platform-side TTL of ``ttl_seconds``,
        # waits up to ``ready_timeout_seconds`` for readiness, and returns
        # it. ``profile`` is an opaque scheduling hint; ``group_name`` and
        # ``labels`` are attribution tags a platform may use for scoped
        # cleanup (an adapter without a tagging concept may ignore them).
        return _InMemoryWorker(image_url, resources)


def make_adapter() -> MinimalAdapter:
    """Adapter factory referenced by the config's ``adapter`` value.

    A factory that declares one positional parameter receives the loaded
    ``Config`` instead (``def make_adapter(config)``).
    """
    return MinimalAdapter()
