"""Daemon-side CPU discovery, nonoverlapping reservations, and recovery."""
import asyncio
import os

import pytest

from tcsexam.backend.adapter import load_adapter
from tcsexam.backend.docker_adapter import (
    DockerCapacityError, DockerError, InvalidArgumentError, _parse_cpu_set,
)
from test_docker_adapter import _config, running_adapter

IMAGE = 'registry.example.com/judge:1'
ONE = {'cpu_count': 1, 'memory_mb': 1024, 'storage_mb': None}


def test_cpu_ids_come_from_target_daemon_not_backend_host(tmp_path, monkeypatch):
    monkeypatch.setattr(os, 'sched_getaffinity', lambda pid: {999})

    async def scenario():
        async with running_adapter(tmp_path) as (adapter, daemon):
            daemon.ncpu = 64  # count alone does not describe usable IDs
            daemon.cpu_set = '10,12-13,47'
            workers = await asyncio.gather(*(
                adapter.create_sandbox('cpu', IMAGE, spec=ONE) for _ in range(4)))
            assert {w.cpu_ids for w in workers} == {(10,), (12,), (13,), (47,)}
            for worker in workers:
                host = daemon.containers[worker.container_id]['HostConfig']
                assert _parse_cpu_set(host['CpusetCpus']) == worker.cpu_ids
                assert host['NanoCpus'] == 1_000_000_000
                assert host['Memory'] == 1024 * 1024 * 1024
            with pytest.raises(DockerCapacityError):
                await adapter.create_sandbox('cpu', IMAGE, spec=ONE, ready_timeout_seconds=0.03)
            assert not adapter._pending and not adapter._pending_cpus

    asyncio.run(scenario())


def test_concurrent_multi_core_allocations_are_disjoint(tmp_path):
    async def scenario():
        async with running_adapter(tmp_path) as (adapter, daemon):
            daemon.cpu_set = '2-5,10-13'
            two = {**ONE, 'cpu_count': 2}
            workers = await asyncio.gather(*(
                adapter.create_sandbox('cpu', IMAGE, spec=two) for _ in range(4)))
            allocated = [cpu for w in workers for cpu in w.cpu_ids]
            assert len(allocated) == len(set(allocated)) == 8
            assert all(len(w.cpu_ids) == w.resources.cpu_count == 2 for w in workers)
            released = workers[1].cpu_ids
            await workers[1].delete()
            replacement = await adapter.create_sandbox('cpu', IMAGE, spec=two)
            assert replacement.cpu_ids == released

    asyncio.run(scenario())


def test_request_larger_than_effective_cpu_set_is_not_downgraded(tmp_path):
    async def scenario():
        async with running_adapter(tmp_path) as (adapter, daemon):
            daemon.ncpu = 32
            daemon.cpu_set = '8,10'
            with pytest.raises(InvalidArgumentError, match='effective CPU capacity'):
                await adapter.create_sandbox('cpu', IMAGE, spec={**ONE, 'cpu_count': 3})
            assert not adapter._workers and not adapter._pending_cpus
            worker = await adapter.create_sandbox('cpu', IMAGE, spec=ONE)
            assert worker.cpu_ids == (8,)

    asyncio.run(scenario())


def test_failed_creation_releases_cpu_reservation(tmp_path):
    async def scenario():
        async with running_adapter(tmp_path) as (adapter, daemon):
            daemon.ncpu = 1
            daemon.fail_start = True
            with pytest.raises(DockerError, match='start failure'):
                await adapter.create_sandbox('cpu', IMAGE, spec=ONE)
            assert not adapter._workers and not adapter._pending_cpus
            assert adapter._cpu_discovery_reservation is None
            daemon.fail_start = False
            first = await adapter.create_sandbox('cpu', IMAGE, spec=ONE)
            await first.delete()
            daemon.fail_start = True
            with pytest.raises(DockerError, match='start failure'):
                await adapter.create_sandbox('cpu', IMAGE, spec=ONE)
            assert not adapter._workers and not adapter._pending_cpus
            daemon.fail_start = False
            assert (await adapter.create_sandbox('cpu', IMAGE, spec=ONE)).cpu_ids == (0,)

    asyncio.run(scenario())


def test_failed_delete_does_not_release_allocated_cpu(tmp_path):
    async def scenario():
        async with running_adapter(tmp_path) as (adapter, daemon):
            daemon.ncpu = 2
            first = await adapter.create_sandbox('cpu', IMAGE, spec=ONE)
            daemon.fail_delete = True
            with pytest.raises(DockerError, match='delete failure'):
                await first.delete()
            assert not first.deleted and first.container_id in adapter._workers
            second = await adapter.create_sandbox('cpu', IMAGE, spec=ONE)
            assert not set(first.cpu_ids) & set(second.cpu_ids)
            daemon.fail_delete = False
            await first.delete()
            replacement = await adapter.create_sandbox('cpu', IMAGE, spec=ONE)
            assert replacement.cpu_ids == first.cpu_ids

    asyncio.run(scenario())


def test_cancellation_during_first_cpu_update_releases_reservation(tmp_path):
    async def scenario():
        async with running_adapter(tmp_path) as (adapter, daemon):
            entered = asyncio.Event()
            original = adapter.engine.update_cpu_set

            async def pending_update(*args, **kwargs):
                entered.set()
                await asyncio.Event().wait()

            adapter.engine.update_cpu_set = pending_update
            pending = asyncio.create_task(adapter.create_sandbox('cpu', IMAGE, spec=ONE))
            await asyncio.wait_for(entered.wait(), 0.5)
            pending.cancel()
            with pytest.raises(asyncio.CancelledError):
                await pending
            assert not adapter._workers and not adapter._pending_cpus
            assert adapter._cpu_discovery_reservation is None
            adapter.engine.update_cpu_set = original
            assert (await adapter.create_sandbox('cpu', IMAGE, spec=ONE)).cpu_ids == (0,)

    asyncio.run(scenario())


def test_restart_recovers_cpu_ids_from_container_receipts(tmp_path):
    async def scenario():
        async with running_adapter(tmp_path) as (first, daemon):
            daemon.ncpu = 2
            daemon.cpu_set = '12,31'
            old = await first.create_sandbox('cpu', IMAGE, spec=ONE)
            await first.close()
            second = load_adapter('docker', _config(daemon))
            try:
                new = await second.create_sandbox('cpu', IMAGE, spec=ONE)
                assert second._workers[old.container_id].cpu_ids == (12,)
                assert new.cpu_ids == (31,)
                await second._workers[old.container_id].delete()
                replacement = await second.create_sandbox('cpu', IMAGE, spec=ONE)
                assert replacement.cpu_ids == (12,)
            finally:
                for worker in list(second._workers.values()):
                    await worker.delete()
                await second.close()

    asyncio.run(scenario())


@pytest.mark.parametrize('receipt', ['', '0,1'])
def test_legacy_or_wrong_size_recovery_blocks_new_workers(tmp_path, receipt):
    async def scenario():
        async with running_adapter(tmp_path) as (first, daemon):
            old = await first.create_sandbox('cpu', IMAGE, spec=ONE)
            await first.close()
            daemon.containers[old.container_id]['HostConfig']['CpusetCpus'] = receipt
            count = len(daemon.containers)
            second = load_adapter('docker', _config(daemon))
            try:
                with pytest.raises(InvalidArgumentError, match='no exact CPU allocation'):
                    await second.create_sandbox('cpu', IMAGE, spec=ONE)
                assert len(daemon.containers) == count
                assert not daemon.containers[old.container_id]['deleted']
            finally:
                await second.close()

    asyncio.run(scenario())


def test_overlapping_recovered_allocations_block_new_workers(tmp_path):
    async def scenario():
        async with running_adapter(tmp_path) as (first, daemon):
            a = await first.create_sandbox('cpu', IMAGE, spec=ONE)
            b = await first.create_sandbox('cpu', IMAGE, spec=ONE)
            await first.close()
            daemon.containers[b.container_id]['HostConfig']['CpusetCpus'] = str(a.cpu_ids[0])
            second = load_adapter('docker', _config(daemon))
            try:
                with pytest.raises(InvalidArgumentError, match='overlapping CPU allocations'):
                    await second.create_sandbox('cpu', IMAGE, spec=ONE)
                assert not daemon.containers[a.container_id]['deleted']
                assert not daemon.containers[b.container_id]['deleted']
            finally:
                await second.close()

    asyncio.run(scenario())


def test_daemon_must_support_and_retain_cpu_sets(tmp_path):
    async def scenario():
        async with running_adapter(tmp_path) as (adapter, daemon):
            daemon.cpu_set_support = False
            with pytest.raises(InvalidArgumentError, match='support CPU sets'):
                await adapter.create_sandbox('cpu', IMAGE, spec=ONE)
            assert not daemon.containers
            daemon.cpu_set_support = True
            daemon.drop_cpu_set = True
            with pytest.raises(InvalidArgumentError, match='CPU set'):
                await adapter.create_sandbox('cpu', IMAGE, spec=ONE)
            assert not adapter._workers and not adapter._pending_cpus

    asyncio.run(scenario())


@pytest.mark.parametrize('key', ['CPUSet', 'Cpuset'])
def test_docker_info_cpu_set_capability_keys(tmp_path, key):
    async def scenario():
        async with running_adapter(tmp_path) as (adapter, daemon):
            daemon.cpu_set_key = key
            worker = await adapter.create_sandbox('cpu', IMAGE, spec=ONE)
            assert worker.cpu_ids == (0,)

    asyncio.run(scenario())


def test_explicit_standard_capability_false_is_not_overridden_by_alias(tmp_path):
    async def scenario():
        async with running_adapter(tmp_path) as (adapter, daemon):
            daemon.cpu_set_support = False
            daemon.cpu_set_alias_support = True
            with pytest.raises(InvalidArgumentError, match='support CPU sets'):
                await adapter.create_sandbox('cpu', IMAGE, spec=ONE)
            assert not daemon.containers

    asyncio.run(scenario())


@pytest.mark.parametrize('value', ['', '-1', '3-1', '0,0', '0-100000000000000000', '0,,1'])
def test_invalid_cpu_lists_are_rejected_without_large_allocations(value):
    with pytest.raises(InvalidArgumentError):
        _parse_cpu_set(value)
