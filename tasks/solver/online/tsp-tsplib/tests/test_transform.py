#!/usr/bin/env python3
"""Mathematical validation of the tsp-tsplib form2 hidden-set transformation (form2-conversion-recipes.md).

Three checks, plus a structural gate:
  A. Structural gate: the hidden official names in split.json equal the official-name
     set in transform_manifest; manifest keys equal reference.json keys and the
     tests/instances file set (33 txNNN.tsp files; reference keys are txNNN without
     the extension); every permutation is a bijection of 1..n.
  B. Round trip (33/33): invert each transformed instance using the manifest
     permutation, then apply the same permutation again. The bytes must exactly
     match the transformed file (an inverse assertion along the same emission path).
  C. Solution value is preserved (public instances with known tours, recipe check):
     transform 3 public instances and their stored tours (solution/precomputed),
     relabel the tour's city IDs, and recompute both tour lengths with the same
     tsp_check used in scoring; they must match exactly.
  D. Solution value is preserved (all 33 hidden instances): run tsp_check on every
     transformed instance and its correspondingly transformed stored tour. The
     recomputed tour length must equal the oracle manifest value, which is the
     recomputed value of the same tour on the original instance during generation;
     see tests/calibration/transform-verify-260920/.
  E. Spot-check K reuse (33/33): reference.json K equals the original-instance K
     recorded in transform_manifest (pairwise distances are preserved, so the
     optimum carries over by isomorphism). B is a form1 placeholder that was
     replaced after batch remeasurement; this test does not verify B.

When this file was created, the full transformation-time checks had run: pairwise
 distances were preserved across all 33 official/transformed instances, inversion
 was consistent, tsp_check gave equal values for stored tours on both sides, and
 25/25 sampled permutations matched the seed rule from the 260911 renaming batch.
The report is in tests/calibration/transform-verify-260920/.

Run with `python3 test_transform.py` (unittest). C/D compile tsp_check with g++
from the same source as environment/app/src/tsp_check.cpp. Those cases are skipped
if g++ is unavailable; A/B/E always run in pure Python."""
import json
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
        inst_files = sorted(f[:-4] for f in os.listdir(os.path.join(HERE, "instances"))
                            if f.endswith(".tsp"))
        officials = sorted(self.manifest["instances"][tx]["official"]
                           for tx in self.tx_sorted)
        self.assertEqual(self.hidden, officials,
                         "split hidden set != manifest official-name set")
        self.assertEqual(self.tx_sorted, sorted(self.reference),
                         "manifest key set != reference key set")
        self.assertEqual(self.tx_sorted, inst_files, "manifest key set != instances file set")
        self.assertEqual(len(self.tx_sorted), 33)
        for tx in self.tx_sorted:
            ent = self.manifest["instances"][tx]
            n = ent["n"]
            self.assertEqual(sorted(ent["old_of_new"]), list(range(1, n + 1)),
                             f"{tx}: old_of_new is not a bijection of 1..n")

    def test_b_roundtrip(self):
        for tx in self.tx_sorted:
            ent = self.manifest["instances"][tx]
            with open(os.path.join(HERE, "instances", tx + ".tsp"), "rb") as f:
                tx_bytes = f.read()
            with tempfile.TemporaryDirectory(prefix="xf-rt-") as work:
                inv_path = os.path.join(work, "inv.tsp")
                with open(inv_path, "wb") as f:
                    f.write(transform.invert_file(
                        os.path.join(HERE, "instances", tx + ".tsp"),
                        ent["old_of_new"]))
                inst_i = transform.parse_instance(inv_path)
                fwd = transform.emit_instance(inst_i, ent["old_of_new"])
            self.assertEqual(fwd, tx_bytes, f"{tx}: apply∘invert is not byte-identical")

    @staticmethod
    def _tsp_check_bin():
        gxx = shutil.which("g++")
        if not gxx:
            return None
        tmp = tempfile.mkdtemp(prefix="tsp-check-")
        bin_path = os.path.join(tmp, "tsp_check")
        src = os.path.join(TASK, "environment", "app", "src", "tsp_check.cpp")
        p = subprocess.run([gxx, "-O2", "-std=c++14", "-o", bin_path, src],
                           capture_output=True, text=True)
        if p.returncode != 0:
            return None
        return bin_path

    def _check_len(self, check_bin, inst_path, tour_path, tag):
        p = subprocess.run([check_bin, inst_path, tour_path],
                           capture_output=True, text=True, timeout=900)
        out = (p.stdout or "").strip()
        self.assertEqual(p.returncode, 0, f"{tag}: tsp_check failed {out[-200:]}")
        self.assertTrue(out.startswith("valid "), f"{tag}: not valid {out[-200:]}")
        return int(out.split()[1])

    def test_c_value_invariance_public(self):
        check_bin = self._tsp_check_bin()
        if check_bin is None:
            self.skipTest("g++ unavailable; skipping tsp_check recomputation on both sides (A/B/E are covered)")
        precomputed = os.path.join(TASK, "solution", "precomputed")
        with open(os.path.join(precomputed, "manifest.json")) as f:
            omani = json.load(f)
        by_official = {}
        for ent in omani.values():
            if not ent.get("instance", "").startswith("tx"):
                by_official.setdefault(ent["instance"], ent)
        publics = sorted(n for n, v in self.split["instances"].items()
                         if v == "public")
        picks = [publics[0], publics[len(publics) // 2], publics[-1]]
        with tempfile.TemporaryDirectory(prefix="xf-public-") as work:
            for official in picks:
                data, ent_t = transform.transform_file(
                    os.path.join(TASK, "environment", "app", "instances",
                                 official + ".tsp"), official)
                old_of_new = ent_t["old_of_new"]
                ent = by_official[official]
                with open(os.path.join(precomputed, ent["tour"])) as f:
                    toks = f.read().split()
                new_toks = transform.permute_tour_tokens(toks, old_of_new)
                orig_tour = os.path.join(work, "orig.tour")
                tx_tour = os.path.join(work, "tx.tour")
                tx_inst = os.path.join(work, "tx.tsp")
                with open(tx_inst, "wb") as f:
                    f.write(data)
                with open(orig_tour, "w") as f:
                    f.write(" ".join(toks) + "\n")
                with open(tx_tour, "w") as f:
                    f.write(" ".join(new_toks) + "\n")
                v1 = self._check_len(check_bin,
                                     os.path.join(TASK, "environment", "app",
                                                  "instances", official + ".tsp"),
                                     orig_tour, f"public {official} original side")
                v2 = self._check_len(check_bin, tx_inst, tx_tour,
                                     f"public {official} transformed side")
                self.assertEqual(v1, v2,
                                 f"public {official}: tour lengths on the two sides {v1} vs {v2}")

    def test_d_value_invariance_hidden(self):
        check_bin = self._tsp_check_bin()
        if check_bin is None:
            self.skipTest("g++ unavailable; skipping tsp_check recomputation (A/B/E are covered)")
        precomputed = os.path.join(TASK, "solution", "precomputed")
        with open(os.path.join(precomputed, "manifest.json")) as f:
            omani = json.load(f)
        tx_entries = {e["instance"]: e for e in omani.values()
                      if e.get("instance", "").startswith("tx")}
        self.assertEqual(sorted(tx_entries), self.tx_sorted,
                         "tx entries in oracle manifest do not match hidden set")
        for tx in self.tx_sorted:
            ent = tx_entries[tx]
            val = self._check_len(
                check_bin,
                os.path.join(HERE, "instances", tx + ".tsp"),
                os.path.join(precomputed, ent["tour"]), tx)
            want = int(ent["len"].split()[1])
            self.assertEqual(val, want, f"{tx}: recomputed {val} != recorded {want}")
            # Known exception (existing form1 convention, noted in solution/solve.sh header): the stored
            # tour for d657 is based on the revised instance file and lies above the literature K; the permutation preserves this difference,
            # while the stored tours for the other instances equal K.
            if self.manifest["instances"][tx]["official"] != "d657":
                self.assertEqual(val, ent["K"], f"{tx}: recomputed {val} != K {ent['K']}")

    def test_e_k_carryover(self):
        for tx in self.tx_sorted:
            ent = self.manifest["instances"][tx]
            self.assertEqual(self.reference[tx]["K"], ent["K"],
                             f"{tx}: reference K differs from original-instance K (isomorphic reuse failed)")
            self.assertEqual(self.reference[tx].get("type"), ent.get("type"))
            self.assertEqual(self.reference[tx].get("transformed_from"),
                             ent["official"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
