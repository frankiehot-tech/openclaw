#!/usr/bin/env python3
"""
生产环境检查脚本
验证所有部署前提条件
"""

import importlib
import os
import sqlite3
import sys
from pathlib import Path


def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    print(f"Python版本: {version.major}.{version.minor}.{version.micro}")
    if version.major == 3 and version.minor >= 8:
        print("✅ Python版本满足要求 (>=3.8)")
        return True
    else:
        print("❌ Python版本不满足要求，需要3.8或更高")
        return False


def check_dependencies():
    """检查依赖包"""
    packages = [
        ("dspy", "roma_dspy"),
        ("yaml", "PyYAML"),
    ]

    all_ok = True
    for import_name, package_name in packages:
        try:
            importlib.import_module(import_name)
            print(f"✅ {package_name} 已安装")
        except ImportError as e:
            print(f"❌ {package_name} 未安装: {e}")
            all_ok = False

    # 内置包检查
    for package in ["sqlite3", "json", "logging", "threading"]:
        try:
            importlib.import_module(package)
            print(f"✅ {package} (内置) 可用")
        except:
            print(f"⚠️  {package} 异常")

    return all_ok


def check_directories():
    """检查目录结构和权限"""
    directories = [
        ("/Volumes/1TB-M2/openclaw/scripts/clawra", "主程序目录"),
        ("/Volumes/1TB-M2/openclaw/memory/maref", "内存数据库目录"),
        ("/Volumes/1TB-M2/openclaw/scripts/clawra/logs", "日志目录"),
        ("/Volumes/1TB-M2/openclaw/scripts/clawra/config", "配置目录"),
    ]

    all_ok = True
    for path, description in directories:
        path_obj = Path(path)
        if path_obj.exists():
            print(f"✅ {description}: {path}")
            # 检查读写权限
            if os.access(path, os.R_OK | os.W_OK):
                print(f"  权限: 可读写")
            else:
                print(f"  ⚠️  权限不足")
                all_ok = False
        else:
            print(f"❌ {description}不存在: {path}")
            all_ok = False

    return all_ok


def check_database():
    """检查数据库"""
    db_path = "/Volumes/1TB-M2/openclaw/memory/maref/maref_memory.db"

    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return False

    print(f"✅ 数据库文件存在: {db_path}")

    # 检查文件大小
    size_mb = os.path.getsize(db_path) / (1024 * 1024)
    print(f"  大小: {size_mb:.2f} MB")

    # 检查权限
    if os.access(db_path, os.R_OK | os.W_OK):
        print(f"  权限: 可读写")
    else:
        print(f"  ❌ 数据库文件权限不足")
        return False

    # 检查表结构
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        print(f"  表数量: {len(tables)}")

        # 检查关键表 - 只需要memory_entries表，其他数据通过entry_type字段区分
        required_tables = ["memory_entries"]
        missing_tables = []
        for table in required_tables:
            if table in tables:
                print(f"  ✅ 关键表存在: {table}")
            else:
                print(f"  ❌ 关键表缺失: {table}")
                missing_tables.append(table)

        if missing_tables:
            print(f"  ❌ {len(missing_tables)}个关键表缺失")
            return False

        # 验证memory_entries表的列结构
        print("  验证表结构...")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(memory_entries);")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()

        # 关键列 - 缺失则失败
        critical_columns = ["entry_id", "entry_type", "timestamp", "content_json"]
        # 重要列 - 缺失则警告
        important_columns = ["priority", "source_agent"]

        missing_critical = []
        missing_important = []

        for col in critical_columns:
            if col in columns:
                print(f"  ✅ 关键列存在: {col}")
            else:
                print(f"  ❌ 关键列缺失: {col}")
                missing_critical.append(col)

        for col in important_columns:
            if col in columns:
                print(f"  ✅ 重要列存在: {col}")
            else:
                print(f"  ⚠️  重要列缺失: {col}")
                missing_important.append(col)

        if missing_critical:
            print(f"  ❌ {len(missing_critical)}个关键列缺失，表结构不完整")
            return False

        if missing_important:
            print(f"  ⚠️  {len(missing_important)}个重要列缺失，可能影响功能")

    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False

    return True


def check_maref_integration():
    """检查MAREF集成"""
    print("\n=== MAREF集成检查 ===")

    try:
        # 检查导入
        sys.path.insert(0, "/Volumes/1TB-M2/openclaw/scripts/clawra")
        from external.ROMA.hexagram_state_manager import HexagramStateManager

        print("✅ HexagramStateManager 导入成功")

        from maref_memory_manager import MAREFMemoryManager

        print("✅ MAREFMemoryManager 导入成功")

        from run_maref_daily_report import create_integration_environment

        print("✅ create_integration_environment 导入成功")

        # 测试集成环境创建
        print("测试集成环境创建...")
        state_manager, agents = create_integration_environment()

        if state_manager is not None and agents is not None:
            print("✅ 集成环境创建成功")
            print(f"  当前卦象: {state_manager.current_state}")
            print(f"  状态管理器类型: {type(state_manager).__name__}")

            # 检查智能体
            agent_types = ["guardian", "communicator", "learner", "explorer"]
            for agent_type in agent_types:
                if agent_type in agents:
                    agent = agents[agent_type]
                    print(f"  ✅ {agent_type}智能体存在: {type(agent).__name__}")
                else:
                    print(f"  ⚠️  {agent_type}智能体缺失")

            return True
        else:
            print("❌ 集成环境不完整")
            return False

    except Exception as e:
        print(f"❌ MAREF集成检查失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """主检查函数"""
    print("=== MAREF生产环境部署前检查 ===\n")

    checks = [
        ("Python版本", check_python_version),
        ("依赖包", check_dependencies),
        ("目录结构", check_directories),
        ("数据库", check_database),
        ("MAREF集成", check_maref_integration),
    ]

    results = []
    for check_name, check_func in checks:
        print(f"\n--- {check_name}检查 ---")
        try:
            result = check_func()
            results.append((check_name, result))
            print(f"结果: {'✅ 通过' if result else '❌ 失败'}")
        except Exception as e:
            print(f"❌ 检查异常: {e}")
            results.append((check_name, False))

    print("\n=== 检查总结 ===")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"通过: {passed}/{total}")

    if passed == total:
        print("✅ 所有检查通过，环境就绪")
        return 0
    else:
        print("❌ 部分检查未通过，请修复后重试")
        for check_name, result in results:
            if not result:
                print(f"  - {check_name}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
