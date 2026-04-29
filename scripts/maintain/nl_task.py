#!/usr/bin/env python3
"""
nl_task.py — Athena 自然语言任务入口

用法:
    python scripts/nl_task.py "检查队列健康"
    python scripts/nl_task.py "运行系统审计"
    python scripts/nl_task.py "修复停滞的队列"
    python scripts/nl_task.py "激活自动研究"
    python scripts/nl_task.py --list

输出: 结构化 JSON + 自然语言总结
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 确保 agent_system 在路径中
_workspace_root = Path(__file__).resolve().parents[1]
if str(_workspace_root) not in sys.path:
    sys.path.insert(0, str(_workspace_root))

from agent_system.semantic import TaskQueueNL, parse_intent


def format_output(processed: dict, fmt: str) -> str:
    """按指定格式输出结果。"""
    if fmt == "json":
        return json.dumps(processed, indent=2, ensure_ascii=False)
    elif fmt == "text":
        tq = TaskQueueNL()
        return tq.explain(processed)
    else:
        tq = TaskQueueNL()
        return tq.explain(processed)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Athena NL Task — 自然语言转换为系统操作",
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="自然语言指令（如 '检查队列健康'）",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="禁用 LLM，仅使用关键词匹配",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出所有可用命令",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["json", "text"],
        default="text",
        help="输出格式 (default: text)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅解析意图，不执行操作",
    )

    args = parser.parse_args()

    tq = TaskQueueNL(use_llm=not args.no_llm)

    if args.list:
        commands = tq.get_intent_labels()
        print("可用命令:")
        for cmd, label in commands.items():
            print(f"  {cmd:20s} {label}")
        return 0

    if not args.input:
        parser.print_help()
        print("\n示例:")
        print('  python scripts/nl_task.py "检查队列健康"')
        print('  python scripts/nl_task.py "查看系统状态"')
        print('  python scripts/nl_task.py "修复卡住的任务"')
        print('  python scripts/nl_task.py "激活自动研究"')
        print('  python scripts/nl_task.py --list')
        return 0

    if args.dry_run:
        intent = parse_intent(args.input, use_llm=not args.no_llm)
        output = {
            "input": args.input,
            "intent": {
                "type": intent.intent.value,
                "confidence": intent.confidence,
                "entities": intent.entities,
                "explanation": intent.explanation,
            },
        }
        print(format_output(output, args.format))
        return 0

    processed = tq.process(args.input)
    print(format_output(processed, args.format))
    return 0


if __name__ == "__main__":
    sys.exit(main())
