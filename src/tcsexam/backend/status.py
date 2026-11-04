"""``GET /v1/status``: service introspection.

Payload shape (keys are ALWAYS present; missing data is null / empty array)::

    service:   {name, version, started_at, uptime_seconds}
    live:      {sessions, tunnels, workers, worker_memory_mb}
    sessions_by_family: [{family, count}]            # judge image family, Top 20
    requests:  {last_60s: {total, by_path}, last_300s: {total, by_path},
                top_paths: [{path, count}]}          # ring buffer, path buckets
    callers:   [{token_id, run_id, agent_name, sessions, requests_300s}]
    submission_cap: {enabled, default, effective_at, overrides,
                     exempt_identities, exempt_identities_file,
                     file_exempt_identities,
                     journaled_sessions, journaled_submissions} | null

Platform-specific reconciliation (diffing the service's registry against a
cloud account's live workers) is adapter territory and intentionally NOT
part of this module: an adapter deployment can layer its own telemetry on
top.
"""
from __future__ import annotations

import time
from collections import deque
from importlib import metadata as importlib_metadata
from typing import Any, Callable

from aiohttp import web

from .config import read_exempt_identities_file

#: Top-N cap for the sessions_by_family table.
_FAMILY_TOP_N = 20

#: Top-N cap for the requests.top_paths table.
_TOP_PATHS_N = 10

#: Top-N cap for the per-caller request counting and the merged callers table.
_TOP_CALLERS_N = 20
_CALLERS_TOP_N = 50


def _package_version() -> str:
    try:
        return importlib_metadata.version("tcsexam")
    except importlib_metadata.PackageNotFoundError:
        return "unknown"


def image_family(image: str) -> str:
    """Judge-image family name, from either image-ref layout:

    - path-style: ``registry.example.com/public/knn-judge:v3`` -> ``knn``
    - tag-style (family lives in the tag):
      ``judge-repo/sat-competition-judge-1.0.1`` -> ``sat-competition``
    """
    base = image.rsplit("/", 1)[-1]
    name, _, tag = base.partition(":")
    if "-judge" in tag:
        return tag.split("-judge", 1)[0]
    if name.endswith("-judge"):
        name = name[: -len("-judge")]
    return name


def classify_path(path: str) -> str | None:
    """Aggregate a request path into one of the counting buckets.

    ``None`` = do not count: liveness/status probes (``/v1/health``,
    ``/v1/status``) are observability traffic, not caller traffic — counting
    them would make the "requests/min" gauge show a constant idle hum.
    """
    if path in ("/v1/health", "/v1/status"):
        return None
    if path == "/v1/judge/sessions":
        return "/v1/judge/sessions"
    if path.startswith("/v1/judge/sessions/"):
        return "/v1/judge/sessions/{sid}"
    if path.startswith("/v1/tunnel/"):
        return "/v1/tunnel/{app}"
    return "other"


class RequestCounter:
    """Ring buffer of recent requests, bucketed by path template.

    Fed by the auth middleware (every request reaching the service is counted,
    including auth-exempt and rejected ones — a 401 storm is load too).
    Non-exempt requests additionally feed the per-caller
    (token_id, run_id, agent_name) counting via :meth:`record_caller` — the
    data source of the status payload's ``callers`` table (requests without
    a resolvable run-id / agent_name count under "").
    """

    def __init__(
        self,
        *,
        window_seconds: float = 300.0,
        short_window_seconds: float = 60.0,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        self.window_seconds = window_seconds
        self.short_window_seconds = short_window_seconds
        self._now = now
        self._events: deque[tuple[float, str]] = deque()
        self._caller_events: deque[tuple[float, str, str, str]] = deque()

    def record(self, path: str) -> None:
        bucket = classify_path(path)
        if bucket is None:  # probe paths are not caller traffic
            return
        self._events.append((self._now(), bucket))
        self._prune()

    def record_caller(self, token_id: str, run_id: str, agent_name: str = "") -> None:
        """Count one non-exempt request against its (token_id, run_id, agent_name)."""
        self._caller_events.append((self._now(), token_id, run_id, agent_name))
        self._prune()

    def _prune(self, now: float | None = None) -> None:
        cutoff = (self._now() if now is None else now) - self.window_seconds
        while self._events and self._events[0][0] < cutoff:
            self._events.popleft()
        while self._caller_events and self._caller_events[0][0] < cutoff:
            self._caller_events.popleft()

    def caller_snapshot(self) -> list[dict[str, Any]]:
        """Per-caller counts over the long window, Top N by count.

        ``[{token_id, run_id, agent_name, count}]``, count desc then
        (token, run, agent) asc — the same deterministic tie-break as
        ``top_paths``.
        """
        self._prune()
        by_caller: dict[tuple[str, str, str], int] = {}
        for _ts, token_id, run_id, agent_name in self._caller_events:
            key = (token_id, run_id, agent_name)
            by_caller[key] = by_caller.get(key, 0) + 1
        top = sorted(by_caller.items(), key=lambda kv: (-kv[1], kv[0]))[:_TOP_CALLERS_N]
        return [
            {"token_id": token_id, "run_id": run_id, "agent_name": agent_name, "count": count}
            for (token_id, run_id, agent_name), count in top
        ]

    def snapshot(self) -> dict[str, Any]:
        now = self._now()
        self._prune(now)
        by_short: dict[str, int] = {}
        by_long: dict[str, int] = {}
        for ts, bucket in self._events:
            by_long[bucket] = by_long.get(bucket, 0) + 1
            if now - ts <= self.short_window_seconds:
                by_short[bucket] = by_short.get(bucket, 0) + 1
        top = sorted(by_long.items(), key=lambda kv: (-kv[1], kv[0]))[:_TOP_PATHS_N]
        return {
            "last_60s": {
                "total": sum(by_short.values()),
                "by_path": dict(sorted(by_short.items())),
            },
            "last_300s": {
                "total": sum(by_long.values()),
                "by_path": dict(sorted(by_long.items())),
            },
            "top_paths": [{"path": path, "count": count} for path, count in top],
        }


# --------------------------------------------------------------------------- #
# Status aggregation
# --------------------------------------------------------------------------- #
def _probe_long_lived_count(executor: Any) -> int | None:
    counter = getattr(executor, "long_lived_count", None)
    return counter() if callable(counter) else None


def _probe_long_lived_memory_mb(executor: Any) -> int | None:
    counter = getattr(executor, "long_lived_memory_mb", None)
    return counter() if callable(counter) else None


class StatusCollector:
    """Builds the /v1/status payload from the wiring pieces.

    Every dependency is optional (None): the corresponding fields still
    appear in the payload, as null / empty arrays.
    """

    def __init__(
        self,
        *,
        config: Any,
        sessions_config: Any = None,
        sessions_store: Any = None,
        tunnels: Any = None,
        executor: Any = None,
        request_counter: RequestCounter | None = None,
        started_at: float | None = None,
        now: Callable[[], float] = time.time,
    ) -> None:
        self._config = config
        self._sessions_config = sessions_config
        self._sessions_store = sessions_store
        self._tunnels = tunnels
        self._executor = executor
        self._request_counter = request_counter
        self.started_at = started_at if started_at is not None else now()
        self._now = now

    def snapshot(self) -> dict[str, Any]:
        now = self._now()

        live_sessions: list[Any] | None = None
        if self._sessions_store is not None:
            live_sessions = self._sessions_store.live_sessions()

        family_counts: dict[str, int] = {}
        for session in live_sessions or []:
            family = image_family(session.image)
            family_counts[family] = family_counts.get(family, 0) + 1
        families = sorted(family_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:_FAMILY_TOP_N]

        tunnel_count = None
        if self._tunnels is not None:
            tunnel_count = self._tunnels.connected_count()

        requests = (
            self._request_counter.snapshot()
            if self._request_counter is not None
            else RequestCounter(now=time.monotonic).snapshot()
        )

        # Submission cap: config + journal usage for ops self-service
        # ("why was my create/submit rejected"). Null when the section is
        # unconfigured.
        submission_cap = None
        cap_cfg = getattr(self._sessions_config, "submission_cap", None)
        journal = getattr(self._sessions_store, "_journal", None)
        if cap_cfg is not None:
            submission_cap = {
                "enabled": cap_cfg.enabled,
                "default": cap_cfg.default,
                "effective_at": cap_cfg.effective_at,
                "overrides": dict(cap_cfg.overrides),
                "exempt_identities": list(cap_cfg.exempt_identities),
                # Hot-reload file: path + the identities it currently
                # yields, so ops can self-answer "why is this address not
                # capped" without shell access.
                "exempt_identities_file": cap_cfg.exempt_identities_file,
                "file_exempt_identities": (
                    read_exempt_identities_file(cap_cfg.exempt_identities_file)
                    if cap_cfg.exempt_identities_file
                    else []
                ),
                "journaled_sessions": len(journal.sessions) if journal is not None else 0,
                "journaled_submissions": (
                    sum(len(s.submissions) for s in journal.sessions.values())
                    if journal is not None
                    else 0
                ),
            }

        return {
            "service": {
                "name": getattr(self._config, "service_name", None),
                "version": _package_version(),
                "started_at": self.started_at,
                "uptime_seconds": max(0.0, now - self.started_at),
            },
            "live": {
                "sessions": len(live_sessions) if live_sessions is not None else None,
                "tunnels": tunnel_count,
                "workers": _probe_long_lived_count(self._executor),
                "worker_memory_mb": _probe_long_lived_memory_mb(self._executor),
            },
            "sessions_by_family": [
                {"family": family, "count": count} for family, count in families
            ],
            "requests": requests,
            "callers": self._build_callers(live_sessions),
            "submission_cap": submission_cap,
        }

    def _build_callers(self, live_sessions: list[Any] | None) -> list[dict[str, Any]]:
        """Merge live sessions and caller-counted requests by
        (token_id, run_id, agent_name).

        Sessions carrying a ``run_id`` attribute are grouped under it (""
        when absent); session-like objects without the attribute (test
        fakes) do not appear. The agent_name dimension comes from
        ``session.agent_name`` (read from the attribution attrs). Requests
        come from the counter's ``caller_snapshot``. Rows sort by
        requests_300s desc, sessions desc, then (token_id, run_id,
        agent_name) asc, capped at ``_CALLERS_TOP_N``.
        """
        merged: dict[tuple[str, str, str], dict[str, Any]] = {}

        def _entry(token_id: str, run_id: str, agent_name: str) -> dict[str, Any]:
            return merged.setdefault(
                (token_id, run_id, agent_name),
                {
                    "token_id": token_id,
                    "run_id": run_id,
                    "agent_name": agent_name,
                    "sessions": 0,
                    "requests_300s": 0,
                },
            )

        for session in live_sessions or []:
            run_id = getattr(session, "run_id", None)
            if run_id is None:
                continue
            token_id = getattr(session, "token_id", "") or "-"
            agent_name = getattr(session, "agent_name", "") or ""
            _entry(token_id, run_id or "", agent_name)["sessions"] += 1
        if self._request_counter is not None:
            for caller in self._request_counter.caller_snapshot():
                _entry(caller["token_id"], caller["run_id"], caller["agent_name"])[
                    "requests_300s"
                ] = caller["count"]
        rows = sorted(
            merged.values(),
            key=lambda r: (
                -r["requests_300s"],
                -r["sessions"],
                r["token_id"],
                r["run_id"],
                r["agent_name"],
            ),
        )
        return rows[:_CALLERS_TOP_N]


async def handle_status(request: web.Request) -> web.Response:
    collector: StatusCollector = request.app["status_collector"]
    return web.json_response(collector.snapshot())


def register_status_routes(app: web.Application, collector: StatusCollector) -> None:
    """Wire ``GET /v1/status`` (behind the same auth middleware as the API)."""
    app["status_collector"] = collector
    app.router.add_get("/v1/status", handle_status)
