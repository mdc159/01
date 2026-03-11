"""
llm.py — Thin, unified client wrapper for all LLM calls in the AI Lab.

Key design decisions:
- o1 models require `max_completion_tokens` (not `max_tokens`) and do NOT
  accept `temperature` or `stream` parameters.
- All other models use the standard chat-completions API.
- A single `call()` function handles routing transparently, so callers
  don't need to know which model tier they are hitting.
"""

from __future__ import annotations

import logging
from typing import Any

from openai import OpenAI

from config import OPENAI_API_KEY, Models, O1Settings

logger = logging.getLogger(__name__)

# ── Shared client (reuses the same HTTP connection pool) ─────────
_client = OpenAI(api_key=OPENAI_API_KEY)

# Models in the o1 family need special handling
_O1_FAMILY = {"o1", "o1-mini", "o1-preview", "o1-pro", "o3", "o3-mini"}


def _is_o1(model: str) -> bool:
    """Return True for any model that behaves like o1 (no temp, no stream)."""
    return any(model.startswith(prefix) for prefix in ("o1", "o3"))


def call(
    messages: list[dict[str, str]],
    model: str | None = None,
    max_tokens: int | None = None,
    system_prompt: str | None = None,
    **kwargs: Any,
) -> str:
    """
    Universal LLM call. Returns the assistant's reply as a plain string.

    Args:
        messages:      List of {"role": ..., "content": ...} dicts.
        model:         Override model. Defaults to WORKER tier.
        max_tokens:    Max output tokens. O1 uses max_completion_tokens.
        system_prompt: Convenience arg — prepended as a system message.
                       NOTE: o1 models treat system messages as developer
                       messages automatically; this is handled for you.
        **kwargs:      Passed through for non-o1 models only.

    Returns:
        The model's reply as a stripped string.
    """
    model = model or Models.WORKER

    # Prepend system/developer message if provided
    if system_prompt:
        messages = [{"role": "system", "content": system_prompt}] + messages

    if _is_o1(model):
        return _call_o1(messages, model, max_tokens)
    else:
        return _call_standard(messages, model, max_tokens, **kwargs)


def _call_o1(
    messages: list[dict[str, str]],
    model: str,
    max_tokens: int | None,
) -> str:
    """Call an o1-family model with its specific API constraints."""
    params: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_completion_tokens": max_tokens or O1Settings.MAX_COMPLETION_TOKENS,
    }

    # reasoning_effort supported on o1 (2025-04+) and o3
    if model in {"o1", "o1-pro", "o3"}:
        params["reasoning_effort"] = O1Settings.REASONING_EFFORT

    logger.info(
        "→ [STRATEGIC] %s | effort=%s | max_completion_tokens=%s",
        model,
        params.get("reasoning_effort", "n/a"),
        params["max_completion_tokens"],
    )

    response = _client.chat.completions.create(**params)
    return response.choices[0].message.content.strip()


def _call_standard(
    messages: list[dict[str, str]],
    model: str,
    max_tokens: int | None,
    **kwargs: Any,
) -> str:
    """Call a standard chat-completions model (gpt-4o, etc.)."""
    params: dict[str, Any] = {
        "model": model,
        "messages": messages,
        **kwargs,
    }
    if max_tokens:
        params["max_tokens"] = max_tokens

    logger.info("→ [LLM] %s", model)
    response = _client.chat.completions.create(**params)
    return response.choices[0].message.content.strip()


# ── Convenience aliases matching the three-tier architecture ─────

def strategic(messages: list[dict[str, str]], **kwargs: Any) -> str:
    """Call the STRATEGIC model (o1). Use for planning and diagnosis."""
    return call(messages, model=Models.STRATEGIC, **kwargs)


def project(messages: list[dict[str, str]], **kwargs: Any) -> str:
    """Call the PROJECT model (gpt-4o). Use for evaluation and routing."""
    return call(messages, model=Models.PROJECT, **kwargs)


def worker(messages: list[dict[str, str]], **kwargs: Any) -> str:
    """Call the WORKER model (gpt-4o-mini). Use for execution tasks."""
    return call(messages, model=Models.WORKER, **kwargs)
