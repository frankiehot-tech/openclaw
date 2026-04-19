#!/usr/bin/env python3
"""
生产部署验证测试
验证生产环境部署脚本和配置是否正常工作
"""

import os
import subprocess
import sys
import time
from pathlib import Path


def test_config_loading():
    """测试配置文件加载"""
    print("=== 测试配置文件加载 ===")

    config_path = Path(__file__).parent / "config" / "production_config.py"
    if not config_path.exists():
        print("❌ 配置文件不存在")
        return False

    # 尝试导入配置
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        # 动态导入配置
        import importlib.util

        spec = importlib.util.spec_from_file_location("production_config", str(config_path))
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)

        # 检查关键配置
        required_configs = [
            "DATABASE_CONFIG",
            "MEMORY_MANAGER_CONFIG",
            "MONITOR_CONFIG",
            "ALERT_CONFIG",
            "AGENT_CONFIG",
            "PERFORMANCE_THRESHOLDS",
        ]

        missing_configs = []
        for config_name in required_configs:
            if hasattr(config_module, config_name):
                config_value = getattr(config_module, config_name)
                print(f"✅ {config_name}: 已定义 ({type(config_value).__name__})")
            else:
                print(f"❌ {config_name}: 未定义")
                missing_configs.append(config_name)

        if missing_configs:
            print(f"❌ 缺失配置项: {missing_configs}")
            return False

        print("✅ 所有配置项检查通过")
        return True

    except Exception as e:
        print(f"❌ 配置文件加载失败: {e}")
        return False


def test_start_script():
    """测试启动脚本语法"""
    print("\n=== 测试启动脚本语法 ===")

    start_script = Path(__file__).parent / "start_maref_production.sh"
    if not start_script.exists():
        print("❌ 启动脚本不存在")
        return False

    # 检查脚本语法
    try:
        result = subprocess.run(["bash", "-n", str(start_script)], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ 启动脚本语法正确")
            return True
        else:
            print(f"❌ 启动脚本语法错误: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 启动脚本测试失败: {e}")
        return False


def test_stop_script():
    """测试停止脚本语法"""
    print("\n=== 测试停止脚本语法 ===")

    stop_script = Path(__file__).parent / "stop_maref_production.sh"
    if not stop_script.exists():
        print("❌ 停止脚本不存在")
        return False

    # 检查脚本语法
    try:
        result = subprocess.run(["bash", "-n", str(stop_script)], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ 停止脚本语法正确")
            return True
        else:
            print(f"❌ 停止脚本语法错误: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 停止脚本测试失败: {e}")
        return False


def test_environment_check():
    """测试环境检查脚本"""
    print("\n=== 测试环境检查脚本 ===")

    check_script = Path(__file__).parent / "check_production_environment.py"
    if not check_script.exists():
        print("❌ 环境检查脚本不存在")
        return False

    # 运行检查脚本
    try:
        result = subprocess.run([sys.executable, str(check_script)], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ 环境检查脚本通过")
            return True
        else:
            print(f"❌ 环境检查脚本失败 (退出码: {result.returncode})")
            print(f"   输出: {result.stdout[-500:]}")  # 最后500字符
            return False
    except Exception as e:
        print(f"❌ 环境检查脚本执行失败: {e}")
        return False


def test_directory_permissions():
    """测试目录权限"""
    print("\n=== 测试目录权限 ===")

    directories = [
        ("/Volumes/1TB-M2/openclaw/scripts/clawra", "主程序目录"),
        ("/Volumes/1TB-M2/openclaw/scripts/clawra/logs", "日志目录"),
        ("/Volumes/1TB-M2/openclaw/scripts/clawra/config", "配置目录"),
        ("/Volumes/1TB-M2/openclaw/memory/maref", "数据库目录"),
    ]

    all_ok = True
    for path_str, description in directories:
        path = Path(path_str)
        if path.exists():
            # 检查可读权限
            if os.access(path, os.R_OK):
                print(f"✅ {description}: 可读")
            else:
                print(f"❌ {description}: 不可读")
                all_ok = False

            # 检查可写权限
            if os.access(path, os.W_OK):
                print(f"✅ {description}: 可写")
            else:
                print(f"❌ {description}: 不可写")
                all_ok = False
        else:
            print(f"❌ {description}: 不存在")
            all_ok = False

    return all_ok


def test_backup_directory():
    """测试备份目录（如果存在）"""
    print("\n=== 测试备份目录 ===")

    backup_dir = Path("/backup/maref")
    if backup_dir.exists():
        # 检查可写权限
        if os.access(backup_dir, os.W_OK):
            print("✅ 备份目录可写")
            return True
        else:
            print("❌ 备份目录不可写")
            return False
    else:
        print("⚠️  备份目录不存在（将在首次备份时创建）")
        return True  # 这不是致命错误


def main():
    """主测试函数"""
    print("=== MAREF生产部署验证测试 ===\n")

    tests = [
        ("配置文件加载", test_config_loading),
        ("启动脚本语法", test_start_script),
        ("停止脚本语法", test_stop_script),
        ("环境检查脚本", test_environment_check),
        ("目录权限", test_directory_permissions),
        ("备份目录", test_backup_directory),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            print(f"\n--- {test_name} ---")
            result = test_func()
            results.append((test_name, result))
            print(f"结果: {'✅ 通过' if result else '❌ 失败'}")
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            results.append((test_name, False))

    print("\n=== 测试总结 ===")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"通过: {passed}/{total}")

    if passed == total:
        print("✅ 所有生产部署验证测试通过")
        return 0
    else:
        print("❌ 部分验证测试未通过，请修复后重试")
        for test_name, result in results:
            if not result:
                print(f"  - {test_name}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
