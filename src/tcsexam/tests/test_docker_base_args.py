"""Docker global ARG defaults must preserve the selected base and mirrors."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
from tcsexam.build import ImageBuilder, docker_from_instructions

PIN='python:3.12-slim@sha256:'+'a'*64
OTHER='python:3.13-slim@sha256:'+'b'*64
class DockerBaseArguments(unittest.TestCase):
 def setUp(self):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=Path(t.name);self.file=self.root/'Dockerfile'
 def write(self,text):self.file.write_text(text);return self.file
 def test_global_default_and_explicit_override(self):
  self.write('ARG BASE="'+PIN+'"\nFROM $BASE\n')
  self.assertEqual(next(docker_from_instructions(self.file,{}))[2],PIN)
  self.assertEqual(next(docker_from_instructions(self.file,{'BASE':OTHER}))[2],OTHER)
 def test_stage_args_do_not_override_global_from_scope(self):
  self.write('ARG BASE='+PIN+'\nFROM $BASE AS first\nARG BASE='+OTHER+'\nFROM ${BASE}\nFROM first AS final\n')
  self.assertEqual([r[2] for r in docker_from_instructions(self.file,{})],[PIN,PIN,'first'])
  builder=object.__new__(ImageBuilder);builder.references={};builder.local_aliases=set();builder.acquire=Mock(return_value={})
  builder.prepare_bases(self.file,{});self.assertEqual([c.args[0] for c in builder.acquire.call_args_list],[PIN,PIN])
 def test_mirror_rewrite_preserves_flags_alias_newlines_and_other_bytes(self):
  original='ARG BASE='+PIN+'\n# keep\nFROM --platform=linux/amd64 ${BASE} AS build\nRUN true\n';self.write(original)
  out=self.root/'generated';ImageBuilder.rewrite_bases(self.file,{PIN:'registry.example/pinned:fixed'},out)
  self.assertEqual(out.read_text(),original.replace('${BASE}','registry.example/pinned:fixed'))
 def test_missing_argument_rejected_and_prefixes_not_confused(self):
  self.write('ARG BASE='+PIN+'\nFROM $BASE_OTHER\n')
  with self.assertRaisesRegex(ValueError,'Unresolved Docker base argument'):list(docker_from_instructions(self.file,{}))
 def test_real_nurse_pinned_default(self):
  path=Path(__file__).resolve().parents[3]/'tasks/solver/online/nurse-inrc/environment/Dockerfile'
  rows=list(docker_from_instructions(path,{'TCSEXAM_PUBLIC_DATA_IMAGE':'tcsexam/data:fixed'}))
  self.assertEqual(rows[0][2],'tcsexam/data:fixed')
  self.assertEqual(rows[1][2],'python:3.12-slim@sha256:cab2dbf575e971934a81e4622f5aba17aa7929719bd7e31033a3a83b97fd0464')
if __name__=='__main__':unittest.main()
