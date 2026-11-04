"""HTTP front-end of the TCSExam judging backend.

Routes (all JSON; auth via ``X-TCSEXAM-Token-Id`` / ``X-TCSEXAM-Token-Secret``
headers when tokens are configured):

* ``POST   /v1/judge/sessions``              — create a judge session from a
  judge image; boots one throwaway worker per shard running the image's
  judge worker and returns the session id once its reverse tunnel is up
  (asynchronously: 202 + polling).
* ``GET    /v1/judge/sessions``              — list sessions (live + recent
  destroyed tail) and the reconciliation queries
  (``?client_ip=`` / ``?session_ids=``).
* ``GET    /v1/judge/sessions/{sid}``        — session status.
* ``GET    /v1/judge/sessions/{sid}/archive``— the session's raw-record
  archive (verifier-only, gated by the ``X-TCSEXAM-Archive-Token``
  credential on top of the service auth; every failure mode answers 404).
* ``GET    /v1/judge/sessions/{sid}/payload[...]`` — verifier-only
  creation-payload / submission-body downloads (same gate).
* ``ALL    /v1/judge/sessions/{sid}/{tail}`` — relay to the in-worker judge
  worker (``/submit``, ``/submissions``, ``/health``).
* ``DELETE /v1/judge/sessions/{sid}``        — destroy (idempotent).
* ``GET    /v1/tunnel/{app}``                — the worker agent's WebSocket
  dial-in (auth'd like everything else).
* ``GET    /v1/health``                      — liveness probe (auth-exempt).
* ``GET    /v1/status``                      — service introspection.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path
from typing import Any

from aiohttp import web

from .adapter import load_adapter
from .auth import RUN_ID_MODES, UNAUTHORIZED_MESSAGE, make_auth_middleware
from .config import Config, load_config
from .sessions import JudgeSessionStore, _stop_sandbox_best_effort
from .sessions import register_routes as register_judge_session_routes
from .status import RequestCounter, StatusCollector, register_status_routes
from .tunnel import TunnelManager
from .tunnel import register_routes as register_tunnel_routes

LOGGER = logging.getLogger("tcsexam.backend.server")


class BackendStatusCollector(StatusCollector):
    """/v1/status plus ``sessions_by_status``: ready (judging, holding
    workers) / provisioning / failed / hibernated (settled, zero workers) /
    destroyed (the retained ledger tail, zero workers). Operators read this
    to tell "many sessions, few workers" apart from a leak — hibernated
    session counts are ledger counts, decoupled from worker counts."""

    def snapshot(self) -> dict:
        payload = super().snapshot()
        counts: dict[str, int] = {
            "ready": 0,
            "provisioning": 0,
            "failed": 0,
            "hibernated": 0,
            "destroyed": 0,
        }
        store = self._sessions_store
        if store is not None:
            for session in store.list_sessions():
                if getattr(session, "destroyed", False):
                    counts["destroyed"] += 1
                else:
                    status = getattr(session, "status", "ready") or "ready"
                    counts[status] = counts.get(status, 0) + 1
        payload["sessions_by_status"] = counts
        return payload


# Solver tars are a few MB; leave generous headroom (1 GiB).
_MAX_BODY = 1024**3

# Backwards-compatible module-level middleware (no request counter); the app
# built in create_app uses its own instance wired to the counter instead.
_auth_middleware = make_auth_middleware(unauthorized_message=UNAUTHORIZED_MESSAGE)


async def handle_health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def _reap_closed_tunnel(app: web.Application, app_name: str) -> None:
    """Tunnel-close hook: a closed tunnel no longer reaps the worker
    outright — transient drops (net/proxy flaps) reconnect within seconds,
    and an instant-teardown rule would delete healthy workers on every flap.
    Sessions the store tracks (ready/provisioning) are claimed for the
    shard-level down-grace: a reconnect within ``shard_down_grace_ticks``
    resets and heals; only a shard still down past the grace is marked
    failed and reaped (in JudgeSessionStore._mark_down_shards). Untracked
    apps (unknown / non-ready) keep the immediate-teardown path."""
    tunnels = app.get("tunnels")
    if tunnels is not None and tunnels.is_connected(app_name):
        return  # A replacement arrived before this scheduled hook ran.
    store = app.get("judge_sessions")
    if store is not None and store.claim_shard_tunnel_close(app_name):
        return
    await _stop_sandbox_best_effort(app["executor"], app_name)


def create_app(config: Config, adapter: Any | None = None) -> web.Application:
    """Build the aiohttp application.

    ``adapter`` overrides the config-selected platform adapter — tests
    inject a fake through it. With ``adapter=None`` the adapter is loaded
    from ``config.adapter`` (see :func:`tcsexam.backend.adapter.load_adapter`;
    an empty spec raises a clear ConfigurationError).

    Raises ``ValueError`` at startup on an unknown ``config.run_id_mode``
    (the caller-identity enforcement toggle, see ``backend.auth``).
    """
    config.validate_auth()
    config.validate_public_image_map()
    config.validate_docker()
    run_id_mode = getattr(config, "run_id_mode", "warn")
    if run_id_mode not in RUN_ID_MODES:
        raise ValueError(
            f"run_id_mode must be one of {RUN_ID_MODES}, got {run_id_mode!r}"
        )
    request_counter = RequestCounter()
    app = web.Application(
        middlewares=[
            make_auth_middleware(
                unauthorized_message=UNAUTHORIZED_MESSAGE, counter=request_counter
            )
        ],
        client_max_size=_MAX_BODY,
    )
    app["config"] = config
    app["executor"] = adapter if adapter is not None else load_adapter(config.adapter, config)
    app["request_counter"] = request_counter
    app.router.add_get("/v1/health", handle_health)

    tunnels = TunnelManager(
        on_tunnel_closed=lambda name: asyncio.ensure_future(_reap_closed_tunnel(app, name)),
    )
    # apps_proxy=False: this backend has no auth-exempt /apps/* twin —
    # every relay path sits behind the service auth middleware.
    register_tunnel_routes(app, tunnels, apps_proxy=False)

    judge_sessions = JudgeSessionStore(app["executor"], config)
    judge_sessions.attach_tunnels(tunnels)
    app["judge_sessions"] = judge_sessions
    register_judge_session_routes(app)

    collector = BackendStatusCollector(
        config=config,
        sessions_config=judge_sessions.cfg,
        sessions_store=judge_sessions,
        tunnels=tunnels,
        executor=app["executor"],
        request_counter=request_counter,
    )
    register_status_routes(app, collector)

    async def _start(app: web.Application) -> None:
        app["judge_sessions"].start_reaper()

    app.on_startup.append(_start)

    async def _cleanup(app: web.Application) -> None:
        await app["judge_sessions"].shutdown()
        close = getattr(app["executor"], "close", None)
        if close is not None:
            await close()

    app.on_cleanup.append(_cleanup)
    return app


def main(argv: list[str] | None = None) -> int:
    """Console entry point: ``python -m tcsexam.backend --config config.yaml``."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(prog="tcsexam-backend")
    parser.add_argument("--config", required=True, help="path to the YAML config")
    parser.add_argument("--host", help="override config host")
    parser.add_argument("--port", type=int, help="override config port")
    args = parser.parse_args(argv)
    config = load_config(args.config)
    host = args.host or config.host
    port = args.port or config.port
    config.state_dir.mkdir(parents=True, exist_ok=True)
    web.run_app(create_app(config), host=host, port=port, print=lambda msg: print(msg, flush=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
