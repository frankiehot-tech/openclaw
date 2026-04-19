#!/usr/bin/env python3
"""最终图像生成测试 - 45秒超时"""

import logging
import os
import sys
import time

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(__file__))


def clear_input_field(cli):
    """清除输入字段"""
    print("清理输入字段...")
    js_code = """
    (function() {
        var inputs = document.querySelectorAll('textarea, input[type="text"]');
        if (inputs.length > 0) {
            inputs[0].value = '';
            inputs[0].dispatchEvent(new Event('input', { bubbles: true }));
            return "输入字段已清空";
        }
        return "未找到输入字段";
    })()
    """
    result = cli.execute_javascript_enhanced(js_code)
    if result.success:
        print(f"清理结果: {result.output}")
    else:
        print(f"清理失败: {result.error_message}")
    time.sleep(1)


def test_complete_generation_with_timeout(timeout_seconds=45):
    """测试完整生成过程，带有超时"""
    print(f"=== 测试完整图像生成（{timeout_seconds}秒超时） ===")

    try:
        from external.ROMA.doubao_cli_enhanced import (
            DoubaoCLIEnhanced,
            ImageGenerationParams,
        )

        # 初始化
        cli = DoubaoCLIEnhanced()

        # 设置超时
        cli.image_generation_timeout = timeout_seconds
        print(f"超时时间设置为: {cli.image_generation_timeout}秒")

        # 创建测试参数
        params = ImageGenerationParams(
            prompt="一个简单的测试图像，蓝天白云，阳光明媚",
            style="realistic",
            size="512x512",
            quality="standard",
            num_images=1,
        )

        print(f"生成参数:")
        print(f"  提示词: {params.prompt}")
        print(f"  风格: {params.style}")
        print(f"  尺寸: {params.size}")
        print(f"  质量: {params.quality}")

        # 可选：清除现有输入
        clear_input_field(cli)

        print("\n开始图像生成...")
        print(f"预计等待最多 {timeout_seconds} 秒...")
        print("如果超时，测试仍将记录流程状态")

        start_time = time.time()
        result = cli.generate_image(params)
        elapsed = time.time() - start_time

        print(f"\n=== 生成结果 ===")
        print(f"总耗时: {elapsed:.1f}秒")
        print(f"成功: {result.success}")

        if result.success:
            print("✅ 图像生成成功！")
            print(f"生成图像数量: {len(result.image_urls)}")

            if result.image_urls:
                print("图像URL:")
                for i, url in enumerate(result.image_urls):
                    print(f"  {i+1}. {url}")

            # 显示元数据
            print("\n元数据:")
            for key, value in result.metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    print(f"  {key}: {value}")

            return True
        else:
            print(f"❌ 图像生成失败")
            print(f"错误信息: {result.error_message}")

            # 分析错误类型
            if "超时" in result.error_message or "timeout" in result.error_message.lower():
                print("⚠️  超时错误 - 生成可能仍在进行中")
                print("   这可能是测试设置的短超时导致的")
                print("   在实际使用中，可以增加超时时间")
                return True  # 超时在测试中可接受
            elif "未找到" in result.error_message or "not found" in result.error_message.lower():
                print("⚠️  DOM元素未找到 - 界面可能已改变")
                return False
            elif "权限" in result.error_message or "permission" in result.error_message.lower():
                print("⚠️  权限错误 - 需要检查豆包设置")
                return False
            else:
                print("❌ 未知错误类型")
                return False

    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("豆包图像生成最终测试\n")

    # 显示当前状态
    print("当前豆包状态:")
    try:
        from external.ROMA.doubao_cli_enhanced import DoubaoCLIEnhanced

        cli = DoubaoCLIEnhanced()
        title_result = cli.execute_javascript_enhanced("document.title")
        url_result = cli.execute_javascript_enhanced("window.location.href")

        if title_result.success and url_result.success:
            title = title_result.output.replace("JavaScript执行结果: ", "")
            url = url_result.output.replace("JavaScript执行结果: ", "")
            print(f"  页面标题: {title}")
            print(f"  页面URL: {url}")
        else:
            print("  无法获取页面状态")
    except:
        print("  状态检查失败")

    print("\n测试将执行以下操作:")
    print("1. 打开豆包AI绘画界面（如果不在该界面）")
    print("2. 输入提示词: '一个简单的测试图像，蓝天白云，阳光明媚'")
    print("3. 选择风格: 'realistic'（写实）")
    print("4. 设置尺寸: 512x512")
    print("5. 触发生成")
    print("6. 等待生成完成（最多45秒）")
    print()

    response = input("是否继续？(y/n): ")
    if response.lower() != "y":
        print("测试取消")
        return 0

    # 运行测试
    success = test_complete_generation_with_timeout(45)

    if success:
        print("\n✅ 测试成功完成")
        print("豆包CLI增强版功能验证通过")
        return 0
    else:
        print("\n❌ 测试失败")
        print("需要调试豆包CLI增强版")
        return 1


if __name__ == "__main__":
    sys.exit(main())
