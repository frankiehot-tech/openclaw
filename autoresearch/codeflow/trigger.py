"""CodeFlow trigger — launches agent pipelines for scanned tasks.

Handles the bridge between directory scanning and agent execution.
Supports Claude Code and OpenCode as agent targets.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from enum import Enum


class AgentType(Enum):
    CLAUDE_CODE = "claude_code"
    OPENCODE = "opencode"


@dataclass
class TriggerConfig:
    agent: AgentType = AgentType.CLAUDE_CODE
    timeout_seconds: int = 600
    dry_run: bool = False
    max_concurrent: int = 1


@dataclass
class TriggerResult:
    success: bool
    agent: AgentType
    command: str
    output: str
    exit_code: int
    error: str = ""


def trigger_claude_code(issue: str, cwd: str | None = None, timeout: int = 600) -> TriggerResult:
    """Trigger Claude Code with an issue prompt.

    Uses the `claude` CLI to issue a task to Claude Code.
    """
    cmd = ["claude", issue]
    return _run_command(cmd, AgentType.CLAUDE_CODE, cwd, timeout)


def trigger_opencode(issue: str, cwd: str | None = None, timeout: int = 600) -> TriggerResult:
    """Trigger OpenCode with an issue prompt."""
    cmd = ["opencode", "run", issue]
    return _run_command(cmd, AgentType.OPENCODE, cwd, timeout)


def trigger_agent(
    issue: str,
    agent: AgentType = AgentType.CLAUDE_CODE,
    cwd: str | None = None,
    timeout: int = 600,
    dry_run: bool = False,
) -> TriggerResult:
    cmd_str = " ".join(["claude", issue] if agent == AgentType.CLAUDE_CODE else ["opencode", "run", issue])
    if dry_run:
        return TriggerResult(
            success=True,
            agent=agent,
            command=cmd_str,
            output="[DRY RUN] Would execute: " + cmd_str,
            exit_code=0,
        )
    if agent == AgentType.CLAUDE_CODE:
        return trigger_claude_code(issue, cwd, timeout)
    return trigger_opencode(issue, cwd, timeout)


def _run_command(cmd: list[str], agent: AgentType, cwd: str | None, timeout: int) -> TriggerResult:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        return TriggerResult(
            success=proc.returncode == 0,
            agent=agent,
            command=" ".join(cmd),
            output=proc.stdout[-2000:] if proc.stdout else "",
            exit_code=proc.returncode,
            error=proc.stderr[-500:] if proc.stderr else "",
        )
    except subprocess.TimeoutExpired:
        return TriggerResult(
            success=False,
            agent=agent,
            command=" ".join(cmd),
            output="",
            exit_code=-1,
            error=f"Command timed out after {timeout}s",
        )
    except FileNotFoundError:
        return TriggerResult(
            success=False,
            agent=agent,
            command=" ".join(cmd),
            output="",
            exit_code=-1,
            error=f"Agent binary not found: {cmd[0]}",
        )
