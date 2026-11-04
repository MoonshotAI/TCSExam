#!/usr/bin/env python3
"""Structure-preserving transformation for the tsp-tsplib form2 hidden set (city relabeling; exact isomorphism).

Transformation definition (TSP recipe in form2-conversion-recipes.md):
  Apply a random city permutation π. For coordinate-based instances, relabel cities while leaving coordinate values
  unchanged (reorder and relabel NODE_COORD_SECTION rows according to π). For EXPLICIT matrix instances,
  permute matrix rows and columns together according to π and emit them using the original EDGE_WEIGHT_FORMAT. Every pairwise city
  distance is preserved, so the transformed instance is isomorphic to the official one: the optimum and best-known value are unchanged (reuse K by isomorphism),
  and every tour has the same length. Remeasure B on the transformed instance because the baseline heuristic trajectory depends on city
  labels. Discard non-weight sections such as DISPLAY_DATA/TOUR (the judging-side tsplib.h ignores them anyway);
  preserve header lines byte for byte.

Seed rule (same as the 2026-08-31 codename-transformation batch):
    h    = uint64-be(sha256(official_name)[:8])
    seed = (20260831 * h) mod 2^64
    old_of_new = Random(seed).shuffle([1..n]); old_of_new[j-1] is the original city ID assigned the new
    city ID j.
The complete permutation table is recorded in transform_manifest.json in this directory (stored only under tests/, together with the
mapping from official names to transformed names txNNN). Validation and oracle rewriting do not depend on replaying the RNG.

Naming: hidden judged instances use new filenames txNNN.tsp (reference key txNNN without an extension, matching the scoring
pipeline convention name + ".tsp"; assign txNNN codes in lexicographic order of official names).

Usage:
    transform.py --apply OFFICIAL_TSP_DIR OUT_DIR MANIFEST_JSON [official_name ...]
        Transform <official>.tsp from OFFICIAL_TSP_DIR into
        txNNN.tsp under OUT_DIR, and write or merge the manifest.
    transform.py --invert TX_TSP MANIFEST_JSON OUT_TSP
        Use the manifest permutation table to invert the transformed instance back to the original IDs (preserve the header byte for byte and restore
        the coordinate rows/matrix in original ID order). Discarded non-weight sections cannot be recovered; the instances are semantically equivalent.
        See the round-trip assertion in test_transform.py.
"""
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
    """Parse a TSPLIB file using the judging-side tsplib.h conventions. Return a dict containing the header lines verbatim,
    the weight-section name, and parsed content (coordinate tokens keyed by original ID, or a 1-based full matrix)."""
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


def derive_seed(name, master_seed=MASTER_SEED):
    h = int.from_bytes(hashlib.sha256(name.encode("utf-8")).digest()[:8], "big")
    return (master_seed * h) % (1 << 64)


def make_permutation(n, seed):
    ids = list(range(1, n + 1))
    random.Random(seed).shuffle(ids)
    return ids  # old_of_new: index j-1 -> original city ID assigned new label j


def emit_instance(inst, id_order, comment_note=None):
    """Emit instance text in id_order (new ID j -> original ID), preserving the header verbatim and writing the weight section."""
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


def transform_file(path, official_name):
    """Transform one instance file. Return (new_bytes, entry)."""
    inst = parse_instance(path)
    seed = derive_seed(official_name)
    old_of_new = make_permutation(inst["n"], seed)
    data = emit_instance(inst, old_of_new)
    entry = {
        "n": inst["n"],
        "edge_weight_type": inst["edge_weight_type"],
        "edge_weight_format": inst["edge_weight_format"] or None,
        "seed": seed,
        "sha256_orig": hashlib.sha256(inst["raw"]).hexdigest(),
        "sha256_new": hashlib.sha256(data).hexdigest(),
        "old_of_new": old_of_new,
    }
    return data, entry


def invert_file(tx_path, old_of_new):
    """Invert using the permutation table: take a transformed file and return emitted text with the original IDs."""
    inst = parse_instance(tx_path)
    n = inst["n"]
    if sorted(old_of_new) != list(range(1, n + 1)):
        raise ValueError("old_of_new is not a bijection of 1..n")
    new_of_old = [0] * (n + 1)  # new_of_old[v] = new label of original ID v
    for j in range(1, n + 1):
        new_of_old[old_of_new[j - 1]] = j
    # To invert, emit using the sequence "new ID j -> original ID old_of_new[j-1]" as id_order:
    # Row v in the output uses the coordinates/matrix row for original ID v.
    if inst["edge_weight_type"] in COORD_TYPES:
        # inst["coords"][j] is the coordinate of new ID j (= the coordinate of original old_of_new[j-1]);
        # after inversion, row v must contain the coordinates = inst["coords"][new_of_old[v]]
        inv_coords = [None] * (n + 1)
        for v in range(1, n + 1):
            inv_coords[v] = inst["coords"][new_of_old[v]]
        inst["coords"] = inv_coords
        return emit_instance(inst, list(range(1, n + 1)))
    # Matrix: pm[j][k] = mat[old_of_new[j-1]][old_of_new[k-1]]; invert by applying the inverse permutation.
    inv_mat = [[0] * (n + 1) for _ in range(n + 1)]
    for v in range(1, n + 1):
        for w in range(1, n + 1):
            inv_mat[v][w] = inst["matrix"][new_of_old[v]][new_of_old[w]]
    inst["matrix"] = inv_mat
    return emit_instance(inst, list(range(1, n + 1)))


def permute_tour_tokens(tokens, old_of_new):
    """Transform a tour solution consistently: relabel the city-ID sequence according to π. tokens are the city IDs from the tour file,
    as a list of 1-based tokens from TOUR_SECTION city rows; the caller must pass only
    city IDs. Return the token list with new IDs."""
    n = len(old_of_new)
    new_of_old = [0] * (n + 1)
    for j in range(1, n + 1):
        new_of_old[old_of_new[j - 1]] = j
    out = []
    for tok in tokens:
        v = int(tok)
        if v == -1:  # Keep the TSPLIB TOUR end marker unchanged
            out.append(tok)
            continue
        if v < 1 or v > n:
            raise ValueError(f"tour city {v} out of range 1..{n}")
        out.append(str(new_of_old[v]))
    return out


def cmd_apply(argv):
    if len(argv) < 4:
        print(f"usage: {argv[0]} --apply OFFICIAL_TSP_DIR OUT_DIR MANIFEST_JSON "
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
        "master_seed": MASTER_SEED,
        "seed_derivation": ("h = uint64-be(sha256(official_name)[:8]); "
                            "seed = (master_seed * h) mod 2^64; old_of_new = "
                            "Random(seed).shuffle([1..n]); old_of_new[j-1] = "
                            "original city id that receives new id j"),
        "name_note": ("txNNN assigned in sorted(official) order; official -> txNNN "
                      "mapping lives ONLY in this tests-side manifest"),
        "instances": {},
    }
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            manifest = json.load(f)
        manifest.setdefault("instances", {})
    officials = sorted(names)
    for i, official in enumerate(officials, start=1):
        tx = f"tx{i:03d}"
        data, entry = transform_file(os.path.join(in_dir, official + ".tsp"),
                                     official)
        with open(os.path.join(out_dir, tx + ".tsp"), "wb") as f:
            f.write(data)
        entry["official"] = official
        manifest["instances"][tx] = entry
        print(f"  {official} -> {tx}: n={entry['n']} "
              f"type={entry['edge_weight_type']}"
              f"{'/' + entry['edge_weight_format'] if entry['edge_weight_format'] else ''}",
              flush=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
    print(f"transformed {len(officials)} instance(s) -> {out_dir}")
    print(f"manifest -> {manifest_path}")
    return 0


def cmd_invert(argv):
    if len(argv) != 5:
        print(f"usage: {argv[0]} --invert TX_TSP MANIFEST_JSON OUT_TSP",
              file=sys.stderr)
        return 2
    tx_tsp, manifest_path, out_tsp = argv[2:5]
    with open(manifest_path) as f:
        manifest = json.load(f)
    tx = os.path.basename(tx_tsp)
    if tx.endswith(".tsp"):
        tx = tx[:-4]
    ent = manifest["instances"].get(tx)
    if ent is None:
        print(f"{argv[0]}: {tx} not in manifest", file=sys.stderr)
        return 1
    data = invert_file(tx_tsp, ent["old_of_new"])
    with open(out_tsp, "wb") as f:
        f.write(data)
    print(f"inverted {tx} (official {ent['official']}) -> {out_tsp}")
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
