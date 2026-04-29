"""
Memory - 历史步骤记录模块

记录每一步执行的信息，防止循环错误
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

# 配置日志
logger = logging.getLogger(__name__)

# 日志文件
AUTOGLM_LOG = "os.path.join(os.path.dirname(os.path.abspath(__file__)), '../logs/autoglm.log')"
PIPELINE_LOG = "os.path.join(os.path.dirname(os.path.abspath(__file__)), '../logs/pipeline.log')"
STATE_LOG = "os.path.join(os.path.dirname(os.path.abspath(__file__)), '../logs/state.log')"

# 配置日志
file_handler = logging.FileHandler(AUTOGLM_LOG)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(file_handler)

pipeline_handler = logging.FileHandler(PIPELINE_LOG)
pipeline_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(pipeline_handler)

# State 日志 (Phase 11.5)
state_logger = logging.getLogger("state")
state_handler = logging.FileHandler(STATE_LOG)
state_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
state_logger.addHandler(state_handler)


@dataclass
class StepRecord:
    """单步执行记录（增强版 - 包含 OCR/Grounding + State/Policy）"""

    step: int
    task: str
    screenshot_path: Optional[str]
    model_output: Dict
    executed_action: Dict
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    result: str = "pending"  # pending, success, failed
    error: Optional[str] = None
    # 基础字段
    screen_hash: Optional[str] = None  # 屏幕哈希
    fallback_used: Optional[str] = None  # 使用的 fallback (back/home)
    failure_type: Optional[str] = None  # 失败类型
    step_duration: Optional[float] = None  # 步骤耗时（秒）
    confidence: Optional[float] = None  # 模型置信度
    raw_model_summary: Optional[str] = None  # 原始模型输出摘要
    # OCR/Grounding 字段
    action_source: Optional[str] = None  # 动作来源: ocr_grounding/model_inference/fallback
    ocr_blocks_count: int = 0  # OCR 文本块数量
    ocr_top_texts: List[str] = field(default_factory=list)  # 高置信文本列表
    grounding_target: Optional[str] = None  # grounding 目标文本
    grounding_candidates: List[str] = field(default_factory=list)  # grounding 候选列表
    screen_summary: str = ""  # 屏幕摘要
    # Policy/State 字段 (Phase 11-lite)
    task_allowed: bool = True  # 任务是否在白名单内
    current_state: Optional[str] = None  # 当前页面状态
    state_confidence: float = 0.0  # 状态检测置信度
    plan_type: Optional[str] = None  # 规划类型: direct_execute/go_home_first/open_browser_first
    planner_reason: Optional[str] = None  # 规划原因
    # Post-Action State Check 字段 (Phase 11.5)
    post_action_state: Optional[str] = None  # 动作执行后的页面状态
    post_action_state_confidence: float = 0.0  # 动作执行后的状态置信度
    post_action_state_check_passed: bool = False  # 动作后状态验证是否通过
    post_action_state_check_failed: bool = False  # 动作后状态验证是否失败
    target_state: Optional[str] = None  # 目标状态
    correction_action_taken: bool = False  # 是否执行了修正动作


class Memory:
    """历史步骤记录器"""

    def __init__(self, max_steps: int = 50):
        """
        初始化记忆模块

        Args:
            max_steps: 最大记录步数
        """
        self.steps: List[StepRecord] = []
        self.max_steps = max_steps
        self.current_task: Optional[str] = None

    def start_task(self, task: str):
        """开始新任务"""
        self.current_task = task
        self.steps.clear()
        logger.info(f"开始新任务: {task}")
        pipeline_handler.emit(
            logging.LogRecord("pipeline", logging.INFO, "", 0, f"[TASK START] {task}", [], None)
        )

    def add_step(
        self,
        step: int,
        task: str,
        screenshot_path: Optional[str],
        model_output: Dict,
        executed_action: Dict,
        result: str = "pending",
        error: Optional[str] = None,
        # 基础参数
        screen_hash: Optional[str] = None,
        fallback_used: Optional[str] = None,
        failure_type: Optional[str] = None,
        step_duration: Optional[float] = None,
        confidence: Optional[float] = None,
        raw_model_summary: Optional[str] = None,
        # OCR/Grounding 参数
        action_source: Optional[str] = None,
        ocr_blocks_count: int = 0,
        ocr_top_texts: Optional[List[str]] = None,
        grounding_target: Optional[str] = None,
        grounding_candidates: Optional[List[str]] = None,
        screen_summary: str = "",
    ):
        """添加一步记录（增强版 - 包含 OCR/Grounding）"""
        record = StepRecord(
            step=step,
            task=task,
            screenshot_path=screenshot_path,
            model_output=model_output,
            executed_action=executed_action,
            result=result,
            error=error,
            screen_hash=screen_hash,
            fallback_used=fallback_used,
            failure_type=failure_type,
            step_duration=step_duration,
            confidence=confidence,
            raw_model_summary=raw_model_summary,
            # OCR/Grounding 字段
            action_source=action_source or model_output.get("action_source", "model_inference"),
            ocr_blocks_count=ocr_blocks_count,
            ocr_top_texts=ocr_top_texts or [],
            grounding_target=grounding_target or model_output.get("grounding_target"),
            grounding_candidates=grounding_candidates or [],
            screen_summary=screen_summary,
        )

        self.steps.append(record)

        # 限制记录数量
        if len(self.steps) > self.max_steps:
            self.steps.pop(0)

        # 记录日志
        logger.info(f"步骤 {step}: {model_output.get('action', 'unknown')} - {result}")
        pipeline_handler.emit(
            logging.LogRecord(
                "pipeline",
                logging.INFO,
                "",
                0,
                f"[STEP {step}] action={model_output.get('action')}, result={result}",
                [],
                None,
            )
        )

    def get_last_step(self) -> Optional[StepRecord]:
        """获取上一步记录"""
        return self.steps[-1] if self.steps else None

    def get_history(self) -> List[Dict]:
        """获取历史记录"""
        return [asdict(step) for step in self.steps]

    def is_loop_detected(self, action: Dict, threshold: int = 3) -> bool:
        """
        检测循环动作

        Args:
            action: 当前动作
            threshold: 相同动作连续出现次数阈值

        Returns:
            是否检测到循环
        """
        if not self.steps:
            return False

        # 检查最近 N 步是否重复相同的动作
        recent_steps = self.steps[-threshold:]

        if len(recent_steps) < threshold:
            return False

        action_type = action.get("action")

        for step in recent_steps:
            step_action = step.model_output.get("action")
            if step_action != action_type:
                return False

        logger.warning(f"检测到循环动作: {action_type} 连续 {threshold} 次")
        return True

    def clear(self):
        """清空记录"""
        self.steps.clear()
        self.current_task = None
        logger.info("记忆已清空")

    def to_json(self) -> str:
        """导出为 JSON"""
        return json.dumps(
            {"current_task": self.current_task, "steps": [asdict(step) for step in self.steps]},
            indent=2,
            ensure_ascii=False,
        )

    @classmethod
    def from_json(cls, json_str: str) -> "Memory":
        """从 JSON 恢复"""
        data = json.loads(json_str)
        memory = cls()
        memory.current_task = data.get("current_task")

        for step_data in data.get("steps", []):
            step = StepRecord(**step_data)
            memory.steps.append(step)

        return memory


# 全局单例
_memory: Optional[Memory] = None


def get_memory() -> Memory:
    """获取全局记忆实例"""
    global _memory
    if _memory is None:
        _memory = Memory()
    return _memory


if __name__ == "__main__":
    # 测试代码
    print("=== Memory 测试 ===")

    memory = get_memory()
    memory.start_task("打开设置")

    # 模拟添加步骤
    memory.add_step(
        step=1,
        task="打开设置",
        screenshot_path="/path/to/screenshot.png",
        model_output={"action": "tap", "x": 500, "y": 1200, "reasoning": "点击设置图标"},
        executed_action={"action": "tap", "x": 500, "y": 1200},
        result="success",
    )

    # 检测循环
    print(f"循环检测: {memory.is_loop_detected({'action': 'tap'}, threshold=3)}")

    # 获取历史
    history = memory.get_history()
    print(f"历史记录: {len(history)} 步")

    # 导出 JSON
    print(memory.to_json())
