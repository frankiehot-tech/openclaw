#!/usr/bin/env python3
"""Rebuild prioritized AI plan queues and catalog.

This script turns the current AI plan directory into:
- one auto-runnable Build queue
- one auto-runnable Codex audit queue
- one auto-runnable Codex plan queue
- one human-readable catalog document
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

try:
    from .openclaw_roots import (
        PLAN_CONFIG_PATH,
        PLAN_DIR,
        QUEUE_STATE_DIR,
    )
except ImportError:
    import sys
    from pathlib import Path

    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from openclaw_roots import (
        PLAN_CONFIG_PATH,
        PLAN_DIR,
        QUEUE_STATE_DIR,
    )

CONFIG_PATH = PLAN_CONFIG_PATH
BUILD_QUEUE_PATH = PLAN_DIR / "OpenHuman-AIPlan-优先执行队列.queue.json"
AUDIT_QUEUE_PATH = PLAN_DIR / "OpenHuman-AIPlan-Codex审计队列.queue.json"
PLAN_QUEUE_PATH = PLAN_DIR / "OpenHuman-AIPlan-自动策划队列.queue.json"
CATALOG_PATH = PLAN_DIR / "OpenHuman-AIPlan-全量优先级任务列队与智能执行工作流.md"
ARCHIVE_DIR = PLAN_DIR / "completed"
DISCOVERY_SKIP_FILENAMES = {
    BUILD_QUEUE_PATH.name,
    AUDIT_QUEUE_PATH.name,
    PLAN_QUEUE_PATH.name,
    CATALOG_PATH.name,
    "OpenHuman-Athena-24小时压力测试执行报告.md",
    "README.md",
}


def resolve_instruction_path(filename: str) -> str:
    primary = PLAN_DIR / filename
    if primary.exists():
        return str(primary)
    archived = ARCHIVE_DIR / filename
    if archived.exists():
        return str(archived)
    return str(primary)


def item(
    *,
    item_id: str,
    title: str,
    filename: str,
    entry_stage: str,
    risk_level: str,
    unattended_allowed: bool,
    priority: str,
    lane: str,
    epic: str,
    category: str,
    rationale: str,
    depends_on: list[str] | None = None,
    autostart: bool = True,
) -> dict:
    return {
        "id": item_id,
        "title": title,
        "instruction_path": resolve_instruction_path(filename),
        "entry_stage": entry_stage,
        "risk_level": risk_level,
        "unattended_allowed": unattended_allowed,
        "targets": [],
        "metadata": {
            "priority": priority,
            "lane": lane,
            "epic": epic,
            "category": category,
            "rationale": rationale,
            "depends_on": depends_on or [],
            "autostart": autostart,
            "generated_by": "rebuild_aiplan_priority_queues.py",
        },
    }


BUILD_ITEMS = [
    item(
        item_id="aiplan_queue_runner_persistence",
        title="OpenHuman-AIPlanQueueRunner-持久执行与防卡死-VSCode执行指令",
        filename="OpenHuman-AIPlanQueueRunner-持久执行与防卡死-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P0",
        lane="build_auto",
        epic="execution_foundation",
        category="runner_foundation",
        rationale="先把队列 runner 的常驻执行、防卡死和真实状态写回做稳，否则后续所有 build 都会再次假死。",
    ),
    item(
        item_id="aiplan_queue_runner_closeout",
        title="OpenHuman-AIPlanQueueRunner-二次审计收口-VSCode执行指令",
        filename="OpenHuman-AIPlanQueueRunner-二次审计收口-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P0",
        lane="build_auto",
        epic="execution_foundation",
        category="runner_hardening",
        rationale="在持久执行恢复后立刻收口假成功、假完成和二次失败路径。",
        depends_on=["aiplan_queue_runner_persistence"],
    ),
    item(
        item_id="phase1_runtime_closeout",
        title="OpenHuman-Phase1-运行时修复与验收收口-VSCode执行指令",
        filename="OpenHuman-Phase1-运行时修复与验收收口-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P0",
        lane="build_auto",
        epic="runtime_repair",
        category="runtime_foundation",
        rationale="先补运行时断层与验收闭环，让主控制面、队列和执行证据处于同一个事实源。",
        depends_on=["aiplan_queue_runner_closeout"],
    ),
    item(
        item_id="athena_p0_schema_hitl_dispatch",
        title="OpenHuman-Athena-P0-任务Schema+HITL风险门+Cost统计+DispatchMVP-VSCode执行指令",
        filename="OpenHuman-Athena-P0-任务Schema+HITL风险门+Cost统计+DispatchMVP-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P1",
        lane="build_auto",
        epic="athena_runtime",
        category="schema_hitl_dispatch",
        rationale="这是 Athena 控制面的最小产品级地基：schema、审批门、成本可见性和 Dispatch MVP。",
        depends_on=["phase1_runtime_closeout"],
    ),
    item(
        item_id="athena_validation_moat_build",
        title="OpenHuman-Athena-Validation-Moat-VSCode执行指令",
        filename="OpenHuman-Athena-Validation-Moat-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P1",
        lane="build_auto",
        epic="athena_runtime",
        category="validation_moat",
        rationale="在 P0 之后补上 Validation Moat，让后续自动化扩张有验证护城河和失败样本回流。",
        depends_on=["athena_p0_schema_hitl_dispatch"],
    ),
    item(
        item_id="athena_skill_wiring_cli_anything",
        title="OpenHuman-Athena-沟通对齐+Skill接线+CLI-Anything增量接入-VSCode执行指令",
        filename="OpenHuman-Athena-沟通对齐+Skill接线+CLI-Anything增量接入-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P2",
        lane="build_auto",
        epic="athena_capabilities",
        category="skill_and_executor_wiring",
        rationale="Skill 接线与 CLI executor 扩展应建立在 Athena P0 主线之上，但不应被 Validation Moat 侧支实现阻塞。",
        depends_on=["athena_p0_schema_hitl_dispatch"],
    ),
    item(
        item_id="athena_chatruntime_seam_build",
        title="OpenHuman-Athena-ChatRuntime-Seam抽取与配置单一事实源-VSCode执行指令",
        filename="OpenHuman-Athena-ChatRuntime-Seam抽取与配置单一事实源-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P2",
        lane="build_auto",
        epic="athena_runtime",
        category="chatruntime_seam",
        rationale="把聊天 provider/fallback/status 先收敛到 chat runtime seam，减少入口层继续补丁化。",
        depends_on=["phase1_runtime_closeout"],
    ),
    item(
        item_id="athena_chatruntime_bridge_status_build",
        title="OpenHuman-Athena-Bridge聊天入口收敛与状态真实化-VSCode执行指令",
        filename="OpenHuman-Athena-Bridge聊天入口收敛与状态真实化-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P2",
        lane="build_auto",
        epic="athena_runtime",
        category="chatruntime_bridge_status",
        rationale="在 seam 建立后，把 athena_bridge 和 Web Desktop 的聊天状态语义收敛到真实运行态。",
        depends_on=["athena_chatruntime_seam_build"],
    ),
    item(
        item_id="athena_tenacitos_chatruntime_alignment_build",
        title="OpenHuman-TenacitOS-Desktop聊天运行态对齐-VSCode执行指令",
        filename="OpenHuman-TenacitOS-Desktop聊天运行态对齐-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P3",
        lane="build_auto",
        epic="athena_runtime",
        category="tenacitos_chatruntime_alignment",
        rationale="把 TenacitOS Desktop 的 health/port/chat runtime 展示与单一事实源对齐，避免再形成第二套状态定义。",
        depends_on=["athena_chatruntime_bridge_status_build"],
    ),
    item(
        item_id="nanobot_health_incident_contract",
        title="OpenHuman-nanobot-Athena-健康事件结构化与最小巡检修复-VSCode执行指令",
        filename="OpenHuman-nanobot-Athena-健康事件结构化与最小巡检修复-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P2",
        lane="build_auto",
        epic="runtime_repair",
        category="health_incident_contract",
        rationale="先把健康巡检输出固化为稳定 incident contract，给后续自动修复桥接器提供可靠输入。",
        depends_on=["phase1_runtime_closeout"],
    ),
    item(
        item_id="nanobot_auto_repair_bridge",
        title="OpenHuman-nanobot-Athena-自动修复桥接器与幂等入队-VSCode执行指令",
        filename="OpenHuman-nanobot-Athena-自动修复桥接器与幂等入队-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P2",
        lane="build_auto",
        epic="runtime_repair",
        category="auto_repair_bridge",
        rationale="在 incident contract 之上补上 issue -> Athena task/queue 的最小桥接器，并保证幂等与状态映射。",
        depends_on=[
            "nanobot_health_incident_contract",
            "athena_p0_schema_hitl_dispatch",
        ],
    ),
    item(
        item_id="nanobot_auto_repair_smoke",
        title="OpenHuman-nanobot-Athena-自动修复链Smoke与状态回写-VSCode执行指令",
        filename="OpenHuman-nanobot-Athena-自动修复链Smoke与状态回写-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P3",
        lane="build_auto",
        epic="runtime_repair",
        category="auto_repair_smoke",
        rationale="最后用最小端到端 smoke 验证 incident -> bridge -> Athena task/queue -> 状态回写这条链已恢复。",
        depends_on=["nanobot_auto_repair_bridge"],
    ),
    item(
        item_id="nanobot_inspection_auto_route",
        title="OpenHuman-nanobot-Athena-巡检结果自动路由与幂等触发-VSCode执行指令",
        filename="OpenHuman-nanobot-Athena-巡检结果自动路由与幂等触发-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P2",
        lane="build_auto",
        epic="runtime_repair",
        category="inspection_auto_route",
        rationale="把 supervisor 巡检产出的 repairable incident 自动送进 router，并在入口层先建立幂等与低风险筛选纪律。",
        depends_on=["nanobot_auto_repair_smoke"],
    ),
    item(
        item_id="nanobot_incident_state_machine",
        title="OpenHuman-nanobot-Athena-incident状态机回写与映射清理-VSCode执行指令",
        filename="OpenHuman-nanobot-Athena-incident状态机回写与映射清理-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P2",
        lane="build_auto",
        epic="runtime_repair",
        category="incident_state_machine",
        rationale="在自动路由之后补齐 detected/queued/running/completed-failed 回写和映射清理，让 nanobot 修复链变成可解释的状态机。",
        depends_on=["nanobot_inspection_auto_route"],
    ),
    item(
        item_id="nanobot_latest_cycle_guard",
        title="OpenHuman-nanobot-Athena-latest事件回放与守护入口-VSCode执行指令",
        filename="OpenHuman-nanobot-Athena-latest事件回放与守护入口-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P3",
        lane="build_auto",
        epic="runtime_repair",
        category="latest_cycle_guard",
        rationale="把 latest.json 驱动的一次性检查-路由-状态更新循环固定成守护入口，为 heartbeat/automation/cron 复用做准备。",
        depends_on=["nanobot_inspection_auto_route"],
    ),
    item(
        item_id="workflow_stability_runner_bootstrap_hardening",
        title="OpenHuman-Athena-WorkflowStability-Runner重启契约与Bootstrap硬化-VSCode执行指令",
        filename="OpenHuman-Athena-WorkflowStability-Runner重启契约与Bootstrap硬化-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P0",
        lane="build_auto",
        epic="workflow_stability",
        category="runner_bootstrap",
        rationale="把 build/review/plan 三类 runner 的 start/stop/status/restart 收敛成统一 bootstrap contract，解决重启后依赖旧 screen/pid 侥幸运行的问题。",
    ),
    item(
        item_id="workflow_stability_queue_reconcile_guard",
        title="OpenHuman-Athena-WorkflowStability-Queue状态对账与残留收口-VSCode执行指令",
        filename="OpenHuman-Athena-WorkflowStability-Queue状态对账与残留收口-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P0",
        lane="build_auto",
        epic="workflow_stability",
        category="queue_reconciliation",
        rationale="把 current_item_id/current_item_ids、stale running、孤儿 root task 和 artifact 缺失的收尾规则做成显式 reconcile guard，减少假活跃和残留状态堵线。",
        depends_on=["workflow_stability_runner_bootstrap_hardening"],
    ),
    item(
        item_id="workflow_stability_consumer_presence_probe",
        title="OpenHuman-Athena-WorkflowStability-ConsumerPresence探针与无人消费识别-VSCode执行指令",
        filename="OpenHuman-Athena-WorkflowStability-ConsumerPresence探针与无人消费识别-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P1",
        lane="build_auto",
        epic="workflow_stability",
        category="consumer_presence",
        rationale="为每条 route 增加 consumer presence probe，并把“有 queue item 但无对应 runner/worker”暴露到 compat 和面板，消除看起来停住但其实无人消费的盲区。",
        depends_on=["workflow_stability_runner_bootstrap_hardening"],
    ),
    item(
        item_id="workflow_stability_workflow_replay_smoke",
        title="OpenHuman-Athena-WorkflowStability-多Lane重放Smoke与恢复验收-VSCode执行指令",
        filename="OpenHuman-Athena-WorkflowStability-多Lane重放Smoke与恢复验收-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P1",
        lane="build_auto",
        epic="workflow_stability",
        category="workflow_replay_smoke",
        rationale="补一条覆盖 build/review/plan 的本地 replay smoke，验证 runner 可重启、queue 可续推、无人消费可见、state 可自动收尾，形成最小稳定性验收基线。",
        depends_on=[
            "workflow_stability_runner_bootstrap_hardening",
            "workflow_stability_queue_reconcile_guard",
            "workflow_stability_consumer_presence_probe",
        ],
    ),
    item(
        item_id="execution_harness_root_helper",
        title="OpenHuman-Athena-ExecutionHarness-根路径Helper与路径漂移收敛-VSCode执行指令",
        filename="OpenHuman-Athena-ExecutionHarness-根路径Helper与路径漂移收敛-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P0",
        lane="build_auto",
        epic="execution_foundation",
        category="root_resolution",
        rationale="先把路径事实源、状态根和兼容入口彻底收敛，为后续 manifest 自动生成与 preflight 门禁打底。",
    ),
    item(
        item_id="execution_harness_route_manifest_split",
        title="OpenHuman-Athena-ExecutionHarness-多队列分类与Manifest自动生成-VSCode执行指令",
        filename="OpenHuman-Athena-ExecutionHarness-多队列分类与Manifest自动生成-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P0",
        lane="build_auto",
        epic="execution_foundation",
        category="route_manifest_split",
        rationale="把 AI plan 文档从手工清单升级为自动分类生成 build/review/plan/research manifest 的事实源。",
        depends_on=["execution_harness_root_helper"],
    ),
    item(
        item_id="execution_harness_build_preflight_gate",
        title="OpenHuman-Athena-ExecutionHarness-Build入队Preflight与窄任务门禁-VSCode执行指令",
        filename="OpenHuman-Athena-ExecutionHarness-Build入队Preflight与窄任务门禁-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P1",
        lane="build_auto",
        epic="execution_foundation",
        category="build_preflight_gate",
        rationale="把 build lane 的放行条件做成结构化门禁，防止大而泛文档再次误入自动执行。",
        depends_on=[
            "execution_harness_root_helper",
            "execution_harness_route_manifest_split",
        ],
    ),
    item(
        item_id="execution_harness_pause_reason_surface",
        title="OpenHuman-Athena-ExecutionHarness-暂停原因结构化与UI透传-VSCode执行指令",
        filename="OpenHuman-Athena-ExecutionHarness-暂停原因结构化与UI透传-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P2",
        lane="build_auto",
        epic="execution_foundation",
        category="pause_reason_surface",
        rationale="把 dependency_blocked/manual_hold/no_consumer 等暂停原因结构化输出并直接透传到 UI，减少靠 artifact 猜状态。",
        depends_on=["execution_harness_build_preflight_gate"],
    ),
    item(
        item_id="execution_harness_memory_writeback",
        title="OpenHuman-Athena-ExecutionHarness-完成后Memory回写与交付摘要-VSCode执行指令",
        filename="OpenHuman-Athena-ExecutionHarness-完成后Memory回写与交付摘要-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P2",
        lane="build_auto",
        epic="execution_foundation",
        category="memory_writeback",
        rationale="让 build/review 完成态自动沉淀到 daily memory，减少第二天只能翻 artifact 的信息摩擦。",
        depends_on=["execution_harness_pause_reason_surface"],
    ),
    item(
        item_id="execution_harness_empty_state_hints",
        title="OpenHuman-Athena-ExecutionHarness-空闲态下一动作提示与面板提示-VSCode执行指令",
        filename="OpenHuman-Athena-ExecutionHarness-空闲态下一动作提示与面板提示-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P2",
        lane="build_auto",
        epic="execution_foundation",
        category="empty_state_hints",
        rationale="把自动链跑空、仅剩 manual_hold、依赖阻塞等状态统一翻译成 next action hint，避免空闲态被误读为故障。",
        depends_on=["execution_harness_pause_reason_surface"],
    ),
    item(
        item_id="athena_thread_workspace_trace_envelope",
        title="OpenHuman-Athena-ThreadWorkspace任务工作目录与Trace包络-VSCode执行指令",
        filename="OpenHuman-Athena-ThreadWorkspace任务工作目录与Trace包络-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P2",
        lane="build_auto",
        epic="athena_capabilities",
        category="thread_workspace_trace",
        rationale="先把 task workspace / evidence / checkpoints / trace 包络做实，为后续 runtime agent 与 sub-agent bus 提供容器。",
        depends_on=["athena_p0_schema_hitl_dispatch"],
    ),
    item(
        item_id="athena_runtime_agent_handoff",
        title="OpenHuman-Athena-RuntimeAgent复杂任务接管与中间层挂接-VSCode执行指令",
        filename="OpenHuman-Athena-RuntimeAgent复杂任务接管与中间层挂接-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P2",
        lane="build_auto",
        epic="athena_capabilities",
        category="runtime_agent_handoff",
        rationale="在不推翻现有控制面的前提下，为复杂任务新增最小 runtime handoff 层。",
        depends_on=["athena_thread_workspace_trace_envelope"],
    ),
    item(
        item_id="athena_pretool_guardrails",
        title="OpenHuman-Athena-Guardrails前置授权与阶段策略下沉-VSCode执行指令",
        filename="OpenHuman-Athena-Guardrails前置授权与阶段策略下沉-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P2",
        lane="build_auto",
        epic="athena_capabilities",
        category="pretool_guardrails",
        rationale="把 stage policy 和 HITL/validation 规则前移到 pre-tool guardrails，减少事后审计兜底。",
        depends_on=["athena_runtime_agent_handoff", "athena_validation_moat_build"],
    ),
    item(
        item_id="athena_subagent_bus_mvp",
        title="OpenHuman-Athena-SubAgentBus-MVP并发委派与结果合成-VSCode执行指令",
        filename="OpenHuman-Athena-SubAgentBus-MVP并发委派与结果合成-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P3",
        lane="build_auto",
        epic="athena_capabilities",
        category="subagent_bus",
        rationale="首轮只补有限角色、有限并发与结果合成，让 runtime 从串行脚本迈向可控并行。",
        depends_on=[
            "athena_thread_workspace_trace_envelope",
            "athena_runtime_agent_handoff",
        ],
    ),
    item(
        item_id="research_engine_workspace_guardrails_build",
        title="OpenHuman-Athena-Research-Engine-工作区骨架与许可边界冻结-VSCode执行指令",
        filename="OpenHuman-Athena-Research-Engine-工作区骨架与许可边界冻结-VSCode执行指令.md",
        entry_stage="build",
        risk_level="low",
        unattended_allowed=True,
        priority="P1",
        lane="build_auto",
        epic="research_engine",
        category="research_engine_scaffold",
        rationale="先冻结 Research Engine 的骨架与许可边界，再继续接公开数据与评分链。",
    ),
    item(
        item_id="research_engine_bls_pipeline_build",
        title="OpenHuman-Athena-Research-Engine-BLS公开数据接入与标准化-VSCode执行指令",
        filename="OpenHuman-Athena-Research-Engine-BLS公开数据接入与标准化-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P1",
        lane="build_auto",
        epic="research_engine",
        category="research_engine_data_pipeline",
        rationale="让 Research Engine 至少拥有一条公开合法的 BLS 数据管线，而不是停在概念层。",
        depends_on=["research_engine_workspace_guardrails_build"],
    ),
    item(
        item_id="research_engine_scoring_reports_build",
        title="OpenHuman-Athena-Research-Engine-评分热力图与简报产出-VSCode执行指令",
        filename="OpenHuman-Athena-Research-Engine-评分热力图与简报产出-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P2",
        lane="build_auto",
        epic="research_engine",
        category="research_engine_scoring",
        rationale="在标准化数据之上产出最小评分结果、heatmap payload 与简报。",
        depends_on=["research_engine_bls_pipeline_build"],
    ),
    item(
        item_id="research_engine_handoff_local_ops_build",
        title="OpenHuman-Athena-Research-Engine-OpenHuman回流接线与本地闭环验收-VSCode执行指令",
        filename="OpenHuman-Athena-Research-Engine-OpenHuman回流接线与本地闭环验收-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P2",
        lane="build_auto",
        epic="research_engine",
        category="research_engine_handoff_ops",
        rationale="把产物回流到 OpenHuman，并补齐本地闭环验收证据。",
        depends_on=["research_engine_scoring_reports_build"],
    ),
    item(
        item_id="athena_enterprise_control_plane_scopes",
        title="OpenHuman-Athena-Enterprise-控制面分层与本地优先策略作用域-VSCode执行指令",
        filename="OpenHuman-Athena-Enterprise-控制面分层与本地优先策略作用域-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P0",
        lane="build_auto",
        epic="enterprise_architecture",
        category="control_plane_scopes",
        rationale="把 Athena/OpenHuman 从脚本拼装状态推进到正式 control plane，并明确 local-first 策略边界。",
        depends_on=[
            "athena_tenacitos_chatruntime_alignment_build",
            "athena_pretool_guardrails",
        ],
    ),
    item(
        item_id="athena_enterprise_hook_event_bus",
        title="OpenHuman-Athena-Enterprise-Hook事件总线与审计证据面-VSCode执行指令",
        filename="OpenHuman-Athena-Enterprise-Hook事件总线与审计证据面-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P1",
        lane="build_auto",
        epic="enterprise_architecture",
        category="hook_event_bus",
        rationale="把 Athena 的控制逻辑从 runner 内部 if/else 升级为统一 hook/event bus 和证据面。",
        depends_on=[
            "athena_enterprise_control_plane_scopes",
            "execution_harness_memory_writeback",
        ],
    ),
    item(
        item_id="athena_enterprise_subagent_registry",
        title="OpenHuman-Athena-Enterprise-Subagent注册表与角色工具边界-VSCode执行指令",
        filename="OpenHuman-Athena-Enterprise-Subagent注册表与角色工具边界-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P1",
        lane="build_auto",
        epic="enterprise_architecture",
        category="subagent_registry",
        rationale="在已有 SubAgentBus MVP 之上形成正式 subagent registry、角色契约和工具边界。",
        depends_on=[
            "athena_subagent_bus_mvp",
            "athena_enterprise_hook_event_bus",
        ],
    ),
    item(
        item_id="athena_enterprise_recursive_distill",
        title="OpenHuman-Athena-Enterprise-completed蒸馏回流与递归改进闭环-VSCode执行指令",
        filename="OpenHuman-Athena-Enterprise-completed蒸馏回流与递归改进闭环-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P2",
        lane="build_auto",
        epic="enterprise_architecture",
        category="recursive_distill_loop",
        rationale="让 completed 从归档终点升级为蒸馏回流入口，为可递归改进架构补齐闭环。",
        depends_on=[
            "athena_enterprise_subagent_registry",
            "execution_harness_memory_writeback",
        ],
    ),
    item(
        item_id="athena_autoresearch_engine_skeleton",
        title="OpenHuman-Athena-AutoResearch-基础优化引擎原型与约束骨架-VSCode执行指令",
        filename="OpenHuman-Athena-AutoResearch-基础优化引擎原型与约束骨架-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P1",
        lane="build_auto",
        epic="autoresearch_integration",
        category="engine_skeleton",
        rationale="把 AutoResearch 从纯研究文档推进到最小可运行引擎骨架，并先补齐约束门。",
        depends_on=[
            "athena_enterprise_recursive_distill",
            "research_engine_handoff_local_ops_build",
        ],
    ),
    item(
        item_id="athena_autoresearch_metrics_baseline",
        title="OpenHuman-Athena-AutoResearch-性能数据采集与评估基线-VSCode执行指令",
        filename="OpenHuman-Athena-AutoResearch-性能数据采集与评估基线-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P1",
        lane="build_auto",
        epic="autoresearch_integration",
        category="metrics_baseline",
        rationale="为 AutoResearch 建立最小性能数据输入，让优化循环基于真实 runtime/queue 证据而非空想。",
        depends_on=["athena_autoresearch_engine_skeleton"],
    ),
    item(
        item_id="athena_autoresearch_workflow_entry",
        title="OpenHuman-Athena-AutoResearch-工作流挂接与研究循环入口-VSCode执行指令",
        filename="OpenHuman-Athena-AutoResearch-工作流挂接与研究循环入口-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P2",
        lane="build_auto",
        epic="autoresearch_integration",
        category="workflow_entry",
        rationale="把 AutoResearch 原型正式挂进 Athena 工作流，并形成可降级的研究循环入口。",
        depends_on=["athena_autoresearch_metrics_baseline"],
    ),
    item(
        item_id="openspace_local_adapter_boundary",
        title="OpenHuman-OpenSpace-本地适配器与配置隔离骨架-VSCode执行指令",
        filename="OpenHuman-OpenSpace-本地适配器与配置隔离骨架-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P1",
        lane="build_auto",
        epic="openspace_integration",
        category="local_adapter_boundary",
        rationale="先把 OpenSpace 收敛成一个本地优先、禁云、可被 Athena 调用的 adapter 骨架，再继续谈进化与监控。",
        depends_on=[
            "athena_autoresearch_workflow_entry",
            "athena_enterprise_architecture_audit",
        ],
    ),
    item(
        item_id="openspace_metrics_sandbox_constraints",
        title="OpenHuman-OpenSpace-技能进化指标采集与安全沙箱约束-VSCode执行指令",
        filename="OpenHuman-OpenSpace-技能进化指标采集与安全沙箱约束-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P1",
        lane="build_auto",
        epic="openspace_integration",
        category="metrics_sandbox_constraints",
        rationale="在 adapter 骨架之上补齐性能指标输入、假设-修改-评估循环骨架和安全沙箱约束。",
        depends_on=["openspace_local_adapter_boundary"],
    ),
    item(
        item_id="openspace_monitoring_audit_surface",
        title="OpenHuman-OpenSpace-审核流与监控证据面接线-VSCode执行指令",
        filename="OpenHuman-OpenSpace-审核流与监控证据面接线-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P2",
        lane="build_auto",
        epic="openspace_integration",
        category="monitoring_audit_surface",
        rationale="让 OpenSpace 集成结果真正进入 Athena 现有证据、审核和人工干预链，而不是成为孤立模块。",
        depends_on=[
            "openspace_metrics_sandbox_constraints",
            "athena_enterprise_hook_event_bus",
        ],
    ),
    item(
        item_id="openhuman_mvp_test_env_baseline",
        title="OpenHuman-MVP-测试环境与内部试用闭环骨架-VSCode执行指令",
        filename="OpenHuman-MVP-测试环境与内部试用闭环骨架-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P1",
        lane="build_auto",
        epic="openhuman_mvp_engineering",
        category="test_env_baseline",
        rationale="先把 MVP 内测环境、内部试用用户分层和 onboarding 契约做实，避免工程化继续停留在计划文档层。",
        depends_on=[
            "openspace_integration_audit",
            "athena_autoresearch_integration_audit",
        ],
    ),
    item(
        item_id="openhuman_mvp_stability_alert_baseline",
        title="OpenHuman-MVP-核心稳定性指标与告警基线-VSCode执行指令",
        filename="OpenHuman-MVP-核心稳定性指标与告警基线-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P1",
        lane="build_auto",
        epic="openhuman_mvp_engineering",
        category="stability_alert_baseline",
        rationale="把 MVP 文档里的稳定性、性能和告警要求落实成当前系统可验证的指标基线。",
        depends_on=["openhuman_mvp_test_env_baseline"],
    ),
    item(
        item_id="openhuman_mvp_feedback_scoreboard",
        title="OpenHuman-MVP-反馈闭环与持续改进评分板-VSCode执行指令",
        filename="OpenHuman-MVP-反馈闭环与持续改进评分板-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P2",
        lane="build_auto",
        epic="openhuman_mvp_engineering",
        category="feedback_scoreboard",
        rationale="把反馈 intake、改进状态流和技术/用户/业务评分板接进现有 Athena 证据与 memory 体系。",
        depends_on=["openhuman_mvp_stability_alert_baseline"],
    ),
    item(
        item_id="openhuman_stitch_workspace_shell",
        title="OpenHuman-Stitch-前端壳体导入与工作区骨架-VSCode执行指令",
        filename="OpenHuman-Stitch-前端壳体导入与工作区骨架-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P1",
        lane="build_auto",
        epic="openhuman_stitch_integration",
        category="workspace_shell",
        rationale="先把 Stitch 生成内容收敛成可承载的前端壳体和工作区骨架，再继续做 Athena 接线和质量基线。",
        depends_on=[
            "openhuman_mvp_engineering_audit",
            "openspace_integration_audit",
        ],
    ),
    item(
        item_id="openhuman_stitch_athena_wiring",
        title="OpenHuman-Stitch-Athena接口接线与状态统一-VSCode执行指令",
        filename="OpenHuman-Stitch-Athena接口接线与状态统一-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P1",
        lane="build_auto",
        epic="openhuman_stitch_integration",
        category="athena_wiring",
        rationale="让 Stitch 壳体真正读到 Athena 的 chat、skills、tasks 和 system status，而不是只停在静态界面。",
        depends_on=["openhuman_stitch_workspace_shell"],
    ),
    item(
        item_id="openhuman_stitch_responsive_quality",
        title="OpenHuman-Stitch-响应式性能与质量基线-VSCode执行指令",
        filename="OpenHuman-Stitch-响应式性能与质量基线-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P2",
        lane="build_auto",
        epic="openhuman_stitch_integration",
        category="responsive_quality",
        rationale="在壳体与 Athena 接线完成后，补齐响应式、性能和 gap register 基线，避免 UI 主线停在演示层。",
        depends_on=["openhuman_stitch_athena_wiring"],
    ),
    item(
        item_id="openhuman_harness_context_constraints_foundation",
        title="OpenHuman-Harness-上下文预算与约束恢复基础层-VSCode执行指令",
        filename="OpenHuman-Harness-上下文预算与约束恢复基础层-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P0",
        lane="build_auto",
        epic="harness_engineering",
        category="context_constraints_foundation",
        rationale="先把 Harness Engineering 的上下文预算、约束和恢复基础层收敛成 Athena/Open Human 当前代码可挂接的正式骨架。",
        depends_on=[
            "openhuman_stitch_integration_audit",
            "athena_enterprise_architecture_audit",
        ],
    ),
    item(
        item_id="openhuman_harness_execution_tool_protocol",
        title="OpenHuman-Harness-执行图状态机与工具协议接线-VSCode执行指令",
        filename="OpenHuman-Harness-执行图状态机与工具协议接线-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P1",
        lane="build_auto",
        epic="harness_engineering",
        category="execution_tool_protocol",
        rationale="在基础层建立后，把 execution graph、state machine 和 tool result protocol 正式接进当前 Athena 执行链。",
        depends_on=["openhuman_harness_context_constraints_foundation"],
    ),
    item(
        item_id="openhuman_harness_observability_acceptance",
        title="OpenHuman-Harness-观测评估基线与集成验收-VSCode执行指令",
        filename="OpenHuman-Harness-观测评估基线与集成验收-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P1",
        lane="build_auto",
        epic="harness_engineering",
        category="observability_acceptance",
        rationale="把 Harness 的 observability、evaluation 和 acceptance baseline 做实，形成当前工程可复用的证据面。",
        depends_on=["openhuman_harness_execution_tool_protocol"],
    ),
    item(
        item_id="openhuman_automaton_budget_modes",
        title="OpenHuman-Automaton-预算心跳与四级生存模式接入-VSCode执行指令",
        filename="OpenHuman-Automaton-预算心跳与四级生存模式接入-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P1",
        lane="build_auto",
        epic="automaton_mvp",
        category="budget_modes",
        rationale="先把 Automaton 的预算 heartbeat 和四级生存模式最小接进 Athena/Open Human 当前运行时，再继续扩支付与暂停闭环。",
        depends_on=[
            "openhuman_harness_engineering_audit",
            "openhuman_mvp_engineering_audit",
        ],
    ),
    item(
        item_id="openhuman_automaton_human_gate",
        title="OpenHuman-Automaton-支付审批接口与人类闸门-VSCode执行指令",
        filename="OpenHuman-Automaton-支付审批接口与人类闸门-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P1",
        lane="build_auto",
        epic="automaton_mvp",
        category="human_gate",
        rationale="在预算 heartbeat 建立后，形成最小支付审批/Human Gate contract 和证据面。",
        depends_on=["openhuman_automaton_budget_modes"],
    ),
    item(
        item_id="openhuman_automaton_pause_acceptance",
        title="OpenHuman-Automaton-优雅暂停恢复与闭环验收-VSCode执行指令",
        filename="OpenHuman-Automaton-优雅暂停恢复与闭环验收-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P2",
        lane="build_auto",
        epic="automaton_mvp",
        category="pause_acceptance",
        rationale="把 Automaton MVP 的暂停/恢复/监控/验收做实，形成最小闭环。",
        depends_on=["openhuman_automaton_human_gate"],
    ),
    item(
        item_id="athena_agent_load_balancer_health",
        title="OpenHuman-Athena-Agent-负载均衡与健康检查调度骨架-VSCode执行指令",
        filename="OpenHuman-Athena-Agent-负载均衡与健康检查调度骨架-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P0",
        lane="build_auto",
        epic="athena_agent_tuning",
        category="load_balancer_health",
        rationale="先把 Athena Agent 的健康评分、负载均衡和故障转移骨架做实，为后续缓存、并发和智能路由提供评分基础。",
    ),
    item(
        item_id="athena_agent_codex_cache_baseline",
        title="OpenHuman-Athena-Agent-Codex语义缓存与命中基线-VSCode执行指令",
        filename="OpenHuman-Athena-Agent-Codex语义缓存与命中基线-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P0",
        lane="build_auto",
        epic="athena_agent_tuning",
        category="codex_cache",
        rationale="在调度骨架稳定后，补 Codex 任务缓存与命中基线，优先解决重复分析耗时和成本问题。",
        depends_on=["athena_agent_load_balancer_health"],
    ),
    item(
        item_id="athena_agent_monitoring_surface",
        title="OpenHuman-Athena-Agent-性能监控增强与实时指标面-VSCode执行指令",
        filename="OpenHuman-Athena-Agent-性能监控增强与实时指标面-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P1",
        lane="build_auto",
        epic="athena_agent_tuning",
        category="monitoring_surface",
        rationale="建立 agent/runner 的实时指标和告警面，为后续并发与路由门控提供真实信号。",
        depends_on=["athena_agent_codex_cache_baseline"],
    ),
    item(
        item_id="athena_agent_parallel_build_gate",
        title="OpenHuman-Athena-Agent-OpenCode并行构建与资源门控-VSCode执行指令",
        filename="OpenHuman-Athena-Agent-OpenCode并行构建与资源门控-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P1",
        lane="build_auto",
        epic="athena_agent_tuning",
        category="parallel_build_gate",
        rationale="在指标面建立后，把 OpenCode 并发调度正式收敛成可解释的资源门控策略。",
        depends_on=["athena_agent_monitoring_surface"],
    ),
    item(
        item_id="athena_agent_smart_routing_score",
        title="OpenHuman-Athena-Agent-智能路由评分与A-B评估-VSCode执行指令",
        filename="OpenHuman-Athena-Agent-智能路由评分与A-B评估-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P2",
        lane="build_auto",
        epic="athena_agent_tuning",
        category="smart_routing_score",
        rationale="把健康度、缓存、监控和并发门控汇总成最小智能路由评分层，并保留对比评估入口。",
        depends_on=[
            "athena_agent_parallel_build_gate",
            "athena_agent_load_balancer_health",
        ],
    ),
    item(
        item_id="openhuman_fusion_automaton_budget_skill_loop",
        title="OpenHuman-Fusion-Automaton-预算技能执行与生存模式闭环-VSCode执行指令",
        filename="OpenHuman-Fusion-Automaton-预算技能执行与生存模式闭环-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P0",
        lane="build_auto",
        epic="fusion_automaton",
        category="budget_skill_loop",
        rationale="先把 Athena/Open Human × Automaton 全量方案里的预算化技能执行和四级生存模式闭环做实，作为后续合作社和运营层的执行底座。",
        depends_on=[
            "openhuman_automaton_mvp_audit",
            "athena_agent_tuning_audit",
        ],
    ),
    item(
        item_id="openhuman_fusion_automaton_skill_coop_ledger",
        title="OpenHuman-Fusion-Automaton-技能合作社注册发现与收益账本-VSCode执行指令",
        filename="OpenHuman-Fusion-Automaton-技能合作社注册发现与收益账本-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P1",
        lane="build_auto",
        epic="fusion_automaton",
        category="skill_coop_ledger",
        rationale="在预算技能执行闭环建立后，把技能合作社注册、发现和收益账本最小接进当前工程。",
        depends_on=["openhuman_fusion_automaton_budget_skill_loop"],
    ),
    item(
        item_id="openhuman_fusion_automaton_ops_monitoring",
        title="OpenHuman-Fusion-Automaton-自动化运营与资金监控告警-VSCode执行指令",
        filename="OpenHuman-Fusion-Automaton-自动化运营与资金监控告警-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P1",
        lane="build_auto",
        epic="fusion_automaton",
        category="ops_monitoring",
        rationale="把资金监控、运营自动化和告警收敛成当前工程可运行的最小骨架，而不是继续停留在 GitHub Actions 示例层。",
        depends_on=["openhuman_fusion_automaton_skill_coop_ledger"],
    ),
    item(
        item_id="openhuman_fusion_automaton_hardening_open_source",
        title="OpenHuman-Fusion-Automaton-安全性能加固与开源就绪-VSCode执行指令",
        filename="OpenHuman-Fusion-Automaton-安全性能加固与开源就绪-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P2",
        lane="build_auto",
        epic="fusion_automaton",
        category="hardening_open_source",
        rationale="在技能/运营主线建立后，做最小安全、性能和开源就绪收口，为后续发布前审计准备 evidence。",
        depends_on=["openhuman_fusion_automaton_ops_monitoring"],
    ),
    item(
        item_id="openhuman_24h_stress_m4_profile_start",
        title="OpenHuman-Athena-24小时压测-M4最佳态校准与启动器-VSCode执行指令",
        filename="OpenHuman-Athena-24小时压测-M4最佳态校准与启动器-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P0",
        lane="build_auto",
        epic="stress_test",
        category="m4_profile_start",
        rationale="先把本地 M4 的安全最佳态和 24h 压测启动器做成正式能力，否则压测只能停留在一次性命令。",
    ),
    item(
        item_id="openhuman_24h_stress_runner_evidence_loop",
        title="OpenHuman-Athena-24小时压测-SoakRunner与证据采集链路-VSCode执行指令",
        filename="OpenHuman-Athena-24小时压测-SoakRunner与证据采集链路-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P1",
        lane="build_auto",
        epic="stress_test",
        category="runner_evidence_loop",
        rationale="在启动器基础上把 24h soak runner、资源采样、稳定性/性能/autoresearch 证据采集链路做实。",
        depends_on=["openhuman_24h_stress_m4_profile_start"],
    ),
    item(
        item_id="openhuman_24h_stress_checkpoint_closeout",
        title="OpenHuman-Athena-24小时压测-恢复检查点与收口审计-VSCode执行指令",
        filename="OpenHuman-Athena-24小时压测-恢复检查点与收口审计-VSCode执行指令.md",
        entry_stage="build",
        risk_level="medium",
        unattended_allowed=True,
        priority="P1",
        lane="build_auto",
        epic="stress_test",
        category="checkpoint_closeout",
        rationale="把 phase checkpoint、异常窗口、恢复窗口和最终收口骨架补进 live 报告与状态文件。",
        depends_on=["openhuman_24h_stress_runner_evidence_loop"],
    ),
]


AUDIT_ITEMS = [
    item(
        item_id="athena_validation_moat_codex_audit",
        title="OpenHuman-Athena-Validation-Moat-Codex审计指令",
        filename="OpenHuman-Athena-Validation-Moat-Codex审计指令.md",
        entry_stage="review",
        risk_level="medium",
        unattended_allowed=False,
        priority="R1",
        lane="review_auto",
        epic="athena_runtime",
        category="codex_audit",
        rationale="Validation Moat 首轮实现完成后，自动进入 Codex 审计链收口，而不是停在纯人工待处理状态。",
        depends_on=["athena_validation_moat_build"],
    ),
    item(
        item_id="athena_chatruntime_codex_audit",
        title="OpenHuman-Athena-ChatRuntime收敛-Codex审计指令",
        filename="OpenHuman-Athena-ChatRuntime收敛-Codex审计指令.md",
        entry_stage="review",
        risk_level="medium",
        unattended_allowed=False,
        priority="R1",
        lane="review_auto",
        epic="athena_runtime",
        category="codex_audit",
        rationale="Chat runtime seam、bridge 状态语义与 TenacitOS 对齐落地后，进入 Codex 审计验证是否真正形成单一事实源。",
        depends_on=["athena_tenacitos_chatruntime_alignment_build"],
    ),
    item(
        item_id="execution_harness_gate_audit",
        title="OpenHuman-Athena-ExecutionHarness-分类纪律与门禁收口-Codex审计指令",
        filename="OpenHuman-Athena-ExecutionHarness-分类纪律与门禁收口-Codex审计指令.md",
        entry_stage="review",
        risk_level="medium",
        unattended_allowed=False,
        priority="R1",
        lane="review_auto",
        epic="execution_foundation",
        category="gate_audit",
        rationale="在根路径、manifest 分类和 build preflight 落地后，独立验证新的执行纪律是否真实成立。",
        depends_on=[
            "execution_harness_root_helper",
            "execution_harness_route_manifest_split",
            "execution_harness_build_preflight_gate",
        ],
    ),
    item(
        item_id="execution_harness_workflow_enhancement_audit",
        title="OpenHuman-Athena-ExecutionHarness-工作流增强收口-Codex审计指令",
        filename="OpenHuman-Athena-ExecutionHarness-工作流增强收口-Codex审计指令.md",
        entry_stage="review",
        risk_level="medium",
        unattended_allowed=False,
        priority="R1",
        lane="review_auto",
        epic="execution_foundation",
        category="workflow_enhancement_audit",
        rationale="在暂停原因透传、memory writeback 与空闲态提示落地后，独立审计状态语义、幂等和用户可理解性。",
        depends_on=[
            "execution_harness_pause_reason_surface",
            "execution_harness_memory_writeback",
            "execution_harness_empty_state_hints",
        ],
    ),
    item(
        item_id="nanobot_auto_repair_second_audit",
        title="OpenHuman-nanobot-Athena-自动修复链二次收口-Codex审计指令",
        filename="OpenHuman-nanobot-Athena-自动修复链二次收口-Codex审计指令.md",
        entry_stage="review",
        risk_level="medium",
        unattended_allowed=False,
        priority="R1",
        lane="review_auto",
        epic="runtime_repair",
        category="nanobot_auto_repair_second_audit",
        rationale="在巡检自动触发、incident 状态机与 latest 守护入口落地后，独立审计 nanobot 自动修复链是否具备再次接回更高频自动运行的条件。",
        depends_on=[
            "nanobot_inspection_auto_route",
            "nanobot_incident_state_machine",
            "nanobot_latest_cycle_guard",
        ],
    ),
    item(
        item_id="athena_enterprise_architecture_audit",
        title="OpenHuman-Athena-Enterprise-优化加固架构收口-Codex审计指令",
        filename="OpenHuman-Athena-Enterprise-优化加固架构收口-Codex审计指令.md",
        entry_stage="review",
        risk_level="medium",
        unattended_allowed=False,
        priority="R1",
        lane="review_auto",
        epic="enterprise_architecture",
        category="enterprise_architecture_audit",
        rationale="在 control plane、event bus、subagent registry 和 recursive distill loop 落地后，独立审计这条企业级加固主线是否真正形成系统骨架。",
        depends_on=[
            "athena_enterprise_control_plane_scopes",
            "athena_enterprise_hook_event_bus",
            "athena_enterprise_subagent_registry",
            "athena_enterprise_recursive_distill",
        ],
    ),
    item(
        item_id="athena_autoresearch_integration_audit",
        title="OpenHuman-Athena-AutoResearch-集成收口-Codex审计指令",
        filename="OpenHuman-Athena-AutoResearch-集成收口-Codex审计指令.md",
        entry_stage="review",
        risk_level="medium",
        unattended_allowed=False,
        priority="R1",
        lane="review_auto",
        epic="autoresearch_integration",
        category="integration_audit",
        rationale="在 AutoResearch 引擎骨架、性能基线和 workflow entry 落地后，独立审计是否真正从概念研究进入最小技术集成。",
        depends_on=[
            "athena_autoresearch_engine_skeleton",
            "athena_autoresearch_metrics_baseline",
            "athena_autoresearch_workflow_entry",
        ],
    ),
    item(
        item_id="openspace_integration_audit",
        title="OpenHuman-OpenSpace-工程集成收口-Codex审计指令",
        filename="OpenHuman-OpenSpace-工程集成收口-Codex审计指令.md",
        entry_stage="review",
        risk_level="medium",
        unattended_allowed=False,
        priority="R1",
        lane="review_auto",
        epic="openspace_integration",
        category="integration_audit",
        rationale="在 OpenSpace adapter、指标与约束、监控与审核流落地后，独立审计是否已经进入最小工程集成阶段。",
        depends_on=[
            "openspace_local_adapter_boundary",
            "openspace_metrics_sandbox_constraints",
            "openspace_monitoring_audit_surface",
        ],
    ),
    item(
        item_id="openhuman_mvp_engineering_audit",
        title="OpenHuman-MVP-工程化实施收口-Codex审计指令",
        filename="OpenHuman-MVP-工程化实施收口-Codex审计指令.md",
        entry_stage="review",
        risk_level="medium",
        unattended_allowed=False,
        priority="R1",
        lane="review_auto",
        epic="openhuman_mvp_engineering",
        category="engineering_audit",
        rationale="在 MVP 测试环境骨架、稳定性指标与反馈评分板落地后，独立审计是否已经达到可内部测试的工程化阶段。",
        depends_on=[
            "openhuman_mvp_test_env_baseline",
            "openhuman_mvp_stability_alert_baseline",
            "openhuman_mvp_feedback_scoreboard",
        ],
    ),
    item(
        item_id="openhuman_stitch_integration_audit",
        title="OpenHuman-Stitch-项目包集成收口-Codex审计指令",
        filename="OpenHuman-Stitch-项目包集成收口-Codex审计指令.md",
        entry_stage="review",
        risk_level="medium",
        unattended_allowed=False,
        priority="R1",
        lane="review_auto",
        epic="openhuman_stitch_integration",
        category="integration_audit",
        rationale="在 Stitch 前端壳体、Athena 接线和质量基线落地后，独立审计是否已达到最小工程集成阶段。",
        depends_on=[
            "openhuman_stitch_workspace_shell",
            "openhuman_stitch_athena_wiring",
            "openhuman_stitch_responsive_quality",
        ],
    ),
    item(
        item_id="openhuman_harness_engineering_audit",
        title="OpenHuman-Harness-Engineering工程收口-Codex审计指令",
        filename="OpenHuman-Harness-Engineering工程收口-Codex审计指令.md",
        entry_stage="review",
        risk_level="medium",
        unattended_allowed=False,
        priority="R1",
        lane="review_auto",
        epic="harness_engineering",
        category="engineering_audit",
        rationale="在 Harness Engineering 三张 build 卡落地后，独立审计 Athena/Open Human 是否已经形成最小可演进的 Harness 工程骨架。",
        depends_on=[
            "openhuman_harness_context_constraints_foundation",
            "openhuman_harness_execution_tool_protocol",
            "openhuman_harness_observability_acceptance",
        ],
    ),
    item(
        item_id="openhuman_automaton_mvp_audit",
        title="OpenHuman-Automaton-MVP集成收口-Codex审计指令",
        filename="OpenHuman-Automaton-MVP集成收口-Codex审计指令.md",
        entry_stage="review",
        risk_level="medium",
        unattended_allowed=False,
        priority="R1",
        lane="review_auto",
        epic="automaton_mvp",
        category="mvp_audit",
        rationale="在 Automaton MVP 的预算、Human Gate、暂停恢复三张 build 卡落地后，独立审计这条经济闭环主线是否真实接进 Athena/Open Human。",
        depends_on=[
            "openhuman_automaton_budget_modes",
            "openhuman_automaton_human_gate",
            "openhuman_automaton_pause_acceptance",
        ],
    ),
    item(
        item_id="athena_agent_tuning_audit",
        title="OpenHuman-Athena-Agent-系统调优收口-Codex审计指令",
        filename="OpenHuman-Athena-Agent-系统调优收口-Codex审计指令.md",
        entry_stage="review",
        risk_level="medium",
        unattended_allowed=False,
        priority="R1",
        lane="review_auto",
        epic="athena_agent_tuning",
        category="tuning_audit",
        rationale="在 Athena Agent 调优五张 build 卡落地后，独立审计系统调优是否形成了可运行闭环，而不是一组孤立优化项。",
        depends_on=[
            "athena_agent_load_balancer_health",
            "athena_agent_codex_cache_baseline",
            "athena_agent_monitoring_surface",
            "athena_agent_parallel_build_gate",
            "athena_agent_smart_routing_score",
        ],
    ),
    item(
        item_id="openhuman_fusion_automaton_full_audit",
        title="OpenHuman-Fusion-Automaton-全量工程收口-Codex审计指令",
        filename="OpenHuman-Fusion-Automaton-全量工程收口-Codex审计指令.md",
        entry_stage="review",
        risk_level="medium",
        unattended_allowed=False,
        priority="R1",
        lane="review_auto",
        epic="fusion_automaton",
        category="full_engineering_audit",
        rationale="在 Athena/Open Human × Automaton 全量工程四张 build 卡落地后，独立审计这条经济自主与技能生态主线是否形成了可验证闭环。",
        depends_on=[
            "openhuman_fusion_automaton_budget_skill_loop",
            "openhuman_fusion_automaton_skill_coop_ledger",
            "openhuman_fusion_automaton_ops_monitoring",
            "openhuman_fusion_automaton_hardening_open_source",
        ],
    ),
    item(
        item_id="openhuman_24h_stress_results_audit",
        title="OpenHuman-Athena-24小时压测-结果审计与发布指令-Codex审计指令",
        filename="OpenHuman-Athena-24小时压测-结果审计与发布指令-Codex审计指令.md",
        entry_stage="review",
        risk_level="medium",
        unattended_allowed=False,
        priority="R1",
        lane="review_auto",
        epic="stress_test",
        category="stress_results_audit",
        rationale="在 24h 压测启动器、runner、证据链和恢复检查点落地后，独立审计这轮压力测试是否已形成正式工程能力。",
        depends_on=["openhuman_24h_stress_checkpoint_closeout"],
    ),
]


PLAN_ITEMS = [
    item(
        item_id="workflow_stability_autoresearch_plan",
        title="OpenHuman-Athena-autoresearch-工作流稳定性研究与跑通方案",
        filename="OpenHuman-Athena-autoresearch-工作流稳定性研究与跑通方案.md",
        entry_stage="plan",
        risk_level="medium",
        unattended_allowed=False,
        priority="S0",
        lane="plan_auto",
        epic="execution_foundation",
        category="workflow_stability_research",
        rationale="这是当前 AIplan 生产线稳定性的总研究母卡，应优先于其它策划卡被消费并继续拆出修复卡。",
    ),
    item(
        item_id="execution_harness_rearchitecture",
        title="OpenHuman-Athena-Execution-Harness-流程重构方案",
        filename="OpenHuman-Athena-Execution-Harness-流程重构方案.md",
        entry_stage="plan",
        risk_level="medium",
        unattended_allowed=False,
        priority="S1",
        lane="plan_auto",
        epic="execution_foundation",
        category="workflow_architecture",
        rationale="作为当前队列与 harness 重构的总蓝图，供 Codex 持续校正执行纪律。",
    ),
    item(
        item_id="chatruntime_convergence_plan",
        title="OpenHuman-Athena-技术债防累积与ChatRuntime收敛执行方案",
        filename="OpenHuman-Athena-技术债防累积与ChatRuntime收敛执行方案.md",
        entry_stage="plan",
        risk_level="medium",
        unattended_allowed=False,
        priority="S1",
        lane="plan_auto",
        epic="athena_runtime",
        category="chatruntime_convergence",
        rationale="作为后续把聊天壳、runtime 和执行队列继续收束到单事实源的参考。",
    ),
    item(
        item_id="nanobot_reconnect_umbrella_reference",
        title="OpenHuman-nanobot-mini-agent-Athena-VSCode-自动修复链重连-VSCode执行指令",
        filename="OpenHuman-nanobot-mini-agent-Athena-VSCode-自动修复链重连-VSCode执行指令.md",
        entry_stage="plan",
        risk_level="medium",
        unattended_allowed=False,
        priority="S2",
        lane="reference_manual",
        epic="runtime_repair",
        category="umbrella_reference",
        rationale="保留原始大卡作为总参考文档，但不再直接进入自动 build runner，避免再次用一张过宽任务拖死主线。",
        autostart=False,
    ),
    item(
        item_id="bailian_pro_routing_plan",
        title="OpenHuman-Athena-百炼Pro路由统一改造与分阶段执行方案",
        filename="OpenHuman-Athena-百炼Pro路由统一改造与分阶段执行方案.md",
        entry_stage="plan",
        risk_level="medium",
        unattended_allowed=False,
        priority="S2",
        lane="plan_auto",
        epic="athena_runtime",
        category="provider_routing",
        rationale="P0 之后继续推进 provider / model 单一事实源和路由统一时参考。",
    ),
    item(
        item_id="validation_moat_agents_plan",
        title="OpenHuman-Athena-Validation-Moat-agents重构方案",
        filename="OpenHuman-Athena-Validation-Moat-agents重构方案.md",
        entry_stage="plan",
        risk_level="medium",
        unattended_allowed=False,
        priority="S2",
        lane="plan_auto",
        epic="athena_runtime",
        category="validation_architecture",
        rationale="定义 Validation Moat 的完整 agents 版图和长期演化。",
    ),
    item(
        item_id="deerflow_harness_upgrade_plan",
        title="OpenHuman-Athena-deerflow2.0类Agent架构增量升级补全方案",
        filename="OpenHuman-Athena-deerflow2.0类Agent架构增量升级补全方案.md",
        entry_stage="plan",
        risk_level="medium",
        unattended_allowed=False,
        priority="S3",
        lane="plan_auto",
        epic="athena_capabilities",
        category="agent_harness_upgrade",
        rationale="用于中期增强 multi-agent harness，而不是先压进当前 build 自动链。",
    ),
    item(
        item_id="research_engine_local_mvp_plan",
        title="OpenHuman-Athena-Research-Engine-M4主脑本地MVP执行方案",
        filename="OpenHuman-Athena-Research-Engine-M4主脑本地MVP执行方案.md",
        entry_stage="plan",
        risk_level="medium",
        unattended_allowed=False,
        priority="S3",
        lane="plan_auto",
        epic="research_engine",
        category="local_research_engine",
        rationale="属于独立的 Research Engine 产品线，避免和当前控制面修复混跑。",
    ),
    item(
        item_id="athena_capability_alignment_plan",
        title="OpenHuman-Athena-能力对齐与分阶段执行方案",
        filename="OpenHuman-Athena-能力对齐与分阶段执行方案.md",
        entry_stage="plan",
        risk_level="medium",
        unattended_allowed=False,
        priority="S3",
        lane="plan_auto",
        epic="athena_capabilities",
        category="capability_alignment",
        rationale="保留为能力基线参考，不直接扔进当前自动 build 链。",
    ),
    item(
        item_id="codex_vscode_workflow_reference",
        title="OpenHuman-Athena-Codex-VSCode-智能执行工作流",
        filename="OpenHuman-Athena-Codex-VSCode-智能执行工作流.md",
        entry_stage="plan",
        risk_level="low",
        unattended_allowed=False,
        priority="S4",
        lane="reference_manual",
        epic="execution_foundation",
        category="workflow_reference",
        rationale="作为旧工作流的参考基线，对照新的 Execution Harness 继续校正。",
        autostart=False,
    ),
    item(
        item_id="athena_reality_roadmap",
        title="OpenHuman-Athena-现实版路线图",
        filename="OpenHuman-Athena-现实版路线图.md",
        entry_stage="research",
        risk_level="low",
        unattended_allowed=False,
        priority="S4",
        lane="research_manual",
        epic="openhuman_strategy",
        category="roadmap",
        rationale="属于长期路线图和战略校准，不进入自动执行链。",
        autostart=False,
    ),
    item(
        item_id="openhuman_mvp_scale_roadmap",
        title="OpenHuman-MVP-开源-政策-规模化增长路线图",
        filename="OpenHuman-MVP-开源-政策-规模化增长路线图.md",
        entry_stage="research",
        risk_level="low",
        unattended_allowed=False,
        priority="S4",
        lane="research_manual",
        epic="openhuman_strategy",
        category="roadmap",
        rationale="战略增长路线参考，保留在研究队列。",
        autostart=False,
    ),
    item(
        item_id="ai_market_intel_clean_room_plan",
        title="OpenHuman-AI市场情报与职业风险引擎-clean-room产品架构方案",
        filename="OpenHuman-AI市场情报与职业风险引擎-clean-room产品架构方案.md",
        entry_stage="research",
        risk_level="low",
        unattended_allowed=False,
        priority="S5",
        lane="research_manual",
        epic="market_intelligence",
        category="product_architecture",
        rationale="独立产品方向，放入研究 lane，不和当前 Athena 控制面修复抢时序。",
        autostart=False,
    ),
    item(
        item_id="karpathy_diagnostic_report",
        title="OpenHuman-Athena-autoresearch-Andrej-Karpathy五维灵魂拷问最优解报告",
        filename="OpenHuman-Athena-autoresearch-Andrej-Karpathy五维灵魂拷问最优解报告.md",
        entry_stage="research",
        risk_level="low",
        unattended_allowed=False,
        priority="S5",
        lane="research_manual",
        epic="openhuman_strategy",
        category="diagnostic_report",
        rationale="作为战略诊断输入，为后续 agents / validation moat 设计提供背景，不自动执行。",
        autostart=False,
    ),
    item(
        item_id="continue_checklist_reference",
        title="OpenHuman-继续推进清单-2026-03-26",
        filename="OpenHuman-继续推进清单-2026-03-26.md",
        entry_stage="plan",
        risk_level="low",
        unattended_allowed=False,
        priority="S6",
        lane="reference_manual",
        epic="openhuman_strategy",
        category="checklist",
        rationale="保留为历史推进清单参考，不直接进入自动执行。",
        autostart=False,
    ),
    item(
        item_id="openspace_engineering_plan_reference",
        title="OpenSpace工程集成实施方案",
        filename="OpenSpace工程集成实施方案.md",
        entry_stage="plan",
        risk_level="medium",
        unattended_allowed=False,
        priority="S2",
        lane="reference_manual",
        epic="openspace_integration",
        category="umbrella_reference",
        rationale="保留 OpenSpace 集成母文档作为总参考；真正自动执行的是已拆出的 adapter、metrics/sandbox、monitoring/audit 三张 build 卡和一张收口审计卡。",
        autostart=False,
    ),
    item(
        item_id="openhuman_24h_stress_plan_reference",
        title="Athena-Open Human系统24小时压力测试方案",
        filename="Athena-Open Human系统24小时压力测试方案.md",
        entry_stage="plan",
        risk_level="medium",
        unattended_allowed=False,
        priority="S1",
        lane="reference_manual",
        epic="stress_test",
        category="umbrella_reference",
        rationale="保留 24h 压测母文档作为总参考；真正自动执行的是已拆出的最佳态、runner、checkpoint 和审计卡。",
        autostart=False,
    ),
]


def manifest_items_from(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    items = payload.get("items")
    return items if isinstance(items, list) else []


def discovered_item_id(filename: str) -> str:
    stem = Path(filename).stem
    ascii_tokens = re.findall(r"[A-Za-z0-9]+", stem)
    slug = "_".join(token.lower() for token in ascii_tokens[:6]) or "doc"
    digest = hashlib.sha1(filename.encode("utf-8")).hexdigest()[:8]
    return f"{slug}_{digest}"


def discovered_item_for(filename: str) -> dict | None:
    title = Path(filename).stem
    if filename in DISCOVERY_SKIP_FILENAMES or filename.startswith("."):
        return None
    if title.endswith("VSCode执行指令"):
        return item(
            item_id=discovered_item_id(filename),
            title=title,
            filename=filename,
            entry_stage="build",
            risk_level="medium",
            unattended_allowed=True,
            priority="P3",
            lane="build_auto",
            epic="auto_discovered",
            category="auto_discovered_build",
            rationale="新增 VSCode 执行指令由 rebuild 自动识别进入 build_auto；如需更高优先级或依赖，再补 override。",
        )
    if title.endswith("Codex审计指令"):
        return item(
            item_id=discovered_item_id(filename),
            title=title,
            filename=filename,
            entry_stage="review",
            risk_level="medium",
            unattended_allowed=False,
            priority="R2",
            lane="review_auto",
            epic="auto_discovered",
            category="auto_discovered_review",
            rationale="新增 Codex 审计指令由 rebuild 自动识别进入 review_auto；默认等待依赖显式补齐。",
        )
    if any(keyword in title for keyword in ["路线图", "报告"]):
        return item(
            item_id=discovered_item_id(filename),
            title=title,
            filename=filename,
            entry_stage="research",
            risk_level="low",
            unattended_allowed=False,
            priority="S5",
            lane="research_manual",
            epic="auto_discovered",
            category="auto_discovered_research",
            rationale="新增报告/路线图默认进入 research_manual，避免误入自动执行链。",
            autostart=False,
        )
    if any(keyword in title for keyword in ["清单", "参考", "工作流"]):
        return item(
            item_id=discovered_item_id(filename),
            title=title,
            filename=filename,
            entry_stage="plan",
            risk_level="low",
            unattended_allowed=False,
            priority="S6",
            lane="reference_manual",
            epic="auto_discovered",
            category="auto_discovered_reference",
            rationale="新增清单/参考/工作流文档默认进入 reference_manual，先作为参考输入保留。",
            autostart=False,
        )
    if any(
        keyword in title
        for keyword in [
            "执行方案",
            "重构方案",
            "升级补全方案",
            "研究与跑通方案",
            "架构方案",
            "方案",
        ]
    ):
        return item(
            item_id=discovered_item_id(filename),
            title=title,
            filename=filename,
            entry_stage="plan",
            risk_level="medium",
            unattended_allowed=False,
            priority="S4",
            lane="plan_auto",
            epic="auto_discovered",
            category="auto_discovered_plan",
            rationale="新增方案文档由 rebuild 自动识别进入 plan_auto；如需改成 manual hold，可补 override。",
        )
    return None


def build_dynamic_item_groups() -> tuple[list[dict], list[dict], list[dict]]:
    build_items = list(BUILD_ITEMS)
    audit_items = list(AUDIT_ITEMS)
    plan_items = list(PLAN_ITEMS)

    known_ids = {entry["id"] for entry in build_items + audit_items + plan_items}
    known_filenames = {
        Path(str(entry["instruction_path"])).name
        for entry in build_items + audit_items + plan_items
    }

    for manifest_path, bucket in (
        (BUILD_QUEUE_PATH, build_items),
        (AUDIT_QUEUE_PATH, audit_items),
        (PLAN_QUEUE_PATH, plan_items),
    ):
        for entry in manifest_items_from(manifest_path):
            item_id = str(entry.get("id", "") or "")
            instruction_path = str(entry.get("instruction_path", "") or "")
            filename = Path(instruction_path).name
            if not item_id or not filename:
                continue
            resolved_path = Path(resolve_instruction_path(filename))
            if not resolved_path.exists():
                continue
            if item_id in known_ids or filename in known_filenames:
                continue
            entry = dict(entry)
            entry["instruction_path"] = str(resolved_path)
            bucket.append(entry)
            known_ids.add(item_id)
            known_filenames.add(filename)

    for path in sorted(PLAN_DIR.glob("*.md")):
        filename = path.name
        if filename in known_filenames:
            continue
        discovered = discovered_item_for(filename)
        if not discovered:
            continue
        stage = str(discovered.get("entry_stage", "") or "plan")
        if stage == "build":
            build_items.append(discovered)
        elif stage == "review":
            audit_items.append(discovered)
        else:
            plan_items.append(discovered)
        known_ids.add(str(discovered["id"]))
        known_filenames.add(filename)

    return build_items, audit_items, plan_items


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def build_queue_doc(title: str, items: list[dict], notes: str) -> dict:
    return {
        "queue_id": title,
        "name": title,
        "notes": notes,
        "items": items,
    }


def build_catalog(build_items: list[dict], audit_items: list[dict], plan_items: list[dict]) -> str:
    def render_group(header: str, items: list[dict]) -> list[str]:
        lines = [f"## {header}", ""]
        for entry in items:
            meta = entry["metadata"]
            lines.append(f"### {meta['priority']} · {entry['title']}")
            lines.append(f"- 队列 ID: `{entry['id']}`")
            lines.append(f"- 阶段: `{entry['entry_stage']}`")
            lines.append(f"- lane: `{meta['lane']}`")
            lines.append(f"- 风险: `{entry['risk_level']}`")
            if meta.get("autostart") is False:
                lines.append("- 自动执行: `否`，需人工点击“运行选中任务”或先拆分成更小 build 卡。")
            if meta.get("depends_on"):
                lines.append(f"- 依赖: `{', '.join(meta['depends_on'])}`")
            lines.append(
                f"- 文档: [{Path(entry['instruction_path']).name}]({entry['instruction_path']})"
            )
            lines.append(f"- 说明: {meta['rationale']}")
            lines.append("")
        return lines

    lines = [
        "# OpenHuman-AIPlan-全量优先级任务列队与智能执行工作流",
        "",
        "**生成时间**: 2026-03-28",
        f"**生成方式**: `{(Path('/Volumes/1TB-M2/openclaw/scripts/rebuild_aiplan_priority_queues.py'))}`",
        "**目标**: 把当前 `007-AI-plan` 里的内容从“文档堆积”收敛成“有优先级、有 lane、有执行规则”的统一任务系统。",
        "",
        "## 一句话原则",
        "",
        "- 先修执行地基，再扩 Athena 能力，再做审计收口，最后保留研究和路线图在 manual lane。",
        "- 自动执行链只允许真正的 `VS Code 执行指令` 进入，并且必须有明确依赖和验收边界。",
        "- `Codex审计`、路线图、方案、报告不再误入 build runner。",
        "",
        "## 智能工作流",
        "",
        "### Lane A · Auto Build",
        "- 只容纳真实 `VS Code 执行指令`。",
        "- 严格按优先级和依赖串行执行。",
        "- WIP 固定为 1，防止 OpenCode 同时吞多张大卡。",
        "- 当前目标是先把 execution harness 和 runtime 修稳，再推进 Athena 能力项。",
        "- 跨系统重连或范围明显过宽的 build 卡会保留在 build 目录里，但默认 `autostart=false`，先手动拉起或继续拆小。",
        "",
        "### Lane B · Codex Audit",
        "- 只容纳审计指令。",
        "- 必须等待对应 build lane 任务完成后再进入。",
        "- 由独立的 Codex review runner 自动消费，不再停在人工待处理。",
        "",
        "### Lane C · Auto Plan",
        "- 由 Codex plan runner 自动消费可执行策划卡。",
        "- 目标是把“策划文档”尽量编译成后续 build/review 卡，而不是停在人工阅读层。",
        "- `autostart=false` 的研究/参考项仍会保留在队列中，但会显示为手动保留，不参与自动推进。",
        "",
        "## 优先级规则",
        "",
        "- `P0`: 执行地基与运行时修复。没有它们，任何功能队列都不可靠。",
        "- `P1`: Athena 控制面地基。包括 schema、HITL、Dispatch 和 Validation Moat。",
        "- `P2`: 能力面扩张。包括沟通契约、skill 接线、software executor 增量。",
        "- `R*`: Codex 审计收口。",
        "- `S*`: 规划 / 研究 / 路线图，进入 manual lane。",
        "",
    ]
    lines.extend(render_group("Auto Build Queue", build_items))
    lines.extend(render_group("Codex Audit Queue", audit_items))
    lines.extend(render_group("Plan / Research Queue", plan_items))
    lines.extend(
        [
            "## 当前执行策略",
            "",
            "- `.athena-auto-queue.json` 允许 `runner_mode=opencode_build`、`runner_mode=codex_review` 与 `runner_mode=codex_plan` 进入自动执行。",
            "- `autostart=false` 的 research/reference 项会保留在同一事实源内，但不强行进入自动推进。",
            "- 如需新增任务，必须先明确它属于哪条 lane，再决定是否允许自动运行。",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def summarize_state(
    manifest_items: list[dict], synced_items: dict[str, dict]
) -> tuple[dict[str, int], str]:
    counts = {
        "pending": 0,
        "running": 0,
        "completed": 0,
        "failed": 0,
        "manual_hold": 0,
    }
    item_by_id: dict[str, dict] = {}
    for entry in manifest_items:
        item_id = str(entry.get("id", "") or "")
        if not item_id:
            continue
        item_by_id[item_id] = entry
        state_item = synced_items.get(item_id, {})
        status = str(state_item.get("status", "") or "pending")
        counts[status] = counts.get(status, 0) + 1

    pending_ids = [
        item_id
        for item_id, state_item in synced_items.items()
        if str(state_item.get("status", "") or "pending") == "pending"
    ]
    running_ids = [
        item_id
        for item_id, state_item in synced_items.items()
        if str(state_item.get("status", "") or "") == "running"
    ]
    manual_hold_ids = [
        item_id
        for item_id, state_item in synced_items.items()
        if str(state_item.get("status", "") or "") == "manual_hold"
    ]

    if not pending_ids and not running_ids:
        return counts, "manual_hold" if manual_hold_ids else "empty"
    if running_ids:
        return counts, "running"

    blocked = False
    for item_id in pending_ids:
        manifest_item = item_by_id.get(item_id, {})
        metadata = manifest_item.get("metadata", {})
        depends_on = metadata.get("depends_on", []) if isinstance(metadata, dict) else []
        for dep_id in depends_on:
            dep_item = synced_items.get(str(dep_id), {})
            if str(dep_item.get("status", "") or "") != "completed":
                blocked = True
                break
        if blocked:
            break
    if blocked:
        return counts, "dependency_blocked"
    return counts, "no_consumer"


def sync_queue_state(queue_id: str, queue_name: str, manifest_items: list[dict]) -> None:
    state_path = QUEUE_STATE_DIR / f"{queue_id}.json"
    existing = {}
    if state_path.exists():
        try:
            existing = json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
    existing_items = existing.get("items") if isinstance(existing.get("items"), dict) else {}
    synced_items: dict[str, dict] = {}
    current_item_id = str(existing.get("current_item_id", "") or "")
    current_item_ids = existing.get("current_item_ids")
    current_item_ids = (
        [str(item_id) for item_id in current_item_ids if isinstance(item_id, str)]
        if isinstance(current_item_ids, list)
        else []
    )

    for entry in manifest_items:
        item_id = str(entry["id"])
        meta = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
        state_item = dict(existing_items.get(item_id, {}))
        state_item.setdefault("title", entry["title"])
        state_item.setdefault("stage", entry["entry_stage"])
        state_item.setdefault("instruction_path", entry["instruction_path"])
        if "status" not in state_item:
            state_item["status"] = "pending"
        if "progress_percent" not in state_item:
            state_item["progress_percent"] = 0
        if "summary" not in state_item:
            state_item["summary"] = "等待队列 runner 接手。"
        if meta.get("autostart") is False and state_item.get("status") != "completed":
            state_item.update(
                {
                    "status": "manual_hold",
                    "progress_percent": 0,
                    "summary": "当前设为手动保留，不进入自动 runner；如需推进，请先继续拆卡或明确转入自动链。",
                    "error": "",
                    "finished_at": "",
                    "pipeline_summary": "manual_hold",
                    "runner_pid": "",
                    "runner_heartbeat_at": "",
                }
            )
            if current_item_id == item_id:
                current_item_id = ""
        synced_items[item_id] = state_item

    payload = {
        "queue_id": queue_id,
        "name": queue_name,
        "current_item_id": current_item_id if current_item_id in synced_items else "",
        "current_item_ids": [item_id for item_id in current_item_ids if item_id in synced_items],
        "updated_at": now_iso(),
        "items": synced_items,
    }
    counts, queue_status = summarize_state(manifest_items, synced_items)
    payload["counts"] = counts
    payload["queue_status"] = queue_status
    write_json(state_path, payload)


def main() -> None:
    build_items, audit_items, plan_items = build_dynamic_item_groups()

    build_manifest = build_queue_doc(
        "OpenHuman AIPlan 优先执行队列",
        build_items,
        "Generated by rebuild_aiplan_priority_queues.py",
    )
    build_manifest["queue_id"] = "openhuman_aiplan_build_priority_20260328"

    audit_manifest = build_queue_doc(
        "OpenHuman AIPlan Codex审计队列",
        audit_items,
        "Generated by rebuild_aiplan_priority_queues.py",
    )
    audit_manifest["queue_id"] = "openhuman_aiplan_codex_audit_20260328"

    plan_manifest = build_queue_doc(
        "OpenHuman AIPlan 自动策划队列",
        plan_items,
        "Generated by rebuild_aiplan_priority_queues.py",
    )
    plan_manifest["queue_id"] = "openhuman_aiplan_plan_manual_20260328"

    write_json(BUILD_QUEUE_PATH, build_manifest)
    write_json(AUDIT_QUEUE_PATH, audit_manifest)
    write_json(PLAN_QUEUE_PATH, plan_manifest)

    config = {
        "plan_dir": str(PLAN_DIR),
        "poll_seconds": 15,
        "exclude_dirs": ["completed"],
        "archive_dir": str(ARCHIVE_DIR),
        "routes": [
            {
                "route_id": "aiplan_build_auto",
                "manifest_path": str(BUILD_QUEUE_PATH),
                "queue_id": build_manifest["queue_id"],
                "name": build_manifest["name"],
                "runner_mode": "opencode_build",
                "defaults": {
                    "entry_stage": "build",
                    "risk_level": "medium",
                    "unattended_allowed": True,
                    "targets": [],
                    "metadata": {
                        "epic": "openhuman_aiplan_build_priority",
                    },
                },
            },
            {
                "route_id": "aiplan_codex_audit",
                "manifest_path": str(AUDIT_QUEUE_PATH),
                "queue_id": audit_manifest["queue_id"],
                "name": audit_manifest["name"],
                "runner_mode": "codex_review",
                "defaults": {
                    "entry_stage": "review",
                    "risk_level": "medium",
                    "unattended_allowed": False,
                    "targets": [],
                    "metadata": {
                        "epic": "openhuman_aiplan_codex_audit",
                    },
                },
            },
            {
                "route_id": "aiplan_plan_auto",
                "manifest_path": str(PLAN_QUEUE_PATH),
                "queue_id": plan_manifest["queue_id"],
                "name": plan_manifest["name"],
                "runner_mode": "codex_plan",
                "defaults": {
                    "entry_stage": "plan",
                    "risk_level": "medium",
                    "unattended_allowed": False,
                    "targets": [],
                    "metadata": {
                        "epic": "openhuman_aiplan_plan_manual",
                    },
                },
            },
        ],
    }
    write_json(CONFIG_PATH, config)
    CATALOG_PATH.write_text(build_catalog(build_items, audit_items, plan_items), encoding="utf-8")
    sync_queue_state(build_manifest["queue_id"], build_manifest["name"], build_items)
    sync_queue_state(audit_manifest["queue_id"], audit_manifest["name"], audit_items)
    sync_queue_state(plan_manifest["queue_id"], plan_manifest["name"], plan_items)
    print("Rebuilt AI plan priority queues and catalog.")
    print(BUILD_QUEUE_PATH)
    print(AUDIT_QUEUE_PATH)
    print(PLAN_QUEUE_PATH)
    print(CATALOG_PATH)


if __name__ == "__main__":
    main()
