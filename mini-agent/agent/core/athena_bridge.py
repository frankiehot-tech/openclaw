#!/usr/bin/env python3
"""
Athena Bridge - Athena 桥接层

负责连接用户请求、路由识别与任务编排。
修复 OpenHuman 阶段的运行时断层问题。
"""

import json
import logging
import os
import shlex
import sys
from typing import Any, Dict, Optional, Tuple

# 添加项目根目录到路径
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, project_root)

# 导入依赖模块
try:
    from .athena_orchestrator import get_orchestrator
    from .athena_prompt import get_skill_keyword_map
    from .chat_runtime import get_runtime
    from .openhuman_artifact_templates import get_templates_manager
    from .openhuman_router import detect_openhuman_stage
    from .runtime_handoff import get_handoff
    from .skill_registry import get_registry as get_skill_registry
    from .software_executor import get_executor as get_software_executor
except ImportError:
    # 备用导入路径
    sys.path.insert(0, os.path.dirname(__file__))
    from athena_orchestrator import get_orchestrator
    from athena_prompt import get_skill_keyword_map
    from chat_runtime import get_runtime
    from openhuman_artifact_templates import get_templates_manager
    from openhuman_router import detect_openhuman_stage
    from runtime_handoff import get_handoff
    from skill_registry import get_registry as get_skill_registry
    from software_executor import get_executor as get_software_executor

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AthenaBridge:
    """Athena 桥接器"""

    def __init__(self):
        self.orchestrator = get_orchestrator()
        self.skill_registry = get_skill_registry()
        self.software_executor = get_software_executor()
        self.skill_keyword_map = get_skill_keyword_map()
        self.chat_runtime = get_runtime()
        self.handoff = get_handoff()
        logger.info("AthenaBridge 初始化完成")

    def _handle_slash_commands(
        self, message: str, context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        处理斜杠命令

        Args:
            message: 用户消息
            context: 上下文信息

        Returns:
            响应结果，如果不是斜杠命令则返回 None
        """

        if not message.startswith("/"):
            return None

        parts = shlex.split(message.strip())
        command = parts[0].lower()

        # /skills - 列出所有技能
        if command == "/skills":
            report = self.skill_registry.get_skill_status_report()

            # 格式化响应
            response_text = "## 已接线技能状态\n\n"
            for skill_info in report["skills"]:
                status_icon = "🟢" if skill_info["available"] else "🔴"
                executable_icon = "⚡" if skill_info["executable"] else "📄"
                response_text += f"{status_icon} {executable_icon} **{skill_info['name']}** (`{skill_info['id']}`)\n"
                response_text += (
                    f"   状态: {skill_info['status']}, 分类: {skill_info['category']}\n"
                )
                if skill_info["issues"]:
                    response_text += f"   问题: {', '.join(skill_info['issues'][:2])}\n"
                response_text += "\n"

            response_text += f"总计: {report['total']} 个技能 | "
            response_text += f"可用: {sum(1 for s in report['skills'] if s['available'])} | "
            response_text += f"可执行: {sum(1 for s in report['skills'] if s['executable'])}"

            return {
                "success": True,
                "message": message,
                "domain": "skill",
                "command": command,
                "response_text": response_text,
                "report": report,
                "status": "success",
            }

        # /skill <skill_id> [args] - 执行技能
        elif command == "/skill" and len(parts) >= 2:
            skill_id = parts[1]
            # 解析简单参数（key=value 格式）
            args = {}
            for part in parts[2:]:
                if "=" in part:
                    key, value = part.split("=", 1)
                    args[key] = value
                else:
                    # 无名参数作为 "arg"
                    args["arg"] = part

            # 执行技能
            result = self.skill_registry.execute_skill(skill_id, args if args else None, context)

            # 格式化响应
            if result.get("success"):
                if result.get("executed", True):
                    response_text = f"✅ 技能执行成功: {skill_id}\n\n"
                    if result.get("stdout"):
                        response_text += f"输出:\n```\n{result['stdout'][:500]}\n```\n"
                    if result.get("stderr"):
                        response_text += f"错误输出:\n```\n{result['stderr'][:200]}\n```\n"
                else:
                    response_text = f"📄 技能文档参考: {skill_id}\n\n"
                    response_text += f"{result.get('message', '无额外信息')}\n"
            else:
                response_text = f"❌ 技能执行失败: {skill_id}\n\n"
                response_text += f"错误: {result.get('error', '未知错误')}\n"
                if result.get("issues"):
                    response_text += f"问题: {', '.join(result['issues'])}\n"

            return {
                "success": result.get("success", False),
                "message": message,
                "domain": "skill",
                "command": command,
                "skill_id": skill_id,
                "result": result,
                "response_text": response_text,
                "status": "executed" if result.get("success") else "failed",
            }

        # /software - 列出软件执行器
        elif command == "/software":
            report = self.software_executor.get_status_report()

            response_text = "## 软件执行器状态\n\n"
            for provider_id, provider in report["providers"].items():
                status_icon = {
                    "available": "🟢",
                    "unavailable": "🔴",
                    "optional": "🟡",
                    "gated": "🟠",
                }.get(provider["status"], "⚪")

                response_text += f"{status_icon} **{provider['name']}** (`{provider_id}`)\n"
                response_text += f"   状态: {provider['status']}\n"
                response_text += (
                    f"   能力: {', '.join([c['name'] for c in provider['capabilities'][:2]])}\n"
                )
                response_text += f"   备注: {provider['notes']}\n\n"

            response_text += f"总计: {report['summary']['total']} 个 provider | "
            response_text += f"可用: {report['summary']['available']} | "
            response_text += f"可选: {report['summary']['optional']}"

            return {
                "success": True,
                "message": message,
                "domain": "software",
                "command": command,
                "response_text": response_text,
                "report": report,
                "status": "success",
            }

        # 其他斜杠命令由上层处理
        return None

    def _handle_skill_natural_language(
        self, message: str, context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        处理自然语言技能请求

        Args:
            message: 用户消息
            context: 上下文信息

        Returns:
            响应结果，如果不是技能请求则返回 None
        """
        # 检查关键词映射
        matched_skill_id = None
        for keyword, skill_id in self.skill_keyword_map.items():
            if keyword.lower() in message.lower():
                matched_skill_id = skill_id
                break

        if not matched_skill_id:
            return None

        # 获取技能信息
        skill = self.skill_registry.get_skill(matched_skill_id)
        if not skill:
            return None

        # 检查可用性
        available, issues = skill.is_available()

        # 根据技能状态返回不同响应
        if skill.status == "docs_only" or not skill.executable:
            response_text = f"📄 识别为文档参考技能: {skill.name}\n\n"
            response_text += f"{skill.description}\n\n"
            response_text += f"该技能为文档参考类，不可执行。如需了解更多，请查阅相关文档。"

            return {
                "success": True,
                "message": message,
                "domain": "skill",
                "skill_id": matched_skill_id,
                "response_text": response_text,
                "status": "docs_only",
                "executable": False,
            }

        elif not available:
            response_text = f"🚧 识别为受限技能: {skill.name}\n\n"
            response_text += f"目前无法直接执行该技能，因为:\n"
            for issue in issues[:3]:
                response_text += f"• {issue}\n"
            response_text += f"\n现在可以:\n"
            response_text += f"• 查阅技能文档了解使用方法\n"
            response_text += f"• 使用其他可用技能替代\n"
            response_text += f"• 解决上述限制条件后重试"

            return {
                "success": False,
                "message": message,
                "domain": "skill",
                "skill_id": matched_skill_id,
                "response_text": response_text,
                "status": "gated",
                "issues": issues,
                "executable": False,
            }

        else:
            # 可执行技能，返回执行指引
            response_text = f"🔧 识别为可执行技能: {skill.name}\n\n"
            response_text += f"技能描述: {skill.description}\n\n"
            response_text += f"如需执行该技能，请使用命令:\n"
            response_text += f"`/skill {matched_skill_id} [参数]`\n\n"
            response_text += f"或直接描述你想完成的具体任务。"

            return {
                "success": True,
                "message": message,
                "domain": "skill",
                "skill_id": matched_skill_id,
                "response_text": response_text,
                "status": "executable",
                "executable": True,
            }

    def chat(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理聊天请求

        Args:
            message: 用户消息
            context: 上下文信息

        Returns:
            响应结果
        """
        logger.info(f"收到消息: {message}")

        # 获取聊天运行时状态（单一事实源）
        chat_status = self.chat_runtime.get_chat_state()
        logger.debug(f"聊天运行时状态: {chat_status}")

        try:
            # 1. 检查是否为斜杠命令（技能/软件相关）
            slash_response = self._handle_slash_commands(message, context)
            if slash_response:
                slash_response["chat_status"] = chat_status
                return slash_response

            # 2. 检查是否为自然语言技能请求
            skill_response = self._handle_skill_natural_language(message, context)
            if skill_response:
                skill_response["chat_status"] = chat_status
                return skill_response

            # 3. 检测是否为 OpenHuman 领域请求
            openhuman_stage, stage_label, route_details = detect_openhuman_stage(message)

            if openhuman_stage != "unknown":
                # 4. 处理 OpenHuman 领域请求
                response = self._handle_openhuman_task(
                    message=message,
                    context=context,
                    openhuman_stage=openhuman_stage,
                    stage_label=stage_label,
                    route_details=route_details,
                )
                response["chat_status"] = chat_status
                return response
            else:
                # 5. 处理普通工程请求（降级到默认处理）
                response = self._handle_engineering_task(
                    message=message, context=context, route_details=route_details
                )
                response["chat_status"] = chat_status
                return response

        except Exception as e:
            logger.error(f"处理消息失败: {e}", exc_info=True)
            error_response = self._create_error_response(
                message=message,
                error=str(e),
                details={"exception_type": type(e).__name__},
            )
            error_response["chat_status"] = chat_status
            return error_response

    def _generate_openhuman_artifact(
        self,
        task_id: str,
        openhuman_stage: str,
        stage_label: str,
        message: str,
        metadata: Dict[str, Any],
    ) -> bool:
        """
        为 OpenHuman 任务生成初始 artifact

        Args:
            task_id: 任务ID
            openhuman_stage: OpenHuman阶段ID
            stage_label: 阶段标签
            message: 原始消息
            metadata: 任务元数据

        Returns:
            bool: 是否成功生成
        """
        try:
            # 获取模板管理器
            templates_manager = get_templates_manager()

            # 获取任务目录
            task_dir = self.orchestrator.get_task_dir(task_id)
            if not task_dir or not task_dir.exists():
                logger.warning(f"任务目录不存在: {task_id}")
                return False

            # 准备上下文数据
            from datetime import datetime

            context = {
                "task_id": task_id,
                "openhuman_stage": openhuman_stage,
                "stage_label": stage_label,
                "original_message": message,
                "generation_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "metadata": str(metadata),
                # 基础字段（会被模板覆盖）
                "source_document": "未指定",
                "distilled_by": "系统",
                "distillation_date": datetime.now().strftime("%Y-%m-%d"),
                "skill_id": f"SKILL-{task_id}",
                "skill_name": f"任务{task_id}相关技能",
                "skill_designer": "系统",
                "design_date": datetime.now().strftime("%Y-%m-%d"),
                "task_order_id": task_id,
                "dispatch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "dispatched_by": "系统",
                "acceptance_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "accepted_by": "系统",
                "settlement_batch_id": f"SETTLE-{task_id}",
                "settlement_date": datetime.now().strftime("%Y-%m-%d"),
                "settled_by": "系统",
                "audit_id": f"AUDIT-{task_id}",
                "audit_date": datetime.now().strftime("%Y-%m-%d"),
                "auditor": "系统",
            }

            # 渲染模板
            artifact_content = templates_manager.render_template(openhuman_stage, context)

            if not artifact_content:
                logger.warning(f"无法渲染模板: {openhuman_stage}")
                return False

            # 确定 artifact 文件名
            artifact_filename = f"{openhuman_stage}_artifact.md"
            artifact_path = task_dir / "outputs" / artifact_filename

            # 确保目录存在
            artifact_path.parent.mkdir(parents=True, exist_ok=True)

            # 写入 artifact 文件
            artifact_path.write_text(artifact_content, encoding="utf-8")

            # 添加到任务 artifacts
            self.orchestrator.add_artifact(
                task_id=task_id,
                artifact_path=str(artifact_path),
                artifact_type="openhuman_artifact",
            )

            logger.info(f"OpenHuman artifact 生成成功: {artifact_path}")
            return True

        except Exception as e:
            logger.error(f"生成 OpenHuman artifact 失败: {e}")
            return False

    def _handle_openhuman_task(
        self,
        message: str,
        context: Dict[str, Any],
        openhuman_stage: str,
        stage_label: str,
        route_details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """处理 OpenHuman 任务"""
        logger.info(f"识别为 OpenHuman 阶段: {openhuman_stage} ({stage_label})")

        # 提取 dispatch 信息
        dispatch_source = context.get("dispatch_source")  # wecom, telegram, api, cli
        dispatch_thread_id = context.get("dispatch_thread_id")  # 消息线程ID

        # 创建任务
        success, task_id_or_error, metadata = self.orchestrator.create_task(
            stage=openhuman_stage,
            domain="openhuman",
            description=message,
            dispatch_source=dispatch_source,
            dispatch_thread_id=dispatch_thread_id,
        )

        if not success:
            # 如果创建失败，返回错误
            return self._create_error_response(
                message=message,
                error=task_id_or_error,
                details={
                    "stage": openhuman_stage,
                    "stage_label": stage_label,
                    "route_details": route_details,
                },
            )

        # 任务创建成功
        task_id = task_id_or_error

        # 构建响应
        response = {
            "success": True,
            "message": message,
            "domain": "openhuman",
            "openhuman_stage": openhuman_stage,
            "openhuman_stage_label": stage_label,
            "internal_stage": metadata["stage"],
            "internal_stage_label": self._get_stage_label(metadata["stage"]),
            "task_id": task_id,
            "task_metadata": metadata,
            "route_details": route_details,
            "executor": metadata.get("executor"),
            "expected_output": metadata.get("expected_output"),
            "status": "task_created",
            "response_text": self._format_response_text(
                domain="openhuman",
                openhuman_stage=openhuman_stage,
                stage_label=stage_label,
                internal_stage=metadata["stage"],
                task_id=task_id,
            ),
        }

        logger.info(f"OpenHuman 任务创建成功: {task_id}, 阶段: {openhuman_stage}")

        # 生成 OpenHuman 初始 artifact
        try:
            artifact_generated = self._generate_openhuman_artifact(
                task_id=task_id,
                openhuman_stage=openhuman_stage,
                stage_label=stage_label,
                message=message,
                metadata=metadata,
            )
            if artifact_generated:
                logger.info(f"OpenHuman 初始 artifact 生成成功: {task_id}")
                response["artifact_generated"] = True
            else:
                logger.warning(f"OpenHuman 初始 artifact 生成失败: {task_id}")
                response["artifact_generated"] = False
        except Exception as e:
            logger.error(f"生成 OpenHuman artifact 时出错: {e}")
            response["artifact_generated"] = False
            response["artifact_error"] = str(e)

        # 复杂任务 handoff 检查
        handoff_request = self.handoff.create_handoff_request_from_task(
            task_metadata=metadata,
            context=context,
            workspace=None,  # 暂时不传 workspace
        )
        handoff_result = self.handoff.perform_handoff(handoff_request)

        # 将 handoff 结果添加到响应中
        response["handoff"] = handoff_result.to_dict()
        response["handoff_performed"] = handoff_result.handoff_performed

        if handoff_result.handoff_performed:
            logger.info(f"任务 {task_id} 已 handoff 到 runtime agent")
            # 可以在这里触发异步执行，但保持响应不变

        return response

    def _handle_engineering_task(
        self, message: str, context: Dict[str, Any], route_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理工程任务"""
        # 默认将普通请求视为规划阶段
        default_stage = "plan"

        # 提取 dispatch 信息
        dispatch_source = context.get("dispatch_source")  # wecom, telegram, api, cli
        dispatch_thread_id = context.get("dispatch_thread_id")  # 消息线程ID

        success, task_id_or_error, metadata = self.orchestrator.create_task(
            stage=default_stage,
            domain="engineering",
            description=message,
            dispatch_source=dispatch_source,
            dispatch_thread_id=dispatch_thread_id,
        )

        if not success:
            return self._create_error_response(
                message=message,
                error=task_id_or_error,
                details={"default_stage": default_stage},
            )

        task_id = task_id_or_error

        response = {
            "success": True,
            "message": message,
            "domain": "engineering",
            "stage": default_stage,
            "stage_label": self._get_stage_label(default_stage),
            "task_id": task_id,
            "task_metadata": metadata,
            "route_details": route_details,
            "executor": metadata.get("executor"),
            "expected_output": metadata.get("expected_output"),
            "status": "task_created",
            "response_text": self._format_response_text(
                domain="engineering",
                stage=default_stage,
                stage_label=self._get_stage_label(default_stage),
                task_id=task_id,
            ),
        }

        logger.info(f"工程任务创建成功: {task_id}, 阶段: {default_stage}")

        # 复杂任务 handoff 检查
        handoff_request = self.handoff.create_handoff_request_from_task(
            task_metadata=metadata,
            context=context,
            workspace=None,  # 暂时不传 workspace
        )
        handoff_result = self.handoff.perform_handoff(handoff_request)

        # 将 handoff 结果添加到响应中
        response["handoff"] = handoff_result.to_dict()
        response["handoff_performed"] = handoff_result.handoff_performed

        if handoff_result.handoff_performed:
            logger.info(f"任务 {task_id} 已 handoff 到 runtime agent")
            # 可以在这里触发异步执行，但保持响应不变

        return response

    def _get_stage_label(self, stage: str) -> str:
        """获取阶段标签"""
        labels = {
            "think": "思考分析",
            "plan": "规划设计",
            "build": "构建实现",
            "review": "审查评估",
            "qa": "质量检查",
            "browse": "浏览探索",
        }

        # 尝试从 orchestrator 导入（绝对或相对）
        try:
            # 尝试绝对导入
            from athena_orchestrator import ENGINEERING_STAGE_LABELS as ORCH_LABELS

            return ORCH_LABELS.get(stage, stage)
        except ImportError:
            try:
                # 尝试相对导入
                from .athena_orchestrator import ENGINEERING_STAGE_LABELS as ORCH_LABELS

                return ORCH_LABELS.get(stage, stage)
            except ImportError:
                return labels.get(stage, stage)

    def _format_response_text(self, domain: str, **kwargs) -> str:
        """格式化响应文本"""
        if domain == "openhuman":
            # kwargs 中应包含：stage_label, openhuman_stage, internal_stage, task_id
            stage_label = kwargs.get("stage_label", "未知")
            openhuman_stage = kwargs.get("openhuman_stage", "unknown")
            internal_stage = kwargs.get("internal_stage", "plan")
            task_id = kwargs.get("task_id", "N/A")

            return (
                f"识别为 OpenHuman 领域: {stage_label} ({openhuman_stage})\n"
                f"已创建任务: {task_id}\n"
                f"内部执行阶段: {internal_stage}\n"
                f"预计产出: {self._get_expected_output(internal_stage)}"
            )
        else:
            # kwargs 中应包含：stage_label, stage, task_id
            stage_label = kwargs.get("stage_label", "未知")
            stage = kwargs.get("stage", "plan")
            task_id = kwargs.get("task_id", "N/A")

            return (
                f"识别为工程领域: {stage_label}\n"
                f"已创建任务: {task_id}\n"
                f"预计产出: {self._get_expected_output(stage)}"
            )

    def _get_expected_output(self, stage: str) -> str:
        """获取预期产出描述"""
        outputs = {
            "think": "分析报告",
            "plan": "设计方案",
            "build": "实现代码",
            "review": "审查意见",
            "qa": "质量报告",
            "browse": "浏览结果",
        }
        return outputs.get(stage, "未知产出")

    def _create_error_response(
        self, message: str, error: str, details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """创建错误响应"""
        return {
            "success": False,
            "message": message,
            "error": error,
            "details": details,
            "status": "error",
            "response_text": f"处理请求时出错: {error}",
        }


# 全局桥接器实例
_bridge_instance: Optional[AthenaBridge] = None


def get_bridge() -> AthenaBridge:
    """获取全局桥接器实例"""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = AthenaBridge()
    return _bridge_instance


if __name__ == "__main__":
    # 测试代码
    print("=== Athena Bridge 测试 ===")

    bridge = AthenaBridge()

    # 测试用例（来自任务说明）
    test_cases = [
        "把这个经验提炼成 Skill",
        "生成审计报告",
        "为 offline_survey 发布任务并筛人",
        "设计一个新技能模板",
        "结算上个月的任务费用",
        "这是一个普通请求",
    ]

    for message in test_cases:
        print(f"\n{'=' * 60}")
        print(f"测试消息: {message}")

        result = bridge.chat(message, {})

        print(f"成功: {result.get('success', False)}")
        print(f"领域: {result.get('domain', 'unknown')}")

        if result.get("domain") == "openhuman":
            print(f"OpenHuman阶段: {result.get('openhuman_stage')}")
            print(f"内部阶段: {result.get('internal_stage')}")

        print(f"任务ID: {result.get('task_id', 'N/A')}")

        if result.get("error"):
            print(f"错误: {result.get('error')}")

        print(f"响应文本:\n{result.get('response_text', '')}")

        # 打印 handoff 信息
        handoff_performed = result.get("handoff_performed", False)
        print(f"Handoff 执行: {handoff_performed}")
        if handoff_performed:
            handoff_data = result.get("handoff", {})
            print(f"  Handoff 消息: {handoff_data.get('message', 'N/A')}")
            print(
                f"  Runtime 结果状态: {handoff_data.get('runtime_result', {}).get('status', 'N/A')}"
            )

    # 验证不会抛异常
    print(f"\n{'=' * 60}")
    print("验证运行时不会抛异常:")

    critical_cases = [
        "把这个经验提炼成 Skill",
        "生成审计报告",
        "为 offline_survey 发布任务并筛人",
    ]

    all_passed = True
    for message in critical_cases:
        try:
            result = bridge.chat(message, {})
            if result.get("success") and not result.get("error"):
                print(f"  ✓ {message}: 成功")
            else:
                print(f"  ✗ {message}: 失败 - {result.get('error', '未知错误')}")
                all_passed = False
        except Exception as e:
            print(f"  ✗ {message}: 异常 - {e}")
            all_passed = False

    if all_passed:
        print("\n✅ 所有关键用例通过，运行时无异常")
    else:
        print("\n❌ 部分关键用例失败")
