"""Keep complete Dijkstra arc logs inside the verifier's immutable definition layer.

The mathematical examples live in the adjacent task's TraceSemantics.lean and
are compiled in an isolated CPU environment. These tests exercise score.py without
starting Lean: weakening coverage, classification, or comparison accounting
must fail before compilation.
"""
import importlib.util
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
TASK = ROOT / 'tasks/theorem/dijkstra-universal'


def scorer():
    spec = importlib.util.spec_from_file_location('dijkstra_trace_scorer', TASK / 'tests/score.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('remove', [
    '  arc_covered : ∀ u evs, (u, evs) ∈ blocks → ∀ v, (u, v) ∈ G.arcs →\n'
    '    ∃ e ∈ evs, e.v = v\n',
    '  skip_valid : ∀ u evs v, BlockEv.skip v ∈ evs → (u, evs) ∈ blocks →\n'
    '    (blocks.map Prod.fst).idxOf v < (blocks.map Prod.fst).idxOf u\n',
    'tr.relaxCount + ',
], ids=['omitted-arcs', 'misclassified-skips', 'uncounted-comparisons'])
def test_trace_semantics_cannot_be_weakened_by_submission(tmp_path, monkeypatch, capsys, remove):
    source = (TASK / 'environment/app/Task/Basic.lean').read_text()
    assert remove in source
    submission = source.replace(remove, '')
    assert submission != source
    run_score(tmp_path, monkeypatch, submission)
    assert 'fixed definition block missing or tampered' in capsys.readouterr().out


def run_score(tmp_path, monkeypatch, submission):
    app = tmp_path / 'app'
    (app / 'Task').mkdir(parents=True)
    (app / 'Task/Basic.lean').write_text(submission)
    reward = tmp_path / 'reward.txt'
    module = scorer()

    def no_lean(*args, **kwargs):
        pytest.fail('this regression must reject the submission before starting Lean')

    monkeypatch.setattr(module, 'run_lean', no_lean)
    monkeypatch.setattr(sys, 'argv', ['score.py', '--app', str(app), '--tests', str(TASK / 'tests'),
                                    '--reward', str(reward)])
    assert module.main() == 0
    assert reward.read_text() == '0'


def test_supplied_definition_matches_reference_and_reaches_proof_slot(tmp_path, monkeypatch, capsys):
    source = (TASK / 'environment/app/Task/Basic.lean').read_text()
    assert source == (TASK / 'tests/reference/Basic.lean').read_text()
    run_score(tmp_path, monkeypatch, source)
    assert 'slot still contains sorry/admit' in capsys.readouterr().out
