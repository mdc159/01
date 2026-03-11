"""
tools.py — Tool Layer.

Thin wrappers around local capabilities that workers can call.
These are deterministic — they execute code, run shells, read files, etc.
Add new tools here as the system grows (MATLAB, CAD, search, etc.).
"""

from __future__ import annotations

import subprocess
import logging
from pathlib import Path

from config import Paths

logger = logging.getLogger(__name__)


def run_python(code: str, timeout: int = 30) -> dict:
    """
    Execute a Python snippet in an isolated subprocess.
    Returns {"stdout": ..., "stderr": ..., "returncode": ...}.
    """
    result = subprocess.run(
        ["python3", "-c", code],
        capture_output=True, text=True, timeout=timeout,
    )
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }


def run_shell(command: str, timeout: int = 30) -> dict:
    """Run an arbitrary shell command. Use carefully."""
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, timeout=timeout,
    )
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }


def read_file(path: str | Path) -> str:
    """Read a text file from the artifacts directory or an absolute path."""
    p = Path(path)
    if not p.is_absolute():
        p = Paths.ARTIFACTS / p
    return p.read_text()


def write_file(filename: str, content: str) -> Path:
    """Write content to a file in the artifacts directory."""
    path = Paths.ARTIFACTS / filename
    path.write_text(content)
    logger.info("[TOOL] Wrote %d bytes → %s", len(content), path)
    return path


# ── Tool registry (for the worker to request tools by name) ─────
REGISTRY: dict[str, callable] = {
    "run_python": run_python,
    "run_shell": run_shell,
    "read_file": read_file,
    "write_file": write_file,
}


def dispatch(tool_name: str, **kwargs) -> dict:
    """
    Call a tool by name with keyword arguments.
    Returns a dict with at minimum {"result": ...} or {"error": ...}.
    """
    fn = REGISTRY.get(tool_name)
    if not fn:
        return {"error": f"Unknown tool: {tool_name}. Available: {list(REGISTRY)}"}
    try:
        result = fn(**kwargs)
        return {"result": result}
    except Exception as exc:
        logger.exception("[TOOL] %s raised: %s", tool_name, exc)
        return {"error": str(exc)}
