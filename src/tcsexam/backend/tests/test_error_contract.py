"""Error-wording contract snapshots.

The task-side clients match on the HTTP status code and the ``error_class``
field of error bodies (verified against the task-side callers during the
extraction); the literals pinned here are the service's own wire constants
(``TRANSIENT_HINT`` inside transient messages, the 502 wording family, the
non-transient error name set, the 401 wording). A rewording anywhere must
fail loudly here.
"""
from __future__ import annotations

from tcsexam.backend.agent_files.sandbox_agent import TunnelClient
from tcsexam.backend.auth import UNAUTHORIZED_MESSAGE
from tcsexam.backend.errors import (
    NON_TRANSIENT_ERROR_NAMES,
    TRANSIENT_HINT,
    is_transient_platform_error,
    transient_suffix,
)
from tcsexam.backend.tunnel import _bad_gateway
from tcsexam.backend.tunnel_protocol import (
    T_RESPONSE_BODY,
    T_RESPONSE_END,
    T_RESPONSE_HEAD,
    FrameParser,
)


def test_transient_hint_exact() -> None:
    assert TRANSIENT_HINT == "please try again"


def test_transient_suffix_exact() -> None:
    assert transient_suffix() == " (transient platform error, please try again)"


def test_non_transient_error_names_exact() -> None:
    assert NON_TRANSIENT_ERROR_NAMES == frozenset(
        {
            "AuthenticationError",
            "PermissionDeniedError",
            "InvalidArgumentError",
            "InsufficientCreditsError",
            # A judge image that fails at boot is not retry-fixable;
            # its failure must NOT carry the "please try again" hint.
            "JudgeBootError",
        }
    )


def test_is_transient_matches_by_class_name() -> None:
    class AuthenticationError(Exception):
        pass

    class ResourceExhaustedError(Exception):
        pass

    class JudgeBootError(RuntimeError):
        pass

    assert is_transient_platform_error(AuthenticationError("bad token")) is False
    assert is_transient_platform_error(ResourceExhaustedError("pool full")) is True
    assert is_transient_platform_error(ValueError("not a platform error")) is True
    assert is_transient_platform_error(JudgeBootError("broken judge image")) is False


def test_unauthorized_message_exact() -> None:
    assert UNAUTHORIZED_MESSAGE == (
        "unauthorized: bad or missing TCSEXAM_TOKEN_ID/TCSEXAM_TOKEN_SECRET"
    )


def test_bad_gateway_wording_exact() -> None:
    resp = _bad_gateway("app 'x' has no live tunnel (please try again)")
    assert resp.status == 502
    assert resp.text == "502 Bad Gateway: app 'x' has no live tunnel (please try again)"


class _FakeWS:
    """Collects the frames a TunnelClient would send over the wire."""

    def __init__(self) -> None:
        self.messages: list[bytes] = []

    def send_message(self, payload: bytes, opcode: int = 0x2) -> None:
        self.messages.append(payload)


def _drain_frames(ws: _FakeWS):
    parser = FrameParser()
    out = []
    for message in ws.messages:
        out.extend(parser.feed(message))
    return out


def test_agent_upstream_unreachable_502_wording() -> None:
    """The in-worker relay's 502 body carries the retry hint verbatim."""
    ws = _FakeWS()
    client = TunnelClient(ws, target_port=1, connect_timeout=0.1)  # port 1: refused
    request_id = b"\x07" * 16
    client._handle(request_id, {"method": "GET", "path": "/health", "headers": {}}, b"")
    frames = _drain_frames(ws)
    types = [t for t, _, _ in frames]
    assert types[0] == T_RESPONSE_HEAD
    assert T_RESPONSE_BODY in types and types[-1] == T_RESPONSE_END
    body = next(p for t, _, p in frames if t == T_RESPONSE_BODY)
    assert body.startswith(b"502 Bad Gateway: upstream unreachable: ")
    assert body.endswith(b" (please try again)")
