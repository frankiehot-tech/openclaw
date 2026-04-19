#!/usr/bin/env python3
"""
Skill Registry - 技能注册表

Athena 主控制面的技能注册与路由系统。
"""

import json
import logging
import os
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)

# 添加项目根目录到路径
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, project_root)


class SkillStatus(Enum):
    """技能状态"""

    EXECUTABLE_NOW = "executable_now"
    GATED = "gated"
    DOCS_ONLY = "docs_only"
    UNAVAILABLE = "unavailable"


class ContractStatus(Enum):
    """合作社合同状态"""

    PENDING_REVIEW = "pending_review"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class PricingModel(Enum):
    """定价模型"""

    FREE = "free"
    USAGE_BASED = "usage_based"
    SUBSCRIPTION = "subscription"
    ONE_TIME = "one_time"
    REVENUE_SHARE = "revenue_share"


@dataclass
class SkillArgument:
    """技能参数"""

    name: str
    type: str
    description: str


@dataclass
class SkillDependency:
    """技能依赖"""

    name: str
    description: str
    check_command: Optional[str] = None


@dataclass
class SkillGateCondition:
    """技能门控条件"""

    condition: str
    description: str
    check: Optional[str] = None


@dataclass
class SkillDefinition:
    """技能定义"""

    id: str
    name: str
    description: str
    status: str
    category: str
    executable: bool
    path: str
    command: Optional[str]
    arguments_schema: List[Dict]
    output_format: str
    dependencies: List[Dict]
    gate_conditions: List[Dict]

    # 合作社注册字段
    developer_id: str = "system"
    pricing_model: str = PricingModel.FREE.value
    base_price: float = 0.0
    contract_status: str = ContractStatus.ACTIVE.value
    revenue_split: Dict[str, float] = field(
        default_factory=lambda: {"developer": 0.7, "platform": 0.2, "community": 0.1}
    )

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)

    def check_dependencies(self) -> Tuple[bool, List[str]]:
        """检查依赖"""
        missing = []
        for dep in self.dependencies:
            if dep.get("check_command"):
                try:
                    subprocess.run(
                        dep["check_command"],
                        shell=True,
                        capture_output=True,
                        check=True,
                    )
                except (subprocess.CalledProcessError, FileNotFoundError):
                    missing.append(f"{dep['name']}: {dep.get('description', '未满足')}")
        return len(missing) == 0, missing

    def check_gate_conditions(self) -> Tuple[bool, List[str]]:
        """检查门控条件"""
        unmet = []
        for gate in self.gate_conditions:
            if gate.get("check"):
                try:
                    subprocess.run(gate["check"], shell=True, capture_output=True, check=True)
                except (subprocess.CalledProcessError, FileNotFoundError):
                    unmet.append(f"{gate['condition']}: {gate.get('description', '未满足')}")
        return len(unmet) == 0, unmet

    def is_available(self) -> Tuple[bool, List[str]]:
        """检查技能是否可用"""
        issues = []

        # 检查依赖
        deps_ok, deps_missing = self.check_dependencies()
        if not deps_ok:
            issues.extend(deps_missing)

        # 检查门控条件
        gates_ok, gates_unmet = self.check_gate_conditions()
        if not gates_ok:
            issues.extend(gates_unmet)

        # 检查路径是否存在（如果可执行）
        if self.executable and self.path and not os.path.exists(self.path):
            issues.append(f"路径不存在: {self.path}")

        return len(issues) == 0, issues


class SkillRegistry:
    """技能注册表"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化技能注册表

        Args:
            config_path: 配置文件路径，默认为 mini-agent/config/athena_skills.yaml
        """
        if config_path is None:
            config_path = os.path.join(project_root, "mini-agent", "config", "athena_skills.yaml")

        self.config_path = config_path
        self.skills: Dict[str, SkillDefinition] = {}
        self.categories: Dict[str, Dict] = {}
        self.load_config()

    def load_config(self) -> None:
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            print(f"警告: 配置文件不存在: {self.config_path}")
            return

        with open(self.config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # 加载技能
        skills_data = config.get("skills", {})
        for skill_id, skill_data in skills_data.items():
            self.skills[skill_id] = SkillDefinition(
                id=skill_id,
                name=skill_data.get("name", skill_id),
                description=skill_data.get("description", ""),
                status=skill_data.get("status", "unavailable"),
                category=skill_data.get("category", "unknown"),
                executable=skill_data.get("executable", False),
                path=skill_data.get("path", ""),
                command=skill_data.get("command"),
                arguments_schema=skill_data.get("arguments_schema", []),
                output_format=skill_data.get("output_format", "text"),
                dependencies=skill_data.get("dependencies", []),
                gate_conditions=skill_data.get("gate_conditions", []),
                # 合作社注册字段
                developer_id=skill_data.get("developer_id", "system"),
                pricing_model=skill_data.get("pricing_model", PricingModel.FREE.value),
                base_price=skill_data.get("base_price", 0.0),
                contract_status=skill_data.get("contract_status", ContractStatus.ACTIVE.value),
                revenue_split=skill_data.get(
                    "revenue_split",
                    {"developer": 0.7, "platform": 0.2, "community": 0.1},
                ),
            )

        # 加载分类
        self.categories = config.get("categories", {})

    def get_skill(self, skill_id: str) -> Optional[SkillDefinition]:
        """获取技能定义"""
        return self.skills.get(skill_id)

    def list_skills(self, category: Optional[str] = None) -> List[SkillDefinition]:
        """列出技能"""
        if category:
            return [skill for skill in self.skills.values() if skill.category == category]
        return list(self.skills.values())

    def execute_skill(
        self, skill_id: str, args: Optional[Dict] = None, context: Optional[Dict] = None
    ) -> Dict:
        """
        执行技能

        Args:
            skill_id: 技能ID
            args: 参数字典
            context: 上下文信息，包含 task_id 等

        Returns:
            执行结果
        """
        skill = self.get_skill(skill_id)
        if not skill:
            return {
                "success": False,
                "error": f"技能不存在: {skill_id}",
                "skill_id": skill_id,
            }

        # 1. 前置授权检查（如果有关联任务）
        task_id = None
        if context and "task_id" in context:
            task_id = context["task_id"]

        if task_id:
            try:
                from .athena_orchestrator import get_orchestrator

                orchestrator = get_orchestrator()
                guardrail_result = orchestrator.check_tool_guardrail(
                    task_id=task_id,
                    tool_name=skill_id,
                    tool_type="skill",
                )

                if not guardrail_result.get("allowed", True):
                    # 根据决策处理
                    decision = guardrail_result.get("decision", "reject")
                    reason = guardrail_result.get("reason", "guardrail 检查失败")

                    if decision == "hitl":
                        return {
                            "success": False,
                            "error": "需要人工介入",
                            "skill_id": skill_id,
                            "guardrail_result": guardrail_result,
                            "status": "hitl_required",
                            "message": f"技能执行被 guardrail 拦截: {reason}",
                        }
                    else:
                        return {
                            "success": False,
                            "error": "工具使用被拒绝",
                            "skill_id": skill_id,
                            "guardrail_result": guardrail_result,
                            "status": "guardrail_rejected",
                            "message": f"技能执行被 guardrail 拒绝: {reason}",
                        }

                # 记录 guardrail 通过
                logger.info(f"技能 {skill_id} 通过 guardrail 检查，任务 {task_id}")

            except ImportError as e:
                logger.warning(f"无法导入 orchestrator: {e}，跳过 guardrail 检查")
            except Exception as e:
                logger.warning(f"guardrail 检查失败: {e}，继续执行技能")

        # 2. 检查可用性
        available, issues = skill.is_available()
        if not available:
            return {
                "success": False,
                "error": "技能不可用",
                "skill_id": skill_id,
                "issues": issues,
                "status": skill.status,
            }

        # 如果不可执行，返回文档信息
        if not skill.executable:
            return {
                "success": True,
                "executed": False,
                "skill_id": skill_id,
                "message": f"技能 {skill.name} 为文档参考类，不可执行。",
                "description": skill.description,
                "status": skill.status,
            }

        # 执行命令
        if not skill.command:
            return {
                "success": False,
                "error": "技能未配置执行命令",
                "skill_id": skill_id,
            }

        # 构建命令
        command = skill.command
        if args:
            # 简单替换参数（实际实现应更安全）
            for key, value in args.items():
                placeholder = f"{{{key}}}"
                if placeholder in command:
                    command = command.replace(placeholder, str(value))

        try:
            # 执行命令
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)

            return {
                "success": result.returncode == 0,
                "skill_id": skill_id,
                "command": command,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "output_format": skill.output_format,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "执行超时",
                "skill_id": skill_id,
                "command": command,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "skill_id": skill_id,
                "command": command,
            }

    def get_skill_status_report(self) -> Dict:
        """获取技能状态报告"""
        report = {
            "total": len(self.skills),
            "by_status": {},
            "by_category": {},
            "skills": [],
        }

        for skill_id, skill in self.skills.items():
            available, issues = skill.is_available()
            status = skill.status

            # 统计
            report["by_status"][status] = report["by_status"].get(status, 0) + 1
            report["by_category"][skill.category] = report["by_category"].get(skill.category, 0) + 1

            # 技能详情
            skill_info = {
                "id": skill_id,
                "name": skill.name,
                "status": status,
                "category": skill.category,
                "executable": skill.executable,
                "available": available,
                "issues": issues,
                "description": skill.description,
            }
            report["skills"].append(skill_info)

        return report

    # ==================== 合作社查询功能 ====================

    def list_skills_by_developer(self, developer_id: str) -> List[SkillDefinition]:
        """按开发者列出技能"""
        return [skill for skill in self.skills.values() if skill.developer_id == developer_id]

    def list_skills_by_pricing_model(self, pricing_model: str) -> List[SkillDefinition]:
        """按定价模型列出技能"""
        return [skill for skill in self.skills.values() if skill.pricing_model == pricing_model]

    def list_skills_by_contract_status(self, contract_status: str) -> List[SkillDefinition]:
        """按合同状态列出技能"""
        return [skill for skill in self.skills.values() if skill.contract_status == contract_status]

    def search_skills(
        self,
        developer_id: Optional[str] = None,
        pricing_model: Optional[str] = None,
        contract_status: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        executable: Optional[bool] = None,
    ) -> List[SkillDefinition]:
        """综合搜索技能"""
        filtered = []
        for skill in self.skills.values():
            if developer_id and skill.developer_id != developer_id:
                continue
            if pricing_model and skill.pricing_model != pricing_model:
                continue
            if contract_status and skill.contract_status != contract_status:
                continue
            if category and skill.category != category:
                continue
            if status and skill.status != status:
                continue
            if executable is not None and skill.executable != executable:
                continue
            filtered.append(skill)
        return filtered

    def update_skill_contract(
        self,
        skill_id: str,
        contract_status: Optional[str] = None,
        pricing_model: Optional[str] = None,
        base_price: Optional[float] = None,
        revenue_split: Optional[Dict[str, float]] = None,
    ) -> Tuple[bool, str]:
        """更新技能合同信息"""
        if skill_id not in self.skills:
            return False, f"技能不存在: {skill_id}"

        skill = self.skills[skill_id]

        # 更新字段
        if contract_status:
            skill.contract_status = contract_status
        if pricing_model:
            skill.pricing_model = pricing_model
        if base_price is not None:
            skill.base_price = base_price
        if revenue_split:
            # 验证分账比例
            total = sum(revenue_split.values())
            if abs(total - 1.0) > 0.0001:
                return False, f"分账比例总和不为1: {total:.4f}"
            skill.revenue_split = revenue_split

        # 保存到配置文件（可选，需要实现）
        # self._save_skill_config(skill)

        return True, "技能合同信息已更新"

    def get_cooperative_summary(self) -> Dict[str, Any]:
        """获取合作社摘要"""
        summary = {
            "total_skills": len(self.skills),
            "by_developer": {},
            "by_pricing_model": {},
            "by_contract_status": {},
            "revenue_potential": 0.0,
        }

        for skill in self.skills.values():
            # 开发者统计
            summary["by_developer"][skill.developer_id] = (
                summary["by_developer"].get(skill.developer_id, 0) + 1
            )

            # 定价模型统计
            summary["by_pricing_model"][skill.pricing_model] = (
                summary["by_pricing_model"].get(skill.pricing_model, 0) + 1
            )

            # 合同状态统计
            summary["by_contract_status"][skill.contract_status] = (
                summary["by_contract_status"].get(skill.contract_status, 0) + 1
            )

            # 收入潜力（仅针对有价格的技能）
            if skill.base_price > 0:
                summary["revenue_potential"] += skill.base_price

        return summary


# 全局注册表实例
_registry_instance: Optional[SkillRegistry] = None


def get_registry() -> SkillRegistry:
    """获取全局注册表实例"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = SkillRegistry()
    return _registry_instance


if __name__ == "__main__":
    # 测试代码
    print("=== Skill Registry 测试 ===")

    registry = SkillRegistry()

    print(f"\n1. 已加载技能数量: {len(registry.skills)}")

    print("\n2. 技能列表:")
    for skill in registry.list_skills():
        available, issues = skill.is_available()
        status_icon = "✓" if available else "✗"
        print(f"  {status_icon} {skill.id}: {skill.name} ({skill.status})")
        if issues:
            print(f"    问题: {', '.join(issues)}")

    print("\n3. 技能状态报告:")
    report = registry.get_skill_status_report()
    print(f"  总计: {report['total']}")
    print(f"  按状态: {report['by_status']}")
    print(f"  按分类: {report['by_category']}")

    print("\n4. 测试执行 openhuman-skill-matcher:")
    result = registry.execute_skill(
        "openhuman-skill-matcher",
        {"profile_skills": ["Python", "React"], "required_skills": ["Python", "AWS"]},
    )
    print(f"  成功: {result.get('success', False)}")
    if result.get("error"):
        print(f"  错误: {result['error']}")

    print("\n5. 测试获取技能:")
    skill = registry.get_skill("humanized-web-scraper")
    if skill:
        print(f"  技能: {skill.name}")
        print(f"  状态: {skill.status}")
        print(f"  可执行: {skill.executable}")
