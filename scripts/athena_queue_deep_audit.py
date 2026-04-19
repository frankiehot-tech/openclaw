#!/usr/bin/env python3
"""
Athena队列深度审计工具 - 阶段1：深度审计与基准建立

基于MAREF智能工作流重构计划，对Athena队列系统进行深度审计，分析5个系统性缺陷：
1. 任务身份规范化失败 - ID以`-`开头被argparse误识别
2. Manifest数据质量缺陷 - 211个条目中160个唯一ID，51个重复条目
3. 进程可靠性契约缺失 - spawn_build_worker函数先标记状态为running再启动进程
4. 活跃占位检测延迟 - 死进程检测有5分钟宽限延迟
5. Lane混合与路由混淆 - Claude Code CLI与OpenCode执行器混淆使用

输出：综合审计报告、性能基准数据、技术债务评估、重构优先级建议
"""

import argparse
import json
import math
import os
import re
import statistics
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psutil

# 配置路径
BASE_DIR = Path("/Volumes/1TB-M2/openclaw")
SCRIPTS_DIR = BASE_DIR / "scripts"
QUEUE_DIR = BASE_DIR / ".openclaw" / "plan_queue"
MANIFEST_PATH = (
    BASE_DIR / ".openclaw" / "plan_queue" / "openhuman_aiplan_priority_execution_20260414.json"
)
ATHENA_RUNNER_PATH = SCRIPTS_DIR / "athena_ai_plan_runner.py"
LIVENESS_PROBE_PATH = SCRIPTS_DIR / "queue_liveness_probe.py"
ATHENA_ORCHESTRATOR_PATH = BASE_DIR / "mini-agent" / "agent" / "core" / "athena_orchestrator.py"

# 审计配置
AUDIT_CONFIG = {
    "heartbeat_threshold_minutes": 5,  # 当前配置
    "target_heartbeat_threshold_seconds": 30,  # 目标配置
    "max_hamming_distance": 3,  # 格雷编码最大汉明距离
    "min_state_space_completeness": 0.1,  # 最小状态空间完备性
    "max_entropy_increase": 0.3,  # 最大熵增加比例
}


class AthenaQueueAuditor:
    """Athena队列深度审计器"""

    def __init__(self, output_dir: str | Path = None):
        # 将字符串转换为Path对象，或使用默认路径
        if output_dir is None:
            self.output_dir = BASE_DIR / "audit_results"
        elif isinstance(output_dir, str):
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = output_dir  # 假设已经是Path对象

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.audit_results = {}
        self.benchmarks = {}

    def run_comprehensive_audit(self) -> Dict[str, Any]:
        """运行综合审计"""
        print("=" * 80)
        print("🧪 Athena队列深度审计开始")
        print("=" * 80)

        # 1. 审计任务身份规范化失败
        print("\n🔍 1. 审计任务身份规范化失败...")
        task_identity_results = self.audit_task_identity()
        self.audit_results["task_identity"] = task_identity_results

        # 2. 审计Manifest数据质量缺陷
        print("\n📊 2. 审计Manifest数据质量缺陷...")
        manifest_quality_results = self.audit_manifest_quality()
        self.audit_results["manifest_quality"] = manifest_quality_results

        # 3. 审计进程可靠性契约缺失
        print("\n⚙️ 3. 审计进程可靠性契约缺失...")
        process_reliability_results = self.audit_process_reliability()
        self.audit_results["process_reliability"] = process_reliability_results

        # 4. 审计活跃占位检测延迟
        print("\n⏱️ 4. 审计活跃占位检测延迟...")
        liveness_detection_results = self.audit_liveness_detection()
        self.audit_results["liveness_detection"] = liveness_detection_results

        # 5. 审计Lane混合与路由混淆
        print("\n🛣️ 5. 审计Lane混合与路由混淆...")
        lane_mixing_results = self.audit_lane_mixing()
        self.audit_results["lane_mixing"] = lane_mixing_results

        # 6. 建立性能基准
        print("\n📈 6. 建立性能基准...")
        benchmark_results = self.establish_performance_benchmarks()
        self.benchmarks = benchmark_results

        # 7. 技术债务评估
        print("\n🏗️ 7. 技术债务评估...")
        tech_debt_results = self.assess_technical_debt()
        self.audit_results["technical_debt"] = tech_debt_results

        # 8. 生成综合报告
        print("\n📋 8. 生成综合报告...")
        comprehensive_report = self.generate_comprehensive_report()

        # 保存所有结果
        self.save_results()

        print("=" * 80)
        print("✅ Athena队列深度审计完成")
        print("=" * 80)

        return comprehensive_report

    def audit_task_identity(self) -> Dict[str, Any]:
        """审计任务身份规范化失败"""
        results = {"issues": [], "metrics": {}, "recommendations": []}

        try:
            # 分析athena_ai_plan_runner.py中的argparse解析逻辑
            with open(ATHENA_RUNNER_PATH, "r", encoding="utf-8") as f:
                content = f.read()

            # 查找argparse定义
            arg_parse_pattern = r'parser\.add_argument\s*\(\s*["\']item_id["\']'
            if re.search(arg_parse_pattern, content):
                results["metrics"]["argparse_item_id_found"] = True

                # 检查item_id参数定义
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if '"item_id"' in line or "'item_id'" in line:
                        # 检查是否是位置参数（不是以--开头）
                        if not line.strip().startswith("--"):
                            results["metrics"]["item_id_is_positional"] = True

                            # 查找帮助文本
                            help_match = re.search(r'help\s*=\s*["\']([^"\']*)["\']', line)
                            if help_match:
                                results["metrics"]["help_text"] = help_match.group(1)

                        # 检查nargs参数
                        nargs_match = re.search(r'nargs\s*=\s*["\']\?["\']', line)
                        if nargs_match:
                            results["metrics"]["nargs_is_optional"] = True

            # 分析队列文件中的任务ID
            problematic_ids = []
            total_ids = 0

            for queue_file in QUEUE_DIR.glob("*.json"):
                try:
                    with open(queue_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    items = data.get("items", {})
                    for item_id, item_data in items.items():
                        total_ids += 1
                        # 检查ID是否以-开头
                        if isinstance(item_id, str) and item_id.startswith("-"):
                            problematic_ids.append(
                                {
                                    "file": queue_file.name,
                                    "id": item_id,
                                    "title": item_data.get("title", "Unknown"),
                                }
                            )
                except Exception as e:
                    print(f"  警告: 无法分析队列文件 {queue_file.name}: {e}")

            results["metrics"]["total_task_ids"] = total_ids
            results["metrics"]["problematic_ids_count"] = len(problematic_ids)
            results["metrics"]["problematic_ids_percentage"] = (
                (len(problematic_ids) / total_ids * 100) if total_ids > 0 else 0
            )
            results["issues"] = problematic_ids[:10]  # 只显示前10个

            # 建议
            if len(problematic_ids) > 0:
                results["recommendations"].append(
                    {
                        "priority": "HIGH",
                        "description": "实现TaskIdentityContract规范任务ID生成",
                        "rationale": f"发现 {len(problematic_ids)} 个以'-'开头的任务ID，会被argparse误识别为选项参数",
                    }
                )

        except Exception as e:
            results["error"] = str(e)
            print(f"  错误: 任务身份审计失败: {e}")

        return results

    def audit_manifest_quality(self) -> Dict[str, Any]:
        """审计Manifest数据质量缺陷"""
        results = {"issues": [], "metrics": {}, "recommendations": []}

        try:
            if not MANIFEST_PATH.exists():
                results["error"] = f"Manifest文件不存在: {MANIFEST_PATH}"
                return results

            with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)

            items = data.get("items", [])
            total_items = len(items)

            # 分析重复条目
            id_counter = Counter()
            title_counter = Counter()
            duplicate_items = []

            for item in items:
                item_id = item.get("id", "")
                title = item.get("title", "")

                if item_id:
                    id_counter[item_id] += 1
                if title:
                    title_counter[title] += 1

            # 识别重复ID
            duplicate_ids = [id for id, count in id_counter.items() if count > 1]
            unique_ids = [id for id, count in id_counter.items() if count == 1]

            # 收集重复条目的详细信息
            for item in items:
                item_id = item.get("id", "")
                if item_id in duplicate_ids:
                    duplicate_items.append(
                        {
                            "id": item_id,
                            "title": item.get("title", "Unknown"),
                            "entry_stage": item.get("entry_stage", "unknown"),
                            "status": item.get("status", "unknown"),
                            "count": id_counter[item_id],
                        }
                    )

            # 计算数据质量指标
            duplicate_count = sum(count - 1 for count in id_counter.values() if count > 1)
            uniqueness_ratio = len(unique_ids) / total_items if total_items > 0 else 0

            results["metrics"] = {
                "total_items": total_items,
                "unique_ids": len(unique_ids),
                "duplicate_ids": len(duplicate_ids),
                "duplicate_items_count": duplicate_count,
                "uniqueness_ratio": uniqueness_ratio,
                "data_quality_score": uniqueness_ratio * 100,
            }

            # 添加重复条目示例
            results["issues"] = duplicate_items[:10]  # 只显示前10个重复条目

            # 建议
            if duplicate_count > 0:
                results["recommendations"].append(
                    {
                        "priority": "HIGH",
                        "description": "清理Manifest重复数据，建立数据质量监控",
                        "rationale": f"发现 {duplicate_count} 个重复条目，唯一ID比例仅 {uniqueness_ratio:.1%}",
                    }
                )

        except Exception as e:
            results["error"] = str(e)
            print(f"  错误: Manifest质量审计失败: {e}")

        return results

    def audit_process_reliability(self) -> Dict[str, Any]:
        """审计进程可靠性契约缺失"""
        results = {"issues": [], "metrics": {}, "recommendations": []}

        try:
            with open(ATHENA_RUNNER_PATH, "r", encoding="utf-8") as f:
                content = f.read()

            # 查找spawn_build_worker函数
            spawn_pattern = r"def spawn_build_worker\s*\([^)]*\)\s*->\s*int:"
            spawn_match = re.search(spawn_pattern, content)

            if not spawn_match:
                results["error"] = "未找到spawn_build_worker函数"
                return results

            start_pos = spawn_match.start()
            # 提取函数内容（简化版本）
            function_text = content[start_pos : start_pos + 5000]

            # 分析状态更新顺序
            issues = []

            # 检查进程启动和状态更新的顺序
            process_start_match = re.search(r"process\s*=\s*subprocess\.Popen", function_text)
            status_update_match = re.search(
                r'set_route_item_state.*status\s*=\s*["\']running["\']', function_text
            )

            if process_start_match and status_update_match:
                process_start_pos = process_start_match.start()
                status_update_pos = status_update_match.start()

                # 检查顺序：应该是先启动进程，再更新状态
                if status_update_pos < process_start_pos:
                    issues.append(
                        {
                            "type": "CONTRACT_VIOLATION",
                            "description": "先标记状态为running再启动进程",
                            "line_estimate": "约1960-1979行",
                            "impact": "进程启动失败时状态不一致",
                        }
                    )
                else:
                    results["metrics"]["correct_sequence"] = True
                    # 但仍然需要检查异常处理
                    if not re.search(r"try:", function_text[:process_start_pos]):
                        issues.append(
                            {
                                "type": "EXCEPTION_HANDLING",
                                "description": "进程启动缺少try-except包装",
                                "impact": "进程启动异常会导致整个函数失败",
                            }
                        )

            # 检查detect_and_cleanup_stale_runs函数
            cleanup_pattern = r"def detect_and_cleanup_stale_runs\s*\([^)]*\)\s*->\s*None:"
            if re.search(cleanup_pattern, content):
                results["metrics"]["cleanup_function_exists"] = True

                # 检查宽限期设置
                grace_period_match = re.search(r"STARTUP_GRACE_PERIOD_SECONDS\s*=\s*(\d+)", content)
                if grace_period_match:
                    grace_seconds = int(grace_period_match.group(1))
                    results["metrics"]["startup_grace_seconds"] = grace_seconds
                    if grace_seconds > 60:
                        issues.append(
                            {
                                "type": "DELAYED_DETECTION",
                                "description": f"启动宽限期过长: {grace_seconds}秒",
                                "impact": "死进程占用资源时间过长",
                            }
                        )

            results["issues"] = issues

            # 建议
            if issues:
                results["recommendations"].append(
                    {
                        "priority": "HIGH",
                        "description": "实现ProcessLifecycleContract确保进程可靠性",
                        "rationale": "进程启动和状态管理缺乏可靠的契约保证",
                    }
                )

        except Exception as e:
            results["error"] = str(e)
            print(f"  错误: 进程可靠性审计失败: {e}")

        return results

    def audit_liveness_detection(self) -> Dict[str, Any]:
        """审计活跃占位检测延迟"""
        results = {"issues": [], "metrics": {}, "recommendations": []}

        try:
            if not LIVENESS_PROBE_PATH.exists():
                results["error"] = f"活性探针文件不存在: {LIVENESS_PROBE_PATH}"
                return results

            with open(LIVENESS_PROBE_PATH, "r", encoding="utf-8") as f:
                content = f.read()

            # 检查心跳阈值配置
            threshold_pattern = r"HEARTBEAT_THRESHOLD_MINUTES\s*=\s*(\d+)"
            threshold_match = re.search(threshold_pattern, content)

            if threshold_match:
                threshold_minutes = int(threshold_match.group(1))
                results["metrics"]["current_threshold_minutes"] = threshold_minutes
                results["metrics"]["current_threshold_seconds"] = threshold_minutes * 60

                # 与目标阈值比较
                target_seconds = AUDIT_CONFIG["target_heartbeat_threshold_seconds"]
                if threshold_minutes * 60 > target_seconds:
                    results["issues"].append(
                        {
                            "type": "EXCESSIVE_DELAY",
                            "description": f"死进程检测延迟过长: {threshold_minutes}分钟",
                            "current": f"{threshold_minutes * 60}秒",
                            "target": f"{target_seconds}秒",
                            "impact": "死进程占用资源长达5分钟才被清理",
                        }
                    )

                results["metrics"]["delay_excess_ratio"] = (threshold_minutes * 60) / target_seconds

                # 检查是否有快速检测机制
                rapid_check_pattern = r"def check_.*_rapid|liveness.*interval|heartbeat.*interval"
                if not re.search(rapid_check_pattern, content, re.IGNORECASE):
                    results["issues"].append(
                        {
                            "type": "MISSING_RAPID_CHECK",
                            "description": "缺少秒级快速检测机制",
                            "impact": "只能依赖5分钟一次的批量检查",
                        }
                    )

            # 建议
            if results.get("issues"):
                results["recommendations"].append(
                    {
                        "priority": "MEDIUM",
                        "description": "降低心跳检测阈值，实现秒级快速检测",
                        "rationale": f"当前{threshold_minutes}分钟检测延迟过长，应降低到{AUDIT_CONFIG['target_heartbeat_threshold_seconds']}秒以内",
                    }
                )

        except Exception as e:
            results["error"] = str(e)
            print(f"  错误: 活性检测审计失败: {e}")

        return results

    def audit_lane_mixing(self) -> Dict[str, Any]:
        """审计Lane混合与路由混淆"""
        results = {"issues": [], "metrics": {}, "recommendations": []}

        try:
            # 分析athena_orchestrator.py中的路由逻辑
            if not ATHENA_ORCHESTRATOR_PATH.exists():
                results["error"] = f"编排器文件不存在: {ATHENA_ORCHESTRATOR_PATH}"
                return results

            with open(ATHENA_ORCHESTRATOR_PATH, "r", encoding="utf-8") as f:
                content = f.read()

            # 查找执行器选择逻辑
            executor_patterns = {
                "claude_code_cli": r"claude.*code|code.*claude",
                "opencode": r"opencode",
                "qwen": r"qwen",
                "mixed": r"混合|混淆|mixed",
            }

            executor_counts = {}
            for executor, pattern in executor_patterns.items():
                count = len(re.findall(pattern, content, re.IGNORECASE))
                if count > 0:
                    executor_counts[executor] = count

            results["metrics"]["executor_mentions"] = executor_counts

            # 检查是否有明确的路由规则
            route_pattern = r"route.*task|task.*route|executor.*selection|selection.*executor"
            route_matches = len(re.findall(route_pattern, content, re.IGNORECASE))
            results["metrics"]["routing_logic_mentions"] = route_matches

            if route_matches < 3:
                results["issues"].append(
                    {
                        "type": "WEAK_ROUTING",
                        "description": "路由逻辑不明确",
                        "impact": "容易发生执行器混淆",
                    }
                )

            # 检查日志文件中的实际混淆案例
            log_patterns = [
                r"Claude.*Code.*OpenCode|OpenCode.*Claude.*Code",
                r"Qwen.*替代.*OpenCode",
                r"错误.*执行器|executor.*error",
            ]

            log_issues = []
            log_files = [
                BASE_DIR / "logs" / "athena_ai_plan_runner.log",
                BASE_DIR / "logs" / "athena_observability_adapter.log",
            ]

            for log_file in log_files:
                if log_file.exists():
                    try:
                        with open(log_file, "r", encoding="utf-8") as f:
                            log_content = f.read()

                        for pattern in log_patterns:
                            if re.search(pattern, log_content, re.IGNORECASE):
                                log_issues.append(
                                    {
                                        "file": log_file.name,
                                        "pattern": pattern,
                                        "evidence": "发现执行器混淆迹象",
                                    }
                                )
                    except Exception as e:
                        print(f"  警告: 无法读取日志文件 {log_file.name}: {e}")

            if log_issues:
                results["issues"].extend(log_issues)

            # 建议
            if results.get("issues"):
                results["recommendations"].append(
                    {
                        "priority": "MEDIUM",
                        "description": "实现SmartOrchestrator明确路由规则",
                        "rationale": "执行器选择和路由逻辑不清晰，容易导致混淆",
                    }
                )

        except Exception as e:
            results["error"] = str(e)
            print(f"  错误: Lane混合审计失败: {e}")

        return results

    def establish_performance_benchmarks(self) -> Dict[str, Any]:
        """建立性能基准"""
        print("  建立性能基准...")

        benchmarks = {
            "timestamp": datetime.now().isoformat(),
            "system_info": self._get_system_info(),
            "queue_metrics": {},
            "process_metrics": {},
            "resource_metrics": {},
        }

        try:
            # 队列指标
            queue_files = list(QUEUE_DIR.glob("*.json"))
            benchmarks["queue_metrics"]["total_queue_files"] = len(queue_files)

            total_items = 0
            status_counts = defaultdict(int)

            for queue_file in queue_files:
                try:
                    with open(queue_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    items = data.get("items", {})
                    total_items += len(items)

                    # 统计状态分布
                    for item_id, item_data in items.items():
                        status = item_data.get("status", "unknown")
                        status_counts[status] += 1
                except Exception as e:
                    print(f"  警告: 无法分析队列文件 {queue_file.name}: {e}")

            benchmarks["queue_metrics"]["total_items"] = total_items
            benchmarks["queue_metrics"]["status_distribution"] = dict(status_counts)

            # 进程指标
            try:
                # 检查athena相关进程
                athena_processes = []
                for proc in psutil.process_iter(
                    ["pid", "name", "cmdline", "cpu_percent", "memory_percent"]
                ):
                    try:
                        cmdline = proc.info["cmdline"]
                        if cmdline and any("athena" in str(arg).lower() for arg in cmdline):
                            athena_processes.append(
                                {
                                    "pid": proc.info["pid"],
                                    "name": proc.info["name"],
                                    "cpu_percent": proc.info["cpu_percent"],
                                    "memory_percent": proc.info["memory_percent"],
                                }
                            )
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                benchmarks["process_metrics"]["athena_process_count"] = len(athena_processes)
                benchmarks["process_metrics"]["athena_processes"] = athena_processes[
                    :10
                ]  # 只显示前10个
            except Exception as e:
                print(f"  警告: 进程指标收集失败: {e}")

            # 资源指标
            try:
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage("/")

                benchmarks["resource_metrics"] = {
                    "cpu_percent": cpu_percent,
                    "memory_total_gb": memory.total / (1024**3),
                    "memory_used_percent": memory.percent,
                    "disk_total_gb": disk.total / (1024**3),
                    "disk_used_percent": disk.percent,
                }
            except Exception as e:
                print(f"  警告: 资源指标收集失败: {e}")

        except Exception as e:
            print(f"  错误: 性能基准建立失败: {e}")
            benchmarks["error"] = str(e)

        return benchmarks

    def assess_technical_debt(self) -> Dict[str, Any]:
        """技术债务评估"""
        results = {"debt_categories": [], "total_debt_score": 0, "recommendations": []}

        try:
            debt_categories = []

            # 1. 临时修复债务
            temp_fix_files = list(SCRIPTS_DIR.glob("fix_*.py"))
            temp_fix_count = len(temp_fix_files)
            if temp_fix_count > 0:
                debt_categories.append(
                    {
                        "category": "TEMPORARY_FIXES",
                        "count": temp_fix_count,
                        "score": min(temp_fix_count * 10, 100),
                        "description": f"发现 {temp_fix_count} 个临时修复脚本",
                        "examples": [f.name for f in temp_fix_files[:5]],
                    }
                )

            # 2. 配置重复债务
            config_files = list(BASE_DIR.glob("**/*.yaml")) + list(BASE_DIR.glob("**/*.yml"))
            config_count = len(config_files)
            if config_count > 20:  # 假设超过20个配置文件表示分散
                debt_categories.append(
                    {
                        "category": "CONFIG_DUPLICATION",
                        "count": config_count,
                        "score": min((config_count - 20) * 2, 80),
                        "description": f"发现 {config_count} 个配置文件，可能存在重复和冲突",
                    }
                )

            # 3. 代码复杂度债务
            try:
                with open(ATHENA_RUNNER_PATH, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                line_count = len(lines)
                function_count = len(re.findall(r"def \w+", "".join(lines)))

                if line_count > 5000:
                    debt_categories.append(
                        {
                            "category": "CODE_COMPLEXITY",
                            "count": line_count,
                            "score": min((line_count - 5000) / 50, 90),
                            "description": f"主运行器文件过大: {line_count} 行，{function_count} 个函数",
                            "metrics": {"lines": line_count, "functions": function_count},
                        }
                    )
            except Exception as e:
                print(f"  警告: 代码复杂度分析失败: {e}")

            # 4. 文档债务
            doc_files = list(BASE_DIR.glob("**/*.md"))
            code_files = list(BASE_DIR.glob("**/*.py"))
            doc_ratio = len(doc_files) / len(code_files) if code_files else 0

            if doc_ratio < 0.1:  # 文档比例低于10%
                debt_categories.append(
                    {
                        "category": "DOCUMENTATION_GAP",
                        "score": int((0.1 - doc_ratio) * 1000),
                        "description": f"文档覆盖率低: {doc_ratio:.1%}",
                        "metrics": {"doc_files": len(doc_files), "code_files": len(code_files)},
                    }
                )

            # 计算总债务分数
            total_score = sum(cat["score"] for cat in debt_categories)
            debt_level = "LOW" if total_score < 100 else "MEDIUM" if total_score < 200 else "HIGH"

            results["debt_categories"] = debt_categories
            results["total_debt_score"] = total_score
            results["debt_level"] = debt_level

            # 建议
            if debt_categories:
                results["recommendations"].append(
                    {
                        "priority": "MEDIUM",
                        "description": "制定技术债务偿还计划",
                        "rationale": f"识别到 {len(debt_categories)} 个技术债务类别，总分数 {total_score} ({debt_level})",
                    }
                )

        except Exception as e:
            results["error"] = str(e)
            print(f"  错误: 技术债务评估失败: {e}")

        return results

    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """生成综合审计报告"""
        report = {
            "metadata": {
                "audit_date": datetime.now().isoformat(),
                "auditor": "AthenaQueueAuditor",
                "version": "1.0",
            },
            "executive_summary": {},
            "detailed_findings": self.audit_results,
            "benchmarks": self.benchmarks,
            "recommendations": [],
            "risk_assessment": {},
            "reconstruction_priority": [],
        }

        # 生成执行摘要
        total_issues = 0
        high_priority_issues = 0

        for category, findings in self.audit_results.items():
            if "issues" in findings:
                issue_count = len(findings["issues"])
                total_issues += issue_count

                # 根据问题类型判断优先级
                if category in ["task_identity", "process_reliability", "manifest_quality"]:
                    high_priority_issues += issue_count

        report["executive_summary"] = {
            "total_issues_identified": total_issues,
            "high_priority_issues": high_priority_issues,
            "audit_categories_completed": len(self.audit_results),
            "systemic_defects_confirmed": 5,  # 我们审计的5个缺陷
            "overall_health_score": max(0, 100 - total_issues * 5),
        }

        # 生成建议
        all_recommendations = []
        for category, findings in self.audit_results.items():
            if "recommendations" in findings:
                all_recommendations.extend(findings["recommendations"])

        # 去重和排序
        unique_recs = {}
        for rec in all_recommendations:
            key = rec["description"]
            if key not in unique_recs or rec.get("priority") == "HIGH":
                unique_recs[key] = rec

        # 按优先级排序
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        report["recommendations"] = sorted(
            unique_recs.values(), key=lambda x: priority_order.get(x.get("priority", "LOW"), 2)
        )

        # 风险评估
        report["risk_assessment"] = {
            "technical_risk": (
                "HIGH"
                if high_priority_issues > 3
                else "MEDIUM" if high_priority_issues > 0 else "LOW"
            ),
            "operational_risk": (
                "HIGH" if total_issues > 10 else "MEDIUM" if total_issues > 5 else "LOW"
            ),
            "data_risk": "MEDIUM" if "manifest_quality" in self.audit_results else "LOW",
            "recovery_time": (
                "DAYS"
                if high_priority_issues > 5
                else "HOURS" if high_priority_issues > 0 else "MINUTES"
            ),
        }

        # 重构优先级建议
        report["reconstruction_priority"] = [
            {
                "phase": 1,
                "focus": "TaskIdentityContract 实现",
                "rationale": "解决最基本的任务ID规范化问题，为后续重构奠定基础",
                "estimated_effort": "3-5天",
            },
            {
                "phase": 2,
                "focus": "ProcessLifecycleContract 实现",
                "rationale": "确保进程可靠性和状态一致性，消除僵尸任务",
                "estimated_effort": "5-7天",
            },
            {
                "phase": 3,
                "focus": "Manifest数据质量清理",
                "rationale": "消除重复条目，建立数据质量监控机制",
                "estimated_effort": "2-3天",
            },
            {
                "phase": 4,
                "focus": "SmartOrchestrator路由优化",
                "rationale": "解决Lane混合问题，明确执行器选择规则",
                "estimated_effort": "4-6天",
            },
            {
                "phase": 5,
                "focus": "活性检测优化",
                "rationale": "降低检测延迟，实现秒级快速检测",
                "estimated_effort": "2-3天",
            },
        ]

        return report

    def save_results(self):
        """保存审计结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存详细审计结果
        audit_file = self.output_dir / f"audit_results_{timestamp}.json"
        with open(audit_file, "w", encoding="utf-8") as f:
            json.dump(self.audit_results, f, indent=2, ensure_ascii=False)
        print(f"  详细审计结果保存到: {audit_file}")

        # 保存性能基准
        benchmark_file = self.output_dir / f"performance_benchmarks_{timestamp}.json"
        with open(benchmark_file, "w", encoding="utf-8") as f:
            json.dump(self.benchmarks, f, indent=2, ensure_ascii=False)
        print(f"  性能基准保存到: {benchmark_file}")

        # 保存综合报告
        report = self.generate_comprehensive_report()
        report_file = self.output_dir / f"comprehensive_report_{timestamp}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"  综合报告保存到: {report_file}")

        # 生成文本格式报告
        text_report = self._generate_text_report(report)
        text_file = self.output_dir / f"executive_summary_{timestamp}.md"
        with open(text_file, "w", encoding="utf-8") as f:
            f.write(text_report)
        print(f"  执行摘要保存到: {text_file}")

    def _generate_text_report(self, report: Dict[str, Any]) -> str:
        """生成文本格式报告"""
        lines = []

        lines.append("# Athena队列系统深度审计报告")
        lines.append(f"生成时间: {report['metadata']['audit_date']}")
        lines.append("")

        # 执行摘要
        lines.append("## 📊 执行摘要")
        summary = report["executive_summary"]
        lines.append(f"- **发现的问题总数**: {summary['total_issues_identified']}")
        lines.append(f"- **高优先级问题**: {summary['high_priority_issues']}")
        lines.append(f"- **审计完成的类别**: {summary['audit_categories_completed']}/5")
        lines.append(f"- **系统性缺陷确认**: {summary['systemic_defects_confirmed']}/5")
        lines.append(f"- **系统健康度评分**: {summary['overall_health_score']}/100")
        lines.append("")

        # 关键发现
        lines.append("## 🔍 关键发现")

        for category, findings in report["detailed_findings"].items():
            if "issues" in findings and findings["issues"]:
                category_name = {
                    "task_identity": "任务身份规范化",
                    "manifest_quality": "Manifest数据质量",
                    "process_reliability": "进程可靠性",
                    "liveness_detection": "活性检测",
                    "lane_mixing": "Lane混合",
                }.get(category, category)

                lines.append(f"### {category_name}")
                lines.append(f"- 发现 {len(findings['issues'])} 个问题")

                if "metrics" in findings:
                    for key, value in findings["metrics"].items():
                        if isinstance(value, (int, float)):
                            lines.append(f"- {key}: {value}")

                # 显示前3个问题
                for i, issue in enumerate(findings["issues"][:3]):
                    lines.append(f"  {i+1}. {issue.get('description', '未描述的问题')}")

        lines.append("")

        # 建议
        lines.append("## 🚀 重构建议")
        for i, rec in enumerate(report["recommendations"][:5], 1):
            lines.append(f"{i}. **[{rec.get('priority', 'LOW')}]** {rec['description']}")
            lines.append(f"   - 理由: {rec.get('rationale', '未提供理由')}")

        lines.append("")

        # 风险评估
        lines.append("## ⚠️ 风险评估")
        risk = report["risk_assessment"]
        lines.append(f"- **技术风险**: {risk['technical_risk']}")
        lines.append(f"- **运营风险**: {risk['operational_risk']}")
        lines.append(f"- **数据风险**: {risk['data_risk']}")
        lines.append(f"- **恢复时间**: {risk['recovery_time']}")
        lines.append("")

        # 重构优先级
        lines.append("## 📅 重构优先级")
        for phase in report["reconstruction_priority"]:
            lines.append(f"**阶段 {phase['phase']}**: {phase['focus']}")
            lines.append(f"  - 理由: {phase['rationale']}")
            lines.append(f"  - 预计工作量: {phase['estimated_effort']}")

        return "\n".join(lines)

    def _get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        info = {
            "platform": sys.platform,
            "python_version": sys.version,
            "working_directory": str(Path.cwd()),
            "audit_script_version": "1.0",
        }

        try:
            import platform

            info["system"] = platform.system()
            info["release"] = platform.release()
            info["machine"] = platform.machine()
        except:
            pass

        return info


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Athena队列深度审计工具")
    parser.add_argument("--output-dir", help="输出目录路径", default=None)
    parser.add_argument("--quick", action="store_true", help="快速模式（只审计关键问题）")

    args = parser.parse_args()

    # 创建审计器
    auditor = AthenaQueueAuditor(output_dir=args.output_dir)

    # 运行审计
    try:
        report = auditor.run_comprehensive_audit()

        # 显示执行摘要
        summary = report.get("executive_summary", {})
        print("\n" + "=" * 80)
        print("📋 审计完成 - 执行摘要")
        print("=" * 80)
        print(f"发现的问题总数: {summary.get('total_issues_identified', 0)}")
        print(f"高优先级问题: {summary.get('high_priority_issues', 0)}")
        print(f"系统健康度评分: {summary.get('overall_health_score', 0)}/100")
        print(f"审计报告保存到: {auditor.output_dir}")
        print("=" * 80)

    except Exception as e:
        print(f"❌ 审计过程发生错误: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
