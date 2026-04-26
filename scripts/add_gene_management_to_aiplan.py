#!/usr/bin/env python3
"""
将Athena/Open Human基因管理Agent工程实施方案编排进AI Plan任务队列
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path


def get_aiplan_directory():
    """获取AI Plan目录路径"""
    aiplan_path = Path(
        "/Volumes/1TB-M2/openclaw/Documents/Athena知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan"
    )
    if not aiplan_path.exists():
        print(f"❌ AI Plan目录不存在: {aiplan_path}")
        sys.exit(1)
    return aiplan_path


def get_queue_files(aiplan_dir):
    """获取队列文件路径"""
    return {
        "build_queue": aiplan_dir / "OpenHuman-AIPlan-优先执行队列.queue.json",
        "audit_queue": aiplan_dir / "OpenHuman-AIPlan-Codex审计队列.queue.json",
        "plan_queue": aiplan_dir / "OpenHuman-AIPlan-自动策划队列.queue.json",
    }


def create_gene_management_tasks():
    """创建基因管理任务配置"""

    gene_management_tasks = [
        # G0阶段: 基础设施搭建 (最高优先级)
        {
            "id": "gene_mgmt_g0_infrastructure",
            "title": "OpenHuman-Athena-基因管理系统G0阶段基础设施搭建-VSCode执行指令",
            "instruction_path": "/Volumes/1TB-M2/openclaw/OpenHuman-Athena-OpenHuman基因管理Agent工程实施方案-VSCode执行指令.md",
            "entry_stage": "build",
            "risk_level": "low",
            "unattended_allowed": True,
            "targets": [],
            "metadata": {
                "priority": "S0",
                "lane": "build_auto",
                "epic": "gene_management",
                "category": "infrastructure",
                "rationale": "基因管理系统的基础设施搭建是后续演进的前提，需要最高优先级执行",
                "depends_on": [],
                "autostart": True,
                "generated_by": "gene_management_plan",
                "estimated_duration": "30分钟",
                "phase": "G0",
            },
        },
        # G1阶段: CLI命令实现
        {
            "id": "gene_mgmt_g1_cli_implementation",
            "title": "OpenHuman-Athena-基因管理系统G1阶段CLI命令实现-VSCode执行指令",
            "instruction_path": "/Volumes/1TB-M2/openclaw/OpenHuman-Athena-OpenHuman基因管理Agent工程实施方案-VSCode执行指令.md",
            "entry_stage": "build",
            "risk_level": "low",
            "unattended_allowed": True,
            "targets": [],
            "metadata": {
                "priority": "S0",
                "lane": "build_auto",
                "epic": "gene_management",
                "category": "cli_implementation",
                "rationale": "CLI命令是基因管理系统的主要操作界面，需要优先实现",
                "depends_on": ["gene_mgmt_g0_infrastructure"],
                "autostart": True,
                "generated_by": "gene_management_plan",
                "estimated_duration": "1小时",
                "phase": "G1",
            },
        },
        # G2阶段: 队列系统集成
        {
            "id": "gene_mgmt_g2_queue_integration",
            "title": "OpenHuman-Athena-基因管理系统G2阶段队列集成-VSCode执行指令",
            "instruction_path": "/Volumes/1TB-M2/openclaw/OpenHuman-Athena-OpenHuman基因管理Agent工程实施方案-VSCode执行指令.md",
            "entry_stage": "build",
            "risk_level": "medium",
            "unattended_allowed": True,
            "targets": [],
            "metadata": {
                "priority": "S1",
                "lane": "build_auto",
                "epic": "gene_management",
                "category": "queue_integration",
                "rationale": "队列集成确保基因管理系统与现有AI Plan工作流无缝对接",
                "depends_on": ["gene_mgmt_g1_cli_implementation"],
                "autostart": True,
                "generated_by": "gene_management_plan",
                "estimated_duration": "45分钟",
                "phase": "G2",
            },
        },
        # 基因管理审计任务
        {
            "id": "gene_mgmt_audit",
            "title": "OpenHuman-Athena-基因管理系统实施审计-Codex审计指令",
            "instruction_path": "/Volumes/1TB-M2/openclaw/OpenHuman-Athena-OpenHuman基因管理Agent工程实施方案-VSCode执行指令.md",
            "entry_stage": "review",
            "risk_level": "low",
            "unattended_allowed": False,
            "targets": [],
            "metadata": {
                "priority": "R1",
                "lane": "review_auto",
                "epic": "gene_management",
                "category": "implementation_audit",
                "rationale": "审计基因管理系统实施效果，确保各阶段功能符合预期",
                "depends_on": ["gene_mgmt_g2_queue_integration"],
                "autostart": True,
                "generated_by": "gene_management_plan",
                "estimated_duration": "30分钟",
                "phase": "Audit",
            },
        },
    ]

    return gene_management_tasks


def update_build_queue(build_queue_path, gene_tasks):
    """更新构建队列"""

    print(f"📝 更新构建队列: {build_queue_path}")

    # 读取现有队列
    with open(build_queue_path, "r", encoding="utf-8") as f:
        queue_data = json.load(f)

    # 添加基因管理任务到队列首位
    existing_items = queue_data.get("items", [])

    # 过滤出基因管理相关的构建任务
    build_gene_tasks = [task for task in gene_tasks if task["entry_stage"] == "build"]

    # 将基因管理任务插入到队列开头
    updated_items = build_gene_tasks + existing_items
    queue_data["items"] = updated_items

    # 更新队列元数据
    queue_data["updated_at"] = datetime.now().isoformat()
    queue_data["description"] = "包含基因管理系统实施的优先执行队列"

    # 保存更新
    with open(build_queue_path, "w", encoding="utf-8") as f:
        json.dump(queue_data, f, indent=2, ensure_ascii=False)

    print(f"✅ 构建队列已更新，添加了 {len(build_gene_tasks)} 个基因管理任务")

    return queue_data


def update_audit_queue(audit_queue_path, gene_tasks):
    """更新审计队列"""

    print(f"📝 更新审计队列: {audit_queue_path}")

    # 读取现有队列
    with open(audit_queue_path, "r", encoding="utf-8") as f:
        queue_data = json.load(f)

    # 添加基因管理审计任务
    existing_items = queue_data.get("items", [])

    # 过滤出审计任务
    audit_gene_tasks = [task for task in gene_tasks if task["entry_stage"] == "review"]

    # 将审计任务添加到队列
    updated_items = audit_gene_tasks + existing_items
    queue_data["items"] = updated_items

    # 更新队列元数据
    queue_data["updated_at"] = datetime.now().isoformat()
    queue_data["description"] = "包含基因管理系统审计的Codex审计队列"

    # 保存更新
    with open(audit_queue_path, "w", encoding="utf-8") as f:
        json.dump(queue_data, f, indent=2, ensure_ascii=False)

    print(f"✅ 审计队列已更新，添加了 {len(audit_gene_tasks)} 个基因管理审计任务")

    return queue_data


def create_queue_state_file(gene_tasks):
    """创建队列状态文件"""

    queue_state_dir = Path("/Volumes/1TB-M2/openclaw/.openclaw/plan_queue")
    queue_state_dir.mkdir(parents=True, exist_ok=True)

    queue_state_path = queue_state_dir / "openhuman_aiplan_gene_management_20260405.json"

    queue_state = {
        "queue_id": "openhuman_aiplan_gene_management_20260405",
        "name": "OpenHuman AIPlan 基因管理队列",
        "description": "基因管理系统实施的专用队列",
        "runner_mode": "opencode_build",
        "queue_status": "running",
        "current_item_id": "gene_mgmt_g0_infrastructure",
        "current_item_ids": ["gene_mgmt_g0_infrastructure"],
        "pause_reason": "",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "items": {},
        "counts": {
            "pending": len([t for t in gene_tasks if t["entry_stage"] == "build"]),
            "running": 1,
            "completed": 0,
            "failed": 0,
            "manual_hold": 0,
        },
    }

    # 添加任务项
    for task in gene_tasks:
        queue_state["items"][task["id"]] = {
            "id": task["id"],
            "title": task["title"],
            "instruction_path": task["instruction_path"],
            "status": "pending" if task["id"] != "gene_mgmt_g0_infrastructure" else "running",
            "progress_percent": 0,
            "started_at": (
                datetime.now().isoformat() if task["id"] == "gene_mgmt_g0_infrastructure" else ""
            ),
            "finished_at": "",
            "runner_pid": "",
            "runner_heartbeat_at": "",
            "metadata": task["metadata"],
        }

    # 保存队列状态
    with open(queue_state_path, "w", encoding="utf-8") as f:
        json.dump(queue_state, f, indent=2, ensure_ascii=False)

    print(f"✅ 队列状态文件已创建: {queue_state_path}")

    return queue_state_path


def update_auto_queue_config(aiplan_dir, gene_tasks):
    """更新自动队列配置"""

    auto_queue_path = aiplan_dir / ".athena-auto-queue.json"

    if auto_queue_path.exists():
        with open(auto_queue_path, "r", encoding="utf-8") as f:
            auto_queue_config = json.load(f)
    else:
        auto_queue_config = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "routes": [],
        }

    # 添加基因管理队列路由
    gene_route = {
        "route_id": "aiplan_gene_management",
        "manifest_path": str(aiplan_dir / "OpenHuman-AIPlan-基因管理队列.queue.json"),
        "queue_id": "openhuman_aiplan_gene_management_20260405",
        "name": "OpenHuman AIPlan 基因管理队列",
        "runner_mode": "opencode_build",
        "defaults": {"entry_stage": "build", "risk_level": "low", "unattended_allowed": True},
    }

    # 检查是否已存在该路由
    existing_routes = [
        r for r in auto_queue_config.get("routes", []) if r["route_id"] == "aiplan_gene_management"
    ]
    if not existing_routes:
        auto_queue_config["routes"].append(gene_route)
        auto_queue_config["updated_at"] = datetime.now().isoformat()

        with open(auto_queue_path, "w", encoding="utf-8") as f:
            json.dump(auto_queue_config, f, indent=2, ensure_ascii=False)

        print("✅ 自动队列配置已更新")
    else:
        print("ℹ️  基因管理路由已存在")

    return auto_queue_config


def main():
    """主函数"""

    print("=" * 60)
    print("🧬 Athena/Open Human基因管理Agent工程实施方案队列编排")
    print("=" * 60)

    # 获取AI Plan目录
    aiplan_dir = get_aiplan_directory()
    print(f"📁 AI Plan目录: {aiplan_dir}")

    # 获取队列文件
    queue_files = get_queue_files(aiplan_dir)

    # 创建基因管理任务配置
    gene_tasks = create_gene_management_tasks()
    print(f"📋 创建了 {len(gene_tasks)} 个基因管理任务")

    # 更新构建队列
    build_queue_data = update_build_queue(queue_files["build_queue"], gene_tasks)

    # 更新审计队列
    audit_queue_data = update_audit_queue(queue_files["audit_queue"], gene_tasks)

    # 创建队列状态文件
    queue_state_path = create_queue_state_file(gene_tasks)

    # 更新自动队列配置
    auto_queue_config = update_auto_queue_config(aiplan_dir, gene_tasks)

    # 输出总结
    print("\n" + "=" * 60)
    print("🎉 基因管理Agent工程实施方案队列编排完成!")
    print("=" * 60)

    print("\n📊 编排结果总结:")
    print(
        f"✅ 构建队列: 添加了 {len([t for t in gene_tasks if t['entry_stage'] == 'build'])} 个任务"
    )
    print(
        f"✅ 审计队列: 添加了 {len([t for t in gene_tasks if t['entry_stage'] == 'review'])} 个任务"
    )
    print(f"✅ 队列状态: {queue_state_path}")
    print(f"✅ 自动配置: 基因管理路由已添加")

    print("\n🎯 任务执行顺序:")
    for i, task in enumerate(gene_tasks, 1):
        phase = task["metadata"].get("phase", "Unknown")
        print(f"{i}. {task['title']} ({phase}阶段)")

    print("\n🔗 监控地址:")
    print("http://127.0.0.1:8080 - 查看队列状态和执行进度")

    print("\n🚀 下一步操作:")
    print("1. 访问监控界面查看基因管理任务状态")
    print("2. 等待队列运行器自动执行任务")
    print("3. 监控各阶段实施效果")


if __name__ == "__main__":
    main()
