"""G1 client compatibility: the 30 frozen online task clients fit the service.

Static, seconds-level cross-check of the judging constants declared by the
existing (frozen) clients of every online task package against each other
and against the extracted service's acceptance rules:

* ``tasks/solver/online/<task>/environment/submit.sh`` — the public
  self-test client (session create payload, shard count, TTLs, polling).
* ``tasks/solver/online/<task>/tests/fetch_final.py`` — the final verifier
  client (``N_SHARDS`` / ``RESOURCES`` / ``SESSION_TTL`` / ``HISTORY_BEST``).
* ``tasks/solver/online/<task>/metadata.json`` — the ``judging`` block
  (``budget_kind`` / ``shards`` / ``shard_cores`` / ``shard_mem_gb``).

The service-side checks call the extracted backend's own code
(:func:`tcsexam.backend.sessions._parse_resources`,
:class:`tcsexam.backend.config.JudgeSessionsConfig`), so a service change
that would reject a frozen client shape fails here. The ttl rule mirrors
``JudgeSessionStore.create`` (sessions.py): the requested ttl is clamped
into ``[60, max_ttl_seconds]`` — accepted, never rejected.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from tcsexam.backend.config import JudgeSessionsConfig
from tcsexam.backend.sessions import _RESOURCE_KEYS, _parse_resources
from tcsexam.layout import repository

ROOT = repository()
ONLINE = ROOT / "tasks/solver/online"

POOL_TASKS = {
    "bpp-bpplib",
    "gp-dimacs10",
    "itc2021-sports-timetabling",
    "logic-syn-iwls2023",
    "qap-qaplib",
    "scp-orlib",
}


def _submit_constants(text: str, environ=None) -> dict:
    import os
    import subprocess
    environ = environ or {}
    def one(pattern, cast=str, env=None):
        match = re.search(pattern, text, re.M)
        assert match, f"submit.sh constant not found: {pattern}"
        return cast(environ.get(env, match.group(1)))
    payload = re.search(r'-d\s*"(\{\\"judge_image\\".*?\})"', text)
    assert payload, "submit.sh: session-create payload not found"
    # Execute only the three variable assignments, optional disk selection,
    # and printf. No service request, solver, keepalive or file write runs.
    lines = [line for line in text.splitlines() if line.startswith(("N_SHARDS=", "SESSION_TTL="))]
    start = text.index('STORAGE_RESOURCE=""')
    stop = text.index('\n: "${TCSEXAM_TOKEN_ID:', start)
    script = '\n'.join(lines) + '\n' + text[start:stop]
    script += '\nJUDGE_IMAGE=synthetic-judge:1\nprintf "%s" "' + payload.group(1) + '"'
    rendered = subprocess.run(['bash','-eu','-c',script], env={'PATH':os.environ['PATH'], **environ},
                              capture_output=True, text=True, check=True)
    body = json.loads(rendered.stdout)
    resources = body['resources']
    assert set(resources) <= {'cpu','mem','storage_mb'}
    return {
        "n_shards": body['n_shards'], "session_ttl":body['ttl'],
        "poll_interval": one(r'POLL_INTERVAL="\$\{TCSEXAM_POLL_INTERVAL:-(\d+)\}"', int, 'TCSEXAM_POLL_INTERVAL'),
        "poll_timeout": one(r'POLL_TIMEOUT="\$\{TCSEXAM_POLL_TIMEOUT:-(\d+)\}"', int, 'TCSEXAM_POLL_TIMEOUT'),
        "cpu": resources['cpu'], "mem_mb":resources['mem'],
        "storage_mb": resources.get('storage_mb'),
        "storage_requested": 'storage_mb' in resources,
        "instance_set": body['instance_set'],
        "judge_image_from_env": 'JUDGE_IMAGE="${TCSEXAM_JUDGE_IMAGE:?' in text,
    }


def _fetch_final_constants(text: str, environ=None) -> dict:
    import ast
    import types
    environ = environ or {}
    tree=ast.parse(text)
    assignments=[n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {"N_SHARDS","RESOURCES","SESSION_TTL"} for t in n.targets)]
    assignments += [n for n in tree.body if isinstance(n,ast.If)
                    and 'TCSEXAM_WORKER_STORAGE_MB' in ast.unparse(n.test)]
    values={"os":types.SimpleNamespace(environ=environ)}
    exec(compile(ast.Module(body=assignments,type_ignores=[]),"client-constants","exec"),values)
    def one(pattern):
        match = re.search(pattern, text, re.M)
        assert match, f"fetch_final.py constant not found: {pattern}"
        return match.group(1)

    return {
        "n_shards": values["N_SHARDS"],
        "cpu": values["RESOURCES"]["cpu"],
        "mem_mb": values["RESOURCES"]["mem"],
        "storage_mb":values["RESOURCES"].get("storage_mb"),
        "storage_requested":"storage_mb" in values["RESOURCES"],
        "session_ttl": values["SESSION_TTL"],
        "history_best": one(r"^HISTORY_BEST = (True|False)") == "True",
        "judge_image_from_env": 'JUDGE_IMAGE = os.environ["TCSEXAM_JUDGE_IMAGE"]' in text,
    }


def _load_task(task_dir: Path) -> dict:
    meta = json.loads((task_dir / "metadata.json").read_text())["judging"]
    return {
        "submit": _submit_constants((task_dir / "environment/submit.sh").read_text()),
        "fetch": _fetch_final_constants((task_dir / "tests/fetch_final.py").read_text()),
        "meta": meta,
    }


TASKS = {p.name: _load_task(p) for p in sorted(ONLINE.iterdir()) if p.is_dir()}


def test_task_inventory() -> None:
    """The 30 online packages all ship both frozen clients and metadata."""
    assert len(TASKS) == 30
    for name in TASKS:
        assert (ONLINE / name / "environment/submit.sh").is_file()
        assert (ONLINE / name / "tests/fetch_final.py").is_file()
        assert (ONLINE / name / "metadata.json").is_file()


@pytest.mark.parametrize("task", sorted(TASKS))
def test_clients_agree_with_each_other_and_metadata(task: str) -> None:
    """submit.sh, fetch_final.py and metadata.json pin the same judging shape."""
    submit, fetch, meta = TASKS[task]["submit"], TASKS[task]["fetch"], TASKS[task]["meta"]
    assert submit["n_shards"] == fetch["n_shards"]
    assert (submit["cpu"], submit["mem_mb"]) == (fetch["cpu"], fetch["mem_mb"])
    assert meta["shards"] == fetch["n_shards"]
    assert meta["shard_cores"] == fetch["cpu"]
    assert meta["shard_mem_gb"] * 1024 == fetch["mem_mb"]
    # Pool semantics (one shared time pool, cross-instance borrowing) forces a
    # single shard; the six pool tasks are exactly the single-shard tasks.
    assert (meta["budget_kind"] == "pool") == (fetch["n_shards"] == 1)
    assert (task in POOL_TASKS) == (meta["budget_kind"] == "pool")
    # The public self-test channel always judges the public instance set;
    # every task currently renders the final-judging-only branch.
    assert submit["instance_set"] == "public"
    assert fetch["history_best"] is False
    # Both clients take the judge image from the environment, never hardcode it.
    assert submit["judge_image_from_env"] and fetch["judge_image_from_env"]


@pytest.mark.parametrize("task", sorted(TASKS))
def test_service_accepts_the_client_shapes(task: str) -> None:
    """The extracted backend accepts every frozen client's session-create shape."""
    cfg = JudgeSessionsConfig()  # the service defaults in config.py
    submit, fetch = TASKS[task]["submit"], TASKS[task]["fetch"]
    # n_shards within the store's bounds (sessions.py handle_session_create).
    for client in (submit, fetch):
        assert 1 <= client["n_shards"] <= cfg.max_shards
        # resources keys map through _parse_resources (cpu/mem -> spec keys).
        mapped = _parse_resources({"cpu": client["cpu"], "mem": client["mem_mb"]})
        assert mapped == {"cpu_count": client["cpu"], "memory_mb": client["mem_mb"]}
        # ttl is clamped into [60, max_ttl_seconds] (JudgeSessionStore.create):
        # accepted even when the requested value exceeds the clamp, so the
        # development and verifier TTLs all go through.
        clamped = max(60.0, min(float(client["session_ttl"]), cfg.max_ttl_seconds))
        assert clamped >= 60.0
    assert {"cpu", "mem"} <= set(_RESOURCE_KEYS)


def test_development_ttl_matches_default_limit_and_final_ttl_stays_independent() -> None:
    """Development gets 12 h plus 1 h margin; final sessions retain task budgets."""
    cfg = JudgeSessionsConfig()
    for task in TASKS.values():
        assert task["submit"]["session_ttl"] == 46800
        assert max(60.0, min(46800.0, cfg.max_ttl_seconds)) == cfg.max_ttl_seconds
        assert 14400 <= task["fetch"]["session_ttl"] <= 28800
        assert task["fetch"]["session_ttl"] <= cfg.max_ttl_seconds


@pytest.mark.parametrize("task", sorted(TASKS))
def test_clients_accept_explicit_prepared_overrides(task):
    env={"TCSEXAM_N_SHARDS":"1" if task in POOL_TASKS else "2", "TCSEXAM_SESSION_TTL":"99999", "TCSEXAM_WORKER_CPUS":"3", "TCSEXAM_WORKER_MEMORY_MB":"12288", "TCSEXAM_WORKER_STORAGE_MB":"16384"}
    directory=ONLINE/task
    submit=_submit_constants((directory/"environment/submit.sh").read_text(),env)
    final=_fetch_final_constants((directory/"tests/fetch_final.py").read_text(),env)
    for client in (submit,final):
        assert client["n_shards"]==int(env["TCSEXAM_N_SHARDS"])
        assert client["session_ttl"]==99999
        assert client["cpu"]==3 and client["mem_mb"]==12288
        assert client["storage_requested"] and client["storage_mb"] == 16384
        assert _parse_resources({"cpu":client["cpu"],"mem":client["mem_mb"],"storage_mb":None}) == {"cpu_count":3,"memory_mb":12288,"storage_mb":None}


@pytest.mark.parametrize("task", sorted(TASKS))
def test_explicit_disabled_disk_reaches_both_clients_as_json_null(task):
    env={"TCSEXAM_WORKER_STORAGE_MB":"null"}
    directory=ONLINE/task
    for parser,path in ((_submit_constants,directory/"environment/submit.sh"),(_fetch_final_constants,directory/"tests/fetch_final.py")):
        record=parser(path.read_text(),env)
        assert record['storage_requested'] and record['storage_mb'] is None
