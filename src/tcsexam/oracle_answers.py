"""Identify concrete oracle-answer paths without reading answer contents."""
from pathlib import PurePosixPath


def is_oracle_answer_path(value):
    parts = PurePosixPath(value).parts
    for index, part in enumerate(parts[:-1]):
        if part != "solution":
            continue
        tail = parts[index + 1:]
        if tail and tail[0] in {"precomputed", "precomputed.tar.xz", "solutions"}:
            return True
        if tail == ("Basic.lean",):
            return True
    return False
