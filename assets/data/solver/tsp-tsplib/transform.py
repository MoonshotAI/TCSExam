"""Original TSPLIB parser and serialization for saved city permutations."""

import hashlib

import json

import os

import random

import sys

MASTER_SEED = 20260831

TRANSFORM_ID = "city-renumbering-v1"

SECTION_MARKERS = {
    "NODE_COORD_SECTION", "EDGE_WEIGHT_SECTION", "DISPLAY_DATA_SECTION",
    "TOUR_SECTION", "EDGE_DATA_SECTION", "FIXED_EDGES_SECTION",
}

COORD_TYPES = {"EUC_2D", "CEIL_2D", "GEO", "ATT"}

TRI_FORMATS = {
    "UPPER_ROW", "LOWER_ROW", "UPPER_COL", "LOWER_COL",
    "UPPER_DIAG_ROW", "LOWER_DIAG_ROW", "UPPER_DIAG_COL", "LOWER_DIAG_COL",
}

def parse_instance(path):
    """按判侧 tsplib.h 的口径解析 TSPLIB 文件。返回 dict：逐字头行、
    权值段名、解析内容（坐标 token 每原 id，或 1 基全矩阵）。"""
    with open(path, "rb") as f:
        raw = f.read()
    text = raw.decode("ascii")
    header_lines = []
    section = None
    weight_section = None
    body = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s in SECTION_MARKERS:
            section = s
            if s in ("NODE_COORD_SECTION", "EDGE_WEIGHT_SECTION"):
                weight_section = s
            continue
        if s == "EOF":
            break
        if section is None:
            header_lines.append(line.rstrip("\r"))
        elif section in ("NODE_COORD_SECTION", "EDGE_WEIGHT_SECTION"):
            body.append(s)

    header = {}
    for ln in header_lines:
        if ":" in ln:
            k, v = ln.split(":", 1)
            header[k.strip()] = v.strip()
    n = int(header["DIMENSION"])
    ewt = header.get("EDGE_WEIGHT_TYPE", "EUC_2D")
    ewf = header.get("EDGE_WEIGHT_FORMAT", "")

    inst = {
        "n": n, "edge_weight_type": ewt, "edge_weight_format": ewf,
        "header_lines": header_lines, "section": weight_section, "raw": raw,
    }
    if ewt in COORD_TYPES:
        coords = [None] * (n + 1)
        read = 0
        for bl in body:
            if read >= n:
                break
            parts = bl.split()
            if len(parts) < 3:
                break
            idx = int(parts[0])
            if not 1 <= idx <= n:
                raise ValueError(f"{path}: bad node index {idx}")
            coords[idx] = (parts[1], parts[2])
            read += 1
        if read < n:
            raise ValueError(f"{path}: expected {n} coord lines, got {read}")
        inst["coords"] = coords
    elif ewt == "EXPLICIT":
        vals = []
        for bl in body:
            vals.extend(int(t) for t in bl.split())
        mat = [[0] * (n + 1) for _ in range(n + 1)]
        f = ewf
        k = 0

        def take():
            nonlocal k
            v = vals[k]
            k += 1
            return v

        if f == "FULL_MATRIX":
            need = n * n
            assert len(vals) >= need, f"{path}: short matrix"
            for i in range(1, n + 1):
                for j in range(1, n + 1):
                    mat[i][j] = take()
        else:
            if f in ("UPPER_ROW", "LOWER_ROW", "UPPER_COL", "LOWER_COL"):
                need = n * (n - 1) // 2
            elif f in TRI_FORMATS:
                need = n * (n + 1) // 2
            else:
                raise ValueError(f"{path}: unsupported EDGE_WEIGHT_FORMAT {f!r}")
            assert len(vals) >= need, f"{path}: short matrix ({len(vals)}<{need})"
            if f == "UPPER_ROW":
                pairs = ((i, j) for i in range(1, n + 1) for j in range(i + 1, n + 1))
            elif f == "LOWER_ROW":
                pairs = ((i, j) for i in range(1, n + 1) for j in range(1, i))
            elif f == "UPPER_DIAG_ROW":
                pairs = ((i, j) for i in range(1, n + 1) for j in range(i, n + 1))
            elif f == "LOWER_DIAG_ROW":
                pairs = ((i, j) for i in range(1, n + 1) for j in range(1, i + 1))
            elif f == "UPPER_COL":
                pairs = ((i, j) for j in range(1, n + 1) for i in range(1, j))
            elif f == "LOWER_COL":
                pairs = ((i, j) for j in range(1, n + 1) for i in range(j + 1, n + 1))
            elif f == "UPPER_DIAG_COL":
                pairs = ((i, j) for j in range(1, n + 1) for i in range(1, j + 1))
            else:  # LOWER_DIAG_COL
                pairs = ((i, j) for j in range(1, n + 1) for i in range(j, n + 1))
            for i, j in pairs:
                v = take()
                mat[i][j] = mat[j][i] = v
        inst["matrix"] = mat
    else:
        raise ValueError(f"{path}: unsupported EDGE_WEIGHT_TYPE {ewt!r}")
    return inst

def emit_instance(inst, id_order, comment_note=None):
    """按 id_order（新编号 j -> 原 id）发射实例文本（头部逐字 + 权值段）。"""
    n = inst["n"]
    out = list(inst["header_lines"])
    out.append(inst["section"])
    if inst["edge_weight_type"] in COORD_TYPES:
        coords = inst["coords"]
        for j in range(1, n + 1):
            x_tok, y_tok = coords[id_order[j - 1]]
            out.append(f"{j} {x_tok} {y_tok}")
    else:
        mat = inst["matrix"]
        pm = [[0] * (n + 1) for _ in range(n + 1)]
        for j in range(1, n + 1):
            oj = id_order[j - 1]
            row_j = mat[oj]
            pm_j = pm[j]
            for k in range(1, n + 1):
                pm_j[k] = row_j[id_order[k - 1]]
        f = inst["edge_weight_format"]
        if f == "FULL_MATRIX":
            for j in range(1, n + 1):
                out.append(" ".join(str(pm[j][k]) for k in range(1, n + 1)))
        else:
            if f in ("UPPER_ROW", "UPPER_DIAG_ROW"):
                diag = f == "UPPER_DIAG_ROW"
                rows = ((i, range(i if diag else i + 1, n + 1)) for i in range(1, n + 1))
            elif f in ("LOWER_ROW", "LOWER_DIAG_ROW"):
                diag = f == "LOWER_DIAG_ROW"
                rows = ((i, range(1, i + 1 if diag else i)) for i in range(1, n + 1))
            elif f in ("UPPER_COL", "UPPER_DIAG_COL"):
                diag = f == "UPPER_DIAG_COL"
                rows = ((j, range(1, j + 1 if diag else j)) for j in range(1, n + 1))
            else:  # LOWER_COL / LOWER_DIAG_COL
                diag = f == "LOWER_DIAG_COL"
                rows = ((j, range(j if diag else j + 1, n + 1)) for j in range(1, n + 1))
            for fixed, js in rows:
                vals = [str(pm[fixed][k]) for k in js]
                if vals:
                    out.append(" ".join(vals))
    out.append("EOF")
    return ("\n".join(out) + "\n").encode("ascii")
