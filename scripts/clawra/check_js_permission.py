#!/usr/bin/env python3
"""
检查豆包JavaScript权限
"""

import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from external.ROMA.doubao_cli_prototype import DoubaoCLI


def check_js_permission():
    """检查JavaScript权限是否启用"""
    print("🔧 检查豆包JavaScript权限...")
    print("=" * 60)

    cli = DoubaoCLI()

    # 测试1: 最简单的JavaScript
    print("\n📋 测试1: 简单字符串")
    result = cli.execute_javascript(js_code="'权限测试'")
    print(f"   结果: {repr(result)}")

    if "JavaScript执行结果: 权限测试" in result:
        print("   ✅ JavaScript执行正常")
        permission_enabled = True
    elif "missing value" in result:
        print("   ⚠️  返回'missing value'，可能权限未启用")
        permission_enabled = False
    elif "JavaScript执行错误" in result:
        print("   ❌ JavaScript执行错误，权限可能未启用")
        permission_enabled = False
    else:
        print(f"   ⚠️  未知结果")
        permission_enabled = False

    # 测试2: 获取页面标题
    print("\n📋 测试2: 获取页面标题")
    result2 = cli.execute_javascript(js_code="document.title")
    print(f"   结果: {repr(result2)}")

    if "JavaScript执行结果:" in result2 and "missing value" not in result2:
        print(f"   ✅ 页面标题获取成功")
        title_working = True
    else:
        print(f"   ⚠️  页面标题获取失败")
        title_working = False

    print("\n" + "=" * 60)
    print("📊 权限检查结果")
    print("=" * 60)

    if permission_enabled and title_working:
        print("✅ JavaScript权限已启用")
        print("\n💡 豆包CLI可以正常工作")
        return True
    else:
        print("❌ JavaScript权限可能未启用")
        print("\n🔧 启用JavaScript权限的步骤:")
        print("1. 确保豆包应用在前台运行")
        print("2. 点击菜单栏: 查看 > 开发者")
        print("3. 勾选: 允许Apple事件中的JavaScript")
        print("4. 重新运行此测试")
        print("\n⚠️  如果已启用但仍有问题:")
        print("1. 重启豆包应用")
        print("2. 检查豆包应用版本")
        print("3. 确保不是豆包网页版，而是桌面应用")
        return False


def main():
    """主函数"""
    print("🎯 豆包JavaScript权限诊断")

    try:
        enabled = check_js_permission()
        return 0 if enabled else 1
    except Exception as e:
        print(f"\n❌ 检查出错: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
