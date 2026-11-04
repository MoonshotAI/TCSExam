"""Create, verify, and explicitly publish private oracle-answer packages."""
import argparse
from collections import defaultdict
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile

from .resources import digest, relative


SCHEMA_VERSION = 1
CONFIRM_PUBLIC_RELEASE = "PUBLISH_ORACLE_ANSWERS"
CONTROL_FILES = {"manifest.json", "SHA256SUMS", "SOURCE.md", "VALIDATION.json"}
FORBIDDEN_PARTS = {".git", ".hg", ".svn", "logs", "trajectories", "secrets"}
FORBIDDEN_SUFFIXES = (".key", ".pem", ".p12", ".pfx", ".keystore", ".jks",
                      ".enc", ".cipher", ".ciphertext", ".log")


def _canonical(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def _safe_name(value, field):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value):
        raise ValueError(f"Invalid {field}: {value!r}")
    return value


def _answer_path(value):
    name = relative(value)
    parts = PurePosixPath(name).parts
    lowered = name.lower()
    if parts[0] != "answers" or len(parts) < 2 or name in CONTROL_FILES:
        raise ValueError(f"Answer path must be below answers/: {name}")
    if any(part in FORBIDDEN_PARTS for part in parts) or lowered.endswith(FORBIDDEN_SUFFIXES):
        raise ValueError(f"Forbidden oracle-package path: {name}")
    if "ciphertext" in lowered or "trajectory" in lowered:
        raise ValueError(f"Forbidden oracle-package content: {name}")
    return name


def _coverage(rows):
    groups = defaultdict(lambda: [0, 0])
    for row in rows:
        group = groups[(row["task"], row["variant"])]
        group[0] += 1
        group[1] += row["bytes"]
    return [{"task": task, "variant": variant, "files": values[0], "bytes": values[1]}
            for (task, variant), values in sorted(groups.items())]


def _answer_set_digest(rows):
    text = "".join(f"{row['sha256']}  {row['path']}\n" for row in rows).encode()
    return hashlib.sha256(text).hexdigest()


def _load_spec(path):
    path = Path(path)
    raw = json.loads(path.read_text())
    if not isinstance(raw, dict) or raw.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported oracle-package specification")
    if set(raw) != {"schema_version", "package", "files"}:
        raise ValueError("Specification has missing or unknown fields")
    package = raw["package"]
    if not isinstance(package, dict) or set(package) != {"id", "version", "source_scope"}:
        raise ValueError("Package metadata requires id, version and source_scope")
    _safe_name(package.get("id"), "package id")
    _safe_name(package.get("version"), "package version")
    if not isinstance(package["source_scope"], str) or not package["source_scope"].strip():
        raise ValueError("Package source_scope must be nonempty text")
    rows = raw["files"]
    if not isinstance(rows, list) or not rows:
        raise ValueError("Specification must contain answer files")
    result = []
    seen = set()
    for item in rows:
        if not isinstance(item, dict) or set(item) != {
                "source", "path", "task", "variant", "bytes", "sha256", "git_blob", "origin"}:
            raise ValueError("Answer entry has missing or unknown fields")
        name = _answer_path(item["path"])
        if name in seen:
            raise ValueError(f"Duplicate answer path: {name}")
        seen.add(name)
        source = Path(item["source"])
        if not source.is_absolute():
            source = path.parent / source
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"Answer source is not a regular file: {source}")
        task = _safe_name(item["task"], "task")
        variant = _safe_name(item["variant"], "variant")
        size = item["bytes"]
        checksum = item["sha256"]
        git_blob = item["git_blob"]
        if (type(size) is not int or size < 0
                or (checksum is not None and not re.fullmatch(r"[0-9a-f]{64}", checksum or ""))
                or not re.fullmatch(r"[0-9a-f]{40}", git_blob or "")):
            raise ValueError(f"Invalid answer size or content hash: {name}")
        origin = item["origin"]
        if not isinstance(origin, dict) or set(origin) != {"source_id", "commit", "path"}:
            raise ValueError(f"Invalid answer origin: {name}")
        _safe_name(origin["source_id"], "origin source_id")
        if not re.fullmatch(r"[0-9a-f]{40}", origin["commit"] or ""):
            raise ValueError(f"Origin commit must be a full Git commit: {name}")
        origin_path = relative(origin["path"])
        row = {"source": source, "path": name, "task": task, "variant": variant,
               "bytes": size, "sha256": checksum, "git_blob": git_blob,
               "origin": {"source_id": origin["source_id"], "commit": origin["commit"],
                          "path": origin_path}}
        result.append(row)
    result.sort(key=lambda row: row["path"])
    return package, result


def _public_row(row):
    return {key: row[key] for key in ("path", "task", "variant", "bytes", "sha256", "git_blob", "origin")}


class _Reader:
    def __init__(self, stream, size):
        self.stream = stream
        self.checksum = hashlib.sha256()
        self.git_checksum = hashlib.sha1(f"blob {size}\0".encode())

    def read(self, size=-1):
        block = self.stream.read(size)
        self.checksum.update(block)
        self.git_checksum.update(block)
        return block

    def hexdigests(self):
        return self.checksum.hexdigest(), self.git_checksum.hexdigest()


def _verify_source(row):
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(row["source"], flags)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size != row["bytes"]:
            raise ValueError(f"Answer source size or type differs: {row['path']}")
        reader = _Reader(stream, row["bytes"])
        while reader.read(1024 * 1024):
            pass
        sha256, git_blob = reader.hexdigests()
    if git_blob != row["git_blob"]:
        raise ValueError(f"Answer source Git blob differs: {row['path']}")
    if row["sha256"] is not None and sha256 != row["sha256"]:
        raise ValueError(f"Answer source SHA-256 differs: {row['path']}")
    return {**row, "sha256": sha256}


def _tar_info(name, size):
    info = tarfile.TarInfo(name)
    info.size = size
    info.mtime = 0
    info.mode = 0o644
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    return info


def _add_bytes(tar, name, data):
    import io
    tar.addfile(_tar_info(name, len(data)), io.BytesIO(data))


def _add_answer(tar, row):
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(row["source"], flags)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size != row["bytes"]:
            raise ValueError(f"Answer source size or type differs: {row['path']}")
        reader = _Reader(stream, row["bytes"])
        tar.addfile(_tar_info(row["path"], row["bytes"]), reader)
        sha256, git_blob = reader.hexdigests()
        if sha256 != row["sha256"] or git_blob != row["git_blob"]:
            raise ValueError(f"Answer source content changed while packaging: {row['path']}")
        if stream.read(1):
            raise ValueError(f"Answer source grew while packaging: {row['path']}")


def _source_text(package, rows):
    origins = sorted({(row["origin"]["source_id"], row["origin"]["commit"]) for row in rows})
    lines = ["# Oracle answer package", "", f"Package: {package['id']}",
             f"Version: {package['version']}", "", "## Source scope", "",
             package["source_scope"], "", "## Authoritative origins", ""]
    lines.extend(f"- {source_id}: `{commit}`" for source_id, commit in origins)
    lines.extend(["", "Only the answer files listed in manifest.json are included. "
                  "Source checkout paths are packaging inputs and are not runtime dependencies.", ""])
    return "\n".join(lines).encode()


def create_package(specification, output, report_path=None):
    """Create a deterministic archive and fail on any source-content mismatch."""
    package, rows = _load_spec(specification)
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError("Oracle-package output must be a new path")
    rows = [_verify_source(row) for row in rows]
    output.parent.mkdir(parents=True, exist_ok=True)
    public_rows = [_public_row(row) for row in rows]
    answer_set = _answer_set_digest(public_rows)
    coverage = _coverage(public_rows)
    manifest = {"schema_version": SCHEMA_VERSION, "package": package,
                "answer_set_sha256": answer_set, "files": len(public_rows),
                "bytes": sum(row["bytes"] for row in public_rows),
                "coverage": coverage, "answers": public_rows}
    manifest_bytes = _canonical(manifest)
    source_bytes = _source_text(package, public_rows)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{output.name}.tmp-", dir=output.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as zipped:
                with tarfile.open(fileobj=zipped, mode="w|", format=tarfile.PAX_FORMAT) as tar:
                    _add_bytes(tar, "manifest.json", manifest_bytes)
                    _add_bytes(tar, "SOURCE.md", source_bytes)
                    for row in rows:
                        _add_answer(tar, row)
                    validation = {"schema_version": SCHEMA_VERSION,
                                  "source_verification": "passed",
                                  "source_files_git_blob_verified": len(rows),
                                  "source_files_sha256_verified": len(rows),
                                  "source_bytes_verified": sum(row["bytes"] for row in rows),
                                  "answer_set_sha256": answer_set, "coverage": coverage,
                                  "package_sha256": "recorded in the external .sha256 sidecar"}
                    validation_bytes = _canonical(validation)
                    _add_bytes(tar, "VALIDATION.json", validation_bytes)
                    sums = [{"path": row["path"], "sha256": row["sha256"]} for row in public_rows]
                    sums.extend({"path": name, "sha256": hashlib.sha256(data).hexdigest()}
                                for name, data in (("manifest.json", manifest_bytes),
                                                   ("SOURCE.md", source_bytes),
                                                   ("VALIDATION.json", validation_bytes)))
                    sums.sort(key=lambda row: row["path"])
                    _add_bytes(tar, "SHA256SUMS",
                               "".join(f"{row['sha256']}  {row['path']}\n" for row in sums).encode())
            raw.flush()
            os.fsync(raw.fileno())
        if output.exists():
            raise ValueError("Oracle-package output appeared during creation")
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    archive_sha256 = digest(output)
    sidecar = output.with_name(output.name + ".sha256")
    sidecar.write_text(f"{archive_sha256}  {output.name}\n")
    report = {"schema_version": SCHEMA_VERSION, "package": package,
              "archive": output.name, "archive_bytes": output.stat().st_size,
              "archive_sha256": archive_sha256, "answer_set_sha256": answer_set,
              "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
              "answer_files": len(rows), "answer_bytes": sum(row["bytes"] for row in rows),
              "coverage": coverage, "source_verification": "passed"}
    if report_path:
        Path(report_path).write_bytes(_canonical(report))
    return report


def _parse_sums(data):
    rows = {}
    for line in data.decode().splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match:
            raise ValueError("Malformed SHA256SUMS line")
        checksum, name = match.groups()
        name = relative(name)
        if name in rows:
            raise ValueError(f"Duplicate SHA256SUMS entry: {name}")
        rows[name] = checksum
    return rows


def _verify_manifest(manifest, actual):
    if not isinstance(manifest, dict) or manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported package manifest")
    if set(manifest) != {"schema_version", "package", "answer_set_sha256", "files", "bytes",
                         "coverage", "answers"}:
        raise ValueError("Manifest has missing or unknown fields")
    rows = manifest["answers"]
    if not isinstance(rows, list) or not rows:
        raise ValueError("Manifest contains no answers")
    seen = set()
    for row in rows:
        if (not isinstance(row, dict) or set(row) != {
                "path", "task", "variant", "bytes", "sha256", "git_blob", "origin"}
                or not re.fullmatch(r"[0-9a-f]{40}", row.get("git_blob") or "")):
            raise ValueError("Manifest answer has missing, unknown or invalid fields")
        name = _answer_path(row["path"])
        if name in seen or name not in actual:
            raise ValueError(f"Missing or duplicate packaged answer: {name}")
        seen.add(name)
        if actual[name][0] != row["bytes"] or actual[name][1] != row["sha256"]:
            raise ValueError(f"Packaged answer differs from manifest: {name}")
        _safe_name(row["task"], "task")
        _safe_name(row["variant"], "variant")
    if seen != {name for name in actual if name.startswith("answers/")}:
        raise ValueError("Unlisted answer content in package")
    if (manifest["files"] != len(rows) or manifest["bytes"] != sum(row["bytes"] for row in rows)
            or manifest["coverage"] != _coverage(rows)
            or manifest["answer_set_sha256"] != _answer_set_digest(rows)):
        raise ValueError("Manifest totals, coverage or answer-set digest differ")


def verify_package(package, destination, authority_spec=None):
    """Extract into a new directory and verify every member and optional authority."""
    package = Path(package)
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise ValueError("Verification destination must be a new path")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.tmp-", dir=destination.parent))
    published = False
    try:
        with tarfile.open(package, "r|gz") as tar:
            for member in tar:
                name = relative(member.name)
                if not member.isfile() or member.issym() or member.islnk():
                    raise ValueError(f"Oracle package contains a non-regular member: {name}")
                target = staging / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(member) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output, 1024 * 1024)
                target.chmod(0o644)
        actual_files = {path.relative_to(staging).as_posix(): path
                        for path in staging.rglob("*") if path.is_file()}
        if any(path.is_symlink() for path in staging.rglob("*")):
            raise ValueError("Verification destination contains a symbolic link")
        if set(actual_files) != CONTROL_FILES | {name for name in actual_files if name.startswith("answers/")}:
            raise ValueError("Unexpected top-level package content")
        if not CONTROL_FILES.issubset(actual_files):
            raise ValueError("Package control files are incomplete")
        actual = {name: (path.stat().st_size, digest(path)) for name, path in actual_files.items()}
        sums = _parse_sums((staging / "SHA256SUMS").read_bytes())
        if set(sums) != set(actual_files) - {"SHA256SUMS"}:
            raise ValueError("SHA256SUMS does not cover exactly the packaged files")
        for name, checksum in sums.items():
            if actual[name][1] != checksum:
                raise ValueError(f"SHA256SUMS mismatch: {name}")
        manifest = json.loads((staging / "manifest.json").read_text())
        _verify_manifest(manifest, actual)
        validation = json.loads((staging / "VALIDATION.json").read_text())
        expected_validation = {"source_verification": "passed",
                               "source_files_git_blob_verified": manifest["files"],
                               "source_files_sha256_verified": manifest["files"],
                               "source_bytes_verified": manifest["bytes"],
                               "answer_set_sha256": manifest["answer_set_sha256"],
                               "coverage": manifest["coverage"]}
        if any(validation.get(key) != value for key, value in expected_validation.items()):
            raise ValueError("Packaging validation record differs from manifest")
        authority = None
        if authority_spec:
            _, source_rows = _load_spec(authority_spec)
            source_rows = [_verify_source(row) for row in source_rows]
            expected = {row["path"]: row for row in source_rows}
            if set(expected) != {row["path"] for row in manifest["answers"]}:
                raise ValueError("Authority specification coverage differs from package")
            for row in manifest["answers"]:
                source = expected[row["path"]]
                if _public_row(source) != row:
                    raise ValueError(f"Authority metadata or content differs: {row['path']}")
            authority = {"files_git_blob_verified": len(source_rows),
                         "files_sha256_verified": len(source_rows),
                         "bytes_verified": sum(row["bytes"] for row in source_rows)}
        os.replace(staging, destination)
        published = True
    finally:
        if not published:
            shutil.rmtree(staging, ignore_errors=True)
    return {"schema_version": SCHEMA_VERSION, "package": manifest["package"],
            "archive_sha256": digest(package), "answer_set_sha256": manifest["answer_set_sha256"],
            "answer_files": manifest["files"], "answer_bytes": manifest["bytes"],
            "coverage": manifest["coverage"], "package_verification": "passed",
            "authority_verification": authority}


def publish_package(package, destination, confirmation, builder="remote", execute=None):
    """Push an OCI data image only after explicit release confirmation and verification."""
    if confirmation != CONFIRM_PUBLIC_RELEASE:
        raise ValueError("Refuse public release: dedicated confirmation is required")
    if not isinstance(destination, str) or not re.fullmatch(
            r"[A-Za-z0-9.-]+(?::[0-9]+)?/[A-Za-z0-9._/-]+:[A-Za-z0-9._-]+", destination or ""):
        raise ValueError("Refuse public release: an explicit registry repository and tag are required")
    if destination.rsplit(":", 1)[1] == "latest" or "@" in destination or "://" in destination:
        raise ValueError("Refuse public release: use an immutable version tag, not latest or a digest")
    package = Path(package)
    with tempfile.TemporaryDirectory(prefix="tcsexam-oracle-publish-") as temporary:
        temporary = Path(temporary)
        verification = verify_package(package, temporary / "verified")
        shutil.copyfile(package, temporary / "package.tar.gz")
        (temporary / "Dockerfile").write_text(
            "FROM scratch\nCOPY package.tar.gz /oracle/answers.tar.gz\n"
            "COPY PACKAGE-SHA256 /oracle/PACKAGE-SHA256\n")
        (temporary / "PACKAGE-SHA256").write_text(verification["archive_sha256"] + "\n")
        metadata = temporary / "metadata.json"
        command = ["docker", "buildx", "build", "--builder", builder, "--push",
                   "--metadata-file", str(metadata), "-t", destination, str(temporary)]
        (execute or subprocess.run)(command, check=True)
        result = {"destination": destination, "archive_sha256": verification["archive_sha256"],
                  "answer_set_sha256": verification["answer_set_sha256"],
                  "public_release": "pushed", "buildx_metadata": json.loads(metadata.read_text())
                  if metadata.is_file() else None}
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create", help="Create a private package without uploading it")
    create.add_argument("--spec", required=True)
    create.add_argument("--output", required=True)
    create.add_argument("--report")
    verify = commands.add_parser("verify", help="Verify and unpack without uploading")
    verify.add_argument("--package", required=True)
    verify.add_argument("--destination", required=True)
    verify.add_argument("--authority-spec")
    publish = commands.add_parser("publish", help="Explicitly publish a verified OCI data image")
    publish.add_argument("--package", required=True)
    publish.add_argument("--destination", required=True,
                         help="Explicit <registry>/<repository>:<version-tag> target")
    publish.add_argument("--confirm-public-release", required=True,
                         help=f"Must be exactly {CONFIRM_PUBLIC_RELEASE}")
    publish.add_argument("--builder", default="remote")
    args = parser.parse_args(argv)
    try:
        if args.command == "create":
            result = create_package(args.spec, args.output, args.report)
        elif args.command == "verify":
            result = verify_package(args.package, args.destination, args.authority_spec)
        else:
            result = publish_package(args.package, args.destination,
                                     args.confirm_public_release, args.builder)
    except (OSError, ValueError, tarfile.TarError, json.JSONDecodeError) as error:
        parser.exit(2, f"error: {error}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
