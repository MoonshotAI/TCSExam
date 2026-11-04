"""Worker normalization preserves computed public results outside the hidden mean."""
import importlib.util
from pathlib import Path
import pytest
from tcsexam.layout import repository
from tcsexam.backend.sessions import aggregate_public, aggregate_submissions


@pytest.fixture(params=['judge-runtime', 'bpp-bpplib/judge'])
def worker(request):
    path = repository() / 'assets/environments/solver' / request.param / 'judge_worker.py'
    spec = importlib.util.spec_from_file_location('worker_excluded_' + request.param.replace('/', '_'), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def payload(worker, table, **extra):
    records, names, excluded, note = worker._build_records({'per_instance': table, **extra})
    return {'submissions': [{'submission': 0, 'status': 'ok', 'ts': 1,
                            'records': records, 'excluded_no_signal': names,
                            'excluded_records': excluded, 'detail': note}]}


def test_hundred_public_results_include_equal_anchor_without_changing_hidden_mean(worker):
    table = {f'heur{i:03}.gr': {'A': 24, 'B': 24, 'K': 10, 'status': 'ok'}
             for i in range(1, 101)}
    table['heur033.gr'] = {'A': 10, 'B': 10, 'K': 10, 'status': 'ok'}
    shards = [payload(worker, dict(list(table.items())[i::2])) for i in range(2)]
    public = aggregate_public(shards)['submissions'][0]['records']
    assert len(public) == 100
    assert {r['instance'] for r in public} == set(table)
    flat = next(r for r in public if r['instance'] == 'heur033.gr')
    assert flat['A'] == 10 and flat['status'] == 'ok' and flat['reason'] == 'b_equals_k'
    assert all('B' not in r and 'K' not in r for r in public)
    hidden = aggregate_submissions(shards)['submissions'][0]
    assert len(hidden['records']) == 99
    assert 'heur033.gr' not in {r['instance'] for r in hidden['records']}


@pytest.mark.parametrize('bad,expected', [
    ({'A': 7, 'status': 'invalid solution'}, 'invalid'),
    ({'A': None, 'status': 'ok'}, 'error'),
    ({'A': 7}, 'error'),
])
def test_excluded_result_normalizes_invalid_and_pipeline_errors(worker, bad, expected):
    entry = payload(worker, {'flat': {'B': 5, 'K': 5, **bad}})['submissions'][0]
    assert entry['records'] == [] and entry['excluded_no_signal'] == ['flat']
    result = entry['excluded_records'][0]
    assert result['status'] == expected
    if expected == 'invalid':
        assert result['A'] is None


def test_missing_anchor_stays_error_and_solve_rate_keeps_equal_anchor(worker):
    entry = payload(worker, {'broken': {'A': 1, 'B': None, 'K': 2, 'status': 'ok'}})['submissions'][0]
    assert entry['records'][0]['status'] == 'error'
    assert entry['excluded_records'] == []
    entry = payload(worker, {'flat': {'A': 1, 'B': 1, 'K': 1, 'status': 'ok'}},
                    scoring_caliber='all-keys-solve-rate-260917')['submissions'][0]
    assert len(entry['records']) == 1 and entry['excluded_records'] == []
