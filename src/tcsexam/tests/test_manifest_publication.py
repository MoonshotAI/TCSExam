"""Exercise filesystem failures and overlapping build-record publication."""
import json
import os
from pathlib import Path
import threading
from unittest.mock import patch

import pytest

from tcsexam import build


@pytest.mark.parametrize('output_name', ['exact.json.lock', 'another-selection.json.lock'])
def test_output_cannot_replace_a_publication_lock(tmp_path, output_name):
    directory = tmp_path / 'new-output-directory'
    paths = [directory / 'exact.json', directory / output_name, directory / 'stable.json']
    with pytest.raises(ValueError, match='reserved .lock suffix'):
        build.publish_selection_manifests(paths, {'new': True})
    assert not directory.exists()


def test_staging_failure_leaves_all_prior_records_untouched(tmp_path):
    paths = [tmp_path / 'exact.json', tmp_path / 'stable.json']
    for path in paths:
        path.write_text('original record\n')
    save = build.save_record

    def fail_stage(path, value):
        if path.name.startswith('stable.json.tmp-'):
            raise OSError('disk full during staging')
        return save(path, value)

    with patch('tcsexam.build.save_record', side_effect=fail_stage):
        with pytest.raises(OSError, match='disk full'):
            build.publish_selection_manifests(paths, {'new': True})
    assert all(path.read_text() == 'original record\n' for path in paths)
    assert not list(tmp_path.glob('*.tmp-*'))
    assert not list(tmp_path.glob('*.rollback-*'))


@pytest.mark.parametrize('interruption', [KeyboardInterrupt, SystemExit])
@pytest.mark.parametrize('target_exists', [False, True])
def test_interruption_after_replacement_restores_all_outputs(tmp_path, interruption, target_exists):
    paths = [tmp_path / name for name in ('first.json', 'target.json', 'last.json')]
    for index, path in enumerate(paths):
        if index != 1 or target_exists:
            path.write_text(f'original {index}\n')
    replace = os.replace

    def interrupt_after_replace(source, destination):
        replace(source, destination)
        if Path(destination) == paths[1] and '.tmp-' in Path(source).name:
            raise interruption('interrupted after filesystem replacement')

    with patch('os.replace', side_effect=interrupt_after_replace):
        with pytest.raises(interruption, match='interrupted after filesystem replacement'):
            build.publish_selection_manifests(paths, {'new': True})
    for index, path in enumerate(paths):
        if index != 1 or target_exists:
            assert path.read_text() == f'original {index}\n'
        else:
            assert not path.exists()
    assert not list(tmp_path.glob('*.tmp-*'))
    assert not list(tmp_path.glob('*.rollback-*'))


def test_rollback_failure_retains_prior_bytes_and_reports_the_backup(tmp_path):
    paths = [tmp_path / 'exact.json', tmp_path / 'stable.json']
    for path in paths:
        path.write_text('original record\n')
    replace = os.replace

    def fail_replace(source, destination):
        if Path(destination) == paths[1] or '.rollback-' in Path(source).name:
            raise PermissionError('filesystem unavailable')
        return replace(source, destination)

    with patch('os.replace', side_effect=fail_replace):
        with pytest.raises(RuntimeError, match='rollback was incomplete') as caught:
            build.publish_selection_manifests(paths, {'new': True})
    backups = list(tmp_path.glob('*.rollback-*'))
    assert len(backups) == 2
    assert all(backup.read_text() == 'original record\n' for backup in backups)
    assert all(str(backup) in str(caught.value) for backup in backups)
    assert json.loads(paths[0].read_text()) == {'new': True}
    assert paths[1].read_text() == 'original record\n'


@pytest.mark.parametrize('interruption', [KeyboardInterrupt, SystemExit])
def test_rollback_interruption_retains_backup_and_restores_other_records(tmp_path, interruption):
    paths = [tmp_path / name for name in ('exact.json', 'custom.json', 'stable.json')]
    for path in paths:
        path.write_text('original record\n')
    replace = os.replace
    interrupted = False

    def fail_replace(source, destination):
        nonlocal interrupted
        if Path(destination) == paths[2] and '.tmp-' in Path(source).name:
            raise OSError('publication failed')
        if '.rollback-' in Path(source).name and Path(destination) == paths[1] and not interrupted:
            interrupted = True
            raise interruption('interrupted restoration')
        return replace(source, destination)

    with patch('os.replace', side_effect=fail_replace):
        with pytest.raises(RuntimeError, match='rollback was incomplete') as caught:
            build.publish_selection_manifests(paths, {'new': True})
    backups = list(tmp_path.glob('*.rollback-*'))
    assert len(backups) == 1
    assert backups[0].read_text() == 'original record\n'
    assert str(backups[0]) in str(caught.value)
    assert paths[0].read_text() == paths[2].read_text() == 'original record\n'
    assert json.loads(paths[1].read_text()) == {'new': True}
    assert not list(tmp_path.glob('*.tmp-*'))


def test_interrupted_rollback_of_new_path_still_restores_prior_records(tmp_path):
    paths = [tmp_path / name for name in ('existing.json', 'new.json', 'last.json')]
    paths[0].write_text('original record\n')
    replace, unlink = os.replace, Path.unlink

    def fail_publish(source, destination):
        if Path(destination) == paths[2]:
            raise OSError('publication failed')
        return replace(source, destination)

    def interrupt_unlink(path, *args, **kwargs):
        if path == paths[1]:
            raise KeyboardInterrupt('interrupted removal')
        return unlink(path, *args, **kwargs)

    with patch('os.replace', side_effect=fail_publish), patch.object(Path, 'unlink', interrupt_unlink):
        with pytest.raises(RuntimeError, match='previous record: absent'):
            build.publish_selection_manifests(paths, {'new': True})
    assert paths[0].read_text() == 'original record\n'
    assert json.loads(paths[1].read_text()) == {'new': True}
    assert not paths[2].exists()


def test_overlapping_publisher_cannot_be_overwritten_by_another_rollback(tmp_path):
    paths = [tmp_path / 'exact.json', tmp_path / 'stable.json']
    for path in paths:
        path.write_text('original record\n')
    stalled, contender_waiting, release = (threading.Event() for _ in range(3))
    completed = threading.Event()
    failures = []
    replace, flock = os.replace, build.fcntl.flock

    def controlled_replace(source, destination):
        if (threading.current_thread().name == 'failing-publisher'
                and Path(destination) == paths[1] and '.tmp-' in Path(source).name):
            stalled.set()
            if not release.wait(5):
                raise AssertionError('test did not release the publisher')
            raise OSError('injected publication failure')
        return replace(source, destination)

    def observed_lock(fd, operation):
        if threading.current_thread().name == 'successful-publisher':
            contender_waiting.set()
        return flock(fd, operation)

    def publish(name):
        try:
            # Opposite order also exercises deterministic lock acquisition.
            requested = paths if name == 'failed' else list(reversed(paths))
            build.publish_selection_manifests(requested, {'build': name})
            if name == 'successful':
                completed.set()
        except BaseException as error:
            failures.append((name, error))

    first = threading.Thread(target=publish, args=('failed',), name='failing-publisher')
    second = threading.Thread(target=publish, args=('successful',), name='successful-publisher')
    with patch('os.replace', side_effect=controlled_replace), patch('tcsexam.build.fcntl.flock', side_effect=observed_lock):
        first.start()
        try:
            assert stalled.wait(5)
            second.start()
            assert contender_waiting.wait(5)
            assert not completed.is_set()
        finally:
            release.set()
            first.join(5)
            if second.ident is not None:
                second.join(5)
        assert not first.is_alive() and not second.is_alive()
    assert len(failures) == 1 and failures[0][0] == 'failed'
    assert isinstance(failures[0][1], OSError)
    assert completed.is_set()
    assert all(json.loads(path.read_text()) == {'build': 'successful'} for path in paths)
    assert not list(tmp_path.glob('*.rollback-*'))
