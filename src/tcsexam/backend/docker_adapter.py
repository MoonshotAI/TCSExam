"""Docker Engine worker adapter for the self-hosted judging backend.

Managed workers receive disjoint logical CPU sets as well as CPU quotas.
CPU IDs are discovered inside the target daemon's first unpublished worker,
not inferred from this backend process's host or from Docker's CPU count.
One backend owns admissions to a daemon; this does not reserve cores against
unmanaged host processes or a second independent backend using that daemon.
"""
from __future__ import annotations

import asyncio
import io
import json
import shlex
import struct
import subprocess
import tarfile
import time
import urllib.parse
import uuid
from pathlib import PurePosixPath
from typing import Any

import aiohttp
from yarl import URL

from .adapter import BasePlatformAdapter, WorkerResources

_MIB = 1024 * 1024
_CONTROL_FILE_LIMIT = 64 * _MIB
_COMMAND_OUTPUT_LIMIT = 64 * _MIB
_CPUSET_PROBE = (
    'while IFS= read -r line; do case "$line" in '
    'Cpus_allowed_list:*) printf "%s\\n" "$line";; esac; done < /proc/self/status'
)


def _parse_cpu_set(value: str) -> tuple[int, ...]:
    """Parse Linux CPU list syntax without assuming contiguous CPU IDs."""
    if not isinstance(value, str):
        raise InvalidArgumentError("Docker CPU set must be a Linux CPU list")
    result: set[int] = set()
    for entry in value.strip().split(','):
        ends = entry.split('-')
        if len(ends) not in (1, 2) or not all(part.isdecimal() for part in ends):
            raise InvalidArgumentError("Docker CPU set must be a nonempty Linux CPU list")
        first, last = int(ends[0]), int(ends[-1])
        if last < first or last - first >= 65536 or len(result) + last - first + 1 > 65536:
            raise InvalidArgumentError("Docker CPU set has an invalid or oversized range")
        cpus = set(range(first, last + 1))
        if cpus & result:
            raise InvalidArgumentError("Docker CPU set contains duplicate logical CPUs")
        result.update(cpus)
    return tuple(sorted(result))


def _format_cpu_set(cpus: tuple[int, ...]) -> str:
    return ','.join(map(str, cpus))


class DockerError(RuntimeError):
    def __init__(self, status: int, message: str) -> None:
        self.status = status
        self.message = message
        super().__init__(f"Docker HTTP {status}: {message}")


class DockerNotFoundError(DockerError):
    pass


class InvalidArgumentError(ValueError):
    pass


class AuthenticationError(RuntimeError):
    pass


class PermissionDeniedError(RuntimeError):
    pass


class DockerCapacityError(RuntimeError):
    pass


def _error_message(data: bytes) -> str:
    text = data.decode(errors="replace").strip()
    try:
        value = json.loads(text)
    except ValueError:
        value = None
    if isinstance(value, dict):
        text = str(value.get("message") or value.get("error") or text)
    return text[:2000] or "empty error response"


def _platform_error(error: DockerError) -> RuntimeError:
    if error.status == 400:
        return InvalidArgumentError(error.message)
    if error.status == 401:
        return AuthenticationError(error.message)
    if error.status == 403:
        return PermissionDeniedError(error.message)
    if error.status == 404:
        return DockerNotFoundError(error.status, error.message)
    return error


class DockerEngine:
    def __init__(self, socket_path: str, *, api_timeout_seconds: float = 60.0) -> None:
        self.socket_path = socket_path
        self.api_timeout_seconds = api_timeout_seconds
        self.api_version = "1.41"

    async def request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        data: bytes | None = None,
        timeout: float | None = None,
        response_limit: int = _CONTROL_FILE_LIMIT,
        raw: bool = False,
    ) -> Any:
        try:
            return await self._request_once(
                method, path, query=query, body=body, data=data,
                timeout=timeout, response_limit=response_limit, raw=raw,
            )
        except DockerError as exc:
            minimum = self._required_api_version(exc)
            if minimum is None:
                raise _platform_error(exc) from None
            self.api_version = minimum
            try:
                return await self._request_once(
                    method, path, query=query, body=body, data=data,
                    timeout=timeout, response_limit=response_limit, raw=raw,
                )
            except DockerError as retry_exc:
                raise _platform_error(retry_exc) from None

    @staticmethod
    def _required_api_version(error: DockerError) -> str | None:
        if error.status != 400:
            return None
        import re

        match = re.search(r"minimum supported API version is (\d+\.\d+)", error.message, re.I)
        return match.group(1) if match else None

    async def _request_once(self, method, path, *, query, body, data, timeout, response_limit, raw) -> Any:
        timeout = self.api_timeout_seconds if timeout is None else timeout
        if timeout <= 0:
            raise TimeoutError("Docker request exceeded its creation budget")
        url = URL(f"http://localhost/v{self.api_version}{path}", encoded=True)
        headers = {"Content-Type": "application/x-tar"} if data is not None else {}
        params = None if query is None else {key: str(value) for key, value in query.items()}
        try:
            async with aiohttp.ClientSession(
                connector=aiohttp.UnixConnector(self.socket_path),
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as session:
                async with session.request(
                    method, url, params=params, json=body, data=data, headers=headers
                ) as response:
                    payload = await self._read_bounded(response, response_limit)
                    if response.status >= 400:
                        raise DockerError(response.status, _error_message(payload))
                    if not payload:
                        return None
                    content_type = response.headers.get("Content-Type", "")
                    if not raw and content_type.startswith("application/json"):
                        return json.loads(payload)
                    return payload
        except aiohttp.ClientError as exc:
            candidates = (exc, exc.__cause__, getattr(exc, "os_error", None))
            if any(isinstance(candidate, PermissionError) for candidate in candidates):
                raise PermissionDeniedError(
                    "cannot access the Docker Unix socket; check the backend user's socket permissions"
                ) from None
            raise DockerError(503, f"cannot communicate with the Docker daemon: {exc}") from None

    @staticmethod
    async def _read_bounded(response: aiohttp.ClientResponse, limit: int) -> bytes:
        payload = bytearray()
        while True:
            chunk = await response.content.read(min(_MIB, limit + 1 - len(payload)))
            if not chunk:
                return bytes(payload)
            payload.extend(chunk)
            if len(payload) > limit:
                raise DockerError(500, "Docker response exceeded the control-channel limit")

    async def info(self, timeout: float) -> dict[str, Any]:
        return await self.request("GET", "/info", timeout=timeout)

    async def inspect_image(self, image: str, timeout: float) -> dict[str, Any] | None:
        try:
            return await self.request(
                "GET", f"/images/{urllib.parse.quote(image, safe='')}/json", timeout=timeout
            )
        except DockerNotFoundError:
            return None

    async def pull_image(self, image: str, timeout: float) -> None:
        result = await self.request(
            "POST", "/images/create", query={"fromImage": image}, timeout=timeout,
            response_limit=8 * _MIB, raw=True,
        )
        text = result.decode(errors="replace") if isinstance(result, bytes) else str(result or "")
        for line in text.splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if isinstance(event, dict) and event.get("error"):
                raise InvalidArgumentError(f"Docker image pull failed: {str(event['error'])[:1000]}")

    async def create_container(self, name: str, config: dict[str, Any], timeout: float) -> str:
        result = await self.request(
            "POST", "/containers/create", query={"name": name}, body=config, timeout=timeout
        )
        container_id = result.get("Id") if isinstance(result, dict) else None
        if not isinstance(container_id, str) or not container_id:
            raise DockerError(500, "Docker create returned no container id")
        return container_id

    async def start_container(self, container_id: str, timeout: float) -> None:
        await self.request("POST", f"/containers/{container_id}/start", timeout=timeout)

    async def update_cpu_set(self, container_id: str, cpus: tuple[int, ...], timeout: float) -> None:
        result = await self.request(
            "POST", f"/containers/{container_id}/update",
            body={"CpusetCpus": _format_cpu_set(cpus)}, timeout=timeout,
        )
        if isinstance(result, dict) and result.get("Warnings"):
            raise InvalidArgumentError("Docker could not enforce the worker CPU set")

    async def inspect_container(self, container_id: str, timeout: float = 30) -> dict[str, Any]:
        return await self.request("GET", f"/containers/{container_id}/json", timeout=timeout)

    async def list_managed_containers(self, timeout: float) -> list[dict[str, Any]]:
        filters = json.dumps({"label": ["org.tcsexam.managed=docker-adapter"]})
        result = await self.request(
            "GET", "/containers/json", query={"all": "1", "filters": filters}, timeout=timeout
        )
        if not isinstance(result, list):
            raise DockerError(500, "Docker container list returned an invalid response")
        return result

    async def delete_container(self, container_id: str) -> None:
        try:
            await self.request(
                "DELETE", f"/containers/{container_id}", query={"force": "1", "v": "1"}
            )
        except DockerNotFoundError:
            pass

    async def put_archive(self, container_id: str, directory: str, data: bytes) -> None:
        await self.request(
            "PUT", f"/containers/{container_id}/archive",
            query={"path": directory, "copyUIDGID": "true"}, data=data, timeout=600,
        )

    async def get_archive(self, container_id: str, path: str) -> bytes:
        result = await self.request(
            "GET", f"/containers/{container_id}/archive", query={"path": path}, timeout=600
        )
        if not isinstance(result, bytes):
            raise DockerError(500, "Docker archive returned no tar data")
        return result

    async def execute(self, container_id: str, config: dict[str, Any], timeout: float) -> tuple[bytes, bytes, int]:
        created = await self.request("POST", f"/containers/{container_id}/exec", body=config, timeout=timeout)
        exec_id = created.get("Id") if isinstance(created, dict) else None
        if not isinstance(exec_id, str) or not exec_id:
            raise DockerError(500, "Docker exec create returned no id")
        url = URL(f"http://localhost/v{self.api_version}/exec/{exec_id}/start", encoded=True)
        stdout = bytearray()
        stderr = bytearray()
        try:
            async with aiohttp.ClientSession(
                connector=aiohttp.UnixConnector(self.socket_path),
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as session:
                async with session.post(url, json={"Detach": False, "Tty": False}) as response:
                    if response.status >= 400:
                        data = await response.content.read(4096)
                        raise _platform_error(DockerError(response.status, _error_message(data)))
                    while True:
                        try:
                            header = await response.content.readexactly(8)
                        except asyncio.IncompleteReadError as exc:
                            if not exc.partial:
                                break
                            raise DockerError(500, "truncated Docker exec stream") from None
                        stream, size = struct.unpack(">B3xI", header)
                        if stream not in (1, 2) or size > _COMMAND_OUTPUT_LIMIT:
                            raise DockerError(500, "invalid Docker exec output frame")
                        data = await response.content.readexactly(size)
                        target = stdout if stream == 1 else stderr
                        if len(stdout) + len(stderr) + len(data) > _COMMAND_OUTPUT_LIMIT:
                            raise DockerError(500, "Docker exec output exceeded 64 MiB")
                        target.extend(data)
        except aiohttp.ClientError as exc:
            raise DockerError(503, f"cannot communicate with the Docker daemon: {exc}") from None
        inspection = await self.request("GET", f"/exec/{exec_id}/json", timeout=timeout)
        if inspection.get("Running") or inspection.get("ExitCode") is None:
            raise DockerError(500, "Docker exec ended without an exit status")
        return bytes(stdout), bytes(stderr), int(inspection["ExitCode"])


def _worker_path(path: str) -> PurePosixPath:
    if not isinstance(path, str) or "\x00" in path:
        raise ValueError("worker path must be a string without NUL bytes")
    result = PurePosixPath(path)
    if not result.is_absolute() or result == PurePosixPath("/") or ".." in result.parts:
        raise ValueError(f"worker path must be an absolute non-root path without '..': {path!r}")
    return result


def _archive_bytes(path: PurePosixPath, data: bytes) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        member = tarfile.TarInfo(path.name)
        member.size = len(data)
        member.mode = 0o600
        member.mtime = 0
        archive.addfile(member, io.BytesIO(data))
    return buffer.getvalue()


class DockerControl:
    def __init__(self, worker: DockerWorker) -> None:
        self.worker = worker

    async def write_bytes(self, path: str, data: bytes, parents: bool = False) -> None:
        destination = _worker_path(path)
        if not isinstance(data, bytes):
            raise TypeError("worker file data must be bytes")
        if len(data) > _CONTROL_FILE_LIMIT:
            raise ValueError("worker control file exceeds 64 MiB")
        self.worker.ensure_live()
        if parents:
            result = await self.run(
                f"mkdir -p -- {shlex.quote(str(destination.parent))}", shell=True, text=True
            )
            if result.returncode:
                raise RuntimeError(f"cannot create worker directory {destination.parent}: {result.stderr}")
        await self.worker.engine.put_archive(
            self.worker.container_id, str(destination.parent), _archive_bytes(destination, data)
        )

    async def read_text(self, path: str) -> str:
        source = _worker_path(path)
        self.worker.ensure_live()
        try:
            data = await self.worker.engine.get_archive(self.worker.container_id, str(source))
        except DockerNotFoundError as exc:
            raise FileNotFoundError(path) from exc
        try:
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
                members = [member for member in archive.getmembers() if member.isfile()]
                if len(members) != 1:
                    raise IsADirectoryError(path)
                member = members[0]
                if member.size > _CONTROL_FILE_LIMIT:
                    raise ValueError("worker control file exceeds 64 MiB")
                extracted = archive.extractfile(member)
                if extracted is None:
                    raise FileNotFoundError(path)
                return extracted.read().decode(errors="replace")
        except tarfile.TarError as exc:
            raise RuntimeError(f"cannot read worker file {path}: invalid archive") from exc

    async def run(self, cmd: str, shell: bool = False, text: bool = False, timeout: float = 30,
                  env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
        if not isinstance(cmd, str) or not cmd or timeout <= 0:
            raise ValueError("Docker exec requires a nonempty command and a positive timeout")
        command = ["/bin/sh", "-c", cmd] if shell else shlex.split(cmd)
        if not command:
            raise ValueError("Docker exec command is empty")
        config: dict[str, Any] = {
            "Cmd": command,
            "AttachStdout": True,
            "AttachStderr": True,
            "Tty": False,
        }
        if env:
            entries = []
            for key, value in env.items():
                if not isinstance(key, str) or not key or "=" in key or "\x00" in key or "\x00" in str(value):
                    raise ValueError("invalid Docker exec environment")
                entries.append(f"{key}={value}")
            config["Env"] = entries
        self.worker.ensure_live()
        stdout, stderr, returncode = await self.worker.engine.execute(
            self.worker.container_id, config, float(timeout)
        )
        if text:
            stdout_result: bytes | str = stdout.decode(errors="replace")
            stderr_result: bytes | str = stderr.decode(errors="replace")
        else:
            stdout_result, stderr_result = stdout, stderr
        return subprocess.CompletedProcess(cmd, returncode, stdout_result, stderr_result)


class DockerWorker:
    def __init__(self, adapter: DockerAdapter, container_id: str, name: str,
                 resources: WorkerResources, cpu_ids: tuple[int, ...] = ()) -> None:
        self.adapter = adapter
        self.engine = adapter.engine
        self.container_id = container_id
        self.name = name
        self.resources = resources
        self.cpu_ids = cpu_ids
        self.ctrl = DockerControl(self)
        self.deleted = False
        self._delete_lock = asyncio.Lock()

    def ensure_live(self) -> None:
        if self.deleted:
            raise RuntimeError(f"Docker worker {self.name} has been deleted")

    async def delete(self) -> None:
        async with self._delete_lock:
            if self.deleted:
                return
            try:
                await self.engine.delete_container(self.container_id)
            except Exception as exc:
                self.adapter.LOGGER.warning("could not delete Docker worker %s: %s", self.name, exc)
                raise
            self.deleted = True
            self.adapter._forget_worker(self)


class DockerAdapter(BasePlatformAdapter):
    logger_name = "tcsexam.backend.docker_adapter"

    def __init__(self, config: Any, *, engine: DockerEngine | None = None) -> None:
        backend = config.backend
        sessions = backend.judge_sessions
        super().__init__(
            create_retries=backend.create_retries,
            create_retry_delay_seconds=backend.create_retry_delay_seconds,
            ready_timeout_seconds=backend.ready_timeout_seconds,
            default_ttl_seconds=sessions.ttl_seconds,
            default_spec=sessions.spec,
            work_dir=sessions.work_dir,
            create_concurrency=backend.create_concurrency,
        )
        self.socket_path = getattr(config, "docker_socket", "/var/run/docker.sock")
        self.network = getattr(config, "docker_network", "bridge")
        self.pull_missing_images = getattr(config, "docker_pull_missing_images", True)
        self.host_gateway = getattr(config, "docker_host_gateway", True)
        self.api_timeout_seconds = getattr(config, "docker_api_timeout_seconds", 60.0)
        self.engine = engine or DockerEngine(self.socket_path, api_timeout_seconds=self.api_timeout_seconds)
        self._workers: dict[str, DockerWorker] = {}
        self._pending: dict[str, WorkerResources] = {}
        self._pending_cpus: dict[str, tuple[int, ...]] = {}
        self._available_cpus: tuple[int, ...] | None = None
        self._cpu_discovery_reservation: str | None = None
        self._ttl_tasks: dict[str, asyncio.Task] = {}
        self._admission_lock = asyncio.Lock()
        self._capacity_changed = asyncio.Event()
        self._recovery_lock = asyncio.Lock()
        self._recovered = False
        if self.network != "host" and urllib.parse.urlsplit(config.public_url()).hostname in {
            "127.0.0.1", "localhost", "::1"
        }:
            raise InvalidArgumentError(
                "adapter: docker requires public_base_url to be reachable from containers; "
                "for a backend on the Docker host use http://host.docker.internal:<port>"
            )

    @staticmethod
    def _validate_resources(resources: WorkerResources) -> None:
        if resources.cpu_count < 1 or resources.memory_mb < 1:
            raise InvalidArgumentError("Docker workers require positive cpu_count and memory_mb")
        if resources.storage_mb is not None and resources.storage_mb < 1:
            raise InvalidArgumentError("storage_mb must be positive or null")

    def _worker_from_inspection(self, inspection: dict[str, Any]) -> tuple[DockerWorker, float] | None:
        labels = (inspection.get("Config") or {}).get("Labels") or {}
        name = labels.get("org.tcsexam.worker", "")
        if labels.get("org.tcsexam.managed") != "docker-adapter" or not name.startswith("tcsexam-"):
            return None
        host_config = inspection.get("HostConfig") or {}
        try:
            import math

            expires_at = float(labels["org.tcsexam.expires-at"])
            memory_bytes = int(host_config["Memory"])
            nano_cpus = int(host_config["NanoCpus"])
            storage = (host_config.get("StorageOpt") or {}).get("size")
            if (
                not math.isfinite(expires_at)
                or memory_bytes <= 0 or memory_bytes % _MIB
                or nano_cpus <= 0 or nano_cpus % 1_000_000_000
            ):
                raise ValueError("invalid worker metadata")
            resources = WorkerResources(
                cpu_count=nano_cpus // 1_000_000_000,
                memory_mb=memory_bytes // _MIB,
                storage_mb=None if storage is None else int(storage) // _MIB,
            )
            container_id = inspection["Id"]
        except (KeyError, TypeError, ValueError):
            self.LOGGER.warning("ignoring a managed Docker container with invalid recovery metadata")
            return None
        cpu_value = host_config.get("CpusetCpus") or ""
        cpu_ids = _parse_cpu_set(cpu_value) if cpu_value else ()
        return DockerWorker(self, container_id, name, resources, cpu_ids), expires_at

    async def _ensure_recovered(self, timeout: float) -> None:
        if self._recovered:
            return
        async with self._recovery_lock:
            if self._recovered:
                return
            summaries = await self.engine.list_managed_containers(timeout)
            for summary in summaries:
                container_id = summary.get("Id") if isinstance(summary, dict) else None
                if not isinstance(container_id, str) or container_id in self._workers:
                    continue
                inspection = await self.engine.inspect_container(container_id, timeout)
                recovered = self._worker_from_inspection(inspection)
                if recovered is None:
                    continue
                worker, expires_at = recovered
                remaining = expires_at - time.time()
                if remaining <= 0:
                    await worker.delete()
                    continue
                if (inspection.get("HostConfig") or {}).get("MemorySwap") != worker.resources.memory_mb * _MIB:
                    raise InvalidArgumentError(
                        "a live managed Docker worker has no enforced swap prohibition; "
                        "finish or remove that worker before admitting new workers"
                    )
                if len(worker.cpu_ids) != worker.resources.cpu_count:
                    raise InvalidArgumentError(
                        "a live managed Docker worker has no exact CPU allocation; "
                        "finish or remove that worker before admitting new workers"
                    )
                if any(set(worker.cpu_ids) & set(other.cpu_ids) for other in self._workers.values()):
                    raise InvalidArgumentError("recovered Docker workers have overlapping CPU allocations")
                self._workers[container_id] = worker
                self._arm_ttl(worker, remaining)
            self._recovered = True

    async def _check_capacity(self, resources: WorkerResources, timeout: float,
                              reservation: str) -> None:
        info = await self.engine.info(timeout)
        if not info.get("MemoryLimit") or not info.get("CpuCfsQuota"):
            raise InvalidArgumentError("Docker daemon must enable memory limits and CPU quotas")
        if not info.get("SwapLimit"):
            raise InvalidArgumentError("Docker daemon must support swap limits to disable worker swap")
        if not info.get("CPUSet", info.get("Cpuset", False)):
            raise InvalidArgumentError("Docker daemon must support CPU sets for isolated worker CPUs")
        cpu_capacity = int(info.get("NCPU") or 0)
        if self._available_cpus is not None:
            cpu_capacity = min(cpu_capacity, len(self._available_cpus))
        memory_capacity = int(info.get("MemTotal") or 0) // _MIB
        if cpu_capacity < 1 or memory_capacity < 1:
            raise DockerCapacityError("Docker daemon reported no usable CPU or memory capacity")
        if resources.cpu_count > cpu_capacity or resources.memory_mb > memory_capacity:
            raise InvalidArgumentError(
                f"requested worker exceeds Docker daemon capacity: "
                f"requested {resources.cpu_count} CPUs/{resources.memory_mb} MiB, "
                f"available {cpu_capacity} CPUs/{memory_capacity} MiB"
            )
        if self._available_cpus is None and self._cpu_discovery_reservation not in (None, reservation):
            raise DockerCapacityError("waiting for the daemon's effective CPU set to be discovered")
        if any(not worker.cpu_ids and not worker.deleted for worker in self._workers.values()):
            raise InvalidArgumentError("an unpublished Docker worker still has no confirmed CPU allocation")
        active = [worker.resources for worker in self._workers.values() if not worker.deleted]
        active.extend(
            resource for token, resource in self._pending.items() if token != reservation
        )
        used_cpu = sum(resource.cpu_count for resource in active)
        used_memory = sum(resource.memory_mb for resource in active)
        if used_cpu + resources.cpu_count > cpu_capacity or used_memory + resources.memory_mb > memory_capacity:
            raise DockerCapacityError(
                "Docker workers would exceed daemon capacity with the new request; "
                "wait for existing workers to finish"
            )

    def _choose_cpu_ids(self, count: int, *, exclude_worker: DockerWorker | None = None) -> tuple[int, ...]:
        assert self._available_cpus is not None
        used: set[int] = set()
        for worker in self._workers.values():
            if worker is exclude_worker or worker.deleted:
                continue
            if not set(worker.cpu_ids) <= set(self._available_cpus):
                raise InvalidArgumentError("a recovered worker CPU set is outside the daemon's effective CPUs")
            used.update(worker.cpu_ids)
        for cpus in self._pending_cpus.values():
            used.update(cpus)
        free = tuple(cpu for cpu in self._available_cpus if cpu not in used)
        if len(free) < count:
            raise DockerCapacityError("not enough unallocated daemon CPUs for this worker")
        return free[:count]

    async def _effective_cpu_ids(self, worker: DockerWorker, timeout: float) -> tuple[int, ...]:
        stdout, _stderr, returncode = await self.engine.execute(
            worker.container_id,
            {"Cmd": ["/bin/sh", "-c", _CPUSET_PROBE], "AttachStdout": True,
             "AttachStderr": True, "Tty": False}, timeout,
        )
        lines = [line.partition(':')[2].strip() for line in stdout.decode().splitlines()
                 if line.startswith('Cpus_allowed_list:')]
        if returncode or len(lines) != 1:
            raise InvalidArgumentError("cannot determine the target Docker worker's effective CPU set")
        return _parse_cpu_set(lines[0])

    async def _create_worker(self, profile: str, image_url: str, *, ttl_seconds: float,
                             resources: WorkerResources, ready_timeout_seconds: float,
                             group_name: str | None, labels: dict[str, str] | None) -> DockerWorker:
        self._validate_resources(resources)
        if not image_url.strip() or ttl_seconds <= 0 or ready_timeout_seconds <= 0:
            raise InvalidArgumentError("Docker worker image, TTL and creation budget must be positive")
        deadline = time.monotonic() + ready_timeout_seconds

        def remaining(*, uncapped: bool = False) -> float:
            value = deadline - time.monotonic()
            if value <= 0:
                raise TimeoutError("Docker worker creation exceeded its readiness budget")
            return value if uncapped else min(self.api_timeout_seconds, value)

        reservation = uuid.uuid4().hex
        name = f"tcsexam-{uuid.uuid4().hex}"
        worker = None
        create_attempted = False
        try:
            await self._ensure_recovered(remaining())
            # Queueing does not reserve resources. Only an admitted creation
            # contributes to _pending, so multiple queued requests cannot
            # deadlock by counting one another as allocated workers.
            while True:
                try:
                    async with self._admission_lock:
                        await self._check_capacity(resources, remaining(), reservation)
                        self._pending[reservation] = resources
                        if self._available_cpus is None:
                            self._cpu_discovery_reservation = reservation
                        else:
                            self._pending_cpus[reservation] = self._choose_cpu_ids(resources.cpu_count)
                    break
                except DockerCapacityError as exc:
                    budget = deadline - time.monotonic()
                    if budget <= 0:
                        raise DockerCapacityError("Docker capacity queue exceeded the creation budget") from exc
                    self._capacity_changed.clear()
                    try:
                        await asyncio.wait_for(self._capacity_changed.wait(), min(1.0, budget))
                    except asyncio.TimeoutError:
                        if time.monotonic() >= deadline:
                            raise DockerCapacityError("Docker capacity queue exceeded the creation budget") from exc
            if await self.engine.inspect_image(image_url, remaining()) is None:
                if not self.pull_missing_images:
                    raise InvalidArgumentError("judge image is absent locally and automatic pulling is disabled")
                await self.engine.pull_image(image_url, remaining(uncapped=True))
                if await self.engine.inspect_image(image_url, remaining()) is None:
                    raise InvalidArgumentError("judge image is unavailable after pulling")
            container_labels = {
                "org.tcsexam.managed": "docker-adapter",
                "org.tcsexam.worker": name,
                "org.tcsexam.expires-at": str(time.time() + ttl_seconds),
                "org.tcsexam.profile": str(profile),
                "org.tcsexam.group": group_name or "",
                "org.tcsexam.request-labels": json.dumps(labels or {}, sort_keys=True),
            }
            host_config: dict[str, Any] = {
                "Memory": resources.memory_mb * _MIB,
                "MemorySwap": resources.memory_mb * _MIB,
                "NanoCpus": resources.cpu_count * 1_000_000_000,
                "NetworkMode": self.network,
                "Privileged": False,
            }
            cpu_ids = self._pending_cpus.get(reservation, ())
            if cpu_ids:
                host_config["CpusetCpus"] = _format_cpu_set(cpu_ids)
            if self.host_gateway:
                host_config["ExtraHosts"] = ["host.docker.internal:host-gateway"]
            if resources.storage_mb is not None:
                host_config["StorageOpt"] = {"size": str(resources.storage_mb * _MIB)}
            container_config = {
                "Image": image_url,
                "Entrypoint": ["/bin/sh"],
                "Cmd": ["-c", "sleep infinity"],
                "Labels": container_labels,
                "HostConfig": host_config,
            }
            create_attempted = True
            container_id = await self.engine.create_container(name, container_config, remaining())
            worker = DockerWorker(self, container_id, name, resources, cpu_ids)
            self._workers[container_id] = worker
            self._pending.pop(reservation, None)
            self._pending_cpus.pop(reservation, None)
            self._arm_ttl(worker, ttl_seconds)
            await self.engine.start_container(container_id, remaining())
            if not worker.cpu_ids:
                # Only sleep infinity runs before this assignment; neither
                # the worker nor its control handle has been returned yet.
                effective_cpus = await self._effective_cpu_ids(worker, remaining())
                async with self._admission_lock:
                    self._available_cpus = effective_cpus
                    if resources.cpu_count > len(effective_cpus):
                        raise InvalidArgumentError(
                            "requested worker exceeds Docker daemon effective CPU capacity"
                        )
                    worker.cpu_ids = self._choose_cpu_ids(resources.cpu_count, exclude_worker=worker)
                    await self.engine.update_cpu_set(container_id, worker.cpu_ids, remaining())
                    self._cpu_discovery_reservation = None
                    self._capacity_changed.set()
            inspection = await self.engine.inspect_container(container_id, remaining())
            self._verify_container(inspection, image_url, resources, worker.cpu_ids)
            if await self._effective_cpu_ids(worker, remaining()) != worker.cpu_ids:
                raise InvalidArgumentError("Docker worker effective CPUs differ from its exclusive allocation")
            if not inspection.get("State", {}).get("Running"):
                raise DockerError(500, "Docker worker did not remain running after startup")
            return worker
        except BaseException as exc:
            reconcile = create_attempted and (
                isinstance(exc, (asyncio.CancelledError, TimeoutError, json.JSONDecodeError))
                or (isinstance(exc, DockerError) and not isinstance(exc, DockerNotFoundError))
            )
            cleanup = asyncio.create_task(
                self._cleanup_failed_creation(name, worker, reconcile=reconcile)
            )
            try:
                await asyncio.shield(cleanup)
            except asyncio.CancelledError:
                try:
                    await cleanup
                except Exception:
                    self.LOGGER.warning("failed to clean up Docker worker %s", name)
                raise
            except Exception:
                self.LOGGER.warning("failed to clean up Docker worker %s", name)
            raise
        finally:
            self._pending.pop(reservation, None)
            self._pending_cpus.pop(reservation, None)
            if self._cpu_discovery_reservation == reservation:
                self._cpu_discovery_reservation = None
            self._capacity_changed.set()

    async def _cleanup_failed_creation(self, name: str, worker: DockerWorker | None,
                                       *, reconcile: bool) -> None:
        if worker is None and reconcile:
            worker = await self._reconcile_creation(name)
        if worker is not None:
            await worker.delete()

    async def _reconcile_creation(self, name: str) -> DockerWorker | None:
        deadline = time.monotonic() + 30
        while True:
            try:
                inspection = await self.engine.inspect_container(name, timeout=5)
                recovered = self._worker_from_inspection(inspection)
                if recovered is not None:
                    worker, expires_at = recovered
                    self._workers[worker.container_id] = worker
                    self._arm_ttl(worker, max(0, expires_at - time.time()))
                    return worker
            except DockerNotFoundError:
                pass
            except Exception as exc:
                self.LOGGER.info("Docker creation reconciliation for %s is still unavailable: %s", name, exc)
            if time.monotonic() >= deadline:
                self.LOGGER.warning("could not reconcile Docker creation for container %s", name)
                return None
            await asyncio.sleep(0.1)

    def _verify_container(self, inspection: dict[str, Any], image: str,
                          resources: WorkerResources, cpu_ids: tuple[int, ...]) -> None:
        host_config = inspection.get("HostConfig") or {}
        expected = {
            "Memory": resources.memory_mb * _MIB,
            "MemorySwap": resources.memory_mb * _MIB,
            "NanoCpus": resources.cpu_count * 1_000_000_000,
        }
        for key, value in expected.items():
            if host_config.get(key) != value:
                raise InvalidArgumentError(f"Docker did not retain the requested {key} resource limit")
        if _parse_cpu_set(host_config.get("CpusetCpus") or "") != cpu_ids:
            raise InvalidArgumentError("Docker did not retain the assigned worker CPU set")
        if resources.storage_mb is not None:
            configured = (host_config.get("StorageOpt") or {}).get("size")
            try:
                retained = int(configured)
            except (TypeError, ValueError):
                retained = None
            if retained != resources.storage_mb * _MIB:
                raise InvalidArgumentError(
                    "Docker did not retain the requested storage quota; this adapter never "
                    "silently drops storage_mb. Use a Docker storage driver that supports "
                    "the size option."
                )
        config = inspection.get("Config") or {}
        if config.get("Image") != image:
            raise InvalidArgumentError("Docker did not retain the requested judge image")
        if host_config.get("NetworkMode") != self.network:
            raise InvalidArgumentError("Docker did not retain the requested worker network")
        if host_config.get("Privileged") or host_config.get("Binds"):
            raise InvalidArgumentError("Docker worker unexpectedly has privileged access or host mounts")

    def _arm_ttl(self, worker: DockerWorker, ttl_seconds: float) -> None:
        async def expire() -> None:
            try:
                await asyncio.sleep(ttl_seconds)
                while not worker.deleted:
                    try:
                        await worker.delete()
                    except Exception:
                        self.LOGGER.warning("TTL deletion failed for %s; retrying in 60 seconds", worker.name)
                        await asyncio.sleep(60)
            except asyncio.CancelledError:
                raise
            finally:
                self._ttl_tasks.pop(worker.container_id, None)

        self._ttl_tasks[worker.container_id] = asyncio.create_task(expire())

    def _forget_worker(self, worker: DockerWorker) -> None:
        self._workers.pop(worker.container_id, None)
        self._capacity_changed.set()
        task = self._ttl_tasks.pop(worker.container_id, None)
        if task is not None and task is not asyncio.current_task():
            task.cancel()

    async def close(self) -> None:
        tasks = list(self._ttl_tasks.values())
        self._ttl_tasks.clear()
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


def make_adapter(config: Any) -> DockerAdapter:
    return DockerAdapter(config)
