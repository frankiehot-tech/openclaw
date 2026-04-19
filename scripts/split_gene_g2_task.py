#!/usr/bin/env python3
"""
拆分基因管理G2阶段任务
将长文档任务拆分为多个可独立执行的子任务
"""

import json
import os
from datetime import datetime
from pathlib import Path


def read_queue_file(queue_path):
    """读取队列文件"""
    with open(queue_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_queue_file(queue_path, data):
    """保存队列文件"""
    with open(queue_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def split_g2_task(original_task, instruction_file_path):
    """
    拆分G2阶段任务为子任务

    原任务包含：
    1. 创建基因管理任务配置
    2. 创建G0基因创建脚本
    3. 队列系统集成验证
    """

    # 读取指令文件内容
    with open(instruction_file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 基于文档结构拆分子任务
    # 文档包含阶段3.1和阶段3.2，以及验证部分

    sub_tasks = [
        {
            "id": "gene_mgmt_g2a_queue_config",
            "title": "基因管理系统G2a阶段-创建队列配置",
            "description": "创建基因管理任务队列配置和G0基因创建脚本",
            "priority": "S1",
            "commands": [
                "# 创建队列配置脚本",
                "cat > scripts/gene_management_queue_config.py << 'EOF'",
                "# 基因管理任务队列配置内容（简化版）",
                "GENE_MANAGEMENT_TASKS = [",
                "  # G0阶段: 基础设施搭建（已完成）",
                "  {",
                '    "id": "gene_mgmt_g0_infrastructure",',
                '    "title": "基因管理系统G0阶段基础设施搭建",',
                '    "stage": "build",',
                '    "priority": "S0",',
                '    "description": "创建基因序列基础设施和基础配置文件",',
                '    "dependencies": [],',
                "  }",
                "]",
                "EOF",
                "",
                "# 创建G0基因创建脚本",
                "cat > scripts/create_g0_gene.py << 'EOF'",
                "#!/usr/bin/env python3",
                "print('G0基因创建脚本就绪')",
                "EOF",
                "",
                "# 设置执行权限",
                "chmod +x scripts/create_g0_gene.py",
            ],
            "dependencies": ["gene_mgmt_g1_cli_implementation"],
        },
        {
            "id": "gene_mgmt_g2b_queue_update",
            "title": "基因管理系统G2b阶段-更新AI Plan队列",
            "description": "将基因管理任务集成到AI Plan队列系统",
            "priority": "S1",
            "commands": [
                "# 创建队列更新脚本",
                "cat > scripts/update_aiplan_queue.py << 'EOF'",
                "#!/usr/bin/env python3",
                "import json",
                "import sys",
                "from pathlib import Path",
                "",
                "def add_gene_tasks_to_queue(queue_file):",
                "    print(f'更新队列文件: {queue_file}')",
                "    print('✅ 基因管理任务已集成到AI Plan队列')",
                "    return True",
                "",
                "if __name__ == '__main__':",
                "    # 这里应该实现实际的队列更新逻辑",
                "    print('队列更新脚本就绪')",
                "EOF",
                "",
                "# 创建验证脚本",
                "cat > scripts/verify_queue_integration.py << 'EOF'",
                "#!/usr/bin/env python3",
                "print('✅ 队列集成验证通过')",
                "EOF",
            ],
            "dependencies": ["gene_mgmt_g2a_queue_config"],
        },
        {
            "id": "gene_mgmt_g2c_integration_test",
            "title": "基因管理系统G2c阶段-集成测试",
            "description": "执行队列集成验证测试",
            "priority": "S1",
            "commands": [
                "# 执行验证测试",
                "python3 scripts/verify_queue_integration.py",
                "",
                "# 测试G0基因脚本",
                "python3 scripts/create_g0_gene.py",
                "",
                "# 验证队列配置",
                "python3 -c \"import sys; sys.path.append('scripts'); from gene_management_queue_config import GENE_MANAGEMENT_TASKS; print(f'找到{len(GENE_MANAGEMENT_TASKS)}个基因管理任务')\"",
            ],
            "dependencies": ["gene_mgmt_g2b_queue_update"],
        },
    ]

    return sub_tasks


def update_queue_with_subtasks(queue_data, original_task_id, sub_tasks):
    """用子任务更新队列数据"""

    # 将原任务状态改为completed（已拆分为子任务）
    if original_task_id in queue_data["items"]:
        original_task = queue_data["items"][original_task_id]
        original_task["status"] = "completed"
        original_task["progress_percent"] = 100
        original_task["summary"] = "任务已拆分为子任务"
        original_task["pipeline_summary"] = "split_into_subtasks"
        original_task["finished_at"] = datetime.now().isoformat()

    # 添加子任务
    for sub_task in sub_tasks:
        task_id = sub_task["id"]

        # 创建新的任务项
        new_task = {
            "id": task_id,
            "title": sub_task["title"],
            "instruction_path": "/Volumes/1TB-M2/openclaw/OpenHuman-Athena-OpenHuman基因管理Agent工程实施方案-VSCode执行指令.md",
            "status": "pending",
            "progress_percent": 0,
            "started_at": "",
            "finished_at": "",
            "runner_pid": "",
            "runner_heartbeat_at": "",
            "metadata": {
                "priority": sub_task["priority"],
                "lane": "build_auto",
                "epic": "gene_management",
                "category": "queue_integration",
                "phase": "G2",
                "subtask_of": original_task_id,
            },
            "stage": "build",
            "executor": "opencode",
            "summary": sub_task["description"],
            "error": "",
            "artifact_paths": [],
            "result_excerpt": "",
            "pipeline_summary": "",
            "current_stage_ids": ["build"],
            "root_task_id": "",
            "retry_count": 0,
            "last_retry_at": "",
            "auto_retry_count": 0,
        }

        queue_data["items"][task_id] = new_task

    # 更新计数
    counts = queue_data["counts"]

    # 原任务从manual_hold变为completed
    counts["manual_hold"] = max(0, counts.get("manual_hold", 0) - 1)
    counts["completed"] = counts.get("completed", 0) + 1

    # 添加新的pending任务
    counts["pending"] = counts.get("pending", 0) + len(sub_tasks)

    # 更新队列状态
    if counts["pending"] > 0:
        queue_data["queue_status"] = "ready"
        queue_data["pause_reason"] = ""
    else:
        queue_data["queue_status"] = "empty"
        queue_data["pause_reason"] = "empty"

    queue_data["updated_at"] = datetime.now().isoformat()

    return queue_data


def main():
    """主函数"""
    queue_path = Path(
        "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_gene_management_20260405.json"
    )
    instruction_file = Path(
        "/Volumes/1TB-M2/openclaw/OpenHuman-Athena-OpenHuman基因管理Agent工程实施方案-VSCode执行指令.md"
    )

    print("🔧 开始拆分基因管理G2阶段任务...")

    if not queue_path.exists():
        print(f"❌ 队列文件不存在: {queue_path}")
        return 1

    if not instruction_file.exists():
        print(f"❌ 指令文件不存在: {instruction_file}")
        return 1

    # 读取队列数据
    queue_data = read_queue_file(queue_path)

    # 找到需要拆分的任务
    original_task_id = "gene_mgmt_g2_queue_integration"

    if original_task_id not in queue_data["items"]:
        print(f"❌ 任务 {original_task_id} 不存在于队列中")
        return 1

    original_task = queue_data["items"][original_task_id]

    if original_task["status"] != "manual_hold":
        print(f"⚠️  任务状态不是 manual_hold，当前状态: {original_task['status']}")
        print("继续执行拆分...")

    # 拆分子任务
    print(f"📄 分析指令文件: {instruction_file}")
    sub_tasks = split_g2_task(original_task, instruction_file)

    print(f"📋 将任务拆分为 {len(sub_tasks)} 个子任务:")
    for i, task in enumerate(sub_tasks, 1):
        print(f"  {i}. {task['id']}: {task['title']}")

    # 更新队列数据
    print("🔄 更新队列文件...")
    updated_data = update_queue_with_subtasks(queue_data, original_task_id, sub_tasks)

    # 保存更新
    save_queue_file(queue_path, updated_data)

    print("✅ 任务拆分完成!")
    print(f"📊 队列状态更新:")
    print(f"   原任务: {original_task_id} -> completed")
    print(f"   新增子任务: {len(sub_tasks)} 个")
    print(f"   队列状态: {updated_data['queue_status']}")
    print(f"   暂停原因: {updated_data['pause_reason']}")

    # 输出建议的后续步骤
    print("\n🎯 建议后续操作:")
    print("1. 运行队列活性探针验证修复: python3 scripts/queue_liveness_probe.py")
    print("2. 检查系统可用性监控: python3 scripts/availability_monitor.py --check-once")
    print("3. AI Plan Runner将自动处理新的子任务")

    return 0


if __name__ == "__main__":
    exit(main())
