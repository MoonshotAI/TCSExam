"""Retain exact source routes while continuing the last successful build.

Only Docker calls are simulated. Recipe selection, fixed-archive verification,
manifest signing/validation, cache writes and CLI orchestration are production
implementations exercised with small input-only fixtures.
"""
from argparse import Namespace
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
from subprocess import CompletedProcess
import tarfile
from unittest.mock import patch

import pytest

from tcsexam.build import selection_artifact_path, validate_manifest
from tcsexam.cli import main,resolve
from tcsexam.tests import test_build as build_fixture
from tcsexam.resources import content_digest

NAME='qbf-judging'


@pytest.fixture
def built(tmp_path):
    case=build_fixture.Build('runTest');case.setUp()
    try:
        path=case.root/'assets/images.json'
        document=json.loads(path.read_text().replace('fixture-data',NAME))
        product=document['images'][0];product.update(task_id='qbf-qbfeval',data_split='hidden')
        path.write_text(json.dumps(document))
        payload=b'p cnf 1 1\ne 1 0\n1 0\n'
        row=dict(path='opt/qbf-judge300/ex001.qdimacs.xz',bytes=len(payload),mode='0644',sha256=hashlib.sha256(payload).hexdigest())
        manifest=case.root/product['files_manifest'];manifest.write_text(json.dumps({'files':[row]}))
        product['manifest_sha256']=hashlib.sha256(manifest.read_bytes()).hexdigest()
        product['content_digest']=content_digest([row],product['target_root'])
        case.write('assets/images.json',document)
        archive=Path(case.temporary.name)/'route-input.tar.gz'
        with tarfile.open(archive,'w:gz')as out:
            info=tarfile.TarInfo(row['path']);info.size=len(payload);info.mode=0o644;out.addfile(info,io.BytesIO(payload))
        source={'id':'qbf-judging-fixed-archive','url':None,'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
        case.write(product['recipe'],{'source':dict(source,id='fixture-source')})
        case.write('assets/data/solver/archive-import/'+NAME+'-recipe.json',{
            'format':'fixed_data_archive','archive_format':'tar+gzip','task_id':'qbf-qbfeval','data_split':'hidden',
            'manifest_sha256':product['manifest_sha256'],'source':source,
            'generator_paths':['src/tcsexam/fixed_data_archive.py']})
        case.write('src/tcsexam/fixed_data_archive.py','# fixture dependency\n')
        case.inputs={'fixture-source':archive}
        case.args.data_recipe=[NAME+'=fixed_archive'];case.args.input=[source['id']+'='+str(archive)]
        case.args.output=tmp_path/'fixed-artifacts.json'
        case.build()
        case.archive=archive;case.source=source
        yield case
    finally:case.doCleanups()


def options(case,**extra):
    fields=dict(root=case.root,command='prepare',suite='full',solver_protocol='offline',track=None,
                task=['sample'],cache=case.cache,docker_context=None,artifacts=None)
    fields.update(extra);return Namespace(**fields)


def test_fixed_route_build_publishes_a_separate_stable_continuation(built):
    exact=selection_artifact_path(built.root,built.rows,built.args)
    stable=selection_artifact_path(built.root,built.rows,built.args,recipe_specific=False)
    assert exact!=stable
    assert exact.read_bytes()==stable.read_bytes()==built.args.output.read_bytes()
    document=json.loads(stable.read_text());validate_manifest(built.root,document)
    assert next(x for x in document['images']if x['id']==NAME)['selected_data_recipe']=='fixed_archive'


def test_prepare_doctor_and_run_continue_without_retaining_archive_path(built,tmp_path,monkeypatch):
    stable=selection_artifact_path(built.root,built.rows,built.args,recipe_specific=False)
    built.archive.unlink()
    monkeypatch.setenv('TCSEXAM_API_KEY','synthetic-key')
    argv=['--root',str(built.root),'--suite','full','--task','sample','--solver-protocol','offline','--cache',str(built.cache)]
    with redirect_stdout(io.StringIO()),patch('tcsexam.runtime.materialize',return_value=([],[])) as prepare:
        assert main(['prepare',*argv,'--output',str(tmp_path/'job.json')])==0
        assert prepare.call_args.args[2].artifacts==stable
    with redirect_stdout(io.StringIO()):assert main(['doctor',*argv])==0
    with redirect_stdout(io.StringIO()),patch('tcsexam.cli.prepare',return_value={'tasks':[]}) as prepare,patch('tcsexam.cli.subprocess.call',return_value=0):
        assert main(['run',*argv,'--output',str(tmp_path/'run.json')])==0
        assert prepare.call_args.args[0].artifacts==stable


def test_default_rebuild_restores_default_route_and_keeps_exact_history(built):
    original=selection_artifact_path(built.root,built.rows,built.args);original_bytes=original.read_bytes()
    built.args.data_recipe=[];built.args.input=[];built.args.output=None
    result=built.build();stable=selection_artifact_path(built.root,built.rows,built.args)
    assert Path(result['manifest'])==stable
    data=json.loads(stable.read_text());validate_manifest(built.root,data)
    assert 'selected_data_recipe'not in next(x for x in data['images']if x['id']==NAME)
    assert original.read_bytes()==original_bytes
    wanted=options(built,data_recipe=[NAME+'=fixed_archive'],input=[built.source['id']+'='+str(built.archive)])
    assert resolve(wanted)[0]==built.root and wanted.artifacts==original
    explicit=options(built,artifacts=original)
    resolve(explicit);assert explicit.artifacts==original


def test_failed_build_does_not_replace_previous_success(built):
    stable=selection_artifact_path(built.root,built.rows,built.args,recipe_specific=False)
    prior=stable.read_bytes();built.args.data_recipe=[];built.args.input=[];built.args.output=None
    dockerfile=built.root/built.task/'tests/Dockerfile';dockerfile.write_text(dockerfile.read_text()+'# changed\n')
    original=built.execute_mock.side_effect
    def fail(command,**kw):
        if any(str(x).startswith('tcsexam/sample-verifier:')for x in command):return CompletedProcess(command,1)
        return original(command,**kw)
    built.execute_mock.side_effect=fail
    with pytest.raises(ValueError,match='sample-verifier'):built.build()
    assert stable.read_bytes()==prior


@pytest.mark.parametrize('environment,args_override',[({'DOCKER_HOST':'unix:///different.sock'},{}),({}, {'docker_context':'another-context'})])
def test_target_mismatch_never_crosses_host_or_context(built,environment,args_override):
    wanted=options(built,**args_override)
    with patch.dict('os.environ',environment):resolve(wanted)
    assert wanted.artifacts is None


def test_explicit_bad_source_never_uses_a_warm_manifest(built):
    built.archive.write_bytes(b'x'*built.source['bytes'])
    wanted=options(built,data_recipe=[NAME+'=fixed_archive'],input=[built.source['id']+'='+str(built.archive)])
    with pytest.raises(ValueError,match='hash or size'):resolve(wanted)
    wanted.input=[]
    with pytest.raises(ValueError,match='explicit --input'):resolve(wanted)


def test_explicit_recipe_rejects_a_valid_artifact_for_another_route(built):
    fixed=built.args.output
    built.args.data_recipe=[];built.args.input=[];built.args.output=None
    default=Path(built.build()['manifest'])
    wanted=options(built,data_recipe=[NAME+'=fixed_archive'],input=[built.source['id']+'='+str(built.archive)],artifacts=default)
    with pytest.raises(ValueError,match='does not match the requested data recipe'):resolve(wanted)
    wanted.artifacts=fixed;resolve(wanted);assert wanted.artifacts==fixed


def test_automatic_continuation_keeps_current_signature_validation(built):
    stable=selection_artifact_path(built.root,built.rows,built.args,recipe_specific=False)
    data=json.loads(stable.read_text());next(x for x in data['images']if x['id']==NAME)['data_recipe_signature']='0'*64
    stable.write_text(json.dumps(data))
    wanted=options(built);resolve(wanted)
    from tcsexam.setup import artifacts
    with pytest.raises(ValueError,match='Selected data recipe is stale'):artifacts(wanted.artifacts,root=built.root)


def test_unsuccessful_host_readiness_cannot_publish_a_continuation(built):
    stable=selection_artifact_path(built.root,built.rows,built.args,recipe_specific=False)
    prior=stable.read_bytes()
    with patch('tcsexam.build.setup_selection',return_value={'host_prepared':False}):
        with pytest.raises(ValueError,match='host preparation did not complete'):built.build()
    assert stable.read_bytes()==prior


def test_custom_output_failure_cannot_replace_the_stable_default(built,tmp_path):
    import os
    stable=selection_artifact_path(built.root,built.rows,built.args,recipe_specific=False)
    prior=stable.read_bytes()
    built.args.data_recipe=[];built.args.input=[];built.args.output=tmp_path/'cannot-publish.json'
    replace=os.replace
    def fail_custom(source,destination):
        if Path(destination)==built.args.output:raise OSError('synthetic custom-output failure')
        return replace(source,destination)
    with patch('tcsexam.build.os.replace',side_effect=fail_custom):
        with pytest.raises(OSError,match='custom-output failure'):built.build()
    assert stable.read_bytes()==prior


@pytest.mark.parametrize('failure', ['custom_output', 'stable_manifest'])
@pytest.mark.parametrize('existing', [True, False])
def test_fixed_route_publication_failure_restores_every_manifest(built, failure, existing):
    import os

    exact = selection_artifact_path(built.root, built.rows, built.args)
    stable = selection_artifact_path(built.root, built.rows, built.args, recipe_specific=False)
    output = built.args.output
    paths = [exact, output, stable]
    previous = {path: path.read_bytes() for path in paths}
    if not existing:
        for path in paths:
            path.unlink()
    dockerfile = built.root / built.task / 'tests/Dockerfile'
    dockerfile.write_text(dockerfile.read_text() + '# new build identity\n')
    target = output if failure == 'custom_output' else stable
    replace = os.replace

    def fail_publish(source, destination):
        if Path(destination) == target and '.tmp-' in Path(source).name:
            raise OSError('injected publication failure')
        return replace(source, destination)

    with patch('os.replace', side_effect=fail_publish):
        with pytest.raises(OSError, match='injected publication failure'):
            built.build()
    for path in paths:
        if existing:
            assert path.read_bytes() == previous[path]
        else:
            assert not path.exists()
    assert not list(output.parent.glob('*.tmp-*'))

    # A normal retry must still publish a complete, current build everywhere.
    built.build()
    assert exact.read_bytes() == stable.read_bytes() == output.read_bytes()
    validate_manifest(built.root, json.loads(exact.read_text()))
    request = options(built, data_recipe=built.args.data_recipe, input=built.args.input)
    resolve(request)
    assert request.artifacts == exact


def test_fixed_route_without_custom_output_rolls_back_when_continuation_fails(built):
    import os

    built.args.output = None
    exact = selection_artifact_path(built.root, built.rows, built.args)
    stable = selection_artifact_path(built.root, built.rows, built.args, recipe_specific=False)
    previous = {path: path.read_bytes() for path in [exact, stable]}
    dockerfile = built.root / built.task / 'tests/Dockerfile'
    dockerfile.write_text(dockerfile.read_text() + '# changed verifier\n')
    replace = os.replace

    def fail_publish(source, destination):
        if Path(destination) == stable and '.tmp-' in Path(source).name:
            raise PermissionError('injected continuation failure')
        return replace(source, destination)

    with patch('os.replace', side_effect=fail_publish):
        with pytest.raises(PermissionError, match='injected continuation failure'):
            built.build()
    assert {path: path.read_bytes() for path in previous} == previous
