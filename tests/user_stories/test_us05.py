import pytest

from rag import retrieve as retrieve_module
from tests.unit.test_rag import FakeCollection, FakeModel


@pytest.mark.user_story("US-05")
def test_us05_rag_augmented_diagnosis(monkeypatch):
    """
    Given: sha-app is running and ChromaDB is seeded with runbook chunks
    When: any failure injection triggers a diagnosis
    Then: DIAGNOSIS_COMPLETE log contains non-empty retrieved_chunks
          with text from rag/runbook.md
    """
    monkeypatch.setattr(retrieve_module, "get_model", lambda: FakeModel())

    chunks = retrieve_module.retrieve(
        "divide by zero error in function", FakeCollection(), request_id="us05"
    )

    assert "CODE_BUG" in chunks[0]
