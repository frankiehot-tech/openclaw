#!/usr/bin/env python3
"""测试集成模式下的日报生成"""

import logging
import os
import sys

sys.path.append(os.path.dirname(__file__))

# 设置日志级别为WARNING以减少输出
logging.basicConfig(level=logging.WARNING)

from run_maref_daily_report import run_daily_report

print("=== 测试集成模式日报生成 ===")
print("注意: 这可能会运行几分钟，将收集实际MAREF智能体数据...")

try:
    # 运行集成模式日报生成
    report_path = run_daily_report(mode="integration", output_dir="/tmp/maref_test")

    if report_path:
        print(f"✅ 日报生成成功!")
        print(f"   报告路径: {report_path}")

        # 检查报告文件是否存在
        if os.path.exists(report_path):
            file_size = os.path.getsize(report_path)
            print(f"   报告文件大小: {file_size} 字节")

            # 读取前几行预览
            try:
                with open(report_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()[:10]
                print(f"   报告预览 (前10行):")
                for i, line in enumerate(lines):
                    print(f"     {i+1}: {line.rstrip()}")
            except Exception as e:
                print(f"   无法读取报告文件: {e}")
        else:
            print(f"⚠️  报告文件不存在: {report_path}")
    else:
        print("❌ 日报生成失败")

except Exception as e:
    print(f"❌ 运行日报生成时发生异常: {e}")
    import traceback

    traceback.print_exc()

print("\n=== 测试完成 ===")
