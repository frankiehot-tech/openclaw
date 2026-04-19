#!/usr/bin/env python3
"""
MAREF生产系统健康检查脚本
用于定期检查生产系统的健康状态
"""

import os
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

import psutil

sys.path.insert(0, str(Path(__file__).parent))


def check_system_processes():
    """检查系统进程"""
    print("=== 系统进程检查 ===")

    # 查找MAREF相关进程
    maref_processes = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = " ".join(proc.info["cmdline"] or [])
            if "run_maref_daily" in cmdline or "maref_monitor" in cmdline:
                maref_processes.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if maref_processes:
        print(f"✅ 找到 {len(maref_processes)} 个MAREF进程:")
        for proc in maref_processes:
            print(
                f"  PID: {proc['pid']}, 命令: {proc['cmdline'][0] if proc['cmdline'] else '未知'}"
            )
        return True
    else:
        print("❌ 未找到运行中的MAREF进程")
        return False


def check_database_health():
    """检查数据库健康状态"""
    print("\n=== 数据库健康检查 ===")

    db_path = "/Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db"

    if not os.path.exists(db_path):
        print("❌ 数据库文件不存在")
        return False

    print(f"✅ 数据库文件存在: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 检查表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"表数量: {len(tables)}")

        # 检查memory_entries表
        cursor.execute("SELECT COUNT(*) FROM memory_entries;")
        total_entries = cursor.fetchone()[0]
        print(f"memory_entries记录数: {total_entries}")

        # 检查最近24小时的数据
        cutoff_time = (datetime.now() - timedelta(hours=24)).isoformat()
        cursor.execute("SELECT COUNT(*) FROM memory_entries WHERE timestamp >= ?;", (cutoff_time,))
        recent_entries = cursor.fetchone()[0]
        print(f"最近24小时记录: {recent_entries}")

        # 检查数据库完整性
        cursor.execute("PRAGMA integrity_check;")
        integrity_result = cursor.fetchone()[0]
        if integrity_result == "ok":
            print("✅ 数据库完整性检查: 通过")
        else:
            print(f"❌ 数据库完整性检查失败: {integrity_result}")
            return False

        conn.close()
        return True

    except Exception as e:
        print(f"❌ 数据库检查失败: {e}")
        return False


def check_log_files():
    """检查日志文件"""
    print("\n=== 日志文件检查 ===")

    log_dir = Path("/Volumes/1TB-M2/openclaw/scripts/clawra/logs")

    if not log_dir.exists():
        print("❌ 日志目录不存在")
        return False

    print(f"✅ 日志目录存在: {log_dir}")

    # 检查主要日志文件
    log_files = {
        "生产日志": "maref_production.log",
        "日报日志": "maref_daily_report.log",
        "监控日志": "monitor_*.log",
    }

    all_ok = True
    for log_type, pattern in log_files.items():
        if "*" in pattern:
            matches = list(log_dir.glob(pattern))
            if matches:
                latest = max(matches, key=lambda f: f.stat().st_mtime)
                print(
                    f"✅ {log_type}: {latest.name} (最近修改: {datetime.fromtimestamp(latest.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')})"
                )
            else:
                print(f"⚠️  {log_type}: 未找到匹配文件")
                all_ok = False
        else:
            log_file = log_dir / pattern
            if log_file.exists():
                size_mb = log_file.stat().st_size / (1024 * 1024)
                print(f"✅ {log_type}: {pattern} ({size_mb:.2f} MB)")
            else:
                print(f"⚠️  {log_type}: {pattern} 不存在")
                all_ok = False

    return all_ok


def check_configuration():
    """检查配置文件"""
    print("\n=== 配置文件检查 ===")

    config_dir = Path("/Volumes/1TB-M2/openclaw/scripts/clawra/config")
    required_configs = ["production_config.py", "performance_baseline.py"]

    all_ok = True
    for config_file in required_configs:
        config_path = config_dir / config_file
        if config_path.exists():
            print(f"✅ {config_file} 存在")
        else:
            print(f"❌ {config_file} 不存在")
            all_ok = False

    return all_ok


def check_maref_integration():
    """检查MAREF集成状态"""
    print("\n=== MAREF集成状态检查 ===")

    try:
        from run_maref_daily_report import create_integration_environment

        print("创建集成环境...")
        # create_integration_environment() 返回 (state_manager, agents) 元组
        result = create_integration_environment()

        if isinstance(result, tuple) and len(result) >= 2:
            state_manager, agents_dict = result[0], result[1]

            print(f"✅ MAREF集成正常")
            print(
                f"  当前卦象: {state_manager.current_state} ({state_manager.get_hexagram_name()})"
            )

            # 检查智能体
            expected_agents = ["guardian", "communicator", "learner", "explorer"]
            all_present = True

            for agent_name in expected_agents:
                if agent_name in agents_dict:
                    agent = agents_dict[agent_name]
                    print(f"  ✅ {agent_name}智能体就绪: {type(agent).__name__}")
                else:
                    print(f"  ❌ {agent_name}智能体缺失")
                    all_present = False

            if all_present:
                return True
            else:
                return False
        else:
            print("❌ 集成环境返回格式不正确")
            return False

    except Exception as e:
        print(f"❌ MAREF集成检查失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("=== MAREF生产系统健康检查 ===")
    print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    checks = [
        ("系统进程", check_system_processes),
        ("数据库健康", check_database_health),
        ("日志文件", check_log_files),
        ("配置文件", check_configuration),
        ("MAREF集成", check_maref_integration),
    ]

    results = []
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
            print(f"结果: {'✅ 通过' if result else '❌ 失败'}\n")
        except Exception as e:
            print(f"❌ {check_name}检查异常: {e}")
            results.append((check_name, False))
            print()

    print("=== 健康检查总结 ===")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"通过: {passed}/{total}")

    if passed == total:
        print("✅ 所有健康检查通过，系统状态正常")
        return 0
    else:
        print("⚠️  部分健康检查未通过")
        for check_name, result in results:
            if not result:
                print(f"  - {check_name}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
