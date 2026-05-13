import hashlib
import sqlite3
import tempfile
from pathlib import Path

import chromadb
import numpy as np
from sentence_transformers import SentenceTransformer

from logger import get_logger

log = get_logger(__name__)
MODEL_NAME = "all-MiniLM-L6-v2"


class HashEmbeddingModel:
    def encode(self, texts):
        vectors = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            values = [byte / 255.0 for byte in digest]
            vectors.append((values * 12)[:384])
        return np.array(vectors, dtype=float)


def get_embedding_model():
    try:
        return SentenceTransformer(MODEL_NAME, local_files_only=True)
    except Exception as exc:
        log.warning(
            "RAG_EMBEDDING_FALLBACK",
            extra={"request_id": "none", "model": MODEL_NAME, "error": str(exc)},
        )
        return HashEmbeddingModel()


def build_collection(
    runbook_path: str = "rag/runbook.md",
    persist_dir: str = ".chromadb",
) -> chromadb.Collection:
    try:
        client = chromadb.PersistentClient(path=persist_dir)
    except sqlite3.OperationalError as exc:
        fallback_dir = str(Path(tempfile.gettempdir()) / "sha_chromadb")
        log.warning(
            "RAG_PERSIST_FALLBACK",
            extra={
                "request_id": "none",
                "persist_dir": persist_dir,
                "fallback": fallback_dir,
                "error": str(exc),
            },
        )
        client = chromadb.PersistentClient(path=fallback_dir)
    collection = client.get_or_create_collection("runbook")

    if collection.count() > 0:
        log.info(
            "RAG_ALREADY_SEEDED",
            extra={"request_id": "none", "count": collection.count()},
        )
        return collection

    model = get_embedding_model()
    text = Path(runbook_path).read_text(encoding="utf-8")
    chunks = [chunk.strip() for chunk in text.split("\n\n") if len(chunk.strip()) > 50]
    encoded = model.encode(chunks)
    embeddings = encoded.tolist() if hasattr(encoded, "tolist") else encoded

    collection.add(
        documents=chunks,
        embeddings=embeddings,
        ids=[f"chunk_{index}" for index in range(len(chunks))],
    )
    log.info("RAG_SEEDED", extra={"request_id": "none", "chunks": len(chunks)})
    return collection
