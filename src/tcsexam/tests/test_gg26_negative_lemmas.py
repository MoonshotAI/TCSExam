"""GG26 proof controls; actual Lean execution belongs in a CPU sandbox."""

import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCORER = ROOT / "tasks/theorem/gg26-proximity/tests/score.py"

# helper, target, proof, expected reward, dependency axioms
CASES = {
    "negation_symbol": (
        "lemma helper : ¬ False := by intro h; exact h", "¬ False",
        "exact helper", 1, []),
    "negation_not": (
        "lemma helper : Not False := by intro h; exact h", "¬ False",
        "exact helper", 1, []),
    "negation_arrow": (
        "lemma helper : False → False := by intro h; exact h", "¬ False",
        "exact helper", 1, []),
    "legal_reductio": (
        "lemma helper (h : ¬ True) : False := h True.intro", "True",
        "by_contra h\n  exact helper h", 1, ["propext", "Classical.choice", "Quot.sound"]),
    "unproved_negation": (
        "lemma helper : ¬ False := by sorry", "¬ False",
        "exact helper", 0, ["sorryAx"]),
    "unproved_false_direct": (
        "lemma bad : False := by sorry", "True",
        "exact False.elim bad", 0, ["sorryAx"]),
    "unproved_false_indirect": (
        "lemma bad : False := by sorry\nlemma bridge : True := False.elim bad", "True",
        "exact bridge", 0, ["sorryAx"]),
    "unused_unproved_helper": (
        "lemma unused : False := by sorry", "True",
        "trivial", 1, []),
    "legal_reductio_prop_alias": (
        "def NoTruth : Prop := ¬ True\nlemma helper (h : NoTruth) : False := h True.intro",
        "True", "by_contra h\n  exact helper h", 1,
        ["propext", "Classical.choice", "Quot.sound"]),
    "nonprop_empty_specification": (
        "lemma helper (a : Fin 0) : False := Fin.elim0 a", "Fin 0 → True",
        "intro a\n  exact False.elim (helper a)", 0, []),
    "legal_reductio_nested_namespace": (
        "namespace Helpers\ndef NoTruth : Prop := ¬ True\n"
        "lemma helper (h : NoTruth) : False := h True.intro\nend Helpers",
        "True", "by_contra h\n  exact Helpers.helper h", 1,
        ["propext", "Classical.choice", "Quot.sound"]),
    "legal_false_hypothesis": (
        "lemma helper (h : False) : False := h", "¬ False",
        "intro h\n  exact helper h", 1, []),
    "legal_private_false_hypothesis": (
        "private lemma helper (h : False) : False := h", "¬ False",
        "intro h\n  exact helper h", 1, []),
}


def load_scorer(path=SCORER):
    spec = importlib.util.spec_from_file_location("gg26_regression_scorer", path)
    scorer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scorer)
    return scorer


def write_case(base, case):
    """Make a small self-contained statement without the benchmark solution."""
    helper, target, proof, _, _ = CASES[case]
    app, tests = base / "app", base / "tests"
    (app / "Task").mkdir(parents=True)
    (tests / "reference").mkdir(parents=True)
    template = (
        "import Mathlib\nnamespace GG26Regression\n"
        "-- END OF FIXED PART\n{helper}\n"
        f"theorem answer : {target} := by\n"
        "  -- CHECKPOINT answer BEGIN\n{proof}\n"
        "  -- CHECKPOINT answer END\nend GG26Regression\n"
    )
    (tests / "reference/Basic.lean").write_text(template.format(helper="", proof="  sorry"))
    (app / "Task/Basic.lean").write_text(template.format(helper=helper, proof="  " + proof))
    (tests / "checkpoints.json").write_text(json.dumps({
        "namespace": "GG26Regression", "main_theorem": "answer",
        "checkpoints": [{"name": "answer"}],
    }))
    return app, tests, base / "reward.txt"


@pytest.mark.parametrize("case", CASES)
def test_gg26_proof_controls(tmp_path, monkeypatch, case):
    """Exercise the whole scorer; Lean dependency reports are controlled here."""
    scorer = load_scorer()
    app, tests, reward = write_case(tmp_path, case)
    _, _, _, expected, axioms = CASES[case]
    calls = []

    def run_lean(app_dir, assembly):
        calls.append(assembly)
        source = Path(assembly).read_text()
        assert '#tcsexam_audit "GG26Regression.answer"' in source
        reports = ""
        for line in source.splitlines():
            if line.startswith("#tcsexam_gg26_shape "):
                name = json.loads(line.split()[1])
                reports += "TCSEXAM_GG26_SHAPE " + json.dumps({
                    "declaration": name, "reject": case == "nonprop_empty_specification",
                }) + "\n"
        return True, reports + "TCSEXAM_AXIOM_REPORT " + json.dumps({
            "declaration": "GG26Regression.answer", "axioms": axioms,
            "native_verified": [],
        }) + "\n"

    monkeypatch.setattr(scorer, "run_lean", run_lean)
    monkeypatch.setattr(scorer, "prepare_shape_audit", lambda app: (True, ""))
    monkeypatch.setattr(sys, "argv", ["score.py", "--app", str(app),
                                     "--tests", str(tests), "--reward", str(reward)])
    assert scorer.main() == 0
    assert float(reward.read_text()) == expected
    assert len(calls) == 1


@pytest.mark.parametrize("report", ["", "TCSEXAM_GG26_SHAPE []\n",
    'TCSEXAM_GG26_SHAPE {"declaration":"other","reject":false}\n',
    'TCSEXAM_GG26_SHAPE {"declaration":"helper","reject":0}\n'])
def test_shape_audit_requires_an_exact_typed_report(report):
    with pytest.raises(ValueError):
        load_scorer().shape_audit_rejections(report, ["helper"])


def test_shape_module_failure_cannot_accept_submission(tmp_path, monkeypatch, capsys):
    scorer = load_scorer()
    app, tests, reward = write_case(tmp_path, "legal_reductio_prop_alias")
    monkeypatch.setattr(scorer, "prepare_shape_audit", lambda app: (False, "specific compilation error"))
    def unexpected_compilation(*args):
        pytest.fail("submitted source must not compile before the trusted shape module")
    monkeypatch.setattr(scorer, "run_lean", unexpected_compilation)
    monkeypatch.setattr(sys, "argv", ["score.py", "--app", str(app),
                                     "--tests", str(tests), "--reward", str(reward)])
    assert scorer.main() == 0
    assert float(reward.read_text()) == 0
    assert "specific compilation error" in capsys.readouterr().out
