#!/usr/bin/env python3
"""
阶段0：数据备份与快照脚本
基于部署计划阶段0要求，备份队列文件、Manifest文件、配置快照
"""

import hashlib
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path


def create_backup_destination(base_dir):
    """创建带时间戳的备份目录"""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = Path(base_dir) / f"deployment_backup_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def backup_queue_files(backup_dir):
    """备份队列文件"""
    queue_source = Path("/Volumes/1TB-M2/openclaw/.openclaw/plan_queue")
    backup_queue_dir = backup_dir / "plan_queue"

    if not queue_source.exists():
        print(f"❌ 队列目录不存在: {queue_source}")
        return False

    try:
        # 复制整个目录
        shutil.copytree(queue_source, backup_queue_dir)
        print(f"✅ 队列文件备份完成: {backup_queue_dir}")
        return True
    except Exception as e:
        print(f"❌ 队列文件备份失败: {e}")
        return False


def backup_manifest_files(backup_dir):
    """备份Manifest文件"""
    # 查找Manifest文件
    manifests = []

    # 常见Manifest文件位置
    potential_locations = [
        "/Volumes/1TB-M2/openclaw/.openclaw/gene_management_queue_manifest.json",
        "/Volumes/1TB-M2/openclaw/.openclaw/*_manifest.json",
        "/Volumes/1TB-M2/openclaw/.openclaw/*/manifest.json",
    ]

    import glob

    for pattern in potential_locations:
        for filepath in glob.glob(pattern):
            manifests.append(filepath)

    backup_manifest_dir = backup_dir / "manifests"
    backup_manifest_dir.mkdir(parents=True, exist_ok=True)

    success = True
    for manifest in manifests:
        try:
            shutil.copy2(manifest, backup_manifest_dir / Path(manifest).name)
            print(f"  ✅ 备份Manifest: {Path(manifest).name}")
        except Exception as e:
            print(f"  ❌ 备份Manifest失败 {manifest}: {e}")
            success = False

    return success


def backup_config_files(backup_dir):
    """备份配置文件"""
    config_files = []

    # 查找配置文件
    potential_configs = [
        "/Volumes/1TB-M2/openclaw/.openclaw/*.json",
        "/Volumes/1TB-M2/openclaw/*.yaml",
        "/Volumes/1TB-M2/openclaw/*.yml",
        "/Volumes/1TB-M2/openclaw/.env*",
        "/Volumes/1TB-M2/openclaw/config/*",
        "/Volumes/1TB-M2/openclaw/queue_monitor_config_*.yaml",
    ]

    import glob

    backup_config_dir = backup_dir / "configs"
    backup_config_dir.mkdir(parents=True, exist_ok=True)

    success = True
    for pattern in potential_configs:
        for filepath in glob.glob(pattern):
            # 跳过备份目录中的文件
            if "deployment_backup_" in filepath:
                continue
            try:
                dest_path = backup_config_dir / Path(filepath).name
                # 如果文件名冲突，添加路径信息
                if dest_path.exists():
                    # 使用相对路径创建子目录结构
                    rel_path = Path(filepath).relative_to("/Volumes/1TB-M2/openclaw")
                    dest_path = backup_config_dir / rel_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)

                shutil.copy2(filepath, dest_path)
                print(f"  ✅ 备份配置: {Path(filepath).name}")
            except Exception as e:
                print(f"  ❌ 备份配置失败 {filepath}: {e}")
                success = False

    return success


def create_snapshot_report(backup_dir):
    """创建快照报告"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "backup_location": str(backup_dir),
        "components": {
            "queues": {
                "source": "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue",
                "backup": str(backup_dir / "plan_queue"),
                "file_count": 0,
                "total_size": 0,
            },
            "manifests": {"backup": str(backup_dir / "manifests"), "files": []},
            "configs": {"backup": str(backup_dir / "configs"), "files": []},
        },
        "checksums": {},
    }

    # 计算文件统计
    for component in ["plan_queue", "manifests", "configs"]:
        comp_dir = backup_dir / component
        if comp_dir.exists():
            file_count = 0
            total_size = 0

            for root, dirs, files in os.walk(comp_dir):
                file_count += len(files)
                for file in files:
                    file_path = Path(root) / file
                    total_size += file_path.stat().st_size

            if component == "plan_queue":
                report["components"]["queues"]["file_count"] = file_count
                report["components"]["queues"]["total_size"] = total_size
            elif component == "manifests":
                report["components"]["manifests"]["file_count"] = file_count
                report["components"]["manifests"]["total_size"] = total_size
            elif component == "configs":
                report["components"]["configs"]["file_count"] = file_count
                report["components"]["configs"]["total_size"] = total_size

    # 计算校验和
    for root, dirs, files in os.walk(backup_dir):
        for file in files:
            if file.endswith(".json") or file.endswith(".yaml") or file.endswith(".yml"):
                file_path = Path(root) / file
                try:
                    with open(file_path, "rb") as f:
                        file_hash = hashlib.md5(f.read()).hexdigest()
                        rel_path = file_path.relative_to(backup_dir)
                        report["checksums"][str(rel_path)] = file_hash
                except:
                    pass

    # 写入报告
    report_path = backup_dir / "backup_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"📊 备份报告已生成: {report_path}")
    return report_path


def verify_backup_integrity(backup_dir):
    """验证备份完整性"""
    report_path = backup_dir / "backup_report.json"
    if not report_path.exists():
        print(f"❌ 备份报告不存在: {report_path}")
        return False

    try:
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)

        print("🔍 验证备份完整性:")
        print(f"   备份时间: {report['timestamp']}")
        print(f"   备份位置: {report['backup_location']}")

        all_good = True

        # 检查关键组件
        for comp_name, comp_info in report["components"].items():
            if comp_name == "queues":
                if comp_info["file_count"] == 0:
                    print(f"   ⚠️  {comp_name}: 文件数为0")
                    all_good = False
                else:
                    size_mb = comp_info["total_size"] / 1024 / 1024
                    print(f"   ✅ {comp_name}: {comp_info['file_count']}个文件, {size_mb:.2f} MB")

        # 检查校验和
        checksum_count = len(report.get("checksums", {}))
        print(f"   ✅ 校验和数量: {checksum_count}")

        if all_good:
            print("🎉 备份完整性验证通过")
        else:
            print("⚠️  备份完整性验证警告")

        return all_good

    except Exception as e:
        print(f"❌ 备份验证失败: {e}")
        return False


def main():
    """主函数"""
    print("💾 阶段0：数据备份与快照")
    print("=" * 60)

    # 创建备份目录
    base_backup_dir = "/Volumes/1TB-M2/openclaw/deployment_backups"
    backup_dir = create_backup_destination(base_backup_dir)
    print(f"📁 备份目录: {backup_dir}")

    # 备份队列文件
    print("\n📊 备份队列文件...")
    queue_success = backup_queue_files(backup_dir)

    # 备份Manifest文件
    print("\n📋 备份Manifest文件...")
    manifest_success = backup_manifest_files(backup_dir)

    # 备份配置文件
    print("\n⚙️  备份配置文件...")
    config_success = backup_config_files(backup_dir)

    # 生成快照报告
    print("\n📈 生成快照报告...")
    report_path = create_snapshot_report(backup_dir)

    # 验证备份完整性
    print("\n🔍 验证备份完整性...")
    verification_success = verify_backup_integrity(backup_dir)

    # 总结
    print("\n" + "=" * 60)
    print("📋 数据备份总结")
    print("=" * 60)

    success = queue_success and manifest_success and config_success and verification_success

    print(f"   队列文件备份: {'✅ 成功' if queue_success else '❌ 失败'}")
    print(f"   Manifest备份: {'✅ 成功' if manifest_success else '❌ 失败'}")
    print(f"   配置文件备份: {'✅ 成功' if config_success else '❌ 失败'}")
    print(f"   完整性验证: {'✅ 通过' if verification_success else '❌ 失败'}")
    print(f"\n   备份位置: {backup_dir}")
    print(f"   报告文件: {report_path}")

    if success:
        print("\n🎉 阶段0数据备份完成，可继续部署")
    else:
        print("\n⚠️  数据备份存在问题，请检查后继续")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
