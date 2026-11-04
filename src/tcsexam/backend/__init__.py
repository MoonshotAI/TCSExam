"""TCSExam judging backend: reverse-tunnel judge sessions on isolated workers.

An aiohttp service that boots one throwaway worker per judge session (one
per shard when sharded) from a task's self-contained judge image, and
relays task-container HTTP traffic to the in-worker judge server over a
reverse WebSocket tunnel. The worker platform itself is pluggable through
:mod:`tcsexam.backend.adapter` — no platform SDK is bundled.

Layout:

* :mod:`~tcsexam.backend.config` — YAML configuration schema
* :mod:`~tcsexam.backend.auth` — shared-token middleware + run-id identity
* :mod:`~tcsexam.backend.errors` — the wire-contract error literals
* :mod:`~tcsexam.backend.tunnel` / :mod:`~tcsexam.backend.tunnel_protocol` —
  the service-side reverse tunnel
* :mod:`~tcsexam.backend.sessions_base` — the single-worker session store
* :mod:`~tcsexam.backend.sessions` — the sharded session store, fan-out and
  aggregation, archive and payload persistence
* :mod:`~tcsexam.backend.adapter` — the platform-adapter interface
* :mod:`~tcsexam.backend.docker_adapter` — optional Docker Engine workers
* :mod:`~tcsexam.backend.status` — ``GET /v1/status``
* :mod:`~tcsexam.backend.server` — application assembly and entry point
* :mod:`~tcsexam.backend.agent_files` — the in-worker agent bundle (uploaded
  as bytes into every judge worker)
* :mod:`~tcsexam.backend.testing` — local test doubles (never for production)
"""
from __future__ import annotations
