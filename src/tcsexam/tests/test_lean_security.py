"""Submission attacks and normal proof controls for all Lean verifier families."""
import importlib.util
import json
from pathlib import Path
import re
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
SHARED = ROOT / 'assets/environments/lean-verifier/lean_security.py'


def load(path):
    spec = importlib.util.spec_from_file_location('lean_test_module', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


security = load(SHARED)
SCORERS = sorted(p for track in ('theorem', 'construction', 'open')
                 for p in (ROOT / 'tasks' / track).glob('*/tests/score.py'))
STANDARD = {'propext', 'Classical.choice', 'Quot.sound'}


@pytest.mark.parametrize('literal', ['"/-"', 'r"/-"', 'r##"/- \\""##',
                                   '"\\\" /- --"', "'\"'", '«name/-suffix»'])
def test_literal_comment_delimiters_cannot_hide_executable_code(literal):
    source = f'def marker := {literal}\nrun_cmd pure ()\n'
    assert security.strip_comments(source) == source
    assert 'run_cmd' in security.source_error(source)


def test_nested_comments_and_literal_values_preserve_offsets():
    source = 'def x := "a/-b" /- one /- two -/ three -/\n-- run_cmd\ndef y := "c"\n'
    stripped = security.strip_comments(source)
    assert len(stripped) == len(source)
    assert stripped.index('def y') == source.index('def y')
    assert '"a/-b"' in stripped
    assert security.source_error(source) is None
    assert security.strip_comments('def x := "a"') != security.strip_comments('def x := "b"')


@pytest.mark.parametrize('source', [
    'run_cmd pure ()', 'example : True := by run_tac pure ()',
    'example : True := by_elab pure ()', '#eval IO.println "forged report"',
    'initialize pure ()', 'elab "attack" : tactic => pure ()',
    '@[implemented_by fake] def real := true',
    'set_option debug.skipKernelTC true',
    'def text := s!"value: {by run_tac pure ()}"',
    'def text := m!"value: {s!"nested: {by run_tac pure ()}"}"',
    'def x : Nat := dbg_trace "{(show Nat from by run_tac pure (); exact 0)}"; 0',
    'example : True := by trace "{(show Nat from by run_tac pure (); exact 0)}"; trivial',
    'def text := "unterminated', '/- unterminated',
])
def test_metaprogramming_and_malformed_source_rejected(source):
    assert security.source_error(source)


@pytest.mark.parametrize('source', [
    'theorem t : True := by trivial',
    'theorem t (p : Prop) : p ∨ ¬ p := Classical.em p',
    'theorem t (h : False) : ¬ True := by intro _; exact h',
    'def text := "run_cmd /- is text"',
    'def text := s!"value: {"/-"}"\ntheorem t : True := by trivial',
    'def name\' := true\ntheorem t : name\' = true := rfl',
])
def test_normal_source_passes(source):
    assert security.source_error(source) is None


@pytest.mark.parametrize('path', SCORERS, ids=lambda p: p.parts[-3])
def test_each_scorer_rejects_axiom_aliases_and_requires_final_exact_report(path):
    scorer = load(path)
    track = path.parts[-4]
    args = ([STANDARD] if track == 'construction' else
            [set()] if track == 'open' or path.parts[-3] == 'lcc-exp-lb' else [])
    def accepted(report):
        return scorer.lean_axioms_ok(report, 'Task.answer', *args)
    good = "'Task.answer' depends on axioms: [propext, Classical.choice, Quot.sound]\n"
    assert accepted(good)
    assert accepted("'Task.answer' does not depend on any axioms\n")
    for name in ['choice', 'sound', 'Other.propext', 'Other.Classical.choice', 'sorryAx',
                 'Other._native.native_decide.ax_1', '']:
        bad = f"'Task.answer' depends on axioms: [{name}]\n"
        assert not accepted(bad)
        assert not accepted(good + bad)
    assert not accepted(good.replace('Task.answer', 'Other.Task.answer'))
    assert not accepted(good.replace(']', ''))
    assert path.with_name('lean_security.py').read_bytes() == SHARED.read_bytes()
    assert path.with_name('TCSExamVerifierAudit.lean').read_bytes() == SHARED.with_name('TCSExamVerifierAudit.lean').read_bytes()


def test_explicit_checkpoint_and_native_trust_names_only():
    report = "'Task.answer' depends on axioms: [Task.previous]\n"
    assert security.axioms_ok(report, 'Task.answer', STANDARD | {'Task.previous'})
    assert not security.axioms_ok(report.replace('Task.previous', 'previous'), 'Task.answer', STANDARD | {'Task.previous'})
    assert security.source_error('theorem t : 1 + 1 = 2 := by native_decide') is None
    assert security.source_error('theorem t : 1 + 1 = 2 := by native_decide', allow_native=False)
    report = "'Task.answer' depends on axioms: [Lean.ofReduceBool]\n"
    assert security.axioms_ok(report, 'Task.answer', STANDARD | {'Lean.ofReduceBool'})
    assert not security.axioms_ok(report, 'Task.answer', STANDARD)


def test_final_structured_report_owns_native_permissions():
    def report(axioms, native):
        return 'TCSEXAM_AXIOM_REPORT ' + json.dumps({
            'declaration': 'Task.answer', 'axioms': axioms, 'native_verified': native}) + '\n'
    allowed = STANDARD | {'Lean.ofReduceBool'}
    forged = report(['choice'], ['choice'])
    assert not security.axioms_ok(forged + report(['choice'], []), 'Task.answer', allowed)
    assert not security.axioms_ok(report(['choice'], []) + forged, 'Task.answer', allowed)
    native = 'Task.answer._native.native_decide.ax_1'
    assert security.axioms_ok(report([native], [native]), 'Task.answer', allowed)
    assert not security.axioms_ok(report([native], [native]), 'Task.answer', STANDARD)
    assert not security.axioms_ok(report(['sorryAx'], []), 'Task.answer', allowed)


def test_open_helper_source_cannot_supply_metaprogramming(tmp_path):
    runner = load(ROOT / 'tasks/open/log-rank-conjecture/tests/trusted_verifier.py')
    (tmp_path / 'Task').mkdir()
    (tmp_path / 'Task/Basic.lean').write_text('import Task.Helper\n')
    (tmp_path / 'Task/Helper.lean').write_text('run_cmd pure ()\n')
    with pytest.raises(ValueError, match='Helper.lean.*run_cmd'):
        runner.collect_submission(tmp_path, 'task-lean-sources')


def test_both_contradictory_main_slots_are_invalid(tmp_path, monkeypatch):
    task = ROOT / 'tasks/open/log-rank-conjecture'
    scorer = load(task / 'tests/score.py')
    (tmp_path / 'Task').mkdir()
    source = (task / 'tests/reference/Basic.lean').read_text()
    (tmp_path / 'Task/Basic.lean').write_text(re.sub(r'\bsorry\b', 'trivial', source))
    reward = tmp_path / 'reward.txt'
    monkeypatch.setattr(sys, 'argv', ['score.py', '--app', str(tmp_path),
                                     '--tests', str(task / 'tests'), '--reward', str(reward)])
    # Independently exercise aggregation even if both isolated checks report success.
    monkeypatch.setattr(scorer, 'run_lean', lambda app, path: (True,
        "'LogRank.conj' does not depend on any axioms\n"
        "'LogRank.refuted' does not depend on any axioms\n"))
    assert scorer.main() == 0
    assert float(reward.read_text()) == 0
    result = json.loads((tmp_path / 'judge_result.json').read_text())
    assert 'both contradictory' in result['reason']


def test_auditor_compiles_separately_before_submitted_source(tmp_path, monkeypatch):
    from types import SimpleNamespace
    source = tmp_path / 'Check.lean'
    source.write_text('import Mathlib\ntheorem answer : True := by trivial\n' + security.axiom_audit('answer'))
    calls = []
    def run(argv, **kwargs):
        calls.append(argv)
        return SimpleNamespace(returncode=0, stdout='', stderr='')
    monkeypatch.setattr(security.subprocess, 'run', run)
    assert security.run_lean(tmp_path, source, 1200)[0]
    assert Path(calls[0][-1]) == SHARED.with_name('TCSExamVerifierAudit.lean')
    assert calls[0][3:5] == ['-R', str(SHARED.parent)]
    assert calls[0][5] == '-o'
    assert calls[1][-1] == str(source)
    assert source.read_text().startswith('import TCSExamVerifierAudit\nimport Mathlib\n')
    assert security.run_lean(tmp_path, source, 1200)[0]
    assert len(calls) == 3  # Reuse the already compiled trusted module in this project.
    assert source.read_text().count('import TCSExamVerifierAudit') == 1


def test_initial_graded_sources_remain_supported():
    for scorer in SCORERS:
        source = scorer.parent / 'reference/Basic.lean'
        assert security.source_error(source.read_text(), allow_native=scorer.parts[-4] == 'construction') is None


def test_certificate_generator_compatibility_is_exact_and_task_owned():
    tests = ROOT / 'tasks/construction/ramsey-r55/tests'
    supported = load(tests / 'lean_security.py')
    template = (tests / 'r55-legacy-generator.txt').read_text()
    source = 'import Mathlib\nnamespace R55\n' + template + '\nend R55\n'
    normalized = supported.certificate_source(source)
    assert len(normalized) == len(source)
    assert normalized.count('\n') == source.count('\n')
    assert 'import Mathlib\nnamespace R55\n' in normalized
    assert 'elab' not in normalized
    assert supported.source_error(source) is None
    assert security.source_error(source)  # Other tasks retain their source policy.
    assert supported.source_error(source.replace('value := proof', 'value := cl.proof'))
    assert supported.source_error(source + '\nrun_cmd pure ()\n')
    assert supported.source_error(source + '\nelab "other" : command => pure ()\n')


def test_certificate_compatibility_preserves_comments_and_literal_data():
    tests = ROOT / 'tasks/construction/ramsey-r55/tests'
    supported = load(tests / 'lean_security.py')
    template = (tests / 'r55-legacy-generator.txt').read_text()
    for source in ['/- ' + template + ' -/', 'def text := r####"' + template + '"####']:
        assert supported.certificate_source(source) == source
    combined = '/- ' + template + ' -/\n' + template
    assert supported.certificate_source(combined).startswith('/- ' + template + ' -/\n')


def test_certificate_module_is_compiled_before_normalized_submission(tmp_path, monkeypatch):
    from types import SimpleNamespace
    tests = ROOT / 'tasks/construction/ramsey-r55/tests'
    supported = load(tests / 'lean_security.py')
    template = (tests / 'r55-legacy-generator.txt').read_text()
    source = tmp_path / 'Check.lean'
    source.write_text('import Mathlib\n' + template + '\n')
    calls = []
    def run(argv, **kwargs):
        calls.append(argv)
        return SimpleNamespace(returncode=0, stdout='', stderr='')
    monkeypatch.setattr(supported.subprocess, 'run', run)
    assert supported.run_lean(tmp_path, source, 1200)[0]
    assert Path(calls[0][-1]).name == 'TCSExamVerifierAudit.lean'
    assert Path(calls[1][-1]).name == 'TCSExamR55Certificate.lean'
    assert calls[2][-1] == str(source)
    assert source.read_text().startswith('import TCSExamVerifierAudit\nimport TCSExamR55Certificate\n')
    assert template not in source.read_text()


def test_certificate_sources_are_synchronized():
    origin = ROOT / 'assets/environments/lean-verifier/certificates/ramsey-r55'
    tests = ROOT / 'tasks/construction/ramsey-r55/tests'
    assert (origin / 'legacy-generator.txt').read_bytes() == (tests / 'r55-legacy-generator.txt').read_bytes()
    assert (origin / 'TCSExamR55Certificate.lean').read_bytes() == (tests / 'TCSExamR55Certificate.lean').read_bytes()
    template = (origin / 'legacy-generator.txt').read_text()
    assert ('namespace TCSExamR55Certificate\n\n' + template +
            '\n\nend TCSExamR55Certificate\n') in (origin / 'TCSExamR55Certificate.lean').read_text()
