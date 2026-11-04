"""Use one finite transfer budget across curl retries and the container wait."""
import hashlib
from pathlib import Path

import pytest

from tcsexam.resources import download_official, official_download_limits


@pytest.mark.parametrize('configured,transfer,outer', [(None, 120, 300), (300, 300, 480),
                                                       (1200, 1200, 1380), (3600, 3600, 3780), (1, 1, 181)])
def test_download_command_and_outer_wait_share_the_same_budget(tmp_path, monkeypatch, configured, transfer, outer):
    source = {'url': 'https://example.com/official.zip', 'bytes': 4,
              'sha256': hashlib.sha256(b'data').hexdigest()}
    build = {'builder_image': 'ubuntu:22.04@sha256:' + 'a' * 64}
    if configured is not None:
        build['download_timeout_sec'] = configured
    calls = []
    def container(command, timeout, logs, **kwargs):
        calls.append((command, timeout))
        assert timeout == outer
        assert command[-3:] == [source['url'], source['sha256'], '4']
        setup = command[command.index('/bin/sh') + 3]
        assert f'timeout --signal=TERM --kill-after=10 {transfer}s curl ' in setup
        assert f'--max-time {transfer} --retry-max-time {transfer} ' in setup
        assert '--retry 2' in setup
        assert 'sha256sum -c -' in setup
        assert 'stat -c %s /out/source' in setup
        Path(kwargs['copy_out'][0][1]).write_bytes(b'data')
    monkeypatch.setattr('tcsexam.resources.run_official_container', container)
    result = download_official(source, tmp_path / 'cache', build, 'fixture-builder')
    assert result.read_bytes() == b'data'
    # A checked cache is reused without a second transfer.
    assert download_official(source, tmp_path / 'cache', build, 'fixture-builder') == result
    assert len(calls) == 1


@pytest.mark.parametrize('invalid', [0, -1, True, False, '1200', '120; false', 1.5,
                                     float('inf'), float('-inf'), float('nan'), None, 2 ** 31])
def test_invalid_download_budget_is_rejected_before_network_or_cache(tmp_path, monkeypatch, invalid):
    build = {'download_timeout_sec': invalid}
    with pytest.raises(ValueError, match='positive finite integer'):
        official_download_limits(build)
    monkeypatch.setattr('tcsexam.resources.run_official_container',
                        lambda *a, **k: pytest.fail('Invalid configuration must not run Docker'))
    with pytest.raises(ValueError, match='positive finite integer'):
        download_official({'sha256': '0' * 64}, tmp_path / 'cache', build, 'fixture-builder')
    assert not (tmp_path / 'cache').exists()
