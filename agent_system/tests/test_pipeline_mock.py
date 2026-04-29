"""
Pipeline Mock Test - 链路 Mock 测试

测试完整控制链路（Athena → Z Flip3）
使用 mock 模式，不调用真实 API
"""

import json
import logging
import os
import sys
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 导入各模块
from athena_adapter.task_router import TaskRouter
from autoglm_bridge.action_executor import ActionExecutor
from autoglm_bridge.agent_loop import AgentLoop
from autoglm_bridge.model_client import ModelClient
from device_control.adb_client import ADBClient

# 配置日志
PIPELINE_LOG = "os.path.join(os.path.dirname(os.path.abspath(__file__)), '../logs/pipeline.log')"
FULL_PIPELINE_LOG = "os.path.join(os.path.dirname(os.path.abspath(__file__)), '../logs/full_pipeline.log')"

# 确保日志目录存在
os.makedirs(os.path.dirname(PIPELINE_LOG), exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

pipeline_logger = logging.getLogger("pipeline")
pipeline_handler = logging.FileHandler(PIPELINE_LOG)
pipeline_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
pipeline_logger.addHandler(pipeline_handler)

full_logger = logging.getLogger("full_pipeline")
full_handler = logging.FileHandler(FULL_PIPELINE_LOG)
full_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
full_logger.addHandler(full_handler)


def run_pipeline_validation(
    task: str,
    device: str = "zflip3",
    max_steps: int = 1,
    use_mock: bool = True,
    device_id: str | None = None,
) -> dict:
    """
    链路验证入口

    接收 Athena 风格任务，经过完整链路，返回验证结果

    Args:
        task: 任务描述
        device: 目标设备
        max_steps: 最大步数
        use_mock: 是否使用 mock 模式
        device_id: 设备序列号

    Returns:
        验证结果:
        {
            "task": "...",
            "device": "...",
            "status": "success/failed/error",
            "steps_executed": [...],
            "final_action": {...},
            "history": [...],
            "error": "...",
            "timestamp": "..."
        }
    """
    timestamp = datetime.now().isoformat()
    result = {
        "task": task,
        "device": device,
        "device_id": device_id,
        "status": "pending",
        "steps_executed": [],
        "final_action": {},
        "history": [],
        "error": None,
        "timestamp": timestamp,
    }

    pipeline_logger.info(f"=== 开始链路验证: {task} ===")
    full_logger.info(f"=== PIPELINE START: {task} ===")

    try:
        # 步骤 1: Task Router
        pipeline_logger.info("步骤 1: Task Router")
        router = TaskRouter()
        protocol = router.route(task, device)
        pipeline_logger.info(f"  协议: {json.dumps(protocol, ensure_ascii=False)}")
        full_logger.info(f"  ROUTED: {json.dumps(protocol, ensure_ascii=False)}")

        # 步骤 2: Agent Loop
        pipeline_logger.info("步骤 2: Agent Loop")
        agent_loop = AgentLoop(device_id=device_id)

        # 执行任务
        loop_result = agent_loop.run_task(
            task=protocol["task"], max_steps=max_steps, device_id=device_id
        )

        # 兼容 use_mock 参数
        loop_result["success"] = loop_result.get("final_result") != "failed"

        result["steps_executed"] = loop_result.get("steps", [])
        result["history"] = loop_result.get("history", [])
        result["final_action"] = loop_result.get("last_action", {})
        result["status"] = "success" if loop_result.get("success", False) else "failed"

        pipeline_logger.info(f"  执行步数: {len(result['steps_executed'])}")
        pipeline_logger.info(
            f"  最终动作: {json.dumps(result['final_action'], ensure_ascii=False)}"
        )
        full_logger.info(f"  STEPS: {len(result['steps_executed'])}")
        full_logger.info(
            f"  FINAL_ACTION: {json.dumps(result['final_action'], ensure_ascii=False)}"
        )

    except Exception as e:
        error_msg = str(e)
        result["status"] = "error"
        result["error"] = error_msg
        pipeline_logger.error(f"  错误: {error_msg}")
        full_logger.error(f"  ERROR: {error_msg}")

    full_logger.info(f"=== PIPELINE END: {result['status']} ===")

    return result


def test_task_router():
    """测试任务路由器"""
    print("\n=== 测试 Task Router ===")

    router = TaskRouter()

    test_cases = [
        ("打开设置", "zflip3"),
        ("返回上一级", "zflip3"),
        ("回到主屏幕", "zflip3"),
        ("向上滑动", "zflip3"),
    ]

    for task, device in test_cases:
        try:
            result = router.route(task, device)
            print(f"  ✓ {task} -> {result['device']}")
            pipeline_logger.info(f"Task Router 测试通过: {task}")
        except Exception as e:
            print(f"  ✗ {task}: {e}")
            pipeline_logger.error(f"Task Router 测试失败: {task} - {e}")


def test_model_client_mock():
    """测试模型客户端 Mock 模式"""
    print("\n=== 测试 Model Client (Mock) ===")

    client = ModelClient(use_mock=True)

    test_tasks = [
        "打开设置",
        "返回上一级",
        "回到主屏幕",
        "向上滑动",
    ]

    for task in test_tasks:
        result = client.infer_action(task, None, [])
        print(
            f"  {task} -> {result.get('action')} ({result.get('reason', result.get('reasoning', ''))})"
        )
        pipeline_logger.info(f"Model Client Mock 测试: {task} -> {result.get('action')}")


def test_action_executor():
    """测试动作执行器"""
    print("\n=== 测试 Action Executor ===")

    executor = ActionExecutor()

    # 测试有效动作（新格式）
    test_actions = [
        {"action": "tap", "params": {"x": 540, "y": 1200}, "reason": "测试点击"},
        {"action": "back", "params": {}, "reason": "测试返回"},
        {"action": "home", "params": {}, "reason": "测试主页"},
    ]

    for action in test_actions:
        valid, error = executor.validate_action(action)
        print(f"  {action['action']}: {'✓' if valid else f'✗ {error}'}")
        if valid:
            pipeline_logger.info(f"Action Executor 校验通过: {action['action']}")


def test_full_pipeline():
    """测试完整链路"""
    print("\n=== 测试完整链路 (Mock 模式) ===")

    test_tasks = [
        "打开设置",
        "返回上一级",
        "回到主屏幕",
        "向上滑动",
    ]

    for task in test_tasks:
        print(f"\n>>> {task}")
        result = run_pipeline_validation(task, max_steps=1, use_mock=True)
        print(f"  状态: {result['status']}")
        print(f"  执行步数: {len(result['steps_executed'])}")
        if result.get("final_action"):
            print(f"  最终动作: {result['final_action'].get('action')}")
        if result.get("error"):
            print(f"  错误: {result['error']}")


def test_no_device_behavior():
    """测试无设备情况下的行为"""
    print("\n=== 测试无设备行为 ===")

    # 尝试使用不存在的设备
    result = run_pipeline_validation(
        task="打开设置", device_id="FAKE_DEVICE_12345", max_steps=1, use_mock=True
    )

    print(f"  状态: {result['status']}")
    print(f"  错误: {result.get('error', '无')}")

    # 验证日志是否记录
    if os.path.exists(PIPELINE_LOG):
        print(f"  日志文件存在: {PIPELINE_LOG}")
    else:
        print("  ✗ 日志文件不存在")


def check_device():
    """检查设备状态"""
    print("\n=== 检查设备状态 ===")

    try:
        adb = ADBClient()
        devices = adb.list_devices()

        if devices:
            print(f"  发现 {len(devices)} 个设备:")
            for dev in devices:
                print(f"    - {dev}")
                pipeline_logger.info(f"设备在线: {dev}")
        else:
            print("  未发现设备")
            pipeline_logger.warning("未发现设备")

        return devices

    except Exception as e:
        print(f"  检查设备失败: {e}")
        pipeline_logger.error(f"检查设备失败: {e}")
        return []


def run_all_tests():
    """运行所有测试"""
    print("=" * 50)
    print("Pipeline Mock 测试套件")
    print("=" * 50)

    # 1. 测试 Task Router
    test_task_router()

    # 2. 测试 Model Client (Mock)
    test_model_client_mock()

    # 3. 测试 Action Executor
    test_action_executor()

    # 4. 检查设备
    devices = check_device()

    # 5. 测试无设备行为
    test_no_device_behavior()

    # 6. 测试完整链路
    test_full_pipeline()

    print("\n" + "=" * 50)
    print("测试完成")
    print(f"日志位置: {PIPELINE_LOG}")
    print("=" * 50)


if __name__ == "__main__":
    run_all_tests()
