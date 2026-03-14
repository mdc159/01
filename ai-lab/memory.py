"""
memory.py — Persistent memory beyond the active state object.

Implements the lower layers of the 5-layer memory hierarchy:
  - Semantic Memory ("SSD"): skill heuristics learned from past experiments
  - Artifact Memory ("Hard Drive"): references to files in ARTIFACTS dir

Skills are stored as a JSON list in skills.json. Embeddings are cached
in skills_embeddings.json for vector similarity retrieval via Ollama.
"""

from __future__ import annotations

import json
import logging
import math
import urllib.request
from pathlib import Path
from typing import Any

from config import Paths, Models

logger = logging.getLogger(__name__)

Paths.ensure_dirs()

EMBED_MODEL = "nomic-embed-text"


# ════════════════════════════════════════════════════════════════
#  Embedding (via Ollama — local, free, no new deps)
# ════════════════════════════════════════════════════════════════

_EMBEDDINGS_PATH = Paths.ROOT / "skills_embeddings.json"


def _ollama_embed(texts: list[str]) -> list[list[float]]:
    """Call Ollama's /api/embed endpoint for batch embedding."""
    base_url = Models.OLLAMA_BASE_URL or "http://localhost:11434"
    url = f"{base_url}/api/embed"
    payload = json.dumps({"model": EMBED_MODEL, "input": texts}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data["embeddings"]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors. Pure Python, no deps."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _load_embedding_cache() -> dict[str, list[float]]:
    """Load cached embeddings keyed by skill description."""
    if not _EMBEDDINGS_PATH.exists():
        return {}
    return json.loads(_EMBEDDINGS_PATH.read_text())


def _save_embedding_cache(cache: dict[str, list[float]]) -> None:
    _EMBEDDINGS_PATH.write_text(json.dumps(cache))


def _ensure_embeddings(skills: list[dict[str, Any]]) -> dict[str, list[float]]:
    """Ensure all skills have cached embeddings. Embed missing ones in batch."""
    cache = _load_embedding_cache()
    missing = []
    for s in skills:
        text = s["description"]
        if text not in cache:
            missing.append(text)

    if missing:
        logger.info("[MEMORY] Embedding %d new skill(s) via %s", len(missing), EMBED_MODEL)
        embeddings = _ollama_embed(missing)
        for text, emb in zip(missing, embeddings):
            cache[text] = emb
        _save_embedding_cache(cache)

    return cache


# ════════════════════════════════════════════════════════════════
#  Skills DB (Semantic Memory)
# ════════════════════════════════════════════════════════════════

def load_skills() -> list[dict[str, Any]]:
    """Load all learned heuristics from the skills DB."""
    if not Paths.SKILLS_DB.exists():
        return []
    return json.loads(Paths.SKILLS_DB.read_text())


def save_skill(description: str, context: str = "", tags: list[str] | None = None) -> None:
    """
    Persist a learned heuristic so future loops can benefit from it.

    Example:
        save_skill(
            description="Using flexure joints reduces hinge stress by 30%.",
            context="prosthetic limb ankle joint design",
            tags=["mechanical", "joint", "stress"],
        )
    """
    skills = load_skills()
    skills.append({
        "description": description,
        "context": context,
        "tags": tags or [],
    })
    Paths.SKILLS_DB.write_text(json.dumps(skills, indent=2))
    logger.info("[MEMORY] Skill saved: %s", description[:80])


def process_memory_actions(actions: list[dict[str, Any]]) -> None:
    """
    Process memory_actions from a v2 strategic response.

    Each action: {"layer": "semantic|artifact|episodic", "action": "write|update|delete", "key": str, "value": str}
    Currently supports semantic layer (skills DB). Artifact and episodic are logged but not yet wired.
    """
    for act in actions:
        layer = act.get("layer", "")
        action = act.get("action", "")
        key = act.get("key", "")
        value = act.get("value", "")

        if layer == "semantic" and action in ("write", "update"):
            save_skill(description=value, context=key, tags=[key])
            logger.info("[MEMORY] Strategic memory action: %s → %s: %s", action, key, value[:80])
        elif layer == "semantic" and action == "delete":
            _delete_skill_by_key(key)
        else:
            logger.info("[MEMORY] Skipped memory action (layer=%s, action=%s, key=%s)", layer, action, key)


def _delete_skill_by_key(key: str) -> None:
    """Remove skills matching a key from the skills DB."""
    skills = load_skills()
    before = len(skills)
    skills = [s for s in skills if s.get("context") != key and key not in s.get("tags", [])]
    Paths.SKILLS_DB.write_text(json.dumps(skills, indent=2))
    removed = before - len(skills)
    if removed:
        logger.info("[MEMORY] Deleted %d skill(s) matching key: %s", removed, key)


def retrieve_skills(query: str | None = None, query_tags: list[str] | None = None, top_k: int = 10) -> list[str]:
    """
    Retrieve the most relevant skills as plain strings for prompt injection.

    Uses vector similarity when a query string is provided and Ollama is available.
    Falls back to tag-based retrieval if Ollama is unreachable or no query given.
    """
    skills = load_skills()
    if not skills:
        return []

    # Vector search path
    if query:
        try:
            cache = _ensure_embeddings(skills)
            query_emb = _ollama_embed([query])[0]
            scored = []
            for s in skills:
                emb = cache.get(s["description"])
                if emb:
                    sim = _cosine_similarity(query_emb, emb)
                    scored.append((sim, s["description"]))
            scored.sort(reverse=True)
            return [desc for _, desc in scored[:top_k]]
        except Exception as e:
            logger.warning("[MEMORY] Vector search failed, falling back to tags: %s", e)

    # Tag-based fallback
    if query_tags:
        scored = []
        for s in skills:
            overlap = len(set(s.get("tags", [])) & set(query_tags))
            if overlap > 0:
                scored.append((overlap, s["description"]))
        scored.sort(reverse=True)
        return [desc for _, desc in scored[:top_k]]

    # No filter → return most recent
    return [s["description"] for s in skills[-top_k:]]


def search(query: str, top_k: int = 8) -> list[dict[str, Any]]:
    """
    Search interface compatible with the eval harness LocalSearchBackend protocol.

    Returns list of dicts with: doc_id, chunk_id, text, score, metadata.
    """
    skills = load_skills()
    if not skills or not query:
        return []

    try:
        cache = _ensure_embeddings(skills)
        query_emb = _ollama_embed([query])[0]
    except Exception as e:
        logger.warning("[MEMORY] Vector search unavailable: %s", e)
        return []

    scored: list[tuple[float, dict[str, Any]]] = []
    for i, s in enumerate(skills):
        emb = cache.get(s["description"])
        if emb:
            sim = _cosine_similarity(query_emb, emb)
            scored.append((sim, {
                "doc_id": f"skill:{i}",
                "chunk_id": f"skill-{i}",
                "text": f"{s['description']} (context: {s.get('context', '')})",
                "score": sim,
                "metadata": {"tags": s.get("tags", []), "context": s.get("context", "")},
            }))

    scored.sort(reverse=True, key=lambda x: x[0])
    return [item for _, item in scored[:top_k]]


# ════════════════════════════════════════════════════════════════
#  Artifact Registry (Artifact Memory)
# ════════════════════════════════════════════════════════════════

def save_artifact(name: str, content: str | bytes, binary: bool = False) -> Path:
    """Write an artifact to the artifacts directory and return its path."""
    path = Paths.ARTIFACTS / name
    if binary:
        assert isinstance(content, bytes)
        path.write_bytes(content)
    else:
        assert isinstance(content, str)
        path.write_text(content)
    logger.info("[MEMORY] Artifact saved: %s (%d bytes)", name, path.stat().st_size)
    return path


def list_artifacts() -> list[Path]:
    """Return a list of all artifact paths."""
    return sorted(Paths.ARTIFACTS.iterdir()) if Paths.ARTIFACTS.exists() else []
