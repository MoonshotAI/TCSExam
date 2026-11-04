"""Local test workers must finish termination before delete returns."""
import asyncio
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys

import pytest

from tcsexam.backend.testing import local_adapter


@pytest.fixture
def worker_process():
    worker = local_adapter.LocalWorker('/tcsexam-backend')
    process = subprocess.Popen(
        [sys.executable, '-c', 'import time; time.sleep(30)'],
        cwd=worker.root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    real_kill = os.kill
    try:
        yield worker, process, real_kill
    finally:
        if process.poll() is None:
            real_kill(process.pid, signal.SIGKILL)
        process.wait(timeout=5)
        shutil.rmtree(worker.root)


def test_delete_waits_for_signaled_process_to_exit(worker_process, monkeypatch):
    worker, process, real_kill = worker_process

    async def scenario():
        # Queue signal delivery to expose the same live-process window that
        # can occur between kill(2) and actual termination on a busy CI host.
        pending = []

        def delayed_kill(pid, sig):
            assert pid == process.pid
            pending.append(asyncio.get_running_loop().call_later(0.03, real_kill, pid, sig))

        monkeypatch.setattr(local_adapter.os, 'kill', delayed_kill)
        try:
            await worker.delete()
            assert process.poll() is not None, 'delete returned while its worker was still alive'
            assert len(pending) == 1
            await worker.delete()  # repeated cleanup remains a no-op
        finally:
            for callback in pending:
                callback.cancel()

    asyncio.run(scenario())


def test_delete_rejects_a_process_that_remains_alive(worker_process, monkeypatch):
    worker, process, _ = worker_process
    monkeypatch.setattr(local_adapter.os, 'kill', lambda pid, sig: None)
    monkeypatch.setattr(local_adapter, '_DELETE_TIMEOUT_SECONDS', 0.03, raising=False)
    with pytest.raises(TimeoutError, match='did not exit'):
        asyncio.run(worker.delete())
    assert process.poll() is None  # genuinely live workers must not be ignored


def test_delete_does_not_signal_a_neighbor_directory(worker_process):
    worker, process, _ = worker_process
    neighbor_root = Path(str(worker.root) + '-neighbor')
    neighbor_root.mkdir()
    neighbor = subprocess.Popen(
        [sys.executable, '-c', 'import time; time.sleep(30)'], cwd=neighbor_root,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        asyncio.run(worker.delete())
        process.wait(timeout=5)
        assert neighbor.poll() is None
    finally:
        if neighbor.poll() is None:
            neighbor.kill()
        neighbor.wait(timeout=5)
        neighbor_root.rmdir()


def test_delete_does_not_wait_for_a_reused_pid(worker_process, monkeypatch):
    worker, process, _ = worker_process
    observed = []
    signaled = []

    def status(pid):
        assert pid == process.pid
        observed.append(pid)
        return 'S', 'original' if len(observed) == 1 else 'replacement'

    monkeypatch.setattr(local_adapter, '_process_status', status)
    monkeypatch.setattr(local_adapter.os, 'kill', lambda pid, sig: signaled.append((pid, sig)))
    asyncio.run(worker.delete())
    assert signaled == [(process.pid, signal.SIGKILL)]
    assert len(observed) == 2
    assert process.poll() is None  # the replacement is not signaled again
