#!/usr/bin/env python3
"""
检查豆包登录状态
"""

import json
import os
import sys
import time

sys.path.append(os.path.dirname(__file__))

from external.ROMA.doubao_cli_prototype import DoubaoCLI


def check_login():
    """检查登录状态"""
    print("=== 检查豆包登录状态 ===")

    doubao = DoubaoCLI()

    # 打开页面
    print("打开豆包页面...")
    result = doubao.open_doubao_ai()
    print(f"打开结果: {result}")
    time.sleep(3)

    # 检查登录状态
    js_check = """
    (function() {
        var bodyText = document.body.innerText || document.body.textContent || '';
        var html = document.documentElement.innerHTML;

        var state = {
            // 检查登录相关文本
            hasLoginText: bodyText.includes('登录') || bodyText.includes('登录') ||
                         bodyText.includes('Sign in') || bodyText.includes('sign in'),
            hasAccountText: bodyText.includes('账号') || bodyText.includes('账户') ||
                           bodyText.includes('Account') || bodyText.includes('account'),
            hasAvatar: !!document.querySelector('img[src*="avatar"], img[alt*="头像"], [class*="avatar"]'),
            // 检查输入框是否可用
            hasInput: !!document.querySelector('textarea, input[type="text"], [contenteditable="true"]'),
            inputDisabled: false,
            // 检查可能的错误消息
            hasError: bodyText.includes('请登录') || bodyText.includes('需要登录') ||
                     bodyText.includes('未登录') || bodyText.includes('登录后使用'),
            // 检查用户信息
            hasUserInfo: bodyText.includes('欢迎') || bodyText.includes('Welcome') ||
                        bodyText.includes('你好') || bodyText.includes('Hi ')
        };

        // 检查输入框是否禁用
        var inputs = document.querySelectorAll('textarea, input[type="text"], [contenteditable="true"]');
        if (inputs.length > 0) {
            state.inputDisabled = inputs[0].disabled || inputs[0].readOnly ||
                                 inputs[0].getAttribute('aria-disabled') === 'true';
        }

        return JSON.stringify(state, null, 2);
    })()
    """

    try:
        result = doubao.execute_javascript(1, 1, js_check)
        print(f"JavaScript结果: {result}")

        if "JavaScript执行结果: " in result:
            json_str = result.split("JavaScript执行结果: ", 1)[1].strip()
            if json_str != "missing value":
                data = json.loads(json_str)
                print(f"\n登录状态分析:")
                print(f"  有登录相关文本: {data['hasLoginText']}")
                print(f"  有账号相关文本: {data['hasAccountText']}")
                print(f"  有头像: {data['hasAvatar']}")
                print(f"  有输入框: {data['hasInput']}")
                print(f"  输入框禁用: {data['inputDisabled']}")
                print(f"  有错误消息: {data['hasError']}")
                print(f"  有用户信息: {data['hasUserInfo']}")

                # 判断是否已登录
                if data["hasError"] or data["hasLoginText"]:
                    print("\n⚠️ 可能未登录或需要登录")
                    return False
                elif data["hasAvatar"] and data["hasInput"] and not data["inputDisabled"]:
                    print("\n✅ 可能已登录")
                    return True
                else:
                    print("\n❓ 登录状态不确定")
                    return None
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        return None


def main():
    print("豆包登录状态检查")
    print("=" * 60)

    login_status = check_login()

    print("\n" + "=" * 60)
    print("检查结果")
    print("=" * 60)

    if login_status is True:
        print("✅ 豆包可能已登录，可以继续测试AI功能")
    elif login_status is False:
        print("⚠️ 豆包可能未登录，需要手动登录后再测试")
        print("\n📝 操作步骤:")
        print("1. 手动打开豆包应用")
        print("2. 完成登录（如果需要）")
        print("3. 确保进入AI聊天界面")
        print("4. 然后重新运行自动化测试")
    else:
        print("❓ 无法确定登录状态，建议手动检查")

    # 保存结果
    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "login_status": (
            "logged_in"
            if login_status is True
            else "not_logged_in" if login_status is False else "unknown"
        ),
    }

    with open("login_check_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n结果已保存到: login_check_results.json")


if __name__ == "__main__":
    main()
