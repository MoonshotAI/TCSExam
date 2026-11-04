"""Original input parser and canonical graph serializer."""

import bz2

import hashlib

import json

import os

import random

import sys

def load_metis(text):
    """解析解压后的 METIS/DIMACS10 实例文本，返回 (n, m, adj)，adj[v] 为
    1 基邻居列表（按读出顺序）。与判分装载语义一致：`%` 行跳过；头行
    后每个非 `%` 行（含空行）算一个顶点的邻接行。"""
    lines = text.splitlines()
    n = m = None
    adj = []
    for line in lines:
        s = line.strip()
        if not s or s.startswith('%'):
            if n is not None and s.startswith('%'):
                continue
            if n is None:
                continue
        if n is None:
            parts = s.split()
            if len(parts) < 2:
                raise ValueError('malformed header line')
            (n, m) = (int(parts[0]), int(parts[1]))
            fmt = parts[2] if len(parts) > 2 else '0'
            if fmt != '0':
                raise ValueError(f'weighted graphs unsupported (fmt={fmt})')
            continue
        adj.append([int(t) for t in s.split()])
        if len(adj) == n:
            break
    if n is None:
        raise ValueError('empty instance')
    if len(adj) != n:
        raise ValueError(f'expected {n} adjacency lines, found {len(adj)}')
    if sum((len(a) for a in adj)) != 2 * m:
        raise ValueError(f'expected {2 * m} adjacency tokens, found {sum((len(a) for a in adj))}')
    return (n, m, adj)

def canonical_text(n, m, adj_new_order):
    """头行 + 邻接行（邻居已升序）的规范文本。"""
    out = [f'{n} {m}\n']
    out += [' '.join((str(u) for u in line)) + '\n' for line in adj_new_order]
    return ''.join(out)

def token_sha256_text(text):
    """oracle 桩的键法：规范化 token 流 sha256（解压后文本）。"""
    return hashlib.sha256(' '.join(text.split()).encode()).hexdigest()
