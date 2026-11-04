from pathlib import Path

import pytest

from tcsexam.source_inputs import prepare_source_inputs


@pytest.fixture(scope="session")
def prepared_lean_source_inputs(tmp_path_factory):
    """Verify explicitly prepared materials; unit tests never fetch real archives."""
    root = Path(__file__).resolve().parents[3]
    return prepare_source_inputs(root, tmp_path_factory.mktemp("lean-source-cache"), offline=True)
