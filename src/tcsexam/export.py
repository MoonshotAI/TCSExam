"""Export a constrained source tree without publishing images or Git history."""
from collections import Counter
import hashlib
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile

from .checks import validate
from .layout import load
from .oracle_answers import is_oracle_answer_path


DECISIONS_PATH = "docs/licenses/third-party/distribution-decisions.json"
FILES_PATH = "assets/files.json"
CACHE_DIRECTORIES = {
    ".cache", ".mypy_cache", ".nox", ".pytest_cache", ".ruff_cache", ".tox",
    ".venv", "__pycache__", "node_modules",
}
VCS_DIRECTORIES = {".git", ".hg", ".svn"}
ENVIRONMENT_TEMPLATES = {".env.example", ".env.sample", ".env.template"}
SENSITIVE_NAMES = {
    ".dockercfg", ".git-credentials", ".htpasswd", ".netrc", ".npmrc", ".pypirc",
    "credentials", "credentials.json", "id_dsa", "id_ecdsa", "id_ed25519", "id_rsa",
    "secrets.json", "secrets.yaml", "secrets.yml",
}
SENSITIVE_DIRECTORIES = {".aws", ".docker", ".gnupg", ".ssh"}
SENSITIVE_SUFFIXES = (".bak", ".jks", ".kdbx", ".key", ".keystore", ".p12", ".pem", ".pfx")

# These exact archives are reacquired and verified by `source-inputs`. A
# maintainer's prepared context must not silently turn into a source archive.
REPREPARABLE_SOURCE_ARCHIVES = {
    'assets/environments/lean-base/graphviz-epl/source/graphviz-15.0.0.tar.gz',
    'assets/environments/lean-base/graphviz-epl/source/hpcc-js-wasm-8b86e2f83cc7344aca44fb3d8aa29a227358c5c4.tar.gz',
}
PRIVATE_REVIEW_FILES = {'docs/integration-status.md'}

# Vendored license records may preserve nested npm package identities. These
# directories hold notices, not installed dependencies. Keep only exact records.
LICENSE_RECORD_ROOT = 'assets/environments/lean-base/proofwidgets-npm'


def _license_records(root):
    directory = root / LICENSE_RECORD_ROOT
    index = directory / 'SHA256SUMS'
    if not index.is_file():
        return set(), set()
    files, folders = set(), set()
    for line in index.read_text().splitlines():
        if not line.strip():
            continue
        digest, name = line.split('  ', 1)
        name = _relative(name)
        path = directory / name
        if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f'License record checksum mismatch: {LICENSE_RECORD_ROOT}/{name}')
        relative = f'{LICENSE_RECORD_ROOT}/{name}'
        files.add(relative)
        folders.update(str(p) for p in PurePosixPath(relative).parents)
    return files, folders


def _relative(value):
    if not isinstance(value, str):
        raise ValueError("Manifest path must be a string")
    path = PurePosixPath(value)
    if (not value or str(path) in {"", "."} or path.is_absolute() or ".." in path.parts
            or "\\" in value or "\x00" in value):
        raise ValueError(f"Unsafe manifest path: {value!r}")
    return str(path)


def _declared_skips(root):
    rows = load(root / FILES_PATH).get("files")
    if not isinstance(rows, list):
        raise ValueError(f"{FILES_PATH} must contain a files list")
    skips = {}
    omitted = Counter()
    unresolved = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"{FILES_PATH} entries must be objects")
        path = _relative(row.get("path"))
        if path in seen:
            raise ValueError(f"Duplicate distribution decision: {path}")
        seen.add(path)
        distribution = row.get("distribution", "unresolved")
        if distribution == "unresolved":
            if row.get("status") == "source_omitted":
                # An external input can remain unready while its recipe is shared.
                # Always exclude the bytes, even if a maintainer restored a copy.
                skips[path] = "unresolved_external_input"
                omitted["unresolved_external_input"] += 1
            else:
                unresolved.append(path)
        elif distribution == "private_only":
            skips[path] = "private_only"
            omitted["private_only"] += 1
        elif distribution == "local_prepare":
            if row.get("status") != "source_omitted":
                raise ValueError(f"local_prepare record is not source_omitted: {path}")
            skips[path] = "local_prepare_source_omitted"
            omitted["local_prepare_source_omitted"] += 1
        elif distribution != "redistributable":
            raise ValueError(f"Unknown distribution decision for {path}: {distribution!r}")
    if unresolved:
        shown = ", ".join(unresolved[:5])
        more = f" and {len(unresolved) - 5} more" if len(unresolved) > 5 else ""
        raise ValueError(
            f"Refuse source export: {len(unresolved)} distribution=unresolved records: {shown}{more}")
    return skips, dict(sorted(omitted.items()))


def _output_path(root, output):
    supplied = Path(output).expanduser()
    if supplied.is_symlink():
        raise ValueError("Output directory cannot be a symbolic link")
    target = supplied.resolve(strict=False)
    if root.is_relative_to(target):
        raise ValueError("Output directory cannot contain the source checkout")
    if target.is_relative_to(root / "tasks"):
        raise ValueError("Output directory cannot be inside the source task tree")
    build = root / "build"
    if target.is_relative_to(root) and (target == build or not target.is_relative_to(build)):
        raise ValueError("Output directory inside the source checkout must be below build/")
    if target.exists():
        if not target.is_dir():
            raise ValueError(f"Output path is not a directory: {target}")
        if any(target.iterdir()):
            raise ValueError(f"Output directory must be new or empty: {target}")
    return target


def _exclusion_reason(relative, directory):
    parts = PurePosixPath(relative).parts
    name = parts[-1]
    lowered = name.lower()
    if not directory and relative in REPREPARABLE_SOURCE_ARCHIVES:
        return 'repreparable_source_archive'
    if not directory and relative in PRIVATE_REVIEW_FILES:
        return 'private_review_document'
    if not directory and is_oracle_answer_path(relative):
        return "oracle_answers_private"
    if name in VCS_DIRECTORIES:
        return "version_control_metadata"
    if len(parts) == 1 and name in {"build", "dist", "jobs"}:
        return "local_jobs_or_build_output"
    # Website tooling belongs to gh-pages, including leftovers in older checkouts.
    if relative == "site-docs":
        return "website_source"
    if name in CACHE_DIRECTORIES or lowered.endswith(".egg-info"):
        return "cache_or_dependency_output"
    if not directory and (lowered.endswith((".pyc", ".pyo", ".swp", ".swo")) or name.endswith("~")
                          or lowered in {".coverage", ".ds_store", "thumbs.db"}):
        return "cache_or_editor_output"
    return None


def _sensitive_reason(relative):
    name = PurePosixPath(relative).name
    lowered = name.lower()
    if name in SENSITIVE_DIRECTORIES:
        return "credential_directory"
    if lowered == ".env" or (lowered.startswith(".env.") and lowered not in ENVIRONMENT_TEMPLATES):
        return "environment_file"
    if lowered in SENSITIVE_NAMES or lowered.endswith(SENSITIVE_SUFFIXES):
        return "sensitive_filename"
    return None


def _plan(root, output, skips):
    license_files, license_folders = _license_records(root)
    output_relative = None
    if output.is_relative_to(root):
        output_relative = output.relative_to(root).as_posix()
    plan = []
    excluded = []
    for directory, folders, files in os.walk(root, followlinks=False):
        folders.sort()
        files.sort()
        for name in list(folders):
            source = Path(directory) / name
            relative = source.relative_to(root).as_posix()
            reason = _exclusion_reason(relative, True)
            if 'node_modules' in PurePosixPath(relative).parts:
                reason = None if relative in license_folders else 'cache_or_dependency_output'
            if relative == output_relative:
                reason = "output_directory"
            if reason:
                excluded.append({"path": relative, "reason": reason})
                folders.remove(name)
                continue
            sensitive = _sensitive_reason(relative)
            if sensitive:
                raise ValueError(f"Refuse sensitive source path {relative}: {sensitive}")
            mode = source.lstat().st_mode
            if stat.S_ISLNK(mode):
                raise ValueError(f"Refuse source symbolic link: {relative}")
            if not stat.S_ISDIR(mode):
                raise ValueError(f"Refuse special source directory entry: {relative}")
        for name in files:
            source = Path(directory) / name
            relative = source.relative_to(root).as_posix()
            reason = _exclusion_reason(relative, False)
            if 'node_modules' in PurePosixPath(relative).parts:
                reason = None if relative in license_files else 'cache_or_dependency_output'
            if reason:
                excluded.append({"path": relative, "reason": reason})
                continue
            sensitive = _sensitive_reason(relative)
            if sensitive:
                raise ValueError(f"Refuse sensitive source path {relative}: {sensitive}")
            mode = source.lstat().st_mode
            if stat.S_ISLNK(mode):
                raise ValueError(f"Refuse source symbolic link: {relative}")
            if not stat.S_ISREG(mode):
                raise ValueError(f"Refuse special source file: {relative}")
            if relative in skips:
                excluded.append({"path": relative, "reason": skips[relative]})
                continue
            plan.append((relative, source))
    excluded.sort(key=lambda row: row["path"])
    return plan, excluded


def _copy_regular_file(source, destination, normalize_modes=False):
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(source, flags)
    with os.fdopen(descriptor, "rb") as inp:
        info = os.fstat(inp.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ValueError(f"Source is no longer a regular file: {source}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as out:
            shutil.copyfileobj(inp, out, 1024 * 1024)
            mode = stat.S_IMODE(info.st_mode)
            if normalize_modes:
                mode = 0o755 if mode & 0o111 else 0o644
            os.fchmod(out.fileno(), mode)
        return destination.stat().st_size


def export_source(root, output, normalize_modes=False):
    """Validate all decisions and sources before atomically creating the output."""
    supplied_root = Path(root).expanduser()
    if supplied_root.is_symlink():
        raise ValueError("Source checkout cannot be a symbolic link")
    root = supplied_root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"Source checkout is not a directory: {root}")
    decisions = load(root / DECISIONS_PATH)
    if not isinstance(decisions, dict):
        raise ValueError(f"Invalid distribution decisions: {DECISIONS_PATH}")
    target = _output_path(root, output)
    skips, declared_omissions = _declared_skips(root)
    validation = validate(root)
    plan, excluded = _plan(root, target, skips)
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.tmp-", dir=target.parent))
    published = False
    files = 0
    byte_count = 0
    try:
        for relative, source in plan:
            byte_count += _copy_regular_file(source, staging / relative, normalize_modes)
            files += 1
        if normalize_modes:
            # mkdir inherits the maintainer's umask too. Normalize the root
            # and every exported directory, including nested notice paths.
            for directory, _, _ in os.walk(staging):
                Path(directory).chmod(0o755)
        if target.exists():
            if target.is_symlink() or not target.is_dir() or any(target.iterdir()):
                raise ValueError(f"Output directory changed during export: {target}")
            target.rmdir()
        os.replace(staging, target)
        published = True
    finally:
        if not published:
            shutil.rmtree(staging, ignore_errors=True)
    counts = Counter(row["reason"] for row in excluded)
    return {
        "output": str(target),
        "files": files,
        "bytes": byte_count,
        "mode_policy": ("directories_0755_files_0644_or_0755" if normalize_modes
                        else "preserve_file_modes"),
        "declared_omissions": declared_omissions,
        "excluded": excluded,
        "excluded_counts": dict(sorted(counts.items())),
        "validation": validation,
        "distribution_review": {
            "recorded_integration_complete": decisions.get("integration_complete", False),
            "recorded_enforced_by_exporter": decisions.get("enforced_by_exporter", False),
            "file_exclusions_enforced": True,
            "runtime_availability_verified": False,
        },
        "note": ("Source export only; this does not establish public image redistribution "
                 "readiness or anonymous acceptance."),
    }
