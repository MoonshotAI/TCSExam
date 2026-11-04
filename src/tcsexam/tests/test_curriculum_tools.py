"""Pinned public library preparation preserves the shipped curriculum tool bytes."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from tcsexam.layout import repository
from tcsexam.resources import prepare_resource, verify
from tcsexam.solver_recipes import curriculum_tools_recipe

ROOT=repository()
ID='solver-curriculum-itc2007-development-tools'

def record():
    value=deepcopy(next(r for r in json.loads((ROOT/'assets/images.json').read_text())['images'] if r.get('id')==ID))
    curriculum_tools_recipe(ROOT,value)
    return value

def test_public_libraries_are_fixed_and_keep_original_content_identity():
    row=record();recipe=json.loads((ROOT/row['recipe']).read_text());files=json.loads((ROOT/row['files_manifest']).read_text())['files']
    assert row['recipe_format']=='official_files'
    assert row['content_digest']=='sha256:849d88e8156c9409529dad60db9be8638e5174c3100946c5be7680afb87083a2'
    assert 'source_input' not in row and 'source_input_file' not in row
    assert len(recipe['sources'])==len(recipe['outputs'])==3
    sources={r['id']:r for r in recipe['sources']}
    files={r['path']:r for r in files}
    for output in recipe['outputs']:
        source=sources[output['source_id']];expected=files[output['path']]
        assert '/a253a5a45a5b148d5a8981c3fd0af5ecf9ae4b06/lib/' in source['url']
        assert (source['bytes'],source['sha256'],source['git_blob'])==(expected['bytes'],expected['sha256'],expected['git_blob'])
        assert output['operation']=='copy'
    row['product_prepared']=True;row['runtime_verified']=True
    before=deepcopy(row);curriculum_tools_recipe(ROOT,row)
    assert row==before


def test_public_preparation_uses_checked_downloads_and_atomic_cache(tmp_path):
    # Exercise the real resource dispatcher and official_files implementation
    # with small stand-ins; the pinned real-byte download verification is separate.
    root=tmp_path/'project';root.mkdir();(root/'recipe.json').write_text(json.dumps({'sources':[{'id':'library','url':'https://example.invalid/fixed.jar','bytes':3,'sha256':hashlib.sha256(b'jar').hexdigest()}],'outputs':[{'path':'app/lib/core.jar','source_id':'library','operation':'copy'}]}))
    files=[{'path':'app/lib/core.jar','bytes':3,'sha256':hashlib.sha256(b'jar').hexdigest(),'mode':'0644'}]
    (root/'files.json').write_text(json.dumps({'files':files}))
    row={'id':ID,'content_version':'test','target_root':'/','recipe_format':'official_files','recipe':'recipe.json','files_manifest':'files.json','manifest_sha256':hashlib.sha256((root/'files.json').read_bytes()).hexdigest()}
    supplied=tmp_path/'core.jar';supplied.write_bytes(b'jar')
    with patch('tcsexam.resources.resource_by_id',return_value=row):
        result=prepare_resource(root,ID,tmp_path/'cache',inputs={'library':supplied})
        assert verify(result,files)=={'files':1,'bytes':3}
        assert prepare_resource(root,ID,tmp_path/'cache',inputs={})==result
    supplied.write_bytes(b'bad')
    with patch('tcsexam.resources.resource_by_id',return_value=row), pytest.raises(ValueError):
        prepare_resource(root,ID,tmp_path/'bad-cache',inputs={'library':supplied})
    assert not (tmp_path/'bad-cache'/ID/'test').exists()
