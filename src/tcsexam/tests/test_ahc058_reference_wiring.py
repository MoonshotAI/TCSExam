"""The current checker, fixed payload and runtime reference must share keys."""
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[3]
class AhcReferenceWiring(unittest.TestCase):
 def test_hidden_copy_uses_the_existing45_key_reference(self):
  docker=(ROOT/'assets/environments/solver/ahc058-atcoder/judge/Dockerfile.hidden').read_text()
  self.assertIn('COPY tasks/solver/online/ahc058-atcoder/tests/reference-hidden.json /tests/reference.json',docker)
  hidden=json.loads((ROOT/'tasks/solver/online/ahc058-atcoder/tests/reference-hidden.json').read_text())['instances']
  offline=json.loads((ROOT/'tasks/solver/offline/ahc058-atcoder/tests/reference.json').read_text())['instances']
  anchors=json.loads((ROOT/'tasks/solver/online/ahc058-atcoder/tests/anchors.json').read_text())
  files=json.loads((ROOT/'assets/data/solver/solver-ahc058-atcoder-judging-data-files.json').read_text())['files']
  self.assertEqual(hidden,offline);self.assertEqual(set(hidden),set(anchors['B']));self.assertEqual(set(hidden),{Path(r['path']).name for r in files});self.assertEqual(len(hidden),45)
 def test_public_original105_keys_are_preserved(self):
  public=json.loads((ROOT/'tasks/solver/online/ahc058-atcoder/environment/app/public_reference.json').read_text())['instances'];files=json.loads((ROOT/'assets/data/solver/solver-ahc058-atcoder-development-data-files.json').read_text())['files'];self.assertEqual(len(public),105);self.assertEqual(set(public),{Path(r['path']).name for r in files})
 def test_capacity_uses_the_actual_controller_reference_for_all30_tasks(self):
  from tcsexam.solver_capacity import solver_task_spec
  tasks=sorted((ROOT/'tasks/solver/online').iterdir())
  self.assertEqual(len(tasks),30)
  for task in tasks:
   with self.subTest(task=task.name):
    actual=json.loads((ROOT/'tasks/solver/offline'/task.name/'tests/reference.json').read_text())['instances']
    spec=solver_task_spec(ROOT,task.name,'hidden');self.assertEqual(spec['instance_count'],len(actual))
    public=solver_task_spec(ROOT,task.name,'public');key='tasks/solver/offline/'+task.name+'/tests/reference.json'
    self.assertIn(key,public['source_sha256'])
    import hashlib
    self.assertEqual(public['source_sha256'][key],hashlib.sha256((ROOT/key).read_bytes()).hexdigest())
    if task.name=='ahc058-atcoder':
     self.assertEqual(spec['instance_count'],45);self.assertEqual(spec['per_instance_seconds'],2)
if __name__=='__main__':unittest.main()
