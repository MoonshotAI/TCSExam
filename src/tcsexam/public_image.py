"""Build and verify single-layer public judge images with a streaming tar filter."""
import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import posixpath
import re
import subprocess
import tarfile
import tempfile
from typing import BinaryIO


CHUNK_SIZE = 1024 * 1024
FORBIDDEN_SUFFIXES = (".key", ".enc")
FORBIDDEN_HIDDEN_PATHS = ("/tests/anchors.json", "/tests/reference-hidden.json", "/tests/solution")
FORBIDDEN_REFERENCE_BACKUP_PREFIX = "/tests/reference.json.bak"
NEUTRAL_LABELS = {
    "org.tcsexam.image-role": "public-judge",
    "org.tcsexam.public-image-schema": "1",
}
SENSITIVE_ENV_NAME = re.compile(r"KEY|TOKEN|SECRET|PASSWORD", re.IGNORECASE)


class PublicImageError(RuntimeError):
    """A public image cannot be built or verified safely."""


class DockerCommandError(PublicImageError):
    def __init__(self, operation: str, returncode: int):
        super().__init__(f"{operation} failed with exit code {returncode}; command output suppressed")


@dataclass(frozen=True)
class PayloadAllowlist:
    root: str
    files: tuple[str, ...]
    regular_file_count: int


@dataclass(frozen=True)
class PublicImageManifest:
    schema_version: int
    task: str
    remove_paths: tuple[str, ...]
    allow_content_paths: tuple[str, ...]
    required_paths: tuple[str, ...]
    distribution: str | None = None
    public_upload_allowed: bool = False
    payload_allowlist: tuple[PayloadAllowlist, ...] = ()

    @classmethod
    def from_dict(cls, raw: dict) -> "PublicImageManifest":
        if not isinstance(raw, dict):
            raise PublicImageError("Public image manifest must be a JSON object")
        required = {"schema_version", "task", "remove_paths", "allow_content_paths", "required_paths"}
        optional = {"distribution", "public_upload_allowed", "payload_allowlist"}
        unknown = set(raw) - required - optional
        missing = required - set(raw)
        if unknown or missing:
            raise PublicImageError(
                f"Manifest fields mismatch; missing={sorted(missing)}, unknown={sorted(unknown)}"
            )
        if type(raw["schema_version"]) is not int or raw["schema_version"] != 1:
            raise PublicImageError("Public image manifest schema_version must be 1")
        if not isinstance(raw["task"], str) or not raw["task"].strip():
            raise PublicImageError("Public image manifest task must be a non-empty string")
        if raw.get("distribution") not in (None, "redistributable", "local_prepare", "private_only", "unresolved"):
            raise PublicImageError("Unknown distribution rule")
        if type(raw.get("public_upload_allowed", False)) is not bool:
            raise PublicImageError("public_upload_allowed must be a boolean")
        paths = {
            name: _manifest_path_list(raw[name], name)
            for name in ("remove_paths", "allow_content_paths", "required_paths")
        }
        manifest = cls(
            1, raw["task"], paths["remove_paths"], paths["allow_content_paths"],
            paths["required_paths"], raw.get("distribution"),
            raw.get("public_upload_allowed", False),
            _payload_allowlist(raw.get("payload_allowlist", [])),
        )
        impossible = [path for path in manifest.required_paths
                      if any(_within(path, root) for root in manifest.remove_paths)]
        if impossible:
            raise PublicImageError(f"Required paths are inside remove_paths: {impossible}")
        for rule in manifest.payload_allowlist:
            overlap = [root for root in manifest.remove_paths
                       if _within(root, rule.root) or _within(rule.root, root)]
            if overlap:
                raise PublicImageError(
                    f"Payload allowlist root {rule.root} overlaps remove_paths: {overlap}"
                )
        missing_removals = [
            path for path in FORBIDDEN_HIDDEN_PATHS
            if not any(_within(path, root) for root in manifest.remove_paths)
        ]
        if missing_removals:
            raise PublicImageError(
                f"Manifest must remove known hidden reference/oracle paths: {missing_removals}"
            )
        return manifest


@dataclass
class FilterResult:
    removed_hashes: set[str]
    allowed_hashes: set[str]
    removed_regular_files: int
    allowed_regular_files: int
    retained_regular_files: int


class DockerClient:
    """Small Docker CLI adapter; command arguments are never passed through a shell."""

    def __init__(self, executable: str = "docker", context: str | None = None):
        self.executable = executable
        self.context = context
        self.command = [executable, *(["--context", context] if context else [])]

    def _run(self, operation: str, arguments: list[str], *, stdin=None) -> bytes:
        completed = subprocess.run(
            [*self.command, *arguments],
            stdin=stdin,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if completed.returncode:
            raise DockerCommandError(operation, completed.returncode)
        return completed.stdout

    def pull(self, image: str) -> None:
        self._run("docker pull", ["pull", image])

    def inspect(self, image: str) -> dict:
        output = self._run("docker image inspect", ["image", "inspect", image])
        try:
            parsed = json.loads(output)
            if not isinstance(parsed, list) or len(parsed) != 1 or not isinstance(parsed[0], dict):
                raise ValueError
            return parsed[0]
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise PublicImageError("docker image inspect returned an invalid response") from exc

    def create(self, image: str) -> str:
        output = self._run("docker create", ["create", image])
        try:
            container = output.decode("ascii").strip()
        except UnicodeDecodeError as exc:
            raise PublicImageError("docker create returned an invalid container id") from exc
        if not re.fullmatch(r"[0-9a-fA-F]{12,64}", container):
            raise PublicImageError("docker create returned an invalid container id")
        return container

    def remove(self, container: str) -> None:
        self._run("docker rm", ["rm", container])

    @contextmanager
    def export(self, container: str):
        """Yield an export stream and check the exporter status without buffering stderr."""
        with tempfile.TemporaryFile() as errors:
            process = subprocess.Popen(
                [*self.command, "export", container],
                stdout=subprocess.PIPE,
                stderr=errors,
            )
            if process.stdout is None:
                process.kill()
                process.wait()
                raise PublicImageError("docker export did not provide an output stream")
            try:
                yield process.stdout
                process.stdout.close()
                returncode = process.wait()
                if returncode:
                    raise DockerCommandError("docker export", returncode)
            except BaseException:
                process.stdout.close()
                if process.poll() is None:
                    process.kill()
                process.wait()
                raise

    def import_tar(self, stream: BinaryIO, changes: list[str], output_image: str) -> None:
        arguments = ["import"]
        for change in changes:
            arguments.extend(["--change", change])
        arguments.extend(["-", output_image])
        self._run("docker import", arguments, stdin=stream)

    def push(self, image: str) -> None:
        self._run("docker push", ["push", image])


def _manifest_path(value, field: str) -> str:
    if not isinstance(value, str) or not value.startswith("/") or value == "/" or "\0" in value:
        raise PublicImageError(f"{field} entries must be absolute non-root paths")
    parts = value.split("/")[1:]
    if any(part in ("", ".", "..") for part in parts):
        raise PublicImageError(f"{field} contains a non-canonical or parent-relative path: {value!r}")
    return "/" + "/".join(parts)


def _manifest_path_list(value, field: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise PublicImageError(f"{field} must be a JSON array")
    return tuple(dict.fromkeys(_manifest_path(item, field) for item in value))


def _payload_allowlist(value) -> tuple[PayloadAllowlist, ...]:
    if not isinstance(value, list):
        raise PublicImageError("payload_allowlist must be a JSON array")
    rules = []
    for index, item in enumerate(value):
        field = f"payload_allowlist[{index}]"
        if not isinstance(item, dict) or set(item) != {"root", "files", "regular_file_count"}:
            raise PublicImageError(
                f"{field} must contain exactly root, files and regular_file_count"
            )
        root = _manifest_path(item["root"], field + ".root")
        if not isinstance(item["files"], list):
            raise PublicImageError(f"{field}.files must be a JSON array")
        files = tuple(_manifest_path(path, field + ".files") for path in item["files"])
        if len(set(files)) != len(files):
            raise PublicImageError(f"{field}.files contains duplicate paths")
        outside = [path for path in files if not _within(path, root) or path == root]
        if outside:
            raise PublicImageError(f"{field}.files contains paths outside its root: {outside}")
        count = item["regular_file_count"]
        if type(count) is not int or count < 0 or count != len(files):
            raise PublicImageError(
                f"{field}.regular_file_count must equal the exact number of listed files"
            )
        if any(_within(root, other.root) or _within(other.root, root) for other in rules):
            raise PublicImageError(f"Payload allowlist roots must not overlap: {root}")
        rules.append(PayloadAllowlist(root, files, count))
    return tuple(rules)


def load_manifest(path: str | os.PathLike) -> PublicImageManifest:
    try:
        raw = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise PublicImageError(f"Cannot load public image manifest: {path}") from exc
    return PublicImageManifest.from_dict(raw)


def _within(path: str, root: str) -> bool:
    return path == root or path.startswith(root + "/")


def _under_any(path: str, roots: tuple[str, ...]) -> bool:
    return any(_within(path, root) for root in roots)


def _tar_name(name: str) -> str | None:
    if not isinstance(name, str) or not name or "\0" in name or name.startswith("/"):
        raise PublicImageError(f"Unsafe tar entry name: {name!r}")
    normalized = name
    while normalized.startswith("./"):
        normalized = normalized[2:]
    trailing = normalized.endswith("/")
    if trailing:
        normalized = normalized.rstrip("/")
    if not normalized:
        return None
    parts = normalized.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise PublicImageError(f"Unsafe tar entry name: {name!r}")
    if trailing and not parts:
        return None
    return "/".join(parts)


def _absolute(path: str) -> str:
    return "/" + path


def _link_target(member: tarfile.TarInfo, name: str) -> str:
    link = member.linkname
    if not isinstance(link, str) or not link or "\0" in link:
        raise PublicImageError(f"Invalid link target at /{name}")
    if member.issym():
        base = "/" if link.startswith("/") else "/" + posixpath.dirname(name)
        return posixpath.normpath(posixpath.join(base, link))
    if link.startswith("/"):
        target = _manifest_path(posixpath.normpath(link), "hard-link target")
        return target
    target_name = _tar_name(link)
    if target_name is None:
        raise PublicImageError(f"Invalid hard-link target at /{name}")
    return _absolute(target_name)


def _check_link(member: tarfile.TarInfo, name: str,
                manifest: PublicImageManifest) -> str | None:
    if not (member.issym() or member.islnk()):
        return None
    target = _link_target(member, name)
    if _under_any(target, manifest.remove_paths):
        raise PublicImageError(f"Link /{name} points into removed hidden path {target}")
    return target


def _check_forbidden_name(name: str) -> None:
    if name.lower().endswith(FORBIDDEN_SUFFIXES):
        raise PublicImageError(f"Forbidden key or encrypted file in public image: /{name}")
    path = _absolute(name)
    if (any(_within(path, root) for root in FORBIDDEN_HIDDEN_PATHS)
            or path.startswith(FORBIDDEN_REFERENCE_BACKUP_PREFIX)):
        raise PublicImageError(f"Forbidden hidden reference or oracle content in public image: {path}")


def _digest_stream(stream: BinaryIO) -> str:
    digest = hashlib.sha256()
    while chunk := stream.read(CHUNK_SIZE):
        digest.update(chunk)
    return digest.hexdigest()


class _HashingReader:
    def __init__(self, stream: BinaryIO):
        self.stream = stream
        self.digest = hashlib.sha256()

    def read(self, size: int) -> bytes:
        chunk = self.stream.read(size)
        self.digest.update(chunk)
        return chunk

    def hexdigest(self) -> str:
        return self.digest.hexdigest()


def _prepare_member(member: tarfile.TarInfo, name: str,
                    hardlink_target: str | None) -> tarfile.TarInfo:
    member.name = name
    if member.islnk() and hardlink_target is not None:
        member.linkname = hardlink_target.lstrip("/")
    member.pax_headers = {
        key: value for key, value in member.pax_headers.items()
        if key not in ("path", "linkpath")
    }
    return member


def _payload_rule(path: str, manifest: PublicImageManifest) -> PayloadAllowlist | None:
    for rule in manifest.payload_allowlist:
        if _within(path, rule.root):
            return rule
    return None


def _check_payload_member(path: str, member: tarfile.TarInfo,
                          rule: PayloadAllowlist | None, seen: set[str]) -> None:
    if rule is None or member.isdir():
        return
    if not member.isfile() or path not in rule.files:
        raise PublicImageError(f"Public payload entry is not a listed regular file: {path}")
    if path in seen:
        raise PublicImageError(f"Public payload regular file appears more than once: {path}")
    seen.add(path)


def _verify_payload_allowlist(manifest: PublicImageManifest, seen: set[str], phase: str) -> None:
    for rule in manifest.payload_allowlist:
        actual = {path for path in seen if _within(path, rule.root)}
        missing = sorted(set(rule.files) - actual)
        if missing:
            raise PublicImageError(
                f"Public payload files missing {phase} under {rule.root}: {missing}"
            )
        if len(actual) != rule.regular_file_count:
            raise PublicImageError(
                f"Public payload file count mismatch {phase} under {rule.root}: "
                f"expected {rule.regular_file_count}, found {len(actual)}"
            )


def filter_tar(source: BinaryIO, destination: BinaryIO,
               manifest: PublicImageManifest) -> FilterResult:
    """Filter one exported rootfs while hashing removed and explicitly public files."""
    removed_hashes, allowed_hashes = set(), set()
    removed_files = allowed_files = retained_files = 0
    seen = set()
    payload_seen = set()
    with tarfile.open(fileobj=source, mode="r|*") as incoming, \
            tarfile.open(fileobj=destination, mode="w|") as outgoing:
        for member in incoming:
            name = _tar_name(member.name)
            if name is None:
                if member.isdir():
                    continue
                raise PublicImageError(f"Unsafe non-directory root tar entry: {member.name!r}")
            path = _absolute(name)
            removed = _under_any(path, manifest.remove_paths)
            allowed = _under_any(path, manifest.allow_content_paths)
            if member.isfile():
                extracted = incoming.extractfile(member)
                if extracted is None:
                    raise PublicImageError(f"Cannot read regular file /{path}")
                if removed:
                    digest = _digest_stream(extracted)
                    removed_hashes.add(digest)
                    removed_files += 1
                    if allowed:
                        allowed_hashes.add(digest)
                        allowed_files += 1
                    continue
                _check_payload_member(path, member, _payload_rule(path, manifest), payload_seen)
                _check_forbidden_name(name)
                seen.add(path)
                retained_files += 1
                if allowed:
                    reader = _HashingReader(extracted)
                    outgoing.addfile(_prepare_member(member, name, None), reader)
                    allowed_hashes.add(reader.hexdigest())
                    allowed_files += 1
                else:
                    outgoing.addfile(_prepare_member(member, name, None), extracted)
                continue
            if removed:
                continue
            _check_payload_member(path, member, _payload_rule(path, manifest), payload_seen)
            _check_forbidden_name(name)
            target = _check_link(member, name, manifest)
            seen.add(path)
            outgoing.addfile(_prepare_member(member, name, target))
    _verify_payload_allowlist(manifest, payload_seen, "after filtering")
    missing = sorted(set(manifest.required_paths) - seen)
    if missing:
        raise PublicImageError(f"Required paths missing after filtering: {missing}")
    return FilterResult(removed_hashes, allowed_hashes, removed_files,
                        allowed_files, retained_files)


def verify_public_tar(source: BinaryIO, manifest: PublicImageManifest,
                      hidden_only_hashes: set[str]) -> int:
    """Re-scan an imported rootfs and reject hidden content at any retained path."""
    seen = set()
    payload_seen = set()
    regular_files = 0
    with tarfile.open(fileobj=source, mode="r|*") as archive:
        for member in archive:
            name = _tar_name(member.name)
            if name is None:
                if member.isdir():
                    continue
                raise PublicImageError(f"Unsafe non-directory root tar entry: {member.name!r}")
            path = _absolute(name)
            if _under_any(path, manifest.remove_paths):
                raise PublicImageError(f"Removed hidden path remains in public image: {path}")
            _check_payload_member(path, member, _payload_rule(path, manifest), payload_seen)
            _check_forbidden_name(name)
            _check_link(member, name, manifest)
            seen.add(path)
            if member.isfile():
                extracted = archive.extractfile(member)
                if extracted is None:
                    raise PublicImageError(f"Cannot read regular file {path}")
                digest = _digest_stream(extracted)
                regular_files += 1
                if digest in hidden_only_hashes:
                    raise PublicImageError(
                        f"Hidden content copied to {path}: sha256={digest}"
                    )
    _verify_payload_allowlist(manifest, payload_seen, "in imported image")
    missing = sorted(set(manifest.required_paths) - seen)
    if missing:
        raise PublicImageError(f"Required paths missing in imported image: {missing}")
    return regular_files


def _public_config(inspection: dict) -> tuple[dict, list[str]]:
    source = inspection.get("Config")
    if not isinstance(source, dict):
        raise PublicImageError("Source image inspection has no OCI Config object")
    environment = source.get("Env") or []
    if not isinstance(environment, list):
        raise PublicImageError("Source image Config.Env must be an array")
    public_environment, dropped = [], []
    for index, entry in enumerate(environment):
        if not isinstance(entry, str):
            raise PublicImageError(f"Source image Config.Env entry {index} is not a string")
        name, separator, _ = entry.partition("=")
        if not separator or not name:
            raise PublicImageError(f"Source image Config.Env entry {index} is malformed")
        if SENSITIVE_ENV_NAME.search(name):
            dropped.append(name)
            continue
        if name != "INSTANCE_SET":
            public_environment.append(entry)
    public_environment.append("INSTANCE_SET=public")
    result = {"Env": public_environment, "Labels": dict(NEUTRAL_LABELS)}
    for key in ("Entrypoint", "Cmd", "WorkingDir", "User", "StopSignal"):
        value = source.get(key)
        if value is not None and value != "":
            result[key] = value
    for key in ("ExposedPorts", "Volumes"):
        value = source.get(key)
        if value:
            if not isinstance(value, dict) or any(not isinstance(port, str) or not port for port in value):
                raise PublicImageError(f"Source image Config.{key} must be a path/port mapping")
            result[key] = {port: {} for port in sorted(value)}
    return result, sorted(set(dropped))


def _command_instruction(name: str, value) -> str:
    if isinstance(value, str):
        return f"{name} {value}"
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return f"{name} {json.dumps(value, ensure_ascii=False, separators=(',', ':'))}"
    raise PublicImageError(f"Source image Config.{name} must be a string or string array")


def _environment_instruction(entry: str) -> str:
    name, separator, value = entry.partition("=")
    if not separator or not name:
        raise PublicImageError("Environment entries must have the form name=value")
    return f"ENV {name}={json.dumps(value, ensure_ascii=False)}"


def _config_changes(config: dict) -> list[str]:
    changes = []
    for key, instruction in (("Entrypoint", "ENTRYPOINT"), ("Cmd", "CMD")):
        if key in config:
            changes.append(_command_instruction(instruction, config[key]))
    changes.extend(_environment_instruction(entry) for entry in config["Env"])
    for key, instruction in (("WorkingDir", "WORKDIR"), ("User", "USER"),
                             ("StopSignal", "STOPSIGNAL")):
        if key in config:
            if not isinstance(config[key], str):
                raise PublicImageError(f"Source image Config.{key} must be a string")
            changes.append(f"{instruction} {config[key]}")
    if "ExposedPorts" in config:
        changes.extend(f"EXPOSE {port}" for port in config["ExposedPorts"])
    if "Volumes" in config:
        changes.append("VOLUME " + json.dumps(list(config["Volumes"]), separators=(",", ":")))
    changes.extend(f"LABEL {name}={value}" for name, value in config["Labels"].items())
    return changes


def _verify_imported_config(inspection: dict, expected: dict) -> None:
    actual = inspection.get("Config")
    if not isinstance(actual, dict):
        raise PublicImageError("Imported image inspection has no OCI Config object")
    for key, expected_value in expected.items():
        if actual.get(key) != expected_value:
            raise PublicImageError(f"Imported image Config.{key} does not match; values suppressed")


def _verify_single_layer(inspection: dict) -> None:
    rootfs = inspection.get("RootFS")
    layers = rootfs.get("Layers") if isinstance(rootfs, dict) else None
    if not isinstance(layers, list) or len(layers) != 1:
        count = len(layers) if isinstance(layers, list) else "unknown"
        raise PublicImageError(f"Imported image must have exactly one RootFS layer; found {count}")


def _cleanup_created(docker, containers: list[str], primary_error=None) -> None:
    failures = []
    for container in reversed(containers[:]):
        try:
            docker.remove(container)
        except Exception as exc:
            failures.append((container, exc))
        else:
            containers.remove(container)
    if not failures:
        return
    message = "Failed to remove created containers: " + ", ".join(item[0] for item in failures)
    if primary_error is not None:
        primary_error.add_note(message)
        return
    raise PublicImageError(message) from failures[0][1]


def build_public_image(source_image: str, output_image: str,
                       manifest: PublicImageManifest, *, pull: bool = False,
                       push: bool = False, private_registry: bool = False, docker=None) -> dict:
    """Build and verify a public-only image, then optionally push to an authorized registry."""
    if not source_image or not output_image:
        raise PublicImageError("Source and output image references must be non-empty")
    if push:
        if manifest.distribution not in ('redistributable', 'local_prepare', 'private_only'):
            raise PublicImageError("Registry upload has no accepted distribution decision")
        if not private_registry and (manifest.distribution != 'redistributable'
                                     or manifest.public_upload_allowed is not True):
            raise PublicImageError("Public registry upload is not authorized by the manifest")
    docker = docker or DockerClient()
    containers = []
    primary_error = None
    try:
        if pull:
            docker.pull(source_image)
        source_inspection = docker.inspect(source_image)
        public_config, dropped_names = _public_config(source_inspection)
        changes = _config_changes(public_config)
        source_container = docker.create(source_image)
        containers.append(source_container)
        with tempfile.TemporaryFile() as filtered:
            with docker.export(source_container) as stream:
                result = filter_tar(stream, filtered, manifest)
            filtered.flush()
            filtered.seek(0)
            docker.import_tar(filtered, changes, output_image)
        imported_inspection = docker.inspect(output_image)
        _verify_single_layer(imported_inspection)
        _verify_imported_config(imported_inspection, public_config)
        hidden_only_hashes = result.removed_hashes - result.allowed_hashes
        verification_container = docker.create(output_image)
        containers.append(verification_container)
        with docker.export(verification_container) as stream:
            verified_files = verify_public_tar(stream, manifest, hidden_only_hashes)
        _cleanup_created(docker, containers)
        if push:
            docker.push(output_image)
        return {
            "task": manifest.task,
            "removed_regular_files": result.removed_regular_files,
            "allowed_regular_files": result.allowed_regular_files,
            "retained_regular_files": result.retained_regular_files,
            "verified_regular_files": verified_files,
            "removed_content_hashes": len(result.removed_hashes),
            "allowed_content_hashes": len(result.allowed_hashes),
            "hidden_only_hashes": len(hidden_only_hashes),
            "payload_allowlist_files": {
                rule.root: rule.regular_file_count for rule in manifest.payload_allowlist
            },
            "payload_allowlist_total_files": sum(
                rule.regular_file_count for rule in manifest.payload_allowlist
            ),
            "rootfs_layers": 1,
            "dropped_environment_names": dropped_names,
            "pushed": push,
        }
    except BaseException as exc:
        primary_error = exc
        raise
    finally:
        _cleanup_created(docker, containers, primary_error)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-image", required=True)
    parser.add_argument("--output-image", required=True)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--pull", action="store_true", help="Pull the source image before inspecting it")
    parser.add_argument("--push", action="store_true", help="Push only after every local verification passes")
    parser.add_argument("--private-registry", action="store_true",
                        help="Explicitly authorize an internal private registry instead of public distribution")
    args = parser.parse_args(argv)
    try:
        report = build_public_image(
            args.source_image,
            args.output_image,
            load_manifest(args.manifest),
            pull=args.pull,
            push=args.push,
            private_registry=args.private_registry,
        )
    except (PublicImageError, OSError, tarfile.TarError) as exc:
        parser.exit(1, f"public image build failed: {exc}\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
