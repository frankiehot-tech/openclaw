#!/usr/bin/env python3
"""
多Agent系统错误分类分析器
基于《多Agent系统24小时压力测试问题修复实施方案》1.2节实现
"""

import glob
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any


class ErrorClassificationAnalyzer:
    """错误分类与根因分析器"""

    def __init__(self, plan_queue_dir: str = "/Volumes/1TB-M2/openclaw/.openclaw/plan_queue"):
        self.plan_queue_dir = plan_queue_dir
        self.error_categories = {
            "timeout": {
                "description": "超时类错误",
                "patterns": [
                    "stale queue task",
                    "timeout",
                    "timed out",
                    "no heartbeat",
                    "响应超时",
                    "连接超时",
                ],
                "examples": [],
            },
            "oom": {
                "description": "内存不足类错误",
                "patterns": [
                    "out of memory",
                    "OOM",
                    "memory limit exceeded",
                    "MemoryError",
                    "无法分配内存",
                ],
                "examples": [],
            },
            "config": {
                "description": "配置类错误",
                "patterns": [
                    "config_error",
                    "configuration error",
                    "invalid config",
                    "missing config",
                    "配置错误",
                    "配置文件不存在",
                ],
                "examples": [],
            },
            "logic": {
                "description": "逻辑类错误",
                "patterns": [
                    "logic error",
                    "validation_error",
                    "invalid operation",
                    "业务逻辑错误",
                    "状态错误",
                ],
                "examples": [],
            },
            "network": {
                "description": "网络类错误",
                "patterns": [
                    "network error",
                    "connection refused",
                    "connection reset",
                    "network unreachable",
                    "网络错误",
                ],
                "examples": [],
            },
            "resource": {
                "description": "资源类错误",
                "patterns": [
                    "resource exhausted",
                    "rate limit",
                    "quota exceeded",
                    "资源不足",
                    "容量不足",
                ],
                "examples": [],
            },
            "unknown": {"description": "未知错误类型", "patterns": [], "examples": []},
        }

    def load_queue_files(self) -> list[dict[str, Any]]:
        """加载所有队列文件"""
        queue_files = []
        pattern = os.path.join(self.plan_queue_dir, "*.json")

        for file_path in glob.glob(pattern):
            try:
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)
                    queue_files.append(
                        {
                            "file": file_path,
                            "data": data,
                            "queue_id": data.get("queue_id", ""),
                            "updated_at": data.get("updated_at", ""),
                        }
                    )
            except Exception as e:
                print(f"警告: 无法加载队列文件 {file_path}: {e}")

        return queue_files

    def analyze_queue_errors(self, queue_data: dict[str, Any]) -> list[dict[str, Any]]:
        """分析队列中的错误任务"""
        errors = []

        if "items" not in queue_data:
            return errors

        for item_id, item_data in queue_data["items"].items():
            status = item_data.get("status", "")
            error = item_data.get("error", "")
            summary = item_data.get("summary", "")

            if status == "failed" or error or "error" in summary.lower():
                # 构建错误信息
                error_info = {
                    "item_id": item_id,
                    "queue_id": queue_data.get("queue_id", ""),
                    "title": item_data.get("title", ""),
                    "status": status,
                    "error": error,
                    "summary": summary,
                    "result_excerpt": item_data.get("result_excerpt", ""),
                    "started_at": item_data.get("started_at", ""),
                    "finished_at": item_data.get("finished_at", ""),
                    "category": self.classify_error(error, summary),
                    "root_cause": "",
                    "retryable": self.is_retryable(error, summary),
                }
                errors.append(error_info)

        return errors

    def classify_error(self, error_text: str, summary_text: str) -> str:
        """对错误进行分类"""
        text = f"{error_text} {summary_text}".lower()

        for category, info in self.error_categories.items():
            if category == "unknown":
                continue

            for pattern in info["patterns"]:
                if pattern.lower() in text:
                    return category

        return "unknown"

    def is_retryable(self, error_text: str, summary_text: str) -> bool:
        """判断错误是否可重试"""
        text = f"{error_text} {summary_text}".lower()

        # 不可重试的错误类型
        non_retryable_patterns = [
            "config_error",
            "validation_error",
            "invalid config",
            "配置错误",
            "业务逻辑错误",
        ]

        # 可重试的错误类型
        retryable_patterns = [
            "timeout",
            "stale queue task",
            "rate limit",
            "network error",
            "connection refused",
            "资源不足",
            "临时错误",
        ]

        # 检查不可重试类型
        for pattern in non_retryable_patterns:
            if pattern.lower() in text:
                return False

        # 检查可重试类型
        for pattern in retryable_patterns:
            if pattern.lower() in text:
                return True

        return True  # 默认可重试

    def analyze_all_errors(self) -> dict[str, Any]:
        """分析所有错误"""
        print("正在分析队列错误...")
        queue_files = self.load_queue_files()

        all_errors = []
        for queue_info in queue_files:
            errors = self.analyze_queue_errors(queue_info["data"])
            all_errors.extend(errors)

        # 统计分类分布
        category_stats = dict.fromkeys(self.error_categories.keys(), 0)
        retryable_stats = {"retryable": 0, "non_retryable": 0}

        for error in all_errors:
            category = error["category"]
            category_stats[category] = category_stats.get(category, 0) + 1

            if error["retryable"]:
                retryable_stats["retryable"] += 1
            else:
                retryable_stats["non_retryable"] += 1

        # 计算百分比
        total_errors = len(all_errors)
        category_percentages = {}
        for category, count in category_stats.items():
            percentage = (count / total_errors * 100) if total_errors > 0 else 0
            category_percentages[category] = round(percentage, 2)

        retryable_percentages = {}
        total_retryable = retryable_stats["retryable"] + retryable_stats["non_retryable"]
        if total_retryable > 0:
            retryable_percentages["retryable"] = round(
                retryable_stats["retryable"] / total_retryable * 100, 2
            )
            retryable_percentages["non_retryable"] = round(
                retryable_stats["non_retryable"] / total_retryable * 100, 2
            )
        else:
            retryable_percentages = {"retryable": 0, "non_retryable": 0}

        # 确定修复优先级（基于频率和影响）
        repair_priority = self.calculate_repair_priority(category_stats, all_errors)

        result = {
            "analysis_time": datetime.now(timezone(timedelta(hours=8))).isoformat(),
            "total_queues_analyzed": len(queue_files),
            "total_errors_found": total_errors,
            "error_details": all_errors,
            "category_distribution": category_stats,
            "category_percentages": category_percentages,
            "retryable_distribution": retryable_stats,
            "retryable_percentages": retryable_percentages,
            "repair_priority": repair_priority,
            "recommendations": self.generate_recommendations(category_stats, retryable_stats),
        }

        return result

    def calculate_repair_priority(
        self, category_stats: dict[str, int], all_errors: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """计算修复优先级"""
        priorities = []

        # 优先级评分标准
        priority_scores = {
            "P0": {"score_range": (80, 100), "description": "立即修复，影响系统可用性"},
            "P1": {"score_range": (60, 79), "description": "高优先级，影响任务成功率"},
            "P2": {"score_range": (30, 59), "description": "中优先级，影响系统稳定性"},
            "P3": {"score_range": (0, 29), "description": "低优先级，优化项"},
        }

        total_errors = sum(category_stats.values())
        if total_errors == 0:
            return []

        # 为每个分类计算优先级分数
        for category, count in category_stats.items():
            if count == 0:
                continue

            # 基于频率的分数（0-70分）
            frequency_score = (count / total_errors) * 70

            # 基于影响严重性的分数（0-30分）
            severity_scores = {
                "timeout": 30,  # 超时影响用户体验和系统可用性
                "oom": 25,  # OOM会导致进程崩溃
                "network": 20,  # 网络错误影响分布式系统
                "config": 15,  # 配置错误需要人工干预
                "resource": 20,  # 资源错误需要扩容
                "logic": 10,  # 逻辑错误需要代码修复
                "unknown": 5,  # 未知错误需要调查
            }
            severity_score = severity_scores.get(category, 5)

            total_score = frequency_score + severity_score

            # 确定优先级级别
            priority_level = "P3"
            for level, info in priority_scores.items():
                min_score, max_score = info["score_range"]
                if min_score <= total_score <= max_score:
                    priority_level = level
                    break

            priorities.append(
                {
                    "category": category,
                    "count": count,
                    "percentage": round(count / total_errors * 100, 2),
                    "frequency_score": round(frequency_score, 2),
                    "severity_score": severity_score,
                    "total_score": round(total_score, 2),
                    "priority": priority_level,
                    "description": self.error_categories[category]["description"],
                    "repair_action": self.get_repair_action(category),
                }
            )

        # 按优先级排序
        priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        priorities.sort(key=lambda x: (priority_order[x["priority"]], -x["total_score"]))

        return priorities

    def get_repair_action(self, category: str) -> str:
        """获取修复建议"""
        actions = {
            "timeout": "1. 增加超时时间阈值\n2. 优化任务处理逻辑\n3. 实现心跳监控和自动重启\n4. 添加任务进度检查点",
            "oom": "1. 增加内存限制\n2. 优化内存使用模式\n3. 实现内存监控和预警\n4. 添加内存泄漏检测",
            "config": "1. 验证配置文件完整性\n2. 添加配置验证机制\n3. 实现配置热加载\n4. 添加配置回滚机制",
            "logic": "1. 修复业务逻辑错误\n2. 添加输入验证\n3. 实现错误边界处理\n4. 添加单元测试",
            "network": "1. 增加网络重试机制\n2. 优化连接池管理\n3. 实现网络健康检查\n4. 添加熔断器模式",
            "resource": "1. 增加资源配额\n2. 优化资源使用效率\n3. 实现资源监控\n4. 添加自动扩容机制",
            "unknown": "1. 收集详细错误日志\n2. 分析错误根因\n3. 实现错误分类\n4. 添加错误处理策略",
        }
        return actions.get(category, "需要进一步分析")

    def generate_recommendations(
        self, category_stats: dict[str, int], retryable_stats: dict[str, int]
    ) -> list[str]:
        """生成推荐修复措施"""
        recommendations = []

        total_errors = sum(category_stats.values())

        if total_errors == 0:
            recommendations.append("✅ 当前系统未发现错误，系统运行正常")
            return recommendations

        # 基于错误分类的推荐
        for category, count in category_stats.items():
            if count > 0:
                percentage = round(count / total_errors * 100, 2)
                if percentage > 50:
                    recommendations.append(
                        f"🚨 主要错误类型: {self.error_categories[category]['description']} ({percentage}%) - 需要立即重点修复"
                    )
                elif percentage > 20:
                    recommendations.append(
                        f"⚠️ 常见错误类型: {self.error_categories[category]['description']} ({percentage}%) - 需要优先处理"
                    )

        # 基于可重试性的推荐
        total_retryable = retryable_stats["retryable"] + retryable_stats["non_retryable"]
        if total_retryable > 0:
            retryable_percentage = round(retryable_stats["retryable"] / total_retryable * 100, 2)
            non_retryable_percentage = round(
                retryable_stats["non_retryable"] / total_retryable * 100, 2
            )

            recommendations.append(
                f"🔄 可重试错误: {retryable_percentage}% - 建议实现指数退避重试机制"
            )
            recommendations.append(
                f"❌ 不可重试错误: {non_retryable_percentage}% - 需要人工干预或配置修复"
            )

        # 通用推荐
        recommendations.append("📊 建议建立实时错误监控和告警系统")
        recommendations.append("🔧 建议实现错误自动分类和根因分析")
        recommendations.append("⚡ 建议添加任务降级和熔断机制")
        recommendations.append("📈 建议定期生成错误分析报告")

        return recommendations

    def generate_report(self, analysis_result: dict[str, Any]) -> str:
        """生成分析报告"""
        report_lines = []

        report_lines.append("=" * 80)
        report_lines.append("多Agent系统错误分类分析报告")
        report_lines.append("=" * 80)
        report_lines.append(f"分析时间: {analysis_result['analysis_time']}")
        report_lines.append(f"分析队列数: {analysis_result['total_queues_analyzed']}")
        report_lines.append(f"发现错误总数: {analysis_result['total_errors_found']}")
        report_lines.append("")

        # 错误分类分布
        report_lines.append("📊 错误分类分布:")
        report_lines.append("-" * 40)
        for category, count in analysis_result["category_distribution"].items():
            if count > 0:
                percentage = analysis_result["category_percentages"][category]
                report_lines.append(
                    f"  {category}: {count} ({percentage}%) - {self.error_categories[category]['description']}"
                )

        report_lines.append("")

        # 可重试性分布
        report_lines.append("🔄 错误可重试性分析:")
        report_lines.append("-" * 40)
        report_lines.append(
            f"  可重试错误: {analysis_result['retryable_distribution']['retryable']} ({analysis_result['retryable_percentages']['retryable']}%)"
        )
        report_lines.append(
            f"  不可重试错误: {analysis_result['retryable_distribution']['non_retryable']} ({analysis_result['retryable_percentages']['non_retryable']}%)"
        )

        report_lines.append("")

        # 修复优先级
        if analysis_result["repair_priority"]:
            report_lines.append("🎯 修复优先级建议:")
            report_lines.append("-" * 40)
            for item in analysis_result["repair_priority"]:
                report_lines.append(
                    f"  [{item['priority']}] {item['category']}: {item['count']} ({item['percentage']}%)"
                )
                report_lines.append(
                    f"     分数: {item['total_score']} (频率:{item['frequency_score']}, 严重性:{item['severity_score']})"
                )
                report_lines.append(f"     描述: {item['description']}")
                _repair = item["repair_action"].split("\n")[0]
                report_lines.append(f"     修复建议: {_repair}")
                report_lines.append("")

        # 详细错误信息
        if analysis_result["error_details"]:
            report_lines.append("🔍 详细错误信息:")
            report_lines.append("-" * 40)
            for error in analysis_result["error_details"]:
                report_lines.append(f"  - {error['queue_id']}/{error['item_id']}")
                report_lines.append(
                    f"    错误: {error['error'][:100]}..."
                    if len(error["error"]) > 100
                    else f"    错误: {error['error']}"
                )
                report_lines.append(f"    分类: {error['category']} | 可重试: {error['retryable']}")
                report_lines.append("")

        # 推荐措施
        report_lines.append("💡 推荐修复措施:")
        report_lines.append("-" * 40)
        for rec in analysis_result["recommendations"]:
            report_lines.append(f"  • {rec}")

        report_lines.append("")
        report_lines.append("=" * 80)
        report_lines.append("基于《多Agent系统24小时压力测试问题修复实施方案》1.2节生成")
        report_lines.append("=" * 80)

        return "\n".join(report_lines)

    def save_report(
        self, analysis_result: dict[str, Any], output_dir: str = "/Volumes/1TB-M2/openclaw/scripts"
    ):
        """保存分析报告"""
        # 生成文本报告
        text_report = self.generate_report(analysis_result)

        # 保存文本报告
        timestamp = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d_%H%M%S")
        text_report_path = os.path.join(output_dir, f"error_classification_report_{timestamp}.txt")

        with open(text_report_path, "w", encoding="utf-8") as f:
            f.write(text_report)

        # 保存JSON格式的详细结果
        json_report_path = os.path.join(
            output_dir, f"error_classification_analysis_{timestamp}.json"
        )
        with open(json_report_path, "w", encoding="utf-8") as f:
            json.dump(analysis_result, f, ensure_ascii=False, indent=2)

        print("✅ 分析报告已保存:")
        print(f"   文本报告: {text_report_path}")
        print(f"   JSON数据: {json_report_path}")

        return text_report_path, json_report_path


def main():
    """主函数"""
    print("🚀 启动多Agent系统错误分类分析器...")

    analyzer = ErrorClassificationAnalyzer()

    try:
        # 分析所有错误
        analysis_result = analyzer.analyze_all_errors()

        # 生成并保存报告
        text_report, json_report = analyzer.save_report(analysis_result)

        # 打印摘要
        print("\n📈 错误分析摘要:")
        print(f"   发现错误总数: {analysis_result['total_errors_found']}")

        if analysis_result["total_errors_found"] > 0:
            print("   错误分类分布:")
            for category, count in analysis_result["category_distribution"].items():
                if count > 0:
                    percentage = analysis_result["category_percentages"][category]
                    print(f"     - {category}: {count} ({percentage}%)")

            print("\n🎯 最高优先级修复项:")
            if analysis_result["repair_priority"]:
                top_priority = analysis_result["repair_priority"][0]
                print(
                    f"     [{top_priority['priority']}] {top_priority['category']}: {top_priority['count']} ({top_priority['percentage']}%)"
                )
                _repair_line = top_priority["repair_action"].split("\n")[0]
                print(f"     修复建议: {_repair_line}")

        print(f"\n📄 详细报告请查看: {text_report}")

    except Exception as e:
        print(f"❌ 分析过程中出现错误: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
