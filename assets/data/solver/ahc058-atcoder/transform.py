#!/usr/bin/env python3
"""ahc058-atcoder form2 保构变换（隐藏 30% 判分实例；tests 侧专用）。

对 split.json 标记为 hidden 的每个实例做严格同构改写：机器（生产依赖图
顶点）列置换 pi: old 0..N-1 -> new 0..N-1——A 行与 L 行成本矩阵的列同步
重排；N/L/T/K 头不动，行序不动。官方计分模拟器（scoring.simulate，官方
AHC058 compute_score 的逐位移植）对机器标号置换不变：任意动作序列的最终
苹果数严格不变，K 由同构沿用。

变换产物用新文件名（t01.txt ...，按源实例名排序依次编号），原始名 ->
变换名映射与置换表只存 tests/transform_manifest.json（tests 侧，不进环境、
不进判分镜像 /tests）。

种子规则（逐实例，确定性）：
    seed = int.from_bytes(sha256("tcshard-form2-ahc058-260920:" + stem)
           .digest()[:8], "big")
    rng  = random.Random(seed)
stem 为源实例名去扩展名（如 "h06"）。同种子严格复现同一份变换字节。

子命令：
  apply              对 split.json 的 hidden 实例批量变换：读
                     tests/instances-library/（自生成原字节），写
                     tests/instances/tNN.txt + tests/transform_manifest.json
  invert             独立逆变换校验：按 manifest 的置换对每个变换后实例做
                     逆变换，与源字节逐一逐字节比对
  rewrite-solutions  用 manifest 的机器置换重写预录动作序列（*.out：T 行，
                     每行 "-1" 或 "<level> <id>"，id 重标号；oracle 桩用），
                     并按变换后实例重建查表 manifest

Stdlib only.
"""
import argparse
import hashlib
import json
import os
import random
import re
import sys

TRANSFORM_ID = "ahc058-machine-relabel-form2-v1"
SEED_PREFIX = "tcshard-form2-ahc058-260920:"
SEED_RULE = (
    'seed = int.from_bytes(sha256("tcshard-form2-ahc058-260920:" + stem)'
    '.digest()[:8], "big"); rng = random.Random(seed); one shuffle of the'
    " machine-id list 0..N-1; transformed file name tNN assigned in sorted"
    " source-name order"
)

TESTS = os.path.dirname(os.path.abspath(__file__))


def derive_seed(stem):
    h = hashlib.sha256((SEED_PREFIX + stem).encode()).digest()
    return int.from_bytes(h[:8], "big")


def oracle_hash(plain_bytes):
    """oracle 桩对实例文本的查表键（空白归一化 token 流的 sha256）。"""
    return hashlib.sha256(b" ".join(plain_bytes.split())).hexdigest()


def load_instance(path):
    """AHC058 format: N L T K, then N values A, then L rows of N costs C."""
    with open(path) as f:
        vals = f.read().split()
    pos = 0

    def nxt():
        nonlocal pos
        if pos >= len(vals):
            raise ValueError("unexpected end of instance file")
        v = int(vals[pos])
        pos += 1
        return v

    N, L, T, K = nxt(), nxt(), nxt(), nxt()
    A = [nxt() for _ in range(N)]
    C = [[nxt() for _ in range(N)] for _ in range(L)]
    if pos != len(vals):
        raise ValueError(f"{path}: trailing tokens after C rows "
                         f"({len(vals) - pos} extra)")
    return {"N": N, "L": L, "T": T, "K": K, "A": A, "C": C}


def emit(inst):
    lines = [f"{inst['N']} {inst['L']} {inst['T']} {inst['K']}",
             " ".join(str(v) for v in inst["A"])]
    lines += [" ".join(str(v) for v in row) for row in inst["C"]]
    return ("\n".join(lines) + "\n").encode()


def transform_instance(inst, perm):
    """Return new_inst with machine columns permuted by perm (new[pi[old]]
    = old[old])."""
    N = inst["N"]
    new_A = [None] * N
    for old in range(N):
        new_A[perm[old]] = inst["A"][old]
    new_C = []
    for row in inst["C"]:
        new_row = [None] * N
        for old in range(N):
            new_row[perm[old]] = row[old]
        new_C.append(new_row)
    return {"N": inst["N"], "L": inst["L"], "T": inst["T"], "K": inst["K"],
            "A": new_A, "C": new_C}


def invert_instance(inst_t, perm):
    inv = [None] * len(perm)
    for old, new in enumerate(perm):
        inv[new] = old
    return transform_instance(inst_t, inv)


def hidden_stems_sorted():
    with open(os.path.join(TESTS, "split.json")) as f:
        split = json.load(f)
    return sorted(fn[:-len(".txt")] for fn, side in split.items()
                  if side == "hidden")


def cmd_apply(args):
    os.makedirs(args.out_dir, exist_ok=True)
    stems = hidden_stems_sorted()
    manifest = {
        "transform": TRANSFORM_ID,
        "operations": ["permute-machine-columns"],
        "header_NLTK": "untouched",
        "seed_rule": SEED_RULE,
        "instances": {},
    }
    for i, stem in enumerate(stems, 1):
        new_name = f"t{i:02d}"
        src = os.path.join(args.instances_dir, stem + ".txt")
        with open(src, "rb") as f:
            plain = f.read()
        inst = load_instance(src)
        n = inst["N"]
        rng = random.Random(derive_seed(stem))
        perm = list(range(n))
        rng.shuffle(perm)
        new = transform_instance(inst, perm)
        out_plain = emit(new)
        dst = os.path.join(args.out_dir, new_name + ".txt")
        with open(dst, "wb") as f:
            f.write(out_plain)
        os.chmod(dst, 0o644)
        manifest["instances"][new_name] = {
            "official": stem,
            "seed": derive_seed(stem),
            "n_machines": n,
            "perm": perm,
            "src_sha256_plain": hashlib.sha256(plain).hexdigest(),
            "out_sha256_plain": hashlib.sha256(out_plain).hexdigest(),
            "oracle_key": oracle_hash(out_plain),
        }
        print(f"[apply] {stem} -> {new_name}.txt ({n} machines)", flush=True)
    with open(args.manifest, "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
        f.write("\n")
    os.chmod(args.manifest, 0o644)
    print(f"[apply] manifest: {args.manifest} "
          f"({len(manifest['instances'])} instances)")


def cmd_invert(args):
    with open(args.manifest) as f:
        manifest = json.load(f)
    n_ok = n_bad = 0
    for new_name, rec in sorted(manifest["instances"].items()):
        stem = rec["official"]
        inst_t = load_instance(os.path.join(args.trans_dir,
                                            new_name + ".txt"))
        restored = invert_instance(inst_t, rec["perm"])
        inst_o = load_instance(os.path.join(args.orig_dir, stem + ".txt"))
        if restored == inst_o:
            n_ok += 1
            print(f"[invert] {new_name} ({stem}): ok")
        else:
            n_bad += 1
            print(f"[invert] {new_name} ({stem}): FAIL restored != original")
    print(f"[invert] ok={n_ok} bad={n_bad}")
    return 1 if n_bad else 0


def cmd_rewrite_solutions(args):
    """Rewrite prerecorded action sequences (T lines: "-1" or
    "<level> <id>") with the manifest's machine permutation; rebuild the
    oracle lookup manifest against the transformed instances."""
    with open(args.manifest) as f:
        manifest = json.load(f)["instances"]
    os.makedirs(args.out_dir, exist_ok=True)
    out_manifest = {}
    n_sol = 0
    for new_name, rec in sorted(manifest.items()):
        stem = rec["official"]
        src_sol = os.path.join(args.sol_dir, stem + ".out")
        if not os.path.exists(src_sol):
            print(f"[rewrite-solutions] {stem}: no prerecorded solution, "
                  f"skipped")
            continue
        perm = rec["perm"]
        out_lines = []
        with open(src_sol) as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    out_lines.append(line)
                    continue
                toks = line.split()
                if toks[0] == "-1":
                    out_lines.append(line)
                    continue
                level, mid = int(toks[0]), int(toks[1])
                out_lines.append(f"{level} {perm[mid]}")
        dst = os.path.join(args.out_dir, new_name + ".out")
        with open(dst, "w") as f:
            f.write("\n".join(out_lines) + "\n")
        with open(os.path.join(args.instances_dir, new_name + ".txt"),
                  "rb") as f:
            key = oracle_hash(f.read())
        if key != rec["oracle_key"]:
            sys.exit(f"[rewrite-solutions] {new_name}: instance key mismatch "
                     f"with manifest ({key} != {rec['oracle_key']})")
        out_manifest[key] = {"sol": new_name + ".out", "instance": new_name}
        n_sol += 1
    with open(os.path.join(args.out_dir, "manifest-hidden.json"), "w") as f:
        json.dump(out_manifest, f, indent=0, sort_keys=True)
        f.write("\n")
    print(f"[rewrite-solutions] {n_sol} solutions rewritten -> {args.out_dir}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("apply")
    p.add_argument("--instances-dir", default=os.path.join(
        TESTS, "instances-library"))
    p.add_argument("--out-dir", default=os.path.join(TESTS, "instances"))
    p.add_argument("--manifest", default=os.path.join(
        TESTS, "transform_manifest.json"))
    p.set_defaults(fn=cmd_apply)
    p = sub.add_parser("invert")
    p.add_argument("--orig-dir", default=os.path.join(TESTS,
                                                      "instances-library"))
    p.add_argument("--trans-dir", default=os.path.join(TESTS, "instances"))
    p.add_argument("--manifest", default=os.path.join(
        TESTS, "transform_manifest.json"))
    p.set_defaults(fn=cmd_invert)
    p = sub.add_parser("rewrite-solutions")
    p.add_argument("--instances-dir", default=os.path.join(TESTS, "instances"),
                   help="directory with the TRANSFORMED instances")
    p.add_argument("--sol-dir", required=True,
                   help="directory with the original prerecorded solutions")
    p.add_argument("--manifest", default=os.path.join(
        TESTS, "transform_manifest.json"))
    p.add_argument("--out-dir", required=True)
    p.set_defaults(fn=cmd_rewrite_solutions)
    args = ap.parse_args()
    sys.exit(args.fn(args) or 0)


if __name__ == "__main__":
    main()
