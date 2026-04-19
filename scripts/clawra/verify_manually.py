#!/usr/bin/env python3
"""
手动验证豆包AI状态指南
"""

import json
import os
import subprocess
import sys
import time


def print_step(step_num, title):
    print(f"\n{step_num}. {title}")
    print("-" * 50)


def print_instruction(instruction):
    print(f"📋 {instruction}")


def print_warning(warning):
    print(f"⚠️  {warning}")


def print_success(message):
    print(f"✅  {message}")


def main():
    print("=" * 70)
    print("豆包AI手动验证指南")
    print("=" * 70)

    print("根据自动化诊断发现的问题，请按以下步骤手动验证：")

    print_step("1", "手动启动豆包应用")
    print_instruction("请执行以下操作：")
    print("  a) 打开Finder，前往应用程序文件夹")
    print("  b) 找到'豆包'应用（图标可能显示为'Doubao'）")
    print("  c) 双击启动豆包应用")
    print("  d) 等待应用完全启动（可能需要几秒钟）")

    input("\n按Enter键继续...")

    print_step("2", "检查应用窗口状态")
    print_instruction("启动豆包后，检查以下内容：")
    print("  a) 豆包主窗口是否出现？")
    print("  b) 窗口标题是什么？")
    print("  c) 窗口内是否显示登录界面或聊天界面？")

    window_status = input("\n请描述你看到的窗口内容: ")

    print_step("3", "登录验证")
    print_instruction("检查是否需要登录：")
    print("  a) 是否看到'登录'按钮或输入账号的界面？")
    print("  b) 如果有登录按钮，请点击并完成登录")
    print("  c) 如果已登录，右上角应该显示你的账号头像")

    login_status = input("\n是否需要登录？(是/否): ")

    print_step("4", "AI聊天界面验证")
    print_instruction("登录后，执行以下测试：")
    print("  a) 在豆包界面中找到输入框（通常在底部）")
    print("  b) 手动输入：'你好，请回复测试成功'")
    print("  c) 按Enter或点击发送按钮")
    print("  d) 等待AI回复（通常需要几秒钟）")

    ai_response = input("\nAI是否回复了？(是/否): ")

    print_step("5", "图像生成测试")
    print_instruction("测试图像生成功能：")
    print("  a) 在输入框中输入：'/draw 一个红色的圆形'")
    print("  b) 或者输入：'生成一张简单的测试图片，比如一个红色的圆形'")
    print("  c) 等待图像生成（可能需要30-90秒）")
    print("  d) 观察是否出现新的图像")

    image_generated = input("\n是否生成了新的图像？(是/否): ")

    print_step("6", "自动化准备")
    print_instruction("为自动化控制准备：")
    print("  a) 确保豆包窗口在屏幕最前面")
    print("  b) 确保AI聊天界面可见")
    print("  c) 不要最小化窗口或切换到其他应用")

    print("\n" + "=" * 70)
    print("验证结果摘要")
    print("=" * 70)

    results = {
        "app_launched": "手动启动" if window_status else "未确认",
        "window_state": window_status[:100],
        "login_needed": login_status,
        "ai_responded": ai_response,
        "image_generated": image_generated,
    }

    print(f"应用启动状态: {results['app_launched']}")
    print(f"窗口状态: {results['window_state']}")
    print(f"需要登录: {results['login_needed']}")
    print(f"AI响应: {results['ai_responded']}")
    print(f"图像生成: {results['image_generated']}")

    print("\n🎯 关键发现:")

    if login_status.lower() == "是":
        print_warning("豆包需要登录才能使用AI功能")
        print_instruction("请完成登录后再继续自动化测试")

    if ai_response.lower() == "否":
        print_warning("AI未响应，可能原因：")
        print("  - 未登录或登录过期")
        print("  - 网络问题")
        print("  - AI服务暂时不可用")
        print("  - 免费额度可能已用完")

    if image_generated.lower() == "是":
        print_success("图像生成功能可用，可以继续自动化测试")
    elif image_generated.lower() == "否":
        print_warning("图像生成可能不可用或需要特定条件")
        print("  - 可能需要付费订阅")
        print("  - 可能有每日限制")
        print("  - 可能需要特定格式的提示词")

    print("\n📝 下一步建议:")
    if login_status.lower() == "是":
        print("1. 先完成豆包登录")
        print("2. 手动验证AI聊天功能")
        print("3. 然后重新运行自动化测试")
    elif ai_response.lower() == "否":
        print("1. 检查网络连接")
        print("2. 尝试重启豆包应用")
        print("3. 查看豆包是否有错误提示")
    else:
        print("1. 保持豆包窗口打开并处于最前面")
        print("2. 运行自动化测试脚本")
        print("3. 监控自动化执行过程")

    # 保存验证结果
    result_file = "manual_verification_results.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n验证结果已保存到: {result_file}")
    print("\n✅ 手动验证指南完成")


if __name__ == "__main__":
    main()
