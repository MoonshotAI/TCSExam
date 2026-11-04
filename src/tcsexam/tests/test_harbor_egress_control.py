"""Check the normalized Harbor egress-control context against its pinned package."""
from concurrent.futures import ThreadPoolExecutor
from importlib.metadata import version
import os
from pathlib import Path
import shutil
import stat
import tempfile
import unittest

from harbor.environments.docker import docker as harbor_docker
from harbor.utils.container_cache import docker_build_context_hash

from tcsexam.harbor_support import normalized_context, source_entries


HARBOR_VERSION = "0.22.0"
EXPECTED_CONTEXT_HASH = "b1e6760734a9e6f6"
PACKAGE_CONTEXT = (Path(harbor_docker.__file__).parent /
                   "harbor-docker-egress-control-sidecar")
PUBLIC_CONTEXT = (Path(__file__).resolve().parents[3] /
                  "assets/environments/harbor/egress-control")


def context_hash(context):
    return docker_build_context_hash(
        context=context,
        dockerfile_path=context / "Dockerfile",
        build_args={},
        platform="linux/amd64",
    )


def copy_with_modes(source, destination, regular, executable, directory):
    entries = source_entries(source)
    shutil.copytree(source, destination)
    for root, directories, files in os.walk(destination):
        Path(root).chmod(directory)
        for name in files:
            path = Path(root) / name
            row = entries[path.relative_to(destination).as_posix()]
            path.chmod(executable if row["mode"] == 0o755 else regular)


class HarborEgressControl(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)

    def test_public_context_matches_harbor_0220(self):
        self.assertEqual(version("harbor"), HARBOR_VERSION,
                         "Run this test with harbor==0.22.0")
        upstream_files = {
            path.relative_to(PACKAGE_CONTEXT).as_posix(): path
            for path in PACKAGE_CONTEXT.rglob("*") if path.is_file()
        }
        public_files = {
            path.relative_to(PUBLIC_CONTEXT).as_posix(): path
            for path in PUBLIC_CONTEXT.rglob("*") if path.is_file()
        }

        self.assertEqual(public_files.keys(), upstream_files.keys())
        self.assertEqual(len(public_files), 5)
        for name, upstream_file in upstream_files.items():
            public_file = public_files[name]
            self.assertEqual(public_file.read_bytes(), upstream_file.read_bytes(), name)
            self.assertEqual(public_file.stat().st_mode & 0o111,
                             upstream_file.stat().st_mode & 0o111, name)

        public, public_hash = normalized_context(self.folder / "public-cache", PUBLIC_CONTEXT)
        package, package_hash = normalized_context(self.folder / "package-cache", PACKAGE_CONTEXT)
        self.assertEqual(public_hash, package_hash)
        self.assertEqual(context_hash(public), EXPECTED_CONTEXT_HASH)
        self.assertEqual(context_hash(package), EXPECTED_CONTEXT_HASH)

    def test_product_and_source_pins_use_the_computed_hash(self):
        import json
        root = PUBLIC_CONTEXT.parents[3]
        images = json.loads((root / "assets/images.json").read_text())["images"]
        helpers = [row for row in images if row.get("support_kind") == "harbor_egress_control"]
        self.assertEqual(len(helpers), 1)
        self.assertEqual(helpers[0]["harbor_context_hash"], EXPECTED_CONTEXT_HASH)
        sources = json.loads((root / "assets/sources.json").read_text())["sources"]
        pin = sources["harbor-0220-egress-control"]
        self.assertEqual(pin["version"], HARBOR_VERSION)
        self.assertEqual(pin["harbor_context_hash"], EXPECTED_CONTEXT_HASH)

    def test_readme_links_the_checked_declaration_instead_of_copying_a_hash(self):
        import re
        readme = PUBLIC_CONTEXT.parent / 'README.md'
        text = readme.read_text()
        self.assertNotRegex(text, r'`[0-9a-f]{16}`')
        self.assertIn('harbor-0220-egress-control', text)
        targets = re.findall(r'\[[^\]]+\]\(([^)]+)\)', text)
        relative = [target for target in targets if not target.startswith('https://')]
        self.assertIn('../../sources.json', relative)
        for target in relative:
            self.assertTrue((readme.parent / target).is_file(), target)
        self.assertIn('src/tcsexam/tests/test_harbor_egress_control.py', text)

    def test_umask_022_and_002_inputs_have_one_runnable_hash(self):
        hashes = []
        for name, modes in (("022", (0o644, 0o755, 0o755)),
                            ("002", (0o664, 0o775, 0o775))):
            with self.subTest(name=name):
                source = self.folder / name / "source"
                copy_with_modes(PACKAGE_CONTEXT, source, *modes)
                context, key = normalized_context(self.folder / name / "cache", source)
                hashes.append(key)
                self.assertEqual(key, EXPECTED_CONTEXT_HASH)
                self.assertEqual(context_hash(context), key)
                self.assertEqual(stat.S_IMODE(context.stat().st_mode), 0o755)
                for relative, row in source_entries(PACKAGE_CONTEXT).items():
                    prepared = context / relative
                    self.assertEqual(prepared.read_bytes() if row["type"] == "file" else b"",
                                     (PACKAGE_CONTEXT / relative).read_bytes()
                                     if row["type"] == "file" else b"")
                    self.assertEqual(stat.S_IMODE(prepared.stat().st_mode), row["mode"])
        self.assertEqual(hashes[0], hashes[1])

    def test_parallel_preparation_reuses_one_verified_context(self):
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(
                lambda _: normalized_context(self.folder / "cache", PACKAGE_CONTEXT), range(2)))
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0][1], EXPECTED_CONTEXT_HASH)

    def test_corrupt_cache_is_rejected_without_silent_replacement(self):
        cache = self.folder / "cache"
        context, _ = normalized_context(cache, PACKAGE_CONTEXT)
        damaged = context / "gost.yaml"
        damaged.write_bytes(b"corrupt cache\n")
        with self.assertRaisesRegex(ValueError, "cache content differs"):
            normalized_context(cache, PACKAGE_CONTEXT)
        self.assertEqual(damaged.read_bytes(), b"corrupt cache\n")

    def test_host_support_uses_the_same_normalized_context(self):
        from argparse import Namespace
        from subprocess import CompletedProcess
        from unittest.mock import patch
        from tcsexam.setup import host_support_targets

        environment = harbor_docker.DockerEnvironment
        original_context = environment._EGRESS_CONTROL_SIDECAR_CONTEXT_PATH
        original_probe = environment._EGRESS_CONTROL_KERNEL_PROBE_IMAGE
        helper = "registry.example/helper@sha256:" + "a" * 64
        evidence = {
            helper: {"id": "helper", "type": "host_support", "image": helper,
                     "support_kind": "harbor_egress_control",
                     "harbor_context_hash": EXPECTED_CONTEXT_HASH},
            original_probe: {"id": "probe", "type": "host_support", "image": original_probe,
                             "support_kind": "harbor_kernel_probe"},
        }
        args = Namespace(cache=self.folder / "cache", docker_context=None)
        try:
            with patch.dict(os.environ, {}, clear=True), \
                    patch("tcsexam.setup.subprocess.run", side_effect=[
                        CompletedProcess([], 0, stdout="unix:///var/run/docker.sock\n"),
                        CompletedProcess([], 0, stdout="linux/amd64\n")]):
                support = host_support_targets(evidence, args)
            expected = self.folder / "cache/harbor/0.22.0/egress-control"
            self.assertEqual(environment._EGRESS_CONTROL_SIDECAR_CONTEXT_PATH, expected)
            self.assertEqual(support[0]["local_tag"],
                             environment._EGRESS_CONTROL_SIDECAR_DOCKER_NAME +
                             "--" + EXPECTED_CONTEXT_HASH)
        finally:
            environment._EGRESS_CONTROL_SIDECAR_CONTEXT_PATH = original_context
            environment._EGRESS_CONTROL_KERNEL_PROBE_IMAGE = original_probe
