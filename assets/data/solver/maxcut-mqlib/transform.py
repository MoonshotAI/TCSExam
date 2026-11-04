#!/usr/bin/env python3
"""maxcut-mqlib form2 隐藏集保构变换（顶点重标号，严格同构）。

变换数学（form2-conversion-recipes.md 图题配方）：
  随机顶点置换 π，按 π 重标号顶点并重写边表。MaxCut 的目标值只依赖加权
  邻接结构，任何割的目标值在 π 下严格不变——K 同构沿用、B 在变换后实例
  上重测（基线禁忌搜索的轨迹依赖顶点编号）。

字节层处置（指纹清除，与 2026-08-31 变换批同一实现规则）：
  * 丢弃每个 `#` 注释行（原文件头注释带实例名/随机种子，是背诵指纹）；
  * 顶点按每实例种子置换重标号；
  * 每条边以 "a b w" 重写，a < b，权重 token 逐字保留（不重格式化——
    60 个实例分数权重、47 个负权，目标值必须逐位一致）；
  * 边表排序，字节流不带原始布局痕迹（判分集 150 个实例已扫描无重复
    端点对、头行 m 与数据行数一致，排序不改语义）。

种子规则（与 2026-08-31 变换批一致，260913 async 变换恢复批同一批置换）：
    seed = int.from_bytes(sha256("tcshard-transform-20260831:" + official_name)[:8])
    perm = Random(seed).shuffle([1..n])；perm[v-1] = 旧顶点 v 的新标号。
完整置换表记录在本目录 transform_manifest.json（只存 tests/，连同
官方名 → 变换名 txNNN 映射），验证与 oracle 重写不依赖重放 RNG。

命名：隐藏判分实例用新文件名 txNNN.txt.xz（防与公开实例撞名；
txNNN 按官方名字典序赋号）。

用法：
    transform.py --apply OFFICIAL_XZ_DIR OUT_DIR MANIFEST_JSON [official_name ...]
        把 OFFICIAL_XZ_DIR 里的 <official>.txt.xz 变换成 OUT_DIR 下的
        txNNN.txt.xz，并写/合并 manifest。
    transform.py --invert TX_XZ MANIFEST_JSON OUT_TXT
        按 manifest 的置换表把变换后实例反演回原始标号（头行 + 原始
        标号的排序边表；注释行不可恢复——语义等价，见 test_transform.py
        的往返一致断言）。
"""
import hashlib
import json
import lzma
import os
import random
import sys

MASTER_SEED_TAG = "tcshard-transform-20260831"
TRANSFORM_ID = "vertex-relabeling-v1"


def derive_seed(official_name):
    """每实例种子：主种子 20260831 x 官方实例名哈希。"""
    h = hashlib.sha256(f"{MASTER_SEED_TAG}:{official_name}".encode())
    return int.from_bytes(h.digest()[:8], "big")


def load_mqlib_text(text):
    """解析解压后的 MQLib 实例文本，返回 (n, edges)，edges 为
    (u, v, w_token) 列表（1 基，权重 token 原文保留，无浮点漂移）。"""
    n = m = None
    edges = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        if n is None:
            n, m = int(parts[0]), int(parts[1])
            continue
        if len(parts) != 3:
            raise ValueError(f"bad data line: {line!r}")
        u, v = int(parts[0]), int(parts[1])
        if u == v:
            raise ValueError(f"self-loop: {line!r}")
        edges.append((u, v, parts[2]))
    if n is None:
        raise ValueError("empty instance")
    if len(edges) != m:
        raise ValueError(f"edge count mismatch: header {m} vs {len(edges)}")
    return n, edges


def canonical_bytes(n, edges):
    """头行 + 排序边表的规范字节流（a<b，权重 token 原文）。"""
    norm = []
    for u, v, w in edges:
        a, b = (u, v) if u < v else (v, u)
        norm.append((a, b, w))
    norm.sort(key=lambda e: (e[0], e[1]))
    out = [f"{n} {len(norm)}\n"]
    out += [f"{a} {b} {w}\n" for a, b, w in norm]
    return "".join(out).encode("utf-8")


def transform_bytes(data, official_name):
    """变换一个解压后的实例字节流。返回 (new_bytes, perm, seed)。"""
    text = data.decode("utf-8", errors="replace")
    n, edges = load_mqlib_text(text)
    seed = derive_seed(official_name)
    perm = list(range(1, n + 1))
    random.Random(seed).shuffle(perm)  # perm[v-1] = 旧顶点 v 的新标号
    new_edges = [(perm[u - 1], perm[v - 1], w) for u, v, w in edges]
    return canonical_bytes(n, new_edges), perm, seed


def invert_bytes(data, perm):
    """按置换表反演：输入变换后字节流，输出原始标号的规范字节流。"""
    text = data.decode("utf-8", errors="replace")
    n, edges = load_mqlib_text(text)
    if sorted(perm) != list(range(1, n + 1)):
        raise ValueError("perm is not a bijection of 1..n")
    inv = [0] * n  # inv[new-1] = old
    for old, new in enumerate(perm, start=1):
        inv[new - 1] = old
    orig_edges = [(inv[a - 1], inv[b - 1], w) for a, b, w in edges]
    return canonical_bytes(n, orig_edges)


def permute_solution_tokens(tokens, perm):
    """解的同步变换：割的 0/1 标号随顶点走，new_side[perm[v]-1] =
    old_side[v-1]。tokens 为每顶点一个 "0"/"1" 的列表。"""
    if len(tokens) != len(perm):
        raise ValueError(f"solution has {len(tokens)} tokens, perm {len(perm)}")
    out = [None] * len(tokens)
    for v in range(len(tokens)):
        out[perm[v] - 1] = tokens[v]
    return out


def cmd_apply(argv):
    if len(argv) < 4:
        print(f"usage: {argv[0]} --apply OFFICIAL_XZ_DIR OUT_DIR MANIFEST_JSON "
              "[official_name ...]", file=sys.stderr)
        return 2
    in_dir, out_dir, manifest_path = argv[2:5]
    names = argv[5:]
    if not names:
        print(f"{argv[0]}: no instance names given (hidden set is explicit)",
              file=sys.stderr)
        return 1
    os.makedirs(out_dir, exist_ok=True)
    manifest = {
        "transform": TRANSFORM_ID,
        "master_seed_tag": MASTER_SEED_TAG,
        "seed_derivation": ("int.from_bytes(sha256(tag + ':' + official_name)[:8]); "
                            "Random(seed).shuffle([1..n]); perm[v-1] = new label "
                            "of old vertex v"),
        "name_note": ("txNNN assigned in sorted(official) order; official -> txNNN "
                      "mapping lives ONLY in this tests-side manifest"),
        "hash_note": "sha256 values are over the RAW DECOMPRESSED byte stream",
        "instances": {},
    }
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            manifest = json.load(f)
        manifest.setdefault("instances", {})
    officials = sorted(names)
    for i, official in enumerate(officials, start=1):
        tx = f"tx{i:03d}.txt"
        src = os.path.join(in_dir, official + ".xz")
        with lzma.open(src, "rb") as f:
            data = f.read()
        new_data, perm, seed = transform_bytes(data, official)
        with lzma.open(os.path.join(out_dir, tx + ".xz"), "wb", preset=6) as f:
            f.write(new_data)
        n = len(perm)
        manifest["instances"][tx] = {
            "official": official,
            "seed_hex": f"{seed:016x}",
            "n": n,
            "m": len(new_data.decode().splitlines()) - 1,
            "perm": perm,
            "sha256_orig_bytes": hashlib.sha256(data).hexdigest(),
            "sha256_new_bytes": hashlib.sha256(new_data).hexdigest(),
        }
        print(f"  {official} -> {tx}: n={n} seed={seed:016x}", flush=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
    print(f"transformed {len(officials)} instance(s) -> {out_dir}")
    print(f"manifest -> {manifest_path}")
    return 0


def cmd_invert(argv):
    if len(argv) != 5:
        print(f"usage: {argv[0]} --invert TX_XZ MANIFEST_JSON OUT_TXT",
              file=sys.stderr)
        return 2
    tx_xz, manifest_path, out_txt = argv[2:5]
    with open(manifest_path) as f:
        manifest = json.load(f)
    tx = os.path.basename(tx_xz)
    if tx.endswith(".xz"):
        tx = tx[:-3]
    ent = manifest["instances"].get(tx)
    if ent is None:
        print(f"{argv[0]}: {tx} not in manifest", file=sys.stderr)
        return 1
    with lzma.open(tx_xz, "rb") as f:
        data = f.read()
    orig = invert_bytes(data, ent["perm"])
    with open(out_txt, "wb") as f:
        f.write(orig)
    print(f"inverted {tx} (official {ent['official']}) -> {out_txt}")
    return 0


def main(argv):
    if len(argv) < 2 or argv[1] not in ("--apply", "--invert"):
        print(__doc__)
        return 2
    if argv[1] == "--apply":
        return cmd_apply(argv)
    return cmd_invert(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
