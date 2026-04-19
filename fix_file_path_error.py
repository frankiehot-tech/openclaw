#!/usr/bin/env python3
"""修复文件路径错误脚本"""

import json
import os
import shutil


def fix_gene_management_instruction_path():
    """修复基因管理审计任务的instruction_path"""

    print("🔍 修复文件路径错误...")

    # 源文件路径（实际存在）
    source_file = "/Volumes/1TB-M2/openclaw/completed/OpenHuman-Athena-OpenHuman基因管理Agent工程实施方案-VSCode执行指令.md"
    # 目标文件路径（队列中引用的路径）
    target_file = "/Volumes/1TB-M2/openclaw/OpenHuman-Athena-OpenHuman基因管理Agent工程实施方案-VSCode执行指令.md"

    # 检查源文件是否存在
    if not os.path.exists(source_file):
        print(f"❌ 源文件不存在: {source_file}")
        return False

    # 检查目标文件是否已存在
    if os.path.exists(target_file):
        print(f"ℹ️ 目标文件已存在: {target_file}")
        print(f"  文件大小: {os.path.getsize(target_file)} 字节")
        print(f"  修改时间: {os.path.getmtime(target_file)}")
        return True

    # 复制文件
    try:
        shutil.copy2(source_file, target_file)
        print(f"✅ 已复制文件: {source_file} → {target_file}")
        print(f"  文件大小: {os.path.getsize(target_file)} 字节")
        return True
    except Exception as e:
        print(f"❌ 复制文件失败: {e}")
        return False


def update_queue_file():
    """更新队列文件中的instruction_path"""

    print("\n🔍 更新队列文件...")

    queue_file = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_gene_management_20260405.json"

    if not os.path.exists(queue_file):
        print(f"❌ 队列文件不存在: {queue_file}")
        return False

    try:
        with open(queue_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 更新gene_mgmt_audit任务的instruction_path
        if "gene_mgmt_audit" in data.get("items", {}):
            # 更新为正确的路径（使用completed目录中的文件）
            correct_path = "/Volumes/1TB-M2/openclaw/completed/OpenHuman-Athena-OpenHuman基因管理Agent工程实施方案-VSCode执行指令.md"
            data["items"]["gene_mgmt_audit"]["instruction_path"] = correct_path

            # 清除错误信息
            data["items"]["gene_mgmt_audit"]["error"] = ""
            data["items"]["gene_mgmt_audit"]["summary"] = "文件路径已修复，等待重新执行"

            # 更新状态为pending以便重新执行
            data["items"]["gene_mgmt_audit"]["status"] = "pending"
            data["items"]["gene_mgmt_audit"]["progress_percent"] = 0
            data["items"]["gene_mgmt_audit"]["finished_at"] = ""

            # 保存更新后的队列文件
            with open(queue_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"✅ 已更新队列文件: {queue_file}")
            print(f"  更新instruction_path为: {correct_path}")
            print(f"  清除错误信息，状态重置为pending")
            return True
        else:
            print(f"❌ 未找到gene_mgmt_audit任务")
            return False

    except Exception as e:
        print(f"❌ 更新队列文件失败: {e}")
        return False


def verify_fix():
    """验证修复结果"""

    print("\n🔍 验证修复结果...")

    # 检查文件是否存在
    target_file = "/Volumes/1TB-M2/openclaw/OpenHuman-Athena-OpenHuman基因管理Agent工程实施方案-VSCode执行指令.md"
    if os.path.exists(target_file):
        print(f"✅ 文件已存在: {target_file}")
        print(f"  文件大小: {os.path.getsize(target_file)} 字节")
    else:
        print(f"❌ 文件不存在: {target_file}")

    # 检查队列文件
    queue_file = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/openhuman_aiplan_gene_management_20260405.json"
    if os.path.exists(queue_file):
        try:
            with open(queue_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if "gene_mgmt_audit" in data.get("items", {}):
                task = data["items"]["gene_mgmt_audit"]
                print(f"✅ 队列任务状态:")
                print(f"  instruction_path: {task.get('instruction_path', 'N/A')}")
                print(f"  status: {task.get('status', 'N/A')}")
                print(f"  error: {task.get('error', 'N/A')}")

                # 检查路径是否正确
                correct_path = "/Volumes/1TB-M2/openclaw/completed/OpenHuman-Athena-OpenHuman基因管理Agent工程实施方案-VSCode执行指令.md"
                if task.get("instruction_path") == correct_path:
                    print(f"  ✅ instruction_path正确")
                else:
                    print(f"  ❌ instruction_path不正确")
            else:
                print(f"❌ 未找到gene_mgmt_audit任务")

        except Exception as e:
            print(f"❌ 读取队列文件失败: {e}")
    else:
        print(f"❌ 队列文件不存在: {queue_file}")


def main():
    """主函数"""

    print("=" * 60)
    print("文件路径错误修复工具")
    print("=" * 60)

    # 修复文件路径
    if fix_gene_management_instruction_path():
        print("\n✅ 文件路径修复成功")
    else:
        print("\n❌ 文件路径修复失败")

    # 更新队列文件
    if update_queue_file():
        print("\n✅ 队列文件更新成功")
    else:
        print("\n❌ 队列文件更新失败")

    # 验证修复结果
    verify_fix()

    print("\n" + "=" * 60)
    print("修复完成！")
    print("=" * 60)

    print("\n🎉 文件路径错误已修复")
    print("\n下一步建议:")
    print("1. 重新执行审计任务: gene_mgmt_audit")
    print("2. 监控任务执行状态")
    print("3. 验证错误是否已消除")


if __name__ == "__main__":
    main()
