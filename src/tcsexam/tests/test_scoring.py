"""Small independent examples; historical model results are not release fixtures."""
import copy
from importlib.resources import files
import json
import unittest

from tcsexam.scoring import aggregate, relative_score


class Scores(unittest.TestCase):
    def setUp(self):
        self.suite = {"suite": "lite", "tasks": [{"id": t, "track": t} for t in
                                                ("theorem", "solver", "construction", "open")]}
        self.cohort = {"suite": "lite", "solver_reference_id": "synthetic-test-only",
                       "solver_protocol": "offline", "models": {"test": {"attempts_per_task": 1}}}
        self.rows = [{"model": "test", "item": t, "track": t, "attempt": 1, "score": score,
                      "adoption_status": "selected", "score_status": "valid",
                      "score_type": "fixed_reference_relative" if t == "solver" else "original_task_score",
                      "solver_protocol": "offline" if t == "solver" else ""}
                     for t, score in [("theorem", 1), ("solver", .5), ("construction", .8), ("open", 0)]]

    def calculate(self):
        return aggregate(self.rows, self.suite, self.cohort)["models"][0]

    def test_hand_calculated_index(self):
        self.assertEqual(self.calculate()["index"], 69)
        self.assertEqual(self.calculate()["status"], "complete")

    def test_unequal_attempt_counts_do_not_reweight_tasks(self):
        self.cohort["models"]["test"]["attempts_per_task"] = 2
        extra = copy.deepcopy(self.rows)
        for r in extra:
            r["attempt"] = 2
        self.rows += extra
        self.assertEqual(self.calculate()["index"], 69)
        self.rows.pop()
        self.assertIsNone(self.calculate()["index"])

    def test_judge_failure_is_distinct_from_valid_zero(self):
        self.rows[0]["score"] = 0
        self.assertIsNotNone(self.calculate()["index"])
        self.rows[0].update(score="", score_status="judge_failed")
        self.assertIsNone(self.calculate()["index"])

    def test_duplicates_raw_solver_rewards_and_protocol_mixing_rejected(self):
        with self.assertRaises(ValueError):
            aggregate(self.rows + [self.rows[0]], self.suite, self.cohort)
        self.rows[1]["score_type"] = "original_task_score"
        with self.assertRaises(ValueError):
            self.calculate()
        self.rows[1].update(score_type="fixed_reference_relative", solver_protocol="online")
        with self.assertRaises(ValueError):
            self.calculate()
        self.cohort.pop("solver_protocol")
        extra = {**self.rows[1], "attempt": 2, "solver_protocol": "offline"}
        with self.assertRaises(ValueError):
            aggregate(self.rows + [extra], self.suite, self.cohort)

    def test_construction_above_one_is_preserved(self):
        self.rows[2]["score"] = 4
        self.assertEqual(self.calculate()["construction"], 4)
        self.assertGreater(self.calculate()["index"], 100)

    def test_provisional_label_and_suite_separation(self):
        self.rows[0]["adoption_status"] = "selected_provisional"
        self.assertEqual(self.calculate()["status"], "provisional")
        self.cohort["suite"] = "full"
        with self.assertRaises(ValueError):
            self.calculate()

    def test_objective_direction_invalidity_and_missing_input(self):
        ref = {"reference_id": "synthetic-test-only", "sigma_floor_relative": .02,
               "sigma_floor_absolute": 1e-9,
               "tasks": {"example": {"direction": "min", "kind": "objective",
                                     "reference_values": {"a": [10, 10, 10]}}}}
        def score(value, status="ok"):
            return relative_score("example", [{"instance": "a", "A": value, "status": status}], ref)["relative_score"]
        self.assertEqual(score(10), .5)
        self.assertGreater(score(9), .5)
        self.assertLess(score(11), .5)
        self.assertEqual(score(None, "timeout"), 0)
        ref["tasks"]["example"]["direction"] = "max"
        self.assertGreater(score(11), .5)
        for status in ("judge_failed", "not_finished"):
            with self.assertRaises(ValueError):
                score(None, status)
        with self.assertRaises(ValueError):
            relative_score("example", [], ref)

    def test_solve_kind_is_independent_of_task_name(self):
        ref = {"reference_id": "synthetic-test-only", "sigma_floor_relative": .02,
               "sigma_floor_absolute": 1e-9,
               "tasks": {"renamed-solve-task": {"direction": "max", "kind": "solve",
                         "reference_values": {"a": [0, 1, 1]}}}}
        def score(**outcome):
            return relative_score("renamed-solve-task",
                [{"instance": "a", "status": "ok", **outcome}], ref)["relative_score"]
        self.assertEqual(score(solved=True, A=100), score(A=1))
        self.assertEqual(score(solved=False, A=100), score(A=0))
        self.assertGreater(score(solved=True), score(solved=False))
        for outcome in ({"solved": 1}, {"A": 2}):
            with self.assertRaises(ValueError):
                score(**outcome)
        ref["tasks"]["qbf-qbfeval"] = {
            "direction": "max", "kind": "objective", "reference_values": {"a": [10, 10, 10]}}
        self.assertEqual(relative_score("qbf-qbfeval",
            [{"instance": "a", "status": "ok", "A": 10, "solved": False}], ref)["relative_score"], .5)

    def test_missing_or_invalid_reference_kind_is_rejected(self):
        ref = {"tasks": {"qbf-qbfeval": {}}}
        for kind in (None, "", "solved", 0, [], {}):
            with self.subTest(kind=kind):
                ref["tasks"]["qbf-qbfeval"] = {"kind": kind}
                with self.assertRaisesRegex(ValueError, "must declare kind as objective or solve"):
                    relative_score("qbf-qbfeval", [], ref)
        ref["tasks"]["qbf-qbfeval"] = {}
        with self.assertRaisesRegex(ValueError, "must declare kind as objective or solve"):
            relative_score("qbf-qbfeval", [], ref)

    def test_published_lite_reference_is_exact_full_subset(self):
        root = files("tcsexam").joinpath("references")
        lite = json.loads(root.joinpath("paper-k3-fixed-260925-lite.json").read_text())
        full = json.loads(root.joinpath("paper-k3-fixed-260925-full.json").read_text())
        task_ids = ("bpp-bpplib", "curriculum-itc2007", "maxcut-mqlib",
                    "mr-roadef2012", "qbf-qbfeval")
        self.assertEqual(list(lite["tasks"]), list(task_ids))
        self.assertEqual(lite, {**full, "tasks": {key: full["tasks"][key] for key in task_ids}})
        for task in full["tasks"].values():
            self.assertIn(task["kind"], ("objective", "solve"))
            self.assertIn("unscored_reference_instances", task)
