"""Docker adapter tests using a real Unix socket and a fake Docker daemon."""
from __future__ import annotations

import asyncio
import io
import json
import re
import shlex
import struct
import tarfile
from contextlib import asynccontextmanager
from pathlib import Path, PurePosixPath

import pytest
from aiohttp import web

from tcsexam.backend.adapter import load_adapter
from tcsexam.backend.config import BackendConfig, Config, JudgeSessionsConfig
from tcsexam.backend.contracttest import run_contract_suite
from tcsexam.backend.docker_adapter import (
    DockerCapacityError,
    DockerNotFoundError,
    InvalidArgumentError,
)

_MIB = 1024 * 1024


def _json_error(status: int, message: str) -> web.Response:
    return web.json_response({"message": message}, status=status)


class FakeDockerDaemon:
    def __init__(self, socket_path: Path) -> None:
        self.socket_path = socket_path
        self.images = {"registry.example.com/judge:1"}
        self.containers: dict[str, dict] = {}
        self.execs: dict[str, dict] = {}
        self.requests: list[tuple[str, str, dict]] = []
        self.removed: list[str] = []
        self.pulled: list[str] = []
        self.ncpu = 8
        self.memory_mb = 16384
        self.memory_limit = True
        self.swap_limit = True
        self.drop_memory_swap = False
        self.cpu_quota = True
        self.cpu_set_support = True
        self.cpu_set_key = 'CPUSet'
        self.cpu_set_alias_support = None
        self.cpu_set = None
        self.drop_cpu_set = False
        self.minimum_api: tuple[int, int] | None = None
        self.fail_start = False
        self.fail_delete = False
        self.start_delay = 0.0
        self.started = None
        self.drop_storage = False
        self.pull_error = False
        self.pull_delay = 0.0
        self.exec_delay = 0.0
        self.fragment_responses = False
        self.lose_create_response = False
        self.runner = None

    async def start(self) -> None:
        app = web.Application()
        app.router.add_route("*", "/{path:.*}", self.dispatch)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        await web.UnixSite(self.runner, str(self.socket_path)).start()

    async def close(self) -> None:
        if self.runner is not None:
            await self.runner.cleanup()

    @staticmethod
    async def fragmented(request: web.Request, data: bytes, content_type: str) -> web.StreamResponse:
        response = web.StreamResponse(headers={"Content-Type": content_type})
        await response.prepare(request)
        for offset in range(0, len(data), 7):
            await response.write(data[offset:offset + 7])
            await asyncio.sleep(0)
        await response.write_eof()
        return response

    async def dispatch(self, request: web.Request) -> web.StreamResponse:
        match = re.match(r"^/v(\d+)\.(\d+)(/.*)$", request.path)
        if match is None:
            return _json_error(404, "unknown Docker endpoint")
        version = tuple(map(int, match.group(1, 2)))
        path = match.group(3)
        query = dict(request.query)
        self.requests.append((request.method, path, query))
        if self.minimum_api is not None and version < self.minimum_api:
            required = ".".join(map(str, self.minimum_api))
            return _json_error(400, f"client version is too old: minimum supported API version is {required}")
        if request.method == "GET" and path == "/info":
            data = json.dumps({
                "NCPU": self.ncpu,
                "MemTotal": self.memory_mb * _MIB,
                "MemoryLimit": self.memory_limit,
                "SwapLimit": self.swap_limit,
                "CpuCfsQuota": self.cpu_quota,
                self.cpu_set_key: self.cpu_set_support,
                **({'Cpuset': self.cpu_set_alias_support} if self.cpu_set_alias_support is not None else {}),
            }).encode()
            if self.fragment_responses:
                return await self.fragmented(request, data, "application/json")
            return web.Response(body=data, content_type="application/json")
        image_match = re.fullmatch(r"/images/(.+)/json", path)
        if request.method == "GET" and image_match:
            image = image_match.group(1)
            if image not in self.images:
                return _json_error(404, "no such image")
            return web.json_response({"Id": f"sha256:{len(image):064d}", "Config": {"Image": image}})
        if request.method == "POST" and path == "/images/create":
            image = query["fromImage"]
            if self.pull_error:
                return web.Response(
                    body=b'{"status":"pulling"}\n{"error":"repository not found"}\n',
                    content_type="application/json",
                )
            self.images.add(image)
            self.pulled.append(image)
            if self.pull_delay:
                await asyncio.sleep(self.pull_delay)
            data = b'{"status":"pulling"}\n{"status":"complete"}\n'
            if self.fragment_responses:
                return await self.fragmented(request, data, "application/json")
            return web.Response(body=data, content_type="application/json")
        if request.method == "POST" and path == "/containers/create":
            body = await request.json()
            container_id = f"container-{len(self.containers) + 1}"
            if query.get("name") in {item["Name"] for item in self.containers.values()}:
                return _json_error(409, "name already exists")
            if self.drop_storage:
                body["HostConfig"].pop("StorageOpt", None)
            if self.drop_memory_swap:
                body["HostConfig"].pop("MemorySwap", None)
            if self.drop_cpu_set:
                body["HostConfig"].pop("CpusetCpus", None)
            self.containers[container_id] = {
                "Id": container_id,
                "Name": query.get("name"),
                "Config": {"Image": body["Image"], "Labels": body.get("Labels") or {}},
                "HostConfig": body["HostConfig"],
                "State": {"Running": False},
                "create": body,
                "files": {},
                "directories": {"/"},
                "deleted": False,
            }
            if self.lose_create_response:
                return _json_error(503, "injected lost create response")
            return web.json_response({"Id": container_id}, status=201)
        if request.method == "GET" and path == "/containers/json":
            return web.json_response([
                {"Id": item["Id"], "Names": ["/" + item["Name"]], "Labels": item["Config"]["Labels"]}
                for item in self.containers.values()
                if not item["deleted"] and item["Config"]["Labels"].get("org.tcsexam.managed") == "docker-adapter"
            ])
        container_match = re.fullmatch(r"/containers/([^/]+)(?:/(.*))?", path)
        if container_match:
            container_id, action = container_match.group(1, 2)
            container = self.containers.get(container_id) or next(
                (item for item in self.containers.values() if item["Name"] == container_id), None
            )
            if container is None or container["deleted"]:
                return _json_error(404, "no such container")
            if request.method == "GET" and action == "json":
                return web.json_response({
                    "Id": container["Id"],
                    "Config": container["Config"],
                    "HostConfig": container["HostConfig"],
                    "State": container["State"],
                })
            if request.method == "POST" and action == "start":
                if self.fail_start:
                    return _json_error(500, "injected start failure")
                if self.started is not None:
                    self.started.set()
                if self.start_delay:
                    await asyncio.sleep(self.start_delay)
                if not container["deleted"]:
                    container["State"] = {"Running": True}
                return web.Response(status=204)
            if request.method == "POST" and action == "update":
                update = await request.json()
                if not self.drop_cpu_set:
                    container['HostConfig'].update(update)
                return web.json_response({'Warnings': []})
            if request.method == "DELETE" and action is None:
                if self.fail_delete:
                    return _json_error(500, 'injected delete failure')
                container["deleted"] = True
                container["State"] = {"Running": False}
                self.removed.append(container["Id"])
                return web.Response(status=204)
            if request.method == "PUT" and action == "archive":
                directory = query["path"]
                if directory not in container["directories"]:
                    return _json_error(404, "parent directory does not exist")
                data = await request.read()
                with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
                    members = archive.getmembers()
                    if len(members) != 1:
                        return _json_error(400, "expected one file")
                    member = members[0]
                    container["files"][str(PurePosixPath(directory) / member.name)] = archive.extractfile(member).read()
                return web.Response(status=200)
            if request.method == "GET" and action == "archive":
                data = container["files"].get(query["path"])
                if data is None:
                    return _json_error(404, "file does not exist")
                buffer = io.BytesIO()
                with tarfile.open(fileobj=buffer, mode="w") as archive:
                    member = tarfile.TarInfo(PurePosixPath(query["path"]).name)
                    member.size = len(data)
                    archive.addfile(member, io.BytesIO(data))
                if self.fragment_responses:
                    return await self.fragmented(request, buffer.getvalue(), "application/x-tar")
                return web.Response(body=buffer.getvalue(), content_type="application/x-tar")
            if request.method == "POST" and action == "exec":
                config = await request.json()
                exec_id = f"exec-{len(self.execs) + 1}"
                self.execs[exec_id] = {"container": container, "config": config, "returncode": None}
                return web.json_response({"Id": exec_id}, status=201)
        exec_match = re.fullmatch(r"/exec/([^/]+)/(start|json)", path)
        if exec_match:
            execution = self.execs.get(exec_match.group(1))
            if execution is None:
                return _json_error(404, "no such exec")
            if exec_match.group(2) == "json":
                return web.json_response({"Running": False, "ExitCode": execution["returncode"]})
            if self.exec_delay:
                await asyncio.sleep(self.exec_delay)
            returncode, stdout, stderr = self.execute(execution)
            execution["returncode"] = returncode
            response = web.StreamResponse(headers={"Content-Type": "application/vnd.docker.multiplexed-stream"})
            await response.prepare(request)
            for stream, data in ((1, stdout), (2, stderr)):
                if data:
                    await response.write(struct.pack(">B3xI", stream, len(data)) + data)
            await response.write_eof()
            return response
        return _json_error(404, "unknown Docker endpoint")

    def execute(self, execution: dict) -> tuple[int, bytes, bytes]:
        command = execution["config"].get("Cmd") or []
        script = command[2] if command[:2] == ["/bin/sh", "-c"] and len(command) == 3 else ""
        if 'Cpus_allowed_list:' in script and '/proc/self/status' in script:
            from tcsexam.backend.docker_adapter import _parse_cpu_set
            available = _parse_cpu_set(self.cpu_set or f'0-{self.ncpu - 1}')
            configured = execution['container']['HostConfig'].get('CpusetCpus')
            actual = sorted(set(available) & set(_parse_cpu_set(configured))) if configured else available
            return 0, ('Cpus_allowed_list:\t' + ','.join(map(str, actual)) + '\n').encode(), b''
        if script.startswith("mkdir -p -- "):
            directory = PurePosixPath(shlex.split(script)[3])
            execution["container"]["directories"].update(
                str(path) for path in (directory, *directory.parents)
            )
            return 0, b"", b""
        if script == "echo contract-marker":
            return 0, b"contract-marker\n", b""
        if "exit 3" in script:
            return 3, b"", b"injected-stderr\n"
        if command == ["printf", "plain"]:
            return 0, b"plain", b""
        return 0, b"", b""


def _config(daemon: FakeDockerDaemon) -> Config:
    return Config(
        docker_socket=str(daemon.socket_path),
        public_base_url="http://host.docker.internal:8420",
        archive_token="archive-test-secret",
        token_id="client-id",
        token_secret="client-secret",
        backend=BackendConfig(
            create_retries=0,
            create_retry_delay_seconds=0.01,
            ready_timeout_seconds=5,
            create_concurrency=8,
            judge_sessions=JudgeSessionsConfig(
                ttl_seconds=10,
                spec={"cpu_count": 1, "memory_mb": 1024, "storage_mb": 1024},
            ),
        ),
    )


@asynccontextmanager
async def running_adapter(tmp_path: Path):
    daemon = FakeDockerDaemon(tmp_path / "docker.sock")
    await daemon.start()
    adapter = load_adapter("docker", _config(daemon))
    try:
        yield adapter, daemon
    finally:
        for worker in list(adapter._workers.values()):
            await worker.delete()
        await adapter.close()
        await daemon.close()


def test_adapter_contract_over_unix_socket(tmp_path: Path) -> None:
    async def scenario() -> None:
        async with running_adapter(tmp_path) as (adapter, daemon):
            results = await run_contract_suite(
                adapter, image="registry.example.com/judge:1", profile="cpu"
            )
            assert [result.name for result in results if not result.ok] == []
            assert all(
                not item["create"]["HostConfig"].get("Binds")
                for item in daemon.containers.values()
            )
            assert not adapter._workers

    asyncio.run(scenario())


def test_resources_files_commands_and_scoped_cleanup(tmp_path: Path) -> None:
    async def scenario() -> None:
        async with running_adapter(tmp_path) as (adapter, daemon):
            worker = await adapter.create_sandbox(
                "cpu", "registry.example.com/judge:1", ttl_seconds=5,
                spec={"cpu_count": 1, "memory_mb": 1024, "storage_mb": 2048},
                group_name="tcsexam--run-1",
                labels={"run_id": "run-1", "token_id": "client-id"},
            )
            container = daemon.containers[worker.container_id]
            request = container["create"]
            assert request["Image"] == "registry.example.com/judge:1"
            assert request["Entrypoint"] == ["/bin/sh"]
            assert request["Cmd"] == ["-c", "sleep infinity"]
            assert request["HostConfig"] == {
                "Memory": 1024 * _MIB,
                "MemorySwap": 1024 * _MIB,
                "NanoCpus": 1_000_000_000,
                "CpusetCpus": "0",
                "NetworkMode": "bridge",
                "Privileged": False,
                "ExtraHosts": ["host.docker.internal:host-gateway"],
                "StorageOpt": {"size": str(2048 * _MIB)},
            }
            assert "Env" not in request
            assert "archive-test-secret" not in json.dumps(request)
            assert str(daemon.socket_path) not in json.dumps(request)
            assert json.loads(request["Labels"]["org.tcsexam.request-labels"])["run_id"] == "run-1"
            assert request["Labels"]["org.tcsexam.group"] == "tcsexam--run-1"

            await worker.ctrl.write_bytes("/tcsexam-backend/nested/probe.txt", "中文\n".encode(), parents=True)
            assert await worker.ctrl.read_text("/tcsexam-backend/nested/probe.txt") == "中文\n"
            with pytest.raises(FileNotFoundError):
                await worker.ctrl.read_text("/missing")
            with pytest.raises(DockerNotFoundError):
                await worker.ctrl.write_bytes("/missing-parent/file", b"x")
            result = await worker.ctrl.run("echo contract-marker", shell=True, text=True)
            assert (result.returncode, result.stdout) == (0, "contract-marker\n")
            failure = await worker.ctrl.run("exit 3", shell=True, text=True)
            assert failure.returncode == 3 and failure.stderr == "injected-stderr\n"
            plain = await worker.ctrl.run("printf plain", env={"ZERO": "0", "OTHER": "value"})
            assert plain.stdout == b"plain"
            assert daemon.execs[f"exec-{len(daemon.execs)}"]["config"]["Env"] == ["ZERO=0", "OTHER=value"]
            with pytest.raises(ValueError):
                await worker.ctrl.run("true", env={"BAD=KEY": "x"})

            other = await adapter.create_sandbox("cpu", "registry.example.com/judge:1")
            adapter.register_long_lived("first", worker)
            adapter.register_long_lived("second", other)
            await adapter.stop_app("first")
            assert not other.deleted
            assert not daemon.containers[other.container_id]["deleted"]
            await worker.delete()
            await worker.delete()
            assert daemon.removed.count(worker.container_id) == 1
            await adapter.stop_app("unknown")

    asyncio.run(scenario())


def test_pull_and_api_version_negotiation(tmp_path: Path) -> None:
    async def scenario() -> None:
        async with running_adapter(tmp_path) as (adapter, daemon):
            daemon.minimum_api = (1, 44)
            worker = await adapter.create_sandbox("cpu", "registry.example.com/new-judge:2")
            assert daemon.pulled == ["registry.example.com/new-judge:2"]
            assert adapter.engine.api_version == "1.44"
            assert daemon.containers[worker.container_id]["create"]["Image"].endswith("new-judge:2")
            await worker.delete()
            adapter.pull_missing_images = False
            with pytest.raises(InvalidArgumentError, match="automatic pulling is disabled"):
                await adapter.create_sandbox("cpu", "registry.example.com/missing:3")
            adapter.pull_missing_images = True
            daemon.pull_error = True
            with pytest.raises(InvalidArgumentError, match="repository not found"):
                await adapter.create_sandbox("cpu", "registry.example.com/missing:4")

    asyncio.run(scenario())


def test_capacity_refusal_and_no_resource_downgrade(tmp_path: Path) -> None:
    async def scenario() -> None:
        async with running_adapter(tmp_path) as (adapter, daemon):
            daemon.ncpu = 4
            daemon.memory_mb = 8192
            workers = await asyncio.gather(*[
                adapter.create_sandbox(
                    "cpu", "registry.example.com/judge:1",
                    spec={"cpu_count": 2, "memory_mb": 4096, "storage_mb": None},
                ) for _ in range(2)
            ])
            assert len(workers) == 2
            with pytest.raises(DockerCapacityError):
                await adapter.create_sandbox("cpu", "registry.example.com/judge:1", ready_timeout_seconds=0.05)
            for worker in workers:
                await worker.delete()
            with pytest.raises(InvalidArgumentError, match="exceeds Docker daemon capacity"):
                await adapter.create_sandbox(
                    "cpu", "registry.example.com/judge:1",
                    spec={"cpu_count": 5, "memory_mb": 1024, "storage_mb": None},
                )
            daemon.drop_storage = True
            with pytest.raises(InvalidArgumentError, match="storage quota"):
                await adapter.create_sandbox("cpu", "registry.example.com/judge:1")
            assert all(item["deleted"] for item in daemon.containers.values())
            assert not adapter._workers
            daemon.memory_limit = False
            with pytest.raises(InvalidArgumentError, match="memory limits"):
                await adapter.create_sandbox(
                    "cpu", "registry.example.com/judge:1",
                    spec={"cpu_count": 1, "memory_mb": 1024, "storage_mb": None},
                )

    asyncio.run(scenario())


def test_swap_support_is_required_before_creation(tmp_path: Path) -> None:
    async def scenario() -> None:
        async with running_adapter(tmp_path) as (adapter, daemon):
            daemon.swap_limit = False
            with pytest.raises(InvalidArgumentError, match="support swap limits"):
                await adapter.create_sandbox("cpu", "registry.example.com/judge:1")
            assert not daemon.containers
            assert not adapter._pending

    asyncio.run(scenario())


def test_dropped_swap_limit_rejects_and_removes_worker(tmp_path: Path) -> None:
    async def scenario() -> None:
        async with running_adapter(tmp_path) as (adapter, daemon):
            daemon.drop_memory_swap = True
            with pytest.raises(InvalidArgumentError, match="MemorySwap"):
                await adapter.create_sandbox("cpu", "registry.example.com/judge:1")
            assert len(daemon.containers) == 1
            assert all(item["deleted"] for item in daemon.containers.values())
            assert not adapter._workers and not adapter._pending
            daemon.drop_memory_swap = False
            worker = await adapter.create_sandbox("cpu", "registry.example.com/judge:1")
            await worker.delete()

    asyncio.run(scenario())


@pytest.mark.parametrize('swap', [None, -1, 2 * 1024 * _MIB])
def test_restart_refuses_live_workers_with_unrestricted_swap(tmp_path: Path, swap) -> None:
    async def scenario() -> None:
        async with running_adapter(tmp_path) as (first, daemon):
            old = await first.create_sandbox("cpu", "registry.example.com/judge:1",
                                            spec={"cpu_count": 1, "memory_mb": 1024, "storage_mb": None})
            await first.close()
            daemon.containers[old.container_id]['HostConfig']['MemorySwap'] = swap
            second = load_adapter("docker", _config(daemon))
            try:
                with pytest.raises(InvalidArgumentError, match="live managed Docker worker.*swap"):
                    await second.create_sandbox("cpu", "registry.example.com/judge:1")
                assert len(daemon.containers) == 1
                assert not daemon.containers[old.container_id]['deleted']
            finally:
                await old.delete()
                await second.close()

    asyncio.run(scenario())


def test_ttl_delete_and_external_delete_are_idempotent(tmp_path: Path) -> None:
    async def scenario() -> None:
        async with running_adapter(tmp_path) as (adapter, daemon):
            worker = await adapter.create_sandbox(
                "cpu", "registry.example.com/judge:1", ttl_seconds=0.05
            )
            for _ in range(100):
                if worker.deleted:
                    break
                await asyncio.sleep(0.01)
            assert worker.deleted
            assert daemon.containers[worker.container_id]["deleted"]
            assert not adapter._ttl_tasks

            other = await adapter.create_sandbox("cpu", "registry.example.com/judge:1")
            container = daemon.containers[other.container_id]
            container["deleted"] = True
            await other.delete()
            await other.delete()
            assert other.deleted

    asyncio.run(scenario())


def test_failed_and_cancelled_creation_clean_up_only_owned_worker(tmp_path: Path) -> None:
    async def scenario() -> None:
        async with running_adapter(tmp_path) as (adapter, daemon):
            daemon.fail_start = True
            with pytest.raises(Exception, match="injected start failure"):
                await adapter.create_sandbox("cpu", "registry.example.com/judge:1")
            assert all(item["deleted"] for item in daemon.containers.values())
            assert not adapter._workers and not adapter._pending and not adapter._ttl_tasks

            daemon.fail_start = False
            daemon.start_delay = 0.2
            daemon.started = asyncio.Event()
            task = asyncio.create_task(adapter.create_sandbox("cpu", "registry.example.com/judge:1"))
            await asyncio.wait_for(daemon.started.wait(), timeout=1)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert len(daemon.containers) == 2
            assert all(item["deleted"] for item in daemon.containers.values())
            assert not adapter._workers and not adapter._pending and not adapter._ttl_tasks
            assert daemon.removed == ["container-1", "container-2"]

    asyncio.run(scenario())


def test_command_timeout_and_deleted_worker_errors(tmp_path: Path) -> None:
    async def scenario() -> None:
        async with running_adapter(tmp_path) as (adapter, daemon):
            worker = await adapter.create_sandbox("cpu", "registry.example.com/judge:1")
            daemon.exec_delay = 0.1
            with pytest.raises(TimeoutError):
                await worker.ctrl.run("echo contract-marker", shell=True, timeout=0.01)
            daemon.exec_delay = 0
            await worker.delete()
            with pytest.raises(RuntimeError, match="deleted"):
                await worker.ctrl.run("true")
            with pytest.raises(ValueError):
                await worker.ctrl.write_bytes("/../escape", b"x")

    asyncio.run(scenario())


def test_fragmented_json_pull_and_archive_are_read_to_eof(tmp_path: Path) -> None:
    async def scenario() -> None:
        async with running_adapter(tmp_path) as (adapter, daemon):
            daemon.fragment_responses = True
            worker = await adapter.create_sandbox("cpu", "registry.example.com/new-judge:2")
            payload = "分段读取-中文\n".encode() * 100
            await worker.ctrl.write_bytes("/tcsexam-backend/probe", payload, parents=True)
            assert await worker.ctrl.read_text("/tcsexam-backend/probe") == payload.decode()
            result = await worker.ctrl.run("echo contract-marker", shell=True, text=True)
            assert result.stdout == "contract-marker\n"
            await worker.delete()

    asyncio.run(scenario())


def test_slow_pull_uses_the_full_creation_budget(tmp_path: Path) -> None:
    async def scenario() -> None:
        async with running_adapter(tmp_path) as (adapter, daemon):
            adapter.api_timeout_seconds = 0.1
            daemon.pull_delay = 0.25
            worker = await adapter.create_sandbox("cpu", "registry.example.com/slow-judge:1")
            assert daemon.pulled == ["registry.example.com/slow-judge:1"]
            await worker.delete()

    asyncio.run(scenario())


def test_lost_create_response_is_reconciled_by_unique_name(tmp_path: Path) -> None:
    async def scenario() -> None:
        async with running_adapter(tmp_path) as (adapter, daemon):
            daemon.lose_create_response = True
            with pytest.raises(Exception, match="injected lost create response"):
                await adapter.create_sandbox("cpu", "registry.example.com/judge:1")
            assert len(daemon.containers) == 1
            assert all(item["deleted"] for item in daemon.containers.values())
            assert not adapter._workers and not adapter._pending and not adapter._ttl_tasks

    asyncio.run(scenario())


def test_restart_adopts_live_workers_and_restores_ttl_and_capacity(tmp_path: Path) -> None:
    async def scenario() -> None:
        async with running_adapter(tmp_path) as (first, daemon):
            daemon.ncpu = 2
            daemon.memory_mb = 2048
            old = await first.create_sandbox(
                "cpu", "registry.example.com/judge:1", ttl_seconds=0.25,
                spec={"cpu_count": 1, "memory_mb": 1024, "storage_mb": None},
            )
            await first.close()
            second = load_adapter("docker", _config(daemon))
            try:
                current = await second.create_sandbox(
                    "cpu", "registry.example.com/judge:1",
                    spec={"cpu_count": 1, "memory_mb": 1024, "storage_mb": None},
                )
                assert set(second._workers) == {old.container_id, current.container_id}
                with pytest.raises(DockerCapacityError):
                    await second.create_sandbox("cpu", "registry.example.com/judge:1", ready_timeout_seconds=0.05)
                for _ in range(100):
                    if daemon.containers[old.container_id]["deleted"]:
                        break
                    await asyncio.sleep(0.01)
                assert daemon.containers[old.container_id]["deleted"]
                assert not current.deleted
                assert old.container_id not in second._workers
                await current.delete()
            finally:
                for worker in list(second._workers.values()):
                    await worker.delete()
                await second.close()

    asyncio.run(scenario())


def test_restart_removes_only_expired_managed_workers(tmp_path: Path) -> None:
    async def scenario() -> None:
        async with running_adapter(tmp_path) as (first, daemon):
            daemon.containers["external"] = {
                "Id": "external", "Name": "other-service",
                "Config": {"Image": "other", "Labels": {}},
                "HostConfig": {"Memory": _MIB, "NanoCpus": 1_000_000_000},
                "State": {"Running": True}, "deleted": False,
            }
            expired = await first.create_sandbox("cpu", "registry.example.com/judge:1", ttl_seconds=0.02)
            await first.close()
            await asyncio.sleep(0.03)
            second = load_adapter("docker", _config(daemon))
            try:
                current = await second.create_sandbox("cpu", "registry.example.com/judge:1", ready_timeout_seconds=0.05)
                assert daemon.containers[expired.container_id]["deleted"]
                assert not daemon.containers["external"]["deleted"]
                await current.delete()
            finally:
                await second.close()

    asyncio.run(scenario())


def test_docker_rejects_a_loopback_tunnel_address(tmp_path: Path) -> None:
    config = _config(FakeDockerDaemon(tmp_path / "unused.sock"))
    config.public_base_url = ""
    with pytest.raises(ValueError, match="public_base_url"):
        load_adapter("docker", config)


def test_capacity_queue_releases_and_cancelled_waiter_reserves_nothing(tmp_path):
    async def scenario():
        async with running_adapter(tmp_path) as (adapter, daemon):
            daemon.ncpu = 2
            daemon.memory_mb = 4096
            spec = {"cpu_count": 2, "memory_mb": 4096, "storage_mb": None}
            first = await adapter.create_sandbox("cpu", "registry.example.com/judge:1", spec=spec)
            waiting = asyncio.create_task(adapter.create_sandbox("cpu", "registry.example.com/judge:1", spec=spec))
            await asyncio.sleep(0.05)
            assert not waiting.done()
            assert not adapter._pending
            waiting.cancel()
            with pytest.raises(asyncio.CancelledError):
                await waiting
            assert not adapter._pending
            waiting = asyncio.create_task(adapter.create_sandbox("cpu", "registry.example.com/judge:1", spec=spec))
            await asyncio.sleep(0.05)
            await first.delete()
            second = await asyncio.wait_for(waiting, 2)
            assert second.resources.cpu_count == 2 and second.resources.memory_mb == 4096
            await second.delete()
            assert not adapter._pending and not adapter._workers
    asyncio.run(scenario())
