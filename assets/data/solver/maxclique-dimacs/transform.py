"""Original DIMACS input parser and frozen transformed serialization."""

import hashlib

import json

import os

import random

import sys

MASTER_SEED_TAG = "tcshard-transform-20260831"

TRANSFORM_ID = "vertex-relabeling-v1"

HEADER_COMMENT = "c max clique instance (DIMACS ASCII)"

def parse_dimacs_text(text):
    """解析 DIMACS ASCII 图文本，返回 (n, edges)，edges 为 (u,v) 集合
    （1 基、u<v；重复/双向行折叠、自环弃除——与判分 checker 的装载语义
    一致）。无 p 行时按最大顶点号回退。"""
    n = None
    vmax = 0
    edges = set()
    for line in text.splitlines():
        if not line or line[0] in "c\r\n":
            continue
        parts = line.split()
        if line[0] == "p":
            if len(parts) >= 4:
                n = int(parts[2])
        elif line[0] == "e":
            if len(parts) < 3:
                continue
            u, v = int(parts[1]), int(parts[2])
            if u == v or u < 1 or v < 1:
                continue
            if u > v:
                u, v = v, u
            edges.add((u, v))
            vmax = max(vmax, u, v)
    if n is None:
        n = vmax
    if n < vmax:
        n = vmax
    if n < 1:
        raise ValueError("no p line and no edges")
    return n, edges

def canonical_text(n, edges):
    """统一注释头 + p 行 + 排序边表的规范文本。"""
    ordered = sorted((a, b) if a < b else (b, a) for a, b in edges)
    out = [HEADER_COMMENT + "\n", f"p edge {n} {len(ordered)}\n"]
    out += [f"e {a} {b}\n" for a, b in ordered]
    return "".join(out)
