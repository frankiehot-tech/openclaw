#!/usr/bin/env python3
"""
快速探索豆包AI界面状态
"""

import json
import os
import sys
import time

sys.path.append(os.path.dirname(__file__))

from external.ROMA.doubao_cli_prototype import DoubaoCLI


def quick_explore():
    print("=== 快速探索豆包AI界面 ===")

    doubao = DoubaoCLI()

    # 打开页面
    print("打开豆包AI页面...")
    result = doubao.open_doubao_ai()
    print(f"结果: {result}")
    time.sleep(3)

    # 检查输入框
    js = """
    (function() {
        var textarea = document.querySelector('textarea');
        if (!textarea) {
            return JSON.stringify({error: "未找到输入框"});
        }

        var state = {
            placeholder: textarea.placeholder || '',
            value: textarea.value || '',
            isDisabled: textarea.disabled,
            isReadOnly: textarea.readOnly,
            maxLength: textarea.maxLength,
            parentText: (textarea.parentElement ? textarea.parentElement.textContent || '' : '').substring(0, 200)
        };

        // 检查是否有禁用或限制消息
        var disabledMsg = document.querySelector('.disabled-message, .limit-message, .upgrade-message');
        if (disabledMsg) {
            state.disabledMessage = (disabledMsg.textContent || disabledMsg.innerText || '').trim().substring(0, 100);
        }

        // 检查是否有登录提示
        var loginPrompt = document.querySelector('[href*="login"], .login-prompt, button:contains("登录")');
        if (loginPrompt) {
            state.loginPrompt = (loginPrompt.textContent || loginPrompt.innerText || '').trim().substring(0, 100);
        }

        return JSON.stringify(state, null, 2);
    })()
    """

    try:
        result = doubao.execute_javascript(1, 1, js)
        print(f"JavaScript结果: {result}")

        if "JavaScript执行结果: " in result:
            json_str = result.split("JavaScript执行结果: ", 1)[1]
            data = json.loads(json_str)

            print(f"\n输入框状态:")
            print(f"占位符: {data.get('placeholder', '无')}")
            print(f"当前值: {data.get('value', '空')}")
            print(f"是否禁用: {data.get('isDisabled', False)}")
            print(f"是否只读: {data.get('isReadOnly', False)}")
            print(f"最大长度: {data.get('maxLength', '未限制')}")

            if "disabledMessage" in data:
                print(f"⚠️ 禁用消息: {data['disabledMessage']}")
            if "loginPrompt" in data:
                print(f"⚠️ 登录提示: {data['loginPrompt']}")

            return data
        else:
            print(f"⚠️ 无法解析结果: {result[:100]}...")
            return None

    except Exception as e:
        print(f"❌ 探索失败: {e}")
        import traceback

        traceback.print_exc()
        return None


if __name__ == "__main__":
    data = quick_explore()
    if data:
        print("\n✅ 探索完成")
        sys.exit(0)
    else:
        print("\n❌ 探索失败")
        sys.exit(1)
