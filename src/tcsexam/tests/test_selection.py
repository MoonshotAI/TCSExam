"""Protect suite/protocol separation and ensure preparation never starts a model."""
from contextlib import redirect_stdout, redirect_stderr
from importlib.resources import files
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tcsexam.cli import main
from tcsexam.layout import repository, require_paths, selection, within


class Selection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = repository()

    def test_coverage_of_both_solver_protocols(self):
        _, rows = selection(self.root, "full", track="solver", solver_protocol="online")
        self.assertEqual(len(rows), 30)
        require_paths(rows)
        _, rows = selection(self.root, "lite", track="solver")
        self.assertEqual(len(rows), 5)
        require_paths(rows)
        _, rows = selection(self.root, "full", track="solver")
        self.assertEqual(len(rows), 30)
        require_paths(rows)
        self.assertTrue(all('/online/' in r['path'] for r in rows))
        _, rows = selection(self.root, "full", track="solver", solver_protocol="offline")
        self.assertEqual(len(rows), 30)
        self.assertTrue(all('/offline/' in r['path'] for r in rows))
        _, rows = selection(self.root, "lite", track="solver", solver_protocol="online")
        self.assertEqual(len(rows), 5)
        self.assertTrue(all('/online/' in r['path'] for r in rows))
        with self.assertRaises(ValueError):
            require_paths([{'id':'unavailable-fixture','path':None}])

    def test_multiple_task_ids_and_partial_misses(self):
        expected = {"dijkstra-universal", "three-taxi"}
        _, rows = selection(self.root, "full", task=["dijkstra-universal", "three-taxi"])
        self.assertEqual({row["id"] for row in rows}, expected)
        _, rows = selection(self.root, "full", task="dijkstra-universal,three-taxi")
        self.assertEqual({row["id"] for row in rows}, expected)
        with self.assertRaisesRegex(ValueError, "does-not-exist"):
            selection(self.root, "full", task=["dijkstra-universal", "does-not-exist"])
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(["list", "--root", str(self.root), "--suite", "full",
                                   "--task", "dijkstra-universal", "--task", "three-taxi"]), 0)
        self.assertEqual(len(output.getvalue().splitlines()), 2)

    def test_full_default_is_recorded_and_explicit_override_is_preserved(self):
        for override, expected in (([], 'online'), (['--solver-protocol', 'offline'], 'offline')):
            with tempfile.TemporaryDirectory() as folder:
                output = Path(folder) / 'job.json'
                with redirect_stdout(io.StringIO()), patch('tcsexam.cli.subprocess.call') as launch:
                    main(['prepare', '--root', str(self.root), '--suite', 'full',
                          '--task', 'bpp-bpplib', '--base-url', 'https://example.invalid/v1',
                          '--output', str(output), *override])
                    launch.assert_not_called()
                record = json.loads(output.with_suffix('.selection.json').read_text())
                self.assertEqual(record['solver_protocol'], expected)
                self.assertIn('/' + expected + '/', record['tasks'][0]['path'])

    def test_shared_paths_do_not_depend_on_solver_protocol(self):
        for track in ("theorem", "construction", "open"):
            _, a = selection(self.root, "lite", track=track, solver_protocol="online")
            _, b = selection(self.root, "lite", track=track, solver_protocol="offline")
            self.assertEqual(a, b)
        with self.assertRaises(ValueError):
            selection(self.root, "lite", task="does-not-exist")
        with self.assertRaises(ValueError):
            within(self.root, "../outside")
        self.assertEqual(repository(self.root), self.root)

    def test_prepare_records_protocol_and_keeps_key_placeholder(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "job.json"
            with redirect_stdout(io.StringIO()), patch("tcsexam.cli.subprocess.call") as launch:
                self.assertEqual(main(["prepare", "--root", str(self.root), "--suite", "lite",
                                       "--base-url", "https://example.invalid/v1", "--output", str(output)]), 0)
                launch.assert_not_called()
            job = json.loads(output.read_text())
            self.assertEqual(len(job["tasks"]), 20)
            self.assertEqual(job["agents"][0]["env"]["KIMI_MODEL_API_KEY"], "${TCSEXAM_API_KEY}")
            record = json.loads(output.with_suffix(".selection.json").read_text())
            self.assertEqual(record["solver_protocol"], "offline")
            self.assertEqual(record["agent_timeout_sec"], 43200)
            self.assertTrue(all("/offline/" in r["path"] for r in record["tasks"] if r["track"] == "solver"))

    def test_unavailable_and_unready_runs_never_start_harbor(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "job.json"
            for suite in ("full", "lite"):
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()), \
                        patch("tcsexam.cli.subprocess.call") as launch, \
                        patch("tcsexam.setup.inspect_image", return_value=None), \
                        patch("tcsexam.setup.subprocess.run") as acquire:
                    acquire.return_value.returncode = 1
                    with self.assertRaises(SystemExit) as error:
                        main(["run", "--root", str(self.root), "--suite", suite, "--output", str(output)])
                    self.assertEqual(error.exception.code, 2)
                    launch.assert_not_called()
            self.assertFalse(output.exists())

    def test_reference_data_is_installed_with_package(self):
        for suite, count in (("lite", 5), ("full", 30)):
            data = json.loads(files("tcsexam").joinpath(f"references/paper-k3-fixed-260925-{suite}.json").read_text())
            self.assertEqual(len(data["tasks"]), count)
