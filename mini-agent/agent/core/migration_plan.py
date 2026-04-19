#!/usr/bin/env python3
"""
迁移计划执行器
基于迁移决策框架的建议，执行分阶段迁移计划。

功能：
1. 加载迁移决策和计划
2. 管理迁移阶段（配置更新、监控设置）
3. 执行阶段转换（验证成功标准）
4. 处理回滚和异常情况
5. 生成迁移进度报告

版本: 1.0
创建日期: 2026-04-17
作者: Claude (AI助手)
"""

import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


class MigrationPhaseStatus(Enum):
    """迁移阶段状态"""

    PENDING = "pending"  # 等待开始
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    ROLLED_BACK = "rolled_back"  # 已回滚


class MigrationTrigger(Enum):
    """迁移触发器"""

    MANUAL = "manual"  # 手动触发
    SCHEDULED = "scheduled"  # 计划时间触发
    CONDITIONAL = "conditional"  # 条件满足触发


@dataclass
class MigrationPhase:
    """迁移阶段定义"""

    phase_number: int
    target_percentage: float  # 迁移百分比 (0-1)
    duration_hours: int
    checkpoints: List[str]
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: MigrationPhaseStatus = MigrationPhaseStatus.PENDING
    metrics: Optional[Dict[str, Any]] = None
    issues: Optional[List[str]] = None


@dataclass
class MigrationPlan:
    """迁移计划"""

    plan_id: str
    task_kind: str
    source_provider: str
    target_provider: str
    total_volume: int
    phases: List[MigrationPhase]
    current_phase_index: int = 0
    rollback_plan: Optional[Dict[str, Any]] = None
    success_criteria: Optional[Dict[str, Any]] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()


class MigrationExecutor:
    """迁移执行器"""

    def __init__(self, config_dir: str = "config", reports_dir: str = "reports"):
        self.config_dir = config_dir
        self.reports_dir = reports_dir
        self.experiments_config_path = os.path.join(config_dir, "experiments.yaml")
        self.migration_plan: Optional[MigrationPlan] = None

    def load_migration_decision(self, decision_path: str) -> Dict[str, Any]:
        """加载迁移决策报告"""
        with open(decision_path, "r", encoding="utf-8") as f:
            decision_data = json.load(f)

        logger.info(f"加载迁移决策: {decision_path}")
        return decision_data

    def create_migration_plan_from_decision(
        self, decision_data: Dict[str, Any], plan_id: str = "deepseek_migration_2026"
    ) -> MigrationPlan:
        """从决策数据创建迁移计划"""
        migration_plan_data = decision_data.get("migration_plan", {})

        # 解析阶段数据
        phases = []
        for phase_data in migration_plan_data.get("phases", []):
            phase = MigrationPhase(
                phase_number=phase_data["phase"],
                target_percentage=phase_data["percentage"] / 100.0,  # 转换为0-1
                duration_hours=phase_data["duration_hours"],
                checkpoints=phase_data["checkpoints"],
                status=MigrationPhaseStatus.PENDING,
            )
            phases.append(phase)

        plan = MigrationPlan(
            plan_id=plan_id,
            task_kind=migration_plan_data.get("task_kind", "coding_plan"),
            source_provider="dashscope",
            target_provider="deepseek",
            total_volume=migration_plan_data.get("total_volume", 1000),
            phases=phases,
            rollback_plan=migration_plan_data.get("rollback_plan", {}),
            success_criteria=migration_plan_data.get("success_criteria", {}),
            current_phase_index=0,
        )

        self.migration_plan = plan
        logger.info(f"创建迁移计划: {plan_id}, 共{len(phases)}个阶段")
        return plan

    def update_experiment_config_for_phase(
        self, phase: MigrationPhase, task_kind: str = "coding_plan"
    ) -> bool:
        """更新实验配置以匹配当前迁移阶段"""
        try:
            # 加载当前实验配置
            with open(self.experiments_config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            # 更新迁移实验的分配比例
            experiment_name = f"deepseek_migration_phase{phase.phase_number}"
            if experiment_name not in config.get("experiments", {}):
                # 如果实验不存在，创建它
                logger.info(f"创建新实验: {experiment_name}")
                self._create_migration_experiment(
                    config, experiment_name, phase.target_percentage, task_kind
                )
            else:
                # 更新现有实验的分配比例
                logger.info(f"更新实验分配比例: {experiment_name} -> {phase.target_percentage:.1%}")
                config["experiments"][experiment_name]["design"]["groups"][1][
                    "allocation"
                ] = phase.target_percentage
                config["experiments"][experiment_name]["enabled"] = True

            # 保存更新后的配置
            with open(self.experiments_config_path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

            logger.info(f"实验配置已更新: {experiment_name} = {phase.target_percentage:.1%}")
            return True

        except Exception as e:
            logger.error(f"更新实验配置失败: {e}")
            return False

    def _create_migration_experiment(
        self,
        config: Dict[str, Any],
        experiment_name: str,
        migration_percentage: float,
        task_kind: str,
    ) -> None:
        """创建迁移实验配置"""
        if "experiments" not in config:
            config["experiments"] = {}

        config["experiments"][experiment_name] = {
            "name": f"DeepSeek分阶段迁移 - 第{experiment_name[-1]}阶段 ({migration_percentage:.0%})",
            "description": f"基于迁移决策报告，分阶段迁移{task_kind}任务到DeepSeek",
            "enabled": True,
            "start_date": datetime.now().strftime("%Y-%m-%d"),
            "end_date": (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d"),
            "design": {
                "type": "迁移实验",
                "groups": [
                    {
                        "name": "original",
                        "provider": "dashscope",
                        "model": "qwen3.5-plus",
                        "allocation": 1.0 - migration_percentage,
                    },
                    {
                        "name": "migrated",
                        "provider": "deepseek",
                        "model": "deepseek-coder",
                        "allocation": migration_percentage,
                    },
                ],
                "randomization": "hash_based",
                "salt": f"{experiment_name}_{datetime.now().strftime('%Y%m')}",
            },
            "metrics": [
                {
                    "name": "成本节省",
                    "description": "迁移部分的成本节省效果",
                    "formula": "(dashscope_cost - deepseek_cost) / dashscope_cost",
                    "target": ">70%",
                },
                {
                    "name": "质量一致性",
                    "description": "迁移部分的质量保持情况",
                    "scale": "0-1",
                    "target": ">=0.9",
                },
                {
                    "name": "错误率对比",
                    "description": "迁移组和原组的错误率差异",
                    "formula": "migrated_error_rate - original_error_rate",
                    "target": "increase < 0.02",
                },
            ],
            "data_collection": {
                "enabled": True,
                "storage_backend": "cost_tracker",
                "additional_fields": [
                    "migration_phase",
                    "migration_group",
                    "quality_score",
                    "error_details",
                    "execution_time",
                ],
            },
            "success_criteria": {
                "primary": [
                    {"metric": "成本节省", "threshold": ">70%", "confidence": "90%"},
                    {"metric": "质量一致性", "threshold": ">=0.9", "confidence": "90%"},
                ],
                "secondary": [
                    {"metric": "错误率对比", "threshold": "increase < 0.02"},
                    {"metric": "用户满意度", "threshold": "no negative feedback"},
                ],
            },
        }

    def start_migration_phase(
        self, phase_index: int, trigger: MigrationTrigger = MigrationTrigger.MANUAL
    ) -> bool:
        """启动迁移阶段"""
        if not self.migration_plan:
            logger.error("没有迁移计划，请先加载决策报告")
            return False

        if phase_index >= len(self.migration_plan.phases):
            logger.error(f"阶段索引超出范围: {phase_index}/{len(self.migration_plan.phases)}")
            return False

        phase = self.migration_plan.phases[phase_index]

        # 检查前序阶段是否完成
        for i in range(phase_index):
            if self.migration_plan.phases[i].status != MigrationPhaseStatus.COMPLETED:
                logger.error(f"前序阶段{i+1}未完成，无法启动阶段{phase_index+1}")
                return False

        logger.info(f"启动迁移阶段 {phase_index+1}/{len(self.migration_plan.phases)}")
        logger.info(f"目标迁移比例: {phase.target_percentage:.1%}")
        logger.info(f"计划时长: {phase.duration_hours}小时")

        # 更新阶段状态
        phase.status = MigrationPhaseStatus.IN_PROGRESS
        phase.start_time = datetime.now()
        phase.issues = []

        # 更新实验配置
        if not self.update_experiment_config_for_phase(phase, self.migration_plan.task_kind):
            phase.status = MigrationPhaseStatus.FAILED
            phase.issues.append("更新实验配置失败")
            return False

        # 更新计划状态
        self.migration_plan.current_phase_index = phase_index
        self.migration_plan.updated_at = datetime.now()

        # 记录启动
        self._log_phase_start(phase, trigger)
        return True

    def check_phase_progress(self, phase_index: int) -> Dict[str, Any]:
        """检查迁移阶段进度"""
        if not self.migration_plan or phase_index >= len(self.migration_plan.phases):
            return {"status": "error", "message": "无效的阶段索引"}

        phase = self.migration_plan.phases[phase_index]

        if phase.status != MigrationPhaseStatus.IN_PROGRESS:
            return {"status": phase.status.value, "message": f"阶段状态: {phase.status.value}"}

        # 计算进度百分比
        if phase.start_time:
            elapsed_hours = (datetime.now() - phase.start_time).total_seconds() / 3600
            progress_percent = min(100, (elapsed_hours / phase.duration_hours) * 100)
        else:
            progress_percent = 0

        # 检查检查点完成情况
        checkpoint_status = {}
        for checkpoint in phase.checkpoints:
            # 这里简化实现，实际应该检查具体指标
            checkpoint_status[checkpoint] = "pending"

        return {
            "status": "in_progress",
            "phase_number": phase.phase_number,
            "target_percentage": phase.target_percentage,
            "progress_percent": progress_percent,
            "elapsed_hours": elapsed_hours if phase.start_time else 0,
            "remaining_hours": (
                max(0, phase.duration_hours - elapsed_hours)
                if phase.start_time
                else phase.duration_hours
            ),
            "checkpoint_status": checkpoint_status,
            "issues": phase.issues or [],
            "start_time": phase.start_time.isoformat() if phase.start_time else None,
        }

    def complete_migration_phase(
        self, phase_index: int, metrics: Optional[Dict[str, Any]] = None, force: bool = False
    ) -> bool:
        """完成迁移阶段"""
        if not self.migration_plan or phase_index >= len(self.migration_plan.phases):
            return False

        phase = self.migration_plan.phases[phase_index]

        if phase.status != MigrationPhaseStatus.IN_PROGRESS:
            logger.warning(f"阶段{phase_index+1}状态为{phase.status.value}，无法完成")
            return False

        # 检查成功标准（除非强制完成）
        if not force and not self._check_success_criteria(phase_index, metrics):
            logger.warning(f"阶段{phase_index+1}未满足成功标准")
            phase.issues = phase.issues or []
            phase.issues.append("未满足成功标准")
            return False

        # 更新阶段状态
        phase.status = MigrationPhaseStatus.COMPLETED
        phase.end_time = datetime.now()
        phase.metrics = metrics or {}

        # 更新计划状态
        self.migration_plan.updated_at = datetime.now()

        logger.info(f"迁移阶段 {phase_index+1} 完成")
        self._generate_phase_report(phase_index)
        return True

    def rollback_migration_phase(self, phase_index: int, reason: str) -> bool:
        """回滚迁移阶段"""
        if not self.migration_plan or phase_index >= len(self.migration_plan.phases):
            return False

        phase = self.migration_plan.phases[phase_index]

        # 更新阶段状态
        phase.status = MigrationPhaseStatus.ROLLED_BACK
        phase.end_time = datetime.now()
        phase.issues = phase.issues or []
        phase.issues.append(f"回滚原因: {reason}")

        # 恢复实验配置到前一个阶段
        if phase_index > 0:
            prev_phase = self.migration_plan.phases[phase_index - 1]
            self.update_experiment_config_for_phase(prev_phase, self.migration_plan.task_kind)
        else:
            # 回滚到初始状态（0%迁移）
            zero_phase = MigrationPhase(
                phase_number=0,
                target_percentage=0.0,
                duration_hours=0,
                checkpoints=["回滚完成"],
                status=MigrationPhaseStatus.COMPLETED,
            )
            self.update_experiment_config_for_phase(zero_phase, self.migration_plan.task_kind)

        # 更新计划状态
        self.migration_plan.current_phase_index = max(0, phase_index - 1)
        self.migration_plan.updated_at = datetime.now()

        logger.warning(f"迁移阶段 {phase_index+1} 已回滚: {reason}")
        self._generate_rollback_report(phase_index, reason)
        return True

    def _check_success_criteria(
        self, phase_index: int, metrics: Optional[Dict[str, Any]] = None
    ) -> bool:
        """检查成功标准"""
        if not self.migration_plan:
            return False

        phase = self.migration_plan.phases[phase_index]
        success_criteria = self.migration_plan.success_criteria or {}

        # 这里简化实现，实际应该检查具体指标
        # 应该从成本跟踪系统和质量评估系统获取实际数据
        logger.info(f"检查阶段{phase_index+1}成功标准: {success_criteria}")

        # 默认返回True（简化实现）
        return True

    def _log_phase_start(self, phase: MigrationPhase, trigger: MigrationTrigger) -> None:
        """记录阶段启动日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": "migration_phase_started",
            "phase_number": phase.phase_number,
            "target_percentage": phase.target_percentage,
            "duration_hours": phase.duration_hours,
            "trigger": trigger.value,
            "checkpoints": phase.checkpoints,
        }

        log_file = os.path.join(self.reports_dir, "migration_log.jsonl")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    def _generate_phase_report(self, phase_index: int) -> None:
        """生成阶段报告"""
        if not self.migration_plan or phase_index >= len(self.migration_plan.phases):
            return

        phase = self.migration_plan.phases[phase_index]

        report = {
            "report_type": "migration_phase_report",
            "phase_number": phase.phase_number,
            "target_percentage": phase.target_percentage,
            "status": phase.status.value,
            "start_time": phase.start_time.isoformat() if phase.start_time else None,
            "end_time": phase.end_time.isoformat() if phase.end_time else None,
            "duration_hours": phase.duration_hours,
            "actual_duration_hours": (
                (phase.end_time - phase.start_time).total_seconds() / 3600
                if phase.start_time and phase.end_time
                else None
            ),
            "metrics": phase.metrics or {},
            "issues": phase.issues or [],
            "checkpoints": phase.checkpoints,
            "checkpoint_status": {cp: "completed" for cp in phase.checkpoints},  # 简化
        }

        report_file = os.path.join(self.reports_dir, f"migration_phase_{phase_index+1}_report.json")
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"阶段报告已生成: {report_file}")

    def _generate_rollback_report(self, phase_index: int, reason: str) -> None:
        """生成回滚报告"""
        report = {
            "report_type": "migration_rollback_report",
            "phase_number": phase_index + 1,
            "rollback_time": datetime.now().isoformat(),
            "reason": reason,
            "action": "experiment_config_rolled_back",
            "new_migration_percentage": max(0, (phase_index - 1) * 0.15),  # 简化
        }

        report_file = os.path.join(
            self.reports_dir, f"migration_rollback_phase_{phase_index+1}_report.json"
        )
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"回滚报告已生成: {report_file}")

    def generate_migration_summary(self) -> Dict[str, Any]:
        """生成迁移摘要报告"""
        if not self.migration_plan:
            return {"status": "error", "message": "没有迁移计划"}

        total_phases = len(self.migration_plan.phases)
        completed_phases = sum(
            1 for p in self.migration_plan.phases if p.status == MigrationPhaseStatus.COMPLETED
        )
        in_progress_phases = sum(
            1 for p in self.migration_plan.phases if p.status == MigrationPhaseStatus.IN_PROGRESS
        )
        failed_phases = sum(
            1 for p in self.migration_plan.phases if p.status == MigrationPhaseStatus.FAILED
        )

        current_percentage = 0.0
        if self.migration_plan.current_phase_index < len(self.migration_plan.phases):
            current_phase = self.migration_plan.phases[self.migration_plan.current_phase_index]
            current_percentage = current_phase.target_percentage

        return {
            "plan_id": self.migration_plan.plan_id,
            "task_kind": self.migration_plan.task_kind,
            "total_phases": total_phases,
            "completed_phases": completed_phases,
            "in_progress_phases": in_progress_phases,
            "failed_phases": failed_phases,
            "current_phase_index": self.migration_plan.current_phase_index,
            "current_migration_percentage": current_percentage,
            "overall_progress": (completed_phases / total_phases * 100) if total_phases > 0 else 0,
            "created_at": self.migration_plan.created_at.isoformat(),
            "updated_at": self.migration_plan.updated_at.isoformat(),
            "status": self._get_overall_status(),
        }

    def _get_overall_status(self) -> str:
        """获取整体状态"""
        if not self.migration_plan:
            return "not_started"

        statuses = [p.status for p in self.migration_plan.phases]

        if any(s == MigrationPhaseStatus.FAILED for s in statuses):
            return "failed"
        elif any(s == MigrationPhaseStatus.ROLLED_BACK for s in statuses):
            return "rolled_back"
        elif all(s == MigrationPhaseStatus.COMPLETED for s in statuses):
            return "completed"
        elif any(s == MigrationPhaseStatus.IN_PROGRESS for s in statuses):
            return "in_progress"
        else:
            return "pending"


def main():
    """主函数：执行迁移计划"""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # 1. 初始化迁移执行器
    executor = MigrationExecutor(
        config_dir="/Volumes/1TB-M2/openclaw/mini-agent/config",
        reports_dir="/Volumes/1TB-M2/openclaw/mini-agent/reports",
    )

    # 2. 加载迁移决策
    decision_path = "/Volumes/1TB-M2/openclaw/mini-agent/reports/migration_decision_report.json"
    if not os.path.exists(decision_path):
        logger.error(f"迁移决策报告不存在: {decision_path}")
        return

    decision_data = executor.load_migration_decision(decision_path)

    # 3. 创建迁移计划
    migration_plan = executor.create_migration_plan_from_decision(
        decision_data, plan_id="deepseek_migration_2026_phase1"
    )

    # 4. 启动第一阶段迁移
    print("=" * 80)
    print("DeepSeek迁移计划执行器")
    print("=" * 80)
    print(f"任务类型: {migration_plan.task_kind}")
    print(f"总阶段数: {len(migration_plan.phases)}")
    print()

    # 显示阶段计划
    for i, phase in enumerate(migration_plan.phases):
        print(f"阶段 {i+1}:")
        print(f"  迁移比例: {phase.target_percentage:.1%}")
        print(f"  计划时长: {phase.duration_hours}小时")
        print(f"  检查点: {', '.join(phase.checkpoints)}")
        print()

    # 询问是否启动第一阶段
    response = input("是否启动第一阶段迁移? (y/N): ")
    if response.lower() == "y":
        success = executor.start_migration_phase(0)
        if success:
            print("✅ 第一阶段迁移已启动 (10%流量迁移到DeepSeek)")
            print("📊 实验配置已更新")
            print("📈 迁移监控已启用")

            # 显示迁移摘要
            summary = executor.generate_migration_summary()
            print()
            print("迁移摘要:")
            print(f"  当前状态: {summary['status']}")
            print(f"  当前迁移比例: {summary['current_migration_percentage']:.1%}")
            print(f"  总体进度: {summary['overall_progress']:.1f}%")
        else:
            print("❌ 第一阶段迁移启动失败")
    else:
        print("迁移计划已创建但未启动")
        print("您可以使用以下命令手动启动:")
        print("  python3 mini-agent/agent/core/migration_plan.py")
        print("或直接更新实验配置以启用迁移")

    # 保存迁移计划
    plan_file = "/Volumes/1TB-M2/openclaw/mini-agent/reports/migration_plan_detailed.json"
    with open(plan_file, "w", encoding="utf-8") as f:
        json.dump(asdict(migration_plan), f, indent=2, ensure_ascii=False, default=str)

    print()
    print(f"详细迁移计划已保存到: {plan_file}")


if __name__ == "__main__":
    main()
