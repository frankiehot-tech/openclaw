#!/usr/bin/env python3
"""
MAREF配置回滚脚本
功能：将MAREF配置恢复到安全状态（read_only_mode: true）
"""

import shutil
import sys
from datetime import datetime
from pathlib import Path

import yaml

# 配置路径
CONFIG_FILE = Path("/Volumes/1TB-M2/openclaw/.openclaw/maref/config/config.yaml")
BACKUP_SUFFIX = ".rollback_" + datetime.now().strftime("%Y%m%d_%H%M%S")


def load_config():
    """加载配置文件"""
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"❌ 加载配置文件失败: {e}")
        return None


def save_config(config_data):
    """保存配置文件（先备份）"""
    try:
        # 创建备份
        backup_path = CONFIG_FILE.with_suffix(CONFIG_FILE.suffix + BACKUP_SUFFIX)
        shutil.copy2(CONFIG_FILE, backup_path)
        print(f"📂 已创建备份: {backup_path}")

        # 保存新配置
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, allow_unicode=True, default_flow_style=False)

        return True
    except Exception as e:
        print(f"❌ 保存配置文件失败: {e}")
        return False


def rollback_to_safe_state():
    """回滚到安全状态"""
    print("🔧 MAREF配置回滚脚本")
    print("=" * 60)

    config_data = load_config()
    if not config_data:
        return False

    print("📊 当前配置状态:")
    print(f"  read_only_mode: {config_data.get('read_only_mode', '未设置')}")
    print(f"  auto_apply_suggestions: {config_data.get('auto_apply_suggestions', '未设置')}")
    print(f"  integration_mode: {config_data.get('integration_mode', '未设置')}")
    print(
        f"  suggestion_confidence_threshold: {config_data.get('suggestion_confidence_threshold', '未设置')}"
    )

    # 安全配置值
    safe_config = {
        "read_only_mode": True,
        "auto_apply_suggestions": False,
        "integration_mode": "observer",
        "suggestion_confidence_threshold": 0.7,
    }

    print(f"\n🔒 安全配置:")
    for key, value in safe_config.items():
        print(f"  {key}: {value}")

    # 询问确认
    print(f"\n❓ 是否回滚到安全状态？")
    print(f"  输入 'yes' 执行回滚")
    print(f"  输入 'no' 或直接回车取消")

    try:
        user_input = input("  你的选择: ").strip().lower()
    except EOFError:
        user_input = "no"

    if user_input != "yes":
        print("❌ 回滚取消")
        return False

    # 更新配置
    config_data.update(safe_config)

    if save_config(config_data):
        print(f"\n✅ 配置已回滚到安全状态")

        # 验证回滚
        verify_config = load_config()
        if verify_config:
            print(f"\n✅ 验证回滚结果:")
            for key, expected_value in safe_config.items():
                actual_value = verify_config.get(key)
                if actual_value == expected_value:
                    print(f"  ✅ {key}: {actual_value}")
                else:
                    print(f"  ❌ {key}: 期望 {expected_value}, 实际 {actual_value}")
        return True
    else:
        print(f"\n❌ 回滚失败")
        return False


def check_maref_status():
    """检查MAREF状态"""
    print(f"\n🔍 MAREF状态检查:")
    print("=" * 40)

    config_data = load_config()
    if not config_data:
        return False

    # 检查关键配置
    critical_configs = [
        ("enabled", True, "MAREF是否启用"),
        ("read_only_mode", False, "是否只读模式"),
        ("auto_apply_suggestions", True, "是否自动应用建议"),
        ("integration_mode", "auto_optimize", "集成模式"),
    ]

    all_ok = True
    for key, expected_value, description in critical_configs:
        actual_value = config_data.get(key)
        if actual_value == expected_value:
            print(f"  ✅ {description}: {actual_value}")
        else:
            print(f"  ⚠️  {description}: 期望 {expected_value}, 实际 {actual_value}")
            all_ok = False

    return all_ok


def main():
    """主函数"""
    print("🔧 MAREF配置管理工具")
    print("=" * 60)

    # 检查当前状态
    if check_maref_status():
        print(f"\n✅ MAREF配置处于自动化启用状态")
    else:
        print(f"\n⚠️  MAREF配置可能有问题")

    # 提供选项
    print(f"\n📋 可用操作:")
    print(f"  1. 检查当前状态")
    print(f"  2. 回滚到安全状态")
    print(f"  3. 退出")

    try:
        choice = input("\n  选择操作 (1-3): ").strip()
    except EOFError:
        choice = "3"

    if choice == "1":
        check_maref_status()
    elif choice == "2":
        rollback_to_safe_state()
    else:
        print("👋 退出")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 脚本执行失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
