"""
Model Client - 模型客户端

封装 AutoGLM / OpenAI API 调用
支持 mock 模式（默认）和真实模式
"""

import json
import logging
import os
import random
import re
import time

import requests


# 手动加载 .env 文件
def load_env_file(env_path):
    """手动解析 .env 文件并设置环境变量"""
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()


env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_env_file(env_path)

# 如果 agent_system/.env 中未设置 AUTOGLM_API_KEY，从根目录 .env 继承
if not os.getenv("AUTOGLM_API_KEY"):
    root_env = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
    if os.path.exists(root_env):
        load_env_file(root_env)

# 配置日志
logger = logging.getLogger(__name__)

# 日志文件
AUTOGLM_LOG = "os.path.join(os.path.dirname(os.path.abspath(__file__)), '../logs/autoglm.log')"

# 配置日志
file_handler = logging.FileHandler(AUTOGLM_LOG)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(file_handler)


# 从环境变量读取配置（动态获取）
def get_autoglm_config():
    """获取 AutoGLM 配置"""
    return {
        "api_key": os.getenv("AUTOGLM_API_KEY") or os.getenv("DASHSCOPE_API_KEY", ""),
        "base_url": os.getenv("AUTOGLM_BASE_URL", ""),
        "model": os.getenv("AUTOGLM_MODEL", "gpt-4"),
        "timeout": int(os.getenv("AUTOGLM_TIMEOUT", "60")),
        "use_mock": os.getenv("AUTOGLM_USE_MOCK", "true").lower() == "true",
    }


# 全局配置变量（会在模块加载时读取一次）
_env_config = get_autoglm_config()
AUTOGLM_API_KEY = _env_config["api_key"]
AUTOGLM_BASE_URL = _env_config["base_url"]
AUTOGLM_MODEL = _env_config["model"]
AUTOGLM_TIMEOUT = _env_config["timeout"]
AUTOGLM_USE_MOCK = _env_config["use_mock"]

# System prompt for real mode - 要求模型只输出动作 JSON
SYSTEM_PROMPT = """你是一个手机控制助手。根据当前屏幕截图和任务描述，输出下一步操作。

输出格式要求（必须严格遵循）：
```json
{
  "action": "tap|swipe|input_text|back|home",
  "params": {
    "x": 500,
    "y": 1200
  },
  "reason": "操作原因",
  "confidence": 0.9
}
```

动作说明：
- tap: 点击，params 需要 x, y 坐标
- swipe: 滑动，params 需要 x1, y1, x2, y2
- input_text: 输入文本，params 需要 text
- back: 返回键
- home: 主页键

只输出 JSON，不要输出其他解释文字。"""


# Mock 模式下的默认动作（新格式）
MOCK_ACTIONS = [
    {
        "action": "tap",
        "params": {"x": 540, "y": 1200},
        "reason": "点击屏幕中央区域",
        "confidence": 0.92,
    },
    {"action": "tap", "params": {"x": 300, "y": 800}, "reason": "点击应用图标", "confidence": 0.88},
    {
        "action": "tap",
        "params": {"x": 900, "y": 200},
        "reason": "点击右上角按钮",
        "confidence": 0.85,
    },
    {
        "action": "swipe",
        "params": {"x1": 540, "y1": 2000, "x2": 540, "y2": 500},
        "reason": "向上滑动屏幕",
        "confidence": 0.90,
    },
    {
        "action": "swipe",
        "params": {"x1": 540, "y1": 500, "x2": 540, "y2": 2000},
        "reason": "向下滑动屏幕",
        "confidence": 0.90,
    },
    {"action": "back", "params": {}, "reason": "返回上一级", "confidence": 0.95},
    {"action": "home", "params": {}, "reason": "返回主页", "confidence": 0.95},
]


def convert_to_new_format(output: dict) -> dict:
    """
    将旧格式转换为新格式（向后兼容）

    旧格式: {"action": "tap", "x": 500, "y": 1200, "reasoning": "..."}
    新格式: {"action": "tap", "params": {"x": 500, "y": 1200}, "reason": "...", "confidence": 0.9}
    """
    if "params" in output and "reason" in output:
        # 已经是新格式
        return output

    # 转换旧格式
    action = output.get("action", "unknown")
    params = {}

    if action == "tap":
        params = {"x": output.get("x", 0), "y": output.get("y", 0)}
    elif action == "swipe":
        params = {
            "x1": output.get("x1", 0),
            "y1": output.get("y1", 0),
            "x2": output.get("x2", 0),
            "y2": output.get("y2", 0),
        }
    elif action == "input_text":
        params = {"text": output.get("text", "")}

    return {
        "action": action,
        "params": params,
        "reason": output.get("reasoning", output.get("reason", "")),
        "confidence": output.get("confidence", 0.9),
    }


class ModelClient:
    """模型客户端"""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "gpt-4",
        use_mock: bool = True,
    ):
        """
        初始化模型客户端

        Args:
            api_key: API 密钥
            base_url: API 基础 URL
            model: 模型名称
            use_mock: 是否使用 mock 模式
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.use_mock = use_mock

        if use_mock:
            logger.info("模型客户端初始化: MOCK 模式")
        else:
            logger.info(f"模型客户端初始化: REAL 模式, model={model}, base_url={base_url}")

    def set_mock_mode(self, enabled: bool):
        """切换 mock 模式"""
        self.use_mock = enabled
        logger.info(f"切换模式: {'MOCK' if enabled else 'REAL'}")

    def infer_action(
        self,
        task: str,
        screenshot_path: str | None,
        history: list[dict],
        use_mock: bool | None = None,
    ) -> dict:
        """
        推理下一步动作

        Args:
            task: 当前任务
            screenshot_path: 截图路径
            history: 历史步骤
            use_mock: 覆盖默认 mock 设置

        Returns:
            结构化动作 JSON:
            {
                "action": "tap",
                "x": 500,
                "y": 1200,
                "reasoning": "..."
            }
        """
        # 确定使用 mock 还是真实模式
        mock_mode = use_mock if use_mock is not None else self.use_mock

        logger.info(f"推理动作: task={task}, mock={mock_mode}")

        if mock_mode:
            return self._mock_infer(task, screenshot_path, history)
        else:
            return self._real_infer(task, screenshot_path, history)

    def _mock_infer(self, task: str, screenshot_path: str | None, history: list[dict]) -> dict:
        """
        Mock 模式推理

        基于任务关键词返回合理的模拟动作（新格式）
        """
        task_lower = task.lower()

        # 根据任务关键词返回不同的动作（新格式）
        if "设置" in task or "settings" in task_lower:
            return {
                "action": "tap",
                "params": {"x": 540, "y": 1400},
                "reason": "点击设置图标",
                "confidence": 0.92,
            }

        elif "返回" in task or "back" in task_lower:
            return {"action": "back", "params": {}, "reason": "执行返回操作", "confidence": 0.95}

        elif "主页" in task or "home" in task_lower:
            return {"action": "home", "params": {}, "reason": "返回主页", "confidence": 0.95}

        elif "滑动" in task or "swipe" in task_lower:
            return {
                "action": "swipe",
                "params": {"x1": 540, "y1": 2000, "x2": 540, "y2": 500},
                "reason": "向上滑动",
                "confidence": 0.90,
            }

        elif "搜索" in task or "search" in task_lower:
            return {
                "action": "tap",
                "params": {"x": 540, "y": 300},
                "reason": "点击搜索框",
                "confidence": 0.88,
            }

        elif "输入" in task or "input" in task_lower:
            return {
                "action": "input_text",
                "params": {"text": "test"},
                "reason": "输入文本",
                "confidence": 0.85,
            }

        else:
            # 默认随机返回一个动作
            action = random.choice(MOCK_ACTIONS).copy()
            action["reason"] = f"默认动作: {action['action']}"
            return action

    def _real_infer(self, task: str, screenshot_path: str | None, history: list[dict]) -> dict:
        """
        真实模式推理

        调用真实的模型 API
        """
        # 动态获取环境变量配置
        config = get_autoglm_config()
        api_key = config["api_key"]
        base_url = config["base_url"]
        model = config["model"]
        timeout = config["timeout"]

        if not api_key or not base_url:
            logger.error("真实模式需要配置 API_KEY 和 BASE_URL")
            return {
                "action": "error",
                "params": {},
                "reason": "未配置 API_KEY 或 BASE_URL",
                "confidence": 0.0,
            }

        # 构建请求
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        # 构建用户消息
        user_message = f"任务: {task}"

        # 如果有截图，添加截图信息（实际应该将截图编码为 base64 发送）
        if screenshot_path:
            user_message += f"\n截图路径: {screenshot_path}"

        # 如果有历史，添加历史信息
        if history:
            recent_steps = history[-3:]  # 只取最近3步
            history_text = "\n".join(
                [
                    f"步骤 {i+1}: {step.get('action')} - {step.get('result')}"
                    for i, step in enumerate(recent_steps)
                ]
            )
            user_message += f"\n\n历史步骤:\n{history_text}"

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.7,
            "max_tokens": 1000,
        }

        # 记录请求摘要（不记录敏感信息）
        logger.info(f"REAL API 请求: model={model}, base_url={base_url}")

        try:
            start_time = time.time()

            response = requests.post(
                f"{base_url}/chat/completions", headers=headers, json=payload, timeout=timeout
            )

            elapsed = time.time() - start_time

            if response.status_code != 200:
                logger.error(
                    f"API 请求失败: status={response.status_code}, body={response.text[:200]}"
                )
                return {
                    "action": "error",
                    "params": {},
                    "reason": f"API 错误: {response.status_code}",
                    "confidence": 0.0,
                }

            result = response.json()

            # 提取模型输出
            if "choices" not in result or len(result["choices"]) == 0:
                logger.error("API 响应格式错误: 无 choices")
                return {
                    "action": "error",
                    "params": {},
                    "reason": "API 响应格式错误",
                    "confidence": 0.0,
                }

            content = result["choices"][0].get("message", {}).get("content", "")
            logger.info(f"API 响应: elapsed={elapsed:.2f}s, content_length={len(content)}")

            # 解析 JSON 输出
            parsed = self._parse_model_output(content)

            if parsed:
                return parsed
            else:
                logger.warning("无法解析模型输出，返回错误动作")
                return {
                    "action": "error",
                    "params": {},
                    "reason": "无法解析模型输出",
                    "confidence": 0.0,
                }

        except requests.exceptions.Timeout:
            logger.error(f"API 请求超时: {AUTOGLM_TIMEOUT}s")
            return {
                "action": "error",
                "params": {},
                "reason": f"请求超时 ({AUTOGLM_TIMEOUT}s)",
                "confidence": 0.0,
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"API 请求异常: {str(e)}")
            return {
                "action": "error",
                "params": {},
                "reason": f"请求异常: {str(e)}",
                "confidence": 0.0,
            }

        except Exception as e:
            logger.error(f"未知异常: {str(e)}")
            return {
                "action": "error",
                "params": {},
                "reason": f"未知异常: {str(e)}",
                "confidence": 0.0,
            }

    def _parse_model_output(self, content: str) -> dict | None:
        """
        解析模型输出

        处理以下情况：
        1. 纯 JSON
        2. Markdown code block 包裹的 JSON
        3. 包含自然语言解释的 JSON

        Args:
            content: 模型原始输出

        Returns:
            解析后的动作字典，解析失败返回 None
        """
        # 尝试提取 JSON（支持 markdown code block）
        json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 尝试直接解析整个内容
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                logger.warning(f"无法从输出中提取 JSON: {content[:100]}...")
                return None

        try:
            parsed = json.loads(json_str)

            # 转换为新格式
            if "params" not in parsed:
                parsed = convert_to_new_format(parsed)

            # 验证输出
            if self.validate_output(parsed):
                return parsed
            else:
                logger.warning(f"模型输出格式验证失败: {parsed}")
                return None

        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失败: {e}, content: {json_str[:100]}...")
            return None

    def validate_output(self, output: dict) -> bool:
        """
        验证模型输出格式（新格式 + 旧格式兼容）

        Args:
            output: 模型输出

        Returns:
            是否有效
        """
        if not isinstance(output, dict):
            return False

        if "action" not in output:
            return False

        # 验证动作类型
        valid_actions = ["tap", "swipe", "input_text", "back", "home", "error"]
        if output["action"] not in valid_actions:
            return False

        # 新格式：使用 params
        if "params" in output:
            params = output["params"]
            if not isinstance(params, dict):
                return False

            # 验证 tap 参数
            if output["action"] == "tap":
                if "x" not in params or "y" not in params:
                    return False

            # 验证 swipe 参数
            elif output["action"] == "swipe":
                required = ["x1", "y1", "x2", "y2"]
                if not all(k in params for k in required):
                    return False

            # 验证 input_text 参数
            elif output["action"] == "input_text" and "text" not in params:
                    return False
        else:
            # 旧格式兼容：直接使用顶层字段
            # 验证坐标
            if output["action"] == "tap":
                if "x" not in output or "y" not in output:
                    return False

            # 验证滑动
            elif output["action"] == "swipe":
                required = ["x1", "y1", "x2", "y2"]
                if not all(k in output for k in required):
                    return False

            # 验证输入
            elif output["action"] == "input_text" and "text" not in output:
                    return False

        return True


# 全局单例
_client: ModelClient | None = None


def get_model_client(
    api_key: str | None = None,
    base_url: str | None = None,
    model: str = "gpt-4",
    use_mock: bool = True,
) -> ModelClient:
    """获取全局模型客户端"""
    global _client

    if _client is None:
        _client = ModelClient(api_key=api_key, base_url=base_url, model=model, use_mock=use_mock)

    return _client


def reset_model_client():
    """重置模型客户端"""
    global _client
    _client = None


def is_real_mode_configured() -> bool:
    """
    检查真实模式是否已配置

    Returns:
        是否已配置真实模式
    """
    # 优先使用实例配置
    if _client is not None and _client.api_key and _client.base_url:
        return True

    # 其次检查环境变量
    return bool(AUTOGLM_API_KEY and AUTOGLM_BASE_URL)


def get_runtime_mode() -> str:
    """
    获取当前运行时模式

    Returns:
        "mock" 或 "real"
    """
    if _client is not None:
        return "mock" if _client.use_mock else "real"

    # 默认检查环境变量
    return "mock" if AUTOGLM_USE_MOCK else "real"


def check_real_mode_config() -> dict:
    """
    检查真实模式配置状态

    Returns:
        配置状态字典
    """
    # 检查环境变量
    has_api_key = bool(AUTOGLM_API_KEY)
    has_base_url = bool(AUTOGLM_BASE_URL)
    has_model = bool(AUTOGLM_MODEL)
    is_configured = has_api_key and has_base_url

    # 检查实例配置
    instance_configured = False
    if _client is not None:
        instance_configured = bool(_client.api_key and _client.base_url)

    return {
        "env_api_key": has_api_key,
        "env_base_url": has_base_url,
        "env_model": has_model,
        "env_configured": is_configured,
        "instance_configured": instance_configured,
        "default_mode": "mock" if AUTOGLM_USE_MOCK else "real",
        "current_mode": get_runtime_mode(),
    }


if __name__ == "__main__":
    # 测试代码
    print("=== Model Client 测试 ===")

    # Mock 模式测试
    client = ModelClient(use_mock=True)

    # 测试各种任务
    test_tasks = ["打开设置", "返回", "主页", "向上滑动", "搜索天气", "输入文字"]

    for task in test_tasks:
        result = client.infer_action(task, "/path/to/screenshot.png", [])
        print(f"任务: {task}")
        print(f"动作: {result}")
        print()

    # 验证输出
    print("输出验证:", client.validate_output({"action": "tap", "x": 100, "y": 200}))
