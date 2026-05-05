"""CodeFlow pipeline — orchestrates scan → trigger → measure → keep/revert.

The full automated pipeline that ties together the ratchet loop components.
Includes crash recovery via .autorun_state marker file protocol.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from autoresearch.codeflow.ratchet_state import (
    AutoRunState,
    clear_state,
    detect_and_recover,
    get_current_commit,
    write_state,
)
from autoresearch.codeflow.scanner import DirectoryScanner, ScanResult
from autoresearch.codeflow.trigger import AgentType, TriggerConfig, TriggerResult, trigger_agent

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    scan_interval_seconds: int = 300
    auto_execute_approved: bool = False
    agent: AgentType = AgentType.CLAUDE_CODE
    trigger: TriggerConfig = field(default_factory=TriggerConfig)
    max_iterations_per_run: int = 10
    dry_run: bool = False


@dataclass
class PipelineResult:
    scanned: list[ScanResult] = field(default_factory=list)
    triggered: list[TriggerResult] = field(default_factory=list)
    total_new_tasks: int = 0
    total_executed: int = 0
    errors: list[str] = field(default_factory=list)
    recovery_message: str | None = None


class CodeFlowPipeline:
    """Orchestrates the full CodeFlow automation pipeline."""

    def __init__(self, config: PipelineConfig | None = None) -> None:
        self.config = config or PipelineConfig()
        self.scanner = DirectoryScanner()

    def run_once(self) -> PipelineResult:
        result = PipelineResult()

        recovery_msg = detect_and_recover()
        if recovery_msg:
            result.recovery_message = recovery_msg
            logger.warning(f"Recovery: {recovery_msg}")

        scan_results = self.scanner.scan()
        result.scanned = scan_results
        new_tasks = sum(r.new_items for r in scan_results)
        result.total_new_tasks = new_tasks

        if new_tasks == 0:
            return result

        for scan in scan_results:
            if not scan.target.auto_execute:
                continue
            if not self.config.auto_execute_approved:
                continue

            for i in range(min(scan.new_items, self.config.max_iterations_per_run)):
                commit_hash = get_current_commit()
                state = AutoRunState(
                    commit_hash=commit_hash,
                    step="evaluating",
                    target_file=str(scan.details.get("path", "")),
                    iteration=i,
                )
                write_state(state)

                issue = f"Execute ratchet loop on {scan.target.description}: {scan.details.get('path', '')}"
                try:
                    trigger = trigger_agent(
                        issue,
                        agent=self.config.agent,
                        timeout=self.config.trigger.timeout_seconds,
                        dry_run=self.config.dry_run or self.config.trigger.dry_run,
                    )
                    result.triggered.append(trigger)
                    if trigger.success:
                        result.total_executed += 1
                    else:
                        result.errors.append(trigger.error)
                except Exception as e:
                    result.errors.append(str(e))

                clear_state()

        return result

    def run(self) -> PipelineResult:
        return self.run_once()
