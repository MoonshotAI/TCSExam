#!/usr/bin/env python3
"""qap-qaplib 判分集保构变换工具（260917 查表默写修复批）。

这是什么：把 QAPLIB 官方实例变换成判分用的代号实例（exNNN），并衍生
oracle 桩的变换后重放包。变换保持最优值不变（保构），让"背下官方实例
最优排列"在判分实例上直接失效——官方实例公开可查，判分实例的置换关系
不进模型环境。

给谁看：出题人（我们自己）与后续复核判分集的人。

变换操作（目标函数值不变）：
  设施用带种子双射 pi 重编号、位置用独立带种子双射 sigma 重编号，
  流量矩阵 F 与距离矩阵 D 同步重排：
      F'[pi(i)][pi(j)] = F[i][j]      D'[sigma(a)][sigma(b)] = D[a][b]
  解的映射：p'(pi(i)) = sigma(p(i))，即 p' = sigma ∘ p ∘ pi^{-1}，
  cost'(p') == cost(p) 对每个排列成立，故最优值 K 同构不变。
  .dat 格式无注释，规范化重写后原文件的字节布局特征一并去除。

种子规则（逐实例、确定性）：
    seed = int.from_bytes(
        sha256(b"tcshard-transform-20260831:" + name.encode())[:8], "big")
    rng  = random.Random(seed)
  name 为官方实例名（如 "bur26a.dat"）。RNG 消耗顺序：先 shuffle [1..n]
  得设施置换 pi，再 shuffle [1..n] 得位置置换 sigma。

  沿用 20260831 种子标签的原因：2026-09-13 恢复批（next-steps-260911.md
  §E2）已按同一规则生成 136 个变换实例并烘进判分镜像 solver-qap-qaplib-judge-v9
  The original restoration used the same facility and location permutation rule.
  保持同一种子让本脚本再生成的字节与在线判分镜像逐字节一致（出厂断言：
  bur26a.dat 再生成 == 恢复批同名字节），final 谱系（v11）与 async 谱系
  （v10）共用同一套变换实例，oracle 桩两包通用。

代号分配：exNNN ↔ 官方名的对应沿用仓内 tests/codename-map.json 的既有
分配（按官方名字典序，ex001..ex136），本脚本只断言一致、不重新分配，
以免与 async 包及在线 v9 镜像漂移。

子命令：
  batch            官方实例目录 → 变换后 exNNN.dat 全集 + transform_manifest.json
                   （完整置换表，保密：默认写到 git 仓外路径，绝不进判分
                   镜像 /tests 的模型可读层）+ codename-map.json（代号 ↔
                   官方名 ↔ 变换后字节 sha256 ↔ 官方字节 sha256 ↔ 置换参数
                   哈希，可进 tests/）。【历史：form2 划分前全库 136 一次性
                   生成用；划分冻结后 tests/instances 只剩隐藏 41 键，不要再跑】
  verify           独立逆变换校验：用 manifest 里的逆置换把变换实例还原成
                   官方矩阵逐元素比对 + 元素多重集比对 + 字节必须不同【历史，
                   同上】
  bake-oracle      官方登记排列（1-based 正向）按 p'(pi(i)) = sigma(p(i))
                   改写，manifest 按变换后实例 token 流 sha256 重键【历史，同上】
  verify-oracle    用任务真 check_qap（tests/scoring.py）对变换后
                   实例逐一代入改写排列，代价值必须精确等于参照 K
  --apply IN --name OFFICIAL_NAME --out OUT
                   单实例正向变换：按种子规则现场重导 π/σ，输出规范化字节
  --invert IN --name OFFICIAL_NAME --out OUT
                   单实例逆变换：同一对 π/σ 把变换矩阵还原（规范形式）；
                   invert(apply(x)) 与 x 逐元素相等（往返一致）

form2（2026-09-20）后判分隐藏集 = 官方全集 136 的 30% 分层抽样（tests/split.json）
的变换副本 41 键；数学核验的日常入口是 tests/test_transform.py（只依赖本文件
与 tests/scoring.py，不依赖保密 manifest）。

Stdlib only.
"""

import argparse
import hashlib
import json
import os
import random
import sys

SEED_TAG = "tcshard-transform-20260831"
TRANSFORM_ID = "qap-fac-loc-permute-v1"
SEED_RULE = (
    "seed = int.from_bytes(sha256('tcshard-transform-20260831:' + name)[:8],"
    " 'big'); rng = random.Random(seed); consumption order: facility"
    " permutation shuffle, then location permutation shuffle;"
    " name = official instance file name (e.g. bur26a.dat)"
)


def derive_seed(name):
    h = hashlib.sha256((SEED_TAG + ":" + name).encode()).digest()
    return int.from_bytes(h[:8], "big")


def oracle_hash(plain_bytes):
    """Exactly what the oracle stub computes on its stdin."""
    return hashlib.sha256(b" ".join(plain_bytes.split())).hexdigest()


def parse_dat(path):
    with open(path) as f:
        vals = f.read().split()
    n = int(vals[0])
    need = 1 + 2 * n * n
    if len(vals) != need:
        raise ValueError(f"{path}: expected {need} tokens, found {len(vals)}")
    nums = [int(v) for v in vals[1:]]
    F = [nums[i * n:(i + 1) * n] for i in range(n)]
    D = [nums[n * n + i * n:n * n + (i + 1) * n] for i in range(n)]
    return n, F, D


def transform_instance(name, n, F, D):
    """Return (Fp, Dp, pi, sigma); pi/sigma are 1-based old->new lists."""
    rng = random.Random(derive_seed(name))
    pi = list(range(1, n + 1))
    rng.shuffle(pi)          # facilities: pi[old-1] = new
    sigma = list(range(1, n + 1))
    rng.shuffle(sigma)       # locations: sigma[old-1] = new
    inv_pi = [0] * n
    inv_sigma = [0] * n
    for old in range(n):
        inv_pi[pi[old] - 1] = old
        inv_sigma[sigma[old] - 1] = old
    Fp = [[F[inv_pi[a]][inv_pi[b]] for b in range(n)] for a in range(n)]
    Dp = [[D[inv_sigma[a]][inv_sigma[b]] for b in range(n)] for a in range(n)]
    return Fp, Dp, pi, sigma


def serialize(n, F, D):
    out = [f"{n}\n"]
    for row in F:
        out.append(" " + " ".join(str(v) for v in row) + " \n")
    for row in D:
        out.append(" " + " ".join(str(v) for v in row) + " \n")
    return "".join(out).encode()


def params_hash(pi, sigma):
    """置换参数哈希：codename-map 里登记的是它，完整置换表只活在
    transform_manifest.json（仓外保密）。"""
    blob = json.dumps({"pi": pi, "sigma": sigma}, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def load_codename_assignment(path):
    """读既有 codename-map.json，返回 {official: exNNN}（按官方名字典序
    断言 ex 编号连续，防止与 async 包/在线镜像漂移）。"""
    with open(path) as f:
        data = json.load(f)
    inst = data["instances"]
    official2code = {rec["official"]: code for code, rec in inst.items()}
    codes = sorted(inst)
    assert codes == [f"ex{i:03d}.dat" for i in range(1, len(codes) + 1)], \
        f"codename 编号不连续: {codes[:3]}...{codes[-3:]}"
    officials = sorted(official2code)
    assert [official2code[o] for o in officials] == codes, \
        "既有分配不是按官方名字典序：与 3580 批分配不一致，停止以防漂移"
    return official2code


def rewrite_perm(perm1, pi, sigma):
    """p'(pi(i)) = sigma(p(i)); all 1-based, lists indexed from 0."""
    n = len(perm1)
    newp = [0] * n
    for old in range(n):
        newp[pi[old] - 1] = sigma[perm1[old] - 1]
    return newp


def cmd_batch(args):
    official2code = load_codename_assignment(args.codename_map)
    os.makedirs(args.out_dir, exist_ok=True)
    names = sorted(f for f in os.listdir(args.instances_dir)
                   if f.endswith(".dat"))
    if sorted(official2code) != names:
        sys.exit(f"[batch] 官方实例集与 codename-map 不一致: "
                 f"map {len(official2code)} vs dir {len(names)}")
    manifest = {
        "transform": TRANSFORM_ID,
        "operations": ["permute-facilities(F lockstep)",
                       "permute-locations(D lockstep)",
                       "canonical-reserialize"],
        "seed_rule": SEED_RULE,
        "codename_rule": "existing codename-map assignment (alphabetical)",
        "instances": {},
    }
    newmap = {
        "transform": {
            "id": TRANSFORM_ID,
            "seed_rule": SEED_RULE,
            "note": ("判分实例 = 官方全集的保构变换副本（设施/位置重编号，"
                     "最优值不变）；完整置换表在 transform_manifest.json"
                     "（仓外保密，见 PROVENANCE.md 2026-09-17 节），本文件只"
                     "登记参数哈希。2026-09-13 恢复批同规则生成，260917 由 "
                     "tests/transform.py 再生成并逐字节核对。"),
        },
        "instances": {},
    }
    for name in names:
        code = official2code[name]
        src = os.path.join(args.instances_dir, name)
        with open(src, "rb") as f:
            plain = f.read()
        n, F, D = parse_dat(src)
        Fp, Dp, pi, sigma = transform_instance(name, n, F, D)
        out_plain = serialize(n, Fp, Dp)
        dst = os.path.join(args.out_dir, code)
        with open(dst, "wb") as f:
            f.write(out_plain)
        os.chmod(dst, 0o644)
        manifest["instances"][name] = {
            "codename": code,
            "seed": derive_seed(name),
            "n": n,
            "perm_facilities_new_from_old": pi,
            "perm_locations_new_from_old": sigma,
            "src_sha256_plain": hashlib.sha256(plain).hexdigest(),
            "out_sha256_plain": hashlib.sha256(out_plain).hexdigest(),
            "oracle_key": oracle_hash(out_plain),
        }
        newmap["instances"][code] = {
            "judged": True,
            "official": name,
            "src_sha256": hashlib.sha256(out_plain).hexdigest(),
            "official_sha256": hashlib.sha256(plain).hexdigest(),
            "transform_params_sha256": params_hash(pi, sigma),
        }
        print(f"[batch] {name} -> {code}: n={n}", flush=True)
    with open(args.manifest, "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
    os.chmod(args.manifest, 0o644)
    with open(args.map_out, "w") as f:
        json.dump(newmap, f, indent=1, sort_keys=True)
    os.chmod(args.map_out, 0o644)
    print(f"[batch] manifest（保密，仓外留档）: {args.manifest} "
          f"({len(manifest['instances'])} instances)")
    print(f"[batch] codename-map: {args.map_out}")


def cmd_verify(args):
    with open(args.manifest) as f:
        manifest = json.load(f)
    official2code = {rec["official"]: code
                     for code, rec in json.load(open(args.codename_map))["instances"].items()}
    n_ok = n_bad = 0
    for name, rec in sorted(manifest["instances"].items()):
        code = rec.get("codename") or official2code[name]
        n_o, F_o, D_o = parse_dat(os.path.join(args.orig_dir, name))
        n_t, F_t, D_t = parse_dat(os.path.join(args.trans_dir, code))
        pi = rec["perm_facilities_new_from_old"]
        sigma = rec["perm_locations_new_from_old"]
        problems = []
        n = rec["n"]
        if n_o != n or n_t != n:
            problems.append("dimension mismatch")
        if sorted(pi) != list(range(1, n + 1)):
            problems.append("facility permutation not a bijection")
        if sorted(sigma) != list(range(1, n + 1)):
            problems.append("location permutation not a bijection")
        if not problems:
            inv_pi = [0] * n
            inv_sigma = [0] * n
            for old in range(n):
                inv_pi[pi[old] - 1] = old
                inv_sigma[sigma[old] - 1] = old
            for a in range(n):
                for b in range(n):
                    if F_t[a][b] != F_o[inv_pi[a]][inv_pi[b]]:
                        problems.append(f"F[{a}][{b}] mismatch")
                        break
                    if D_t[a][b] != D_o[inv_sigma[a]][inv_sigma[b]]:
                        problems.append(f"D[{a}][{b}] mismatch")
                        break
                if problems:
                    break
            # 元素多重集（行/列同步置换保持整个矩阵的元素多重集）
            if sorted(v for row in F_t for v in row) != \
               sorted(v for row in F_o for v in row):
                problems.append("F element multiset differs")
            if sorted(v for row in D_t for v in row) != \
               sorted(v for row in D_o for v in row):
                problems.append("D element multiset differs")
            with open(os.path.join(args.orig_dir, name), "rb") as f:
                orig_bytes = f.read()
            with open(os.path.join(args.trans_dir, code), "rb") as f:
                if f.read() == orig_bytes:
                    problems.append("bytes unchanged")
        if problems:
            n_bad += 1
            print(f"[verify] {name} ({code}): FAIL {'; '.join(problems)}")
        else:
            n_ok += 1
    print(f"[verify] ok={n_ok} bad={n_bad}")
    return 1 if n_bad else 0


def cmd_bake_oracle(args):
    with open(args.manifest) as f:
        manifest = json.load(f)
    with open(os.path.join(args.orig_oracle, "manifest.json")) as f:
        om = json.load(f)
    with open(args.reference) as f:
        ref = json.load(f)["instances"]
    os.makedirs(args.out_dir, exist_ok=True)
    new_manifest = {}
    for name, rec in sorted(manifest["instances"].items()):
        code = rec["codename"]
        ent = None
        for _, e in om.items():
            if e["instance"] == name:
                ent = e
                break
        if ent is None:
            sys.exit(f"[bake-oracle] no original oracle entry for {name}")
        with open(os.path.join(args.orig_oracle, ent["perm"])) as f:
            perm1 = [int(x) for x in f.read().split()]
        newp = rewrite_perm(perm1, rec["perm_facilities_new_from_old"],
                            rec["perm_locations_new_from_old"])
        with open(os.path.join(args.out_dir, ent["perm"]), "w") as f:
            f.write(" ".join(str(x) for x in newp) + "\n")
        with open(os.path.join(args.trans_dir, code), "rb") as f:
            key = oracle_hash(f.read())
        if key != rec["oracle_key"]:
            sys.exit(f"[bake-oracle] oracle_key mismatch for {name}")
        new_manifest[key] = {"instance": name,
                             "codename": code,
                             "perm": ent["perm"],
                             "K": ref[name]["K"],
                             "interpretation": "rewritten-by-transform"}
    with open(os.path.join(args.out_dir, "manifest.json"), "w") as f:
        json.dump(new_manifest, f, indent=1, sort_keys=True)
    os.chmod(os.path.join(args.out_dir, "manifest.json"), 0o644)
    print(f"[bake-oracle] {len(new_manifest)} rewritten packs -> {args.out_dir}")


def cmd_verify_oracle(args):
    sys.path.insert(0, args.scoring_dir)
    import scoring  # the task's own scoring module (check_qap)
    with open(args.manifest) as f:
        manifest = json.load(f)
    with open(args.reference) as f:
        ref = json.load(f)["instances"]
    n_ok = n_bad = 0
    for name, rec in sorted(manifest["instances"].items()):
        code = rec["codename"]
        base = name[:-len(".dat")]
        sol_path = os.path.join(args.oracle_dir, base + ".perm")
        inst_path = os.path.join(args.trans_dir, code)
        cost, err = scoring.check_qap(inst_path, sol_path)
        K = ref[name]["K"] if name in ref else None
        if err is not None:
            n_bad += 1
            print(f"[verify-oracle] {code} ({name}): INVALID {err}")
        elif K is not None and cost != K:
            n_bad += 1
            print(f"[verify-oracle] {code} ({name}): cost {cost} != K {K}")
        else:
            n_ok += 1
            print(f"[verify-oracle] {code} ({name}): ok cost={cost}")
    print(f"[verify-oracle] ok={n_ok} bad={n_bad}")
    return 1 if n_bad else 0


def invert_instance(name, n, Ft, Dt):
    """正向变换的逆：F[x][y] = Ft[pi(x)][pi(y)]，D 同理（pi/sigma 由种子规则
    按官方名现场重导，与正向同一对）。返回 (F, D, pi, sigma)。"""
    rng = random.Random(derive_seed(name))
    pi = list(range(1, n + 1))
    rng.shuffle(pi)
    sigma = list(range(1, n + 1))
    rng.shuffle(sigma)
    F = [[Ft[pi[a] - 1][pi[b] - 1] for b in range(n)] for a in range(n)]
    D = [[Dt[sigma[a] - 1][sigma[b] - 1] for b in range(n)] for a in range(n)]
    return F, D, pi, sigma


def cmd_apply(args):
    n, F, D = parse_dat(args.apply)
    Fp, Dp, _, _ = transform_instance(args.name, n, F, D)
    with open(args.out, "wb") as f:
        f.write(serialize(n, Fp, Dp))
    print(f"[apply] {args.name}: n={n} -> {args.out}")


def cmd_invert(args):
    n, Ft, Dt = parse_dat(args.invert)
    F, D, _, _ = invert_instance(args.name, n, Ft, Dt)
    with open(args.out, "wb") as f:
        f.write(serialize(n, F, D))
    print(f"[invert] {args.name}: n={n} -> {args.out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", metavar="IN",
                    help="单实例正向变换：输入官方 .dat，--out 输出变换字节")
    ap.add_argument("--invert", metavar="IN",
                    help="单实例逆变换：输入变换后 .dat，--out 输出还原矩阵")
    ap.add_argument("--name", help="官方实例名（种子派生依据，如 bur26a.dat）")
    ap.add_argument("--out", help="--apply/--invert 的输出路径")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("batch")
    p.add_argument("--instances-dir", required=True,
                   help="官方实例目录（environment/app/instances）")
    p.add_argument("--out-dir", required=True,
                   help="变换后 exNNN.dat 输出目录（tests/instances）")
    p.add_argument("--manifest", required=True,
                   help="transform_manifest.json 输出路径（仓外保密路径）")
    p.add_argument("--codename-map", required=True,
                   help="既有 codename-map.json（沿用其 exNNN 分配）")
    p.add_argument("--map-out", required=True,
                   help="新 codename-map.json 输出路径")
    p.set_defaults(fn=cmd_batch)
    p = sub.add_parser("verify")
    p.add_argument("--orig-dir", required=True)
    p.add_argument("--trans-dir", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--codename-map", required=True)
    p.set_defaults(fn=cmd_verify)
    p = sub.add_parser("bake-oracle")
    p.add_argument("--orig-oracle", required=True,
                   help="官方排列源目录（tests/official-perms，含 manifest.json）")
    p.add_argument("--trans-dir", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--reference", required=True,
                   help="官方名键 reference.json（取 K）")
    p.add_argument("--out-dir", required=True)
    p.set_defaults(fn=cmd_bake_oracle)
    p = sub.add_parser("verify-oracle")
    p.add_argument("--oracle-dir", required=True)
    p.add_argument("--trans-dir", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--reference", required=True,
                   help="官方名键 reference.json（取 K）")
    p.add_argument("--scoring-dir", required=True)
    p.set_defaults(fn=cmd_verify_oracle)
    args = ap.parse_args()
    if args.apply or args.invert:
        if not args.name or not args.out:
            ap.error("--apply/--invert 需要 --name 与 --out")
        if args.apply and args.invert:
            ap.error("--apply 与 --invert 二选一")
        if args.apply:
            cmd_apply(args)
        else:
            cmd_invert(args)
        return
    if not args.cmd:
        ap.error("需要子命令（batch/verify/bake-oracle/verify-oracle）或 --apply/--invert")
    sys.exit(args.fn(args) or 0)


if __name__ == "__main__":
    main()
