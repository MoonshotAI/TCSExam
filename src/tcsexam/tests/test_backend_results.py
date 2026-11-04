"""Run frozen client request and result parsers against HTTP fixtures."""
import ast
from contextlib import redirect_stdout
import io
import json
import os
import socket
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch
import urllib.error
import urllib.request

from tcsexam.layout import repository


class BackendResults(unittest.TestCase):
    def scope(self, path):
        names = {'_std_headers', 'http_get_json', 'http_call', 'submit_once',
                 'merge_submissions', '_finalize_candidate', 'poll_until_done',
                 'client_ip_total_observed', 'chain_reconcile', 'chain_hidden_reconciliation'}
        tree = ast.parse(path.read_text())
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
        def fail(message):
            raise RuntimeError(message)
        scope = {'os': os, 'socket': socket, 'urllib': __import__('urllib'), 'json': json,
                 'time': Mock(wraps=time), 'sys': sys, 'TOKEN_ID': 'fixture-id',
                 'TOKEN_SECRET': 'fixture-secret', 'SERVICE_BASE': 'https://judge.example.invalid',
                 'SUBMIT_503_RETRIES': 2, 'SUBMIT_503_BACKOFF': 0,
                 'SUBMIT_TIMEOUT': 60, 'POLL_TIMEOUT': 5, 'POLL_INTERVAL': 0,
                 'CHAIN_QUERY_RETRIES': 1, 'CHAIN_QUERY_BACKOFF': 0, 'CHAIN_QUERY_TIMEOUT': 10,
                 'infra_fail': fail, 'terminal_fail': fail,
                 'terminal_answer': lambda *args: False, 'terminal_destroyed': lambda *args: False}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), scope)
        return scope

    def test_real_request_json_status_and_exactly_once_upload(self):
        path = repository()/'tasks/solver/online/bpp-bpplib/tests/fetch_final.py'
        scope = self.scope(path)
        with patch.dict(os.environ, {'TCSEXAM_RUN_ID': 'fixture-attempt'}, clear=True), \
                patch('urllib.request.urlopen') as opening, redirect_stdout(io.StringIO()):
            response = opening.return_value.__enter__.return_value
            response.read.return_value = b'{"submission":17}'
            response.status = 202
            with tempfile.NamedTemporaryFile() as payload:
                payload.write(b'archive-bytes');payload.flush()
                self.assertEqual(scope['submit_once']('session-a', payload.name), 17)
            self.assertEqual(opening.call_count, 1)
            request = opening.call_args.args[0]
            self.assertEqual(request.method, 'POST')
            self.assertEqual(request.data, b'archive-bytes')
            self.assertEqual(request.get_header('X-tcsexam-run-id'), 'fixture-attempt')
            self.assertIsNone(request.get_header('X-tcsexam-archive-token'))
            opening.reset_mock()
            opening.side_effect = urllib.error.URLError('fixture disconnect')
            with tempfile.NamedTemporaryFile() as payload:
                with self.assertRaisesRegex(RuntimeError, 'NOT retrying'):
                    scope['submit_once']('session-a', payload.name)
            self.assertEqual(opening.call_count, 1)

    def test_reconciliation_requests_send_archive_token_and_parse_counts(self):
        clients = list((repository()/'tasks/solver/online').glob('*/tests/fetch_final.py'))
        self.assertEqual(len(clients), 30)
        for path in clients:
            with self.subTest(task=path.parent.parent.name):
                scope = self.scope(path)
                with patch.dict(os.environ, {'TCSEXAM_RUN_ID': 'fixture-attempt'}, clear=True), \
                        patch('urllib.request.urlopen') as opening, redirect_stdout(io.StringIO()):
                    response = opening.return_value.__enter__.return_value
                    response.read.return_value = json.dumps({'total_submissions': 3, 'sessions': [
                        {'session_id': 'agent-a', 'submissions': 2,
                         'public_submissions': 1, 'present': True},
                        {'session_id': 'own-a', 'submissions': 1,
                         'public_submissions': 0, 'present': True},
                    ]}).encode()
                    result = scope['chain_hidden_reconciliation'](
                        ['agent-a'], 'own-a', 'fixture-archive')
                    self.assertEqual(result['agent_hidden'], 2)
                    self.assertEqual(result['own_counted'], 1)
                    self.assertEqual(result['total'], 3)
                    request = opening.call_args.args[0]
                    self.assertEqual(request.get_method(), 'GET')
                    self.assertEqual(
                        request.full_url,
                        'https://judge.example.invalid/v1/judge/sessions?session_ids=agent-a,own-a')
                    self.assertEqual(request.get_header('X-tcsexam-archive-token'),
                                     'fixture-archive')
                    self.assertEqual(opening.call_args.kwargs['timeout'], 10)

                    opening.reset_mock()
                    response.read.return_value = b'{"total_submissions":4}'
                    self.assertEqual(scope['client_ip_total_observed']('fixture-archive'), 4)
                    request = opening.call_args.args[0]
                    self.assertEqual(request.get_method(), 'GET')
                    self.assertEqual(
                        request.full_url,
                        'https://judge.example.invalid/v1/judge/sessions?client_ip=self')
                    self.assertEqual(request.get_header('X-tcsexam-archive-token'),
                                     'fixture-archive')

    def test_completed_records_public_channels_and_infrastructure_errors(self):
        for path in (repository()/'tasks/solver/online').glob('*/tests/fetch_final.py'):
            with self.subTest(task=path.parent.parent.name):
                scope = self.scope(path)
                archive = {'instance_set': 'hidden', 'n_shards': 1, 'shard_payloads': {'0': {
                    'submissions': [{'status': 'ok', 'records': [{'instance': 'fixture', 'A': 7}]}]}}}
                candidates, notes = scope['merge_submissions']({'session-a': archive})
                self.assertEqual(candidates[0]['records'][0]['A'], 7)
                self.assertFalse(candidates[0]['skipped'])
                public = {**archive, 'instance_set': 'public'}
                self.assertFalse(scope['merge_submissions']({'public': public})[0])
                self.assertTrue(scope['merge_submissions']({'public': public}, include_public=True)[0])
                broken = {**archive, 'shard_payloads': {'0': {'submissions': [{'status': 'judge_error'}]}}}
                failed, _ = scope['merge_submissions']({'broken': broken})
                self.assertTrue(failed[0]['skipped'])
                self.assertTrue(failed[0]['infra_missing'])
