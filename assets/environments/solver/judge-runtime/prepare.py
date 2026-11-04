"""Materialize compressed inputs in a private judge filesystem."""
from pathlib import Path
import bz2
import gzip
import lzma
import shutil
import os


def prepare(directory):
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    for source in root.rglob("*"):
        if not source.is_file() or source.suffix not in {".xz", ".bz2", ".gz"}:
            continue
        target = source.with_suffix("")
        if target.exists():
            continue
        opener = {".xz": lzma.open, ".bz2": bz2.open, ".gz": gzip.open}[source.suffix]
        temporary = target.with_name(target.name + ".tcsexam-tmp")
        try:
            with opener(source, "rb") as src, temporary.open("wb") as dst:
                shutil.copyfileobj(src, dst, length=1024*1024)
            os.chmod(temporary, 0o644)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)

if __name__ == "__main__":
    import sys
    prepare(sys.argv[1])
