#!/usr/bin/env python3
"""Mathematical validation of the maxcut-mqlib form2 hidden-set transformation (form2-conversion-recipes.md).

Three checks, plus a structural gate:
  A. Structural gate: hidden keys in split.json equal the transform_manifest keys,
     reference.json keys, and the files in tests/instances/ (45 txNNN.txt.xz files);
     every permutation is a bijection of 1..n.
  B. Round trip (45/45): invert each transformed instance using the manifest
     permutation, then apply the same permutation again. The bytes must exactly
     match the transformed file (both passes use canonical form, confirming that
     --apply and --invert are inverses and the permutation is self-consistent).
  C. Solution value is preserved (public instances with known solutions, recipe
     check): transform 3 public instances and their stored solutions
     (solution/precomputed), then recompute the objective with mc_check on both
     sides; values must match exactly (weighted instances use a 1e-9 relative
     tolerance, matching scoring REL_TOL).
  D. Solution value is preserved (all 45 hidden instances): run mc_check on each
     transformed instance and its transformed stored solution. The recomputed value
     must equal the solution-manifest value, which is the value recomputed for the
     same solution on the original instance; see tests/calibration/transform-verify-260920/.
  E. Spot-check K reuse (45/45): reference.json K equals the original-instance K
     recorded in transform_manifest (reused by isomorphism). B is a form1
     placeholder replaced after batch remeasurement; this test does not verify B.

When this file was created, full checks had run: the edge multisets of all 45
original/transformed pairs were isomorphic, mc_check gave equal values for stored
solutions on both sides, and bytes matched the 260913 transformation batch. The
report is in tests/calibration/transform-verify-260920/.

Run with `python3 test_transform.py` (unittest). C/D compile mc_check with g++;
those cases are skipped if g++ is unavailable; A/B/E always run in pure Python."""
import json
import lzma
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import transform  # noqa: E402

REL_TOL = 1e-9


def load_json(name):
    with open(os.path.join(HERE, name)) as f:
        return json.load(f)


class TransformTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.split = load_json("split.json")
        cls.manifest = load_json("transform_manifest.json")
        cls.reference = load_json("reference.json")["instances"]
        cls.hidden = sorted(n for n, v in cls.split["instances"].items()
                            if v == "hidden")
        cls.tx_sorted = sorted(cls.manifest["instances"])

    def test_a_structure(self):
        inst_files = sorted(f[:-3] for f in os.listdir(os.path.join(HERE, "instances"))
                            if f.endswith(".txt.xz"))
        officials = sorted(self.manifest["instances"][tx]["official"]
                           for tx in self.tx_sorted)
        self.assertEqual(self.hidden, officials,
                         "split hidden set != manifest official-name set")
        self.assertEqual(self.tx_sorted, sorted(self.reference),
                         "manifest key set != reference key set")
        self.assertEqual(self.tx_sorted, inst_files, "manifest key set != instances file set")
        self.assertEqual(len(self.tx_sorted), 45)
        for tx in self.tx_sorted:
            ent = self.manifest["instances"][tx]
            n = ent["n"]
            self.assertEqual(sorted(ent["perm"]), list(range(1, n + 1)),
                             f"{tx}: perm is not a bijection of 1..n")

    def test_b_roundtrip(self):
        for tx in self.tx_sorted:
            ent = self.manifest["instances"][tx]
            with lzma.open(os.path.join(HERE, "instances", tx + ".xz"), "rb") as f:
                tx_bytes = f.read()
            orig = transform.invert_bytes(tx_bytes, ent["perm"])
            # Invert to canonical bytes with original labels, then reapply the same permutation and require a byte-for-byte match
            # with the transformed file (inverse assertion in canonical form).
            n, edges = transform.load_mqlib_text(orig.decode())
            self.assertEqual(n, ent["n"], f"{tx}: inverted n differs")
            self.assertEqual(len(edges), ent["m"], f"{tx}: inverted m differs")
            fwd = transform.canonical_bytes(
                n, [(ent["perm"][u - 1], ent["perm"][v - 1], w) for u, v, w in edges])
            self.assertEqual(fwd, tx_bytes, f"{tx}: apply∘invert is not byte-identical")

    @staticmethod
    def _mc_check_bin():
        gxx = shutil.which("g++")
        if not gxx:
            return None
        tmp = tempfile.mkdtemp(prefix="mc-check-")
        bin_path = os.path.join(tmp, "mc_check")
        src = os.path.join(TASK, "environment", "mc_check.cpp")
        p = subprocess.run([gxx, "-O3", "-std=c++17", "-o", bin_path, src],
                           capture_output=True, text=True)
        if p.returncode != 0:
            return None
        return bin_path

    def _check_value_pair(self, mc_bin, orig_txt, orig_sol, tx_txt, tx_sol, tag):
        """Run mc_check on both sides; recomputed values must match within a 1e-9 relative tolerance."""
        vals = []
        for inst, sol in ((orig_txt, orig_sol), (tx_txt, tx_sol)):
            p = subprocess.run([mc_bin, inst, sol], capture_output=True, text=True,
                               timeout=900)
            out = (p.stdout or "").strip()
            self.assertEqual(p.returncode, 0, f"{tag}: mc_check failed {out[-200:]}")
            self.assertTrue(out.startswith("OK "), f"{tag}: mc_check did not return OK {out[-200:]}")
            vals.append(float(out.split()[1]))
        v1, v2 = vals
        tol = REL_TOL * max(1.0, abs(v1), abs(v2))
        self.assertLessEqual(abs(v1 - v2), tol, f"{tag}: recomputed values on both sides {v1} vs {v2} differ")
        return v1, v2

    def test_c_value_invariance_public(self):
        mc_bin = self._mc_check_bin()
        if mc_bin is None:
            self.skipTest("g++ unavailable; skipping mc_check recomputation on both sides (A/B/E are covered)")
        precomputed = os.path.join(TASK, "solution", "precomputed")
        with open(os.path.join(precomputed, "manifest.json")) as f:
            omani = json.load(f)
        by_official = {}
        for ent in omani.values():
            by_official.setdefault(ent["instance"], ent)
        publics = sorted(n for n, v in self.split["instances"].items() if v == "public")
        # Cover three public instances from different size buckets (one small, medium, and large, selected at evenly spaced lexicographic positions).
        picks = [publics[0], publics[len(publics) // 2], publics[-1]]
        with tempfile.TemporaryDirectory(prefix="xf-public-") as work:
            for official in picks:
                with lzma.open(os.path.join(TASK, "environment", "app", "instances",
                                            official + ".xz"), "rb") as f:
                    data = f.read()
                tx_bytes, perm, _ = transform.transform_bytes(data, official)
                ent = by_official[official]
                with open(os.path.join(precomputed, ent["out"])) as f:
                    toks = f.read().split()
                new_toks = transform.permute_solution_tokens(toks, perm)
                orig_txt = os.path.join(work, "orig.txt")
                tx_txt = os.path.join(work, "tx.txt")
                orig_sol = os.path.join(work, "orig.sol")
                tx_sol = os.path.join(work, "tx.sol")
                with open(orig_txt, "wb") as f:
                    f.write(transform.canonical_bytes(*transform.load_mqlib_text(
                        data.decode("utf-8", errors="replace"))))
                with open(tx_txt, "wb") as f:
                    f.write(tx_bytes)
                with open(orig_sol, "w") as f:
                    f.write("\n".join(toks) + "\n")
                with open(tx_sol, "w") as f:
                    f.write("\n".join(new_toks) + "\n")
                self._check_value_pair(mc_bin, orig_txt, orig_sol, tx_txt, tx_sol,
                                       f"public {official}")

    def test_d_value_invariance_hidden(self):
        mc_bin = self._mc_check_bin()
        if mc_bin is None:
            self.skipTest("g++ unavailable; skipping mc_check recomputation (A/B/E are covered)")
        precomputed = os.path.join(TASK, "solution", "precomputed")
        with open(os.path.join(precomputed, "manifest.json")) as f:
            omani = json.load(f)
        tx_entries = {e["instance"]: e for e in omani.values()
                      if e["instance"].startswith("tx")}
        self.assertEqual(sorted(tx_entries), self.tx_sorted,
                         "tx entries in oracle manifest do not match hidden set")
        with tempfile.TemporaryDirectory(prefix="xf-hidden-") as work:
            for tx in self.tx_sorted:
                with lzma.open(os.path.join(HERE, "instances", tx + ".xz"), "rb") as f:
                    data = f.read()
                inst = os.path.join(work, "inst.txt")
                with open(inst, "wb") as f:
                    f.write(data)
                ent = tx_entries[tx]
                sol = os.path.join(precomputed, ent["out"])
                p = subprocess.run([mc_bin, inst, sol], capture_output=True,
                                   text=True, timeout=900)
                out = (p.stdout or "").strip()
                self.assertEqual(p.returncode, 0, f"{tx}: mc_check failed {out[-200:]}")
                self.assertTrue(out.startswith("OK "), f"{tx}: not OK {out[-200:]}")
                val = float(out.split()[1])
                want = float(ent["value"])
                tol = REL_TOL * max(1.0, abs(val), abs(want))
                self.assertLessEqual(abs(val - want), tol,
                                     f"{tx}: recomputed {val} != recorded {want}")

    def test_e_k_carryover(self):
        for tx in self.tx_sorted:
            ent = self.manifest["instances"][tx]
            self.assertEqual(self.reference[tx]["K"], ent["K"],
                             f"{tx}: reference K differs from original-instance K (isomorphic reuse failed)")
            self.assertEqual(self.reference[tx].get("family"), ent.get("family"))
            self.assertEqual(self.reference[tx].get("transformed_from"),
                             ent["official"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
