"""Signature/grammar regressions with synthetic inputs; no cvc5 process runs."""
import importlib.util
from pathlib import Path
from unittest.mock import Mock

import pytest

ROOT=Path(__file__).resolve().parents[3]
COPIES=['assets/environments/solver/sygus-comp/judge/sygus_check.py',
        'tasks/solver/online/sygus-comp/environment/app/sygus_check.py']


@pytest.fixture(params=COPIES)
def checker(request):
    spec=importlib.util.spec_from_file_location('synthetic_sygus_checker',ROOT/request.param)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def benchmark(tmp_path,params='((x Int))',grammar=False):
    path=tmp_path/'input.sl'
    section=' ((Start Int (0 x)))' if grammar else ''
    path.write_text(f'(set-logic ALL)\n(synth-fun f {params} Int{section})\n'
                    '(constraint true)\n(check-synth)\n')
    return path


@pytest.mark.parametrize('definition,reason',[
    ('(define-fun f () Int 0)','parameter count mismatch'),
    ('(define-fun f ((x Int) (y Int)) Int 0)','parameter count mismatch'),
    ('(define-fun f ((renamed Bool)) Int 0)','parameter sort mismatch'),
])
@pytest.mark.parametrize('grammar',[False,True])
def test_constant_body_cannot_hide_bad_signature(checker,tmp_path,definition,reason,grammar):
    # A constant body with no grammar can pass semantic checking despite an
    # unused, wrongly typed extra parameter. Reject before invoking cvc5.
    checker.semantic_check=Mock(side_effect=AssertionError('Semantic solver must not run'))
    valid,why=checker.check_answer(benchmark(tmp_path,grammar=grammar),definition)
    assert valid is False and reason in why
    checker.semantic_check.assert_not_called()


@pytest.mark.parametrize('expected,actual',[
    ('(_ BitVec 8)','(_ BitVec 16)'),
    ('(Array Int (_ BitVec 8))','(Array Bool (_ BitVec 8))'),
    ('(Array Int (_ BitVec 8))','(Array Int (_ BitVec 16))'),
    ('Int','(Array Int Int)'),
])
def test_compound_and_indexed_parameter_sorts_reject_mismatch(checker,tmp_path,expected,actual):
    checker.semantic_check=Mock(side_effect=AssertionError('Semantic solver must not run'))
    valid,why=checker.check_answer(benchmark(tmp_path,params=f'((x {expected}))'),
                                   f'(define-fun f ((renamed {actual})) Int 0)')
    assert valid is False and 'parameter sort mismatch' in why
    checker.semantic_check.assert_not_called()


@pytest.mark.parametrize('sort', ['Int','Bool','(_ BitVec 8)','(Array Int (_ BitVec 8))'])
def test_parameter_alpha_renaming_and_matching_compound_sorts(checker,tmp_path,sort):
    checker.semantic_check=Mock(return_value=(True,None))
    assert checker.check_answer(benchmark(tmp_path,params=f'((x {sort}))'),
                                f'(define-fun f ((renamed {sort})) Int 0)')==(True,None)
    checker.semantic_check.assert_called_once()


def test_grammar_parameter_can_be_renamed(checker,tmp_path):
    checker.semantic_check=Mock(return_value=(True,None))
    assert checker.check_answer(benchmark(tmp_path,grammar=True),
                                '(define-fun f ((renamed Int)) Int renamed)')==(True,None)
    checker.semantic_check.assert_called_once()


def test_legacy_bitvector_sort_spelling_uses_existing_normalization(checker):
    sx=checker.parse_sexprs
    synth=checker.SynthFun('f',[('x',sx('(_ BitVec 8)')[0])],checker.Sx('Int'),None,False)
    assert checker.grammar_check(synth,[('renamed',sx('(BitVec 8)')[0])],checker.Sx('0'))==(True,None)


def test_duplicate_formals_rejected_before_parameter_map_can_collapse(checker,tmp_path):
    checker.semantic_check=Mock(side_effect=AssertionError('Semantic solver must not run'))
    valid,why=checker.check_answer(benchmark(tmp_path,params='((x Int) (y Int))'),
                                   '(define-fun f ((same Int) (same Int)) Int 0)')
    assert valid is False and 'duplicate solution parameter' in why
    checker.semantic_check.assert_not_called()


def test_correct_signature_does_not_bypass_grammar(checker,tmp_path):
    checker.semantic_check=Mock(side_effect=AssertionError('Semantic solver must not run'))
    valid,why=checker.check_answer(benchmark(tmp_path,grammar=True),
                                   '(define-fun f ((renamed Int)) Int 999)')
    assert valid is False and 'not derivable' in why
    checker.semantic_check.assert_not_called()
