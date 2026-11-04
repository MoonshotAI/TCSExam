"""Service side of the reverse tunnel.

The worker agent dials ``GET /v1/tunnel/{app}`` (WebSocket, same shared-token
auth as the rest of the API). The service then relays judge traffic:

    client --HTTP-->  /apps/{app}/<path>  --frames-->  tunnel  --HTTP-->
    localhost:<port> inside the worker (and the response streams back)

Design points:

* One WebSocket per app; concurrent HTTP requests are multiplexed over it by
  request id, each with its own frame queue.
* Responses are STREAMED (aiohttp ``StreamResponse`` written per
  RESPONSE_BODY frame) so server-sent events reach the caller token by token.
* If the tunnel drops, every in-flight request fails with 502 and the app is
  unregistered (web-url lookups go 404). The task harness's transient-failure
  retries absorb the 502s.
* The ``/apps/*`` proxy route is optional (``register_routes(apps_proxy=)``):
  deployments that register it exempt the path from the auth middleware and
  gate each app with a per-session token instead (``session_tokens``);
  deployments that keep every relay behind the auth middleware leave it off.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

from aiohttp import WSMsgType, web

from .tunnel_protocol import (
    CONTROL_ID,
    MAX_FRAME,
    T_DYING,
    T_PING,
    T_PONG,
    T_READY,
    T_REQUEST_ABORT,
    T_REQUEST_BODY,
    T_REQUEST_END,
    T_REQUEST_HEAD,
    T_RESPONSE_ABORT,
    T_RESPONSE_BODY,
    T_RESPONSE_END,
    T_RESPONSE_HEAD,
    FrameParser,
    pack_frame,
)

LOGGER = logging.getLogger("tcsexam.backend.tunnel")

# Hop-by-hop headers are meaningful only on one leg of the relay; drop them
# both ways (Content-Length is recomputed by the receiving HTTP stack).
_HOP_BY_HOP = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
        "host",
        "content-length",
    }
)

#: Payload chunk size when forwarding a large request body over the tunnel.
_BODY_CHUNK = 8 * 1024 * 1024

#: Per-session relay gate header (only checked on the auth-exempt /apps/*
#: proxy path; the /v1/judge/sessions/* relay passes check_token=False).
SESSION_TOKEN_HEADER = "X-TCSEXAM-Session-Token"


def _filter_headers(headers: Any) -> dict[str, str]:
    return {k: v for k, v in headers.items() if k.lower() not in _HOP_BY_HOP}


def _bad_gateway(message: str) -> web.Response:
    # The wording matters: "502 Bad Gateway" hits the task harness's
    # transient-failure markers, so a tunnel flap is retried, not scored 0.
    return web.Response(status=502, text=f"502 Bad Gateway: {message}")


class Tunnel:
    """One app's live reverse tunnel."""

    def __init__(self, app_name: str, ws: web.WebSocketResponse) -> None:
        self.app_name = app_name
        self.ws = ws
        self.pending: dict[bytes, asyncio.Queue] = {}
        self.ready_info: dict[str, Any] | None = None
        self.closed = False
        self.send_lock = asyncio.Lock()

    async def send(self, frame_type: int, request_id: bytes, payload: bytes = b"") -> None:
        async with self.send_lock:
            await self.ws.send_bytes(pack_frame(frame_type, request_id, payload))


class TunnelManager:
    """Tracks live tunnels and relays HTTP requests through them."""

    def __init__(self, on_tunnel_closed: Any = None, on_activity: Any = None) -> None:
        self._tunnels: dict[str, Tunnel] = {}
        self._connect_events: dict[str, asyncio.Event] = {}
        self._closed_apps: set[str] = set()
        # callback(app_name) — the server uses it to unregister the worker
        self._on_closed = on_tunnel_closed
        # callback(app_name) — fired on every accepted relay request; a
        # deployment-level warm pool uses it as the idle-timeout activity
        # stamp (None when pooling is disabled).
        self._on_activity = on_activity
        # Per-session relay gate for judge sessions: app name -> token.
        # Sessions are created by the task-side client over the network; the
        # token keeps anyone else who can merely reach the service from using
        # the unsanitized judge API behind /apps/judge-*. Only checked on
        # the auth-exempt /apps/* proxy path (see register_routes(apps_proxy=)).
        self.session_tokens: dict[str, str] = {}

    # ------------------------------------------------------------------ #
    # Worker side: the WebSocket endpoint
    # ------------------------------------------------------------------ #
    async def handle_ws(self, request: web.Request) -> web.StreamResponse:
        app_name = request.match_info["app_name"]
        if app_name in self._closed_apps:
            return web.Response(status=404)
        # heartbeat=240: PING every 240s, PONG timeout 120s (aiohttp =
        # heartbeat/2). CPU-saturated workers (a judge pinning all cores
        # during an evaluation) can need tens of seconds to answer a PONG;
        # a shorter heartbeat would make the service kill healthy tunnels.
        ws = web.WebSocketResponse(max_msg_size=MAX_FRAME + 64, heartbeat=240)
        await ws.prepare(request)
        # prepare() can yield while destroy marks the app closed.
        if app_name in self._closed_apps:
            await ws.close()
            return ws
        LOGGER.info("tunnel connected: app=%s remote=%s", app_name, request.remote)
        tunnel = Tunnel(app_name, ws)
        old = self._tunnels.get(app_name)
        # Publish the replacement without yielding. Each concurrent connection
        # owns exactly one predecessor, which it closes inside the cleanup scope.
        self._tunnels[app_name] = tunnel
        self._connect_events.setdefault(app_name, asyncio.Event()).set()
        parser = FrameParser()
        try:
            if old is not None:
                LOGGER.warning("tunnel for app=%s replaced by a new connection", app_name)
                # Closing a predecessor may block. Cancellation of this
                # handler must still let that close finish; our own tunnel
                # is independently cleaned up in the finally scope below.
                await asyncio.shield(self._teardown(old, "replaced by a new tunnel", notify=False))
            async for msg in ws:
                if msg.type == WSMsgType.BINARY:
                    for frame_type, request_id, payload in parser.feed(msg.data):
                        await self._dispatch(tunnel, frame_type, request_id, payload)
                elif msg.type == WSMsgType.ERROR:
                    LOGGER.warning(
                        "tunnel app=%s WS error: %s", app_name, ws.exception()
                    )
                    break
                elif msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED):
                    break
        except Exception:
            LOGGER.exception("tunnel app=%s reader crashed", app_name)
            raise
        finally:
            LOGGER.info(
                "tunnel closed: app=%s close_code=%s exception=%r in_flight=%d ready=%s",
                app_name,
                ws.close_code,
                ws.exception(),
                len(tunnel.pending),
                tunnel.ready_info is not None,
            )
            await self._teardown(tunnel, "tunnel closed")
        return ws

    async def _dispatch(self, tunnel: Tunnel, frame_type: int, request_id: bytes, payload: bytes) -> None:
        if frame_type == T_PING:
            await tunnel.send(T_PONG, CONTROL_ID, payload)
            return
        if frame_type == T_PONG:
            return
        if frame_type == T_READY:
            try:
                tunnel.ready_info = json.loads(payload.decode())
            except Exception:  # noqa: BLE001
                tunnel.ready_info = {}
            LOGGER.info("tunnel app=%s READY: %s", tunnel.app_name, tunnel.ready_info)
            return
        if frame_type == T_DYING:
            # The serve process died; closing the WS unregisters the app and
            # fails in-flight requests with 502.
            try:
                reason = json.loads(payload.decode()).get("reason", "?")
            except Exception:  # noqa: BLE001
                reason = payload.decode(errors="replace")
            LOGGER.warning("tunnel app=%s reports DYING: %s", tunnel.app_name, reason)
            await tunnel.ws.close()
            return
        queue = tunnel.pending.get(request_id)
        if queue is not None:
            queue.put_nowait((frame_type, payload))

    async def _teardown(self, tunnel: Tunnel, reason: str, *, notify: bool = True) -> None:
        tunnel.closed = True
        for queue in tunnel.pending.values():
            queue.put_nowait((T_RESPONSE_ABORT, reason.encode()))
        tunnel.pending.clear()
        try:
            await tunnel.ws.close()
        except Exception:  # noqa: BLE001
            pass
        finally:
            # Re-check after close() yields: a replacement can connect while
            # an old socket is closing. Update mapping, event and callback
            # together without another await, and only for the current owner.
            if notify and self._tunnels.get(tunnel.app_name) is tunnel:
                self._tunnels.pop(tunnel.app_name, None)
                event = self._connect_events.get(tunnel.app_name)
                if event is not None:
                    event.clear()
                if self._on_closed is not None:
                    self._on_closed(tunnel.app_name)

    async def close(self, app_name: str) -> None:
        """Close one app's tunnel permanently and forget its session token.

        Unknown and already-closed apps are no-ops. Pending relays are aborted
        through the same teardown path used by the WebSocket handler; later
        connections for this one-shot app name are rejected.
        """
        self._closed_apps.add(app_name)
        self.session_tokens.pop(app_name, None)
        tunnel = self._tunnels.get(app_name)
        if tunnel is not None:
            await self._teardown(tunnel, "session destroyed")

    # ------------------------------------------------------------------ #
    # Service side: queries and the HTTP relay
    # ------------------------------------------------------------------ #
    def is_connected(self, app_name: str) -> bool:
        tunnel = self._tunnels.get(app_name)
        return tunnel is not None and not tunnel.closed

    def in_flight(self, app_name: str) -> int:
        """Relayed requests currently in flight on this app's tunnel (0 when
        no tunnel is connected). The judge-session idle reaper skips sessions
        with in-flight judging — a long evaluation emits no new messages for
        hours and would otherwise look idle.
        """
        tunnel = self._tunnels.get(app_name)
        return len(tunnel.pending) if tunnel is not None else 0

    def connected_count(self) -> int:
        """Number of live (connected, not closed) tunnels (the /v1/status data source)."""
        return sum(1 for t in self._tunnels.values() if not t.closed)

    def ready_info(self, app_name: str) -> dict[str, Any] | None:
        tunnel = self._tunnels.get(app_name)
        return tunnel.ready_info if tunnel else None

    async def wait_connected(self, app_name: str, timeout: float) -> bool:
        event = self._connect_events.setdefault(app_name, asyncio.Event())
        if self.is_connected(app_name):
            return True
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            return self.is_connected(app_name)
        return self.is_connected(app_name)

    async def _abort_request(self, tunnel: Tunnel, request_id: bytes) -> None:
        """Tell the worker to drop one in-flight request (best-effort)."""
        try:
            await tunnel.send(T_REQUEST_ABORT, request_id)
        except Exception:  # noqa: BLE001 - tunnel may already be gone
            pass

    async def call(
        self,
        app_name: str,
        method: str,
        path: str,
        body: bytes = b"",
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        """Programmatic variant of ``forward``: send one request through the
        tunnel and COLLECT the full response instead of streaming it back to
        an HTTP caller. Used by server-side fan-out (one caller request is
        fanned out to N workers and the N responses are merged server-side;
        there is no single upstream connection to stream to). Tunnel failures
        map to 502 like ``forward`` does, so the merged endpoint keeps the
        same transient-retry contract.
        """
        tunnel = self._tunnels.get(app_name)
        if tunnel is None or tunnel.closed:
            LOGGER.info("call 502: app=%s has no live tunnel (%s %s)", app_name, method, path)
            return 502, {}, f"502 Bad Gateway: app {app_name!r} has no live tunnel (please try again)".encode()
        request_id = uuid.uuid4().bytes
        queue: asyncio.Queue = asyncio.Queue()
        tunnel.pending[request_id] = queue
        try:
            head = json.dumps(
                {"method": method, "path": path, "headers": headers or {}}
            ).encode()
            try:
                await tunnel.send(T_REQUEST_HEAD, request_id, head)
                for offset in range(0, len(body), _BODY_CHUNK):
                    await tunnel.send(T_REQUEST_BODY, request_id, body[offset : offset + _BODY_CHUNK])
                await tunnel.send(T_REQUEST_END, request_id)
            except Exception as exc:  # noqa: BLE001 - the tunnel is dying
                LOGGER.warning("call 502: tunnel write failed: app=%s %s %s: %s", app_name, method, path, exc)
                return 502, {}, f"502 Bad Gateway: tunnel write failed: {exc} (please try again)".encode()

            frame_type, payload = await queue.get()
            if frame_type != T_RESPONSE_HEAD:
                LOGGER.warning(
                    "call aborted before response head: app=%s %s %s reason=%s",
                    app_name, method, path, payload[:200].decode(errors="replace"),
                )
                return 502, {}, b"502 Bad Gateway: tunnel request aborted: " + payload[:200]
            try:
                meta = json.loads(payload.decode())
            except Exception:  # noqa: BLE001
                return 502, {}, b"502 Bad Gateway: malformed response head from the tunnel"
            status = int(meta.get("status", 200))
            resp_headers = _filter_headers(meta.get("headers") or {})
            chunks: list[bytes] = []
            while True:
                frame_type, payload = await queue.get()
                if frame_type == T_RESPONSE_BODY:
                    chunks.append(payload)
                elif frame_type == T_RESPONSE_END:
                    return status, resp_headers, b"".join(chunks)
                else:  # T_RESPONSE_ABORT
                    LOGGER.warning(
                        "call aborted mid-stream: app=%s %s %s reason=%s",
                        app_name, method, path, payload[:200].decode(errors="replace"),
                    )
                    return 502, {}, b"502 Bad Gateway: tunnel request aborted mid-stream: " + payload[:200]
        finally:
            tunnel.pending.pop(request_id, None)

    async def forward(
        self, app_name: str, request: web.Request, *, check_token: bool = True
    ) -> web.StreamResponse:
        """Relay one HTTP request to the worker's localhost server.

        Failure isolation rules: a dying UPSTREAM (judge) connection aborts
        only this request (the worker is told via T_REQUEST_ABORT) and never
        touches the tunnel; a dying TUNNEL fails this request with 502 and
        the tunnel teardown handles the rest.

        ``check_token=False`` skips the per-session X-TCSEXAM-Session-Token
        gate — used by callers whose own path already went through the
        service auth middleware (the /v1/judge/sessions/* relay).
        """
        tunnel = self._tunnels.get(app_name)
        if tunnel is None or tunnel.closed:
            LOGGER.info("relay 502: app=%s has no live tunnel (%s %s)", app_name, request.method, request.path)
            return _bad_gateway(f"app {app_name!r} has no live tunnel (please try again)")
        expected_token = self.session_tokens.get(app_name)
        if (
            check_token
            and expected_token is not None
            and request.headers.get(SESSION_TOKEN_HEADER) != expected_token
        ):
            return web.Response(
                status=403, text=f"403 Forbidden: bad or missing {SESSION_TOKEN_HEADER}"
            )
        if self._on_activity is not None:
            self._on_activity(app_name)
        request_id = uuid.uuid4().bytes
        queue: asyncio.Queue = asyncio.Queue()
        tunnel.pending[request_id] = queue
        prepared: web.StreamResponse | None = None
        try:
            tail = request.match_info.get("tail", "")
            path = "/" + tail
            if request.query_string:
                path += "?" + request.query_string
            head = json.dumps(
                {
                    "method": request.method,
                    "path": path,
                    "headers": _filter_headers(request.headers),
                }
            ).encode()
            try:
                await tunnel.send(T_REQUEST_HEAD, request_id, head)
                body = await request.read()
                for offset in range(0, len(body), _BODY_CHUNK):
                    await tunnel.send(T_REQUEST_BODY, request_id, body[offset : offset + _BODY_CHUNK])
                await tunnel.send(T_REQUEST_END, request_id)
            except Exception as exc:  # noqa: BLE001 - the tunnel is dying
                LOGGER.warning(
                    "relay 502: tunnel write failed: app=%s %s %s: %s",
                    app_name, request.method, path, exc,
                )
                return _bad_gateway(f"tunnel write failed: {exc} (please try again)")

            frame_type, payload = await queue.get()
            if frame_type != T_RESPONSE_HEAD:
                LOGGER.warning(
                    "relay aborted before response head: app=%s %s %s reason=%s",
                    app_name, request.method, path, payload[:200].decode(errors="replace"),
                )
                return _bad_gateway(f"tunnel request aborted: {payload.decode(errors='replace')}")
            try:
                meta = json.loads(payload.decode())
            except Exception:  # noqa: BLE001
                return _bad_gateway("malformed response head from the tunnel")
            response = web.StreamResponse(
                status=int(meta.get("status", 200)),
                headers=_filter_headers(meta.get("headers") or {}),
            )
            await response.prepare(request)
            prepared = response
            while True:
                frame_type, payload = await queue.get()
                if frame_type == T_RESPONSE_BODY:
                    await response.write(payload)
                elif frame_type == T_RESPONSE_END:
                    await response.write_eof()
                    return response
                else:  # T_RESPONSE_ABORT
                    LOGGER.warning(
                        "relay aborted mid-stream: app=%s %s %s reason=%s",
                        app_name, request.method, path, payload[:200].decode(errors="replace"),
                    )
                    await response.write_eof()
                    return response
        except asyncio.CancelledError:
            # aiohttp cancels the handler when the caller's connection drops.
            await self._abort_request(tunnel, request_id)
            raise
        except ConnectionError as exc:
            # The caller went away mid-relay (its own timeout fired first):
            # abort just this request — the tunnel itself is untouched.
            LOGGER.info(
                "relay client-side connection lost: app=%s %s (%s); aborted this request only",
                app_name, request.path, exc,
            )
            await self._abort_request(tunnel, request_id)
            return prepared if prepared is not None else _bad_gateway("client disconnected")
        finally:
            tunnel.pending.pop(request_id, None)


def register_routes(app: web.Application, manager: TunnelManager, *, apps_proxy: bool = True) -> None:
    """Wire the tunnel endpoints onto the aiohttp app.

    ``apps_proxy`` registers the ``/apps/{app}/{tail}`` proxy route; leave it
    off on deployments whose relays all sit behind the auth middleware.
    """
    app["tunnels"] = manager
    app.router.add_get("/v1/tunnel/{app_name}", manager.handle_ws)

    if apps_proxy:

        async def _proxy(request: web.Request) -> web.StreamResponse:
            return await manager.forward(request.match_info["app_name"], request)

        app.router.add_route("*", "/apps/{app_name}/{tail:.*}", _proxy)
