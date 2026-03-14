"""Local retrieval backend using Ollama embeddings over repo documents."""

from __future__ import annotations

import json
import logging
import math
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

EMBED_MODEL = "nomic-embed-text"
OLLAMA_URL = "http://localhost:11434"
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
CACHE_PATH = HERE / "results" / "doc_embeddings.json"

# Chunk repo docs into segments of roughly this many characters
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200

# Files to index for retrieval
DOC_PATTERNS = [
    "CANON.md",
    "README.md",
    "CLAUDE.md",
    "ai-lab/o1_system_prompt.md",
    "ai-lab/o1_next_question_mvp.md",
    "docs/lab/architecture.md",
]


def _ollama_embed(texts: list[str]) -> list[list[float]]:
    """Batch embed via Ollama."""
    payload = json.dumps({"model": EMBED_MODEL, "input": texts}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/embed",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    return data["embeddings"]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _chunk_text(text: str, doc_id: str) -> list[dict[str, str]]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    idx = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk_text = text[start:end]
        chunks.append(
            {
                "doc_id": doc_id,
                "chunk_id": f"{doc_id}::chunk-{idx}",
                "text": chunk_text,
            }
        )
        start = end - CHUNK_OVERLAP
        idx += 1
    return chunks


def _build_corpus() -> list[dict[str, str]]:
    """Read and chunk all repo docs."""
    chunks = []
    for pattern in DOC_PATTERNS:
        path = REPO_ROOT / pattern
        if not path.exists():
            logger.warning("[LOCAL] Doc not found: %s", path)
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        doc_id = pattern
        chunks.extend(_chunk_text(text, doc_id))
    logger.info(
        "[LOCAL] Built corpus: %d chunks from %d doc patterns",
        len(chunks),
        len(DOC_PATTERNS),
    )
    return chunks


def _load_cache() -> dict[str, Any] | None:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text())
    return None


def _save_cache(data: dict[str, Any]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(data))


class RepoSearchBackend:
    """
    LocalSearchBackend for the eval harness runner.

    Embeds repo documents via Ollama's nomic-embed-text, caches embeddings,
    and returns cosine-similarity-ranked chunks.

    Usage with runner.py:
        --local-backend evals.knowledge_plane.local_backend:RepoSearchBackend
    """

    def __init__(self) -> None:
        self._chunks: list[dict[str, str]] = []
        self._embeddings: list[list[float]] = []
        self._load_or_build()

    def _load_or_build(self) -> None:
        cache = _load_cache()
        if cache:
            self._chunks = cache["chunks"]
            self._embeddings = cache["embeddings"]
            logger.info("[LOCAL] Loaded %d cached chunk embeddings", len(self._chunks))
            return

        self._chunks = _build_corpus()
        texts = [c["text"] for c in self._chunks]

        # Embed in batches of 32 to avoid timeout
        batch_size = 32
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            embs = _ollama_embed(batch)
            all_embeddings.extend(embs)
            logger.info(
                "[LOCAL] Embedded batch %d-%d / %d", i, i + len(batch), len(texts)
            )

        self._embeddings = all_embeddings
        _save_cache({"chunks": self._chunks, "embeddings": self._embeddings})
        logger.info(
            "[LOCAL] Cached %d chunk embeddings to %s", len(self._chunks), CACHE_PATH
        )

    def search(self, query: str, top_k: int = 8) -> list[dict[str, Any]]:
        query_emb = _ollama_embed([query])[0]

        scored: list[tuple[float, dict[str, Any]]] = []
        for chunk, emb in zip(self._chunks, self._embeddings):
            sim = _cosine_similarity(query_emb, emb)
            scored.append(
                (
                    sim,
                    {
                        "doc_id": chunk["doc_id"],
                        "chunk_id": chunk["chunk_id"],
                        "text": chunk["text"],
                        "score": sim,
                        "metadata": {},
                    },
                )
            )

        best_by_doc: dict[str, tuple[float, dict[str, Any]]] = {}
        for score, item in scored:
            doc_id = str(item["doc_id"])
            current_best = best_by_doc.get(doc_id)
            if current_best is None or score > current_best[0]:
                best_by_doc[doc_id] = (score, item)

        deduped = list(best_by_doc.values())
        deduped.sort(reverse=True, key=lambda x: x[0])
        return [item for _, item in deduped[:top_k]]
