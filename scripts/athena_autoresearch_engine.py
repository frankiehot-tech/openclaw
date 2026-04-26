#!/usr/bin/env python3
"""Minimal Athena AutoResearch engine skeleton.

Implements the five-stage optimization loop:
collect -> analyze -> propose -> gate -> emit

This is a dry-run prototype that does not modify production systems.
All optimization suggestions must pass constraint gates before being emitted.

Key safety constraints:
- Only analyze files under /Volumes/1TB-M2/openclaw/
- Never modify .openclaw/ config files directly
- High-risk recommendations require manual confirmation
- All outputs are structured JSON with confidence scores
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

load_dotenv()

# Import shared root paths
try:
    from .openclaw_roots import PLAN_CONFIG_PATH, RUNTIME_ROOT
except ImportError:
    # fallback for direct script execution
    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from openclaw_roots import PLAN_CONFIG_PATH, RUNTIME_ROOT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================================
# Structured Result Contract
# ============================================================================


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class Finding:
    """A specific observation about the system."""

    id: str
    title: str
    description: str
    location: str  # file:line or component name
    evidence: List[str]  # supporting data points
    timestamp: str


@dataclass
class Recommendation:
    """A proposed optimization action."""

    id: str
    title: str
    description: str
    action_type: str  # "config_change", "code_refactor", "process_improvement", etc.
    target: str  # what to modify
    expected_benefit: str
    risk_level: RiskLevel
    confidence: float  # 0.0 to 1.0
    dependencies: List[str]  # other recommendation IDs that must be applied first
    requires_manual_confirmation: bool


@dataclass
class ResearchResult:
    """Complete output of an AutoResearch cycle."""

    cycle_id: str
    timestamp: str
    findings: List[Finding]
    recommendations: List[Recommendation]
    summary: str
    metadata: Dict[str, Any]


# ============================================================================
# Constraint Framework
# ============================================================================


class ConstraintViolation(Exception):
    """Raised when an optimization proposal violates constraints."""

    pass


class ConstraintGate:
    """Validates optimization proposals against safety constraints."""

    # Allowed optimization targets (paths relative to RUNTIME_ROOT)
    ALLOWED_TARGETS = [
        "scripts/",
        "workspace/",
        "candidates/",
        "mini-agent/",
    ]

    # Forbidden targets (never modify directly)
    FORBIDDEN_TARGETS = [
        ".openclaw/",
        ".git/",
        ".venv*",
        "vendor/",
    ]

    # High-risk action types that require manual confirmation
    HIGH_RISK_ACTIONS = [
        "delete_file",
        "modify_core_config",
        "change_auth",
        "external_api_call",
    ]

    @classmethod
    def validate_target(cls, target_path: str) -> bool:
        """Check if a target is allowed for optimization."""
        abs_target = os.path.abspath(target_path)
        abs_runtime = os.path.abspath(RUNTIME_ROOT)

        # Must be within runtime root
        if not abs_target.startswith(abs_runtime + os.sep):
            raise ConstraintViolation(f"Target outside runtime root: {target_path}")

        # Check against forbidden targets
        for forbidden in cls.FORBIDDEN_TARGETS:
            if forbidden.rstrip("/") in target_path:
                raise ConstraintViolation(
                    f"Target in forbidden area: {target_path} matches {forbidden}"
                )

        # Check if in allowed targets
        target_relative = os.path.relpath(abs_target, abs_runtime)
        for allowed in cls.ALLOWED_TARGETS:
            if target_relative.startswith(allowed):
                return True

        # Special case: root-level files with specific extensions
        if "/" not in target_relative and target_relative.endswith((".md", ".py", ".json")):
            return True

        raise ConstraintViolation(f"Target not in allowed areas: {target_path}")

    @classmethod
    def validate_recommendation(cls, recommendation: Recommendation) -> Tuple[bool, List[str]]:
        """Validate a recommendation against all constraints."""
        warnings = []

        try:
            # Validate target
            cls.validate_target(recommendation.target)
        except ConstraintViolation as e:
            return False, [str(e)]

        # Check for high-risk actions
        if recommendation.action_type in cls.HIGH_RISK_ACTIONS:
            if not recommendation.requires_manual_confirmation:
                warnings.append(
                    f"High-risk action {recommendation.action_type} must require manual confirmation"
                )
                recommendation.requires_manual_confirmation = True

        # Confidence threshold for auto-approval
        if recommendation.confidence < 0.7 and recommendation.risk_level != RiskLevel.LOW:
            recommendation.requires_manual_confirmation = True
            warnings.append(f"Low confidence ({recommendation.confidence}) for non-low risk action")

        return True, warnings


# ============================================================================
# Five-Stage Engine
# ============================================================================


class AutoResearchEngine:
    """Core AutoResearch engine implementing the five-stage loop."""

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.cycle_id = f"ares-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.findings: List[Finding] = []
        self.recommendations: List[Recommendation] = []
        self.constraint_gate = ConstraintGate()

    # ------------------------------------------------------------------------
    # Stage 1: Collect
    # ------------------------------------------------------------------------

    def collect(self) -> Dict[str, Any]:
        """Collect system state and performance data."""
        logger.info(f"[{self.cycle_id}] Collecting system data...")

        data = {
            "timestamp": datetime.now().isoformat(),
            "system": self._collect_system_metrics(),
            "workflow": self._collect_workflow_metrics(),
            "codebase": self._collect_codebase_metrics(),
        }

        # Create findings from collected data
        self._create_findings_from_data(data)

        return data

    def _collect_system_metrics(self) -> Dict[str, Any]:
        """Collect basic system resource metrics."""
        # In a real implementation, this would collect CPU, memory, disk, etc.
        # For the prototype, return simulated data
        return {
            "python_version": sys.version,
            "platform": sys.platform,
            "cwd": os.getcwd(),
            "runtime_root": str(RUNTIME_ROOT),
        }

    def _collect_workflow_metrics(self) -> Dict[str, Any]:
        """Collect workflow execution metrics."""
        metrics = {
            "tasks": self._analyze_task_history(),
            "queues": self._analyze_queue_state(),
        }
        return metrics

    def _collect_codebase_metrics(self) -> Dict[str, Any]:
        """Collect codebase health metrics."""
        # Simple metrics for prototype
        scripts_dir = Path(RUNTIME_ROOT) / "scripts"
        workspace_dir = Path(RUNTIME_ROOT) / "workspace"

        metrics = {
            "scripts_count": len(list(scripts_dir.glob("*.py"))) if scripts_dir.exists() else 0,
            "workspace_files": len(list(workspace_dir.rglob("*"))) if workspace_dir.exists() else 0,
            "recent_changes": self._detect_recent_changes(),
        }
        return metrics

    def _analyze_task_history(self) -> Dict[str, Any]:
        """Analyze recent task execution history."""
        tasks_path = Path(RUNTIME_ROOT) / ".openclaw" / "orchestrator" / "tasks.json"
        if not tasks_path.exists():
            return {"error": "tasks.json not found", "count": 0}

        try:
            with open(tasks_path) as f:
                tasks_data = json.load(f)

            tasks = tasks_data.get("tasks", [])
            completed = [t for t in tasks if t.get("status") == "completed"]
            failed = [t for t in tasks if t.get("status") == "failed"]
            running = [t for t in tasks if t.get("status") == "running"]

            return {
                "total": len(tasks),
                "completed": len(completed),
                "failed": len(failed),
                "running": len(running),
                "success_rate": len(completed) / len(tasks) if tasks else 0,
            }
        except Exception as e:
            return {"error": str(e), "count": 0}

    def _analyze_queue_state(self) -> Dict[str, Any]:
        """Analyze queue state for bottlenecks."""
        # Simplified for prototype
        return {
            "queues": ["build", "review", "plan"],
            "pending_count": 0,  # Would be calculated from actual queue data
        }

    def _detect_recent_changes(self) -> List[str]:
        """Detect recently modified files."""
        # Simplified: check for recent .py files in scripts
        scripts_dir = Path(RUNTIME_ROOT) / "scripts"
        if not scripts_dir.exists():
            return []

        recent = []
        for py_file in scripts_dir.glob("*.py"):
            stat = py_file.stat()
            # If modified in last 24 hours
            if time.time() - stat.st_mtime < 86400:
                recent.append(str(py_file.relative_to(RUNTIME_ROOT)))

        return recent[:10]  # Limit to 10 most recent

    def _create_findings_from_data(self, data: Dict[str, Any]) -> None:
        """Create findings from collected data."""
        # Example finding: low success rate
        workflow = data.get("workflow", {})
        tasks = workflow.get("tasks", {})

        if tasks.get("total", 0) > 10 and tasks.get("success_rate", 1.0) < 0.8:
            self.findings.append(
                Finding(
                    id=f"finding-{len(self.findings) + 1}",
                    title="Suboptimal task success rate",
                    description=f"Task success rate is {tasks['success_rate']:.1%} (< 80%)",
                    location=".openclaw/orchestrator/tasks.json",
                    evidence=[
                        f"Total tasks: {tasks['total']}",
                        f"Completed: {tasks['completed']}",
                        f"Failed: {tasks['failed']}",
                    ],
                    timestamp=datetime.now().isoformat(),
                )
            )

        # Example finding: no recent changes
        codebase = data.get("codebase", {})
        recent_changes = codebase.get("recent_changes", [])
        if len(recent_changes) == 0:
            self.findings.append(
                Finding(
                    id=f"finding-{len(self.findings) + 1}",
                    title="No recent code changes detected",
                    description="No Python files modified in the last 24 hours",
                    location="scripts/",
                    evidence=["Checked for *.py files with mtime < 24h"],
                    timestamp=datetime.now().isoformat(),
                )
            )

    # ------------------------------------------------------------------------
    # Stage 2: Analyze
    # ------------------------------------------------------------------------

    def analyze(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze collected data to identify optimization opportunities."""
        logger.info(f"[{self.cycle_id}] Analyzing data...")

        insights = []

        # Analyze task success rate
        tasks = data.get("workflow", {}).get("tasks", {})
        if tasks.get("success_rate", 1.0) < 0.9:
            insights.append(
                {
                    "type": "workflow_optimization",
                    "priority": "medium",
                    "reason": "Task success rate below 90%",
                    "metric": tasks["success_rate"],
                }
            )

        # Analyze script count
        codebase = data.get("codebase", {})
        if codebase.get("scripts_count", 0) > 50:
            insights.append(
                {
                    "type": "codebase_maintenance",
                    "priority": "low",
                    "reason": "Large number of scripts (>50) may need organization",
                    "metric": codebase["scripts_count"],
                }
            )

        return insights

    # ------------------------------------------------------------------------
    # Stage 3: Propose
    # ------------------------------------------------------------------------

    def propose(self, insights: List[Dict[str, Any]]) -> List[Recommendation]:
        """Generate optimization proposals based on insights."""
        logger.info(f"[{self.cycle_id}] Generating proposals...")

        recommendations = []

        for insight in insights:
            if insight["type"] == "workflow_optimization":
                rec = self._create_workflow_recommendation(insight)
                recommendations.append(rec)
            elif insight["type"] == "codebase_maintenance":
                rec = self._create_codebase_recommendation(insight)
                recommendations.append(rec)

        self.recommendations = recommendations
        return recommendations

    def _create_workflow_recommendation(self, insight: Dict[str, Any]) -> Recommendation:
        """Create a workflow optimization recommendation."""
        return Recommendation(
            id=f"rec-{len(self.recommendations) + 1}",
            title="Implement task failure analysis",
            description="Add automated analysis of failed tasks to identify common patterns",
            action_type="code_refactor",
            target="scripts/athena_ai_plan_runner.py",
            expected_benefit="Reduce task failure rate by identifying systemic issues",
            risk_level=RiskLevel.LOW,
            confidence=0.85,
            dependencies=[],
            requires_manual_confirmation=False,
        )

    def _create_codebase_recommendation(self, insight: Dict[str, Any]) -> Recommendation:
        """Create a codebase maintenance recommendation."""
        return Recommendation(
            id=f"rec-{len(self.recommendations) + 1}",
            title="Organize scripts into subdirectories",
            description="Group related scripts into functional directories (e.g., runners/, monitors/, utils/)",
            action_type="code_refactor",
            target="scripts/",
            expected_benefit="Improved maintainability and discoverability",
            risk_level=RiskLevel.MEDIUM,
            confidence=0.75,
            dependencies=[],
            requires_manual_confirmation=True,  # Medium risk, requires confirmation
        )

    # ------------------------------------------------------------------------
    # Stage 4: Gate
    # ------------------------------------------------------------------------

    def gate(self, recommendations: List[Recommendation]) -> Tuple[List[Recommendation], List[str]]:
        """Apply constraint gates to recommendations."""
        logger.info(f"[{self.cycle_id}] Applying constraint gates...")

        approved = []
        all_warnings = []

        for rec in recommendations:
            try:
                is_valid, warnings = self.constraint_gate.validate_recommendation(rec)
                if is_valid:
                    approved.append(rec)
                    all_warnings.extend(warnings)
                else:
                    logger.warning(f"Recommendation {rec.id} rejected by constraints")
            except ConstraintViolation as e:
                logger.warning(f"Recommendation {rec.id} violates constraints: {e}")

        # In dry-run mode, all approved recommendations are marked for manual review
        if self.dry_run:
            for rec in approved:
                rec.requires_manual_confirmation = True
                rec.title = f"[DRY-RUN] {rec.title}"

        return approved, all_warnings

    # ------------------------------------------------------------------------
    # Stage 5: Emit
    # ------------------------------------------------------------------------

    def emit(self, approved_recommendations: List[Recommendation]) -> ResearchResult:
        """Emit structured research results."""
        logger.info(f"[{self.cycle_id}] Emitting results...")

        # Create summary
        summary = (
            f"AutoResearch cycle {self.cycle_id} completed. "
            f"Found {len(self.findings)} findings and generated {len(approved_recommendations)} recommendations. "
            f"{sum(1 for r in approved_recommendations if r.requires_manual_confirmation)} require manual confirmation."
        )

        result = ResearchResult(
            cycle_id=self.cycle_id,
            timestamp=datetime.now().isoformat(),
            findings=self.findings,
            recommendations=approved_recommendations,
            summary=summary,
            metadata={
                "dry_run": self.dry_run,
                "constraints_applied": True,
                "output_format": "structured_json",
            },
        )

        # Write to file
        output_path = self._write_output(result)
        logger.info(f"Results written to {output_path}")

        return result

    def _write_output(self, result: ResearchResult) -> Path:
        """Write research results to a JSON file."""
        output_dir = Path(RUNTIME_ROOT) / "workspace" / "autoresearch"
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / f"{self.cycle_id}.json"

        # Convert dataclasses to dict
        result_dict = asdict(result)

        with open(output_path, "w") as f:
            json.dump(result_dict, f, indent=2, default=str)

        return output_path

    # ------------------------------------------------------------------------
    # Main Loop
    # ------------------------------------------------------------------------

    def run_cycle(self) -> ResearchResult:
        """Execute a complete AutoResearch cycle."""
        logger.info(f"Starting AutoResearch cycle {self.cycle_id}")

        # Stage 1: Collect
        data = self.collect()

        # Stage 2: Analyze
        insights = self.analyze(data)

        # Stage 3: Propose
        recommendations = self.propose(insights)

        # Stage 4: Gate
        approved, warnings = self.gate(recommendations)

        # Log warnings
        for warning in warnings:
            logger.warning(f"Constraint warning: {warning}")

        # Stage 5: Emit
        result = self.emit(approved)

        logger.info(f"AutoResearch cycle {self.cycle_id} completed successfully")
        return result


# ============================================================================
# CLI Interface
# ============================================================================


def main():
    parser = argparse.ArgumentParser(description="Athena AutoResearch Engine")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Run in dry-run mode (default: True)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Directory to write output files (default: workspace/autoresearch)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Create and run engine
    engine = AutoResearchEngine(dry_run=args.dry_run)

    try:
        result = engine.run_cycle()

        # Print summary
        print("\n" + "=" * 60)
        print("AutoResearch Cycle Complete")
        print("=" * 60)
        print(f"Cycle ID: {result.cycle_id}")
        print(f"Findings: {len(result.findings)}")
        print(f"Recommendations: {len(result.recommendations)}")
        print(
            f"Requires manual confirmation: {sum(1 for r in result.recommendations if r.requires_manual_confirmation)}"
        )
        print(f"Summary: {result.summary}")

        # Print recommendations
        if result.recommendations:
            print("\nRecommendations:")
            for rec in result.recommendations:
                confirm = (
                    " [REQUIRES MANUAL CONFIRMATION]" if rec.requires_manual_confirmation else ""
                )
                print(
                    f"  • {rec.title} (confidence: {rec.confidence:.0%}, risk: {rec.risk_level}){confirm}"
                )

        print(f"\nFull results written to: workspace/autoresearch/{result.cycle_id}.json")

    except Exception as e:
        logger.error(f"AutoResearch cycle failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
