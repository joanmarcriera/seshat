import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def whisperx_sample(repo_root: Path) -> dict:
    import json
    return json.loads((repo_root / "tests/fixtures/whisperx-sample.json").read_text())
