#!/usr/bin/env python3
"""
生产环境验收测试
验证MAREF生产环境部署是否成功
"""

import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path


def test_environment():
    """测试基础环境"""
    print("=== 基础环境测试 ===")

    # 运行环境检查脚本
    check_script = Path(__file__).parent / "check_production_environment.py"
    if not check_script.exists():
        print("❌ 环境检查脚本不存在")
        return False

    result = subprocess.run([sys.executable, str(check_script)], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ 基础环境检查通过")
        return True
    else:
        print("❌ 基础环境检查失败")
        print(f"输出:\n{result.stdout[-500:]}")
        return False


def test_database():
    """测试数据库连接和结构"""
    print("\n=== 数据库测试 ===")

    db_path = "/Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db"
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return False

    print(f"✅ 数据库文件存在: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 检查表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"✅ 数据库表: {len(tables)} 个")

        # 检查memory_entries表数据
        cursor.execute("SELECT COUNT(*) FROM memory_entries")
        entry_count = cursor.fetchone()[0]
        print(f"✅ 内存条目数: {entry_count}")

        # 检查状态转换记录
        cursor.execute("""
            SELECT COUNT(*) FROM memory_entries
            WHERE entry_type = 'state_transition'
        """)
        transition_count = cursor.fetchone()[0]
        print(f"✅ 状态转换记录数: {transition_count}")

        # 检查最新条目时间
        cursor.execute("""
            SELECT MAX(timestamp) FROM memory_entries
        """)
        latest_timestamp = cursor.fetchone()[0]
        if latest_timestamp:
            print(f"✅ 最新记录时间: {latest_timestamp}")
        else:
            print("⚠️  无记录时间戳")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ 数据库测试失败: {e}")
        return False


def test_configuration():
    """测试配置文件"""
    print("\n=== 配置文件测试 ===")

    config_path = Path(__file__).parent / "config" / "production_config.py"
    if not config_path.exists():
        print("❌ 配置文件不存在")
        return False

    print(f"✅ 配置文件存在: {config_path}")

    # 尝试导入配置
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("production_config", str(config_path))
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)

        required_configs = [
            "DATABASE_CONFIG",
            "MEMORY_MANAGER_CONFIG",
            "MONITOR_CONFIG",
            "ALERT_CONFIG",
            "AGENT_CONFIG",
            "PERFORMANCE_THRESHOLDS",
        ]

        for config_name in required_configs:
            if hasattr(config_module, config_name):
                print(f"✅ {config_name}: 已定义")
            else:
                print(f"❌ {config_name}: 未定义")
                return False

        # 验证关键配置值
        db_path = config_module.DATABASE_CONFIG.get("path")
        if db_path and os.path.exists(db_path):
            print(f"✅ 数据库路径有效: {db_path}")
        else:
            print(f"⚠️  数据库路径可能无效: {db_path}")

        return True

    except Exception as e:
        print(f"❌ 配置文件测试失败: {e}")
        return False


def test_start_stop_scripts():
    """测试启动/停止脚本"""
    print("\n=== 启动/停止脚本测试 ===")

    scripts = [
        ("启动脚本", "start_maref_production.sh"),
        ("停止脚本", "stop_maref_production.sh"),
        ("备份脚本", "backup_maref_production.sh"),
        ("日志管理脚本", "manage_maref_logs.sh"),
    ]

    all_ok = True
    for script_name, script_file in scripts:
        script_path = Path(__file__).parent / script_file
        if script_path.exists():
            # 检查执行权限
            if os.access(script_path, os.X_OK):
                print(f"✅ {script_name}: 存在且可执行")
            else:
                print(f"⚠️  {script_name}: 存在但不可执行")
                all_ok = False

            # 检查语法
            result = subprocess.run(
                ["bash", "-n", str(script_path)], capture_output=True, text=True
            )
            if result.returncode == 0:
                print(f"  ✅ 语法正确")
            else:
                print(f"  ❌ 语法错误: {result.stderr[:100]}")
                all_ok = False
        else:
            print(f"❌ {script_name}: 不存在")
            all_ok = False

    return all_ok


def test_service_start_stop():
    """测试服务启动和停止（模拟）"""
    print("\n=== 服务启动/停止测试 ===")

    print("注意: 这是一个模拟测试，不会实际启动长期服务")

    # 检查当前是否有服务在运行
    result = subprocess.run(["ps", "aux"], capture_output=True, text=True)

    maref_processes = []
    for line in result.stdout.split("\n"):
        if "run_maref_daily" in line or "maref_monitor" in line:
            if "grep" not in line:
                maref_processes.append(line.strip())

    if maref_processes:
        print(f"⚠️  发现运行中的MAREF进程: {len(maref_processes)} 个")
        for proc in maref_processes[:3]:
            print(f"  {proc[:80]}...")
    else:
        print("✅ 无运行中的MAREF进程")

    # 测试停止脚本（应该无害）
    print("测试停止脚本（无进程时）...")
    stop_script = Path(__file__).parent / "stop_maref_production.sh"
    result = subprocess.run([str(stop_script)], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ 停止脚本执行成功（无进程时）")
    else:
        print(f"❌ 停止脚本执行失败: {result.stderr[:200]}")
        return False

    return True


def test_integration_environment():
    """测试集成环境创建"""
    print("\n=== 集成环境测试 ===")

    try:
        from run_maref_daily_report import create_integration_environment

        print("✅ create_integration_environment 导入成功")

        print("创建集成环境...")
        state_manager, agents = create_integration_environment()

        if state_manager and agents:
            print("✅ 集成环境创建成功")
            print(f"  当前状态: {state_manager.current_state}")
            print(f"  智能体数量: {len(agents)}")

            # 验证智能体
            required_agents = ["guardian", "communicator", "learner", "explorer"]
            for agent_name in required_agents:
                if agent_name in agents:
                    print(f"  ✅ {agent_name}: 存在")
                else:
                    print(f"  ❌ {agent_name}: 缺失")
                    return False

            return True
        else:
            print("❌ 集成环境创建失败")
            return False

    except Exception as e:
        print(f"❌ 集成环境测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_performance_metrics():
    """测试性能指标采集"""
    print("\n=== 性能指标测试 ===")

    try:
        from maref_monitor import MAREFMonitor

        # 创建模拟环境
        class MockStateManager:
            current_state = "000000"

            def get_hexagram_name(self):
                return "䷀乾为天"

        class MockAgent:
            agent_id = "test_agent"

        mock_agents = {
            "guardian": MockAgent(),
            "communicator": MockAgent(),
            "learner": MockAgent(),
            "explorer": MockAgent(),
        }

        monitor = MAREFMonitor(MockStateManager(), mock_agents)

        # 采集指标
        metrics = monitor.collect_all_metrics()

        if metrics:
            print("✅ 性能指标采集成功")
            print(f"  采集的指标数: {len(metrics)}")

            # 检查关键指标
            required_metrics = ["system_metrics", "maref_metrics", "timestamp"]
            for metric in required_metrics:
                if metric in metrics:
                    print(f"  ✅ {metric}: 存在")
                else:
                    print(f"  ⚠️  {metric}: 缺失")

            return True
        else:
            print("❌ 性能指标采集失败")
            return False

    except Exception as e:
        print(f"❌ 性能指标测试失败: {e}")
        return False


def main():
    """主验收测试"""
    print("=== MAREF生产环境验收测试 ===\n")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试环境: {sys.platform} Python {sys.version.split()[0]}\n")

    tests = [
        ("基础环境", test_environment),
        ("数据库", test_database),
        ("配置文件", test_configuration),
        ("启动/停止脚本", test_start_stop_scripts),
        ("服务启动/停止", test_service_start_stop),
        ("集成环境", test_integration_environment),
        ("性能指标", test_performance_metrics),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            print(f"\n--- {test_name}测试 ---")
            result = test_func()
            results.append((test_name, result))
            print(f"结果: {'✅ 通过' if result else '❌ 失败'}")
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            results.append((test_name, False))

    print("\n" + "=" * 60)
    print("=== 验收测试总结 ===")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"\n测试通过: {passed}/{total}")

    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name:20} {status}")

    print("\n" + "=" * 60)

    if passed == total:
        print("🎉 所有验收测试通过！MAREF生产环境部署成功。")
        print("\n下一步建议:")
        print("1. 执行首次备份: ./backup_maref_production.sh --mode daily")
        print("2. 启动生产服务: ./start_maref_production.sh")
        print("3. 监控日志: tail -f logs/maref_production.log")
        print("4. 验证日报生成: python3 run_maref_daily_report.py --mode production")
        return 0
    else:
        print("❌ 部分验收测试未通过，请修复问题后重试。")

        failed_tests = [name for name, result in results if not result]
        print(f"\n失败的测试: {', '.join(failed_tests)}")

        print("\n修复建议:")
        if "基础环境" in failed_tests:
            print("  - 运行 python3 check_production_environment.py 查看详细错误")
        if "数据库" in failed_tests:
            print("  - 检查数据库文件权限和路径")
        if "配置文件" in failed_tests:
            print("  - 验证 config/production_config.py 文件内容")
        if "启动/停止脚本" in failed_tests:
            print("  - 检查脚本权限: chmod +x *.sh")
        if "集成环境" in failed_tests:
            print("  - 检查MAREF组件导入路径")

        return 1


if __name__ == "__main__":
    sys.exit(main())
