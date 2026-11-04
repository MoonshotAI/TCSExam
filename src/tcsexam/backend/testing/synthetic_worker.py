#!/usr/bin/env python3
"""Synthetic judge worker for local end-to-end tests: a single aiohttp
process listening on a whole port range (default 8082 + 96 ports), each
port simulating one shard's judge worker — no containers needed.

Behavior (independent state per port; the current worker protocol):

* ``GET  /health``      → 200 ``{"status": "ok"}``
* ``POST /submit``      → 202 ``{"submission": k}``, immediately records a
  terminal entry ``{status: ok, records: [{instance, A: 2, B: 1, K: 4,
  status: ok}]}`` (one instance per shard — the "1 instance 1 worker" main
  scenario: each shard's judging set is exactly 1 instance; A=2>B=1 and
  K=4>B give the MAX direction, so after five-number aggregation every live
  shard contributes better=1 / delta=+1 and every dead shard contributes
  failed=1); plus one ``excluded_records`` side-channel record (B==K=3,
  A=3, reason ``b_equals_k``) — hidden aggregation must IGNORE it (five
  numbers and records unchanged), public aggregation must merge it with
  anchors stripped. Like real workers, entries carry ``pack_sha256`` (the
  request body's sha256), forwarded by the public aggregation.
* ``GET  /submissions`` → this shard's submission history (per-instance
  records, no scalar score)

Control port (default 8200):

* ``POST /kill/<port>`` → stop the given port's listener (mid-judging
  shard-kill injection: the port then refuses connections and the agent
  relay gets a 502)

Ports are not bound to shard indices: the local test adapter assigns ports
in creation order, the worker behaves identically on every port, and the
aggregation math only depends on each shard carrying exactly 1 record. The
instance name carries the port number for archive readability only.

Environment: ``TCSEXAM_SYNTH_BASE_PORT`` (8082), ``TCSEXAM_SYNTH_N_PORTS``
(96), ``TCSEXAM_SYNTH_CTRL_PORT`` (8200).
"""
import asyncio
import hashlib
import os
import time

from aiohttp import web

BASE_PORT = int(os.environ.get("TCSEXAM_SYNTH_BASE_PORT", "8082"))
N_PORTS = int(os.environ.get("TCSEXAM_SYNTH_N_PORTS", "96"))
CTRL_PORT = int(os.environ.get("TCSEXAM_SYNTH_CTRL_PORT", "8200"))


def _shard_app(port: int) -> web.Application:
    state: dict = {"subs": []}

    async def health(request: web.Request) -> web.Response:
        return web.json_response({"status": "ok"})

    async def submit(request: web.Request) -> web.Response:
        body = await request.read()
        sid = len(state["subs"])
        state["subs"].append(
            {
                "submission": sid,
                "ts": time.time(),
                "status": "ok",
                # Same shape as real workers: the submitted pack's sha256
                # rides on the entry.
                "pack_sha256": hashlib.sha256(body).hexdigest(),
                "records": [
                    {
                        "instance": f"synthetic-{port}",
                        "A": 2,
                        "B": 1,
                        "K": 4,
                        "status": "ok",
                        "detail": "",
                    }
                ],
                # Side channel (worker protocol): B==K no-signal keys stay
                # out of records, carried whole on excluded_records —
                # hidden aggregation must ignore them, public aggregation
                # must merge them with anchors stripped.
                "excluded_records": [
                    {
                        "instance": f"synthetic-{port}-flat",
                        "A": 3,
                        "B": 3,
                        "K": 3,
                        "status": "ok",
                        "detail": "",
                        "reason": "b_equals_k",
                    }
                ],
                "detail": "",
            }
        )
        return web.json_response({"submission": sid, "status": "running"}, status=202)

    async def submissions(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "submissions": state["subs"],
                "count": len(state["subs"]),
            }
        )

    app = web.Application()
    app.router.add_get("/health", health)
    app.router.add_post("/submit", submit)
    app.router.add_get("/submissions", submissions)
    return app


async def main() -> None:
    # One app instance PER PORT: each shard keeps its own submission
    # counter and history (sharing one app would interleave the counters
    # and break the fan-out's sequence-consistency check).
    sites: dict[int, tuple[web.AppRunner, web.TCPSite]] = {}
    for offset in range(N_PORTS):
        port = BASE_PORT + offset
        runner = web.AppRunner(_shard_app(port))
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", port)
        await site.start()
        sites[port] = (runner, site)

    async def kill(request: web.Request) -> web.Response:
        port = int(request.match_info["port"])
        entry = sites.pop(port, None)
        if entry is not None:
            runner, site = entry
            await site.stop()
            await runner.cleanup()
        return web.json_response({"ok": True, "port": port, "was_listening": entry is not None})

    ctrl = web.Application()
    ctrl.router.add_post("/kill/{port}", kill)
    ctrl_runner = web.AppRunner(ctrl)
    await ctrl_runner.setup()
    await web.TCPSite(ctrl_runner, "127.0.0.1", CTRL_PORT).start()
    print(f"synthetic worker: {N_PORTS} shard ports {BASE_PORT}..{BASE_PORT + N_PORTS - 1}, ctrl :{CTRL_PORT}", flush=True)
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
