import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import tarfile
import tempfile
import time
import urllib.request

REPO = "https://raw.githubusercontent.com/MarioGrobler/PACE2025-instances"


def download(row, commit):
    url = f"{REPO}/{commit}/{row['path']}"
    expected_size = row["size"]
    for attempt in range(3):
        try:
            with tempfile.NamedTemporaryFile(suffix=".tar.xz", delete=False) as tmp:
                git_sha = hashlib.sha1()
                git_sha.update(f"blob {expected_size}\0".encode())
                size = 0
                request = urllib.request.Request(url, headers={"User-Agent": "tcsexam-release-rebuild"})
                with urllib.request.urlopen(request, timeout=120) as response:
                    while chunk := response.read(1024 * 1024):
                        tmp.write(chunk)
                        git_sha.update(chunk)
                        size += len(chunk)
                if size != expected_size or git_sha.hexdigest() != row["sha"]:
                    raise ValueError(f"upstream object mismatch: {row['path']}")
                tmp.flush()
                return tmp.name
        except Exception:
            if attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))


def extract(archive, row, reference, plain_dir):
    name = Path(row["path"]).name.removesuffix(".tar.xz")
    instance = name.removesuffix(".hgr")
    expected = reference["instances"][instance]
    with tarfile.open(archive, mode="r:xz") as tar:
        members = [member for member in tar.getmembers() if member.isfile()]
        if len(members) != 1 or not members[0].name.endswith(".hgr"):
            raise ValueError(f"unexpected archive layout: {row['path']}")
        with tar.extractfile(members[0]) as source:
            head = source.read(65536)
            lines = head.decode("ascii").splitlines()
            header = next((line for line in lines if line.startswith("p hs ")), None)
            if header is None:
                raise ValueError(f"missing HGR header: {name}")
            fields = header.split()
            if fields[2:] != [str(expected["n"]), str(expected["m"])]:
                raise ValueError(f"HGR dimensions differ: {name}: {header}")
            output = plain_dir / f"{name}.tmp"
            digest = hashlib.sha256()
            size = 0
            with output.open("wb") as target:
                target.write(head)
                digest.update(head)
                size += len(head)
                while chunk := source.read(1024 * 1024):
                    target.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
            if size == 0:
                raise ValueError(f"empty plaintext: {name}")
            output.replace(plain_dir / name)
    return {
        "path": f"plain/{name}",
        "bytes": size,
        "sha256": digest.hexdigest(),
        "hgr_header": header,
        "upstream_path": row["path"],
        "upstream_git_blob": row["sha"],
    }


def process(row, commit, reference, plain_dir):
    archive = download(row, commit)
    try:
        return extract(archive, row, reference, plain_dir)
    finally:
        Path(archive).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--expected-count", type=int, default=100)
    args = parser.parse_args()
    source = json.loads(Path(args.manifest).read_text())
    reference = json.loads(Path(args.reference).read_text())
    rows = source["files"]
    if len(rows) != args.expected_count or len({Path(row["path"]).name for row in rows}) != args.expected_count:
        raise ValueError(f"expected exactly {args.expected_count} distinct upstream instances")
    out = Path(args.out)
    plain_dir = out / "plain"
    if plain_dir.exists() and any(plain_dir.iterdir()):
        raise ValueError(f"output is not empty: {plain_dir}")
    plain_dir.mkdir(parents=True, exist_ok=True)
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(process, row, source["source_commit"], reference, plain_dir) for row in rows]
        for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
            results.append(future.result())
            if index % 10 == 0 or index == len(futures):
                print(f"validated {index}/{len(futures)}", flush=True)
    results.sort(key=lambda row: row["path"])
    manifest = {
        "source_repository": "MarioGrobler/PACE2025-instances",
        "source_commit": source["source_commit"],
        "instance_count": len(results),
        "total_plaintext_bytes": sum(row["bytes"] for row in results),
        "files": results,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (out / "files.sha256").write_text("".join(f"{row['sha256']}  {row['path']}\n" for row in results))
    print(json.dumps({key: manifest[key] for key in ("instance_count", "total_plaintext_bytes")}, indent=2))


if __name__ == "__main__":
    main()
