"""Check the real clients' HTTP namespace without running a solver or backend."""
import ast
from contextlib import redirect_stdout
import io
import json
import os
import re
import socket
import unittest
from unittest.mock import Mock, patch
import urllib.request

from tcsexam.layout import repository


class BackendInterface(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = repository()

    def test_verifiers_send_only_tcsexam_headers(self):
        clients = list((self.root / 'tasks/solver/online').glob('*/tests/fetch_final.py'))
        self.assertEqual(len(clients), 30)
        expected = {
            'x-tcsexam-token-id': 'test-id', 'x-tcsexam-token-secret': 'test-secret',
            'x-tcsexam-client-id': 'attempt-a', 'x-tcsexam-run-id': 'attempt-a',
            'x-tcsexam-agent-name': 'test-agent',
        }
        for path in clients:
            with self.subTest(task=path.parent.parent.name):
                tree = ast.parse(path.read_text())
                functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                             and n.name in {'_std_headers', 'http_get_json'}]
                self.assertEqual(len(functions), 2)
                module = ast.Module(body=functions, type_ignores=[])
                scope = {'TOKEN_ID': 'test-id', 'TOKEN_SECRET': 'test-secret',
                         'os': os, 'socket': socket, 'urllib': __import__('urllib'), 'json': json}
                exec(compile(module, str(path), 'exec'), scope)
                with patch.dict(os.environ, {'TCSEXAM_RUN_ID': 'attempt-a',
                                             'TCSEXAM_AGENT_NAME': 'test-agent'}, clear=True):
                    request = urllib.request.Request('https://judge.example.invalid/v1/judge/sessions')
                    scope['_std_headers'](request)
                    self.assertEqual({k.lower(): v for k, v in request.header_items()}, expected)
                    with patch('urllib.request.urlopen') as opening:
                        opening.return_value.__enter__.return_value.read.return_value = b'{}'
                        scope['http_get_json']('https://judge.example.invalid/archive',
                                              {'X-TCSEXAM-Archive-Token': 'test-archive'})
                        sent = opening.call_args.args[0]
                        self.assertEqual({k.lower(): v for k, v in sent.header_items()},
                                         {**expected, 'x-tcsexam-archive-token': 'test-archive'})
                with patch.dict(os.environ, {'HOSTNAME': 'attempt-host'}, clear=True):
                    request = urllib.request.Request('https://judge.example.invalid/status')
                    scope['_std_headers'](request)
                    self.assertEqual(request.get_header('X-tcsexam-client-id'), 'attempt-host')

    def test_hidden_create_sends_archive_token(self):
        names = {'_std_headers', 'http_call', 'create_session'}
        clients = list((self.root / 'tasks/solver/online').glob('*/tests/fetch_final.py'))
        self.assertEqual(len(clients), 30)
        def fail(message):
            raise RuntimeError(message)
        for path in clients:
            with self.subTest(task=path.parent.parent.name):
                tree = ast.parse(path.read_text())
                functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                             and n.name in names]
                self.assertEqual(len(functions), len(names))
                scope = {
                    'os': os, 'socket': socket, 'urllib': __import__('urllib'), 'json': json,
                    'TOKEN_ID': 'test-id', 'TOKEN_SECRET': 'test-secret',
                    'SERVICE_BASE': 'https://judge.example.invalid',
                    'JUDGE_IMAGE': 'fixture-judge', 'SESSION_TTL': 60, 'N_SHARDS': 1,
                    'RESOURCES': {'cpu': 1, 'mem': 128}, 'CREATE_RETRIES': 1,
                    'CREATE_RETRY_BACKOFF': 0, 'infra_fail': fail, 'terminal_fail': fail,
                    'terminal_answer': lambda *args: False, 'wait_ready': Mock(),
                }
                exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), 'exec'), scope)
                with patch.dict(os.environ, {'TCSEXAM_RUN_ID': 'attempt-a'}, clear=True), \
                        patch('urllib.request.urlopen') as opening, redirect_stdout(io.StringIO()):
                    response = opening.return_value.__enter__.return_value
                    response.status = 201
                    response.read.return_value = b'{"session_id":"session-a"}'
                    self.assertEqual(scope['create_session']('test-archive'), 'session-a')
                self.assertEqual(opening.call_count, 1)
                request = opening.call_args.args[0]
                self.assertEqual(request.method, 'POST')
                self.assertEqual(request.full_url,
                                 'https://judge.example.invalid/v1/judge/sessions')
                self.assertEqual(request.get_header('X-tcsexam-archive-token'), 'test-archive')
                scope['wait_ready'].assert_called_once_with('session-a')

    def test_main_forwards_archive_token_to_protected_requests(self):
        expected = {'create_session': 1, 'chain_hidden_reconciliation': 2,
                    'client_ip_total_observed': 1}
        for path in (self.root / 'tasks/solver/online').glob('*/tests/fetch_final.py'):
            with self.subTest(task=path.parent.parent.name):
                tree = ast.parse(path.read_text())
                main = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                            and n.name == 'main')
                calls = [n for n in ast.walk(main) if isinstance(n, ast.Call)
                         and isinstance(n.func, ast.Name) and n.func.id in expected]
                for name, count in expected.items():
                    matching = [n for n in calls if n.func.id == name]
                    self.assertEqual(len(matching), count)
                    for call in matching:
                        self.assertIsInstance(call.args[-1], ast.Name)
                        self.assertEqual(call.args[-1].id, 'archive_token')

    def test_submit_and_keepalive_share_the_header_namespace(self):
        expected = {'X-TCSEXAM-Token-Id', 'X-TCSEXAM-Token-Secret',
                    'X-TCSEXAM-Run-Id', 'X-TCSEXAM-Client-Id', 'X-TCSEXAM-Agent-Name'}
        for path in (self.root / 'tasks/solver/online').glob('*/environment/submit.sh'):
            with self.subTest(task=path.parent.parent.name):
                text = path.read_text()
                headers = re.findall(r'-H "(X-[A-Za-z0-9_-]+):', text)
                self.assertEqual(set(headers), expected)
                for header in expected:
                    self.assertGreaterEqual(headers.count(header), 2)
                self.assertIn('${TCSEXAM_BASE_URL:?', text)
                self.assertIn('${TCSEXAM_RUN_ID:-${HOSTNAME:-}}', text)

    def test_namespace_aliases_are_explicitly_unpublished(self):
        manifest = json.loads((self.root / 'assets/images.json').read_text())
        planned = [r for r in manifest['images'] if r.get('reference_role') == 'planned_namespace_alias']
        self.assertTrue(planned)
        for row in planned:
            self.assertIn('/tcsexam', row['image'])
            self.assertEqual(row['status'], 'namespace_migration_pending')
            self.assertIsNone(row['replacement'])
