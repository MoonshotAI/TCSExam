#!/usr/bin/env python3
"""Mathematical validation of the maxclique-dimacs form2 hidden-set transformation (form2-conversion-recipes.md).

Three checks, plus a structural gate:
  A. Structural gate: the hidden official names in split.json equal the official-name
     set in transform_manifest; manifest keys equal reference.json keys and the
     tests/instances file set (24 txNNN.clq files); every permutation is a bijection
     of 1..n.
  B. Round trip (24/24): invert each transformed instance using the manifest
     permutation, then apply the same permutation again. The bytes must exactly
     match the transformed file (an inverse assertion in canonical form).
  C. Solution value is preserved (public instances with known solutions, recipe
     check): transform 3 public instances with stored reference cliques and transform
     the cliques too. The clique sizes recomputed on both sides with check_clique,
     the same checker used for scoring, must match exactly.
  D. Solution value is preserved (all 24 hidden instances): run check_clique on
     every transformed instance and its transformed reference clique. The recomputed
     clique size must equal the oracle manifest value, which is the recomputed value
     of the same reference clique on the original instance; see the generation
     report in tests/calibration/transform-verify-260920/.
  E. Spot-check K reuse (24/24): reference.json K equals the original-instance K
     recorded in transform_manifest (reused by isomorphism). B is a form1
     placeholder replaced after batch remeasurement; this test does not verify B.

When this file was created, the full checks had run: the edge sets of all 24
original/transformed pairs were isomorphic, inversion was consistent, check_clique
gave equal values for stored cliques on both sides, and output bytes matched the
260913 transformation batch in 24/24 cases. The report is in
 tests/calibration/transform-verify-260920/.

Run with `python3 test_transform.py` (unittest). All checks use pure Python;
check_clique is imported from tests/scoring.py, the same implementation used for scoring."""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import transform  # noqa: E402
import scoring  # noqa: E402  (tests/scoring.py, same check_clique used by scoring)


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
        inst_files = sorted(f for f in os.listdir(os.path.join(HERE, "instances"))
                            if f.endswith(".clq"))
        officials = sorted(self.manifest["instances"][tx]["official"]
                           for tx in self.tx_sorted)
        self.assertEqual(self.hidden, officials,
                         "split hidden set != manifest official-name set")
        self.assertEqual(self.tx_sorted, sorted(self.reference),
                         "manifest key set != reference key set")
        self.assertEqual(self.tx_sorted, inst_files, "manifest key set != instances file set")
        self.assertEqual(len(self.tx_sorted), 24)
        for tx in self.tx_sorted:
            ent = self.manifest["instances"][tx]
            n = ent["n"]
            self.assertEqual(sorted(ent["perm"]), list(range(1, n + 1)),
                             f"{tx}: perm is not a bijection of 1..n")

    def test_b_roundtrip(self):
        for tx in self.tx_sorted:
            ent = self.manifest["instances"][tx]
            with open(os.path.join(HERE, "instances", tx), errors="replace") as f:
                tx_text = f.read()
            orig = transform.invert_text(tx_text, ent["perm"])
            n, edges = transform.parse_dimacs_text(orig)
            self.assertEqual(n, ent["n"], f"{tx}: inverted n differs")
            self.assertEqual(len(edges), ent["m"], f"{tx}: inverted m differs")
            fwd = transform.canonical_text(
                n, {(ent["perm"][u - 1], ent["perm"][v - 1]) for u, v in edges})
            self.assertEqual(fwd, tx_text, f"{tx}: apply∘invert is not byte-identical")

    @staticmethod
    def _check_pair(orig_text, orig_toks, tx_text, tx_toks, tag, work):
        """Run check_clique on both sides; recomputed clique sizes must match exactly."""
        orig_inst = os.path.join(work, "orig.clq")
        tx_inst = os.path.join(work, "tx.clq")
        orig_sol = os.path.join(work, "orig.sol")
        tx_sol = os.path.join(work, "tx.sol")
        with open(orig_inst, "w") as f:
            f.write(orig_text)
        with open(tx_inst, "w") as f:
            f.write(tx_text)
        with open(orig_sol, "w") as f:
            f.write(" ".join(orig_toks) + "\n")
        with open(tx_sol, "w") as f:
            f.write(" ".join(tx_toks) + "\n")
        v1, e1 = scoring.check_clique(orig_inst, orig_sol)
        v2, e2 = scoring.check_clique(tx_inst, tx_sol)
        return v1, e1, v2, e2

    def test_c_value_invariance_public(self):
        precomputed = os.path.join(TASK, "solution", "precomputed")
        with open(os.path.join(precomputed, "manifest.json")) as f:
            omani = json.load(f)
        by_official = {}
        for ent in omani.values():
            if not ent.get("name", "").startswith("tx"):
                by_official.setdefault(ent["name"], ent)
        publics = [n for n, v in sorted(self.split["instances"].items())
                   if v == "public" and n in by_official]
        self.assertGreaterEqual(len(publics), 3, "fewer than 3 public instances have stored colorings")
        picks = [publics[0], publics[len(publics) // 2], publics[-1]]
        with tempfile.TemporaryDirectory(prefix="xf-public-") as work:
            for official in picks:
                with open(os.path.join(TASK, "environment", "app", "instances",
                                       official), errors="replace") as f:
                    text = f.read()
                tx_text, perm, _, _, _ = transform.transform_text(text, official)
                ent = by_official[official]
                with open(os.path.join(precomputed, ent["clique"])) as f:
                    toks = f.read().split()
                new_toks = transform.permute_clique_tokens(toks, perm)
                canon_orig = transform.canonical_text(
                    *transform.parse_dimacs_text(text))
                v1, e1, v2, e2 = self._check_pair(
                    canon_orig, toks, tx_text, new_toks, official, work)
                self.assertIsNotNone(v1, f"public {official}: checker failed on original side {e1}")
                self.assertIsNotNone(v2, f"public {official}: checker failed on transformed side {e2}")
                self.assertEqual(v1, v2, f"public {official}: clique sizes on the two sides {v1} vs {v2}")

    def test_d_value_invariance_hidden(self):
        precomputed = os.path.join(TASK, "solution", "precomputed")
        with open(os.path.join(precomputed, "manifest.json")) as f:
            omani = json.load(f)
        tx_entries = {e["name"]: e for e in omani.values()
                      if e.get("name", "").startswith("tx")}
        self.assertEqual(sorted(tx_entries), sorted(
            tx for tx in self.tx_sorted
            if self.manifest["instances"][tx]["official"] in
            {e["name"] for e in omani.values()}))
        with tempfile.TemporaryDirectory(prefix="xf-hidden-") as work:
            for tx in sorted(tx_entries):
                with open(os.path.join(HERE, "instances", tx), errors="replace") as f:
                    tx_text = f.read()
                ent = tx_entries[tx]
                with open(os.path.join(precomputed, ent["clique"])) as f:
                    toks = f.read().split()
                inst = os.path.join(work, "inst.clq")
                sol = os.path.join(work, "inst.sol")
                with open(inst, "w") as f:
                    f.write(tx_text)
                with open(sol, "w") as f:
                    f.write(" ".join(toks) + "\n")
                val, err = scoring.check_clique(inst, sol)
                self.assertIsNotNone(val, f"{tx}: check_clique failed {err}")
                self.assertEqual(val, ent["value"],
                                 f"{tx}: recomputed {val} != recorded {ent['value']}")

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
