"""Exercise constrained source exports using only synthetic local fixtures."""
from contextlib import redirect_stdout
import io
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from tcsexam.cli import main
from tcsexam.export import (DECISIONS_PATH, FILES_PATH, REPREPARABLE_SOURCE_ARCHIVES,
                            export_source)


class SourceExport(unittest.TestCase):
    def test_documentation_sources_survive_without_generated_site_or_dependencies(self):
        sources = ('docs/index.md', 'docs/index.zh-CN.md', 'README.md', 'paper.pdf', '.github/CONTRIBUTING.md')
        for name in sources:
            self.write(name, 'source fixture')
        generated = ('site-docs/package.json', 'site-docs/.vitepress/config.mjs',
                     'site-docs/.generated/index.md', 'site-docs/.vitepress/dist/index.html',
                     'site-docs/.vitepress/cache/hash.js', 'site-docs/node_modules/example/index.js')
        for name in generated:
            self.write(name, 'generated fixture')
        report = export_source(self.root, self.output)
        for name in sources:
            self.assertEqual((self.output / name).read_text(), 'source fixture')
        for name in generated:
            self.assertFalse((self.output / name).exists())
        self.assertEqual(report['excluded_counts']['website_source'], 1)

    def test_prepared_graphviz_archives_and_private_review_are_not_exported(self):
        for name in REPREPARABLE_SOURCE_ARCHIVES:
            self.write(name, b'local prepared archive fixture')
        self.write('docs/integration-status.md', 'private review fixture')
        self.write('docs/source-delivery.md', 'public preparation guide fixture')
        self.write('assets/environments/lean-base/graphviz-epl/source-manifest.json', '{}')
        self.write('assets/environments/lean-base/graphviz-epl/source/SHA256SUMS', 'fixed fixture')
        # Do not blanket-exclude archives: an unrelated source file needs its
        # own distribution decision rather than disappearing by suffix.
        self.write('assets/fixture.tar.gz', b'other declared source fixture')
        report = export_source(self.root, self.output)
        self.assertEqual(report['excluded_counts']['repreparable_source_archive'], 2)
        self.assertEqual(report['excluded_counts']['private_review_document'], 1)
        for name in (*REPREPARABLE_SOURCE_ARCHIVES, 'docs/integration-status.md'):
            self.assertFalse((self.output / name).exists())
        for name in ('docs/source-delivery.md', 'assets/fixture.tar.gz',
                     'assets/environments/lean-base/graphviz-epl/source-manifest.json',
                     'assets/environments/lean-base/graphviz-epl/source/SHA256SUMS'):
            self.assertTrue((self.output / name).is_file())
        self.assert_report_totals(report)

    def test_export_archive_exclusions_match_fixed_source_input_manifest(self):
        root = Path(__file__).resolve().parents[3]
        prefix = 'assets/environments/lean-base/graphviz-epl/'
        manifest = json.loads((root / prefix / 'source-manifest.json').read_text())
        self.assertEqual(REPREPARABLE_SOURCE_ARCHIVES,
                         {prefix + manifest[name]['archive']['file']
                          for name in ('graphviz', 'wrapper')})

    def test_curated_nested_license_records_survive_but_dependency_cache_does_not(self):
        prefix = 'assets/environments/lean-base/proofwidgets-npm/'
        name = 'packages/a/node_modules/b/notices/LICENSE'
        data = b'fixture license\n'
        self.write(prefix + name, data)
        self.write(prefix + 'SHA256SUMS', hashlib.sha256(data).hexdigest() + '  ' + name + '\n')
        self.write(prefix + 'packages/a/node_modules/b/index.js', 'cache fixture')
        self.write('site/node_modules/cache/index.js', 'cache fixture')
        export_source(self.root, self.output)
        self.assertEqual((self.output / prefix / name).read_bytes(), data)
        self.assertFalse((self.output / prefix / 'packages/a/node_modules/b/index.js').exists())
        self.assertFalse((self.output / 'site/node_modules').exists())

    def test_changed_license_record_is_rejected_before_export(self):
        prefix = 'assets/environments/lean-base/proofwidgets-npm/'
        self.write(prefix + 'SHA256SUMS', '0' * 64 + '  LICENSE\n')
        self.write(prefix + 'LICENSE', 'changed')
        with self.assertRaisesRegex(ValueError, 'License record checksum mismatch'):
            export_source(self.root, self.output)
        self.assertFalse(self.output.exists())

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        self.root = self.folder / "source"
        (self.root / "tasks").mkdir(parents=True)
        self.output = self.folder / "exported"
        self.write("suites/tasks.json", json.dumps({"tasks": []}))
        self.decisions(False, [])
        validation = patch("tcsexam.export.validate", return_value={"static_integrity": "passed"})
        self.validate = validation.start()
        self.addCleanup(validation.stop)

    def write(self, name, content=""):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content)
        return path

    def decisions(self, complete, files, enforced=None):
        self.write(DECISIONS_PATH, json.dumps({
            "integration_complete": complete,
            "enforced_by_exporter": complete if enforced is None else enforced,
        }))
        self.write(FILES_PATH, json.dumps({"files": list(files)}))

    def assert_report_totals(self, report):
        files = [path for path in self.output.rglob("*") if path.is_file()]
        self.assertEqual(report["files"], len(files))
        self.assertEqual(report["bytes"], sum(path.stat().st_size for path in files))
        self.assertIn("Source export only", report["note"])
        self.assertIn("does not establish public image", report["note"])

    def test_external_integration_pending_does_not_block_source_only_export(self):
        self.write("src/example.py", "print('fixture')\n")
        output = self.folder / "new-parent" / "exported"
        report = export_source(self.root, output)
        self.assertTrue((output / 'src/example.py').is_file())
        self.assertFalse(report['distribution_review']['recorded_integration_complete'])
        self.assertFalse(report['distribution_review']['runtime_availability_verified'])

    def test_exporter_enforces_per_file_rules_without_setting_review_flags(self):
        self.decisions(True, [], enforced=False)
        self.write("src/example.py", "print('fixture')\n")
        output = self.folder / "new-parent" / "exported"
        report = export_source(self.root, output)
        self.assertTrue(report['distribution_review']['file_exclusions_enforced'])
        self.assertFalse(report['distribution_review']['recorded_enforced_by_exporter'])

    def test_unresolved_record_is_rejected_even_when_integration_is_complete(self):
        self.decisions(True, [{
            "path": "tasks/fixture/tests/private-input.dat",
            "distribution": "unresolved",
            "status": "bundled",
        }])
        output = self.folder / "new-parent" / "exported"
        with self.assertRaisesRegex(ValueError, "distribution=unresolved") as raised:
            export_source(self.root, output)
        self.assertIn("tasks/fixture/tests/private-input.dat", str(raised.exception))
        self.validate.assert_not_called()
        self.assertFalse(output.parent.exists())

    def test_unresolved_omitted_inputs_never_leave_in_source_export(self):
        self.decisions(False, [{
            'path': 'tasks/fixture/input.dat', 'distribution': 'unresolved',
            'status': 'source_omitted',
        }])
        self.write('tasks/fixture/input.dat', b'restored external input')
        self.write('tasks/fixture/recipe.json', '{}')
        report = export_source(self.root, self.output)
        self.assertFalse((self.output / 'tasks/fixture/input.dat').exists())
        self.assertTrue((self.output / 'tasks/fixture/recipe.json').is_file())
        self.assertEqual(report['declared_omissions']['unresolved_external_input'], 1)
        self.assertFalse(report['distribution_review']['runtime_availability_verified'])

    def test_private_and_local_prepare_inputs_are_skipped_but_siblings_remain(self):
        self.decisions(True, [
            {"path": "tasks/fixture/private.dat", "distribution": "private_only",
             "status": "source_omitted"},
            {"path": "tasks/fixture/inputs/raw.dat", "distribution": "local_prepare",
             "status": "source_omitted"},
        ])
        self.write("tasks/fixture/private.dat", b"private fixture")
        self.write("tasks/fixture/inputs/raw.dat", b"local input fixture")
        self.write("tasks/fixture/inputs/recipe.json", "{}\n")
        self.write("tasks/fixture/code.py", "VALUE = 1\n")
        self.output.mkdir()
        report = export_source(self.root, self.output)
        self.assertFalse((self.output / "tasks/fixture/private.dat").exists())
        self.assertFalse((self.output / "tasks/fixture/inputs/raw.dat").exists())
        self.assertEqual((self.output / "tasks/fixture/inputs/recipe.json").read_text(), "{}\n")
        self.assertEqual((self.output / "tasks/fixture/code.py").read_text(), "VALUE = 1\n")
        self.assertEqual(report["declared_omissions"], {
            "local_prepare_source_omitted": 1,
            "private_only": 1,
        })
        excluded = {(row["path"], row["reason"]) for row in report["excluded"]}
        self.assertIn(("tasks/fixture/private.dat", "private_only"), excluded)
        self.assertIn(("tasks/fixture/inputs/raw.dat", "local_prepare_source_omitted"), excluded)
        self.assert_report_totals(report)

    def test_cli_keeps_source_and_redistributable_files_and_excludes_local_outputs(self):
        self.decisions(True, [{
            "path": "assets/redistributable.bin",
            "distribution": "redistributable",
            "status": "source_omitted",
        }])
        self.write("src/example.py", "print('fixture')\n")
        self.write("assets/redistributable.bin", b"\x00\xff\x10")
        self.write(".env.example", "EXAMPLE_SETTING=\n")
        self.write(".git/config", "not exported")
        self.write("jobs/result.json", "not exported")
        self.write("build/output.o", "not exported")
        self.write("dist/package.whl", "not exported")
        self.write("src/__pycache__/example.pyc", b"not exported")
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            result = main(["export", "--root", str(self.root), "--output", str(self.output)])
        self.assertEqual(result, 0)
        report = json.loads(stdout.getvalue())
        self.assertEqual((self.output / "src/example.py").read_text(), "print('fixture')\n")
        self.assertEqual((self.output / "assets/redistributable.bin").read_bytes(), b"\x00\xff\x10")
        self.assertTrue((self.output / ".env.example").is_file())
        for name in (".git", "jobs", "build", "dist", "src/__pycache__"):
            self.assertFalse((self.output / name).exists(), name)
        self.assertEqual(report["excluded_counts"]["version_control_metadata"], 1)
        self.assertEqual(report["excluded_counts"]["local_jobs_or_build_output"], 3)
        self.assertEqual(report["excluded_counts"]["cache_or_dependency_output"], 1)
        self.assert_report_totals(report)

    def test_sensitive_filenames_are_rejected_without_reading_contents(self):
        self.decisions(True, [])
        self.write("src/example.py", "safe fixture\n")
        for index, name in enumerate((
                "retired.bak", "instance.key", ".env", ".env.production",
                "id_rsa", "certificate.pem", "credentials.json")):
            with self.subTest(name=name):
                path = self.write(name, os.urandom(16))
                output = self.folder / f"blocked-sensitive-{index}"
                with self.assertRaisesRegex(ValueError, "sensitive"):
                    export_source(self.root, output)
                self.assertFalse(output.exists())
                path.unlink()

    def test_file_and_directory_symlinks_are_rejected(self):
        self.decisions(True, [])
        self.write("src/example.py", "safe fixture\n")
        for index, name in enumerate(("linked-file", "linked-directory")):
            with self.subTest(name=name):
                link = self.root / name
                if name == "linked-file":
                    link.symlink_to("src/example.py")
                else:
                    link.symlink_to("src", target_is_directory=True)
                output = self.folder / f"blocked-link-{index}"
                with self.assertRaisesRegex(ValueError, "symbolic link"):
                    export_source(self.root, output)
                self.assertFalse(output.exists())
                link.unlink()

    def test_nonempty_output_and_task_tree_output_are_rejected(self):
        self.decisions(True, [])
        self.write("src/example.py", "safe fixture\n")
        self.output.mkdir()
        retained = self.output / "keep.txt"
        retained.write_text("unchanged")
        with self.assertRaisesRegex(ValueError, "new or empty"):
            export_source(self.root, self.output)
        self.assertEqual(retained.read_text(), "unchanged")
        with self.assertRaisesRegex(ValueError, "task tree"):
            export_source(self.root, self.root / "tasks/fixture/exported")

    def test_export_below_build_excludes_other_build_products(self):
        self.decisions(True, [])
        self.write("src/example.py", "safe fixture\n")
        self.write("build/intermediate.o", "not exported")
        self.write("build/scratch/debug.tmp", "not exported")
        self.output = self.root / "build/exported"
        report = export_source(self.root, self.output)
        self.assertEqual((self.output / "src/example.py").read_text(), "safe fixture\n")
        self.assertFalse((self.output / "build").exists())
        self.assertFalse((self.output / "intermediate.o").exists())
        self.assertFalse((self.output / "scratch/debug.tmp").exists())
        self.assertIn({"path": "build", "reason": "local_jobs_or_build_output"},
                      report["excluded"])
        self.assert_report_totals(report)

    def test_text_binary_and_executable_modes_are_preserved(self):
        self.decisions(True, [])
        expected = {
            "text.txt": (b"text fixture\n", 0o640),
            "run.sh": (b"#!/bin/sh\nexit 0\n", 0o755),
            "binary.dat": (b"\x00\x01\xff", 0o604),
        }
        for name, (content, mode) in expected.items():
            path = self.write(name, content)
            path.chmod(mode)
        report = export_source(self.root, self.output)
        for name, (content, mode) in expected.items():
            path = self.output / name
            self.assertEqual(path.read_bytes(), content)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), mode)
        self.assert_report_totals(report)

    def test_publication_mode_normalization_is_explicit_and_preserves_bytes(self):
        expected = {
            "nested/text.txt": (b"text fixture\n", 0o664, 0o644),
            "nested/run.sh": (b"#!/bin/sh\nexit 0\n", 0o775, 0o755),
            "binary.dat": (b"\x00\x01\xff", 0o600, 0o644),
        }
        for name, (content, original, _) in expected.items():
            self.write(name, content).chmod(original)
        previous_umask = os.umask(0o002)
        try:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = main(["export", "--root", str(self.root), "--output", str(self.output),
                               "--normalize-modes"])
        finally:
            os.umask(previous_umask)
        self.assertEqual(result, 0)
        report = json.loads(stdout.getvalue())
        self.assertEqual(report['mode_policy'], 'directories_0755_files_0644_or_0755')
        for name, (content, original, exported) in expected.items():
            self.assertEqual((self.output / name).read_bytes(), content)
            self.assertEqual(stat.S_IMODE((self.output / name).stat().st_mode), exported)
            self.assertEqual(stat.S_IMODE((self.root / name).stat().st_mode), original)
        for directory in (self.output, *(p for p in self.output.rglob('*') if p.is_dir())):
            self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o755)
        self.assert_report_totals(report)

    def test_validation_failure_leaves_no_output(self):
        self.decisions(True, [])
        self.write("src/example.py", "safe fixture\n")
        self.validate.side_effect = ValueError("fixture validation failure")
        with self.assertRaisesRegex(ValueError, "fixture validation failure"):
            export_source(self.root, self.output)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
