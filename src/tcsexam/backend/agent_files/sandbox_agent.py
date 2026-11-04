"""In-worker relay core for the reverse tunnel: WSClient + TunnelClient.

Uploaded to throwaway judge workers next to the shape's entry agent
(``judge_session_agent.py``) and imported by it under the FLAT name
``sandbox_agent`` — the ``__package__`` check below resolves the import
relatively on the service side and by bare top-level name inside the worker.
**Stdlib only** — the worker image has no websockets/aiohttp guarantee, so
the WebSocket client below is a from-scratch RFC 6455 implementation.
``tunnel_protocol.py`` is uploaded next to this file.

* ``WSClient``: one WebSocket to the service's ``/v1/tunnel/{app}`` endpoint,
  all socket I/O on a single background thread.
* ``TunnelClient``: relays tunnel request frames to the in-worker server on
  ``http://127.0.0.1:<port>`` and streams the response frames back.
"""
from __future__ import annotations

import base64
import hashlib
import http.client
import json
import os
import queue
import socket
import ssl
import struct
import sys
import threading
import time
import traceback
from pathlib import Path

_HERE = Path(__file__).resolve().parent

if __package__:
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
else:  # flat layout: uploaded to the worker, imported by bare name
    sys.path.insert(0, str(_HERE))
    from tunnel_protocol import (  # noqa: E402
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

_WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
_HOP_BY_HOP = frozenset(
    {
        "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
        "te", "trailer", "transfer-encoding", "upgrade", "host", "content-length",
    }
)
_READ_CHUNK = 65536


def log(msg: str) -> None:
    print(f"[sandbox_agent {time.strftime('%H:%M:%S')}] {msg}", flush=True)


# --------------------------------------------------------------------------- #
# Minimal RFC 6455 client (client frames are masked; server frames are not)
# --------------------------------------------------------------------------- #
def _encode_ws_frame(opcode: int, payload: bytes) -> bytes:
    """Build one client->server WS frame (FIN set, masked per RFC 6455)."""
    header = bytearray([0x80 | opcode])
    length = len(payload)
    if length < 126:
        header.append(0x80 | length)
    elif length < 65536:
        header.append(0x80 | 126)
        header += struct.pack(">H", length)
    else:
        header.append(0x80 | 127)
        header += struct.pack(">Q", length)
    mask = os.urandom(4)
    header += mask
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    return bytes(header) + masked


class WSClient:
    """WebSocket client over one TCP(/TLS) connection.

    All socket I/O happens in a SINGLE background thread (selector loop):
    callers hand complete frames to a send queue, and complete messages arrive
    on a receive queue. This matters because the production path is wss:// —
    an ``SSLSocket`` must never be driven by concurrent recv/send from
    different threads (a post-handshake TLS event racing a write corrupts the
    session); with one I/O thread that whole failure class is impossible.
    """

    def __init__(self, url: str, headers: dict[str, str], timeout: float = 60.0) -> None:
        self.url = url
        self.headers = headers
        self.timeout = timeout
        self.sock: socket.socket | None = None
        self._inbox: queue.Queue[bytes | None] = queue.Queue()  # None = closed
        self._outq: queue.Queue[bytes] = queue.Queue()
        self._closed = threading.Event()
        self._wake_r: socket.socket | None = None
        self._wake_w: socket.socket | None = None
        self.stats = {"pings": 0, "pongs": 0, "messages_in": 0, "frames_out": 0}

    # --------------------------- connection ------------------------------ #
    def connect(self) -> None:
        rest = self.url.split("://", 1)[1]
        scheme = self.url.split("://", 1)[0]
        hostport, _, path = rest.partition("/")
        path = "/" + path
        host, _, port_s = hostport.partition(":")
        port = int(port_s) if port_s else (443 if scheme == "wss" else 80)
        raw = socket.create_connection((host, port), timeout=self.timeout)
        if scheme == "wss":
            ctx = ssl.create_default_context()
            raw = ctx.wrap_socket(raw, server_hostname=host)
        self.sock = raw
        key = base64.b64encode(os.urandom(16)).decode()
        lines = [
            f"GET {path} HTTP/1.1",
            f"Host: {hostport}",
            "Upgrade: websocket",
            "Connection: Upgrade",
            f"Sec-WebSocket-Key: {key}",
            "Sec-WebSocket-Version: 13",
            *[f"{k}: {v}" for k, v in self.headers.items()],
            "",
            "",
        ]
        raw.sendall("\r\n".join(lines).encode())
        head, leftover = self._read_http_head()
        status_line = head.split("\r\n", 1)[0]
        if " 101" not in status_line:
            raise ConnectionError(f"WebSocket upgrade refused: {status_line} | {head[:400]}")
        accept = base64.b64encode(hashlib.sha1((key + _WS_GUID).encode()).digest()).decode()
        if accept not in head:
            raise ConnectionError("WebSocket upgrade returned a bad Sec-WebSocket-Accept")
        raw.setblocking(False)
        self._wake_r, self._wake_w = socket.socketpair()
        self._wake_r.setblocking(False)
        self._wake_w.setblocking(False)
        threading.Thread(target=self._io_main, args=(leftover,), daemon=True).start()

    def _read_http_head(self) -> tuple[str, bytes]:
        """Read the 101 response; returns (head, leftover).

        The leftover matters: any WS frame bytes that arrived coalesced with
        the handshake response must seed the frame parser, not be dropped.
        """
        assert self.sock is not None
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("connection closed during the WS handshake")
            buf += chunk
        head, _, leftover = buf.partition(b"\r\n\r\n")
        return head.decode(errors="replace"), leftover

    def close(self) -> None:
        """Close the connection (best-effort close frame, then TCP)."""
        if self._closed.is_set():
            return
        try:
            self.send_message(b"", opcode=0x8)
            time.sleep(0.05)  # give the I/O thread a beat to flush the close
        except Exception:  # noqa: BLE001
            pass
        self._closed.set()
        for sock in (self._wake_w, self._wake_r, self.sock):
            try:
                if sock is not None:
                    sock.close()
            except Exception:  # noqa: BLE001
                pass
        self._inbox.put(None)

    # --------------------------- public API ------------------------------ #
    def send_message(self, payload: bytes, opcode: int = 0x2) -> None:
        """Queue one message as a single WS frame (masked). Thread-safe."""
        if self._closed.is_set():
            raise ConnectionError("tunnel is closed")
        self._outq.put(_encode_ws_frame(opcode, payload))
        self.stats["frames_out"] += 1
        try:
            if self._wake_w is not None:
                self._wake_w.send(b"\0")
        except (BlockingIOError, OSError):
            pass

    def recv_message(self) -> bytes | None:
        """Return the next complete message, or None when the tunnel closed."""
        return self._inbox.get()

    # --------------------------- the I/O thread -------------------------- #
    def _io_main(self, leftover: bytes) -> None:
        import selectors

        sel = selectors.DefaultSelector()
        sock = self.sock
        assert sock is not None and self._wake_r is not None
        sel.register(sock, selectors.EVENT_READ, "sock")
        sel.register(self._wake_r, selectors.EVENT_READ, "wake")
        inbuf = bytearray(leftover)
        outbuf = bytearray()
        message = bytearray()
        try:
            while not self._closed.is_set():
                for key, _ in sel.select(timeout=1.0):
                    if key.data == "wake":
                        try:
                            self._wake_r.recv(65536)
                        except (BlockingIOError, OSError):
                            pass
                        continue
                    try:
                        chunk = sock.recv(1 << 16)
                    except (ssl.SSLWantReadError, ssl.SSLWantWriteError, BlockingIOError):
                        chunk = None
                    if chunk == b"":
                        raise ConnectionError("tunnel socket closed by the service")
                    if chunk is not None:
                        inbuf += chunk
                while True:
                    try:
                        outbuf += self._outq.get_nowait()
                    except queue.Empty:
                        break
                while outbuf:
                    try:
                        sent = sock.send(bytes(outbuf[: 1 << 16]))
                    except (ssl.SSLWantReadError, ssl.SSLWantWriteError, BlockingIOError):
                        break
                    del outbuf[:sent]
                while True:
                    frame = self._take_ws_frame(inbuf)
                    if frame is None:
                        break
                    fin, opcode, payload = frame
                    if opcode == 0x8:  # close
                        code: int | None = None
                        reason = ""
                        if len(payload) >= 2:
                            (code,) = struct.unpack(">H", payload[:2])
                            reason = payload[2:].decode(errors="replace")
                        log(f"tunnel closed by the service (code={code} reason={reason!r})")
                        try:
                            sock.sendall(_encode_ws_frame(0x8, payload))
                        except Exception:  # noqa: BLE001
                            pass
                        return
                    if opcode == 0x9:  # ping -> pong (aiohttp heartbeat)
                        self.stats["pings"] += 1
                        self._outq.put(_encode_ws_frame(0xA, payload))
                        self.stats["pongs"] += 1
                        log(f"heartbeat ping #{self.stats['pings']} -> pong queued")
                        continue
                    if opcode == 0xA:  # pong
                        continue
                    if opcode in (0x1, 0x2, 0x0):
                        message += payload
                        if fin:
                            self.stats["messages_in"] += 1
                            self._inbox.put(bytes(message))
                            message = bytearray()
        except (ConnectionError, OSError, ssl.SSLError) as exc:
            log(f"tunnel socket lost: {type(exc).__name__}: {exc}")
        except BaseException:
            # Anything else would otherwise kill this thread SILENTLY (the
            # finally still unblocks recv_message, the main thread returns,
            # and the agent vanishes from the tunnel with no word). Log the
            # full traceback to agent.log — the service pulls it on teardown.
            log("tunnel I/O loop crashed:\n" + traceback.format_exc())
        finally:
            try:
                sel.close()
            except Exception:  # noqa: BLE001
                pass
            try:
                sock.close()
            except Exception:  # noqa: BLE001
                pass
            was_closed = self._closed.is_set()
            self._closed.set()
            self._inbox.put(None)
            if not was_closed:
                log("tunnel I/O loop exited")

    @staticmethod
    def _take_ws_frame(buf: bytearray) -> tuple[bool, int, bytes] | None:
        """Pop one complete WS frame off ``buf``; None when incomplete."""
        if len(buf) < 2:
            return None
        first, second = buf[0], buf[1]
        fin = bool(first & 0x80)
        opcode = first & 0x0F
        masked = bool(second & 0x80)
        length = second & 0x7F
        pos = 2
        if length == 126:
            if len(buf) < 4:
                return None
            (length,) = struct.unpack(">H", buf[2:4])
            pos = 4
        elif length == 127:
            if len(buf) < 10:
                return None
            (length,) = struct.unpack(">Q", buf[2:10])
            pos = 10
        mask = b""
        if masked:
            if len(buf) < pos + 4:
                return None
            mask = bytes(buf[pos : pos + 4])
            pos += 4
        if len(buf) < pos + length:
            return None
        payload = bytes(buf[pos : pos + length])
        del buf[: pos + length]
        if masked:
            payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        return fin, opcode, payload


# --------------------------------------------------------------------------- #
# Tunnel client: frames <-> localhost HTTP
# --------------------------------------------------------------------------- #
class TunnelClient:
    """Relays tunnel request frames to the in-worker server and streams the
    responses back. One handler thread per request; sends are serialized.

    Upstream timeouts are split on purpose: a short CONNECT timeout (the local
    server down/not listening must fail fast into the 502 path) and a long
    READ timeout (multi-minute generations are legitimate). A caller
    disconnect arrives as T_REQUEST_ABORT and closes the upstream connection,
    freeing the handler thread.
    """

    def __init__(
        self,
        ws: WSClient,
        target_port: int,
        *,
        connect_timeout: float = 10.0,
        read_timeout: float = 900.0,
    ) -> None:
        self.ws = ws
        self.target_port = target_port
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self._bodies: dict[bytes, list] = {}
        self._conns: dict[bytes, http.client.HTTPConnection] = {}
        self._conns_lock = threading.Lock()
        self._send_lock = threading.Lock()
        self.stats = {"aborts": 0}

    def send_frame(self, frame_type: int, request_id: bytes, payload: bytes = b"") -> None:
        with self._send_lock:
            self.ws.send_message(pack_frame(frame_type, request_id, payload))

    def run_forever(self) -> None:
        parser = FrameParser()
        while True:
            try:
                message = self.ws.recv_message()
            except (ConnectionError, OSError):
                log("tunnel socket lost")
                return
            if message is None:
                log("tunnel closed by the service")
                return
            try:
                frames = parser.feed(message)
            except Exception as exc:  # noqa: BLE001 - stream desync is unrecoverable
                log(f"frame parser desync ({exc}); dropping the tunnel\n{traceback.format_exc()}")
                return
            for frame_type, request_id, payload in frames:
                try:
                    self._dispatch(frame_type, request_id, payload)
                except Exception:  # noqa: BLE001 - one bad frame must not kill the agent
                    log(f"frame dispatch failed (type={frame_type:#x}):\n{traceback.format_exc()}")

    def _dispatch(self, frame_type: int, request_id: bytes, payload: bytes) -> None:
        if frame_type == T_PING:
            self.send_frame(T_PONG, CONTROL_ID, payload)
            return
        if frame_type == T_REQUEST_HEAD:
            head = json.loads(payload.decode())
            self._bodies[request_id] = [head, bytearray()]
            return
        if frame_type == T_REQUEST_BODY:
            entry = self._bodies.get(request_id)
            if entry is not None:
                entry[1] += payload
            return
        if frame_type == T_REQUEST_END:
            entry = self._bodies.pop(request_id, None)
            if entry is None:
                return
            head, body = entry
            threading.Thread(
                target=self._handle, args=(request_id, head, bytes(body)), daemon=True
            ).start()
            return
        if frame_type == T_REQUEST_ABORT:
            # The caller went away mid-request: close the upstream connection
            # so the handler thread stops instead of lingering on a dead call.
            self.stats["aborts"] += 1
            self._bodies.pop(request_id, None)
            with self._conns_lock:
                conn = self._conns.pop(request_id, None)
            if conn is not None:
                try:
                    conn.close()
                except Exception:  # noqa: BLE001
                    pass
            return

    def _handle(self, request_id: bytes, head: dict, body: bytes) -> None:
        conn: http.client.HTTPConnection | None = None
        try:
            # Short CONNECT timeout (fail fast while the local server is
            # down); the long READ timeout is applied to the connected socket
            # below.
            conn = http.client.HTTPConnection(
                "127.0.0.1", self.target_port, timeout=self.connect_timeout
            )
            with self._conns_lock:
                self._conns[request_id] = conn
            conn.request(
                head["method"],
                head["path"],
                body=body or None,
                headers={k: v for k, v in (head.get("headers") or {}).items() if k.lower() not in _HOP_BY_HOP},
            )
            if conn.sock is not None:
                conn.sock.settimeout(self.read_timeout)
            resp = conn.getresponse()
        except Exception as exc:  # noqa: BLE001 - upstream not up yet / crashed / aborted
            with self._conns_lock:
                self._conns.pop(request_id, None)
            payload = json.dumps(
                {"status": 502, "headers": {"Content-Type": "text/plain"}}
            ).encode()
            try:
                self.send_frame(T_RESPONSE_HEAD, request_id, payload)
                self.send_frame(
                    T_RESPONSE_BODY,
                    request_id,
                    f"502 Bad Gateway: upstream unreachable: {exc} (please try again)".encode(),
                )
                self.send_frame(T_RESPONSE_END, request_id)
            except Exception:  # noqa: BLE001 - tunnel already gone
                pass
            return
        try:
            meta = json.dumps(
                {
                    "status": resp.status,
                    "headers": {k: v for k, v in resp.getheaders() if k.lower() not in _HOP_BY_HOP},
                }
            ).encode()
            self.send_frame(T_RESPONSE_HEAD, request_id, meta)
            while True:
                # read1 (not read): returns as soon as ONE chunk is available,
                # which is what keeps SSE streaming end to end.
                chunk = resp.read1(_READ_CHUNK)
                if not chunk:
                    break
                self.send_frame(T_RESPONSE_BODY, request_id, chunk)
            self.send_frame(T_RESPONSE_END, request_id)
        except Exception as exc:  # noqa: BLE001 - upstream died / aborted mid-stream
            try:
                self.send_frame(T_RESPONSE_ABORT, request_id, str(exc).encode())
            except Exception:  # noqa: BLE001
                pass
        finally:
            with self._conns_lock:
                self._conns.pop(request_id, None)
            conn.close()
