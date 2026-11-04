"""The flat in-worker agent bundle.

``judge_session_agent.py`` / ``sandbox_agent.py`` / ``tunnel_protocol.py``
are read as BYTES and uploaded next to each other into throwaway judge
workers, where they import each other by bare top-level names. Keep them
stdlib-only and keep the dual-import (``__package__``) shape. Never import
them from the service side; read them through :func:`agent_file_path`.

``agent_files/tunnel_protocol.py`` must stay byte-identical to the
service-side ``tcsexam/backend/tunnel_protocol.py``.
"""
from __future__ import annotations

from pathlib import Path

#: Directory holding the flat in-worker agent files.
AGENT_FILES_DIR = Path(__file__).resolve().parent

#: The three files uploaded to every judge worker, in upload order.
AGENT_FILE_NAMES = ("judge_session_agent.py", "sandbox_agent.py", "tunnel_protocol.py")


def agent_file_path(name: str) -> Path:
    """Filesystem path of an in-worker agent file (e.g. ``sandbox_agent.py``)."""
    return AGENT_FILES_DIR / name
