#!/usr/bin/env python3
"""错误分类与根因分析"""

import glob
import json
import os
import re
import time
from collections import Counter
from datetime import datetime
from pathlib import Path


def analyze_queue_errors():
    """分析队列文件中的错误"""

    print("🔍 分析队列文件中的错误...")

    error_types = Counter()
    error_details = []
    queue_dir = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue/"

    for file_path in glob.glob(os.path.join(queue_dir, "*.json")):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            queue_name = os.path.basename(file_path)
            items = data.get("items", {})

            for item_id, item_data in items.items():
                status = item_data.get("status", "")
                if status == "failed":
                    error_msg = item_data.get("error", "")
                    summary = item_data.get("summary", "")
                    task_title = item_data.get("title", "")

                    # 分类错误类型
                    error_type = classify_error(error_msg, summary, task_title)
                    error_types[error_type] += 1

                    error_details.append(
                        {
                            "queue": queue_name,
                            "item_id": item_id,
                            "item_title": task_title,
                            "error_type": error_type,
                            "error_msg": error_msg[:200],  # 截断长错误消息
                            "summary": summary[:200] if summary else "",
                            "started_at": item_data.get("started_at", ""),
                            "finished_at": item_data.get("finished_at", ""),
                            "retry_count": item_data.get("retry_count", 0),
                        }
                    )

        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {file_path} - {e}")
        except Exception as e:
            print(f"❌ 分析队列错误失败: {file_path} - {e}")

    return error_types, error_details


def analyze_task_logs():
    """分析任务日志中的错误"""

    print("🔍 分析任务日志中的错误...")

    log_errors = Counter()
    log_details = []
    tasks_dir = "/Volumes/1TB-M2/openclaw/.openclaw/orchestrator/tasks/"

    # 查找最近30天的任务日志
    for log_file in glob.glob(os.path.join(tasks_dir, "**/*.log"), recursive=True):
        try:
            # 检查文件修改时间（最近30天）
            file_mtime = os.path.getmtime(log_file)
            days_old = (time.time() - file_mtime) / (24 * 3600)
            if days_old > 30:
                continue

            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # 查找错误模式
            error_patterns = [
                (r"Error:.*", "通用错误"),
                (r"error:.*", "小写错误"),
                (r"证书.*错误|certificate.*error", "证书错误"),
                (r"超时|timeout", "超时错误"),
                (r"不存在|not found", "文件不存在"),
                (r"权限|permission", "权限错误"),
                (r"内存|memory", "内存错误"),
                (r"连接|connection", "连接错误"),
            ]

            for pattern, error_type in error_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    log_errors[error_type] += len(matches)

                    # 记录详细错误
                    for match in matches[:3]:  # 只记录前3个
                        log_details.append(
                            {
                                "log_file": os.path.basename(os.path.dirname(log_file)),
                                "error_type": error_type,
                                "error_msg": match[:150],
                                "file_path": log_file,
                            }
                        )

        except Exception as e:
            print(f"❌ 分析日志文件失败: {log_file} - {e}")

    return log_errors, log_details


def classify_error(error_msg, summary, task_title):
    """分类错误类型"""

    combined_text = f"{error_msg} {summary} {task_title}".lower()

    # 证书相关错误
    if any(keyword in combined_text for keyword in ["证书", "certificate", "ssl", "tls"]):
        return "证书验证错误"

    # 文件路径错误
    if any(
        keyword in combined_text
        for keyword in ["不存在", "not found", "找不到", "instruction_path"]
    ):
        return "文件路径错误"

    # 认证错误
    if any(
        keyword in combined_text for keyword in ["401", "unauthorized", "认证", "authentication"]
    ):
        return "认证错误"

    # 网络错误
    if any(
        keyword in combined_text for keyword in ["404", "timeout", "超时", "连接", "connection"]
    ):
        return "网络错误"

    # 格式错误
    if any(keyword in combined_text for keyword in ["格式", "format", "json", "解析"]):
        return "数据格式错误"

    # 资源错误
    if any(keyword in combined_text for keyword in ["内存", "memory", "磁盘", "disk", "空间"]):
        return "资源不足错误"

    # 配置错误
    if any(keyword in combined_text for keyword in ["配置", "config", "设置", "setting"]):
        return "配置错误"

    # 依赖错误
    if any(
        keyword in combined_text for keyword in ["依赖", "dependency", "模块", "module", "import"]
    ):
        return "依赖错误"

    return "未知错误"


def generate_error_report(error_types, error_details, log_errors, log_details):
    """生成错误分析报告"""

    print("\n" + "=" * 60)
    print("📊 多Agent系统错误分析报告")
    print("=" * 60)

    # 队列错误统计
    total_queue_errors = sum(error_types.values())
    print(f"\n📈 队列错误统计:")
    print(f"   总错误数: {total_queue_errors}")

    if total_queue_errors > 0:
        print(f"   错误率: {total_queue_errors}/111 = {(total_queue_errors/111)*100:.1f}%")
        print("\n   错误类型分布:")

        for error_type, count in error_types.most_common():
            percentage = (count / total_queue_errors) * 100
            print(f"     {error_type}: {count} 次 ({percentage:.1f}%)")
    else:
        print("   ✅ 未发现队列错误")

    # 日志错误统计
    total_log_errors = sum(log_errors.values())
    print(f"\n📝 日志错误统计:")
    print(f"   总错误数: {total_log_errors}")

    if total_log_errors > 0:
        print("\n   错误类型分布:")
        for error_type, count in log_errors.most_common():
            percentage = (count / total_log_errors) * 100
            print(f"     {error_type}: {count} 次 ({percentage:.1f}%)")
    else:
        print("   ✅ 未发现日志错误")

    # 详细错误信息
    if error_details:
        print(f"\n🔍 详细队列错误信息 (前10个):")
        for i, detail in enumerate(error_details[:10]):
            print(f"\n   {i+1}. 队列: {detail['queue']}")
            print(f"      任务: {detail['item_title']}")
            print(f"      类型: {detail['error_type']}")
            print(f"      错误: {detail['error_msg']}")
            if detail["retry_count"] > 0:
                print(f"      重试次数: {detail['retry_count']}")

    # 根因分析
    print(f"\n🔬 根因分析:")

    if "证书验证错误" in error_types:
        print("   ❗ 证书验证错误:")
        print("      - 可能原因: SSL证书配置问题")
        print("      - 建议: 检查证书配置，更新证书链")
        print("      - 修复: 设置环境变量 SSL_CERT_FILE")

    if "文件路径错误" in error_types:
        print("   ❗ 文件路径错误:")
        print("      - 可能原因: 文件被移动或删除")
        print("      - 建议: 检查instruction_path配置")
        print("      - 修复: 验证文件路径存在性")

    if "认证错误" in error_types:
        print("   ❗ 认证错误:")
        print("      - 可能原因: API密钥过期或无效")
        print("      - 建议: 检查token文件和API配置")
        print("      - 修复: 更新认证配置")

    # 修复建议
    print(f"\n💡 修复建议:")

    if total_queue_errors > 0:
        print("   1. 优先修复高频错误类型")
        for error_type, count in error_types.most_common(3):
            print(f"      - {error_type}: {count}次")

        print("\n   2. 实施错误重试机制")
        print("      - 指数退避重试策略")
        print("      - 错误分类重试")

        print("\n   3. 加强错误监控")
        print("      - 实时错误告警")
        print("      - 错误趋势分析")
    else:
        print("   ✅ 系统错误率较低，建议:")
        print("      - 继续保持监控")
        print("      - 定期错误分析")
        print("      - 预防性维护")

    # 生成报告文件
    report_file = "/Volumes/1TB-M2/openclaw/error_analysis_report.md"
    generate_markdown_report(report_file, error_types, error_details, log_errors, log_details)
    print(f"\n📄 详细报告已生成: {report_file}")


def generate_markdown_report(file_path, error_types, error_details, log_errors, log_details):
    """生成Markdown格式的详细报告"""

    total_queue_errors = sum(error_types.values())
    total_log_errors = sum(log_errors.values())

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("# 多Agent系统错误分析报告\n\n")
        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**分析范围**: 队列文件 + 任务日志\n\n")

        f.write("## 📈 错误统计概览\n\n")
        f.write(f"- **队列错误总数**: {total_queue_errors}\n")
        f.write(f"- **日志错误总数**: {total_log_errors}\n")
        f.write(f"- **综合错误率**: {(total_queue_errors/111)*100:.1f}%\n\n")

        if total_queue_errors > 0:
            f.write("## 📊 队列错误类型分布\n\n")
            f.write("| 错误类型 | 次数 | 占比 |\n")
            f.write("|----------|------|------|\n")
            for error_type, count in error_types.most_common():
                percentage = (count / total_queue_errors) * 100
                f.write(f"| {error_type} | {count} | {percentage:.1f}% |\n")
            f.write("\n")

        if total_log_errors > 0:
            f.write("## 📝 日志错误类型分布\n\n")
            f.write("| 错误类型 | 次数 | 占比 |\n")
            f.write("|----------|------|------|\n")
            for error_type, count in log_errors.most_common():
                percentage = (count / total_log_errors) * 100
                f.write(f"| {error_type} | {count} | {percentage:.1f}% |\n")
            f.write("\n")

        if error_details:
            f.write("## 🔍 详细错误信息\n\n")
            for i, detail in enumerate(error_details[:20]):
                f.write(f"### {i+1}. {detail['item_title']}\n\n")
                f.write(f"- **队列**: {detail['queue']}\n")
                f.write(f"- **错误类型**: {detail['error_type']}\n")
                f.write(f"- **错误信息**: {detail['error_msg']}\n")
                if detail["retry_count"] > 0:
                    f.write(f"- **重试次数**: {detail['retry_count']}\n")
                if detail["started_at"]:
                    f.write(f"- **开始时间**: {detail['started_at']}\n")
                f.write("\n")

        f.write("## 🔬 根因分析与修复建议\n\n")

        # 证书错误
        if "证书验证错误" in error_types:
            f.write("### ❗ 证书验证错误\n\n")
            f.write("**可能原因**:\n")
            f.write("- SSL证书配置不正确\n")
            f.write("- 证书链不完整\n")
            f.write("- 系统证书存储问题\n\n")
            f.write("**修复建议**:\n")
            f.write("1. 设置环境变量: `export SSL_CERT_FILE=/path/to/cert.pem`\n")
            f.write("2. 更新系统证书: `sudo update-ca-certificates`\n")
            f.write("3. 禁用证书验证（仅测试环境）\n\n")

        # 文件路径错误
        if "文件路径错误" in error_types:
            f.write("### ❗ 文件路径错误\n\n")
            f.write("**可能原因**:\n")
            f.write("- 文件被移动或删除\n")
            f.write("- 相对路径解析问题\n")
            f.write("- 权限不足\n\n")
            f.write("**修复建议**:\n")
            f.write("1. 验证文件路径存在性\n")
            f.write("2. 使用绝对路径\n")
            f.write("3. 检查文件权限\n\n")

        # 通用建议
        f.write("## 💡 通用修复建议\n\n")
        f.write("1. **实施错误重试机制**\n")
        f.write("   - 指数退避重试策略\n")
        f.write("   - 错误分类重试（可重试错误 vs 不可重试错误）\n\n")

        f.write("2. **加强错误监控**\n")
        f.write("   - 实时错误告警\n")
        f.write("   - 错误趋势分析\n")
        f.write("   - 自动化根因分析\n\n")

        f.write("3. **预防性维护**\n")
        f.write("   - 定期证书更新\n")
        f.write("   - 文件路径验证\n")
        f.write("   - 依赖包版本管理\n\n")

        f.write("---\n")
        f.write("*报告生成: 多Agent系统错误分析工具*\n")


def main():
    """主函数"""

    print("=" * 60)
    print("多Agent系统错误分析工具")
    print("=" * 60)

    # 分析队列错误
    error_types, error_details = analyze_queue_errors()

    # 分析日志错误
    log_errors, log_details = analyze_task_logs()

    # 生成报告
    generate_error_report(error_types, error_details, log_errors, log_details)

    print("\n" + "=" * 60)
    print("🎉 错误分析完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
