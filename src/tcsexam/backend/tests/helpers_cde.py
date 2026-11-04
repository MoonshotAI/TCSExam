"""Shared harness for the C/D/E acceptance-test groups (full-HTTP, real local
workers).

What this builds per test:

* a REAL backend service (``create_app``) on a background event loop, driven
  only over loopback HTTP (urllib);
* the :class:`LocalProcessAdapter` behind it, so every judge worker is a real
  local subprocess running the real ``judge_session_agent.py`` that dials the
  service tunnel back — exactly the production relay shape, minus containers;
* the synthetic judge worker (one aiohttp process listening on a port range,
  one port per shard) as the in-worker judge server.

Nothing here touches conftest.py (owned by another agent); the helpers are
self-contained. All traffic is 127.0.0.1; all state lands in pytest tmp dirs.
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import tarfile
import threading
import time
import types
import urllib.error
import urllib.request
from pathlib import Path

import aiohttp.web  # noqa: E402

# Make `import tcsexam` work without installation (src layout), the same way
# tests/conftest.py does.
_SRC = Path(__file__).resolve().parents[3]
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from tcsexam.backend.config import (  # noqa: E402
    BackendConfig,
    Config,
    JudgeSessionsConfig,
    SubmissionCapConfig,
)
from tcsexam.backend.server import create_app  # noqa: E402
from tcsexam.backend.testing.local_adapter import (  # noqa: E402
    LocalProcessAdapter,
    LocalWorker,
    _GatedCtrl,
    _LocalCtrl,
)

TOKEN_ID = "cde-token-id"
TOKEN_SECRET = "cde-token-secret"
ARCHIVE_TOKEN = "cde-archive-token"

AUTH = {"X-TCSEXAM-Token-Id": TOKEN_ID, "X-TCSEXAM-Token-Secret": TOKEN_SECRET}
ARCHIVE_H = {"X-TCSEXAM-Archive-Token": ARCHIVE_TOKEN}
JUDGE_IMAGE = "registry.example.com/family-judge:1.0.0"
PUBLIC_JUDGE_IMAGE = "registry.example.com/family-judge-public-only:1.0.0"
PUBLIC_IMAGE_MAP = {JUDGE_IMAGE: PUBLIC_JUDGE_IMAGE}

#: The in-worker work dir (JudgeSessionsConfig default; the local adapter
#: mirrors it under each worker root).
WORK_DIR = "/tcsexam-backend"

#: Loopback-only opener: a stray http_proxy env var must never route local
#: test traffic through a proxy.
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


# --------------------------------------------------------------------------- #
# Ports
# --------------------------------------------------------------------------- #
def free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def free_port_range(n: int, attempts: int = 60) -> int:
    """Find n consecutive free 127.0.0.1 ports; returns the base port."""
    for _ in range(attempts):
        base = 20000 + (os.getpid() % 1000) + free_port() % 20000
        socks = []
        try:
            for port in range(base, base + n):
                sock = socket.socket()
                sock.bind(("127.0.0.1", port))
                socks.append(sock)
            return base
        except OSError:
            continue
        finally:
            for sock in socks:
                sock.close()
    raise RuntimeError(f"no free range of {n} consecutive ports")


# --------------------------------------------------------------------------- #
# HTTP helpers (blocking urllib; the service loop lives in its own thread)
# --------------------------------------------------------------------------- #
def http(method: str, url: str, *, headers=None, body: bytes | None = None,
         json_body=None, timeout: float = 30.0):
    """One HTTP request -> (status, raw body bytes). Errors captured, not raised."""
    hdrs = dict(headers or {})
    data = body
    if json_body is not None:
        data = json.dumps(json_body).encode()
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with _OPENER.open(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def http_json(method: str, url: str, **kw):
    status, body = http(method, url, **kw)
    try:
        return status, json.loads(body.decode())
    except Exception:  # noqa: BLE001 - non-JSON bodies surface as None
        return status, None


def wait_until(predicate, timeout: float = 30.0, interval: float = 0.05, what: str = "condition"):
    """Poll predicate() until truthy; returns its value. AssertionError on timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    raise AssertionError(f"{what} did not happen within {timeout}s")


def run_in_threads(*funcs, collect=None):
    """Run callables concurrently (one thread each); return their results in order."""
    results = [None] * len(funcs)

    def _wrap(i, fn):
        results[i] = fn()

    threads = [threading.Thread(target=_wrap, args=(i, fn)) for i, fn in enumerate(funcs)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    return results


# --------------------------------------------------------------------------- #
# Local adapter with deterministic failure injection + leak tracking
# --------------------------------------------------------------------------- #
class _PredCtrl(_GatedCtrl):
    """_GatedCtrl whose agent-launch gate consults a mutable predicate on the
    app name (the suffix variant only covers endswith matches)."""

    should_fail = staticmethod(lambda app_name: False)

    async def run(self, cmd, shell=False, text=False, timeout=30, env=None):
        if "judge_session_agent.py" in str(cmd):
            try:
                cfg = json.loads(
                    (self.root / self._work_dir.lstrip("/") / "agent_config.json").read_text()
                )
                app_name = str(cfg.get("app_name") or "")
            except Exception:  # noqa: BLE001 - config unreadable: don't gate
                app_name = ""
            if app_name and self.should_fail(app_name):
                return subprocess.CompletedProcess(cmd, 0, "", "")
        return await _LocalCtrl.run(self, cmd, shell=shell, text=text, timeout=timeout, env=env)


class CdeAdapter(LocalProcessAdapter):
    """LocalProcessAdapter instrumented for the acceptance tests.

    * ``should_fail(app_name)``: mutable predicate — matching shards never
      launch their agent (deterministic shard-boot failure, like _GatedCtrl's
      env/ctor suffix but decidable after construction).
    * ``create_delay``: artificial worker-creation latency (provisioning-
      window tests: mid-create DELETE, concurrent-create singleflight).
    * ``fail_next_creates``: exceptions raised by the next create_sandbox
      calls (creation-retry tests).
    * ``workers``: every LocalWorker ever created here (leak assertions).
    """

    def __init__(self, config, *, should_fail=None, create_delay: float = 0.0,
                 fail_next_creates: list | None = None) -> None:
        super().__init__(config, fail_app_suffix="")
        self.should_fail = should_fail or (lambda app_name: False)
        self.create_delay = create_delay
        self.fail_next_creates: list[BaseException] = list(fail_next_creates or [])
        self.workers: list[LocalWorker] = []
        self.create_attempts = 0
        self.create_images: list[str] = []

    async def create_sandbox(self, profile, image_url, **kwargs):
        self.create_attempts += 1
        self.create_images.append(image_url)
        if self.fail_next_creates:
            raise self.fail_next_creates.pop(0)
        if self.create_delay:
            await asyncio.sleep(self.create_delay)
        worker = await super().create_sandbox(profile, image_url, **kwargs)
        ctrl = _PredCtrl(worker.root)
        ctrl._work_dir = worker.work_dir
        ctrl.should_fail = self.should_fail
        worker.ctrl = ctrl
        self.workers.append(worker)
        return worker

    # Historical alias (some callers probe this name).
    _create_sandbox = create_sandbox

    def live_agent_pids(self) -> list[int]:
        """PIDs whose /proc cwd sits under one of this adapter's worker roots."""
        roots = [str(w.root) for w in self.workers]
        if not roots:
            return []
        pids: list[int] = []
        for entry in os.listdir("/proc"):
            if not entry.isdigit():
                continue
            try:
                cwd = os.readlink(f"/proc/{entry}/cwd")
            except OSError:
                continue
            if any(cwd.startswith(root) for root in roots):
                pids.append(int(entry))
        return pids

    def assert_no_leaks(self, where: str = "") -> None:
        """No registered long-lived workers and no leftover agent processes."""
        leftovers = dict(self._long_lived)
        pids = self.live_agent_pids()
        assert not leftovers, f"{where}: long-lived workers still registered: {sorted(leftovers)}"
        assert not pids, f"{where}: leftover agent processes (pids {pids})"


# --------------------------------------------------------------------------- #
# Service lifecycle
# --------------------------------------------------------------------------- #
def make_config(port: int, state_dir, judge_port: int, *,
                archive_token=ARCHIVE_TOKEN, run_id_mode: str = "warn",
                public_image_map: dict[str, str] | None = None,
                submission_cap: SubmissionCapConfig | None = None,
                backend_overrides: dict | None = None, **judge_overrides) -> Config:
    """The C/D/E Config: small timeouts everywhere, relay-only workers
    (command="" — the synthetic worker already listens), fast failure paths.
    """
    judge = dict(
        max_sessions=64,
        profile="cde-profile",
        ttl_seconds=21600,
        ready_timeout_seconds=judge_overrides.pop("ready_timeout_seconds", 15),
        idle_ttl_seconds=judge_overrides.pop("idle_ttl_seconds", 14400),
        reaper_interval_seconds=judge_overrides.pop("reaper_interval_seconds", 0.2),
        provision_janitor_margin_seconds=judge_overrides.pop("provision_janitor_margin_seconds", 30),
        shard_boot_retries=judge_overrides.pop("shard_boot_retries", 0),
        shard_boot_retry_delay_seconds=judge_overrides.pop("shard_boot_retry_delay_seconds", 0.05),
        min_ready_ratio=judge_overrides.pop("min_ready_ratio", 1.0),
        shard_down_grace_ticks=judge_overrides.pop("shard_down_grace_ticks", 2),
        # Kill-injection tests must classify shard transport failures at once
        # (the 300s default cold-worker grace would swallow them).
        shard_boot_call_grace_seconds=judge_overrides.pop("shard_boot_call_grace_seconds", 0.0),
        failed_retention_seconds=judge_overrides.pop("failed_retention_seconds", 2.0),
        hibernate_enabled=judge_overrides.pop("hibernate_enabled", False),
        hibernate_grace_seconds=judge_overrides.pop("hibernate_grace_seconds", 0.8),
        command=judge_overrides.pop("command", ""),
        judge_port=judge_port,
        spec={"cpu_count": 1, "memory_mb": 512, "storage_mb": 1024},
        submission_cap=submission_cap or SubmissionCapConfig(),
    )
    judge.update(judge_overrides)
    backend = dict(ready_timeout_seconds=30.0, judge_sessions=JudgeSessionsConfig(**judge))
    backend.update(backend_overrides or {})
    return Config(
        host="127.0.0.1",
        port=port,
        advertise_host="127.0.0.1",
        token_id=TOKEN_ID,
        token_secret=TOKEN_SECRET,
        archive_token=archive_token,
        run_id_mode=run_id_mode,
        public_image_map=dict(PUBLIC_IMAGE_MAP if public_image_map is None else public_image_map),
        state_dir=Path(state_dir),
        backend=BackendConfig(**backend),
    )


class ServiceHandle:
    url: str
    config: Config
    adapter: CdeAdapter
    app: aiohttp.web.Application
    loop: asyncio.AbstractEventLoop
    state_dir: Path


def start_service(config: Config, adapter: CdeAdapter) -> ServiceHandle:
    """Boot the real aiohttp app on 127.0.0.1:config.port (background loop)."""
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()

    async def _start():
        app = create_app(config, adapter=adapter)
        runner = aiohttp.web.AppRunner(app)
        await runner.setup()
        site = aiohttp.web.TCPSite(runner, "127.0.0.1", config.port)
        await site.start()
        return runner, app

    runner, app = asyncio.run_coroutine_threadsafe(_start(), loop).result(timeout=30)
    handle = ServiceHandle()
    handle.url = f"http://127.0.0.1:{config.port}"
    handle.config = config
    handle.adapter = adapter
    handle.app = app
    handle.loop = loop
    handle.runner = runner
    handle.state_dir = Path(config.state_dir)
    return handle


def cleanup_app(handle: ServiceHandle) -> None:
    """The app's OWN shutdown path only: store.shutdown() (what on_cleanup
    calls) then AppRunner.cleanup. The store shutdown comes first explicitly:
    it kills the agent processes, so the tunnel handlers exit and the runner
    cleanup does not block on their websocket reads (~30s each otherwise).
    The on_cleanup hook then re-runs store.shutdown() — it is idempotent."""
    async def _stop():
        store = handle.app.get("judge_sessions")
        if store is not None:
            await store.shutdown()
        await handle.runner.cleanup()

    asyncio.run_coroutine_threadsafe(_stop(), handle.loop).result(timeout=60)


def stop_service(handle: ServiceHandle) -> None:
    """cleanup_app + loop stop + straggler kill + worker temp-dir scrub.
    Best-effort: never asserts (leak assertions belong to the tests
    themselves, executed BEFORE this backstop runs)."""
    try:
        cleanup_app(handle)
    except Exception:  # noqa: BLE001 - teardown must not hang the suite
        pass
    handle.loop.call_soon_threadsafe(handle.loop.stop)
    for worker in handle.adapter.workers:
        try:
            asyncio.run(worker.delete())
        except Exception:  # noqa: BLE001
            pass
        shutil.rmtree(worker.root, ignore_errors=True)


def run_on_service_loop(handle: ServiceHandle, coro, timeout: float = 15.0):
    """Run a coroutine on the service's own loop (for TunnelManager surgery:
    closing a tunnel server-side needs the loop that owns the websocket)."""
    return asyncio.run_coroutine_threadsafe(coro, handle.loop).result(timeout=timeout)


def kill_agent(handle: ServiceHandle, app_name: str) -> None:
    """Kill the in-worker agent process (the tunnel then drops by itself);
    the worker stays on the adapter's long-lived table."""
    worker = handle.adapter.sandbox_for_app(app_name)
    assert worker is not None, f"no worker registered for {app_name}"
    asyncio.run(worker.delete())


def close_tunnel_server_side(handle: ServiceHandle, app_name: str) -> None:
    """Close the service end of one app's tunnel (the agent then redials)."""
    tunnels = handle.app["tunnels"]
    tunnel = tunnels._tunnels.get(app_name)
    assert tunnel is not None, f"no live tunnel for {app_name}"

    async def _close():
        await tunnel.ws.close()

    run_on_service_loop(handle, _close())


def tunnel_connected(handle: ServiceHandle, app_name: str) -> bool:
    return handle.app["tunnels"].is_connected(app_name)


# --------------------------------------------------------------------------- #
# Synthetic judge worker (one subprocess, one port per shard)
# --------------------------------------------------------------------------- #
class SyntheticWorker:
    """The multi-port synthetic judge worker as a subprocess (sys.executable,
    so aiohttp is importable); one instance serves a whole test file."""

    def __init__(self, n_ports: int = 96) -> None:
        self.n_ports = n_ports
        self.base_port = free_port_range(n_ports + 1)
        self.ctrl_port = self.base_port + n_ports
        env = dict(os.environ)
        env["TCSEXAM_SYNTH_BASE_PORT"] = str(self.base_port)
        env["TCSEXAM_SYNTH_N_PORTS"] = str(n_ports)
        env["TCSEXAM_SYNTH_CTRL_PORT"] = str(self.ctrl_port)
        src = str(_SRC)
        env["PYTHONPATH"] = src + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "tcsexam.backend.testing.synthetic_worker"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        wait_until(self.healthy, timeout=30, what="synthetic worker health")

    def healthy(self) -> bool:
        try:
            status, _ = http("GET", f"http://127.0.0.1:{self.base_port}/health", timeout=2)
            if status != 200:
                return False
            status, _ = http(
                "POST", f"http://127.0.0.1:{self.ctrl_port}/kill/{self.ctrl_port + 1}", timeout=2
            )
            return status == 200
        except (urllib.error.URLError, OSError):
            return False

    def kill_port(self, port: int) -> None:
        status, body = http_json(
            "POST", f"http://127.0.0.1:{self.ctrl_port}/kill/{port}", timeout=5
        )
        assert status == 200 and body.get("ok"), f"kill {port} failed: {status} {body}"

    def stop(self) -> None:
        try:
            self.proc.kill()
            self.proc.wait(timeout=10)
        except Exception:  # noqa: BLE001
            pass


class PortWindows:
    """Hands out disjoint judge-port windows inside the synthetic worker's
    range, so sequentially-run services (one per test) never share a shard
    port's accumulated submission state."""

    def __init__(self, synth: SyntheticWorker, window: int = 8) -> None:
        self.synth = synth
        self.window = window
        self.offset = 0
        self._lock = threading.Lock()

    def next(self) -> int:
        with self._lock:
            base = self.synth.base_port + self.offset
            self.offset += self.window
            assert self.offset <= self.synth.n_ports, "synthetic port range exhausted"
            return base


# --------------------------------------------------------------------------- #
# Session-level HTTP verbs
# --------------------------------------------------------------------------- #
def create_session(handle: ServiceHandle, image="registry.example.com/family-judge:1.0.0",
                   *, headers=None, expect=202, archive_token=ARCHIVE_TOKEN, **body):
    payload = {"judge_image": image}
    payload.update(body)
    hdrs = dict(AUTH)
    if payload.get("instance_set", "hidden") == "hidden" and archive_token is not None:
        hdrs["X-TCSEXAM-Archive-Token"] = archive_token
    hdrs.update(headers or {})
    status, resp = http_json("POST", f"{handle.url}/v1/judge/sessions", json_body=payload, headers=hdrs)
    assert status == expect, f"create -> {status}: {resp}"
    return resp


def session_status(handle: ServiceHandle, sid: str, *, headers=None):
    hdrs = dict(AUTH)
    hdrs.update(headers or {})
    return http_json("GET", f"{handle.url}/v1/judge/sessions/{sid}", headers=hdrs)


def wait_ready(handle: ServiceHandle, sid: str, timeout: float = 30.0, *, headers=None):
    """Poll the status endpoint over HTTP until the session flips ready."""
    def _poll():
        status, body = session_status(handle, sid, headers=headers)
        if status == 200 and body.get("status") == "ready":
            return body
        if status == 200 and body.get("status") == "failed":
            raise AssertionError(f"session {sid} failed: {body.get('error')}")
        return None

    return wait_until(_poll, timeout=timeout, what=f"session {sid} ready")


def wait_session_status(handle: ServiceHandle, sid: str, want: str, timeout: float = 30.0):
    def _poll():
        status, body = session_status(handle, sid)
        if status == 200 and body.get("status") == want:
            return body
        return None

    return wait_until(_poll, timeout=timeout, what=f"session {sid} status={want}")


def wait_gone(handle: ServiceHandle, sid: str, timeout: float = 30.0):
    """Poll until the status endpoint answers 410 (destroyed)."""
    def _poll():
        status, body = session_status(handle, sid)
        if status == 410 and body.get("error_class") == "terminal":
            return body
        return None

    return wait_until(_poll, timeout=timeout, what=f"session {sid} destroyed")


def delete_session(handle: ServiceHandle, sid: str, *, headers=None):
    hdrs = dict(AUTH)
    hdrs.update(headers or {})
    return http_json("DELETE", f"{handle.url}/v1/judge/sessions/{sid}", headers=hdrs)


def submit(handle: ServiceHandle, sid: str, body: bytes, *, headers=None, timeout: float = 30.0):
    hdrs = dict(AUTH)
    hdrs.update(headers or {})
    hdrs.setdefault("Content-Type", "application/gzip")
    return http("POST", f"{handle.url}/v1/judge/sessions/{sid}/submit",
                headers=hdrs, body=body, timeout=timeout)


def get_submissions(handle: ServiceHandle, sid: str, *, headers=None):
    hdrs = dict(AUTH)
    hdrs.update(headers or {})
    return http_json("GET", f"{handle.url}/v1/judge/sessions/{sid}/submissions", headers=hdrs)


def get_health(handle: ServiceHandle, sid: str, *, headers=None):
    hdrs = dict(AUTH)
    hdrs.update(headers or {})
    return http_json("GET", f"{handle.url}/v1/judge/sessions/{sid}/health", headers=hdrs)


def get_archive(handle: ServiceHandle, sid: str, *, token=ARCHIVE_TOKEN, headers=None):
    hdrs = dict(AUTH)
    if token is not None:
        hdrs["X-TCSEXAM-Archive-Token"] = token
    hdrs.update(headers or {})
    return http("GET", f"{handle.url}/v1/judge/sessions/{sid}/archive", headers=hdrs)


def get_payload(handle: ServiceHandle, sid: str, *, token=ARCHIVE_TOKEN, headers=None):
    hdrs = dict(AUTH)
    if token is not None:
        hdrs["X-TCSEXAM-Archive-Token"] = token
    hdrs.update(headers or {})
    return http("GET", f"{handle.url}/v1/judge/sessions/{sid}/payload", headers=hdrs)


def get_payload_submissions(handle: ServiceHandle, sid: str, seq=None, *,
                            token=ARCHIVE_TOKEN, headers=None):
    hdrs = dict(AUTH)
    if token is not None:
        hdrs["X-TCSEXAM-Archive-Token"] = token
    hdrs.update(headers or {})
    tail = "/payload/submissions" if seq is None else f"/payload/submissions/{seq}"
    return http("GET", f"{handle.url}/v1/judge/sessions/{sid}{tail}", headers=hdrs)


def session_ids_query(handle: ServiceHandle, sids, *, headers=None):
    hdrs = {**AUTH, **ARCHIVE_H}
    hdrs.update(headers or {})
    status, body = http_json(
        "GET", f"{handle.url}/v1/judge/sessions?session_ids={','.join(sids)}", headers=hdrs
    )
    assert status == 200, f"?session_ids= -> {status}: {body}"
    return body


def hidden_count(handle: ServiceHandle, sid: str) -> int:
    body = session_ids_query(handle, [sid])
    return body["sessions"][0]["submissions"]


def service_status(handle: ServiceHandle, *, headers=None):
    hdrs = dict(AUTH)
    hdrs.update(headers or {})
    status, body = http_json("GET", f"{handle.url}/v1/status", headers=hdrs)
    assert status == 200, f"/v1/status -> {status}"
    return body


# --------------------------------------------------------------------------- #
# Payload builders
# --------------------------------------------------------------------------- #
def make_tar_gz(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for name, data in sorted(files.items()):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------- #
# The env-recording judge server (started BY the in-worker agent via a
# non-empty `command`: the agent injects PORT + INSTANCE_SHARD/INSTANCE_SET
# into its environment; the script dumps them to ./env.json in the worker's
# cwd, then serves the judge-worker protocol on $PORT with stdlib only).
# Markers in the submit body: BADTAR -> 400; SLOW -> 6s judging time.
# --------------------------------------------------------------------------- #
RECORDER_JUDGE_PY = r'''
import hashlib
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("PORT", "8082"))
with open("env.json", "w") as fh:
    json.dump({
        "PORT": os.environ.get("PORT"),
        "INSTANCE_SHARD": os.environ.get("INSTANCE_SHARD"),
        "INSTANCE_SET": os.environ.get("INSTANCE_SET"),
    }, fh)

STATE = {"subs": [], "bad_submits": 0}


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"status": "ok"})
        elif self.path == "/submissions":
            self._send(200, {
                "submissions": STATE["subs"],
                "count": len(STATE["subs"]),
                "bad_submits": STATE["bad_submits"],
            })
        else:
            self._send(404, {"error": "unknown path"})

    def do_POST(self):
        if self.path != "/submit":
            self._send(404, {"error": "unknown path"})
            return
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        if b"BADTAR" in body:
            STATE["bad_submits"] += 1
            self._send(400, {"error": "bad submission tar (recorder)"})
            return
        if b"SLOW" in body:
            time.sleep(6)
        sid = len(STATE["subs"])
        STATE["subs"].append({
            "submission": sid,
            "ts": time.time(),
            "status": "ok",
            "pack_sha256": hashlib.sha256(body).hexdigest(),
            "records": [{
                "instance": "rec-%d" % PORT,
                "A": 2, "B": 1, "K": 4,
                "status": "ok", "detail": "",
            }],
            "excluded_records": [{
                "instance": "rec-%d-flat" % PORT,
                "A": 3, "B": 3, "K": 3,
                "status": "ok", "detail": "", "reason": "b_equals_k",
            }],
            "detail": "",
        })
        self._send(202, {"submission": sid, "status": "running"})


ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
'''


def write_recorder_judge(tmp_path) -> str:
    """Write the recorder judge script; returns its absolute path (for the
    judge_sessions.command config)."""
    path = Path(tmp_path) / "recorder_judge.py"
    path.write_text(RECORDER_JUDGE_PY)
    return str(path)


def read_worker_env(handle: ServiceHandle, app_name: str) -> dict:
    """The env.json the recorder judge dumped in its worker's cwd."""
    worker = handle.adapter.sandbox_for_app(app_name)
    assert worker is not None, f"no worker registered for {app_name}"
    env_path = worker.root / WORK_DIR.lstrip("/") / "env.json"
    return json.loads(env_path.read_text())


# --------------------------------------------------------------------------- #
# pytest fixtures shared by the C/D/E modules (fixtures imported into a test
# module's namespace are registered by pytest — conftest.py stays untouched)
# --------------------------------------------------------------------------- #
import pytest  # noqa: E402


@pytest.fixture(scope="module")
def synth():
    """One synthetic judge worker per test module (96 shard ports)."""
    worker = SyntheticWorker(n_ports=96)
    yield worker
    worker.stop()


@pytest.fixture(scope="module")
def windows(synth):
    """Disjoint judge-port windows inside the synthetic worker's range."""
    return PortWindows(synth, window=8)


@pytest.fixture
def service_factory(tmp_path, windows):
    """Function-scoped service factory: each call boots a real app with its
    own state dir and its own judge-port window; teardown stops everything
    the test started. ``state_dir`` may be pinned (restart tests)."""
    handles: list[ServiceHandle] = []
    counter = {"n": 0}

    def _make(*, state_dir=None, judge_port: int | None = None,
              adapter_kwargs: dict | None = None, **config_kwargs) -> ServiceHandle:
        counter["n"] += 1
        root = Path(state_dir) if state_dir is not None else tmp_path / f"svc{counter['n']}"
        port = free_port()
        config = make_config(port, root, judge_port or windows.next(), **config_kwargs)
        adapter = CdeAdapter(config, **(adapter_kwargs or {}))
        handle = start_service(config, adapter)
        handles.append(handle)
        return handle

    yield _make

    for handle in handles:
        stop_service(handle)
