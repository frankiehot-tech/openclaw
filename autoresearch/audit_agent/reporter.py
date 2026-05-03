"""Audit Agent reporter — generates score reports in multiple formats."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .scorer import AuditScore


def format_report(score: AuditScore) -> str:
    """Generate formatted 5-dimension score report (text)."""
    lines = [
        "=" * 50,
        "Karpathy 智能工作流 - 量化评分报告",
        "=" * 50,
        f"Commit: {score.commit_hash}",
        "",
    ]
    for d in score.dimensions:
        weighted = d.weight * d.score
        lines.append(f"{d.name:　<6}: {d.score:.1f}/10 × {d.weight:.2f} = {weighted:.3f}")
        for detail in d.details:
            lines.append(f"  → {detail}")
    lines.append("-" * 50)
    status_icons = {"PASS": "✅ PASS", "MANUAL": "⚠️ MANUAL", "RETRY": "🔄 RETRY", "REJECT": "❌ REJECT"}
    lines.append(f"综合评分: {score.composite:.3f}/10")
    lines.append(f"状态: {status_icons.get(score.status.value, score.status.value)}")
    if score.warnings:
        lines.append("")
        lines.append("警告:")
        for w in score.warnings:
            lines.append(f"  ⚠ {w}")
    lines.append("=" * 50)
    return "\n".join(lines)


def save_report(score: AuditScore, output_dir: str | Path | None = None, fmt: str = "text") -> str:
    """Save score report to file. Returns the file path."""
    out_dir = Path(output_dir or ".")
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    commit_short = score.commit_hash[:7] if score.commit_hash else "HEAD"

    if fmt == "json":
        path = out_dir / f"audit_{commit_short}_{timestamp}.json"
        data = {
            "commit": score.commit_hash,
            "composite": score.composite,
            "status": score.status.value,
            "dimensions": [
                {"name": d.name, "weight": d.weight, "score": d.score, "details": d.details}
                for d in score.dimensions
            ],
            "warnings": score.warnings,
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        path = out_dir / f"audit_{commit_short}_{timestamp}.md"
        path.write_text(format_report(score))

    return str(path)


def append_to_tsv(score: AuditScore, tsv_path: str | Path = "results.tsv") -> None:
    """Append score to ratchet loop results.tsv."""
    tsv = Path(tsv_path)
    status_char = "keep" if score.status.value == "PASS" else "discard"
    line = f"\n{score.commit_hash[:7]}\t{score.composite:.3f}\t{status_char}\tauto-audit"
    with open(tsv, "a") as f:
        f.write(line)
