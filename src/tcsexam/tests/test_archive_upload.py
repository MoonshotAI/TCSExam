"""Recover only failed initial uploads, with fresh admitted workers and no score."""
from concurrent.futures import Future
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from tcsexam.layout import repository


def modules():
    root = repository()/'assets/environments/solver/offline-runtime'
    loaded = {}
    for name in ('docker_api', 'resources', 'admission', 'controller'):
        spec = importlib.util.spec_from_file_location(name, root/(name+'.py'))
        value = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, loaded):
            spec.loader.exec_module(value)
        loaded[name] = value
    return loaded


class ArchiveUpload(unittest.TestCase):
    def setUp(self):
        self.loaded = modules()
        self.api = self.loaded['docker_api']
        self.controller = self.loaded['controller']

    def test_broken_pipe_preserves_actual_http_error_and_short_response_timeout(self):
        connection = Mock()
        failure = BrokenPipeError('daemon stopped reading')
        connection.request.side_effect = failure
        response = connection.getresponse.return_value
        response.status = 404
        response.read.return_value = b'{"message":"missing archive destination"}'
        with patch.object(self.api, 'UnixHTTP', return_value=connection):
            with self.assertRaises(self.api.DockerError) as caught:
                self.api.Docker().put_archive('worker', '/', io.BytesIO(b'tar'))
        self.assertEqual(caught.exception.status, 404)
        self.assertEqual(json.loads(caught.exception.message)['message'], 'missing archive destination')
        self.assertIs(caught.exception.__cause__, failure)
        connection.sock.settimeout.assert_called_once_with(5)
        connection.close.assert_called_once()

    def test_broken_pipe_without_error_response_cannot_become_success(self):
        for no_response in (False, True):
            with self.subTest(no_response=no_response):
                connection = Mock()
                failure = BrokenPipeError('truncated upload')
                connection.request.side_effect = failure
                if no_response:
                    connection.getresponse.side_effect = TimeoutError('no response')
                else:
                    connection.getresponse.return_value.status = 200
                    connection.getresponse.return_value.read.return_value = b''
                with patch.object(self.api, 'UnixHTTP', return_value=connection):
                    with self.assertRaises(BrokenPipeError) as caught:
                        self.api.Docker().put_archive('worker', '/', io.BytesIO(b'tar'))
                self.assertIs(caught.exception, failure)
                connection.close.assert_called_once()

    def test_docker_api_version_is_upgraded_when_daemon_requires_it(self):
        first = Mock()
        first.getresponse.return_value.status = 400
        first.getresponse.return_value.read.return_value = (
            b'{"message":"client version 1.41 is too old. Minimum supported API version is 1.44, please upgrade your client to a newer version"}')
        second = Mock()
        second.getresponse.return_value.status = 200
        second.getresponse.return_value.read.return_value = b'{}'
        with patch.object(self.api, 'UnixHTTP', side_effect=[first, second]):
            self.assertEqual(self.api.Docker().call('GET', '/info'), {})
        first.request.assert_called_once_with('GET', '/v1.41/info', body=None, headers={})
        second.request.assert_called_once_with('GET', '/v1.44/info', body=None, headers={})
        first.close.assert_called_once()
        second.close.assert_called_once()

    def worker(self, *, status='created', owner='controller', task='example', pid=0):
        return {'Id':'worker', 'State':{'Status':status,'Running':status=='running','Pid':pid},
                'Config':{'Labels':{self.controller.PREFIX+'.owner':owner,
                                   self.controller.PREFIX+'.unit':task}}}

    def test_only_exact_initial_404_of_owned_created_worker_can_be_recovered(self):
        message = json.dumps({'message':'Could not find the file / in container worker'})
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder)/'submission.tar'
            archive.write_bytes(b'one frozen submission')
            for changes in ({}, {'status':'running'}, {'owner':'other'},
                            {'task':'other'}, {'pid':123}):
                with self.subTest(changes=changes):
                    docker = Mock()
                    docker.put_archive.side_effect = self.api.DockerError(404, message)
                    docker.inspect.return_value = self.worker(**changes)
                    expected = self.controller.ArchiveUploadUnavailable if not changes else self.api.DockerError
                    with self.assertRaises(expected):
                        self.controller.upload_submission(docker, 'worker', archive,
                                                          {'task':'example'}, 'controller')
                    docker.start.assert_not_called()

    def test_other_archive_errors_are_not_retried_or_reclassified(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder)/'submission.tar'
            archive.write_bytes(b'unchanged')
            for status, message in ((404,'No such container'), (500,'backend error'),
                                    (404,'Could not find the file /other in container worker')):
                with self.subTest(status=status, message=message):
                    docker = Mock()
                    failure = self.api.DockerError(status,json.dumps({'message':message}))
                    docker.put_archive.side_effect = failure
                    with self.assertRaises(self.api.DockerError) as caught:
                        self.controller.upload_submission(docker,'worker',archive,
                                                          {'task':'example'},'controller')
                    self.assertIs(caught.exception,failure)
                    docker.inspect.assert_not_called()

    def test_failed_state_check_preserves_initial_http_error(self):
        with tempfile.TemporaryDirectory() as folder:
            archive=Path(folder)/'submission.tar';archive.write_bytes(b'unchanged')
            docker=Mock()
            failure=self.api.DockerError(404,json.dumps({
                'message':'Could not find the file / in container worker'}))
            docker.put_archive.side_effect=failure
            docker.inspect.side_effect=TimeoutError('inspection timeout')
            with self.assertRaisesRegex(self.controller.EnvironmentUnavailable,'HTTP 404.*inspection timeout') as caught:
                self.controller.upload_submission(docker,'worker',archive,{'task':'example'},'controller')
            self.assertIs(caught.exception.__cause__,failure)

    def test_failed_cleanup_keeps_worker_for_another_cleanup_attempt(self):
        with tempfile.TemporaryDirectory() as folder:
            active={'first':('worker-1',['key']), 'second':('worker-2',['other'])}
            trace={'events':[]}
            docker=Mock()
            docker.remove.side_effect=[OSError('temporary removal failure'),None,None]
            with patch.object(self.controller,'OUT',Path(folder)):
                self.assertEqual(self.controller.release_workers(docker,active,trace),['worker-1'])
                self.assertEqual(active,{'first':('worker-1',['key'])})
                self.assertEqual(self.controller.release_workers(docker,active,trace),[])
            self.assertFalse(active)
            self.assertEqual(trace['events'][0]['container'],'worker-1')
            saved=json.loads((Path(folder)/'resources.json').read_text())
            self.assertEqual(saved['events'],trace['events'])

    def test_recovery_preserves_key_group_and_stops_after_three_workers(self):
        controller = self.controller
        group = ['first','second']
        pending, failures, trace = [], {}, {'events':[]}
        error = controller.ArchiveUploadUnavailable('actual HTTP 404')
        for attempt in range(1,4):
            if attempt < 3:
                controller.retry_upload_failure(error,'worker-'+str(attempt),group,failures,pending,trace)
                self.assertEqual(pending.pop(0),group)
            else:
                with self.assertRaisesRegex(controller.EnvironmentUnavailable,'after 3 workers'):
                    controller.retry_upload_failure(error,'worker-3',group,failures,pending,trace)
        self.assertFalse(pending)
        self.assertEqual(failures,{tuple(group):3})
        self.assertEqual([r['attempt'] for r in trace['events']],[1,2,3])
        self.assertTrue(all(r['keys']==group and r['reason']=='actual HTTP 404' for r in trace['events']))

    def test_scheduler_removes_failed_worker_before_new_admission(self):
        controller = self.controller
        events = []
        cfg = {'task':'example','cpus':1,'memory_mb':512,'disk_mb':64,'pool':False}
        docker = Mock()
        docker.call.return_value = {'MemoryLimit':True,'CpuCfsQuota':True,'CPUSet':True}
        docker.remove.side_effect = lambda cid:events.append(('remove',cid))
        def reserve(*args):
            cid = 'worker-'+str(sum(e[0]=='reserve' for e in events)+1)
            events.append(('reserve',cid))
            return (cid,[1]), SimpleNamespace(json=lambda:{})
        def execute(docker,cid,archive,cfg,owner):
            events.append(('execute',cid,Path(archive).read_bytes()))
            if cid=='worker-1':
                raise controller.ArchiveUploadUnavailable('actual HTTP 404')
            return {'per_instance':{'key':{'A':None,'status':'build_error'}}}
        class Executor:
            def __init__(self,**kwargs):pass
            def submit(self,fn,*args):
                future=Future()
                try:future.set_result(fn(*args))
                except Exception as exc:future.set_exception(exc)
                return future
            def shutdown(self,**kwargs):pass
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            contents={'/opt/public_judge/task.json':cfg,
                      '/tests/reference.json':{'instances':{'key':{}}},
                      '/tests/anchors.json':{},'/tests/metric_config.json':{}}
            paths={}
            for index,(key,data) in enumerate(contents.items()):
                path=root/str(index);path.write_text(json.dumps(data));paths[key]=path
            def path(value):return paths.get(str(value),Path(value))
            engine=SimpleNamespace(compute_metric=lambda *args:{'score':0})
            adapter=SimpleNamespace(prepare=lambda *args:({}, {}, []))
            original_path=list(sys.path)
            try:
                with patch.object(controller,'OUT',root/'output'), \
                     patch.object(controller,'Path',side_effect=path), \
                     patch.object(controller,'Docker',return_value=docker), \
                     patch.object(controller,'identify_controller',return_value={'Id':'controller','Image':'fixed-image'}), \
                     patch.object(controller,'daemon_capacity',return_value=SimpleNamespace(json=lambda:{},cpu_count=2)), \
                     patch.object(controller,'slots',return_value=1), \
                     patch.object(controller,'reserve',side_effect=reserve), \
                     patch.object(controller,'execute',side_effect=execute), \
                     patch.object(controller,'ThreadPoolExecutor',Executor), \
                     patch.object(controller,'submission_archive',side_effect=lambda:io.BytesIO(b'frozen tar bytes')), \
                     patch.object(controller.time,'sleep'), \
                     patch.dict(sys.modules,{'metric.engine':engine,'metric_adapter':adapter}), \
                     patch.dict('os.environ',{'TCSEXAM_MAX_JOBS':'1'}):
                    controller.main()
            finally:sys.path[:]=original_path
            self.assertLess(events.index(('remove','worker-1')),events.index(('reserve','worker-2')))
            uploads=[e[2] for e in events if e[0]=='execute']
            self.assertEqual(uploads,[b'frozen tar bytes',b'frozen tar bytes'])
            trace=json.loads((root/'output/resources.json').read_text())
            self.assertEqual(trace['status'],'completed')
            self.assertEqual(sum(e['event']=='archive_upload_failed' for e in trace['events']),1)
            self.assertEqual(sum(e['event']=='finished' for e in trace['events']),1)
            self.assertEqual((root/'output/reward.txt').read_text(),'0')


if __name__ == '__main__':
    unittest.main()
