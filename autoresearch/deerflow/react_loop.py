"""DeerFlow v2 — ReAct micro-loop for agent execution.

Reason → Act → Observe cycle for individual task execution.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ReActStep:
    step_id: int
    thought: str
    action: str
    observation: str
    timestamp: float = field(default_factory=time.time)
    success: bool = True
    tokens_used: int = 0


@dataclass
class ReActResult:
    success: bool
    steps: list[ReActStep] = field(default_factory=list)
    final_answer: str = ""
    total_tokens: int = 0
    total_time: float = 0.0
    errors: list[str] = field(default_factory=list)


class ReActLoop:
    """ReAct (Reasoning + Acting) micro-loop executor."""

    def __init__(self, max_steps: int = 10, token_budget: int = 50000) -> None:
        self.max_steps = max_steps
        self.token_budget = token_budget

    def execute(
        self,
        task: str,
        tools: dict[str, callable] | None = None,
        reasoning_fn: callable | None = None,
    ) -> ReActResult:
        start = time.time()
        steps: list[ReActStep] = []
        total_tokens = 0
        errors: list[str] = []
        tools = tools or {}

        for i in range(self.max_steps):
            if total_tokens >= self.token_budget:
                errors.append("Token budget exceeded")
                break

            step_id = i + 1
            thought = f"[Step {step_id}] Analyzing task: {task}" if i == 0 else f"[Step {step_id}] Processing observation..."

            action = self._choose_action(i, steps, tools)
            observation = self._execute_action(action, tools)
            success = "error" not in observation.lower()

            step = ReActStep(
                step_id=step_id,
                thought=thought,
                action=action,
                observation=observation,
                success=success,
                tokens_used=len(thought) + len(observation),
            )
            steps.append(step)
            total_tokens += step.tokens_used

            if self._is_terminal(observation, tools.keys()):
                break

        return ReActResult(
            success=all(s.success for s in steps),
            steps=steps,
            final_answer=steps[-1].observation if steps else "No steps executed",
            total_tokens=total_tokens,
            total_time=round(time.time() - start, 3),
            errors=errors,
        )

    def _choose_action(self, step_idx: int, history: list[ReActStep], tools: dict) -> str:
        if step_idx == 0:
            return "analyze"
        if history and not history[-1].success:
            return "retry"
        if tools:
            return next(iter(tools.keys()), "complete")
        return "complete"

    def _execute_action(self, action: str, tools: dict[str, callable]) -> str:
        if action in tools:
            try:
                return str(tools[action]())
            except Exception as e:
                return f"Action '{action}' failed: {e}"
        return f"Action '{action}' completed successfully"

    def _is_terminal(self, observation: str, tool_names: set) -> bool:
        return "complete" in observation.lower() or "finished" in observation.lower()
