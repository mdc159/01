"""
opencode_executor.py — OpenCode execution bridge.

Runs tasks via `opencode run --format json` and parses the JSON event
stream. Supports both vanilla OpenCode and OMO agent orchestration.

This is the bridge between the Python orchestrator (main.py) and the
OpenCode/OMO execution runtime. Python owns the decision loop; OpenCode
owns the execution.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import shutil
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parent.parent


@dataclass
class ExecutionResult:
    """Parsed result from an opencode run --format json session."""
    session_id: str = ""
    success: bool = False
    text_output: str = ""
    tools_used: list[dict] = field(default_factory=list)
    files_changed: list[str] = field(default_factory=list)
    total_tokens: int = 0
    total_cost: float = 0.0
    steps: int = 0
    error: str = ""


def is_available() -> bool:
    """Check if opencode CLI is installed."""
    return shutil.which("opencode") is not None


def run_task(
    prompt: str,
    *,
    agent: str | None = None,
    model: str | None = None,
    timeout: int = 300,
    working_dir: str | None = None,
) -> ExecutionResult:
    """
    Execute a task via opencode run --format json.

    Args:
        prompt:      The task prompt to send.
        agent:       OMO agent name (e.g. "sisyphus", "hephaestus"). None = vanilla.
        model:       Model override (e.g. "openai/gpt-5.3-codex"). None = agent default.
        timeout:     Seconds before killing the process.
        working_dir: Directory to run in. Defaults to project root.

    Returns:
        ExecutionResult with parsed event stream data.
    """
    cmd = ["opencode", "run", "--format", "json"]

    if agent:
        cmd.extend(["--agent", agent])
    if model:
        cmd.extend(["--model", model])

    cmd.append(prompt)

    cwd = working_dir or str(_PROJECT_ROOT)

    logger.info(
        "[OPENCODE] Running: agent=%s model=%s prompt=%s",
        agent or "default", model or "default", prompt[:80],
    )

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
    except subprocess.TimeoutExpired:
        logger.warning("[OPENCODE] Timed out after %ds", timeout)
        return ExecutionResult(error=f"Timeout after {timeout}s")
    except FileNotFoundError:
        logger.error("[OPENCODE] opencode CLI not found")
        return ExecutionResult(error="opencode CLI not found")

    return parse_event_stream(proc.stdout, proc.stderr)


def parse_event_stream(stdout: str, stderr: str = "") -> ExecutionResult:
    """Parse the JSON event stream from opencode run --format json."""
    result = ExecutionResult()
    text_parts = []

    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue

        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue

        evt_type = evt.get("type", "")

        if not result.session_id:
            result.session_id = evt.get("sessionID", "")

        if evt_type == "text":
            text = evt.get("part", {}).get("text", "")
            text_parts.append(text)

        elif evt_type == "tool_use":
            part = evt.get("part", {})
            tool_name = part.get("tool", "")
            state = part.get("state", {})
            status = state.get("status", "")

            tool_record = {
                "tool": tool_name,
                "status": status,
            }

            # Extract file changes from apply_patch / edit tools
            metadata = state.get("metadata", {})
            if tool_name in ("apply_patch", "edit") and status == "completed":
                files = metadata.get("files", [])
                for f in files:
                    path = f.get("relativePath", f.get("filePath", ""))
                    if path and path not in result.files_changed:
                        result.files_changed.append(path)

            result.tools_used.append(tool_record)

        elif evt_type == "step_finish":
            part = evt.get("part", {})
            tokens = part.get("tokens", {})
            result.total_tokens += tokens.get("total", 0)
            result.total_cost += part.get("cost", 0.0)
            result.steps += 1

        elif evt_type == "error":
            err = evt.get("error", {})
            result.error = err.get("data", {}).get("message", str(err))

    result.text_output = "\n".join(text_parts)
    result.success = not result.error and "DONE" in result.text_output

    if stderr and not result.error:
        # Check stderr for non-JSON error output (stack traces, etc.)
        for line in stderr.splitlines():
            if "Error" in line or "error" in line.lower():
                result.error = stderr[:500]
                result.success = False
                break

    logger.info(
        "[OPENCODE] Complete: success=%s steps=%d tokens=%d cost=$%.4f files=%s",
        result.success, result.steps, result.total_tokens,
        result.total_cost, result.files_changed or "none",
    )

    return result


def run_plan(
    plan_path: str | Path,
    *,
    agent: str = "sisyphus",
    model: str | None = None,
    timeout: int = 600,
) -> ExecutionResult:
    """
    Execute a .sisyphus plan via OpenCode.

    Convenience wrapper that constructs the right prompt for plan execution.
    """
    plan_path = Path(plan_path)
    if not plan_path.exists():
        return ExecutionResult(error=f"Plan not found: {plan_path}")

    # Use relative path if under project root
    try:
        rel = plan_path.relative_to(_PROJECT_ROOT)
    except ValueError:
        rel = plan_path

    prompt = (
        f"Read the plan at {rel} and execute all tasks in it. "
        f"Follow the constraints and acceptance criteria exactly. "
        f"When all tasks are complete, say DONE."
    )

    return run_task(prompt, agent=agent, model=model, timeout=timeout)
