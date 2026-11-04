"""Shared-token auth middleware (the service's single-token gate) plus the
caller-identity (run-id) layer.

Clients authenticate with the ``X-TCSEXAM-Token-Id`` /
``X-TCSEXAM-Token-Secret`` headers. The check is skipped entirely when no
token is configured, and for infrastructure paths selected by the
``is_exempt`` predicate.

Run-id: non-exempt requests may carry ``X-TCSEXAM-Run-Id``, a readable
per-attempt label (the task clients derive it from ``TCSEXAM_RUN_ID`` or the
container hostname). The validated value lands in ``request["run_id"]``
("" when absent/invalid) and feeds the per-caller request counting surfaced
at ``GET /v1/status`` (``callers``). The ``run_id_mode`` config field
selects the enforcement:

* ``warn`` (default) — missing/malformed headers log a throttled WARNING
  (one per minute per (token, ip, path)); the response is unaffected;
* ``required`` — missing/malformed headers are rejected 400
  (:data:`errors.INVALID_RUN_ID_MESSAGE`);
* ``off`` — the header is not read at all.

Attribution attrs: the request's "attribution attrs"
(``request["attrs"]``) are synthesized from the identity headers:

* ``TCSEXAM_RUN_ID`` — the effective run-id ("" when absent/invalid);
* ``TCSEXAM_CLIENT_ID`` — the ``X-TCSEXAM-Client-Id`` singleflight-dedup
  header, when present;
* ``TCSEXAM_AGENT_NAME`` — the ``X-TCSEXAM-Agent-Name`` header, when present
  (an opaque caller-chosen agent label).
"""
from __future__ import annotations

import logging
import hmac
import time
from typing import Any, Callable

from aiohttp import web

from .errors import INVALID_RUN_ID_MESSAGE
from .status import classify_path

LOGGER = logging.getLogger("tcsexam.backend.auth")

#: 401 body wording — a contract with the clients' error surfacing.
UNAUTHORIZED_MESSAGE = "unauthorized: bad or missing TCSEXAM_TOKEN_ID/TCSEXAM_TOKEN_SECRET"

#: Service auth headers.
TOKEN_ID_HEADER = "X-TCSEXAM-Token-Id"
TOKEN_SECRET_HEADER = "X-TCSEXAM-Token-Secret"

#: Caller-identity header and its validation rules (format only — honor system).
RUN_ID_HEADER = "X-TCSEXAM-Run-Id"
MAX_RUN_ID_LENGTH = 128

#: The singleflight dedup header; it also joins the attrs as TCSEXAM_CLIENT_ID.
CLIENT_ID_HEADER = "X-TCSEXAM-Client-Id"

#: Optional opaque agent label carried by the clients.
AGENT_NAME_HEADER = "X-TCSEXAM-Agent-Name"

#: Attribution attr keys (the synthesized ``request["attrs"]`` dict).
ATTR_RUN_ID = "TCSEXAM_RUN_ID"
ATTR_AGENT_NAME = "TCSEXAM_AGENT_NAME"
ATTR_CLIENT_ID = "TCSEXAM_CLIENT_ID"

#: Attr value length cap (headers are caller-controlled; nothing unbounded
#: lands in memory).
MAX_ATTR_VALUE_LENGTH = 256


def resolve_identity(request: web.Request) -> str:
    """The client identity for per-run accounting.

    ``X-Forwarded-For`` first value when present, else ``request.remote``.
    Deploy this service behind a reverse proxy that REWRITES the XFF header
    to the real client address (discarding any client-forged value); the
    first XFF entry is then a trustworthy identity while the raw remote is
    the proxy's own address (useless as an identity). Comma-chained XFF
    yields its first entry.
    """
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        first = xff.split(",", 1)[0].strip()
        if first:
            return first
    return request.remote or "-"


#: Valid ``run_id_mode`` config values.
RUN_ID_MODES = ("warn", "required", "off")

#: Predicate deciding whether a request skips the token check.
ExemptPredicate = Callable[[web.Request], bool]


def is_valid_run_id(value: str) -> bool:
    """Format gate: non-empty, <= 128 chars, printable ASCII (0x20-0x7E)."""
    return (
        bool(value)
        and len(value) <= MAX_RUN_ID_LENGTH
        and all(0x20 <= ord(ch) <= 0x7E for ch in value)
    )


def resolve_run_id(headers: Any) -> str | None:
    """Effective run-id: the ``X-TCSEXAM-Run-Id`` header when valid, else
    None (an invalid value counts as missing for warn/required purposes)."""
    raw = headers.get(RUN_ID_HEADER)
    if raw is not None and is_valid_run_id(raw):
        return raw
    return None


def health_only(request: web.Request) -> bool:
    """Exempt only the liveness probe (the strictest shape)."""
    return request.path == "/v1/health"


def health_and_apps(request: web.Request) -> bool:
    """Exempt ``/v1/health`` and the ``/apps/*`` tunnel-proxy paths.

    ``/apps/{app}/...`` requests are workload requests proxied through the
    tunnel, carrying only the upstream server's own credentials, not the
    service token; they are gated per-session by
    ``TunnelManager.session_tokens`` instead.
    """
    return request.path == "/v1/health" or request.path.startswith("/apps/")


class _WarnThrottle:
    """One log line per ``interval_seconds`` per key (missing-header warnings
    must not flood the journal when a legacy client storms).
    """

    def __init__(
        self,
        interval_seconds: float = 60.0,
        *,
        now: Callable[[], float] = time.monotonic,
        max_keys: int = 4096,
    ) -> None:
        self._interval = interval_seconds
        self._now = now
        self._max_keys = max_keys
        self._last: dict[tuple[str, str, str], float] = {}

    def allow(self, key: tuple[str, str, str]) -> bool:
        now = self._now()
        last = self._last.get(key)
        if last is not None and now - last < self._interval:
            return False
        if len(self._last) >= self._max_keys:
            cutoff = now - self._interval
            self._last = {k: ts for k, ts in self._last.items() if ts > cutoff}
        self._last[key] = now
        return True


def make_auth_middleware(
    is_exempt: ExemptPredicate | None = None,
    *,
    unauthorized_message: str = UNAUTHORIZED_MESSAGE,
    counter: Any = None,
) -> Callable[..., Any]:
    """Build the shared-token middleware; a no-op when no token is configured.

    ``is_exempt(request)`` selects the paths that skip the check; it defaults
    to :func:`health_only`. ``counter`` is an optional request counter (see
    ``status.RequestCounter``): every request reaching the service is counted
    by path bucket — exempt and rejected ones included, a 401 storm is load
    too. Non-exempt requests additionally feed the per-caller
    (token_id, run_id, agent_name) counting; see the module docstring for the
    run-id modes and the attribution-attrs synthesis.
    """
    exempt = is_exempt or health_only
    throttle = _WarnThrottle()

    @web.middleware
    async def _auth_middleware(request: web.Request, handler: Any) -> web.Response:
        config = request.app["config"]
        if counter is not None:
            counter.record(request.path)
        # Proxy-attested identity, stamped on every request — the
        # submission-cap counter and the client_ip query key on it.
        request["identity"] = resolve_identity(request)
        is_exempt_request = exempt(request)
        mode = getattr(config, "run_id_mode", "warn")
        if mode not in RUN_ID_MODES:
            mode = "warn"  # create_app validates at startup; stay total here
        attrs: dict[str, str] = {}
        if not is_exempt_request:
            # Attribution attrs: the dedup client id and the opaque agent
            # label; the TCSEXAM_RUN_ID synthesis happens in the mode-gated
            # block below.
            client_id = request.headers.get(CLIENT_ID_HEADER)
            if client_id:
                attrs[ATTR_CLIENT_ID] = client_id[:MAX_ATTR_VALUE_LENGTH]
            agent_name = request.headers.get(AGENT_NAME_HEADER)
            if agent_name:
                attrs[ATTR_AGENT_NAME] = agent_name[:MAX_ATTR_VALUE_LENGTH]
            request["attrs"] = attrs
        if not is_exempt_request and mode != "off":
            token = request.headers.get(TOKEN_ID_HEADER) or "-"
            raw = request.headers.get(RUN_ID_HEADER)
            run_id = resolve_run_id(request.headers)
            request["run_id"] = run_id or ""
            attrs[ATTR_RUN_ID] = run_id or ""
            if counter is not None:
                # Probe paths (/v1/health, /v1/status) are not caller
                # traffic — classify_path returns None for them, so skip the
                # caller count too.
                if classify_path(request.path) is not None:
                    counter.record_caller(token, run_id or "", attrs.get(ATTR_AGENT_NAME) or "")
            if run_id is None:
                if mode == "required":
                    return web.json_response({"error": INVALID_RUN_ID_MESSAGE}, status=400)
                if throttle.allow((token, request.remote or "-", request.path)):
                    reason = "missing" if raw is None else f"malformed ({raw[:80]!r})"
                    LOGGER.warning(
                        "request without a valid run-id (%s header): %s, token=%s "
                        "ip=%s path=%s (run_id_mode=warn, served normally)",
                        RUN_ID_HEADER,
                        reason,
                        token,
                        request.remote or "-",
                        request.path,
                    )
        if not is_exempt_request and config.auth_enabled:
            config.validate_auth()
            # Primary pair plus any rotation-window additional pairs.
            offered = (
                request.headers.get(TOKEN_ID_HEADER, "").encode("utf-8", errors="surrogatepass"),
                request.headers.get(TOKEN_SECRET_HEADER, "").encode("utf-8", errors="surrogatepass"),
            )
            valid = [(config.token_id, config.token_secret), *config.additional_tokens]
            matched = False
            for token_id, token_secret in valid:
                matched |= (
                    hmac.compare_digest(offered[0], token_id.encode("utf-8", errors="surrogatepass"))
                    & hmac.compare_digest(offered[1], token_secret.encode("utf-8", errors="surrogatepass"))
                )
            if not matched:
                return web.json_response({"error": unauthorized_message}, status=401)
        return await handler(request)

    return _auth_middleware
