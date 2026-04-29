#!/usr/bin/env python3
"""
Gate 3 测试脚本：验证真机截图 -> vision_router -> qwen_service 链路
修复版本：处理adb截图中的警告信息
"""

import logging
import os
import subprocess
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from vision.vision_router import describe_with_qwen


def capture_screen_without_warnings():
    """捕获屏幕截图，过滤adb警告信息"""
    screenshot_path = "/tmp/athena_gate3_screen.png"

    try:
        # 执行adb命令
        proc = subprocess.Popen(
            ["adb", "-s", "R3CR80FKA0V", "exec-out", "screencap", "-p"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        stdout_data, stderr_data = proc.communicate()

        # 查找PNG文件头
        png_header = b"\x89PNG\r\n\x1a\n"
        pos = stdout_data.find(png_header)

        if pos == -1:
            raise ValueError("未找到PNG文件头")

        # 提取PNG数据
        png_data = stdout_data[pos:]

        # 写入文件
        with open(screenshot_path, "wb") as f:
            f.write(png_data)

        return screenshot_path, len(png_data)

    except Exception as e:
        raise RuntimeError(f"截图失败: {str(e)}")


def main():
    """主函数"""
    # 设置日志
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    logger = logging.getLogger(__name__)

    # 截图路径
    screenshot_path = "/tmp/athena_gate3_screen.png"

    try:
        # 捕获屏幕截图
        logger.info("捕获屏幕截图...")
        screenshot_path, file_size = capture_screen_without_warnings()
        logger.info(f"截图文件: {screenshot_path}, 大小: {file_size} bytes")

        # 调用 vision_router 的 qwen 分支
        logger.info("调用 vision_router.describe_with_qwen...")
        result = describe_with_qwen(screenshot_path)

        logger.info(f"Qwen 服务返回: {result}")

        # 检查结果
        if result.get("ok"):
            text = result.get("text", "")
            if text and isinstance(text, str) and len(text.strip()) > 0:
                return {"success": True, "text": text, "raw_result": result}
            else:
                return {
                    "success": False,
                    "error": "vision_result_invalid",
                    "message": "返回文本为空或无效",
                    "raw_result": result,
                }
        else:
            error_msg = result.get("error", "未知错误")
            return {
                "success": False,
                "error": "router_call_failed",
                "message": f"Qwen 服务调用失败: {error_msg}",
                "raw_result": result,
            }

    except Exception as e:
        logger.error(f"测试失败: {e}")
        return {"success": False, "error": "test_failed", "message": f"测试失败: {str(e)}"}


if __name__ == "__main__":
    result = main()

    # 输出结果
    print("\n=== Gate 3 测试结果 ===")
    print(f"成功: {result.get('success', False)}")

    if result.get("success"):
        print(f"输出文本: {result.get('text', '')}")
    else:
        print(f"错误类型: {result.get('error', 'unknown')}")
        print(f"错误信息: {result.get('message', '')}")

    # 输出原始结果（调试用）
    if "raw_result" in result:
        print(f"\n原始结果: {result['raw_result']}")
