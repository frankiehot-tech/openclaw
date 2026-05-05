"""Karpathy 5-dimension auto-scorer.

独立审计 Agent 的核心评分引擎。输入 git diff + ruff 结果，输出量化评分。

评分维度: 正确性(35%) + 测试(25%) + 代码质量(20%) + 安全(10%) + 性能(10%)
阈值: ≥9.0 自动合并, 8.0-8.9 人工确认, 6.0-7.9 重生成, <6.0 丢弃
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from enum import Enum

SCRIPT_VERSION = "0.2.0"


class ScoreStatus(Enum):
    PASS = "PASS"
    RETRY = "RETRY"
    REJECT = "REJECT"
    MANUAL = "MANUAL"


@dataclass
class DimensionScore:
    name: str
    weight: float
    score: float
    details: list[str] = field(default_factory=list)


@dataclass
class AuditScore:
    commit_hash: str = ""
    dimensions: list[DimensionScore] = field(default_factory=list)
    composite: float = 0.0
    status: ScoreStatus = ScoreStatus.REJECT
    summary: str = ""
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.status == ScoreStatus.PASS


class KarpathyScorer:
    """5-dimension code quality scorer based on Karpathy AutoResearch methodology."""

    def __init__(
        self,
        base_path: str | None = None,
    ) -> None:
        self.base_path = base_path or "."

    def score_commit(self, commit_hash: str | None = None) -> AuditScore:
        commit = commit_hash or "HEAD"
        diff = self._get_diff(commit)
        ruff_issues = self._get_ruff_issues()
        return self._calculate_score(commit, diff, ruff_issues)

    def score_diff(self, diff_text: str, extra_context: str = "") -> AuditScore:
        ruff_issues = self._get_ruff_issues()
        return self._calculate_score("HEAD", diff_text, ruff_issues)

    def _calculate_score(self, commit: str, diff_text: str, ruff_issues: str) -> AuditScore:
        dimensions: list[DimensionScore] = []

        # 1. Correctness (35%)
        correctness = self._score_correctness(diff_text)
        dimensions.append(correctness)

        # 2. Testing (25%)
        testing = self._score_testing(diff_text)
        dimensions.append(testing)

        # 3. Code quality (20%)
        quality = self._score_code_quality(diff_text, ruff_issues)
        dimensions.append(quality)

        # 4. Security (10%)
        security = self._score_security(diff_text)
        dimensions.append(security)

        # 5. Performance (10%)
        performance = self._score_performance(diff_text)
        dimensions.append(performance)

        composite = sum(d.weight * d.score for d in dimensions)

        return AuditScore(
            commit_hash=commit,
            dimensions=dimensions,
            composite=round(composite, 3),
            status=self._determine_status(composite, security.score),
            summary=f"Composite: {composite:.2f}/10",
            warnings=self._extract_warnings(diff_text),
        )

    def _score_correctness(self, diff: str) -> DimensionScore:
        score = 10.0
        details: list[str] = []
        added = self._added_lines(diff)
        if not added:
            return DimensionScore(name="正确性", weight=0.35, score=score, details=["无代码变更"])
        # Check for potential logic errors
        if re.search(r"def \w+\([^)]*\):\s*pass", diff):
            score -= 3
            details.append("空函数体 (-3)")
        if re.search(r"TODO|FIXME|HACK", diff):
            score -= 1
            details.append("未完成标记 (-1)")
        return DimensionScore(name="正确性", weight=0.35, score=max(0, score), details=details)

    def _score_testing(self, diff: str) -> DimensionScore:
        score = 7.0
        details: list[str] = []
        added = self._added_lines(diff)
        has_test_import = bool(re.search(r"import (pytest|unittest)", diff))
        has_test_func = bool(re.search(r"def test_", diff))
        has_test_file = bool(re.search(r"tests?/test_", diff))

        if has_test_func and has_test_import:
            score = 10
            details.append("包含测试用例 (+3)")
        elif has_test_file:
            score = 9
            details.append("修改测试文件 (+2)")
        elif not added:
            score = 8
            details.append("无新增代码 (基线+1)")
        return DimensionScore(name="测试", weight=0.25, score=score, details=details)

    def _score_code_quality(self, diff: str, ruff_issues: str) -> DimensionScore:
        score = 10.0
        details: list[str] = []
        added = self._added_lines(diff)
        removed = self._removed_lines(diff)
        net = len(added) - len(removed)

        if net < -5:
            score = 10
            details.append(f"净删除 {-net} 行 (简化胜利)")
        elif net < 0:
            score = 10
            details.append(f"净减少 {-net} 行")
        elif net > 50:
            score -= 2
            details.append(f"新增 {net} 行 (>50行，审查建议) (-2)")
        elif net > 20:
            score -= 0.5
            details.append(f"新增 {net} 行 (-0.5)")

        ruff_count = len([line for line in ruff_issues.split("\n") if line.strip() and "Found" not in line])
        if ruff_count > 0:
            score -= min(2, ruff_count * 0.3)
            details.append(f"ruff 残留 {ruff_count} 项 (-{min(2, ruff_count * 0.3):.1f})")

        return DimensionScore(name="代码质量", weight=0.20, score=max(0, score), details=details)

    def _score_security(self, diff: str) -> DimensionScore:
        score = 10.0
        details: list[str] = []
        veto_patterns = [
            (r"(?i)(api_key|secret|password|token)\s*=\s*['\"][^'\"]{8,}['\"]", "硬编码凭据"),
            (r"subprocess\.(call|Popen|run)\([^)]*shell\s*=\s*True", "shell=True 注入风险"),
            (r"(?i)exec\s*\(|eval\s*\(", "动态代码执行"),
            (r"import\s+pickle", "pickle 反序列化风险"),
        ]
        for pattern, desc in veto_patterns:
            if re.search(pattern, diff):
                score = 0
                details.append(f"{desc} (一票否决)")
                break
        return DimensionScore(name="安全", weight=0.10, score=score, details=details or ["无明显安全问题"])

    def _score_performance(self, diff: str) -> DimensionScore:
        score = 10.0
        details: list[str] = []
        if re.search(r"O\(n\^2\)|O\(n\^3\)", diff):
            score -= 3
            details.append("高复杂度算法 (-3)")
        if re.search(r"time\.sleep\([2-9]\d*\)|time\.sleep\(\d{2,}\)", diff):
            score -= 1
            details.append("长时间阻塞 sleep (-1)")
        return DimensionScore(name="性能", weight=0.10, score=max(0, score), details=details or ["无明显性能问题"])

    def _get_diff(self, commit: str) -> str:
        try:
            proc = subprocess.run(
                ["git", "diff", f"{commit}~1", commit],
                capture_output=True, text=True, cwd=self.base_path, timeout=10,
            )
            return proc.stdout if proc.returncode == 0 else ""
        except Exception:
            return ""

    def _get_ruff_issues(self) -> str:
        try:
            proc = subprocess.run(
                ["ruff", "check"],
                capture_output=True, text=True, cwd=self.base_path, timeout=30,
            )
            return proc.stdout if proc.returncode == 0 else proc.stdout
        except Exception:
            return ""

    def _added_lines(self, diff: str) -> list[str]:
        return [line for line in diff.split("\n") if line.startswith("+") and not line.startswith("+++")]

    def _removed_lines(self, diff: str) -> list[str]:
        return [line for line in diff.split("\n") if line.startswith("-") and not line.startswith("---")]

    def _determine_status(self, composite: float, security_score: float) -> ScoreStatus:
        if security_score == 0:
            return ScoreStatus.REJECT
        if composite >= 9.0:
            return ScoreStatus.PASS
        if composite >= 8.0:
            return ScoreStatus.MANUAL
        if composite >= 6.0:
            return ScoreStatus.RETRY
        return ScoreStatus.REJECT

    def _extract_warnings(self, diff: str) -> list[str]:
        warnings: list[str] = []
        if re.search(r"# (TODO|FIXME|HACK)", diff):
            warnings.append("Contains TODO/FIXME comments")
        return warnings
