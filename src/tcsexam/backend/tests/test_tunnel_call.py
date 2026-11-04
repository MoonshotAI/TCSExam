"""TunnelManager.call(): the programmatic (collect-full-response) relay.

Used for server-side fan-out shapes (the sharded judge sessions). The 502
bodies are part of the task-side retry contract and are pinned byte for byte
here.
"""
from __future__ import annotations

import asyncio
import json

import aiohttp

from conftest import ARCHIVE_TOKEN, wait_session_ready

TOKEN_HEADERS = {
    "X-TCSEXAM-Token-Id": "test-token-id",
    "X-TCSEXAM-Token-Secret": "test-token-secret",
}
VERIFIER_HEADERS = {**TOKEN_HEADERS, "X-TCSEXAM-Archive-Token": ARCHIVE_TOKEN}


def _create_session(jservice) -> str:
    async def _create() -> str:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{jservice.url}/v1/judge/sessions",
                json={"judge_image": "toy:latest"},
                headers=VERIFIER_HEADERS,
            ) as resp:
                assert resp.status == 202, await resp.text()
                return (await resp.json())["session_id"]

    sid = asyncio.run_coroutine_threadsafe(_create(), jservice.loop).result(timeout=30)
    wait_session_ready(jservice, sid)  # the tunnel connect lands asynchronously
    return sid


def _call(jservice, *args, **kwargs):
    return asyncio.run_coroutine_threadsafe(
        jservice.app["tunnels"].call(*args, **kwargs), jservice.loop
    ).result(timeout=30)


def test_call_collects_get_response(jservice) -> None:
    sid = _create_session(jservice)
    status, headers, body = _call(jservice, sid, "GET", "/health")
    assert status == 200
    assert json.loads(body.decode())["status"] == "ok"
    assert headers.get("Content-Type", "").startswith("application/json")


def test_call_sends_request_body(jservice) -> None:
    sid = _create_session(jservice)
    payload = json.dumps({"code": "int main() {}"}).encode()
    status, _headers, body = _call(
        jservice,
        sid,
        "POST",
        "/submit",
        body=payload,
        headers={"Content-Type": "application/json"},
    )
    assert status == 200
    echoed = json.loads(body.decode())
    assert echoed["status"] == "queued"
    assert echoed["code_len"] == len("int main() {}")


def test_call_unknown_app_is_a_contract_502(jservice) -> None:
    status, _headers, body = _call(jservice, "no-such-app", "GET", "/health")
    assert status == 502
    assert body == b"502 Bad Gateway: app 'no-such-app' has no live tunnel (please try again)"
