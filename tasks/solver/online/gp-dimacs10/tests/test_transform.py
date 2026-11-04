#!/usr/bin/env python3
"""Mathematical validation of the gp-dimacs10 form2 hidden-set transformation (form2-conversion-recipes.md).

Three checks, plus a structural gate:
  A. Structural gate: the hidden official names in split.json equal the official-name
     set in transform_manifest; manifest keys equal reference.json keys and the
     tests/instances file set (13 txNNN.graph.bz2 files; reference keys are
     txNNN.graph); every permutation is a bijection of 1..n. The k=4 block count
     and 3% balance tolerance are not carried in instance files (manifest params_note).
  B. Round trip (13/13): invert each transformed instance using the manifest
     permutation, then apply the same permutation again. The bytes must exactly
     match the transformed file (an inverse assertion in canonical form).
  C. Solution value is preserved (public instances with known partitions, recipe
     check): transform 3 public instances that have stored partitions and transform
     the partitions too. The cut values recomputed on both sides with check_gp,
     the same checker used in scoring (balance constraint plus cut-value recomputation),
     must match exactly.
  D. Solution value is preserved (all hidden instances with stored partitions):
     check_gp on each transformed instance and its transformed partition. The cut
     value must equal the oracle manifest value, which is the value recomputed for
     the same partition on the original instance; see the generation report in
     tests/calibration/transform-verify-260920/.
  E. Spot-check K reuse (13/13): reference.json K equals the original-instance K
     recorded in transform_manifest (reused by isomorphism). B is a form1
     placeholder replaced after batch remeasurement; this test does not verify B.

When this file was created, full checks had run: all 13 original/transformed
instances were isomorphic as adjacency multisets, inversion was consistent, and
check_gp gave equal values for stored partitions on both sides. The report is in
 tests/calibration/transform-verify-260920/.

Run with `python3 test_transform.py` (unittest). All checks use pure Python;
check_gp is imported from tests/scoring.py, the same implementation used for scoring."""
import bz2
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import transform  # noqa: E402
import scoring  # noqa: E402  (tests/scoring.py, same check_gp used by scoring)


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
                            if f.endswith(".bz2"))
        officials = sorted(self.manifest["instances"][tx]["official"]
                           for tx in self.tx_sorted)
        self.assertEqual(self.hidden, officials,
                         "split hidden set != manifest official-name set")
        self.assertEqual(self.tx_sorted, sorted(self.reference),
                         "manifest key set != reference key set")
        self.assertEqual(self.tx_sorted, inst_files, "manifest key set != instances file set")
        self.assertEqual(len(self.tx_sorted), 13)
        self.assertIn("params_note", self.manifest,
                      "missing note that k/balance parameters are not carried in instance files")
        for tx in self.tx_sorted:
            ent = self.manifest["instances"][tx]
            n = ent["n"]
            self.assertEqual(sorted(ent["perm"]), list(range(1, n + 1)),
                             f"{tx}: perm is not a bijection of 1..n")

    def test_b_roundtrip(self):
        for tx in self.tx_sorted:
            ent = self.manifest["instances"][tx]
            with bz2.open(os.path.join(HERE, "instances", tx + ".bz2"), "rt") as f:
                tx_text = f.read()
            orig = transform.invert_text(tx_text, ent["perm"])
            n, m, adj = transform.load_metis(orig)
            self.assertEqual(n, ent["n"], f"{tx}: inverted n differs")
            self.assertEqual(m, ent["m"], f"{tx}: inverted m differs")
            new_adj = [None] * n
            for v in range(n):
                new_adj[ent["perm"][v] - 1] = sorted(ent["perm"][u - 1] for u in adj[v])
            fwd = transform.canonical_text(n, m, new_adj)
            self.assertEqual(fwd, tx_text, f"{tx}: apply∘invert is not byte-identical")

    def test_c_value_invariance_public(self):
        precomputed = os.path.join(TASK, "solution", "precomputed")
        with open(os.path.join(precomputed, "manifest.json")) as f:
            omani = json.load(f)
        publics = [n for n, v in sorted(self.split["instances"].items())
                   if v == "public"]
        covered = []
        for official in publics:
            with bz2.open(os.path.join(TASK, "environment", "app", "instances",
                                       official + ".bz2"), "rt") as f:
                text = f.read()
            if transform.token_sha256_text(text) in omani:
                covered.append((official, text))
        self.assertGreaterEqual(len(covered), 3, "fewer than 3 public instances have stored partitions")
        picks = [covered[0], covered[len(covered) // 2], covered[-1]]
        with tempfile.TemporaryDirectory(prefix="xf-public-") as work:
            for official, text in picks:
                tx_text, perm, _, _, _ = transform.transform_text(text, official)
                oent = omani[transform.token_sha256_text(text)]
                with open(os.path.join(precomputed, oent["part"])) as f:
                    toks = f.read().split()
                new_toks = transform.permute_partition_tokens(toks, perm)
                orig_inst = os.path.join(work, "orig.graph")
                tx_inst = os.path.join(work, "tx.graph")
                orig_sol = os.path.join(work, "orig.part")
                tx_sol = os.path.join(work, "tx.part")
                with open(orig_inst, "w") as f:
                    f.write(text)
                with open(tx_inst, "w") as f:
                    f.write(tx_text)
                with open(orig_sol, "w") as f:
                    f.write("\n".join(toks) + "\n")
                with open(tx_sol, "w") as f:
                    f.write("\n".join(new_toks) + "\n")
                v1, e1 = scoring.check_gp(orig_inst, orig_sol)
                v2, e2 = scoring.check_gp(tx_inst, tx_sol)
                self.assertIsNotNone(v1, f"public {official}: checker failed on original side {e1}")
                self.assertIsNotNone(v2, f"public {official}: checker failed on transformed side {e2}")
                self.assertEqual(v1, v2, f"public {official}: cut values on the two sides {v1} vs {v2}")

    def test_d_value_invariance_hidden(self):
        precomputed = os.path.join(TASK, "solution", "precomputed")
        with open(os.path.join(precomputed, "manifest.json")) as f:
            omani = json.load(f)
        with tempfile.TemporaryDirectory(prefix="xf-hidden-") as work:
            covered = 0
            for tx in self.tx_sorted:
                with bz2.open(os.path.join(HERE, "instances", tx + ".bz2"), "rt") as f:
                    tx_text = f.read()
                oent = omani.get(transform.token_sha256_text(tx_text))
                if oent is None:
                    continue
                covered += 1
                inst = os.path.join(work, "inst.graph")
                sol = os.path.join(precomputed, oent["part"])
                with open(inst, "w") as f:
                    f.write(tx_text)
                val, err = scoring.check_gp(inst, sol)
                self.assertIsNotNone(val, f"{tx}: check_gp failed {err}")
                self.assertEqual(val, oent["cut"],
                                 f"{tx}: recomputed {val} != recorded {oent['cut']}")
            self.assertEqual(covered, 9, "coverage count differs from generation report (9/13)")

    def test_e_k_carryover(self):
        for tx in self.tx_sorted:
            ent = self.manifest["instances"][tx]
            self.assertEqual(self.reference[tx]["K"], ent["K"],
                             f"{tx}: reference K differs from original-instance K (isomorphic reuse failed)")
            self.assertEqual(self.reference[tx].get("transformed_from"),
                             ent["official"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
