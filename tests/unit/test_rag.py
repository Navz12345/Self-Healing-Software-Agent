from pathlib import Path

from rag import embed as embed_module
from rag import retrieve as retrieve_module


class FakeModel:
    def encode(self, texts):
        return [[float(index + 1)] * 4 for index, _ in enumerate(texts)]


class FakeCollection:
    def query(self, query_embeddings, n_results):
        return {"documents": [["## CODE_BUG\nZeroDivisionError repair runbook"][:n_results]]}


def test_build_collection_seeds_runbook(monkeypatch, tmp_path):
    runbook = tmp_path / "runbook.md"
    runbook.write_text(Path("rag/runbook.md").read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(embed_module, "SentenceTransformer", lambda _: FakeModel())

    collection = embed_module.build_collection(str(runbook), str(tmp_path / "chroma"))

    assert collection.count() >= 3


def test_retrieve_returns_chunks(monkeypatch):
    monkeypatch.setattr(retrieve_module, "get_model", lambda: FakeModel())

    chunks = retrieve_module.retrieve("divide by zero", FakeCollection(), request_id="ragtest")

    assert "CODE_BUG" in chunks[0]
