import pytest

from rag import retrieve as retrieve_module
from tests.unit.test_rag import FakeCollection, FakeModel


@pytest.mark.user_story("US-05")
def test_us05_rag_augmented_diagnosis(monkeypatch):
    monkeypatch.setattr(retrieve_module, "get_model", lambda: FakeModel())

    chunks = retrieve_module.retrieve(
        "divide by zero error in function", FakeCollection(), request_id="us05"
    )

    assert "CODE_BUG" in chunks[0]
