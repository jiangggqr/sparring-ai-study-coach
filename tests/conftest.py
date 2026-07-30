from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
try:
    sys.path.remove(str(PROJECT_ROOT))
except ValueError:
    pass
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


SAMPLE_MATERIAL = """Retrieval practice asks a learner to bring an idea back from memory before
seeing the answer. The effort of trying makes later feedback more useful because the learner
can compare an attempted answer with the source.

Confidence judgments add a second observation to each answer. A correct response with low
confidence and an incorrect response with high confidence need different feedback, even when
the quiz score alone looks similar.

Spaced practice returns to an idea after time has passed. A cold review changes the wording
and removes hints, so the learner must reconstruct the relationship rather than recognize the
original question. One, three, and seven days are a transparent default schedule here."""


@pytest.fixture
def material() -> str:
    return SAMPLE_MATERIAL


@pytest.fixture
def client(tmp_path: Path):
    settings = Settings(
        mode="fixture",
        database_path=tmp_path / "sparring.sqlite3",
        static_dir=PROJECT_ROOT / "static",
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client
