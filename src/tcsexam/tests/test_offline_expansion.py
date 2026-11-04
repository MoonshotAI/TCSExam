"""Protect frozen judging semantics when scheduling local Docker workers."""
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest

from tcsexam.layout import repository


def module(name):
    path = repository()/'assets/environments/solver/offline-runtime'/f'{name}.py'
    spec = importlib.util.spec_from_file_location('offline_'+name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class OfflineExpansion(unittest.TestCase):
    def test_preserved_checker_reference_anchors_and_metric(self):
        root = repository()
        paths = sorted((root/'tasks/solver/offline').glob('*/offline-adapter.json'))
        self.assertEqual(len(paths), 25)
        for path in paths:
            data = json.loads(path.read_text())
            source = root/data['online_source']
            target = path.parent
            with self.subTest(task=target.name):
                for leaf in ('checker.py','anchors.json','metric_config.json',
                             'metric/engine.py','metric/config.py'):
                    self.assertEqual((source/'tests'/leaf).read_bytes(),
                                     (target/'tests'/leaf).read_bytes())
                recipe=json.loads((root/f'assets/environments/solver/{target.name}/judge/rebuild.json').read_text())
                reference_source=next(row['source'] for row in recipe['sources']
                                      if row['target']=='/tests/reference.json')
                self.assertEqual((root/reference_source).read_bytes(),
                                 (target/'tests/reference.json').read_bytes())
                config = json.loads((target/'tests/runtime/task.json').read_text())
                reference = json.loads((target/'tests/reference.json').read_text())
                self.assertEqual(config['instance_count'],len(reference['instances']))
                text=(target/'instruction.md').read_text()
                self.assertNotIn('submit.sh',text)
                self.assertNotIn('except the judging service',text)
                self.assertIn('Fair play: live computation at judging time',text)

    def test_time_pools_cannot_be_split_or_lose_instances(self):
        worker = module('worker')
        reference={'instances':{'a':{'B':9,'K':2},'b':{'B':7,'K':2}},'metadata':'retained'}
        self.assertEqual(worker.restricted_reference(reference,['b','a'],True),reference)
        for keys in (['a'],['a','a'],['unknown']):
            with self.assertRaises(RuntimeError):
                worker.restricted_reference(reference,keys,True)
        result=worker.restricted_reference(reference,['a'],False)
        self.assertEqual(set(result['instances']),{'a'})
        self.assertEqual(result['metadata'],'retained')
        self.assertEqual(set(reference['instances']),{'a','b'})
        expected={'gp-dimacs10':780,'itc2021-sports-timetabling':960,
                  'logic-syn-iwls2023':4000,'qap-qaplib':1230,'scp-orlib':780}
        pools={}
        for path in (repository()/'tasks/solver/offline').glob('*/offline-adapter.json'):
            config=json.loads((path.parent/'tests/runtime/task.json').read_text())
            if config['pool']:
                pools[path.parent.name]=config['seconds']
                self.assertEqual(config['cpus'],4)
        self.assertEqual(pools,expected)
        glass=json.loads((repository()/'tasks/solver/offline/glasscut-roadef2018/tests/runtime/task.json').read_text())
        self.assertEqual(glass['seconds'],180+3600)

    def test_cpu_indices_map_inside_nonzero_reserved_cpuset(self):
        rewrite=module('judge_entry').taskset_command
        self.assertEqual(rewrite(['taskset','-c','0','/app/solver'],[17],True),
                         ['taskset','-c','17','/app/solver'])
        self.assertEqual(rewrite(['taskset','-c','0,1','/app/solver'],[17,23],True),
                         ['taskset','-c','17,23','/app/solver'])
        absolute=['taskset','-c','23','/app/solver']
        self.assertEqual(rewrite(absolute,[23],False),absolute)
        with self.assertRaises(RuntimeError):
            rewrite(['taskset','-c','1','/app/solver'],[17],True)

    def test_build_failure_and_missing_judge_data_remain_distinct(self):
        check=module('worker').checked_records
        reference={'instances':{'a':{'B':9,'K':2},'b':{'B':7,'K':2}}}
        for key in ('build_error','compile_error'):
            records=check({key:'fixture compilation failure','per_instance':{}},reference)
            self.assertEqual(set(records),{'a','b'})
            self.assertTrue(all(r['A'] is None and r['status']=='build_error'
                                for r in records.values()))
        for output in ({'per_instance':{}}, {'integrity_error':'changed tool'},
                       {'per_instance':{'a':{'A':2,'status':'ok'}}}):
            with self.assertRaises(RuntimeError):
                check(output,reference)
        with self.assertRaisesRegex(RuntimeError,'Judge data unavailable'):
            check({'per_instance':{'a':{'status':'instance file missing on judge side'},
                                   'b':{'status':'ok'}}},reference)

    def test_preparation_only_unpacks_assigned_unchanged_bytes(self):
        prepare=module('worker').preparation_files
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'a.gr.xz').write_bytes(b'compressed-original-a')
            (root/'b.gr.xz').write_bytes(b'compressed-original-b')
            (root/'manifest.json').write_text('{}')
            prepare(root,{'a.gr','b.gr'},{'a.gr'},'.xz')
            self.assertEqual((root/'a.gr.xz').read_bytes(),b'compressed-original-a')
            self.assertFalse((root/'b.gr.xz').exists())
            self.assertTrue((root/'manifest.json').is_file())
            with self.assertRaisesRegex(RuntimeError,'Judge data unavailable'):
                prepare(root,{'a.gr','b.gr'},{'b.gr'},'.xz')

    def test_metric_adapter_matches_frozen_online_status_rules(self):
        # Exercise the frozen worker's complete status contract.
        adapter=module('metric_adapter')
        anchors={'B':{'ok':10,'suffix':10,'bad':10,'verdict':10,'missing':10,
                      'numeric':10,'equal':2,'inverted':1},
                 'K':{'ok':2,'suffix':2,'bad':2,'verdict':2,'missing':2,
                      'numeric':2,'equal':2,'inverted':5}}
        records={'ok':{'A':6,'status':'ok'},'suffix':{'A':0,'status':'ok (verified)'},
                 'bad':{'A':1,'status':'invalid solution'},
                 'verdict':{'A':0,'verdict':'not solved'},'missing':{'A':1},
                 'numeric':{'A':None,'status':'ok'},'equal':{'A':1,'status':'ok'},
                 'inverted':{'A':3,'status':'ok'}}
        raw,usable,issues=adapter.prepare(records,anchors,{'shape':'gap_ratio','direction':'min'})
        normalized={r['instance']:r for r in raw}
        self.assertEqual(normalized['ok']['status'],'ok')
        self.assertEqual(normalized['suffix']['status'],'ok')
        self.assertEqual(normalized['bad']['status'],'invalid')
        self.assertIsNone(normalized['bad']['A'])
        self.assertEqual(normalized['verdict']['status'],'ok')
        self.assertEqual(normalized['missing']['status'],'error')
        self.assertEqual(normalized['numeric']['status'],'error')
        self.assertIn('equal',usable['B'])
        self.assertEqual(issues,[dict(instance='inverted',reason='anchor_direction_mismatch',B=1,K=5)])
        for value in (math.nan,math.inf,True):
            self.assertFalse(adapter.numeric(value))


if __name__ == '__main__':
    unittest.main()
