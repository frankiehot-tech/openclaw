#!/usr/bin/env python3
"""
路径配置集中化管理模块

解决硬编码路径问题，提供统一的路径访问接口。
所有脚本应导入此模块，使用定义的路径常量。

使用示例:
    from config.paths import ROOT_DIR, PLAN_QUEUE_DIR, SCRIPTS_DIR

    # 构建队列文件路径
    queue_file = PLAN_QUEUE_DIR / "openhuman_aiplan_plan_manual_20260328.json"

    # 构建脚本路径
    runner_script = SCRIPTS_DIR / "athena_ai_plan_runner.py"

设计原则:
1. 单一事实源: 所有路径从此模块导出
2. 平台兼容: 使用pathlib.Path处理路径分隔符
3. 环境感知: 支持开发、测试、生产环境配置
4. 向后兼容: 保持现有硬编码路径的等效性
"""

import os
from pathlib import Path

# 项目根目录 (自动检测)
try:
    # 尝试从环境变量获取
    ROOT_DIR = Path(os.environ.get("OPENCLAW_ROOT", "/Volumes/1TB-M2/openclaw"))

    # 如果环境变量未设置，尝试基于当前文件位置推导
    if not ROOT_DIR.exists():
        # 假设此文件在项目根目录的config子目录中
        current_file = Path(__file__).resolve()
        ROOT_DIR = current_file.parent.parent

        # 验证推导的根目录
        if not (ROOT_DIR / ".openclaw").exists():
            raise FileNotFoundError(f"无法确定OpenClaw项目根目录: {ROOT_DIR}")

except Exception as e:
    print(f"⚠️  警告: 无法确定项目根目录: {e}")
    print("   使用默认路径: /Volumes/1TB-M2/openclaw")
    ROOT_DIR = Path("/Volumes/1TB-M2/openclaw")

# 核心目录
OPENCLAW_DIR = ROOT_DIR / ".openclaw"
CONFIG_DIR = ROOT_DIR / "config"
SCRIPTS_DIR = ROOT_DIR / "scripts"
LOGS_DIR = ROOT_DIR / "logs"
DOCS_DIR = ROOT_DIR / "docs"
ARCHIVE_DIR = ROOT_DIR / "archive"
TEMPLATES_DIR = ROOT_DIR / "templates"
VENV_DIR = ROOT_DIR / "venv"

# .openclaw子目录
PLAN_QUEUE_DIR = OPENCLAW_DIR / "plan_queue"
ARCHIVED_QUEUES_DIR = OPENCLAW_DIR / "archived_queues"
BACKUPS_DIR = OPENCLAW_DIR / "backups"
CHAT_INSTRUCTIONS_DIR = OPENCLAW_DIR / "chat_instructions"
CONFIG_STATE_DIR = OPENCLAW_DIR / "config"
FEEDBACK_STATE_DIR = OPENCLAW_DIR / "feedback_state"
HEALTH_DIR = OPENCLAW_DIR / "health"
IMPROVEMENT_LOOP_DIR = OPENCLAW_DIR / "improvement_loop"
MAREF_DIR = OPENCLAW_DIR / "maref"
ORCHESTRATOR_DIR = OPENCLAW_DIR / "orchestrator"
PLATFORMS_DIR = OPENCLAW_DIR / "platforms"
REPORTS_DIR = OPENCLAW_DIR / "reports"
SCOREBOARD_DIR = OPENCLAW_DIR / "scoreboard"
SMART_ORCHESTRATOR_DIR = OPENCLAW_DIR / "smart_orchestrator"
WORKFLOW_STATE_DIR = OPENCLAW_DIR / "workflow_state"

# 重要文件
CLAUDE_CONFIG = ROOT_DIR / "CLAUDE.md"
TASK_PLAN = ROOT_DIR / "task_plan.md"
FINDINGS = ROOT_DIR / "findings.md"
PROGRESS = ROOT_DIR / "progress.md"
AGENTS_MD = ROOT_DIR / "AGENTS.md"
TOOLS_MD = ROOT_DIR / "TOOLS.md"
HEARTBEAT_MD = ROOT_DIR / "HEARTBEAT.md"
COGNITIVE_DNA_MD = ROOT_DIR / "COGNITIVE_DNA.md"
MEMORY_MD = ROOT_DIR / "MEMORY.md"

# 脚本文件
ATHENA_AI_PLAN_RUNNER = SCRIPTS_DIR / "athena_ai_plan_runner.py"
ATHENA_WEB_DESKTOP_COMPAT = SCRIPTS_DIR / "athena_web_desktop_compat.py"
QUEUE_LIVENESS_PROBE = SCRIPTS_DIR / "queue_liveness_probe.py"
QUEUE_MONITOR = ROOT_DIR / "queue_monitor.py"
QUEUE_MONITOR_DASHBOARD = ROOT_DIR / "queue_monitor_dashboard.py"

# PID文件
ATHENA_RUNNER_PID = OPENCLAW_DIR / "athena_ai_plan_runner.pid"
ATHENA_WEB_PID = OPENCLAW_DIR / "athena_web_desktop_compat.pid"
CODEX_RUNNER_PID = OPENCLAW_DIR / "codex_plan_runner.pid"
CODEX_REVIEW_PID = OPENCLAW_DIR / "codex_review_runner.pid"

# 配置文件
CLAUDE_CODE_INTEGRATION = OPENCLAW_DIR / "claude_code_integration.json"
WORKSPACE_STATE = OPENCLAW_DIR / "workspace-state.json"
MONITOR_LOG = OPENCLAW_DIR / "monitor_log.json"

# 常用队列文件 (硬编码路径映射)
# 注意: 理想情况下应动态发现队列文件，但为保持向后兼容性提供映射
QUEUE_FILES = {
    "plan_manual": PLAN_QUEUE_DIR / "openhuman_aiplan_plan_manual_20260328.json",
    "build_priority": PLAN_QUEUE_DIR / "openhuman_aiplan_build_priority_20260328.json",
    "review_priority": PLAN_QUEUE_DIR / "openhuman_aiplan_review_priority_20260328.json",
    "qa_priority": PLAN_QUEUE_DIR / "openhuman_aiplan_qa_priority_20260328.json",
    "priority_execution": PLAN_QUEUE_DIR / "openhuman_aiplan_priority_execution_20260414.json",
    "gene_management": PLAN_QUEUE_DIR / "openhuman_aiplan_gene_management_20260405.json",
}


# 环境检测函数
def detect_environment() -> str:
    """
    检测当前运行环境

    返回:
        "development": 开发环境
        "testing": 测试环境
        "production": 生产环境
    """
    env = os.environ.get("OPENCLAW_ENV", "development")

    # 通过文件存在性验证
    if env == "production":
        if not (OPENCLAW_DIR / "production.lock").exists():
            return "development"
    elif env == "testing" and not (OPENCLAW_DIR / "test.lock").exists():
        return "development"

    return env


def get_queue_file(queue_name: str) -> Path | None:
    """
    获取队列文件路径

    参数:
        queue_name: 队列名称或队列文件名

    返回:
        Path对象或None(如果未找到)
    """
    # 尝试从映射获取
    if queue_name in QUEUE_FILES:
        return QUEUE_FILES[queue_name]

    # 尝试直接查找
    queue_path = PLAN_QUEUE_DIR / f"{queue_name}"
    if queue_path.exists():
        return queue_path

    # 尝试添加.json后缀
    queue_path = PLAN_QUEUE_DIR / f"{queue_name}.json"
    if queue_path.exists():
        return queue_path

    # 搜索匹配文件
    for file_path in PLAN_QUEUE_DIR.glob(f"*{queue_name}*.json"):
        return file_path

    return None


def get_all_queue_files() -> list[Path]:
    """获取所有队列文件"""
    return list(PLAN_QUEUE_DIR.glob("*.json"))


def get_latest_queue_file(pattern: str = "*") -> Path | None:
    """获取最新的匹配模式的队列文件"""
    files = list(PLAN_QUEUE_DIR.glob(f"*{pattern}*.json"))
    if not files:
        return None

    # 按修改时间排序
    files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return files[0]


def validate_paths() -> dict[str, bool]:
    """
    验证所有路径是否存在

    返回:
        字典: 路径名称 -> 是否存在
    """
    validation = {}

    # 核心目录
    validation["ROOT_DIR"] = ROOT_DIR.exists()
    validation["OPENCLAW_DIR"] = OPENCLAW_DIR.exists()
    validation["CONFIG_DIR"] = CONFIG_DIR.exists()
    validation["SCRIPTS_DIR"] = SCRIPTS_DIR.exists()
    validation["LOGS_DIR"] = LOGS_DIR.exists()
    validation["DOCS_DIR"] = DOCS_DIR.exists()

    # 重要文件
    validation["CLAUDE_CONFIG"] = CLAUDE_CONFIG.exists()
    validation["TASK_PLAN"] = TASK_PLAN.exists()
    validation["FINDINGS"] = FINDINGS.exists()
    validation["PROGRESS"] = PROGRESS.exists()

    # 脚本文件
    validation["ATHENA_AI_PLAN_RUNNER"] = ATHENA_AI_PLAN_RUNNER.exists()

    return validation


def print_path_summary():
    """打印路径摘要"""
    print("📁 OpenClaw路径配置摘要")
    print("=" * 60)

    env = detect_environment()
    print(f"🌍 环境: {env}")
    print(f"📦 项目根目录: {ROOT_DIR}")
    print(f"📁 .openclaw目录: {OPENCLAW_DIR}")
    print(f"📁 配置目录: {CONFIG_DIR}")
    print(f"📁 脚本目录: {SCRIPTS_DIR}")
    print(f"📁 队列目录: {PLAN_QUEUE_DIR}")

    # 统计队列文件
    queue_files = get_all_queue_files()
    print(f"📊 队列文件数量: {len(queue_files)}")

    # 验证结果
    print("\n✅ 路径验证:")
    validation = validate_paths()
    for name, exists in validation.items():
        status = "✅" if exists else "❌"
        print(f"  {status} {name}")


# 模块初始化时验证
if __name__ == "__main__":
    print_path_summary()
else:
    # 导入时静默验证
    pass
