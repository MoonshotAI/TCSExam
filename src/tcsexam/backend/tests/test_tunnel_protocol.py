"""Tunnel wire-protocol codec tests: frame round trips, fragmentation,
protocol-error paths. Pure stdlib, no I/O.
"""
from __future__ import annotations

import pytest

from tcsexam.backend.tunnel_protocol import (
    CONTROL_ID,
    MAX_FRAME,
    T_PING,
    T_REQUEST_BODY,
    T_REQUEST_HEAD,
    FrameParser,
    ProtocolError,
    pack_frame,
)


def test_pack_parse_roundtrip() -> None:
    frame = pack_frame(T_REQUEST_HEAD, b"\x01" * 16, b'{"method":"GET"}')
    parser = FrameParser()
    out = parser.feed(frame)
    assert out == [(T_REQUEST_HEAD, b"\x01" * 16, b'{"method":"GET"}')]


def test_empty_payload_roundtrip() -> None:
    parser = FrameParser()
    assert parser.feed(pack_frame(T_PING, CONTROL_ID)) == [(T_PING, CONTROL_ID, b"")]


def test_multiple_frames_in_one_buffer() -> None:
    buf = (
        pack_frame(T_REQUEST_HEAD, b"\x02" * 16, b"head")
        + pack_frame(T_REQUEST_BODY, b"\x02" * 16, b"body-bytes")
        + pack_frame(T_PING, CONTROL_ID, b"ping")
    )
    parser = FrameParser()
    out = parser.feed(buf)
    assert [t for t, _, _ in out] == [T_REQUEST_HEAD, T_REQUEST_BODY, T_PING]
    assert out[1][2] == b"body-bytes"


def test_fragmented_delivery_byte_by_byte() -> None:
    frame = pack_frame(T_REQUEST_BODY, b"\x03" * 16, b"x" * 5000)
    parser = FrameParser()
    out = []
    for i in range(len(frame)):
        out.extend(parser.feed(frame[i : i + 1]))
    assert out == [(T_REQUEST_BODY, b"\x03" * 16, b"x" * 5000)]


def test_max_frame_payload_accepted() -> None:
    frame = pack_frame(T_REQUEST_BODY, b"\x04" * 16, b"y" * MAX_FRAME)
    parser = FrameParser()
    assert parser.feed(frame)[0][2] == b"y" * MAX_FRAME


def test_oversized_pack_rejected() -> None:
    with pytest.raises(ProtocolError):
        pack_frame(T_REQUEST_BODY, b"\x05" * 16, b"z" * (MAX_FRAME + 1))


def test_oversized_declared_length_rejected() -> None:
    # A header declaring more than MAX_FRAME must fail before any body read.
    import struct

    bad = struct.pack(">B16sI", T_REQUEST_BODY, b"\x06" * 16, MAX_FRAME + 1)
    parser = FrameParser()
    with pytest.raises(ProtocolError):
        parser.feed(bad)


def test_request_id_length_validated() -> None:
    with pytest.raises(ProtocolError):
        pack_frame(T_PING, b"short")
