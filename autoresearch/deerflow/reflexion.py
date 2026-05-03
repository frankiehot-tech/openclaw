"""DeerFlow v2 — Reflexion self-critique for quality improvement.

Reflexion enables agents to critique their own outputs and improve
through iterative self-reflection.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CritiqueResult:
    score: float
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    passed: bool = False


class ReflexionEngine:
    """Self-critique engine for agent output quality improvement."""

    def __init__(self, pass_threshold: float = 7.0) -> None:
        self.threshold = pass_threshold

    def critique(self, output: str, criteria: list[str] | None = None) -> CritiqueResult:
        criteria = criteria or ["correctness", "completeness", "clarity"]
        issues: list[str] = []
        suggestions: list[str] = []

        if "correctness" in criteria and not self._check_correctness(output):
            issues.append("Logical inconsistencies detected")
            suggestions.append("Verify all claims against source data")

        if "completeness" in criteria and len(output) < 50:
            issues.append("Output too short — may be incomplete")
            suggestions.append("Expand with more detail")

        if "clarity" in criteria and self._has_ambiguity(output):
            issues.append("Ambiguous language detected")
            suggestions.append("Use more specific terms")

        precision_issues = self._count_precision_issues(output)
        score = max(0, 10.0 - len(issues) * 2.0 - precision_issues)
        passed = score >= self.threshold

        return CritiqueResult(
            score=round(score, 1),
            issues=issues,
            suggestions=suggestions,
            passed=passed,
        )

    def refine(self, output: str, critique: CritiqueResult, max_rounds: int = 3) -> str:
        if critique.passed:
            return output

        round_count = 0
        current = output
        while not critique.passed and round_count < max_rounds:
            current = self._apply_suggestions(current, critique.suggestions)
            critique = self.critique(current)
            round_count += 1

        return current

    def _check_correctness(self, output: str) -> bool:
        contradictions = [
            ("always", "never"),
            ("all", "none"),
            ("must", "must not"),
        ]
        return all(not (a in output.lower() and b in output.lower()) for a, b in contradictions)

    def _has_ambiguity(self, output: str) -> bool:
        ambiguous = ["maybe", "perhaps", "possibly", "could be", "might be"]
        lower = output.lower()
        return sum(1 for w in ambiguous if w in lower) >= 2

    def _count_precision_issues(self, output: str) -> float:
        vagueness = ["stuff", "things", "etc", "and so on", "various"]
        lower = output.lower()
        return sum(0.3 for v in vagueness if v in lower)

    def _apply_suggestions(self, output: str, suggestions: list[str]) -> str:
        lines = output.split("\n")
        improved = []
        for s in suggestions:
            improved.append(f"[REFINED: {s}]")
        return "\n".join(improved + lines)
