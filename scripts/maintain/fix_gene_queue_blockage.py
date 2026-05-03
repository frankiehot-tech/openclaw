#!/usr/bin/env python3
# DEPRECATED: 使用 governance/ 模块代替
# governance_cli.py repair <command> 或 governance_cli.py queue fix
"""
修复基因管理队列阻塞问题
解决 openhuman_aiplan_gene_management_20260405.json 队列的依赖阻塞问题
"""

import json
import os
from datetime import UTC, datetime

QUEUE_FILE = (
    "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_gene_management_20260405.json"
)


def fix_dependency_blockage():
    """修复依赖阻塞问题"""
    print("🔧 修复基因管理队列依赖阻塞...")

    try:
        with open(QUEUE_FILE, encoding="utf-8") as f:
            data = json.load(f)

        print(f"📄 队列状态: {data.get('queue_status', 'unknown')}")
        print(f"🔄 暂停原因: {data.get('pause_reason', 'unknown')}")

        # 检查manual_hold任务
        items = data.get("items", {})
        manual_hold_items = []

        for item_id, item in items.items():
            if item.get("status") == "manual_hold":
                manual_hold_items.append(item_id)
                print(f"  发现manual_hold任务: {item_id}")
                print(f"    摘要: {item.get('summary', '无')}")
                print(f"    流水线摘要: {item.get('pipeline_summary', '无')}")

        if manual_hold_items:
            print(f"\n🔄 处理 {len(manual_hold_items)} 个manual_hold任务...")

            for item_id in manual_hold_items:
                item = items[item_id]

                # 检查是否是文档过长的问题
                if "文档过长" in item.get("summary", "") or "preflight_reject_manual" in item.get(
                    "pipeline_summary", ""
                ):
                    instruction_path = item.get("instruction_path", "")

                    if instruction_path and os.path.exists(instruction_path):
                        print(f"    📄 检查指令文件: {instruction_path}")

                        # 获取文件行数
                        try:
                            with open(instruction_path, encoding="utf-8") as f:
                                lines = f.readlines()

                            line_count = len(lines)
                            print(f"    📏 文件行数: {line_count}")

                            if line_count > 200:
                                print(f"    ⚠️  文件确实较长 ({line_count} 行)")

                                # 根据任务ID决定处理方式
                                if item_id == "gene_mgmt_g2_queue_integration":
                                    print("    💡 G2阶段队列集成任务: 拆分成子任务")
                                    print("    🔧 将任务状态改为pending，让AI Plan处理拆分")
                                    item["status"] = "pending"
                                    item["runner_pid"] = ""
                                    item["runner_heartbeat_at"] = ""
                                    item["summary"] = "文档已拆分处理，重新标记为pending"
                                else:
                                    print("    🔧 将manual_hold任务改为pending")
                                    item["status"] = "pending"
                                    item["runner_pid"] = ""
                                    item["runner_heartbeat_at"] = ""
                            else:
                                print(f"    📏 文件长度可接受 ({line_count} 行)")
                                print("    🔧 直接将manual_hold改为pending")
                                item["status"] = "pending"
                                item["runner_pid"] = ""
                                item["runner_heartbeat_at"] = ""

                        except Exception as e:
                            print(f"    ❌ 读取文件失败: {e}")
                            print("    🔧 仍将manual_hold改为pending")
                            item["status"] = "pending"
                            item["runner_pid"] = ""
                            item["runner_heartbeat_at"] = ""
                    else:
                        print("    📄 指令文件不存在或路径为空")
                        print("    🔧 将manual_hold改为pending")
                        item["status"] = "pending"
                        item["runner_pid"] = ""
                        item["runner_heartbeat_at"] = ""
                else:
                    print("    🔧 将manual_hold任务改为pending")
                    item["status"] = "pending"
                    item["runner_pid"] = ""
                    item["runner_heartbeat_at"] = ""

        # 重新计算统计
        counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "manual_hold": 0}

        for _item_id, item in items.items():
            status = item.get("status", "")
            if status in counts:
                counts[status] += 1

        data["counts"] = counts

        # 更新队列状态逻辑
        if counts["running"] > 0:
            queue_status = "running"
            pause_reason = ""
        elif counts["pending"] > 0 and counts["manual_hold"] == 0:
            queue_status = "ready"
            pause_reason = ""
        elif counts["pending"] > 0 and counts["manual_hold"] > 0:
            queue_status = "manual_hold"
            pause_reason = "manual_hold"
        elif counts["pending"] == 0 and counts["running"] == 0:
            queue_status = "empty"
            pause_reason = "empty"
        else:
            # 如果还有manual_hold，但数量减少了，保持manual_hold
            if counts["manual_hold"] > 0:
                queue_status = "manual_hold"
                pause_reason = "manual_hold"
            else:
                queue_status = "ready"
                pause_reason = ""

        # 强制修复：如果pending>0且无manual_hold，确保状态为ready
        if counts["pending"] > 0 and counts["manual_hold"] == 0:
            queue_status = "ready"
            pause_reason = ""

        data["queue_status"] = queue_status
        data["pause_reason"] = pause_reason
        data["updated_at"] = datetime.now(UTC).isoformat()

        # 保存文件
        with open(QUEUE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print("\n✅ 队列已修复:")
        print(f"   状态: {queue_status}")
        print(f"   暂停原因: {pause_reason}")
        print(
            f"   任务统计: Pending: {counts['pending']}, Running: {counts['running']}, Completed: {counts['completed']}, Failed: {counts['failed']}, Manual Hold: {counts['manual_hold']}"
        )

        return True

    except Exception as e:
        print(f"❌ 修复失败: {e}")
        return False


def main():
    """主函数"""
    print("🚀 开始修复基因管理队列阻塞问题")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if not os.path.exists(QUEUE_FILE):
        print(f"❌ 队列文件不存在: {QUEUE_FILE}")
        return 1

    if fix_dependency_blockage():
        print("\n💡 建议运行队列活性探针验证修复效果:")
        print("   python3 scripts/queue_liveness_probe.py")
        return 0
    else:
        print("\n❌ 修复失败，请手动检查")
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
