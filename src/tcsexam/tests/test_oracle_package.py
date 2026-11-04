"""Exercise oracle-answer packaging with synthetic fixtures only."""
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from tcsexam.export import DECISIONS_PATH, FILES_PATH, export_source
from tcsexam.oracle_package import (CONFIRM_PUBLIC_RELEASE, create_package,
                                    publish_package, verify_package)


COMMIT = "1" * 40


class OraclePackage(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        self.source = self.folder / "source"
        self.source.mkdir()
        self.files = []

    def answer(self, name, content, task="fixture", variant="solver-online", origin_path=None):
        path = self.source / Path(name).name
        path.write_bytes(content)
        row = {"source": str(path), "path": name, "task": task, "variant": variant,
               "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(),
               "git_blob": hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest(),
               "origin": {"source_id": "synthetic-source", "commit": COMMIT,
                          "path": origin_path or f"tasks/{task}/solution/{Path(name).name}"}}
        self.files.append(row)
        return row

    def spec(self, name="spec.json"):
        path = self.folder / name
        path.write_text(json.dumps({
            "schema_version": 1,
            "package": {"id": "synthetic-oracle", "version": "v1",
                        "source_scope": "Synthetic test answers; no production content."},
            "files": self.files,
        }))
        return path

    def standard_spec(self):
        self.answer("answers/tasks/solver/online/fixture/solution/precomputed/a.sol",
                    b"synthetic solver answer\n")
        self.answer("answers/tasks/construction/fixture/solution/Basic.lean",
                    b"-- synthetic proof fixture\n", task="fixture-construction",
                    variant="construction", origin_path="tasks/fixture/solution/Basic.lean")
        self.files[0]["sha256"] = None
        return self.spec()

    def test_create_is_deterministic_and_clean_verification_matches_authority(self):
        spec = self.standard_spec()
        first = self.folder / "first.tar.gz"
        second = self.folder / "second.tar.gz"
        report = create_package(spec, first, self.folder / "create-report.json")
        second_report = create_package(spec, second)
        self.assertEqual({**report, "archive": "second.tar.gz"}, second_report)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertEqual(report["answer_files"], 2)
        self.assertEqual(report["answer_bytes"], sum(row["bytes"] for row in self.files))
        self.assertEqual(first.with_name(first.name + ".sha256").read_text(),
                         f"{report['archive_sha256']}  first.tar.gz\n")
        destination = self.folder / "unpacked"
        verified = verify_package(first, destination, spec)
        self.assertEqual(verified["package_verification"], "passed")
        self.assertEqual(verified["authority_verification"]["files_sha256_verified"], 2)
        for row in self.files:
            self.assertEqual((destination / row["path"]).read_bytes(), Path(row["source"]).read_bytes())
        manifest = json.loads((destination / "manifest.json").read_text())
        self.assertEqual(manifest["coverage"], report["coverage"])
        self.assertNotIn(str(self.source), (destination / "manifest.json").read_text())
        self.assertNotIn(str(self.source), (destination / "SOURCE.md").read_text())
        with tarfile.open(first, "r:gz") as archive:
            for member in archive:
                self.assertTrue(member.isfile())
                self.assertEqual(member.mtime, 0)
                self.assertEqual(member.uid, 0)
                self.assertEqual(member.gid, 0)
                self.assertEqual(member.mode, 0o644)

    def test_source_hash_mismatch_leaves_no_package(self):
        spec = self.standard_spec()
        changed = Path(self.files[0]["source"])
        changed.write_bytes(b"X" * changed.stat().st_size)
        output = self.folder / "blocked.tar.gz"
        with self.assertRaisesRegex(ValueError, "Git blob differs"):
            create_package(spec, output)
        self.assertFalse(output.exists())

    def test_forbidden_answer_paths_are_rejected(self):
        for index, name in enumerate((
                "answers/tasks/fixture/solution/private.key",
                "answers/.git/objects/answer",
                "answers/internal.log",
                "answers/old.ciphertext",
                "outside/answer.sol")):
            with self.subTest(name=name):
                self.files = []
                self.answer("answers/tasks/fixture/solution/placeholder.sol", b"fixture")
                self.files[0]["path"] = name
                with self.assertRaises(ValueError):
                    create_package(self.spec(f"forbidden-{index}.json"),
                                   self.folder / f"forbidden-{index}.tar.gz")

    def test_tampered_archive_fails_verification(self):
        spec = self.standard_spec()
        package = self.folder / "original.tar.gz"
        create_package(spec, package)
        members = {}
        with tarfile.open(package, "r:gz") as archive:
            for member in archive:
                members[member.name] = archive.extractfile(member).read()
        name = self.files[0]["path"]
        members[name] = b"X" * len(members[name])
        tampered = self.folder / "tampered.tar.gz"
        with tarfile.open(tampered, "w:gz") as archive:
            for member_name, data in members.items():
                info = tarfile.TarInfo(member_name)
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
        with self.assertRaisesRegex(ValueError, "SHA256SUMS mismatch"):
            verify_package(tampered, self.folder / "tampered-output")

    def test_publish_requires_target_and_dedicated_confirmation(self):
        package = self.folder / "package.tar.gz"
        package.write_bytes(b"synthetic package")
        execute = unittest.mock.Mock()
        for destination, confirmation in (("", CONFIRM_PUBLIC_RELEASE),
                                          ("registry.example/team/answers:v1", "yes"),
                                          ("registry.example/team/answers:latest", CONFIRM_PUBLIC_RELEASE)):
            with self.subTest(destination=destination, confirmation=confirmation):
                with self.assertRaisesRegex(ValueError, "Refuse public release"):
                    publish_package(package, destination, confirmation, execute=execute)
        execute.assert_not_called()

    def test_explicit_publish_verifies_then_uses_buildx_push(self):
        package = self.folder / "package.tar.gz"
        package.write_bytes(b"synthetic package")
        calls = []

        def execute(command, check):
            calls.append((command, check))
            metadata = Path(command[command.index("--metadata-file") + 1])
            metadata.write_text('{"containerimage.digest":"sha256:synthetic"}')

        verification = {"archive_sha256": "a" * 64, "answer_set_sha256": "b" * 64}
        with patch("tcsexam.oracle_package.verify_package", return_value=verification) as verify:
            result = publish_package(package, "registry.example/team/answers:v1",
                                     CONFIRM_PUBLIC_RELEASE, execute=execute)
        verify.assert_called_once()
        self.assertEqual(len(calls), 1)
        command = calls[0][0]
        self.assertEqual(command[:3], ["docker", "buildx", "build"])
        self.assertIn("--push", command)
        self.assertIn("registry.example/team/answers:v1", command)
        self.assertEqual(result["public_release"], "pushed")


class PublicExportExcludesOracleAnswers(unittest.TestCase):
    def test_export_omits_synthetic_answers_and_private_package_workspace(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "source"
            root.mkdir()
            (root / "suites").mkdir()
            (root / "suites/tasks.json").write_text('{"tasks": []}')
            (root / DECISIONS_PATH).parent.mkdir(parents=True)
            (root / DECISIONS_PATH).write_text(
                '{"integration_complete": true, "enforced_by_exporter": true}')
            (root / FILES_PATH).parent.mkdir(parents=True)
            (root / FILES_PATH).write_text('{"files": []}')
            answers = (
                "tasks/solver/online/fixture/solution/precomputed/a.sol",
                "tasks/solver/online/fixture/solution/precomputed.tar.xz",
                "tasks/solver/online/fixture/solution/solutions/a.sol",
                "tasks/construction/fixture/solution/Basic.lean",
                "tasks/solver/online/fixture/tests/solution/precomputed/expected.sol",
            )
            for name in answers:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"synthetic oracle fixture")
            public = root / "tasks/solver/online/fixture/solution/solve.sh"
            public.write_text("# synthetic public script\n")
            private = root / "build/oracle-private-package/package.tar.gz"
            private.parent.mkdir(parents=True)
            private.write_bytes(b"synthetic private package")
            output = Path(temporary) / "exported"
            with patch("tcsexam.export.validate", return_value={"static_integrity": "passed"}):
                report = export_source(root, output)
            for name in answers:
                self.assertFalse((output / name).exists(), name)
            self.assertTrue((output / "tasks/solver/online/fixture/solution/solve.sh").is_file())
            self.assertFalse((output / "build").exists())
            self.assertNotIn("build/oracle-private-package", {row["path"] for row in report["excluded"]})
            self.assertEqual(report["excluded_counts"].get("oracle_answers_private"), len(answers))


class OracleDistributionPolicy(unittest.TestCase):
    def test_private_backup_scope_and_future_release_guard(self):
        root = Path(__file__).resolve().parents[3]
        decisions = json.loads((root / "docs/licenses/third-party/distribution-decisions.json").read_text())
        self.assertFalse(decisions["integration_complete"])
        self.assertFalse(decisions["enforced_by_exporter"])
        record = next(row for row in decisions["resources"]
                      if row["id"] == "oracle-answer-private-retention")
        self.assertEqual(record["recommended_action"], "retain_private_bundle_with_explicit_future_release")
        self.assertEqual(record["distribution"], "private_only")
        self.assertFalse(record["public_release_performed"])
        self.assertNotIn("accepted_fixed_products", record)
        verification = record["verification"]
        self.assertEqual(verification["answer_files"], 2571)
        self.assertEqual(verification["answer_bytes"], 640578027)
        self.assertEqual(verification["archive_bytes"], 510624920)
        self.assertEqual(verification["tasks"], 50)
        self.assertEqual(verification["task_variant_groups"], 55)
        self.assertTrue(verification["independent_rebuilds_identical"])
        self.assertTrue(verification["clean_unpack_verified"])
        self.assertEqual(verification["public_export_known_answer_paths_excluded"], 2581)
        self.assertFalse(verification["oracle_judging_executed"])
        self.assertIn("PUBLISH_ORACLE_ANSWERS", " ".join(record["conditions"]))


if __name__ == "__main__":
    unittest.main()
