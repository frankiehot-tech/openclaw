"""
任务宽度治理模块
防止过宽任务阻塞队列，实现智能任务分解
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class TaskComplexityLevel(Enum):
    """任务复杂度级别"""

    SIMPLE = "simple"  # 简单任务
    MEDIUM = "medium"  # 中等任务
    COMPLEX = "complex"  # 复杂任务
    VERY_COMPLEX = "very_complex"  # 非常复杂任务


@dataclass
class TaskAnalysis:
    """任务分析结果"""

    complexity_score: int
    complexity_level: TaskComplexityLevel
    estimated_time_seconds: int
    components: list[str]
    can_be_decomposed: bool
    decomposition_suggestions: list[str]

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "complexity_score": self.complexity_score,
            "complexity_level": self.complexity_level.value,
            "estimated_time_seconds": self.estimated_time_seconds,
            "components": self.components,
            "can_be_decomposed": self.can_be_decomposed,
            "decomposition_suggestions": self.decomposition_suggestions,
        }


class TaskWidthGovernance:
    """任务宽度治理器"""

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {
            "max_complexity_score": 50,
            "auto_decompose_threshold": 35,
            "simple_task_max_components": 3,
            "medium_task_max_components": 6,
            "complex_task_max_components": 10,
        }

        # 任务类型模式识别
        self.task_patterns = {
            "implementation": ["实现", "开发", "编写", "创建", "构建"],
            "analysis": ["分析", "研究", "评估", "审查", "调研"],
            "refactoring": ["重构", "优化", "改进", "整理", "清理"],
            "documentation": ["文档", "说明", "注释", "手册", "指南"],
            "testing": ["测试", "验证", "检查", "调试", "验证"],
        }

    def analyze_task(self, task_description: str) -> TaskAnalysis:
        """分析任务复杂度"""

        # 基础复杂度分数
        complexity_score = 0

        # 1. 长度分析
        char_count = len(task_description)
        if char_count > 500:
            complexity_score += 20
        elif char_count > 300:
            complexity_score += 15
        elif char_count > 150:
            complexity_score += 10
        elif char_count > 50:
            complexity_score += 5

        # 2. 关键词分析
        components = self.extract_components(task_description)
        complexity_score += len(components) * 3

        # 3. 任务类型分析
        task_type_complexity = {
            "implementation": 15,
            "refactoring": 12,
            "analysis": 10,
            "testing": 8,
            "documentation": 5,
        }

        for task_type, keywords in self.task_patterns.items():
            if any(keyword in task_description for keyword in keywords):
                complexity_score += task_type_complexity.get(task_type, 0)
                break

        # 4. 多步骤指示词分析
        step_keywords = ["首先", "然后", "接着", "最后", "第一步", "第二步", "第三步"]
        step_count = sum(1 for keyword in step_keywords if keyword in task_description)
        complexity_score += step_count * 2

        # 5. 文件操作分析
        file_operations = ["文件", "目录", "文件夹", "路径", "读取", "写入", "保存"]
        if any(op in task_description for op in file_operations):
            complexity_score += 8

        # 确定复杂度级别
        if complexity_score >= 40:
            complexity_level = TaskComplexityLevel.VERY_COMPLEX
        elif complexity_score >= 30:
            complexity_level = TaskComplexityLevel.COMPLEX
        elif complexity_score >= 20:
            complexity_level = TaskComplexityLevel.MEDIUM
        else:
            complexity_level = TaskComplexityLevel.SIMPLE

        # 估算执行时间（秒）
        estimated_time = self.estimate_execution_time(complexity_score, components)

        # 判断是否可以分解
        can_be_decomposed = complexity_score >= self.config["auto_decompose_threshold"]

        # 生成分解建议
        decomposition_suggestions = []
        if can_be_decomposed:
            decomposition_suggestions = self.generate_decomposition_suggestions(
                task_description, components, complexity_level
            )

        return TaskAnalysis(
            complexity_score=complexity_score,
            complexity_level=complexity_level,
            estimated_time_seconds=estimated_time,
            components=components,
            can_be_decomposed=can_be_decomposed,
            decomposition_suggestions=decomposition_suggestions,
        )

    def extract_components(self, task_description: str) -> list[str]:
        """提取任务组件"""
        components = []

        # 提取模块/组件名称
        module_patterns = [
            r"实现(\w+)模块",
            r"开发(\w+)功能",
            r"编写(\w+)代码",
            r"创建(\w+)系统",
            r"构建(\w+)组件",
        ]

        for pattern in module_patterns:
            matches = re.findall(pattern, task_description)
            components.extend(matches)

        # 提取技术栈
        tech_keywords = ["API", "数据库", "前端", "后端", "界面", "服务", "框架"]
        components.extend([kw for kw in tech_keywords if kw in task_description])

        return list(set(components))  # 去重

    def estimate_execution_time(self, complexity_score: int, components: list[str]) -> int:
        """估算执行时间"""
        # 基础时间（分钟）
        base_time = complexity_score * 2

        # 组件数量影响
        component_factor = len(components) * 5

        # 总估算时间（秒）
        estimated_minutes = base_time + component_factor
        return min(estimated_minutes * 60, 7200)  # 最多2小时

    def generate_decomposition_suggestions(
        self, task_description: str, components: list[str], complexity_level: TaskComplexityLevel
    ) -> list[str]:
        """生成任务分解建议"""
        suggestions = []

        if complexity_level == TaskComplexityLevel.COMPLEX:
            if len(components) > 3:
                suggestions.append(
                    f"将任务分解为 {len(components)} 个子任务，每个子任务负责一个组件"
                )
            suggestions.append("先实现核心功能，再逐步添加辅助功能")

        elif complexity_level == TaskComplexityLevel.VERY_COMPLEX:
            suggestions.append("任务非常复杂，建议分阶段实施")
            suggestions.append("第一阶段：需求分析和架构设计")
            suggestions.append("第二阶段：核心功能实现")
            suggestions.append("第三阶段：测试和优化")

            if components:
                suggestions.append(f"按组件分解：{', '.join(components[:3])}...")

        return suggestions

    def should_decompose_task(self, task_analysis: TaskAnalysis) -> bool:
        """判断是否需要分解任务"""
        return (
            task_analysis.complexity_score >= self.config["auto_decompose_threshold"]
            and task_analysis.can_be_decomposed
        )

    def create_decomposition_plan(
        self, task_description: str, task_analysis: TaskAnalysis
    ) -> list[dict[str, Any]]:
        """创建任务分解计划"""
        if not self.should_decompose_task(task_analysis):
            return []

        sub_tasks = []

        if task_analysis.components:
            # 按组件分解
            for i, component in enumerate(task_analysis.components[:5], 1):
                sub_task = {
                    "id": f"subtask_{i}",
                    "description": f"实现{component}组件",
                    "priority": i,
                    "estimated_time_seconds": task_analysis.estimated_time_seconds
                    // len(task_analysis.components),
                    "dependencies": [] if i == 1 else [f"subtask_{i - 1}"],
                }
                sub_tasks.append(sub_task)
        else:
            # 按阶段分解
            phases = ["分析设计", "核心实现", "测试验证", "文档整理"]
            for i, phase in enumerate(phases, 1):
                sub_task = {
                    "id": f"phase_{i}",
                    "description": f"{phase}阶段",
                    "priority": i,
                    "estimated_time_seconds": task_analysis.estimated_time_seconds // len(phases),
                    "dependencies": [] if i == 1 else [f"phase_{i - 1}"],
                }
                sub_tasks.append(sub_task)

        return sub_tasks


# 使用示例
if __name__ == "__main__":
    governor = TaskWidthGovernance()

    # 测试任务
    test_tasks = [
        "实现用户注册功能，包括注册表单、邮箱验证和密码加密",
        "分析系统架构，编写设计文档",
        "重构用户管理模块，优化代码结构",
    ]

    for task in test_tasks:
        print(f"\n分析任务: {task}")
        analysis = governor.analyze_task(task)
        print(f"复杂度分数: {analysis.complexity_score}")
        print(f"复杂度级别: {analysis.complexity_level.value}")
        print(f"估算时间: {analysis.estimated_time_seconds // 60}分钟")
        print(f"组件: {analysis.components}")
        print(f"可分解: {analysis.can_be_decomposed}")
        if analysis.decomposition_suggestions:
            print(f"分解建议: {analysis.decomposition_suggestions}")
