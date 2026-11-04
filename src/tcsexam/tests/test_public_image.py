"""Tests for streaming public-image filtering and Docker build orchestration."""
from contextlib import contextmanager
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
from unittest.mock import Mock

import pytest

from tcsexam import public_image
from tcsexam.public_image import (
    DockerClient,
    PublicImageError,
    PublicImageManifest,
    build_public_image,
    filter_tar,
    verify_public_tar,
)


TASK = "tasks/solver/online/ds-pace2025"
REMOVE = ("/tests",)
ALLOW = ("/tests-public", "/public-instances", "/public_reference.json", "/judge")
REQUIRED = (
    "/judge/entry.sh",
    "/tests-public/checker.py",
    "/tests-public/reference.json",
    "/tests-public/instances",
    "/public-instances",
)
SOURCE_CONFIG = {
    "Entrypoint": ["/judge/entry.sh"],
    "Cmd": ["--serve"],
    "Env": [
        "PATH=/usr/local/bin:/usr/bin",
        "API_KEY=super-secret-value",
        "auth_token=another-secret-value",
        "INSTANCE_SET=hidden",
    ],
    "WorkingDir": "/judge",
    "User": "1000:1000",
    "ExposedPorts": {"8080/tcp": {}},
    "Volumes": {"/work": {}},
    "StopSignal": "SIGTERM",
    "Labels": {"internal": "secret-label-value"},
}
PUBLIC_CONFIG = {
    "Entrypoint": ["/judge/entry.sh"],
    "Cmd": ["--serve"],
    "Env": ["PATH=/usr/local/bin:/usr/bin", "INSTANCE_SET=public"],
    "WorkingDir": "/judge",
    "User": "1000:1000",
    "ExposedPorts": {"8080/tcp": {}},
    "Volumes": {"/work": {}},
    "StopSignal": "SIGTERM",
    "Labels": dict(public_image.NEUTRAL_LABELS),
}


def manifest(*, remove=REMOVE, allow=ALLOW, required=REQUIRED,
             distribution='redistributable', allowed=True):
    return PublicImageManifest(1, TASK, tuple(remove), tuple(allow), tuple(required),
                               distribution=distribution, public_upload_allowed=allowed)


def make_tar(entries):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w") as archive:
        for entry in entries:
            name, kind, value = entry
            info = tarfile.TarInfo(name)
            if kind == "file":
                info.size = len(value)
                archive.addfile(info, io.BytesIO(value))
            elif kind == "dir":
                info.type = tarfile.DIRTYPE
                archive.addfile(info)
            elif kind == "symlink":
                info.type = tarfile.SYMTYPE
                info.linkname = value
                archive.addfile(info)
            elif kind == "hardlink":
                info.type = tarfile.LNKTYPE
                info.linkname = value
                archive.addfile(info)
            else:
                raise AssertionError(kind)
    return output.getvalue()


def names(data):
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
        return archive.getnames()


def base_entries(hidden=b"hidden reference", public=b"public reference"):
    return [
        ("./judge", "dir", None),
        ("./judge/entry.sh", "file", b"#!/bin/sh\n"),
        ("./tests-public", "dir", None),
        ("./tests-public/checker.py", "file", b"checker\n"),
        ("./tests-public/reference.json", "file", public),
        ("./tests-public/instances", "dir", None),
        ("./public-instances", "dir", None),
        ("./public-instances/example.gr", "file", b"public instance\n"),
        ("./public_reference.json", "file", public),
        ("./tests", "dir", None),
        ("./tests/reference.json", "file", hidden),
    ]


PAYLOAD_FILES = ("/app/public.txt", "/app/solutions/public.sol")


def payload_manifest(files=PAYLOAD_FILES):
    return PublicImageManifest(
        1, TASK, REMOVE, ALLOW + ("/app",), REQUIRED,
        distribution="redistributable", public_upload_allowed=True,
        payload_allowlist=(public_image.PayloadAllowlist("/app", tuple(files), len(files)),),
    )


def payload_entries(*, include_hidden=True):
    entries = base_entries() + [
        ("./app", "dir", None),
        ("./app/public.txt", "file", b"public payload\n"),
        ("./app/solutions", "dir", None),
        ("./app/solutions/public.sol", "file", b"public practice answer\n"),
    ]
    if include_hidden:
        return entries
    return [entry for entry in entries
            if entry[0] != "./tests" and not entry[0].startswith("./tests/")]


def test_payload_allowlist_build_and_independent_reexport():
    fake = FakeDocker(make_tar(payload_entries()))
    report = build_public_image(
        "registry.example/judge:hidden", "registry.example/judge:public",
        payload_manifest(), docker=fake,
    )
    assert report["payload_allowlist_files"] == {"/app": 2}
    assert report["payload_allowlist_total_files"] == 2
    assert report["pushed"] is False


@pytest.mark.parametrize("path", [
    "app/instances/hidden-source.col",
    "app/solutions/extra-answer.sol",
    "app/neither/example.col",
    "app/instances/transformed-hidden.col",
])
def test_payload_allowlist_rejects_old_or_extra_input_files(path):
    entries = payload_entries() + [(path, "file", b"different unlisted bytes")]
    with pytest.raises(PublicImageError, match="not a listed regular file"):
        filter_tar(io.BytesIO(make_tar(entries)), io.BytesIO(), payload_manifest())


def test_payload_verifier_rejects_unlisted_path_with_unrelated_hash():
    entries = payload_entries(include_hidden=False) + [
        ("app/solutions/extra-answer.sol", "file", b"hash is not in hidden set"),
    ]
    with pytest.raises(PublicImageError, match="not a listed regular file"):
        verify_public_tar(io.BytesIO(make_tar(entries)), payload_manifest(), set())


def test_payload_allowlist_rejects_missing_listed_file():
    entries = [entry for entry in payload_entries()
               if entry[0] != "./app/solutions/public.sol"]
    with pytest.raises(PublicImageError, match="files missing after filtering"):
        filter_tar(io.BytesIO(make_tar(entries)), io.BytesIO(), payload_manifest())


def test_payload_allowlist_rejects_non_regular_entry():
    entries = payload_entries() + [
        ("app/solutions/link.sol", "symlink", "public.sol"),
    ]
    with pytest.raises(PublicImageError, match="not a listed regular file"):
        filter_tar(io.BytesIO(make_tar(entries)), io.BytesIO(), payload_manifest())


def test_payload_manifest_checks_declared_count_and_remove_overlap():
    raw = {
        "schema_version": 1,
        "task": TASK,
        "remove_paths": ["/tests"],
        "allow_content_paths": ["/app"],
        "required_paths": [],
        "payload_allowlist": [{
            "root": "/app",
            "files": list(PAYLOAD_FILES),
            "regular_file_count": 3,
        }],
    }
    with pytest.raises(PublicImageError, match="regular_file_count"):
        PublicImageManifest.from_dict(raw)
    raw["payload_allowlist"][0]["regular_file_count"] = 2
    raw["remove_paths"].append("/app/cache")
    with pytest.raises(PublicImageError, match="overlaps remove_paths"):
        PublicImageManifest.from_dict(raw)


def test_allow_content_paths_alone_remains_hash_permission_not_path_allowlist():
    entries = payload_entries() + [("app/unlisted.txt", "file", b"legacy retained file")]
    destination = io.BytesIO()
    filter_tar(io.BytesIO(make_tar(entries)), destination, manifest(allow=ALLOW + ("/app",)))
    assert "app/unlisted.txt" in names(destination.getvalue())
    with pytest.raises(PublicImageError, match="not a listed regular file"):
        filter_tar(io.BytesIO(make_tar(entries)), io.BytesIO(), payload_manifest())


class FakeDocker:
    def __init__(self, source_tar, *, layers=1, output_config=None):
        self.source_tar = source_tar
        self.output_tar = None
        self.layers = layers
        self.output_config = output_config or PUBLIC_CONFIG
        self.source_inspection = {"Config": SOURCE_CONFIG}
        self.containers = {}
        self.created = []
        self.removed = []
        self.pulled = []
        self.pushed = []
        self.changes = None
        self.operations = []

    def pull(self, image):
        self.pulled.append(image)

    def inspect(self, image):
        if image == "registry.example/judge:hidden":
            return self.source_inspection
        assert image == "registry.example/judge:public"
        return {
            "Config": self.output_config,
            "RootFS": {"Layers": ["sha256:layer"] * self.layers},
        }

    def create(self, image):
        container = f"created-{len(self.created) + 1}"
        self.created.append(container)
        self.containers[container] = image
        self.operations.append(("create", container))
        return container

    @contextmanager
    def export(self, container):
        self.operations.append(("export", container))
        data = self.source_tar if self.containers[container].endswith(":hidden") else self.output_tar
        yield io.BytesIO(data)

    def import_tar(self, stream, changes, output_image):
        self.changes = changes
        self.output_tar = stream.read()
        self.operations.append(("import", output_image))

    def remove(self, container):
        self.removed.append(container)
        self.operations.append(("remove", container))

    def push(self, image):
        self.pushed.append(image)
        self.operations.append(("push", image))


def build(fake, **kwargs):
    return build_public_image(
        "registry.example/judge:hidden",
        "registry.example/judge:public",
        manifest(),
        docker=fake,
        **kwargs,
    )


def test_filter_accepts_dot_prefix_and_streams_required_paths():
    destination = io.BytesIO()
    result = filter_tar(io.BytesIO(make_tar(base_entries())), destination, manifest())
    filtered_names = names(destination.getvalue())
    assert "./tests/reference.json" not in filtered_names
    assert "tests/reference.json" not in filtered_names
    assert "judge/entry.sh" in filtered_names
    assert result.removed_regular_files == 1
    assert result.allowed_regular_files == 5
    assert result.retained_regular_files == 5


@pytest.mark.parametrize("entry", ["../escape", "/absolute", "safe/../../escape"])
def test_filter_rejects_tar_path_traversal(entry):
    with pytest.raises(PublicImageError, match="Unsafe tar entry"):
        filter_tar(io.BytesIO(make_tar([(entry, "file", b"bad")])), io.BytesIO(), manifest())


@pytest.mark.parametrize("path", ["/", "/tests/../public", "tests"])
def test_manifest_rejects_root_parent_and_relative_paths(path):
    raw = {
        "schema_version": 1,
        "task": TASK,
        "remove_paths": [path],
        "allow_content_paths": [],
        "required_paths": [],
    }
    with pytest.raises(PublicImageError):
        PublicImageManifest.from_dict(raw)


def test_manifest_requires_known_hidden_removals():
    raw = {
        "schema_version": 1,
        "task": TASK,
        "remove_paths": ["/tests/instances"],
        "allow_content_paths": [],
        "required_paths": [],
    }
    with pytest.raises(PublicImageError, match="must remove known hidden reference/oracle paths"):
        PublicImageManifest.from_dict(raw)
    raw["remove_paths"].extend([
        "/tests/anchors.json", "/tests/reference-hidden.json", "/tests/solution",
    ])
    assert PublicImageManifest.from_dict(raw).task == TASK


def test_filter_fails_when_required_path_is_missing():
    entries = [entry for entry in base_entries() if entry[0] != "./judge/entry.sh"]
    with pytest.raises(PublicImageError, match="Required paths missing.*judge/entry.sh"):
        filter_tar(io.BytesIO(make_tar(entries)), io.BytesIO(), manifest())


@pytest.mark.parametrize("name", ["public-instances/instance.key", "public-instances/old.txt.xz.enc"])
def test_filter_rejects_keys_and_legacy_ciphertext(name):
    with pytest.raises(PublicImageError, match="Forbidden key or encrypted file"):
        filter_tar(
            io.BytesIO(make_tar(base_entries() + [(name, "file", b"secret")])),
            io.BytesIO(),
            manifest(),
        )


@pytest.mark.parametrize(
    "name",
    [
        "tests/anchors.json",
        "tests/reference-hidden.json",
        "tests/solution/precomputed/answer.txt",
        "tests/reference.json.bak-repin20260905",
    ],
)
def test_filter_rejects_hidden_reference_and_oracle_paths(name):
    with pytest.raises(PublicImageError, match="Forbidden hidden reference or oracle content"):
        filter_tar(
            io.BytesIO(make_tar(base_entries() + [(name, "file", b"secret")])),
            io.BytesIO(),
            manifest(remove=("/tests/instances",)),
        )


@pytest.mark.parametrize(
    "kind,name,target",
    [
        ("symlink", "public-instances/leak", "../tests/reference.json"),
        ("hardlink", "public-instances/leak", "tests/reference.json"),
    ],
)
def test_filter_rejects_links_into_removed_hidden_tree(kind, name, target):
    with pytest.raises(PublicImageError, match="points into removed hidden path"):
        filter_tar(
            io.BytesIO(make_tar(base_entries() + [(name, kind, target)])),
            io.BytesIO(),
            manifest(),
        )


def test_verifier_rejects_forbidden_path_even_if_filter_was_bypassed():
    entries = [entry for entry in base_entries()
               if entry[0] != "./tests" and not entry[0].startswith("./tests/")]
    data = make_tar(entries + [("opt/instance.key", "file", b"secret")])
    with pytest.raises(PublicImageError, match="Forbidden key or encrypted file"):
        verify_public_tar(io.BytesIO(data), manifest(), set())


def test_hidden_file_copied_elsewhere_fails_after_reexport_and_is_not_pushed():
    secret = b"unique hidden bytes"
    fake = FakeDocker(make_tar(base_entries(hidden=secret) + [("opt/copy", "file", secret)]))
    digest = hashlib.sha256(secret).hexdigest()
    with pytest.raises(PublicImageError, match=f"Hidden content copied to /opt/copy: sha256={digest}"):
        build(fake, push=True)
    assert fake.pushed == []
    assert sorted(fake.removed) == sorted(fake.created)


def test_public_push_requires_an_explicit_distribution_decision():
    for distribution, allowed, message in (
            (None, False, 'no accepted distribution decision'),
            ('local_prepare', False, 'not authorized'),
            ('redistributable', False, 'not authorized')):
        fake = FakeDocker(make_tar(base_entries()))
        rule = manifest(distribution=distribution, allowed=allowed)
        with pytest.raises(PublicImageError, match=message):
            build_public_image('registry.example/judge:hidden', 'registry.example/judge:public',
                               rule, push=True, docker=fake)
        assert fake.created == []
        assert fake.pushed == []


def test_private_registry_is_explicit_and_allows_local_preparation():
    fake = FakeDocker(make_tar(base_entries()))
    rule = manifest(distribution='local_prepare', allowed=False)
    report = build_public_image('registry.example/judge:hidden', 'registry.example/judge:public',
                                rule, push=True, private_registry=True, docker=fake)
    assert report['pushed'] is True
    assert fake.pushed == ['registry.example/judge:public']


def test_content_also_allowed_public_may_be_duplicated_and_pushed():
    shared = b"explicitly public shared bytes"
    entries = base_entries(hidden=shared, public=shared) + [("opt/public-copy", "file", shared)]
    fake = FakeDocker(make_tar(entries))
    report = build(fake, push=True)
    assert report["hidden_only_hashes"] == 0
    assert report["pushed"] is True
    assert fake.pushed == ["registry.example/judge:public"]
    assert fake.operations[-1] == ("push", "registry.example/judge:public")


def test_multiple_imported_layers_fail_before_target_export_or_push():
    fake = FakeDocker(make_tar(base_entries()), layers=2)
    with pytest.raises(PublicImageError, match="exactly one RootFS layer; found 2"):
        build(fake, push=True)
    assert len(fake.created) == 1
    assert fake.removed == fake.created
    assert fake.pushed == []


def test_oci_config_is_preserved_without_sensitive_values_or_old_labels():
    fake = FakeDocker(make_tar(base_entries()))
    report = build(fake)
    changes = "\n".join(fake.changes)
    assert 'ENTRYPOINT ["/judge/entry.sh"]' in changes
    assert 'CMD ["--serve"]' in changes
    assert 'ENV PATH="/usr/local/bin:/usr/bin"' in changes
    assert 'ENV INSTANCE_SET="public"' in changes
    assert "WORKDIR /judge" in changes
    assert "USER 1000:1000" in changes
    assert "EXPOSE 8080/tcp" in changes
    assert 'VOLUME ["/work"]' in changes
    assert "STOPSIGNAL SIGTERM" in changes
    assert "super-secret-value" not in changes
    assert "another-secret-value" not in changes
    assert "secret-label-value" not in changes
    assert "INSTANCE_SET=hidden" not in changes
    assert report["dropped_environment_names"] == ["API_KEY", "auth_token"]


def test_environment_instructions_quote_spaces_and_special_characters():
    changes = public_image._config_changes({
        "Env": ["JUDGE_CMD=bash /judge/entry.sh", "QUOTED=a \"b\"\\c"],
        "Labels": {},
    })
    assert changes == [
        'ENV JUDGE_CMD="bash /judge/entry.sh"',
        'ENV QUOTED="a \\"b\\"\\\\c"',
    ]


def test_config_verification_error_does_not_echo_environment_values():
    wrong = dict(PUBLIC_CONFIG)
    wrong["Env"] = ["PATH=/different", "INSTANCE_SET=public"]
    fake = FakeDocker(make_tar(base_entries()), output_config=wrong)
    with pytest.raises(PublicImageError) as caught:
        build(fake)
    message = str(caught.value)
    assert "Config.Env" in message
    assert "super-secret-value" not in message
    assert "/different" not in message


def test_only_containers_created_by_this_build_are_cleaned_up():
    unrelated = "preexisting-container"
    fake = FakeDocker(make_tar(base_entries()))
    fake.containers[unrelated] = "registry.example/unrelated:image"
    build(fake)
    assert sorted(fake.removed) == sorted(fake.created)
    assert unrelated not in fake.removed
    assert unrelated in fake.containers


def test_cli_supports_pull_and_push_without_printing_secret_values(tmp_path, monkeypatch, capsys):
    path = tmp_path / "public-image.json"
    path.write_text(json.dumps({
        "schema_version": 1,
        "task": TASK,
        "remove_paths": list(REMOVE),
        "allow_content_paths": list(ALLOW),
        "required_paths": list(REQUIRED),
        "distribution": "redistributable",
        "public_upload_allowed": True,
    }))
    fake = FakeDocker(make_tar(base_entries()))
    monkeypatch.setattr(public_image, "DockerClient", lambda: fake)
    result = public_image.main([
        "--source-image", "registry.example/judge:hidden",
        "--output-image", "registry.example/judge:public",
        "--manifest", str(path),
        "--pull",
        "--push",
    ])
    captured = capsys.readouterr()
    assert result == 0
    assert fake.pulled == ["registry.example/judge:hidden"]
    assert fake.pushed == ["registry.example/judge:public"]
    assert "super-secret-value" not in captured.out + captured.err
    assert "another-secret-value" not in captured.out + captured.err
    assert json.loads(captured.out)["rootfs_layers"] == 1


def test_docker_client_uses_argument_arrays_and_removes_only_named_container():
    run = Mock(return_value=subprocess.CompletedProcess([], 0, stdout=b""))
    client = DockerClient()
    original = public_image.subprocess.run
    public_image.subprocess.run = run
    try:
        client.remove("created-by-this-build")
    finally:
        public_image.subprocess.run = original
    run.assert_called_once_with(
        ["docker", "rm", "created-by-this-build"],
        stdin=None,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def test_all_thirty_task_public_manifests_are_complete_and_valid():
    from tcsexam.layout import repository

    paths = sorted((repository() / "assets/environments/solver").glob("*/public-image.json"))
    assert len(paths) == 30
    for path in paths:
        manifest = public_image.load_manifest(path)
        assert manifest.task == f"tasks/solver/online/{path.parent.name}"
        assert manifest.allow_content_paths
        assert manifest.required_paths


def test_only_celar_and_coloring_opt_into_exact_payload_allowlists():
    from tcsexam.layout import repository

    root = repository() / "assets/environments/solver"
    strict = {}
    for path in sorted(root.glob("*/public-image.json")):
        rule = public_image.load_manifest(path)
        if rule.payload_allowlist:
            strict[path.parent.name] = rule
    assert set(strict) == {"celar-rlfap", "coloring-dimacs"}
    assert sum(item.regular_file_count for item in strict["celar-rlfap"].payload_allowlist) == 42
    assert sum(item.regular_file_count for item in strict["coloring-dimacs"].payload_allowlist) == 281

    answers = {}
    for task, rule in strict.items():
        answers[task] = {
            path for item in rule.payload_allowlist for path in item.files
            if path.startswith("/app/solutions/") and path.endswith(".sol")
        }
    assert answers["celar-rlfap"] == set()
    assert answers["coloring-dimacs"] == {
        "/app/solutions/DSJC250.5.col.sol",
        "/app/solutions/mug88_1.col.sol",
        "/app/solutions/myciel6.col.sol",
        "/app/solutions/queen8_8.col.sol",
        "/app/solutions/r250.5.col.sol",
    }


def test_public_rebuild_records_match_payload_allowlists_and_block_release():
    from tcsexam.layout import repository

    root = repository()
    images = fixed_image_records()
    for task in ("celar-rlfap", "coloring-dimacs"):
        record = json.loads((root /
                             f"assets/environments/solver/{task}/judge/public-rebuild.json").read_text())
        manifest = json.loads((root / record["manifest"]).read_text())
        assert record["task"] == manifest["task"] == f"tasks/solver/online/{task}"
        groups = manifest["payload_allowlist"]
        assert {group["root"]: len(group["files"]) for group in groups} == record["payload_allowlist"]["roots"]
        assert all(group["regular_file_count"] == len(group["files"]) for group in groups)
        files = [path for group in groups for path in group["files"]]
        assert len(files) == len(set(files)) == record["payload_allowlist"]["total_regular_files"]
        assert not any(path == "/tests" or path.startswith("/tests/") for path in files)
        public_instances = {path.removeprefix("/public-instances/") for path in files
                            if path.startswith("/public-instances/")}
        data = images[f"solver-{task}-development-data"]
        data_files = json.loads((root / data["files_manifest"]).read_text())["files"]
        assert public_instances == {row["path"].removeprefix("app/instances/") for row in data_files}
        assert {path for path in files if path.startswith("/app/solutions/")} == set(
            record["payload_allowlist"]["public_practice_answers"]
            + record["payload_allowlist"]["public_solution_placeholders"]
        )
        assert data["data_split"] == "public"
        assert record["distribution"] == "local_prepare"
        assert manifest["distribution"] == "unresolved"
        assert manifest["public_upload_allowed"] is False
        assert record["license_review"]["required_before_any_upload"] is True
        assert record["license_review"]["system_dependencies_and_third_party_data_reviewed_for_public_distribution"] is False


def fixed_image_records():
    from tcsexam.layout import repository

    rows = json.loads((repository() / "assets/images.json").read_text())["images"]
    return {row["id"]: row for row in rows if row.get("id")}


def test_qbf_approved_content_is_not_blocked_by_legacy_classification():
    from tcsexam.inventory import classification

    paths = [
        "tasks/solver/online/qbf-qbfeval/environment/app/instances/ex018.qdimacs.xz",
        "tasks/solver/online/qbf-qbfeval/solution/precomputed/ex018.qrp.xz",
        "tasks/solver/online/qbf-qbfeval/solution/precomputed/manifest.json",
        "tasks/solver/offline/qbf-qbfeval/tests/reference.json",
        "tasks/solver/offline/qbf-qbfeval/tests/reference-transformed.json",
        "tasks/solver/offline/qbf-qbfeval/tests/anchors.json",
    ]
    for path in paths:
        purpose, distribution, evidence = classification(path)
        expected_evidence = ("docs/licenses/third-party/qbf-data-distribution-source.json"
                             if "/environment/" in path
                             else "docs/licenses/third-party/distribution-decisions.json")
        assert purpose
        assert distribution == "redistributable", path
        assert evidence == expected_evidence


def test_qbf_accepted_products_retain_bmc_conditions_and_publication_pending_state():
    from tcsexam.layout import repository

    records = fixed_image_records()
    accepted = [
        "qbf-public",
        "qbf-judging",
        "qbf-qbfeval-online-development",
        "qbf-qbfeval-offline-development",
        "qbf-qbfeval-online-backend",
        "qbf-qbfeval-offline-verifier",
        "backend-public-online-qbf-qbfeval",
    ]
    for identity in accepted:
        assert records[identity]["distribution"] == "redistributable"
        assert records[identity]["public_upload_allowed"] is True
        assert records[identity]["public_image"] is None
        assert records[identity]["public_pull_verified"] is False

    conditions = " ".join(records["qbf-judging"]["conditions"])
    for instance in ("ex018", "ex019", "ex020"):
        assert instance in conditions
    assert "noncommercial education/research" in conditions

    manifest = public_image.load_manifest(
        repository() / "assets/environments/solver/qbf-qbfeval/public-image.json"
    )
    assert manifest.distribution == "redistributable"
    assert manifest.public_upload_allowed is True

    decisions = json.loads((repository() /
                            "docs/licenses/third-party/distribution-decisions.json").read_text())
    qbf = next(row for row in decisions["resources"] if row["id"] == "qbf-70-data")
    assert set(qbf["accepted_fixed_products"]) == set(accepted)
    decision_conditions = " ".join(qbf["conditions"])
    for instance in ("ex018", "ex019", "ex020"):
        assert instance in decision_conditions
    assert decisions["enforced_by_exporter"] is False
    assert decisions["integration_complete"] is False


def test_qbf_judging_recipe_matches_image_distribution_and_bmc_conditions():
    from tcsexam.layout import repository

    image = fixed_image_records()["qbf-judging"]
    recipe = json.loads((repository() / image["recipe"]).read_text())

    # The current reconstruction recipe grants no new distribution rights.
    # The fixed historical image retains its separate accepted conditions.
    assert recipe["distribution"] == "local_prepare"
    assert recipe["public_upload_allowed"] is False
    assert recipe["distribution_evidence"] == "docs/licenses/third-party/qbf-data-distribution-source.json"
    assert "original Toronto research-only conditions" in recipe["terms"]
    conditions = " ".join(image["conditions"])
    for instance in ("ex018", "ex019", "ex020"):
        assert instance in conditions
    assert "noncommercial education/research" in conditions


def test_mr_products_with_pdf_or_incomplete_scope_cannot_be_publicly_pushed():
    from tcsexam.layout import repository

    records = fixed_image_records()
    blocked = [
        "solver-mr-roadef2012-development-data",
        "dev-online-mr-roadef2012",
        "dev-offline-mr-roadef2012",
        "verifier-mr-roadef2012",
        "backend-online-mr-roadef2012",
        "backend-public-online-mr-roadef2012",
    ]
    for identity in blocked:
        assert records[identity]["public_upload_allowed"] is False
        assert records[identity]["distribution"] != "redistributable"
        assert records[identity]["public_image"] is None
        assert records[identity]["public_pull_verified"] is False

    judging = records["solver-mr-roadef2012-judging-data"]
    assert judging["distribution"] == "local_prepare"
    assert judging["public_upload_allowed"] is False
    assert judging["public_image"] is None
    assert judging["public_pull_verified"] is False
    recipe = json.loads((repository() / judging["recipe"]).read_text())
    assert recipe["distribution"] == judging["distribution"]
    assert recipe["public_upload_allowed"] is False

    rule = public_image.load_manifest(
        repository() / "assets/environments/solver/mr-roadef2012/public-image.json"
    )
    assert rule.distribution == records["backend-public-online-mr-roadef2012"]["distribution"]
    assert rule.public_upload_allowed is False
    fake = FakeDocker(make_tar(base_entries()))
    with pytest.raises(PublicImageError, match="no accepted distribution decision"):
        build_public_image("registry.example/judge:hidden", "registry.example/judge:public",
                           rule, push=True, docker=fake)
    assert fake.created == []
    assert fake.pushed == []


def test_local_generation_and_explicit_private_storage_remain_available():
    from tcsexam.inventory import classification

    pdf = "tasks/solver/online/mr-roadef2012/environment/app/problem_definition_v1_1.pdf"
    assert classification(pdf)[1] == "local_prepare"
    rule = manifest(distribution="local_prepare", allowed=False)

    local_fake = FakeDocker(make_tar(base_entries()))
    local = build_public_image("registry.example/judge:hidden", "registry.example/judge:public",
                               rule, docker=local_fake)
    assert local["pushed"] is False
    assert local_fake.pushed == []

    private_fake = FakeDocker(make_tar(base_entries()))
    private = build_public_image("registry.example/judge:hidden", "registry.example/judge:public",
                                 rule, push=True, private_registry=True, docker=private_fake)
    assert private["pushed"] is True
    assert private_fake.pushed == ["registry.example/judge:public"]


def test_isolation_rebuild_records_use_only_public_dependencies_and_block_publication():
    root = Path(__file__).resolve().parents[3]
    images = fixed_image_records()
    for task in ("celar-rlfap", "coloring-dimacs"):
        identity = f"backend-public-online-{task}"
        row = images[identity]
        assert row["distribution"] == "local_prepare"
        assert row["public_upload_allowed"] is False
        assert row["public_image"] is None
        assert row["public_pull_verified"] is False
        assert row["build"].get("kind", "docker") == "docker"
        assert "source_product" not in row["build"]
        assert row["dependencies"] == [f"dev-online-{task}", f"solver-{task}-development-data"]
        assert row["build"]["image_args"] == {
            "TCSEXAM_CLEAN_TOOLS_IMAGE": f"dev-online-{task}",
            "TCSEXAM_JUDGE_DATA_IMAGE": f"solver-{task}-development-data",
        }
        assert images[f"solver-{task}-development-data"]["data_split"] == "public"
        pending = list(row["dependencies"])
        seen = set()
        while pending:
            dependency = pending.pop()
            if dependency in seen:
                continue
            seen.add(dependency)
            product = images[dependency]
            assert product.get("data_split") != "hidden"
            pending.extend(product.get("dependencies", []))
        assert f"backend-online-{task}" not in seen
        dockerfile = (root / row["build"]["dockerfile"]).read_text()
        assert "TCSEXAM_JUDGE_DATA_IMAGE" in dockerfile
        assert "TCSEXAM_CLEAN_TOOLS_IMAGE" in dockerfile
        assert row["public_source_cleanup_verified"] is True
        rebuild = json.loads((root / row["distribution_evidence"]).read_text())
        assert rebuild["distribution"] == "local_prepare"
        assert rebuild["license_review"]["required_before_any_upload"] is True
    decisions = json.loads((root / "docs/licenses/third-party/distribution-decisions.json").read_text())
    assert decisions["integration_complete"] is False
    assert decisions["enforced_by_exporter"] is False
    decision = next(row for row in decisions["resources"]
                    if row["id"] == "public-self-test-isolation-remediation")
    assert decision["local_preparation_products"] == [
        "backend-public-online-celar-rlfap", "backend-public-online-coloring-dimacs"
    ]
    assert decision["public_upload_performed"] is False
    assert decision["anonymous_public_pull_verified"] is False
