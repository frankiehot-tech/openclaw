#!/usr/bin/env python3
import sys

with open("sub_agent_bus.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find line index of _check_dependencies
target_line = None
for i, line in enumerate(lines):
    if line.strip().startswith("def _check_dependencies"):
        target_line = i
        break

if target_line is None:
    print("Error: target line not found")
    sys.exit(1)

# Insert new methods before target_line
new_methods = '''    def _handle_planner_task(self, task_input: TaskInput) -> Dict[str, Any]:
        """处理规划者任务"""
        # 最小实现：模拟规划工作
        payload = task_input.payload
        topic = payload.get("topic", "未知主题")

        # 模拟规划工作
        time.sleep(1)  # 模拟处理时间

        return {
            "plan": f"关于 {topic} 的详细规划",
            "tasks": [
                f"任务1: 调研 {topic}",
                f"任务2: 设计 {topic} 架构",
                f"任务3: 实现 {topic} 核心功能",
            ],
            "dependencies": ["任务1", "任务2"],
            "acceptance_criteria": [
                f"{topic} 功能完整实现",
                "通过所有测试用例",
                "文档齐全",
            ],
            "estimated_time": 8.5,
            "risks": ["技术风险: 未知依赖", "时间风险: 估算不足"],
        }

    def _handle_build_worker_task(self, task_input: TaskInput) -> Dict[str, Any]:
        """处理构建者任务（新）"""
        # 最小实现：模拟构建工作
        payload = task_input.payload
        component = payload.get("component", "未知组件")

        # 模拟构建工作
        time.sleep(2)  # 模拟处理时间

        return {
            "component": component,
            "build_status": "success",
            "artifacts": [
                f"{component}_v1.0.py",
                f"{component}_test.py",
                f"{component}_docs.md",
            ],
            "tests_passed": True,
            "code_coverage": 0.85,
            "warnings": ["lint 警告: 第 42 行过长"],
        }

    def _handle_validator_task(self, task_input: TaskInput) -> Dict[str, Any]:
        """处理验证者任务"""
        # 最小实现：模拟验证工作
        payload = task_input.payload
        target = payload.get("target", "未知目标")

        # 模拟验证工作
        time.sleep(1.5)  # 模拟处理时间

        return {
            "validation_target": target,
            "validation_status": "passed",
            "metrics": {
                "execution_time_ms": 1500,
                "test_cases": 10,
                "passed_cases": 10,
                "coverage": 0.95,
            },
            "passed": True,
            "failures": [],
            "evidence": [f"{target}_validation_report.md"],
        }

'''

# Insert before target_line (preserve blank line before)
# Ensure there is a blank line before the new methods
if target_line > 0 and lines[target_line - 1].strip() == "":
    # Already blank line, insert after it
    insert_at = target_line
else:
    # Add blank line before new methods
    lines.insert(target_line, "\n")
    insert_at = target_line + 1
    target_line += 1

# Insert new methods
for i, line in enumerate(new_methods.splitlines(keepends=True)):
    lines.insert(insert_at + i, line)

# Write back
with open("sub_agent_bus.py", "w", encoding="utf-8") as f:
    f.writelines(lines)

print("New methods inserted successfully")
