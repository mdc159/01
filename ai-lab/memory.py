"""
memory.py — Persistent memory beyond the active state object.

Implements the lower layers of the 5-layer memory hierarchy:
  - Semantic Memory ("SSD"): skill heuristics learned from past experiments
  - Artifact Memory ("Hard Drive"): references to files in ARTIFACTS dir

Skills are stored as a JSON list in skills.json and injected into new
worker contexts to prevent re-learning known solutions.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from config import Paths

logger = logging.getLogger(__name__)

Paths.ensure_dirs()


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


def retrieve_skills(query_tags: list[str] | None = None, top_k: int = 10) -> list[str]:
    """
    Retrieve the most relevant skills as plain strings for prompt injection.
    Simple tag-based retrieval (swap for vector search when scaling up).
    """
    skills = load_skills()
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
