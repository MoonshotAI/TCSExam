"""Wire protocol for the reverse tunnel.

Shared between the service (``tcsexam.backend.tunnel``) and the in-worker
agents (``tcsexam.backend.agent_files.sandbox_agent`` and
``judge_session_agent``); an identical copy of this module is uploaded to
the worker alongside the agents, so it must stay **stdlib-only**. Keep the
service-side copy and ``agent_files/tunnel_protocol.py`` byte-identical.

The worker holds the workload (a judge server on localhost) but is
unreachable from the task containers, so the agent dials OUT to the service
over a single WebSocket (``GET /v1/tunnel/{app}``) and the service relays
HTTP requests through it.

Frame layout (binary, big-endian)::

    [1B frame type][16B request id][4B payload length][payload]

* Request id correlates the frames of one relayed HTTP request; control
  frames (READY/DYING/PING/PONG) use ``CONTROL_ID`` (16 zero bytes).
* Payloads of one frame are capped at ``MAX_FRAME`` (16 MiB); bigger bodies
  travel as multiple BODY frames.
* HEAD frame payloads are UTF-8 JSON: ``{method, path, headers}`` for
  requests, ``{status, headers}`` for responses. BODY frames are raw bytes.
  Responses stream: the service writes each RESPONSE_BODY to the caller as
  it arrives, and RESPONSE_END/ABORT terminate the stream.
"""
from __future__ import annotations

import struct

# request lifecycle (service -> worker)
T_REQUEST_HEAD = 0x01
T_REQUEST_BODY = 0x02
T_REQUEST_END = 0x03
T_REQUEST_ABORT = 0x04  # caller went away; worker drops the upstream request
# response lifecycle (worker -> service)
T_RESPONSE_HEAD = 0x11
T_RESPONSE_BODY = 0x12
T_RESPONSE_END = 0x13
T_RESPONSE_ABORT = 0x14  # payload: UTF-8 reason
# tunnel control (worker -> service)
T_READY = 0x21  # payload: JSON {app_name, port, label, function_name}
T_DYING = 0x22  # payload: JSON {reason} — the serve process died
# keepalive (either direction; payloads are echoed)
T_PING = 0x31
T_PONG = 0x32

CONTROL_ID = b"\x00" * 16
MAX_FRAME = 16 * 1024 * 1024

_HEADER = struct.Struct(">B16sI")


class ProtocolError(ValueError):
    """Malformed frame (bad length, trailing garbage, ...)."""


def pack_frame(frame_type: int, request_id: bytes, payload: bytes = b"") -> bytes:
    """Serialize one frame."""
    if len(request_id) != 16:
        raise ProtocolError(f"request id must be 16 bytes, got {len(request_id)}")
    if len(payload) > MAX_FRAME:
        raise ProtocolError(f"frame payload {len(payload)} exceeds MAX_FRAME")
    return _HEADER.pack(frame_type, request_id, len(payload)) + payload


class FrameParser:
    """Incremental byte-stream -> frames parser (feed bytes, drain frames)."""

    def __init__(self) -> None:
        self._buf = bytearray()

    def feed(self, data: bytes) -> list[tuple[int, bytes, bytes]]:
        out: list[tuple[int, bytes, bytes]] = []
        self._buf += data
        while True:
            if len(self._buf) < _HEADER.size:
                return out
            frame_type, request_id, length = _HEADER.unpack(bytes(self._buf[: _HEADER.size]))
            if length > MAX_FRAME:
                raise ProtocolError(f"declared payload {length} exceeds MAX_FRAME")
            if len(self._buf) < _HEADER.size + length:
                return out
            payload = bytes(self._buf[_HEADER.size : _HEADER.size + length])
            del self._buf[: _HEADER.size + length]
            out.append((frame_type, request_id, payload))
