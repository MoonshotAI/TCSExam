"""Test doubles for the judging backend: a local-process platform adapter
and a synthetic judge worker.

Everything in this package is for tests and local verification ONLY — it
provides no isolation, no resource enforcement and no security boundary.
Production deployments load a real platform adapter via the ``adapter``
config key (see :mod:`tcsexam.backend.adapter`).
"""
from __future__ import annotations
