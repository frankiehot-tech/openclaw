#!/usr/bin/env python3
"""
修复超时队列任务脚本
基于《多Agent系统24小时压力测试问题修复实施方案》1.1节实现
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 配置常量
QUEUE_DIR = Path("/Volumes/1TB-M2/openclaw/.openclaw/plan_queue")
HEARTBEAT_TIMEOUT = 300  # 5分钟，与runner配置一致
STALE_TASK_TIMEOUT = 600  # 10分钟，与runner配置一致
AUTO_RETRY_LIMIT = 3
AUTO_RETRY_COOLDOWN = 90  # 1.5分钟


def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_json_file(path):
    """加载JSON文件"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"警告: 无法加载文件 {path}: {e}")
        return None


def save_json_file(path, data):
    """保存JSON文件"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ 已保存: {path}")
    except Exception as e:
        print(f"❌ 保存失败 {path}: {e}")


def is_timestamp_old(timestamp_str, timeout_seconds):
    """检查时间戳是否超过超时阈值"""
    if not timestamp_str:
        return True

    try:
        # 解析ISO格式时间戳
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc).astimezone()
        elapsed = (now - dt).total_seconds()
        return elapsed > timeout_seconds
    except Exception as e:
        print(f"解析时间戳失败 {timestamp_str}: {e}")
        return True


def analyze_queue_file(queue_path):
    """分析队列文件中的超时任务"""
    print(f"分析队列文件: {queue_path.name}")
    data = load_json_file(queue_path)
    if not data:
        return []

    stale_tasks = []
    items = data.get("items", {})

    for item_id, item_data in items.items():
        if not isinstance(item_data, dict):
            continue

        status = item_data.get("status", "")
        error = item_data.get("error", "")
        summary = item_data.get("summary", "")
        started_at = item_data.get("started_at", "")
        runner_heartbeat_at = item_data.get("runner_heartbeat_at", "")

        # 检查是否超时
        is_stale = False
        timeout_reason = ""

        # 检查心跳超时
        if runner_heartbeat_at:
            if is_timestamp_old(runner_heartbeat_at, HEARTBEAT_TIMEOUT):
                is_stale = True
                timeout_reason = f"心跳超时 ({HEARTBEAT_TIMEOUT}s)"

        # 检查开始时间超时
        if started_at and not runner_heartbeat_at:
            if is_timestamp_old(started_at, STALE_TASK_TIMEOUT):
                is_stale = True
                timeout_reason = f"任务启动超时 ({STALE_TASK_TIMEOUT}s)"

        # 检查错误信息中的超时提示
        if "stale queue task" in str(error).lower() or "timeout" in str(error).lower():
            is_stale = True
            timeout_reason = "错误信息显示超时"

        if is_stale:
            stale_tasks.append(
                {
                    "queue_id": data.get("queue_id", ""),
                    "queue_path": queue_path,
                    "item_id": item_id,
                    "item_data": item_data,
                    "timeout_reason": timeout_reason,
                    "status": status,
                    "error": error,
                    "summary": summary,
                    "started_at": started_at,
                    "runner_heartbeat_at": runner_heartbeat_at,
                }
            )

    return stale_tasks


def fix_stale_task(stale_task, retry_count=0):
    """修复超时任务"""
    queue_path = stale_task["queue_path"]
    item_id = stale_task["item_id"]
    queue_id = stale_task["queue_id"]

    print(f"\n🔄 修复超时任务: {queue_id}/{item_id}")
    print(f"   超时原因: {stale_task['timeout_reason']}")
    print(f"   当前状态: {stale_task['status']}")
    print(f"   错误信息: {stale_task.get('error', '无')}")

    # 加载队列数据
    data = load_json_file(queue_path)
    if not data:
        print(f"❌ 无法加载队列数据")
        return False

    items = data.get("items", {})
    if item_id not in items:
        print(f"❌ 任务 {item_id} 不存在于队列中")
        return False

    item_data = items[item_id]

    # 检查重试次数
    retries = item_data.get("retry_count", 0)
    if retries >= AUTO_RETRY_LIMIT:
        print(f"⚠️  已达到最大重试次数 ({AUTO_RETRY_LIMIT})，标记为失败")
        item_data["status"] = "failed"
        item_data["error"] = (
            f"达到最大重试次数 ({AUTO_RETRY_LIMIT})，原始错误: {item_data.get('error', '超时')}"
        )
        item_data["finished_at"] = now_iso()
        save_json_file(queue_path, data)
        return False

    # 检查是否可以重试
    error_text = str(item_data.get("error", "")).lower()
    summary_text = str(item_data.get("summary", "")).lower()

    # 不可重试的错误类型
    non_retryable_patterns = [
        "config_error",
        "validation_error",
        "invalid config",
        "配置错误",
        "业务逻辑错误",
        "preflight_reject_manual",
    ]

    for pattern in non_retryable_patterns:
        if pattern in error_text or pattern in summary_text:
            print(f"⚠️  不可重试的错误类型: {pattern}")
            item_data["status"] = "failed"
            item_data["finished_at"] = now_iso()
            save_json_file(queue_path, data)
            return False

    # 执行重试
    print(f"🔄 执行第 {retries + 1} 次重试 (共 {AUTO_RETRY_LIMIT} 次)")

    # 指数退避等待
    cooldown = AUTO_RETRY_COOLDOWN * (2**retries)  # 指数退避
    print(f"⏳ 等待 {cooldown} 秒后重试...")
    time.sleep(min(cooldown, 300))  # 最多等待5分钟

    # 重置任务状态
    item_data["status"] = "pending"
    item_data["error"] = ""
    item_data["summary"] = f"自动重试 {retries + 1}/{AUTO_RETRY_LIMIT}"
    item_data["retry_count"] = retries + 1
    item_data["last_retry_at"] = now_iso()

    # 清除过时的运行器信息
    if "runner_pid" in item_data:
        item_data["runner_pid"] = ""
    if "runner_heartbeat_at" in item_data:
        item_data["runner_heartbeat_at"] = ""
    if "finished_at" in item_data:
        del item_data["finished_at"]

    # 保存更新
    save_json_file(queue_path, data)

    print(f"✅ 任务 {item_id} 已重置为 pending 状态，等待重新执行")
    print(f"📝 重试记录: {retries + 1}/{AUTO_RETRY_LIMIT}")

    return True


def analyze_all_queues():
    """分析所有队列文件"""
    print("🔍 开始分析所有队列文件中的超时任务...")

    all_stale_tasks = []
    for queue_file in QUEUE_DIR.glob("*.json"):
        if queue_file.name.endswith(".lock"):
            continue

        stale_tasks = analyze_queue_file(queue_file)
        all_stale_tasks.extend(stale_tasks)

    print(f"\n📊 分析完成:")
    print(f"   队列文件数: {len(list(QUEUE_DIR.glob('*.json')))}")
    print(f"   发现超时任务: {len(all_stale_tasks)}")

    if all_stale_tasks:
        print("\n📋 超时任务列表:")
        for i, task in enumerate(all_stale_tasks, 1):
            print(f"  {i}. {task['queue_id']}/{task['item_id']}")
            print(f"     状态: {task['status']}")
            print(f"     超时原因: {task['timeout_reason']}")
            print(f"     开始时间: {task['started_at']}")
            print(f"     最后心跳: {task['runner_heartbeat_at']}")
            print()

    return all_stale_tasks


def fix_all_stale_tasks(dry_run=False):
    """修复所有超时任务"""
    stale_tasks = analyze_all_queues()

    if not stale_tasks:
        print("✅ 未发现超时任务")
        return True

    if dry_run:
        print("\n🔧 模拟修复模式 (dry-run):")
        for task in stale_tasks:
            print(f"  - 将修复: {task['queue_id']}/{task['item_id']}")
            print(f"    操作: 重置为 pending 状态，重试计数+1")
        return True

    print(f"\n🔧 开始修复 {len(stale_tasks)} 个超时任务...")

    fixed_count = 0
    failed_count = 0

    for task in stale_tasks:
        try:
            if fix_stale_task(task):
                fixed_count += 1
            else:
                failed_count += 1
        except Exception as e:
            print(f"❌ 修复任务失败 {task['queue_id']}/{task['item_id']}: {e}")
            failed_count += 1

    print(f"\n📈 修复结果:")
    print(f"   成功修复: {fixed_count}")
    print(f"   修复失败: {failed_count}")
    print(f"   总任务数: {len(stale_tasks)}")

    return failed_count == 0


def check_queue_runner_status():
    """检查队列运行器状态"""
    print("\n🔍 检查队列运行器状态...")

    try:
        # 检查athena_ai_plan_runner进程
        result = subprocess.run(["ps", "aux"], capture_output=True, text=True, check=True)

        runner_processes = []
        for line in result.stdout.split("\n"):
            if "athena_ai_plan_runner" in line and "grep" not in line:
                runner_processes.append(line.strip())

        if runner_processes:
            print("✅ Athena AI Plan Runner 正在运行:")
            for proc in runner_processes:
                print(f"  - {proc}")
        else:
            print("❌ Athena AI Plan Runner 未运行")

        return len(runner_processes) > 0

    except Exception as e:
        print(f"❌ 检查运行器状态失败: {e}")
        return False


def implement_exponential_backoff_retry():
    """实现指数退避重试机制模块"""
    print("\n🔧 实现指数退避重试机制...")

    retry_module_path = Path("/Volumes/1TB-M2/openclaw/scripts/retry_mechanism.py")

    retry_code = '''#!/usr/bin/env python3
"""
指数退避重试机制模块
基于《多Agent系统24小时压力测试问题修复实施方案》1.3节实现
"""

import time
import random
import logging
from typing import Callable, Any, Optional, Dict, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class RetryableErrorType(Enum):
    """可重试错误类型"""
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    NETWORK_ERROR = "network_error"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    TEMPORARY_ERROR = "temporary_error"

class NonRetryableErrorType(Enum):
    """不可重试错误类型"""
    CONFIG_ERROR = "config_error"
    VALIDATION_ERROR = "validation_error"
    INVALID_CONFIG = "invalid_config"
    LOGIC_ERROR = "logic_error"
    PERMISSION_DENIED = "permission_denied"

@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    backoff_factor: float = 2.0
    initial_delay: float = 1.0
    max_delay: float = 60.0
    jitter: bool = True
    retryable_errors: List[str] = None
    non_retryable_errors: List[str] = None
    
    def __post_init__(self):
        if self.retryable_errors is None:
            self.retryable_errors = [
                "timeout", "rate_limit", "network error", 
                "connection refused", "resource exhausted",
                "temporary error", "stale queue task"
            ]
        if self.non_retryable_errors is None:
            self.non_retryable_errors = [
                "config_error", "validation_error", "invalid config",
                "业务逻辑错误", "权限不足", "preflight_reject_manual"
            ]

class ExponentialBackoffRetry:
    """指数退避重试机制"""
    
    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()
        self.attempts = 0
        
    def is_retryable_error(self, error_message: str) -> bool:
        """判断错误是否可重试"""
        error_lower = error_message.lower()
        
        # 检查不可重试错误
        for pattern in self.config.non_retryable_errors:
            if pattern.lower() in error_lower:
                logger.debug(f"错误不可重试 (匹配 '{pattern}'): {error_message}")
                return False
        
        # 检查可重试错误
        for pattern in self.config.retryable_errors:
            if pattern.lower() in error_lower:
                logger.debug(f"错误可重试 (匹配 '{pattern}'): {error_message}")
                return True
        
        # 默认：未知错误视为可重试
        logger.debug(f"未知错误类型，默认视为可重试: {error_message}")
        return True
    
    def calculate_backoff(self, attempt: int) -> float:
        """计算退避时间"""
        delay = self.config.initial_delay * (self.config.backoff_factor ** attempt)
        
        # 添加抖动
        if self.config.jitter:
            jitter = random.uniform(0.8, 1.2)
            delay *= jitter
        
        # 限制最大延迟
        return min(delay, self.config.max_delay)
    
    def execute_with_retry(
        self, 
        func: Callable[[], Any],
        on_retry: Optional[Callable[[int, float, Exception], None]] = None,
        should_retry: Optional[Callable[[Exception], bool]] = None
    ) -> Any:
        """执行函数并自动重试"""
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"重试尝试 {attempt}/{self.config.max_retries}")
                
                result = func()
                
                # 如果这是重试后的成功，记录成功信息
                if attempt > 0:
                    logger.info(f"重试成功 (尝试 {attempt})")
                
                return result
                
            except Exception as e:
                last_exception = e
                error_message = str(e)
                
                # 检查是否应该重试
                should_retry_flag = False
                if should_retry:
                    should_retry_flag = should_retry(e)
                else:
                    should_retry_flag = self.is_retryable_error(error_message)
                
                # 检查是否达到最大重试次数
                if attempt >= self.config.max_retries or not should_retry_flag:
                    break
                
                # 计算等待时间
                wait_time = self.calculate_backoff(attempt)
                logger.warning(f"尝试 {attempt + 1} 失败: {error_message}")
                logger.info(f"等待 {wait_time:.2f} 秒后重试...")
                
                # 调用重试回调
                if on_retry:
                    try:
                        on_retry(attempt, wait_time, e)
                    except Exception:
                        pass
                
                # 等待
                time.sleep(wait_time)
        
        # 如果所有重试都失败，抛出最后一个异常
        logger.error(f"所有 {self.config.max_retries} 次重试均失败")
        raise last_exception

class TaskRetryManager:
    """任务重试管理器"""
    
    def __init__(self):
        self.retry_configs = {}
        self.task_retry_history = {}
        
    def get_retry_config(self, task_type: str) -> RetryConfig:
        """获取任务类型的重试配置"""
        if task_type in self.retry_configs:
            return self.retry_configs[task_type]
        
        # 默认配置
        if task_type == "build":
            config = RetryConfig(
                max_retries=3,
                backoff_factor=2.0,
                initial_delay=2.0,
                max_delay=300.0,  # 5分钟
                retryable_errors=["timeout", "rate_limit", "network error"],
                non_retryable_errors=["config_error", "validation_error"]
            )
        elif task_type == "review":
            config = RetryConfig(
                max_retries=2,
                backoff_factor=1.5,
                initial_delay=5.0,
                max_delay=120.0,
                retryable_errors=["timeout", "rate_limit"],
                non_retryable_errors=["validation_error", "logic_error"]
            )
        else:
            config = RetryConfig()
        
        self.retry_configs[task_type] = config
        return config
    
    def record_retry_attempt(self, task_id: str, attempt: int, success: bool, error: str = ""):
        """记录重试尝试"""
        if task_id not in self.task_retry_history:
            self.task_retry_history[task_id] = []
        
        self.task_retry_history[task_id].append({
            "timestamp": time.time(),
            "attempt": attempt,
            "success": success,
            "error": error
        })
    
    def get_task_retry_summary(self, task_id: str) -> Dict:
        """获取任务重试摘要"""
        if task_id not in self.task_retry_history:
            return {"total_attempts": 0, "successful_attempts": 0}
        
        history = self.task_retry_history[task_id]
        total = len(history)
        successful = sum(1 for entry in history if entry["success"])
        
        return {
            "total_attempts": total,
            "successful_attempts": successful,
            "last_attempt": history[-1] if history else None
        }

# 全局重试管理器实例
_retry_manager = TaskRetryManager()

def get_retry_manager() -> TaskRetryManager:
    """获取全局重试管理器"""
    return _retry_manager

def retry_with_exponential_backoff(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_errors: List[str] = None,
    non_retryable_errors: List[str] = None
):
    """重试装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            config = RetryConfig(
                max_retries=max_retries,
                backoff_factor=backoff_factor,
                initial_delay=initial_delay,
                max_delay=max_delay,
                retryable_errors=retryable_errors,
                non_retryable_errors=non_retryable_errors
            )
            
            retry_mechanism = ExponentialBackoffRetry(config)
            
            def func_wrapper():
                return func(*args, **kwargs)
            
            return retry_mechanism.execute_with_retry(func_wrapper)
        return wrapper
    return decorator

# 使用示例
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # 示例1: 使用装饰器
    @retry_with_exponential_backoff(max_retries=3, initial_delay=1.0)
    def example_function():
        import random
        if random.random() < 0.7:
            raise Exception("模拟超时错误")
        return "成功"
    
    try:
        result = example_function()
        print(f"结果: {result}")
    except Exception as e:
        print(f"所有重试失败: {e}")
    
    # 示例2: 直接使用重试管理器
    manager = get_retry_manager()
    config = manager.get_retry_config("build")
    retry_mechanism = ExponentialBackoffRetry(config)
    
    def task_function():
        # 模拟任务执行
        raise Exception("rate_limit: 超过API限制")
    
    try:
        retry_mechanism.execute_with_retry(task_function)
    except Exception as e:
        print(f"任务执行失败: {e}")
'''

    try:
        retry_module_path.write_text(retry_code, encoding="utf-8")
        print(f"✅ 指数退避重试机制模块已创建: {retry_module_path}")

        # 使文件可执行
        retry_module_path.chmod(0o755)

        return True
    except Exception as e:
        print(f"❌ 创建重试机制模块失败: {e}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="修复超时队列任务")
    parser.add_argument("--dry-run", action="store_true", help="模拟运行，不实际修改")
    parser.add_argument("--fix", action="store_true", help="执行修复")
    parser.add_argument("--analyze", action="store_true", help="仅分析")
    parser.add_argument("--check-runner", action="store_true", help="检查运行器状态")
    parser.add_argument("--implement-retry", action="store_true", help="实现重试机制")
    parser.add_argument("--all", action="store_true", help="执行完整修复流程")

    args = parser.parse_args()

    print("🚀 多Agent系统超时任务修复工具")
    print("基于《多Agent系统24小时压力测试问题修复实施方案》第一阶段")
    print("=" * 60)

    if args.all:
        # 执行完整修复流程
        print("执行完整修复流程...")

        # 1. 检查运行器状态
        check_queue_runner_status()

        # 2. 分析超时任务
        stale_tasks = analyze_all_queues()

        # 3. 修复超时任务
        if stale_tasks and not args.dry_run:
            fix_all_stale_tasks(dry_run=args.dry_run)

        # 4. 实现重试机制
        implement_exponential_backoff_retry()

        print("\n✅ 完整修复流程完成")

    elif args.check_runner:
        check_queue_runner_status()

    elif args.implement_retry:
        implement_exponential_backoff_retry()

    elif args.analyze:
        analyze_all_queues()

    elif args.fix:
        fix_all_stale_tasks(dry_run=args.dry_run)

    else:
        # 默认执行分析
        stale_tasks = analyze_all_queues()
        if stale_tasks:
            print("\n💡 使用 --fix 参数来修复超时任务")
            print("💡 使用 --dry-run 参数模拟修复")
            print("💡 使用 --all 参数执行完整修复流程")


if __name__ == "__main__":
    main()
