"""Missing baseline data must not turn an invalid or unknown result into success."""
import importlib.util
import pytest
from tcsexam.layout import repository
from tcsexam.backend.sessions import aggregate_public, five_numbers


@pytest.fixture(params=['judge-runtime', 'bpp-bpplib/judge', 'hs-pace2025/judge'])
def worker(request):
    spec = importlib.util.spec_from_file_location('unsolved_' + request.param.replace('/', '_'),
        repository() / 'assets/environments/solver' / request.param / 'judge_worker.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('raw,status,objective', [
    ({'A': 7, 'status': 'ok'}, 'ok', 7),
    ({'A': None, 'status': 'invalid solution (3 hard violations)'}, 'invalid', None),
    ({'A': 7, 'status': 'timeout'}, 'invalid', None),
    ({'A': None, 'status': 'ok'}, 'error', None),
    ({'A': 7}, 'error', 7),
])
def test_unsolved_baseline_retains_outcome_and_original_statistical_exclusion(worker, raw, status, objective):
    records, names, side, note = worker._build_records({'per_instance': {
        'no-baseline': {'B': None, 'K': 3, 'anchor_baseline_unsolved': True, **raw}}})
    assert not names and not side and not note
    rec = records[0]
    assert rec['status'] == status and rec['A'] == objective
    assert rec['anchor_baseline_unsolved'] is True
    old = {**rec, 'status': 'ok'}
    old.pop('anchor_baseline_unsolved')
    assert five_numbers(records) == five_numbers([old]) == {
        'better': 0, 'equal': 0, 'worse': 0, 'delta': 0, 'failed': 0}
    feedback = aggregate_public([{'submissions': [{'submission': 0, 'status': 'ok', 'records': records}]}])
    entry = feedback['submissions'][0]['records'][0]
    assert entry['status'] == status and entry['A'] == objective
    assert 'B' not in entry and 'K' not in entry


def test_missing_baseline_without_explicit_marker_is_still_pipeline_error(worker):
    records, _, _, _ = worker._build_records({'per_instance': {
        'broken': {'A': 5, 'B': None, 'K': 3, 'status': 'ok'}}})
    assert records[0]['status'] == 'error'
    assert five_numbers(records)['failed'] == 1


def test_invalid_status_without_exclusion_marker_keeps_legacy_counting():
    assert five_numbers([{'A': None, 'B': None, 'K': 3, 'status': 'invalid'}])['worse'] == 1
    assert five_numbers([{'A': None, 'B': None, 'K': None, 'status': 'error',
                          'anchor_baseline_unsolved': True}])['failed'] == 1


def test_actual_sports_public_pool_keeps_all_29_outcomes_and_original_statistics(worker):
    import json
    from tcsexam.backend.sessions import aggregate_submissions
    fixture = repository() / 'src/tcsexam/tests/fixtures/sports_public_reward_261030.json'
    reward = json.loads(fixture.read_text())
    records, names, side, note = worker._build_records(reward)
    assert len(records) == 29 and not names and not side and not note
    assert {r['instance'] for r in records} == set(reward['per_instance'])
    assert sum(r['status'] == 'ok' for r in records) == 8
    assert sum(r['status'] == 'invalid' for r in records) == 21
    for r in records:
        raw = reward['per_instance'][r['instance']]
        assert r['A'] == raw['A']
        if raw['B'] is None:
            assert r['status'] == 'invalid' and r['A'] is None
            assert r['anchor_baseline_unsolved'] is True
        else:
            assert r['status'] == 'ok' and r['A'] == raw['B']
    old_records = [{**r, 'status': 'ok'} if r['B'] is None else dict(r) for r in records]
    for r in old_records:
        r.pop('anchor_baseline_unsolved', None)
    assert five_numbers(old_records) == five_numbers(records) == {
        'better': 0, 'equal': 8, 'worse': 0, 'failed': 0, 'delta': 0}
    shards = [{'submissions': [{'submission': 0, 'status': 'ok', 'records': records}]}]
    public = aggregate_public(shards)['submissions'][0]['records']
    assert len(public) == 29 and sum(r['status'] == 'invalid' for r in public) == 21
    hidden = aggregate_submissions(shards)['submissions'][0]
    assert hidden['equal'] == 8 and hidden['worse'] == hidden['failed'] == 0
