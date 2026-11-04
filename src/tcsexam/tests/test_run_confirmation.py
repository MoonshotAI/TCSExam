"""Host environment approval is explicit and forwarded only when requested."""
from unittest.mock import patch
import pytest
from tcsexam.cli import main


@pytest.mark.parametrize('flag,expected', [([], False), (['--yes'], True), (['-y'], True)])
def test_run_environment_confirmation_is_explicit(tmp_path, monkeypatch, flag, expected):
    monkeypatch.setenv('TCSEXAM_API_KEY', 'unused-no-model')
    row = {'track': 'solver'}
    with patch('tcsexam.cli.resolve', return_value=(tmp_path, [row])), \
         patch('tcsexam.cli.require_paths'), \
         patch('tcsexam.setup.setup_selection', return_value={}), \
         patch('tcsexam.cli.doctor', return_value=0), \
         patch('tcsexam.cli.prepare', return_value={'tasks': [row]}), \
         patch('tcsexam.cli.subprocess.call', return_value=0) as launch:
        assert main(['run', '--output', str(tmp_path / 'job.json'), *flag]) == 0
    command = launch.call_args.args[0]
    assert ('--yes' in command) is expected
    assert 'tcsexam.harbor_launch' in command
    assert '--share' not in command and '--upload' not in command
