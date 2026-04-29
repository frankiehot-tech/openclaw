"""
Test Model Inference Fallback - 测试模型推理回退

验证当 OCR grounding 未命中时，系统能回退到 model inference
"""

import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


# 手动加载 .env
def load_env():
    env_path = os.path.join(project_root, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip()


load_env()

# 设置日志
import logging

logging.basicConfig(level=logging.INFO)

from autoglm_bridge.agent_loop import AgentLoop
from device_control.device_manager import get_device_manager


def test_model_fallback():
    """测试 model inference fallback"""

    print("=" * 60)
    print("测试 Model Inference Fallback")
    print("=" * 60)

    # 确保设备可用
    device_manager = get_device_manager()
    device_id = device_manager.ensure_device_available()

    if not device_id:
        print("❌ 无法获取设备")
        return

    print(f"✓ 使用设备: {device_id}")

    # 创建 Agent 循环（使用真实模式）
    agent = AgentLoop(device_id=device_id, use_mock=False, max_steps=3)  # 使用真实模式

    # 测试任务列表
    test_tasks = ["打开浏览器", "点击搜索"]

    results = []

    for task in test_tasks:
        print(f"\n{'=' * 60}")
        print(f"任务: {task}")
        print("=" * 60)

        # 重置 agent 状态
        agent.memory.start_task(task)

        # 执行任务
        result = agent.run_task(task, max_steps=2, device_id=device_id)

        # 收集结果
        task_result = {
            "task": task,
            "total_steps": result["total_steps"],
            "final_result": result["final_result"],
            "action_sources": [],
        }

        for step in result["steps"]:
            action = step.get("model_output", {}).get("action", "unknown")
            action_source = step.get("model_output", {}).get("action_source", "unknown")
            step_result = step.get("result", "unknown")

            task_result["action_sources"].append(
                {
                    "step": step["step"],
                    "action": action,
                    "action_source": action_source,
                    "result": step_result,
                }
            )

            print(f"\n步骤 {step['step']}:")
            print(f"  动作: {action}")
            print(f"  来源: {action_source}")
            print(f"  结果: {step_result}")

        results.append(task_result)

        # 打印总结
        print(f"\n任务结果: {result['final_result']}")

    # 打印总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    for task_result in results:
        print(f"\n任务: {task_result['task']}")
        print(f"  总步数: {task_result['total_steps']}")
        print(f"  最终结果: {task_result['final_result']}")
        print("  动作来源:")
        for step_info in task_result["action_sources"]:
            print(
                f"    步骤 {step_info['step']}: {step_info['action']} ({step_info['action_source']})"
            )

    # 统计 action_source 分布
    print("\n" + "=" * 60)
    print("Action Source 分布")
    print("=" * 60)

    source_counts = {}
    for task_result in results:
        for step_info in task_result["action_sources"]:
            source = step_info["action_source"]
            source_counts[source] = source_counts.get(source, 0) + 1

    for source, count in source_counts.items():
        print(f"  {source}: {count}")

    return results


if __name__ == "__main__":
    test_model_fallback()
