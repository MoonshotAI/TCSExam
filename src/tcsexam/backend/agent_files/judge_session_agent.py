"""In-worker agent for the judge-session shape.

Uploaded to a throwaway judge worker (the task's self-contained judge
image) by ``JudgeSessionStore.create`` and run as a plain root process. It:

1. optionally writes inline payload files (the judge_payload override
   scenario — the stock path needs none: the image already bakes the judge
   server and its data);
2. starts the judge server (``command`` from agent_config.json; an EMPTY
   command skips the process start and the process watch — the agent then
   only relays to an already-running server) with ``PORT`` in the env;
3. waits until the server answers its health endpoint;
4. dials the service's ``/v1/tunnel/{app}`` WebSocket and relays each request
   to ``http://127.0.0.1:<port>`` (the reverse tunnel: the worker can reach
   the service, task containers can only reach the service);
5. reports READY once connected, and DYING + exits when the judge server
   process dies (the service then reaps the worker).

agent_config.json keys (unknown keys are ignored, missing keys have
defaults): ``app_name``/``service_ws_url`` (required), ``port`` (8082),
``command`` (empty = relay only), ``health_path`` (/health),
``boot_timeout_seconds`` (600), ``read_timeout_seconds`` (7200),
``ready_label``, ``env``, ``payload_files``, ``token_id``/``token_secret``.

Stdlib only; reuses the WSClient/TunnelClient relay core from
``sandbox_agent.py`` (uploaded next to this file).
"""
from __future__ import annotations

import base64
import json
import os
import shlex  # noqa: F401  (kept for parity with the original agent file)
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

_HERE = Path(__file__).resolve().parent

if __package__:
    from .sandbox_agent import TunnelClient, WSClient, log
    from .tunnel_protocol import CONTROL_ID, T_READY
else:  # flat layout: uploaded to the worker, imported by bare name
    sys.path.insert(0, str(_HERE))
    from sandbox_agent import TunnelClient, WSClient, log  # noqa: E402
    from tunnel_protocol import CONTROL_ID, T_READY  # noqa: E402

_ENGINE_LOG = "judge_server.log"


# Proxy-bypassing opener for the localhost health probe. Some judge images
# bake http_proxy/https_proxy (build-time proxy leftovers) into their ENV
# without no_proxy; the worker DNS cannot resolve the proxy host, so a plain
# urlopen to 127.0.0.1 dies on *proxy name resolution* and the agent never
# sees the judge healthy.
_NO_PROXY_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _engine_health(port: int, health_path: str) -> tuple[bool, str | None]:
    """Probe the judge server's health endpoint.

    Returns ``(healthy, fatal)``: ``healthy`` is True on HTTP 200. ``fatal``
    is the judge-reported terminal error string when the endpoint answers the
    error state of the three-state contract (``{"status": "error", "error":
    ...}``); anything else (connection refused, non-JSON, ``"starting"``)
    means keep waiting: ``(False, None)``.
    """
    body = b""
    try:
        with _NO_PROXY_OPENER.open(f"http://127.0.0.1:{port}{health_path}", timeout=3) as r:
            if r.status == 200:
                return True, None
            body = r.read(4096)
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read(4096)
        except Exception:
            body = b""
    except Exception:
        return False, None
    try:
        payload = json.loads(body.decode("utf-8", "replace"))
    except Exception:
        return False, None
    if isinstance(payload, dict) and payload.get("status") == "error":
        return False, str(payload.get("error") or payload)
    return False, None


def _connect_with_retry(
    ws: WSClient, *, attempts: int = 10, base_delay: float = 2.0, max_delay: float = 30.0
) -> None:
    """Dial the service tunnel with exponential backoff.

    The service may briefly refuse the WebSocket upgrade (its own restart,
    reverse-proxy convergence, a transient network fault). Without retries
    the whole judge session dies on a single transient dial failure even
    though the freshly-booted judge server is healthy. ``connect()`` builds a
    fresh socket per call, so retrying on the same WSClient is safe.
    """
    for attempt in range(1, attempts + 1):
        try:
            ws.connect()
            return
        except Exception as exc:
            if attempt >= attempts:
                raise
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            log(f"tunnel dial failed (attempt {attempt}/{attempts}): {exc}; retrying in {delay:g}s")
            time.sleep(delay)


def _tunnel_serve_loop(
    config: dict,
    proc: "subprocess.Popen | None",
    port: int,
    read_timeout: float,
    app_name: str,
    ready_label: str,
    headers: dict,
) -> int:
    """Serve the reverse tunnel with reconnect-after-drop.

    The agent redials with backoff and resumes on tunnel drops (READY is
    re-sent on every connect; the service holds the session for its
    reconnect grace window), and exits only when the judge server is gone.
    """
    ready_payload = json.dumps(
        {"app_name": app_name, "port": port, "label": ready_label}
    ).encode()
    backoff = 1.0
    while True:
        try:
            ws = WSClient(config["service_ws_url"], headers=headers)
            _connect_with_retry(ws)
        except Exception as exc:
            if proc is not None and proc.poll() is not None:
                log("judge server is gone; giving up on the tunnel")
                return 1
            log(f"tunnel dial round failed ({exc}); retrying in {backoff:g}s")
            time.sleep(backoff)
            backoff = min(backoff * 2, 60.0)
            continue
        client = TunnelClient(ws, target_port=port, read_timeout=read_timeout)
        client.send_frame(T_READY, CONTROL_ID, ready_payload)
        log("tunnel connected, READY sent")
        client.run_forever()  # returns when the tunnel drops
        if proc is not None and proc.poll() is not None:
            log("judge server gone and tunnel dropped; exiting")
            return 1
        log("tunnel dropped; redialing")
        backoff = 1.0


def main() -> int:
    config = json.loads(Path("agent_config.json").read_text())
    port = int(config.get("port", 8082))
    app_name = config["app_name"]
    command = str(config.get("command") or "")
    health_path = str(config.get("health_path") or "/health")
    boot_timeout = float(config.get("boot_timeout_seconds", 600))
    read_timeout = float(config.get("read_timeout_seconds", 7200.0))
    ready_label = str(config.get("ready_label") or "judge-session")

    # judge_payload override: inline files written before the server starts
    # (engine-override scenario only; the stock shape ships them in the image).
    for path, b64 in (config.get("payload_files") or {}).items():
        dest = Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(base64.b64decode(b64))
        log(f"payload file written: {path} ({dest.stat().st_size} bytes)")

    proc: subprocess.Popen | None = None
    if command:
        env = dict(os.environ)
        env["PORT"] = str(port)
        env.update({str(k): str(v) for k, v in (config.get("env") or {}).items()})
        log(f"starting judge server ({command}, port={port})")
        engine_log = open(_ENGINE_LOG, "ab")
        proc = subprocess.Popen(
            command,
            shell=True,
            env=env,
            stdout=engine_log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

        deadline = time.time() + boot_timeout
        while time.time() < deadline:
            if proc.poll() is not None:
                # BOOT-FATAL sentinel: the service polls agent.log during the
                # tunnel wait and fails the session within seconds instead of
                # waiting out the whole boot budget.
                log(f"BOOT-FATAL: judge server exited early rc={proc.returncode}")
                return 1
            healthy, fatal = _engine_health(port, health_path)
            if fatal is not None:
                log(f"BOOT-FATAL: {fatal}")
                return 1
            if healthy:
                break
            time.sleep(2)
        else:
            log(f"judge server did not become healthy within {boot_timeout:g}s")
            return 1
        log("judge server healthy; dialing service tunnel")

    headers = {}
    if config.get("token_id"):
        headers["X-TCSEXAM-Token-Id"] = str(config["token_id"])
        headers["X-TCSEXAM-Token-Secret"] = str(config.get("token_secret") or "")
    if config.get("run_id"):
        headers["X-TCSEXAM-Run-Id"] = str(config["run_id"])
    if config.get("agent_name"):
        headers["X-TCSEXAM-Agent-Name"] = str(config["agent_name"])

    if proc is not None:

        def _watch_engine() -> None:
            # The supervise loop owns the tunnel across reconnects, so no
            # live client reference is available here; exiting drops the
            # socket, which the service reads as the tunnel closing (the
            # boot-fatal path above already covered boot-time deaths).
            proc.wait()
            log(f"judge server process exited rc={proc.returncode}; exiting")
            os._exit(1)

        threading.Thread(target=_watch_engine, daemon=True).start()
    return _tunnel_serve_loop(config, proc, port, read_timeout, app_name, ready_label, headers)


if __name__ == "__main__":
    sys.exit(main())
