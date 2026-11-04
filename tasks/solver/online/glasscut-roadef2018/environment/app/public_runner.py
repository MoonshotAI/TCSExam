"""Local public-instance runner for the glasscut-roadef2018 task.

This is a convenience runner for the agent's dev box only. It rebuilds via
/app/build.sh, runs the public practice instances (those listed in
/app/public_reference.json) under the official
ROADEF/EURO 2018 final-phase dual time limits (a 3-minute run and a 1-hour
run per instance), validates the cutting patterns, recomputes their waste,
and prints one line per instance: the two tiers' waste values, the
per-instance composite (the official 0.1/0.9 weighted value of the two
tiers), validity status, and seconds used. Nothing is aggregated across
instances.

This dev box is NOT the judging sandbox: core count, memory, and timing
behavior differ here, and limit enforcement differs too. Treat the results
of submit.sh (public practice channel) as authoritative.

The validity checker below re-implements the semantics of the official
ROADEF/EURO 2018 checker (checker.zip, version of 25/06/2018) in Python,
differentially tested against the official C++ binary (see
tests/calibration/). One deliberate deviation: blank lines and a trailing
newline are simply ignored here, while the original parser miscounts plate
node blocks on such files (undefined behaviour for multi-plate solutions).
The accepted format is a strict superset of what the official checker
validates: every solution the official checker accepts is accepted here
with the same objective value.

Instance = three files sharing a prefix <P>:
  <P>_batch.csv    ITEM_ID;LENGTH_ITEM;WIDTH_ITEM;STACK;SEQUENCE
  <P>_defects.csv  DEFECT_ID;PLATE_ID;X;Y;WIDTH;HEIGHT   (floats truncated
                   toward zero, exactly like the official checker's atoi)
  global_param.csv nPlates / widthPlates / heightPlates / min1Cut / max1Cut /
                   min2Cut / minWaste, in this order, one NAME;VALUE per line

Solution CSV (the solver's output), one header line then rows:
  PLATE_ID;NODE_ID;X;Y;WIDTH;HEIGHT;TYPE;CUT;PARENT

Objective per tier (minimize): OF = m*W*H - H*residual_width - sum(item
areas), identical to the official checker's "OF" (waste area, last plate's
residual discounted).

Time budget: PER-TIER hard limits — the solver is invoked twice per
instance, first with a 180 s limit, then with a 3600 s limit (wall clock,
OS-level hard kill). The solver learns the current run's limit via env
GLASSCUT_TIME_LIMIT on every run. Validity checking does not consume the
budget.
"""

import json
import os
import re
import signal
import subprocess
import sys
import time

BUILD_TIMEOUT = int(os.environ.get("BUILD_TIMEOUT", "600"))
# Official ROADEF 2018 final-phase tiers (Challenge_Rules.pdf §2.2): a
# 3-minute run and a 1-hour run per instance, composited 0.1/0.9.
TIER_SHORT_SECONDS = float(os.environ.get("TIER_SHORT_SECONDS", "180"))
TIER_LONG_SECONDS = float(os.environ.get("TIER_LONG_SECONDS", "3600"))
TIER_SHORT_WEIGHT_NUM = 1  # composite = (1 * V3 + 9 * V60) / 10
TIER_LONG_WEIGHT_NUM = 9
TIER_WEIGHT_DEN = 10

WASTE, BRANCH, RESIDUAL = -1, -2, -3


def atoi(s):
    """C atoi semantics: leading whitespace, optional sign, leading digits."""
    m = re.match(r"\s*([+-]?\d+)", s)
    return int(m.group(1)) if m else 0


# --------------------------------------------------------------------------
# parsing
# --------------------------------------------------------------------------

def read_rows(path):
    """CSV rows after the header; blank lines are ignored entirely."""
    rows = []
    with open(path, errors="replace") as f:
        lines = f.read().splitlines()
    for line in lines[1:]:
        if line.strip():
            rows.append(line.split(";"))
    return rows


def parse_global_param(path):
    vals = []
    for row in read_rows(path):
        vals.append(atoi(row[1]) if len(row) > 1 else 0)
    names = ["nPlates", "widthPlates", "heightPlates", "min1Cut", "max1Cut",
             "min2Cut", "minWaste"]
    if len(vals) < len(names):
        raise ValueError("global_param.csv has too few rows")
    p = dict(zip(names, vals[:len(names)]))
    if p["nPlates"] <= 0 or p["widthPlates"] <= 0 or p["heightPlates"] <= 0 \
            or p["min1Cut"] < 0 or p["max1Cut"] < 0 or p["min2Cut"] < 0 \
            or p["minWaste"] < 0:
        raise ValueError("global_param.csv has negative or null parameters")
    return p


def parse_batch(path):
    """Returns (items, stacks): items = list of dicts in file order;
    stacks = list of item-id lists (file order) in stack order."""
    items = []
    for row in read_rows(path):
        if len(row) < 5:
            raise ValueError(f"malformed batch row: {';'.join(row)!r}")
        it = {"id": atoi(row[0]), "h": atoi(row[1]), "w": atoi(row[2]),
              "stack": atoi(row[3]), "seq": atoi(row[4])}
        if it["id"] < 0 or it["stack"] < 0 or it["seq"] < 0 \
                or it["h"] <= 0 or it["w"] <= 0:
            raise ValueError("batch item with negative or null attribute")
        items.append(it)
    stacks = []
    by_id = {}
    for it in items:
        if it["stack"] not in by_id:
            by_id[it["stack"]] = len(stacks)
            stacks.append([])
        stacks[by_id[it["stack"]]].append(it["id"])
    return items, stacks


def parse_defects(path, n_plates):
    """Defects grouped by plate id. Mirrors the official checker: rows are
    scanned in file order and scanning STOPS at the first defect whose
    plate id is outside the used range; defects failing the
    negative/null check are a hard input error only before that point."""
    defects = [[] for _ in range(n_plates)]
    for row in read_rows(path):
        if len(row) < 6:
            raise ValueError(f"malformed defect row: {';'.join(row)!r}")
        pid = atoi(row[1])
        if pid < 0 or pid >= n_plates:
            break
        d = {"x": atoi(row[2]), "y": atoi(row[3]),
             "w": atoi(row[4]), "h": atoi(row[5])}
        if d["x"] < 0 or d["y"] < 0 or d["w"] <= 0 or d["h"] <= 0:
            raise ValueError("defect with negative or null attribute")
        defects[pid].append(d)
    return defects


class SolError(Exception):
    pass


def parse_solution(sol_path, params):
    """Parse the solution CSV. Returns (plates, residual_or_None).

    plates: list of plates; each plate is a dict with its root children;
    every node is a dict {id, x, y, w, h, type, cut, children}.
    Raises SolError on any structural (PARSE-level) violation.
    """
    rows = read_rows(sol_path)
    plates = []
    flat = []  # all node rows in file order
    for idx, row in enumerate(rows):
        if len(row) < 9:
            row = row + [""] * (9 - len(row))
        if row[1].strip() == "":
            continue  # row without NODE_ID: ignored
        if atoi(row[1]) != idx:
            raise SolError(
                f"node id violation: row {idx} claims NODE_ID {row[1]!r}")
        plate_id, x, y = atoi(row[0]), atoi(row[2]), atoi(row[3])
        w, h, ntype, cut = atoi(row[4]), atoi(row[5]), atoi(row[6]), atoi(row[7])
        parent = row[8].strip()
        if parent == "":
            # plate row
            if plate_id != len(plates):
                raise SolError(
                    f"plate utilization sequence violated: plate {plate_id} "
                    f"used when plate {len(plates)} is expected")
            if w != params["widthPlates"] or h != params["heightPlates"]:
                raise SolError(f"plate {plate_id}: dimensions differ from "
                               "global parameters")
            if x < 0 or y < 0 or w <= 0 or h <= 0 or cut < 0:
                raise SolError(f"plate {plate_id}: negative or null attribute")
            plates.append({"id": atoi(row[1]), "plate_id": plate_id,
                           "x": x, "y": y, "w": w, "h": h,
                           "type": ntype, "cut": cut, "children": []})
        else:
            if plate_id != len(plates) - 1:
                raise SolError(
                    f"node {idx}: rows of plate {plate_id} are not "
                    "contiguous / plate row missing")
            if x < 0 or y < 0 or w <= 0 or h <= 0 or cut < 0:
                raise SolError(f"node {idx}: negative or null attribute")
            flat.append({"id": atoi(row[1]), "plate_id": plate_id,
                         "x": x, "y": y, "w": w, "h": h, "type": ntype,
                         "cut": cut, "parent": atoi(parent), "children": []})
    if not plates:
        raise SolError("solution has no plate row")
    if len(plates) > params["nPlates"]:
        raise SolError(f"solution uses {len(plates)} plates, limit is "
                       f"{params['nPlates']}")

    # Build the trees. Parents must appear before children inside each
    # plate's row block (the official checker scans forward only).
    by_id = {}
    for node in flat:
        by_id[node["id"]] = node
    max_cut = 0
    n_residual_declared = 0
    for node in flat:
        max_cut = max(max_cut, node["cut"])
        par = by_id.get(node["parent"])
        if par is None:
            # parent may be the plate row itself
            pl = plates[node["plate_id"]]
            if node["parent"] != pl["id"]:
                raise SolError(f"node {node['id']}: unknown parent "
                               f"{node['parent']}")
            par = pl
        if node["type"] == RESIDUAL:
            n_residual_declared += 1
            if par is not plates[node["plate_id"]]:
                raise SolError(f"node {node['id']}: residual must be a "
                               "1-cut child of its plate")
        par["children"].append(node)
        if par is not plates[node["plate_id"]]:
            if par["type"] != BRANCH:
                raise SolError(f"node {node['id']}: child of a non-branch "
                               "node")
            if par["cut"] > 2 and len(par["children"]) > 2:
                raise SolError(f"node {par['id']}: {par['cut']}-cut branch "
                               "with more than 2 successors")
    if max_cut > 4:
        raise SolError(f"solution has {max_cut} cut stages, max is 4")

    # Residual handling: at most one; it must sit on the last used plate as
    # the last row of the plate's block; a waste in that position is
    # reclassified as the residual (official checker behaviour).
    if n_residual_declared > 1:
        raise SolError("solution has more than one residual")
    last = plates[-1]
    residual = None
    tail = flat_tail(last, flat)
    # A waste that is the last row of the last plate's block AND a direct
    # child of the plate is reclassified as the residual (official
    # behaviour); a waste in that position but inside a branch stays waste.
    if tail is not None and tail["type"] == WASTE \
            and tail["parent"] == last["id"]:
        residual = tail
    if n_residual_declared:
        node = [n for n in flat if n["type"] == RESIDUAL][0]
        if node["plate_id"] != len(plates) - 1:
            raise SolError("residual must be located on the last used plate")
        if node is not tail:
            raise SolError("residual must be the rightmost node of the last "
                           "plate")
        if residual is not None:
            raise SolError("solution has more than one residual")
        residual = node
    return plates, residual


def flat_tail(plate, flat):
    """Last node row of the plate's block in file order."""
    tail = None
    for node in flat:
        if node["plate_id"] == plate["plate_id"]:
            tail = node
    return tail


# --------------------------------------------------------------------------
# constraint verification (mirrors the official checker)
# --------------------------------------------------------------------------

def iter_leaves(node):
    if not node["children"]:
        yield node
    for c in node["children"]:
        yield from iter_leaves(c)


def iter_items(plates):
    """Useful (item) nodes in DFS pre-order, children in file order -
    the order the official checker collects sol_items."""
    for pl in plates:
        yield from _iter_items_node(pl)


def _iter_items_node(node):
    for c in node["children"]:
        if c["type"] >= 0:
            yield c
        elif c["type"] == BRANCH:
            yield from _iter_items_node(c)


def verify_item_production(batch_items, plates):
    count = {}
    for node in iter_items(plates):
        count[node["type"]] = count.get(node["type"], 0) + 1
    for it in batch_items:
        if count.get(it["id"], 0) > 1:
            return f"item {it['id']} is duplicated"
        if count.get(it["id"], 0) == 0:
            return f"item {it['id']} is not produced"
    extra = [t for t in count if t not in {it["id"] for it in batch_items}]
    if extra:
        return f"solution produces unknown item id {extra[0]}"
    return None


def verify_defects(defects, plates):
    for pid, pl in enumerate(plates):
        if not pl["children"] or not defects[pid]:
            continue
        n_overlap = 0
        for leaf in iter_leaves(pl):
            for d in defects[pid]:
                if (leaf["x"] < d["x"] + d["w"] and d["x"] < leaf["x"] + leaf["w"]
                        and leaf["y"] < d["y"] + d["h"]
                        and d["y"] < leaf["y"] + leaf["h"]):
                    n_overlap += 1
                    if not (leaf["x"] <= d["x"]
                            and d["x"] + d["w"] <= leaf["x"] + leaf["w"]
                            and leaf["y"] <= d["y"]
                            and d["y"] + d["h"] <= leaf["y"] + leaf["h"]):
                        return ("a cut goes through a defect on plate "
                                f"{pid} (defect not contained in one leaf)")
        if n_overlap != len(defects[pid]):
            return (f"a cut goes through a defect on plate {pid} "
                    "(defect not covered by exactly one leaf)")
    for node in iter_items(plates):
        for d in defects[node["plate_id"]]:
            if (node["x"] < d["x"] + d["w"] and d["x"] < node["x"] + node["w"]
                    and node["y"] < d["y"] + d["h"]
                    and d["y"] < node["y"] + node["h"]):
                return f"item node {node['id']} overlaps a defect"
    return None


def verify_idt_sequence(batch_items, stacks, plates):
    by_id = {it["id"]: it for it in batch_items}
    pos = [0] * len(stacks)
    idty = None
    for node in iter_items(plates):
        found = False
        for si, stack in enumerate(stacks):
            if pos[si] < len(stack) and node["type"] == stack[pos[si]]:
                found = True
                pos[si] += 1
                it = by_id[node["type"]]
                if not ((node["h"] == it["h"] and node["w"] == it["w"])
                        or (node["h"] == it["w"] and node["w"] == it["h"])):
                    idty = (f"item {node['type']} dimensions "
                            f"{node['w']}x{node['h']} differ from batch "
                            f"{it['w']}x{it['h']}")
                break
        if not found:
            return f"sequence constraint violated: item {node['type']} is " \
                   "not the next item of its stack"
    return idty


def verify_dimensions(params, plates, residual):
    for pl in plates:
        err = _check_children(params, pl, pl["children"], plate_level=True)
        if err:
            return err
        for c in pl["children"]:
            if c["type"] == BRANCH:
                err = _check_succ(params, c)
                if err:
                    return err
    if residual is not None and residual["w"] < params["minWaste"]:
        return f"residual width {residual['w']} less than minWaste"
    return None


def _check_children(params, parent, children, plate_level):
    """Tiling + parameter checks shared by the plate level and, via
    _check_succ, all branch levels."""
    pcut = parent["cut"]
    for j, c in enumerate(children):
        if c["cut"] != pcut + 1:
            return f"node {c['id']}: cut != parent cut + 1"
        if c["type"] == WASTE and (c["h"] < params["minWaste"]
                                   or c["w"] < params["minWaste"]):
            return f"waste node {c['id']} smaller than minWaste"
        if plate_level and c["type"] == BRANCH:
            if c["w"] < params["min1Cut"]:
                return f"node {c['id']}: 1-cut width less than min1Cut"
            if c["w"] > params["max1Cut"]:
                return f"node {c['id']}: 1-cut width greater than max1Cut"
        if (not plate_level) and c["cut"] == 2 and c["type"] == BRANCH \
                and c["h"] < params["min2Cut"]:
            return f"node {c['id']}: 2-cut height less than min2Cut"
        odd = c["cut"] % 2 == 1
        if odd:  # vertical strips along x
            if c["y"] != parent["y"] or c["h"] != parent["h"]:
                return f"node {c['id']}: y/height differ from parent"
            if j == 0 and c["x"] != parent["x"]:
                return f"node {c['id']}: first child x != parent x"
            if j > 0 and c["x"] != children[j - 1]["x"] + children[j - 1]["w"]:
                return f"node {c['id']}: x != previous sibling x + width"
            if c["x"] + c["w"] > parent["x"] + parent["w"]:
                return f"node {c['id']}: overflows parent on the right"
            if j == len(children) - 1 \
                    and c["x"] + c["w"] < parent["x"] + parent["w"]:
                return f"node {c['id']}: last child does not reach the " \
                       "parent's right edge"
        else:  # horizontal strips along y
            if c["x"] != parent["x"] or c["w"] != parent["w"]:
                return f"node {c['id']}: x/width differ from parent"
            if j == 0 and c["y"] != parent["y"]:
                return f"node {c['id']}: first child y != parent y"
            if j > 0 and c["y"] != children[j - 1]["y"] + children[j - 1]["h"]:
                return f"node {c['id']}: y != previous sibling y + height"
            if c["y"] + c["h"] > parent["y"] + parent["h"]:
                return f"node {c['id']}: overflows parent at the bottom"
            if j == len(children) - 1 \
                    and c["y"] + c["h"] < parent["y"] + parent["h"]:
                return f"node {c['id']}: last child does not reach the " \
                       "parent's bottom edge"
    return None


def _check_succ(params, parent):
    err = _check_children(params, parent, parent["children"],
                          plate_level=False)
    if err:
        return err
    for c in parent["children"]:
        if c["type"] == BRANCH:
            err = _check_succ(params, c)
            if err:
                return err
    return None


def check_solution(inst_prefix, sol_path):
    """Full validity check + objective value. Returns (of, None) iff valid;
    otherwise (None, reason). inst_prefix: path without _batch.csv suffix."""
    try:
        params = parse_global_param(
            os.path.join(os.path.dirname(inst_prefix), "global_param.csv"))
        batch_items, stacks = parse_batch(inst_prefix + "_batch.csv")
        # plates count is needed to scope defects; parse the solution first
        # for the plate count, but defects only for used plates.
        try:
            plates, residual = parse_solution(sol_path, params)
        except SolError as e:
            return None, str(e)
        defects = parse_defects(inst_prefix + "_defects.csv", len(plates))
    except (ValueError, OSError) as e:
        return None, f"could not load inputs: {e}"

    for check in (lambda: verify_item_production(batch_items, plates),
                  lambda: verify_defects(defects, plates),
                  lambda: verify_idt_sequence(batch_items, stacks, plates),
                  lambda: verify_dimensions(params, plates, residual)):
        err = check()
        if err:
            return None, err

    of = len(plates) * params["widthPlates"] * params["heightPlates"]
    if residual is not None:
        of -= params["heightPlates"] * residual["w"]
    for it in batch_items:
        of -= it["h"] * it["w"]
    return of, None


# --------------------------------------------------------------------------
# build / run / evaluate
# --------------------------------------------------------------------------

def build_solver(app_dir, timeout=BUILD_TIMEOUT):
    """Run the agent-visible build script; require /app/solver afterwards."""
    script = os.path.join(app_dir, "build.sh")
    if not os.path.exists(script):
        return None, "no /app/build.sh found"
    try:
        p = subprocess.run(
            ["bash", script], cwd=app_dir, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return None, f"build.sh timed out after {timeout}s"
    solver = os.path.join(app_dir, "solver")
    if not (os.path.exists(solver) and os.access(solver, os.X_OK)):
        tail = ((p.stdout or "") + (p.stderr or ""))[-3000:]
        return None, (f"build.sh finished (exit {p.returncode}) but did not "
                      f"produce an executable /app/solver\n{tail}")
    return solver, None


def run_solver(solver, inst_prefix, out_path, limit_seconds):
    """Run solver <inst_prefix> <out_path> with a hard timeout of
    limit_seconds (one tier). The solver learns this run's limit via env
    GLASSCUT_TIME_LIMIT. Returns (seconds, None) on success,
    (seconds, reason) otherwise."""
    env = dict(os.environ)
    env["GLASSCUT_TIME_LIMIT"] = f"{limit_seconds:.3f}"
    t0 = time.time()
    with open(os.devnull, "w") as devnull:
        p = subprocess.Popen(
            [solver, inst_prefix, out_path], stdin=subprocess.DEVNULL,
            stdout=devnull, stderr=devnull, env=env, start_new_session=True,
        )
        try:
            p.wait(timeout=limit_seconds)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait()
            return time.time() - t0, f"timeout after {limit_seconds:g}s"
    seconds = time.time() - t0
    if p.returncode != 0:
        return seconds, f"solver exited with code {p.returncode}"
    if not os.path.exists(out_path):
        return seconds, "solver produced no output file"
    return seconds, None


def run_tier(solver, inst_prefix, out_path, limit_seconds):
    """One tier: run the solver under the tier limit, then validate the
    pattern with the real checker. Returns
    (value_or_None, status_label, seconds)."""
    seconds, err = run_solver(solver, inst_prefix, out_path, limit_seconds)
    if err is not None:
        return None, err, seconds
    of, cerr = check_solution(inst_prefix, out_path)
    if cerr is not None:
        return None, f"invalid solution ({cerr})", seconds
    return of, "ok", seconds


def main(argv):
    if len(argv) != 4:
        print(f"usage: {argv[0]} APP_DIR INSTANCES_DIR REFERENCE_JSON",
              file=sys.stderr)
        return 2
    app_dir, instances_dir, ref_path = argv[1], argv[2], argv[3]
    # The public practice set is defined by the reference file's keys
    # (the same set submit.sh's public channel judges).
    with open(ref_path) as f:
        reference = json.load(f)["instances"]
    names = sorted(reference)
    work_dir = os.path.join("/tmp", f"glasscut-run-{os.getpid()}")
    os.makedirs(work_dir, exist_ok=True)

    solver, err = build_solver(app_dir)
    if err:
        print(f"BUILD FAILED: {err}", file=sys.stderr)
        return 1

    for name in names:
        inst_prefix = os.path.join(instances_dir, name)
        out_short = os.path.join(work_dir, name + "_solution_3min.csv")
        out_long = os.path.join(work_dir, name + "_solution_1hour.csv")
        a_short, st_short, sec_short = run_tier(
            solver, inst_prefix, out_short, TIER_SHORT_SECONDS)
        a_long, st_long, sec_long = run_tier(
            solver, inst_prefix, out_long, TIER_LONG_SECONDS)
        if a_short is not None and a_long is not None:
            comp = ((TIER_SHORT_WEIGHT_NUM * a_short
                     + TIER_LONG_WEIGHT_NUM * a_long) / TIER_WEIGHT_DEN)
            comp_s = f"{comp:.1f}"
        elif reference[name].get("practice_no_anchors") is True:
            comp_s = "- (tier failed; no baseline fallback on a practice key)"
        else:
            comp_s = "- (tier failed; at judging the official fallback "
            comp_s += "applies)"
        t3 = f"A={a_short}" if a_short is not None else "A=-"
        t60 = f"A={a_long}" if a_long is not None else "A=-"
        print(f"{name}\t3min: {t3} [{st_short}] ({sec_short:.2f}s)"
              f"\t1hour: {t60} [{st_long}] ({sec_long:.2f}s)"
              f"\tcomposite A={comp_s}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
