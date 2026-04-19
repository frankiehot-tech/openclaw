#!/usr/bin/env python3
"""
生成规范化任务ID的脚本
用于替换bash脚本中的简单任务ID生成逻辑

使用示例:
  python generate_task_id.py                        # 使用默认前缀
  python generate_task_id.py engineering-plan       # 指定前缀
"""

import json
import os
import sys

# 添加项目根目录到路径，确保能导入contracts模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from contracts.task_identity import TaskIdentity
except ImportError as e:
    print(f"ERROR: 无法导入TaskIdentity: {e}", file=sys.stderr)
    print(f"Python路径: {sys.path}", file=sys.stderr)
    sys.exit(1)


def generate_task_id(prefix="task"):
    """
    生成规范化任务ID

    Args:
        prefix: 任务前缀，默认"task"

    Returns:
        TaskIdentity对象
    """
    try:
        task_identity = TaskIdentity.generate(prefix)
        return task_identity
    except Exception as e:
        print(f"ERROR: 生成任务ID失败: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    # 解析命令行参数
    prefix = "task"  # 默认前缀

    if len(sys.argv) > 1:
        prefix = sys.argv[1]
        if prefix.startswith("-"):
            # 处理可能以'-'开头的参数
            print(f"警告: 前缀以'-'开头，这可能被误识别为flag参数", file=sys.stderr)
            print(f"将使用规范化前缀: task_{prefix[1:]}", file=sys.stderr)
            prefix = f"task_{prefix[1:]}"

    # 生成任务ID
    task_identity = generate_task_id(prefix)

    # 输出结果
    result = {
        "id": task_identity.id,
        "original_id": task_identity.original_id,
        "prefix": task_identity.prefix,
        "timestamp": task_identity.timestamp,
        "sequence": task_identity.sequence,
        "full_id": task_identity.id,  # 兼容性字段，用于bash脚本直接使用
    }

    # 根据调用方式输出不同格式
    if len(sys.argv) > 2 and sys.argv[2] == "--json":
        # 输出完整JSON
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        # 默认只输出ID（用于bash脚本直接捕获）
        print(task_identity.id)

    return 0


if __name__ == "__main__":
    sys.exit(main())
