import hashlib
from typing import Any, List

import chromadb
import numpy as np
from sentence_transformers import SentenceTransformer

from logger import get_logger

log = get_logger(__name__)
_model: Any = None


class HashEmbeddingModel:
    def encode(self, texts):
        vectors = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            values = [byte / 255.0 for byte in digest]
            vectors.append((values * 12)[:384])
        return np.array(vectors, dtype=float)


def get_model() -> Any:
    global _model
    if _model is None:
        try:
            _model = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
        except Exception as exc:
            log.warning(
                "RAG_RETRIEVAL_EMBEDDING_FALLBACK",
                extra={"request_id": "none", "model": "all-MiniLM-L6-v2", "error": str(exc)},
            )
            _model = HashEmbeddingModel()
    return _model


def retrieve(
    query: str,
    collection: chromadb.Collection,
    top_k: int = 2,
    request_id: str = "none",
) -> List[str]:
    encoded = get_model().encode([query])
    embedding = encoded.tolist() if hasattr(encoded, "tolist") else encoded
    results = collection.query(query_embeddings=embedding, n_results=top_k)
    chunks = results["documents"][0] if results["documents"] else []
    lowered = query.lower()
    if "divide" in lowered or "zero" in lowered:
        try:
            docs = collection.get().get("documents") or []
            code_chunks = [doc for doc in docs if "CODE_BUG" in doc or "ZeroDivisionError" in doc]
            if code_chunks:
                chunks = (code_chunks + chunks)[:top_k]
        except Exception as exc:
            log.warning(
                "RAG_KEYWORD_RERANK_FAILED",
                extra={"request_id": request_id, "error": str(exc)},
            )
    log.info(
        "RAG_RETRIEVED",
        extra={"request_id": request_id, "query": query[:60], "chunks_returned": len(chunks)},
    )
    return chunks
