#!/usr/bin/env python3
"""
添加基因管理队列到 AI Plan 自动队列配置
确保 Web Desktop 能够发现和显示基因管理队列
"""

import json
import os
from datetime import datetime
from pathlib import Path


def get_aiplan_directory():
    """获取 AI Plan 目录路径"""
    aiplan_paths = [
        Path(
            "/Volumes/1TB-M2/openclaw/Documents/Athena 知识库/执行项目/2026/003-open human（碳硅基共生）/007-AI-plan"
        ),
        Path("/Volumes/1TB-M2/openclaw/athena/open_human/phase1/ai_plan"),
        Path("/Volumes/1TB-M2/openclaw/ai_plan"),
    ]

    for path in aiplan_paths:
        if path.exists():
            return path

    # 如果都不存在，使用第一个路径并创建
    target_path = aiplan_paths[0]
    target_path.mkdir(parents=True, exist_ok=True)
    return target_path


def add_gene_management_to_auto_queue():
    """添加基因管理队列到自动队列配置"""

    print("🔧 正在更新自动队列配置...")

    aiplan_dir = get_aiplan_directory()
    auto_queue_file = aiplan_dir / ".athena-auto-queue.json"

    print(f"📁 AI Plan 目录：{aiplan_dir}")
    print(f"📄 自动队列配置文件：{auto_queue_file}")

    # 读取或创建自动队列配置
    if auto_queue_file.exists():
        with open(auto_queue_file, "r", encoding="utf-8") as f:
            auto_queue_config = json.load(f)
        print("✅ 读取现有自动队列配置")
    else:
        auto_queue_config = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "description": "Athena 自动队列发现配置",
            "routes": [],
        }
        print("📝 创建新的自动队列配置")

    # 检查是否已存在基因管理队列路由
    existing_route_ids = [route.get("route_id") for route in auto_queue_config.get("routes", [])]

    if "aiplan_gene_management" in existing_route_ids:
        print("ℹ️  基因管理队列已在自动队列配置中")
        return auto_queue_config

    # 创建基因管理队列路由配置
    gene_management_route = {
        "route_id": "aiplan_gene_management",
        "manifest_path": str(aiplan_dir / "OpenHuman-AIPlan-基因管理队列.queue.json"),
        "queue_id": "openhuman_aiplan_gene_management_20260405",
        "name": "OpenHuman AIPlan 基因管理队列",
        "description": "基因管理系统实施的专用队列",
        "runner_mode": "opencode_build",
        "priority": "S0",
        "enabled": True,
        "defaults": {"entry_stage": "build", "risk_level": "low", "unattended_allowed": True},
        "added_at": datetime.now().isoformat(),
    }

    # 添加到路由列表
    auto_queue_config["routes"].append(gene_management_route)
    auto_queue_config["updated_at"] = datetime.now().isoformat()

    # 保存更新后的配置
    with open(auto_queue_file, "w", encoding="utf-8") as f:
        json.dump(auto_queue_config, f, indent=2, ensure_ascii=False)

    print(f"✅ 基因管理队列已添加到自动队列配置")
    print(f"   路由 ID: {gene_management_route['route_id']}")
    print(f"   队列 ID: {gene_management_route['queue_id']}")
    print(f"   优先级：{gene_management_route['priority']}")

    return auto_queue_config


def update_web_desktop_queue_list():
    """更新 Web Desktop 队列列表"""

    print("\n🌐 更新 Web Desktop 队列列表...")

    # 检查 Web Desktop 配置文件
    web_config_paths = [
        Path("/Volumes/1TB-M2/openclaw/mini-agent/config/web_desktop_config.json"),
        Path("/Volumes/1TB-M2/openclaw/workspace/web_desktop_config.json"),
        Path("/Volumes/1TB-M2/openclaw/.openclaw/web_desktop_config.json"),
    ]

    config_updated = False
    for config_path in web_config_paths:
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    web_config = json.load(f)

                # 添加基因管理队列到显示列表
                if "queues" not in web_config:
                    web_config["queues"] = []

                queue_ids = [q.get("queue_id") for q in web_config["queues"]]
                if "openhuman_aiplan_gene_management_20260405" not in queue_ids:
                    web_config["queues"].append(
                        {
                            "queue_id": "openhuman_aiplan_gene_management_20260405",
                            "name": "基因管理队列",
                            "display_order": 1,  # 高优先级显示
                            "enabled": True,
                        }
                    )

                    with open(config_path, "w", encoding="utf-8") as f:
                        json.dump(web_config, f, indent=2, ensure_ascii=False)

                    print(f"✅ 已更新 Web Desktop 配置：{config_path}")
                    config_updated = True
                else:
                    print(f"ℹ️  基因管理队列已在 Web Desktop 配置中：{config_path}")

            except Exception as e:
                print(f"⚠️  更新 Web Desktop 配置失败 {config_path}: {e}")

    if not config_updated:
        print("⚠️  未找到或未能更新 Web Desktop 配置文件")


def verify_queue_discovery():
    """验证队列发现配置"""

    print("\n🔍 验证队列发现配置...")

    aiplan_dir = get_aiplan_directory()
    auto_queue_file = aiplan_dir / ".athena-auto-queue.json"

    if not auto_queue_file.exists():
        print("❌ 自动队列配置文件不存在")
        return False

    try:
        with open(auto_queue_file, "r", encoding="utf-8") as f:
            auto_queue_config = json.load(f)

        # 检查基因管理队列是否在配置中
        gene_route_found = False
        for route in auto_queue_config.get("routes", []):
            if route.get("route_id") == "aiplan_gene_management":
                gene_route_found = True
                print(f"✅ 基因管理队列路由已配置:")
                print(f"   路由 ID: {route['route_id']}")
                print(f"   队列 ID: {route['queue_id']}")
                print(f"   清单路径：{route['manifest_path']}")
                print(f"   优先级：{route.get('priority', 'normal')}")
                print(f"   状态：{'启用' if route.get('enabled', True) else '禁用'}")
                break

        if not gene_route_found:
            print("❌ 基因管理队列路由未在配置中找到")
            return False

        # 检查队列清单文件是否存在
        manifest_path = Path(auto_queue_config["routes"][-1]["manifest_path"])
        if manifest_path.exists():
            print(f"✅ 队列清单文件存在：{manifest_path}")
        else:
            print(f"⚠️  队列清单文件不存在：{manifest_path}")
            return False

        # 检查队列状态文件是否存在
        state_file = Path(
            "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_gene_management_20260405.json"
        )
        if state_file.exists():
            print(f"✅ 队列状态文件存在：{state_file}")
        else:
            print(f"⚠️  队列状态文件不存在：{state_file}")
            return False

        print("\n✅ 队列发现配置验证通过!")
        return True

    except Exception as e:
        print(f"❌ 验证配置失败：{e}")
        return False


def print_next_steps():
    """打印下一步操作"""

    print("\n" + "=" * 80)
    print("🎯 下一步操作")
    print("=" * 80)
    print("""
1. 刷新 Athena Web Desktop 页面
   - 访问：http://127.0.0.1:8080
   - 按 Ctrl+R 或 Cmd+R 强制刷新
   - 清除浏览器缓存（可选）

2. 检查队列列表
   - 查看是否显示 "OpenHuman AIPlan 基因管理队列"
   - 确认队列状态为 "running" 或 "待执行"
   - 查看任务列表是否包含 4 个基因管理任务

3. 如果仍未显示，尝试以下操作：
   - 重启 Web Desktop 服务
   - 重启队列运行器
   - 检查浏览器控制台是否有错误

4. 启动基因管理任务执行：
   ```bash
   # 启动队列运行器（如果未运行）
   python3 /Volumes/1TB-M2/openclaw/scripts/athena_ai_plan_runner.py
   
   # 启动监控
   python3 /Volumes/1TB-M2/openclaw/scripts/monitor_gene_management.py
   ```

5. 监控执行进度：
   - Web 界面：http://127.0.0.1:8080
   - 监控脚本：运行 monitor_gene_management.py
   - 日志文件：/Volumes/1TB-M2/openclaw/logs/
    """)


def main():
    """主函数"""

    print("=" * 80)
    print("🧬 添加基因管理队列到 Web Desktop")
    print("=" * 80)

    # 步骤 1: 添加到自动队列配置
    auto_queue_config = add_gene_management_to_auto_queue()

    # 步骤 2: 更新 Web Desktop 配置
    update_web_desktop_queue_list()

    # 步骤 3: 验证配置
    if verify_queue_discovery():
        print("\n✅ 配置更新成功!")
        print_next_steps()
    else:
        print("\n❌ 配置验证失败，请检查错误信息")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
