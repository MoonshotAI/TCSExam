"""B2 acceptance: resource passing — HTTP request body -> session store ->
platform adapter, field by field.

Covers:
* POST /v1/judge/sessions ``resources``/``ttl`` reach the adapter's
  create_sandbox as the config-defaults-plus-request merge says
  (image/profile/ttl/spec/group_name/labels asserted verbatim);
* n_shards > 1 creates exactly one worker per shard, same merged spec;
* the alias keys (cpu/mem/storage_mb vs cpu_count/memory_mb/storage_mb) map
  onto the same worker spec; unknown knobs are ignored, a non-object
  ``resources`` is a 400;
* ttl clamping: below 60 -> 60, above max_ttl_seconds -> the cap, unset ->
  the configured default;
* merge priority: request keys override the configured spec per-key;
* insufficient resources: a non-transient refusal (PermissionDeniedError)
  fails the session fast (no adapter retry, no shard-boot retry) with a
  readable error and NO transient hint, while a transient failure is retried
  with backoff at both retry layers before the session lands failed with the
  transient wording.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from helpers_b import (  # noqa: E402
    FactoryAdapter,
    PermissionDeniedError,
    create_session,
    http_request,
    start_service,
    stop_service,
    wait_failed,
    wait_ready,
    wait_until,
)

IMAGE = "registry.example.com/b2-judge:1"


@pytest.fixture
def service_factory(tmp_path):
    """One backend service per call (recording local adapter by default);
    every started service is torn down at test end (agent processes included)."""
    handles = []

    def _start(**kwargs):
        handle = start_service(tmp_path / f"state-{len(handles)}", **kwargs)
        handles.append(handle)
        return handle

    yield _start
    for handle in handles:
        stop_service(handle)


def _one_call(handle, timeout: float = 15.0) -> dict:
    """Wait for exactly one recorded create_sandbox call and return it."""
    return wait_until(
        lambda: handle.adapter.calls[0] if handle.adapter.calls else None,
        timeout=timeout,
        what="the adapter's first create_sandbox call",
    )


def test_create_params_reach_the_adapter_verbatim(service_factory) -> None:
    handle = service_factory(profile="b2-profile")
    body = create_session(
        handle,
        {"judge_image": IMAGE, "resources": {"cpu": 8, "mem": 4096}, "ttl": 7200},
    )
    assert body["status"] == "provisioning" and body["n_shards"] == 1
    call = _one_call(handle)
    # The sharded store calls create_sandbox(profile, image, ttl_seconds=...,
    # spec=...) — positional profile/image, exactly these two keywords. (The
    # run-id worker tagging — labels/group_name — is the BASE store's
    # behavior; the sharded store wired by create_app carries no caller
    # identity onto workers, so both stay None.)
    assert call["profile"] == "b2-profile", "config judge_sessions.profile passed through untouched"
    assert call["image_url"] == IMAGE
    assert call["ttl_seconds"] == 7200.0
    assert call["spec"] == {
        "cpu_count": 8,  # request overrides the config default (4)
        "memory_mb": 4096,  # request overrides the config default (8192)
        "storage_mb": 20480,  # untouched request key: config default fills in
    }
    assert call.get("group_name") is None and call.get("labels") is None
    assert set(call) == {"profile", "image_url", "ttl_seconds", "spec"}, (
        f"unexpected extra create kwargs: {sorted(call)}"
    )
    session = wait_ready(handle, body["session_id"])
    assert session.ttl == 7200.0
    status, _ = http_request(handle, "DELETE", f"/v1/judge/sessions/{body['session_id']}")
    assert status == 200
    wait_until(lambda: handle.adapter.long_lived_count() == 0, what="worker recycle after DELETE")


def test_sharded_session_creates_one_worker_per_shard(service_factory) -> None:
    handle = service_factory()
    body = create_session(
        handle,
        {"judge_image": IMAGE, "n_shards": 3, "resources": {"cpu": 2}, "ttl": 900},
    )
    assert body["n_shards"] == 3
    wait_until(lambda: len(handle.adapter.calls) == 3, what="three create_sandbox calls")
    for call in handle.adapter.calls:
        assert call["image_url"] == IMAGE
        assert call["ttl_seconds"] == 900.0
        assert call["spec"] == {"cpu_count": 2, "memory_mb": 8192, "storage_mb": 20480}
    session = wait_ready(handle, body["session_id"])
    assert len(session.shards) == 3
    # One registered long-lived worker per shard, under per-shard app names.
    wait_until(lambda: handle.adapter.long_lived_count() == 3, what="three registered workers")
    status, _ = http_request(handle, "DELETE", f"/v1/judge/sessions/{body['session_id']}")
    assert status == 200
    wait_until(lambda: handle.adapter.long_lived_count() == 0, what="group teardown leaves no worker")


def test_resource_key_aliases_are_equivalent(service_factory) -> None:
    handle = service_factory()
    first = create_session(
        handle,
        {"judge_image": IMAGE, "resources": {"cpu": 8, "mem": 4096, "storage_mb": 1024}},
    )
    second = create_session(
        handle,
        {
            "judge_image": IMAGE,
            "resources": {"cpu_count": 8, "memory_mb": 4096, "storage_mb": 1024},
        },
    )
    wait_until(lambda: len(handle.adapter.calls) == 2, what="two create_sandbox calls")
    spec_alias = handle.adapter.calls[0]["spec"]
    spec_canonical = handle.adapter.calls[1]["spec"]
    assert spec_alias == spec_canonical == {
        "cpu_count": 8,
        "memory_mb": 4096,
        "storage_mb": 1024,
    }
    for sid in (first["session_id"], second["session_id"]):
        http_request(handle, "DELETE", f"/v1/judge/sessions/{sid}")


def test_unknown_resource_keys_ignored_and_bad_shapes_400(service_factory) -> None:
    handle = service_factory()
    body = create_session(
        handle,
        {"judge_image": IMAGE, "resources": {"cpu": 8, "future_knob": 42}},
    )
    call = _one_call(handle)
    # Forward-compatible: unknown knobs degrade silently, known ones apply.
    assert call["spec"] == {"cpu_count": 8, "memory_mb": 8192, "storage_mb": 20480}
    http_request(handle, "DELETE", f"/v1/judge/sessions/{body['session_id']}")

    status, raw = http_request(
        handle, "POST", "/v1/judge/sessions", json_body={"judge_image": IMAGE, "resources": [8, 4096]}
    )
    assert status == 400 and b"resources must be an object" in raw

    status, raw = http_request(
        handle,
        "POST",
        "/v1/judge/sessions",
        json_body={"judge_image": IMAGE, "resources": {"cpu": "not-a-number"}},
    )
    assert status == 400


def test_ttl_clamped_to_service_bounds(service_factory) -> None:
    handle = service_factory()  # ttl_seconds=21600, max_ttl_seconds=46800
    cases = [
        ({"ttl": 30}, 60.0, "below the 60s floor clamps up to 60"),
        ({"ttl": 999999}, 46800.0, "above max_ttl_seconds clamps down to the cap"),
        ({}, 21600.0, "unset ttl falls back to the configured default"),
    ]
    for extra, expected, why in cases:
        body = create_session(handle, {"judge_image": IMAGE, **extra})
        call = wait_until(
            lambda n=len(handle.adapter.calls): handle.adapter.calls[n - 1]
            if len(handle.adapter.calls) >= n
            else None,
            what=f"create call for ttl case {extra}",
        )
        assert call["ttl_seconds"] == expected, f"{why}: adapter got {call['ttl_seconds']}"
        session = handle.store.get(body["session_id"])
        assert session.ttl == expected, f"{why}: session.ttl is {session.ttl}"
        http_request(handle, "DELETE", f"/v1/judge/sessions/{body['session_id']}")


def test_request_spec_overrides_config_spec_per_key(service_factory) -> None:
    handle = service_factory(spec={"cpu_count": 2, "memory_mb": 2048, "storage_mb": 4096})
    body = create_session(handle, {"judge_image": IMAGE, "resources": {"mem": 16384}})
    call = _one_call(handle)
    assert call["spec"] == {
        "cpu_count": 2,  # config default kept
        "memory_mb": 16384,  # request wins per-key
        "storage_mb": 4096,  # config default kept
    }
    http_request(handle, "DELETE", f"/v1/judge/sessions/{body['session_id']}")


def test_insufficient_resources_fail_fast_non_transient(service_factory) -> None:
    """The platform refuses the requested memory: PermissionDeniedError is
    non-transient by contract — the adapter's retry loop must NOT engage, the
    shard-boot retry must NOT engage, and the session lands failed with a
    readable error WITHOUT the transient retry hint (the caller must fix the
    request, not retry it)."""

    def _refuse_big_memory(*, resources, **kwargs):
        if resources.memory_mb > 16384:
            raise PermissionDeniedError(
                f"cannot provide memory_mb={resources.memory_mb}: project quota is 16384 MB"
            )
        return None

    adapter = FactoryAdapter(
        _refuse_big_memory,
        create_retries=2,  # would retry a transient error twice — must stay idle here
        create_retry_delay_seconds=0.01,
    )
    handle = service_factory(adapter=adapter, shard_boot_retries=1, shard_boot_retry_delay_seconds=0.01)
    body = create_session(handle, {"judge_image": IMAGE, "resources": {"mem": 32768}})
    session = wait_failed(handle, body["session_id"], timeout=15)
    assert "PermissionDeniedError" in session.error
    assert "16384" in session.error, f"error must be readable/actionable: {session.error}"
    assert "judge session create failed" in session.error
    assert "please try again" not in session.error, (
        f"a non-transient refusal must not invite retries: {session.error}"
    )
    assert len(adapter.worker_calls) == 1, (
        f"a non-transient refusal must fail fast — got {len(adapter.worker_calls)} creation attempts"
    )
    # The failed session never registered a worker.
    assert adapter.long_lived_count() == 0


def test_transient_creation_error_retried_with_backoff(service_factory) -> None:
    """Contrast case: a transient platform failure (unknown error class) IS
    retried — the adapter's retry loop (create_retries=2 -> 3 attempts per
    boot) under the store's whole-boot retry (shard_boot_retries=1 -> 2
    boots) makes 6 attempts before the session lands failed WITH the
    transient hint."""

    def _pool_busy(**kwargs):
        raise RuntimeError("worker pool temporarily full")

    adapter = FactoryAdapter(_pool_busy, create_retries=2, create_retry_delay_seconds=0.01)
    handle = service_factory(adapter=adapter, shard_boot_retries=1, shard_boot_retry_delay_seconds=0.01)
    body = create_session(handle, {"judge_image": IMAGE, "resources": {"mem": 4096}})
    session = wait_failed(handle, body["session_id"], timeout=15)
    assert "RuntimeError" in session.error and "worker pool temporarily full" in session.error
    assert "please try again" in session.error, (
        f"a transient failure must carry the retry hint: {session.error}"
    )
    assert len(adapter.worker_calls) == 6, (
        f"expected 3 adapter attempts x 2 whole-boot retries = 6, got {len(adapter.worker_calls)}"
    )
    assert adapter.long_lived_count() == 0
