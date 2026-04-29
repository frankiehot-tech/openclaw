#!/usr/bin/env python3
"""
Athena Auto Repair Router - 自动修复桥接器

将 repairable incident 桥接到 Athena 执行通道，提供幂等入队与映射记录。
支持 athena_runtime_problem 和 m4_health_problem 两类问题的自动修复。
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 尝试导入 Athena 组件
IMPORT_SUCCESS = False
try:
    # 添加 mini-agent 目录到路径
    mini_agent_path = project_root / "mini-agent"
    if str(mini_agent_path) not in sys.path:
        sys.path.insert(0, str(mini_agent_path))

    from agent.core.athena_orchestrator import get_orchestrator

    from scripts.workflow_state import (
        INCIDENT_STATE_DETECTED,
        INCIDENT_STATE_FAILED,
        INCIDENT_STATE_QUEUED,
        get_incident_state,
        get_task_for_incident,
        record_incident_detected,
        record_incident_task,
        set_incident_state,
        update_incident_state_from_task,
    )

    IMPORT_SUCCESS = True
    print("✅ Athena 组件导入成功")
except ImportError as e:
    print(f"导入 Athena 组件失败: {e}")
    print("请确保在项目根目录运行")
    IMPORT_SUCCESS = False

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class IncidentRouter:
    """Incident 路由处理器"""

    # 支持的 incident 类别
    SUPPORTED_CATEGORIES = {
        "athena_runtime_problem": {
            "domain": "engineering",
            "stage": "build",
            "description_template": "修复 Athena 运行时问题: {summary}",
        },
        "m4_health_problem": {
            "domain": "engineering",
            "stage": "build",
            "description_template": "修复 M4 健康问题: {summary}",
        },
    }

    # 高风险 severity 列表（不自动修复）
    HIGH_RISK_SEVERITIES = {"high", "critical"}

    def __init__(self):
        self.orchestrator = get_orchestrator() if IMPORT_SUCCESS else None

    def validate_incident(self, incident: dict[str, Any]) -> tuple[bool, str]:
        """验证 incident 是否适合自动修复"""
        # 1. 必需字段检查
        required_fields = ["id", "category", "severity", "repairable", "summary"]
        for field in required_fields:
            if field not in incident:
                return False, f"incident 缺少必需字段: {field}"

        # 2. 是否可修复
        if not incident.get("repairable", False):
            return False, "incident 标记为不可修复 (repairable=false)"

        # 3. 风险等级检查
        severity = incident.get("severity", "").lower()
        if severity in self.HIGH_RISK_SEVERITIES:
            return False, f"高风险 severity ({severity}) 不自动修复"

        # 4. 类别支持检查
        category = incident.get("category", "")
        if category not in self.SUPPORTED_CATEGORIES:
            return False, f"不支持的 incident 类别: {category}"

        # 5. 修复流程检查
        repair_flow = incident.get("repair_flow", "")
        if repair_flow == "manual_intervention":
            return False, "修复流程需要人工介入"

        return True, "验证通过"

    def check_duplicate(self, incident_id: str) -> tuple[bool, str | None]:
        """检查 incident 是否已有对应任务"""
        existing_task_id = get_task_for_incident(incident_id)
        if existing_task_id:
            return True, existing_task_id
        return False, None

    def create_repair_task(self, incident: dict[str, Any]) -> tuple[bool, str, dict | None]:
        """为 incident 创建修复任务"""
        if not self.orchestrator:
            return False, "Athena orchestrator 不可用", None

        category = incident["category"]
        category_config = self.SUPPORTED_CATEGORIES[category]

        # 构建任务描述
        description = category_config["description_template"].format(summary=incident["summary"])

        # 添加 incident 详情到上下文
        context = {
            "dispatch_source": "auto_repair_router",
            "incident_id": incident["id"],
            "incident_category": category,
            "incident_severity": incident["severity"],
            "incident_details": incident.get("details", {}),
        }

        try:
            success, task_id_or_error, metadata = self.orchestrator.create_task(
                stage=category_config["stage"],
                domain=category_config["domain"],
                description=description,
                dispatch_source=context["dispatch_source"],
                dispatch_thread_id=incident["id"],
            )

            if not success:
                return False, f"创建任务失败: {task_id_or_error}", None

            task_id = task_id_or_error
            logger.info(f"为 incident {incident['id']} 创建修复任务: {task_id}")
            return True, task_id, metadata

        except Exception as e:
            logger.error(f"创建修复任务时异常: {e}", exc_info=True)
            return False, f"创建任务异常: {str(e)}", None

    def route_incident(self, incident_path: Path) -> tuple[bool, str, dict | None]:
        """路由 incident 到修复通道"""
        # 1. 加载 incident
        try:
            with open(incident_path, encoding="utf-8") as f:
                incident = json.load(f)
        except Exception as e:
            return False, f"加载 incident 文件失败: {e}", None

        incident_id = incident.get("id", "unknown")
        logger.info(f"处理 incident: {incident_id}")

        try:
            record_incident_detected(
                incident,
                metadata={
                    "router_action": "incident_loaded",
                    "timestamp": datetime.now().isoformat(),
                },
            )
        except Exception as e:
            logger.error(f"记录 detected 状态失败: {e}")

        # 2. 验证 incident
        valid, reason = self.validate_incident(incident)
        if not valid:
            logger.info(f"incident {incident_id} 验证失败: {reason}")
            return False, reason, None

        # 3. 幂等检查
        is_duplicate, existing_task_id = self.check_duplicate(incident_id)
        if is_duplicate:
            logger.info(f"incident {incident_id} 已有对应任务: {existing_task_id}")
            # 确保 incident 有状态
            try:
                current_state = get_incident_state(incident_id)
                current_state_value = (
                    current_state.get("state") if isinstance(current_state, dict) else None
                )
                if not current_state or current_state_value == INCIDENT_STATE_DETECTED:
                    # 尝试根据任务状态更新
                    updated = update_incident_state_from_task(existing_task_id, incident_id)
                    if not updated:
                        # 任务状态未知，设置为 queued
                        set_incident_state(
                            incident_id,
                            INCIDENT_STATE_QUEUED,
                            {
                                "task_id": existing_task_id,
                                "reason": "duplicate_with_unknown_status",
                            },
                        )
            except Exception as e:
                logger.error(f"更新重复 incident 状态失败: {e}")
            return (
                False,
                f"incident 已有对应任务: {existing_task_id}",
                {"task_id": existing_task_id},
            )

        # 4. 创建修复任务
        success, task_id_or_error, metadata = self.create_repair_task(incident)
        if not success:
            try:
                set_incident_state(
                    incident_id,
                    INCIDENT_STATE_FAILED,
                    {
                        "error": task_id_or_error,
                        "router_action": "task_create_failed",
                        "timestamp": datetime.now().isoformat(),
                    },
                )
            except Exception as e:
                logger.error(f"设置 incident 失败状态失败: {e}")
            return False, task_id_or_error, None

        task_id = task_id_or_error

        # 5. 记录映射
        try:
            record_incident_task(incident_id, task_id)
            logger.info(f"记录 incident-task 映射: {incident_id} -> {task_id}")
        except Exception as e:
            logger.error(f"记录映射失败: {e}")
            # 继续执行，映射失败不影响任务创建

        # 6. 更新 incident 状态为 queued
        try:
            set_incident_state(
                incident_id,
                INCIDENT_STATE_QUEUED,
                {
                    "task_id": task_id,
                    "router_action": "task_created",
                    "timestamp": datetime.now().isoformat(),
                },
            )
            logger.info(f"设置 incident 状态为 queued: {incident_id}")
        except Exception as e:
            logger.error(f"设置 incident 状态失败: {e}")
            # 继续执行，状态失败不影响任务创建

        return (
            True,
            task_id,
            {"incident_id": incident_id, "task_id": task_id, "metadata": metadata},
        )


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Athena 自动修复桥接器")
    parser.add_argument(
        "--incident",
        type=Path,
        help="incident JSON 文件路径 (默认: 使用 --latest 或 latest.json)",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="使用最新的 incident (等价于 --incident .openclaw/health/events/latest.json)",
    )
    parser.add_argument("--force", action="store_true", help="强制重新创建任务（忽略幂等检查）")

    args = parser.parse_args()

    # 确定 incident 文件路径
    if args.latest:
        incident_path = Path("/Volumes/1TB-M2/openclaw/.openclaw/health/events/latest.json")
    elif args.incident:
        incident_path = args.incident
    else:
        # 默认使用 latest.json
        incident_path = Path("/Volumes/1TB-M2/openclaw/.openclaw/health/events/latest.json")

    # 检查 incident 文件
    if not incident_path.exists():
        print(f"❌ incident 文件不存在: {incident_path}")
        sys.exit(1)

    # 检查 Athena 组件导入状态
    if not IMPORT_SUCCESS:
        print("❌ Athena 组件导入失败，无法继续")
        sys.exit(1)

    # 创建路由器并处理
    router = IncidentRouter()
    success, message, result = router.route_incident(incident_path)

    if success:
        print("✅ 修复任务创建成功")
        print(f"   Incident: {result['incident_id']}")
        print(f"   Task ID: {result['task_id']}")
        print("   映射已记录到 workflow_state")
        sys.exit(0)
    else:
        print(f"⚠️  {message}")
        if result and "task_id" in result:
            print(f"   现有任务 ID: {result['task_id']}")
        sys.exit(0 if "已有对应任务" in message else 1)


if __name__ == "__main__":
    main()
