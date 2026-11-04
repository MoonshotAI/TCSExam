"""Keep oracle-answer path policy aligned between inventory and export."""
import json
from pathlib import Path

from tcsexam.inventory import classification, refresh
from tcsexam.oracle_answers import is_oracle_answer_path


EVIDENCE = "docs/licenses/third-party/distribution-decisions.json"
ANSWER_PATHS = (
    "tasks/solver/online/ce-pace2021/solution/precomputed/heur003.out",
    "tasks/solver/online/hs-pace2025/solution/precomputed.tar.xz",
    "tasks/solver/online/jsplib-jssp/solution/solutions/ex002.sol",
    "tasks/construction/binary-code-a22-10/solution/Basic.lean",
    "tasks/solver/online/mr-roadef2012/tests/solution/precomputed/expected.sol",
)
QBF_EXCEPTIONS = (
    "tasks/solver/online/qbf-qbfeval/solution/precomputed/ex018.qrp.xz",
    "tasks/solver/online/qbf-qbfeval/solution/precomputed/manifest.json",
    "tasks/solver/offline/qbf-qbfeval/tests/reference.json",
    "tasks/solver/offline/qbf-qbfeval/tests/reference-transformed.json",
    "tasks/solver/offline/qbf-qbfeval/tests/anchors.json",
    "tasks/solver/offline/qbf-qbfeval/tests/mapping.json",
)
NON_ANSWER_PATHS = (
    "tasks/solver/online/example/solution/solve.sh",
    "tasks/solver/online/example/solution/reference.json",
    "tasks/solver/online/example/solution/generate.py",
    "tasks/solver/online/example/tests/reference.json",
    "tasks/solver/online/example/tests/scoring.py",
    "tasks/solver/online/example/tests/instances/hidden.dat",
    "tasks/solver/online/example/environment/app/instances/public.dat",
    "tasks/solver/online/example/environment/app/solutions/reference.sol",
)


def test_answer_path_rule_covers_known_forms_without_name_based_false_positives():
    for path in ANSWER_PATHS + QBF_EXCEPTIONS[:2]:
        assert is_oracle_answer_path(path), path
    for path in NON_ANSWER_PATHS + QBF_EXCEPTIONS[2:]:
        assert not is_oracle_answer_path(path), path


def test_inventory_makes_answers_private_but_retains_qbf_public_exceptions():
    for path in ANSWER_PATHS:
        purpose, distribution, evidence = classification(path)
        assert distribution == "private_only", path
        assert evidence == EVIDENCE
        expected_purpose = "hidden_judging" if "/tests/" in path else "reference_validation"
        assert purpose == expected_purpose
    for path in QBF_EXCEPTIONS:
        assert classification(path) == ("reference_validation" if "/solution/" in path
                                       else "hidden_judging", "redistributable", EVIDENCE)
    for path in NON_ANSWER_PATHS:
        assert classification(path)[1] == "unresolved", path


def test_inventory_refresh_moves_only_answers_and_preserves_file_metadata(tmp_path):
    paths = ANSWER_PATHS + QBF_EXCEPTIONS + NON_ANSWER_PATHS
    rows = [{"path": path, "bytes": index + 1, "git_blob": f"{index:040x}",
             "mode": "100644", "retained_field": "unchanged"}
            for index, path in enumerate(paths)]
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "files.json").write_text(json.dumps({"files": rows}))
    (assets / "images.json").write_text('{"images": []}\n')

    refresh(tmp_path)

    updated = {row["path"]: row for row in
               json.loads((assets / "files.json").read_text())["files"]}
    assert len(updated) == len(rows)
    for index, (path, row) in enumerate(updated.items()):
        assert row["bytes"] == index + 1
        assert row["git_blob"] == f"{index:040x}"
        assert row["mode"] == "100644"
        assert row["retained_field"] == "unchanged"
    for path in ANSWER_PATHS:
        assert updated[path]["distribution"] == "private_only"
        assert updated[path]["group_id"].endswith("private_only")
    for path in QBF_EXCEPTIONS:
        assert updated[path]["distribution"] == "redistributable"
    for path in NON_ANSWER_PATHS:
        assert updated[path]["distribution"] == "unresolved"


def test_refresh_splits_test_answers_from_public_checker_references(tmp_path):
    answer = "tasks/solver/online/mr-roadef2012/tests/solution/precomputed/expected.sol"
    reference = "tasks/solver/online/mr-roadef2012/tests/reference.json"
    hidden = "tasks/solver/online/mr-roadef2012/tests/instances/hidden.dat"
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "files.json").write_text(json.dumps({"files": [
        {"path": answer, "bytes": 3},
        {"path": reference, "bytes": 5},
        {"path": hidden, "bytes": 7},
    ]}))
    (assets / "images.json").write_text('{"images": []}\n')

    refresh(tmp_path)

    groups = {row["id"]: row for row in
              json.loads((assets / "resource-groups.json").read_text())["groups"]}
    private = groups["tasks-solver-online-mr-roadef2012-hidden_judging-private_only"]
    public = groups["tasks-solver-online-mr-roadef2012-hidden_judging-redistributable"]
    assert (private["files"], private["bytes"]) == (1, 3)
    assert (public["files"], public["bytes"]) == (2, 12)


def test_repository_inventory_matches_the_shared_classification():
    root = Path(__file__).resolve().parents[3]
    rows = json.loads((root / "assets/files.json").read_text())["files"]
    for row in rows:
        expected = classification(row["path"])
        actual = (row["purpose"], row["distribution"], row["distribution_evidence"])
        assert actual == expected, row["path"]
