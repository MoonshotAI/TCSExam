"""Declaration formatting and executable-diagnostic submission contracts."""
import importlib.util
from pathlib import Path
import re
import sys

import pytest


ROOT = Path(__file__).resolve().parents[3]
CONSTRUCTIONS = ROOT / 'tasks/construction'
SCORERS = sorted(CONSTRUCTIONS.glob('*/tests/score.py'))
LOCATORS = [p for p in SCORERS if 'def find_' in p.read_text()]
TSP_TASKS = ['tsp-gap', 'graph-tsp-gap', 'rectilinear-tsp-gap']
LEAN_TASKS = sorted(p.parent.parent for track in ('theorem', 'construction', 'open')
                    for p in (ROOT / 'tasks' / track).glob('*/tests/score.py'))
CHECKPOINT_TASKS = [p for p in LEAN_TASKS if p.parent.name != 'construction']


def load(path):
    spec = importlib.util.spec_from_file_location('format_test_module', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('path', LOCATORS, ids=lambda p: p.parts[-3])
@pytest.mark.parametrize('prefix,separator', [('', ' '), ('  ', ' '), ('\t', ' '),
                                             ('  ', '\n    ')])
def test_claim_locator_preserves_header_and_body_across_whitespace(path, prefix, separator):
    scorer = load(path)
    source = (f'{prefix}theorem{separator}answer : True :=\n'
              f'{prefix}-- CLAIM answer BEGIN\n'
              f'{prefix}by trivial\n'
              f'{prefix}-- CLAIM answer END\n')
    if hasattr(scorer, 'find_main_theorem'):
        header = scorer.find_main_theorem(source, 'answer')
    else:
        span, header, body = scorer.find_claim_block(source, 'answer')
        assert body.strip() == 'by trivial'
        assert source[span[0]:span[1]].strip().endswith('-- CLAIM answer END')
    assert header is not None
    assert ''.join(header.split()) == ':True'


@pytest.mark.parametrize('name', ['capset-d7', 'covering-code-k10'])
@pytest.mark.parametrize('prefix', ['', '  ', '\t'])
def test_top_level_locator_keeps_namespace_boundary(name, prefix):
    scorer = load(CONSTRUCTIONS / name / 'tests/score.py')
    declaration = f'{prefix}theorem\n{prefix}  answer : True := by trivial\n'
    assert scorer.find_main_theorem('namespace Inner\n' + declaration + 'end Inner\n', 'answer') is None
    assert scorer.find_main_theorem('namespace Inner\nend Inner\n' + declaration, 'answer') is not None
    assert scorer.find_main_theorem(declaration.replace('answer', 'answer_extra'), 'answer') is None
    assert scorer.find_main_theorem(declaration.replace('theorem', 'def'), 'answer') is None


@pytest.mark.parametrize('name', TSP_TASKS)
@pytest.mark.parametrize('prefix,separator', [('', ' '), ('  ', ' '), ('\t', ' '),
                                             ('  ', '\n    ')])
def test_tsp_formatted_interfaces_reach_proof_check(name, prefix, separator, tmp_path, monkeypatch):
    tests = CONSTRUCTIONS / name / 'tests'
    scorer = load(tests / 'score.py')
    source = (tests / 'reference/Basic.lean').read_text()
    # This test exercises parser dispatch; actual Lean compilation is tested separately.
    source = re.sub(r'\bsorry\b', 'trivial', source)
    source, count = re.subn(r'(?m)^(def|theorem)\s+', lambda m: prefix + m[1] + separator, source)
    assert count > 0
    (tmp_path / 'Task').mkdir()
    (tmp_path / 'Task/Basic.lean').write_text(source)
    monkeypatch.setattr(sys, 'argv', ['score.py', '--app', str(tmp_path), '--tests', str(tests),
                                     '--reward', str(tmp_path / 'reward.txt')])
    probes = []
    def reject_proof(app, path, **kwargs):
        probes.append(Path(path).read_text())
        Path(path).unlink()
        return False, 'Proof rejected by the controlled compilation stub'
    monkeypatch.setattr(scorer, 'run_lean', reject_proof)
    assert scorer.main() == 0
    assert len(probes) == 1
    assert float((tmp_path / 'reward.txt').read_text()) == 0


@pytest.mark.parametrize('name', TSP_TASKS)
def test_tsp_missing_interface_is_rejected_before_proof_check(name, tmp_path, monkeypatch):
    tests = CONSTRUCTIONS / name / 'tests'
    scorer = load(tests / 'score.py')
    source = (tests / 'reference/Basic.lean').read_text()
    source = re.sub(r'\bsorry\b', 'trivial', source)
    source = re.sub(r'(?m)^def certN\b', 'def certN_extra', source)
    (tmp_path / 'Task').mkdir()
    (tmp_path / 'Task/Basic.lean').write_text(source)
    monkeypatch.setattr(sys, 'argv', ['score.py', '--app', str(tmp_path), '--tests', str(tests),
                                     '--reward', str(tmp_path / 'reward.txt')])
    def unexpected_probe(*args, **kwargs):
        pytest.fail('Missing interface must be rejected before compilation')
    monkeypatch.setattr(scorer, 'run_lean', unexpected_probe)
    assert scorer.main() == 0
    assert float((tmp_path / 'reward.txt').read_text()) == 0


@pytest.mark.parametrize('task', CHECKPOINT_TASKS, ids=lambda p: p.name)
@pytest.mark.parametrize('prefix,separator', [('', ' '), ('  ', ' '), ('\t', ' '),
                                             ('  ', '\n    ')])
def test_checkpoint_locator_preserves_names_and_spans(task, prefix, separator):
    scorer = load(task / 'tests/score.py')
    source = (f'{prefix}theorem{separator}answer\' : True :=\n'
              f'{prefix}-- CHECKPOINT answer\' BEGIN\n'
              f'{prefix}by trivial\n'
              f'{prefix}-- CHECKPOINT answer\' END\n')
    block, header, body = scorer.find_checkpoint_block(source, "answer'")
    assert ''.join(source[slice(*header)].split()) == ':True'
    assert source[slice(*body)].strip() == 'by trivial'
    assert source[slice(*block)].strip().endswith("-- CHECKPOINT answer' END")
    assert scorer.find_checkpoint_block(source, 'answer') is None


@pytest.mark.parametrize('task', LEAN_TASKS, ids=lambda p: p.name)
@pytest.mark.parametrize('diagnostic,rejected', [('', False), ('#eval (1 + 1)', True),
    ('#eval IO.println "diagnostic"', True), ('#exit', True),
    ('-- #eval (1 + 1)', False), ('/- #eval (1 + 1) -/', False),
    ('def message := "#eval (1 + 1)"', False)])
def test_diagnostic_policy_at_submission_collection(task, diagnostic, rejected, tmp_path):
    runner = load(task / 'tests/trusted_verifier.py')
    source = 'theorem answer : 1 + 1 = 2 := by decide\n' + diagnostic + '\n'
    (tmp_path / 'Task').mkdir()
    (tmp_path / 'Task/Basic.lean').write_text(source)
    if rejected:
        with pytest.raises(ValueError, match='unsupported metaprogramming'):
            runner.collect_submission(tmp_path, 'basic-only')
    else:
        assert runner.collect_submission(tmp_path, 'basic-only') == {'Task/Basic.lean': source.encode()}


@pytest.mark.parametrize('task', LEAN_TASKS, ids=lambda p: p.name)
def test_instructions_document_executable_diagnostics(task):
    instruction = (task / 'instruction.md').read_text()
    for command in ('#eval', '#exec', '#exit', '#compile'):
        assert f'`{command}`' in instruction
    assert 'Remove these commands before submission' in instruction
    if task.parent.name == 'construction':
        assert '`native_decide` remains allowed' in instruction
