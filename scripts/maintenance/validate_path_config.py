#!/usr/bin/env python3
"""
路径配置验证脚本
验证所有Python脚本中的路径配置一致性
检查硬编码路径问题，确保路径配置模块正常工作
"""

import os
import subprocess
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config.paths import OPENCLAW_DIR, PLAN_QUEUE_DIR, ROOT_DIR, SCRIPTS_DIR

    PATHS_MODULE_AVAILABLE = True
except ImportError as e:
    print(f"❌ 无法导入config.paths模块: {e}")
    PATHS_MODULE_AVAILABLE = False
    # 使用回退路径
    ROOT_DIR = Path("/Volumes/1TB-M2/openclaw")
    PLAN_QUEUE_DIR = ROOT_DIR / ".openclaw" / "plan_queue"
    SCRIPTS_DIR = ROOT_DIR / "scripts"
    OPENCLAW_DIR = ROOT_DIR / ".openclaw"


def check_paths_module():
    """检查config.paths模块功能"""
    print("🔍 检查config.paths模块...")

    if not PATHS_MODULE_AVAILABLE:
        print("❌ config.paths模块不可用")
        return False

    # 验证路径存在性
    paths_to_check = [
        ("ROOT_DIR", ROOT_DIR),
        ("PLAN_QUEUE_DIR", PLAN_QUEUE_DIR),
        ("SCRIPTS_DIR", SCRIPTS_DIR),
        ("OPENCLAW_DIR", OPENCLAW_DIR),
    ]

    all_exist = True
    for name, path in paths_to_check:
        if path.exists():
            print(f"✅ {name}: {path} (存在)")
        else:
            print(f"❌ {name}: {path} (不存在)")
            all_exist = False

    # 测试get_queue_file函数
    try:
        from config.paths import get_queue_file

        # 测试存在的队列
        test_queue_id = "gene_management"
        queue_file = get_queue_file(test_queue_id)
        if queue_file and queue_file.exists():
            print(f"✅ get_queue_file函数可用，返回路径: {queue_file}")
        else:
            print(f"✅ get_queue_file函数可用，但队列 '{test_queue_id}' 不存在: {queue_file}")

        # 测试不存在的队列
        non_existent = "non_existent_queue_123"
        non_existent_file = get_queue_file(non_existent)
        if non_existent_file is None:
            print("✅ get_queue_file正确处理不存在的队列: 返回None")
        else:
            print(f"✅ get_queue_file返回路径但可能不存在: {non_existent_file}")

    except Exception as e:
        print(f"❌ get_queue_file函数测试失败: {e}")
        all_exist = False

    return all_exist


def check_hardcoded_paths():
    """检查项目中的硬编码路径"""
    print("\n🔍 检查硬编码路径...")

    # 搜索硬编码路径模式
    patterns = ["/Volumes/1TB-M2/openclaw", "openclaw/.openclaw/plan_queue", "openclaw/scripts"]

    results = {}
    for pattern in patterns:
        try:
            cmd = f"grep -r '{pattern}' . --include='*.py' --include='*.sh' 2>/dev/null | head -20"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                count = len(result.stdout.strip().split("\n"))
                results[pattern] = count
                print(f"  发现 {count} 个文件包含模式: {pattern}")
            else:
                results[pattern] = 0
        except Exception as e:
            print(f"   搜索模式 {pattern} 失败: {e}")

    return results


def check_scripts_openclaw_roots():
    """检查scripts目录的openclaw_roots模块"""
    print("\n🔍 检查scripts/openclaw_roots.py模块...")

    roots_path = ROOT_DIR / "scripts" / "openclaw_roots.py"
    if not roots_path.exists():
        print("❌ scripts/openclaw_roots.py文件不存在")
        return False

    try:
        # 尝试导入模块
        scripts_dir = str(ROOT_DIR / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)

        import openclaw_roots

        print("✅ 成功导入openclaw_roots模块")

        # 检查关键变量
        for attr in ["RUNTIME_ROOT", "QUEUE_STATE_DIR", "TASKS_DIR"]:
            if hasattr(openclaw_roots, attr):
                value = getattr(openclaw_roots, attr)
                print(f"  ✅ {attr}: {value}")
                if hasattr(value, "exists") and value.exists():
                    print("    路径存在")
                else:
                    print("    路径不存在或无法验证")
            else:
                print(f"  ❌ {attr}未定义")

        return True
    except Exception as e:
        print(f"❌ 检查openclaw_roots模块失败: {e}")
        return False


def check_environment_variables():
    """检查环境变量配置"""
    print("\n🔍 检查环境变量...")

    env_vars = [
        ("OPENCLAW_ROOT", "项目根目录环境变量"),
        ("ATHENA_RUNTIME_ROOT", "Athena运行时根目录"),
        ("DASHSCOPE_API_KEY", "DashScope API密钥"),
    ]

    found_vars = []
    for var, description in env_vars:
        value = os.environ.get(var)
        if value:
            print(f"✅ {var}: 已设置 ({description})")
            # 不打印敏感值，只显示长度
            if "KEY" in var or "TOKEN" in var or "SECRET" in var:
                print(f"   值长度: {len(value)} 字符")
            found_vars.append(var)
        else:
            print(f"⚠️  {var}: 未设置 ({description})")

    return found_vars


def check_migrated_scripts():
    """检查已迁移的脚本"""
    print("\n🔍 检查已迁移路径配置的脚本...")

    # 已迁移的脚本列表（从之前的编辑中获取）
    migrated_scripts = [
        "remove_stale_task.py",
        "final_comprehensive_queue_fix.py",
        "fix_queue_stage_sync.py",
        "protect_all_queues.py",
        "verify_process_consistency.py",
        "detect_and_stop_queue_reset.py",
        "cleanup_backups_aggressive.py",
        "cleanup_queue_backups.py",
        "scan_approval_folder.py",
        "analyze_pending_tasks.py",
        "fix_all_zombie_running.py",
    ]

    status = {}
    for script_name in migrated_scripts:
        script_path = ROOT_DIR / script_name
        if not script_path.exists():
            status[script_name] = "文件不存在"
            print(f"❌ {script_name}: 文件不存在")
            continue

        try:
            with open(script_path, encoding="utf-8") as f:
                content = f.read()

            # 检查是否包含导入语句
            has_import = "from config.paths import" in content or "import config.paths" in content
            has_hardcoded = "/Volumes/1TB-M2/openclaw" in content
            has_fallback = "使用回退的硬编码路径" in content or "使用回退路径" in content

            # 已迁移脚本的预期状态：有导入语句，可能有硬编码路径作为回退，并有回退消息
            if has_import:
                if has_fallback:
                    # 这是预期的设计：有导入语句，有回退逻辑
                    status[script_name] = "已迁移（带回退）"
                    print(f"✅ {script_name}: 已迁移到config.paths（包含回退逻辑）")
                elif not has_hardcoded:
                    status[script_name] = "完全迁移"
                    print(f"✅ {script_name}: 完全迁移到config.paths")
                else:
                    status[script_name] = "部分迁移"
                    print(f"⚠️  {script_name}: 部分迁移（仍有硬编码路径但无回退消息）")
            else:
                status[script_name] = "未迁移"
                print(f"❌ {script_name}: 未迁移到config.paths")

        except Exception as e:
            status[script_name] = f"检查失败: {e}"
            print(f"❌ {script_name}: 检查失败 - {e}")

    return status


def generate_report():
    """生成验证报告"""
    print("\n" + "=" * 80)
    print("📋 路径配置验证报告")
    print("=" * 80)

    # 收集所有检查结果
    results = {}

    print("\n1. config.paths模块检查:")
    results["paths_module"] = check_paths_module()

    print("\n2. 硬编码路径检查:")
    results["hardcoded_paths"] = check_hardcoded_paths()

    print("\n3. scripts/openclaw_roots检查:")
    results["openclaw_roots"] = check_scripts_openclaw_roots()

    print("\n4. 环境变量检查:")
    results["env_vars"] = check_environment_variables()

    print("\n5. 已迁移脚本检查:")
    results["migrated_scripts"] = check_migrated_scripts()

    # 总结
    print("\n" + "=" * 80)
    print("🎯 总结与建议")
    print("=" * 80)

    # 分析硬编码路径情况
    hardcoded_counts = results.get("hardcoded_paths", {})
    total_hardcoded = sum(hardcoded_counts.values())

    if total_hardcoded > 0:
        print(f"⚠️  发现 {total_hardcoded} 个硬编码路径实例")
        print("   建议继续迁移重要脚本到config.paths模块")
    else:
        print("✅ 未发现硬编码路径")

    # 检查已迁移脚本状态
    migrated_status = results.get("migrated_scripts", {})
    # 计算迁移状态：已迁移（带回退）和完全迁移都算作已迁移
    migrated_count = sum(1 for s in migrated_status.values() if "已迁移" in s or "完全迁移" in s)
    total_checked = len(migrated_status)

    if total_checked > 0:
        print(f"📊 已迁移脚本: {migrated_count}/{total_checked}")
        # 显示详细状态
        print("   详细状态:")
        for script, status in migrated_status.items():
            print(f"     • {script}: {status}")

    # 环境变量建议
    env_vars = results.get("env_vars", [])
    if "OPENCLAW_ROOT" not in env_vars:
        print("💡 建议设置OPENCLAW_ROOT环境变量支持灵活部署")

    if "ATHENA_RUNTIME_ROOT" not in env_vars:
        print("💡 建议设置ATHENA_RUNTIME_ROOT环境变量支持scripts目录配置")

    # 自动化检查建议
    print("\n🔧 自动化检查建议:")
    print("1. 将此验证脚本添加到持续集成流程")
    print("2. 设置预提交钩子检查新硬编码路径")
    print("3. 定期运行验证确保路径配置一致性")

    return results


def main():
    print("🚀 开始路径配置验证")
    print(f"项目根目录: {ROOT_DIR}")
    print(f"时间: {subprocess.run(['date'], capture_output=True, text=True).stdout.strip()}")

    results = generate_report()

    # 返回退出码
    hardcoded_counts = results.get("hardcoded_paths", {})
    total_hardcoded = sum(hardcoded_counts.values())

    if total_hardcoded > 100:
        print("\n❌ 验证失败: 发现大量硬编码路径")
        return 2
    elif total_hardcoded > 20:
        print("\n⚠️  验证警告: 发现较多硬编码路径")
        return 1
    else:
        print("\n✅ 验证通过: 路径配置基本正常")
        return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏹️ 用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 验证脚本异常: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(3)
