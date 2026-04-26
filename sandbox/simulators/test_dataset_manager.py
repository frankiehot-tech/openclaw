#!/usr/bin/env python3
"""
MAREF沙箱测试数据集管理器

生成多样化的测试任务集合，用于验证基线系统和增强系统的性能。
支持任务类型分布、代码复杂度控制、质量问题注入等功能。
"""

import random
import json
import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class TaskType(Enum):
    """任务类型枚举"""

    ALGORITHM = "algorithm"  # 算法任务
    DATA_PROCESSING = "data_processing"  # 数据处理
    UTILITY = "utility"  # 工具函数
    QUALITY_TEST = "quality_test"  # 质量测试（包含已知问题）
    STRESS_TEST = "stress_test"  # 压力测试（高复杂度）


class ComplexityLevel(Enum):
    """代码复杂度等级"""

    SIMPLE = "simple"  # 简单（10-50行）
    MEDIUM = "medium"  # 中等（50-200行）
    COMPLEX = "complex"  # 复杂（200-500行）


class QualityIssue(Enum):
    """代码质量问题类型"""

    SYNTAX_ERROR = "syntax_error"  # 语法错误
    LOGIC_ERROR = "logic_error"  # 逻辑错误
    PERFORMANCE_ISSUE = "performance_issue"  # 性能问题
    STYLE_VIOLATION = "style_violation"  # 风格违规
    SECURITY_VULNERABILITY = "security_vulnerability"  # 安全漏洞
    CODE_SMELL = "code_smell"  # 代码异味


class TestDatasetManager:
    """测试数据集管理器"""

    def __init__(self, output_dir: str = "./test_datasets"):
        """
        初始化测试数据集管理器

        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # 默认配置
        self.default_config = {
            # 任务类型分布
            "task_type_distribution": {
                "algorithm": 0.30,  # 30%
                "data_processing": 0.25,  # 25%
                "utility": 0.20,  # 20%
                "quality_test": 0.15,  # 15%
                "stress_test": 0.10,  # 10%
            },
            # 代码复杂度分布
            "complexity_distribution": {
                "simple": 0.40,  # 40%
                "medium": 0.40,  # 40%
                "complex": 0.20,  # 20%
            },
            # 代码行数范围（按复杂度）
            "code_lines_ranges": {
                "simple": (10, 50),
                "medium": (50, 200),
                "complex": (200, 500),
            },
            # 质量问题注入配置
            "quality_issues_config": {
                "syntax_error": {
                    "probability": 0.10,  # 10%的概率包含语法错误
                    "severity": "high",
                },
                "logic_error": {
                    "probability": 0.15,
                    "severity": "medium",
                },
                "performance_issue": {
                    "probability": 0.20,
                    "severity": "medium",
                },
                "style_violation": {
                    "probability": 0.30,
                    "severity": "low",
                },
                "security_vulnerability": {
                    "probability": 0.05,
                    "severity": "high",
                },
                "code_smell": {
                    "probability": 0.25,
                    "severity": "low",
                },
            },
            # 模板库
            "templates": {
                "algorithm": [
                    # 排序算法
                    "def bubble_sort(arr):\n    n = len(arr)\n    for i in range(n):\n        for j in range(0, n - i - 1):\n            if arr[j] > arr[j + 1]:\n                arr[j], arr[j + 1] = arr[j + 1], arr[j]\n    return arr",
                    "def quick_sort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr) // 2]\n    left = [x for x in arr if x < pivot]\n    middle = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quick_sort(left) + middle + quick_sort(right)",
                    "def merge_sort(arr):\n    if len(arr) <= 1:\n        return arr\n    mid = len(arr) // 2\n    left = merge_sort(arr[:mid])\n    right = merge_sort(arr[mid:])\n    return merge(left, right)\n\ndef merge(left, right):\n    result = []\n    i = j = 0\n    while i < len(left) and j < len(right):\n        if left[i] < right[j]:\n            result.append(left[i])\n            i += 1\n        else:\n            result.append(right[j])\n            j += 1\n    result.extend(left[i:])\n    result.extend(right[j:])\n    return result",
                    # 搜索算法
                    "def binary_search(arr, target):\n    low, high = 0, len(arr) - 1\n    while low <= high:\n        mid = (low + high) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            low = mid + 1\n        else:\n            high = mid - 1\n    return -1",
                    "def linear_search(arr, target):\n    for i, item in enumerate(arr):\n        if item == target:\n            return i\n    return -1",
                    # 数学算法
                    "def fibonacci(n):\n    if n <= 1:\n        return n\n    a, b = 0, 1\n    for i in range(2, n + 1):\n        a, b = b, a + b\n    return b",
                    "def factorial(n):\n    if n <= 1:\n        return 1\n    result = 1\n    for i in range(2, n + 1):\n        result *= i\n    return result",
                    "def is_prime(n):\n    if n <= 1:\n        return False\n    for i in range(2, int(n**0.5) + 1):\n        if n % i == 0:\n            return False\n    return True",
                ],
                "data_processing": [
                    # 数据清洗
                    "def clean_data(data):\n    cleaned = []\n    for item in data:\n        if isinstance(item, (int, float)):\n            cleaned.append(float(item))\n        elif isinstance(item, str):\n            try:\n                cleaned.append(float(item))\n            except ValueError:\n                pass\n    return cleaned",
                    "def normalize_data(data):\n    if not data:\n        return []\n    min_val = min(data)\n    max_val = max(data)\n    if min_val == max_val:\n        return [0.5 for _ in data]\n    return [(x - min_val) / (max_val - min_val) for x in data]",
                    # 统计分析
                    "def calculate_statistics(data):\n    if not data:\n        return {}\n    mean = sum(data) / len(data)\n    sorted_data = sorted(data)\n    median = sorted_data[len(sorted_data) // 2] if len(sorted_data) % 2 == 1 else \\\n             (sorted_data[len(sorted_data) // 2 - 1] + sorted_data[len(sorted_data) // 2]) / 2\n    variance = sum((x - mean) ** 2 for x in data) / len(data)\n    std_dev = variance ** 0.5\n    return {\n        'mean': mean,\n        'median': median,\n        'variance': variance,\n        'std_dev': std_dev,\n        'min': min(data),\n        'max': max(data),\n        'count': len(data)\n    }",
                    # 数据可视化（模拟）
                    "def generate_histogram(data, bins=10):\n    if not data:\n        return []\n    min_val = min(data)\n    max_val = max(data)\n    bin_width = (max_val - min_val) / bins\n    histogram = [0] * bins\n    for value in data:\n        if value == max_val:\n            bin_index = bins - 1\n        else:\n            bin_index = int((value - min_val) / bin_width)\n        if 0 <= bin_index < bins:\n            histogram[bin_index] += 1\n    return histogram",
                ],
                "utility": [
                    # 字符串处理
                    "def reverse_string(s):\n    return s[::-1]",
                    "def count_words(text):\n    words = text.split()\n    word_count = {}\n    for word in words:\n        word = word.lower().strip('.,!?;:')\n        if word:\n            word_count[word] = word_count.get(word, 0) + 1\n    return word_count",
                    "def find_longest_word(text):\n    words = text.split()\n    if not words:\n        return ''\n    return max(words, key=len)",
                    # 文件操作
                    "def read_file_lines(filepath):\n    lines = []\n    try:\n        with open(filepath, 'r', encoding='utf-8') as f:\n            for line in f:\n                lines.append(line.strip())\n    except FileNotFoundError:\n        pass\n    return lines",
                    "def write_file_lines(filepath, lines):\n    try:\n        with open(filepath, 'w', encoding='utf-8') as f:\n            for line in lines:\n                f.write(line + '\\n')\n        return True\n    except Exception:\n        return False",
                    # 日期时间处理
                    "def format_timestamp(timestamp, fmt='%Y-%m-%d %H:%M:%S'):\n    from datetime import datetime\n    return datetime.fromtimestamp(timestamp).strftime(fmt)",
                    "def parse_date(date_str, fmt='%Y-%m-%d'):\n    from datetime import datetime\n    try:\n        return datetime.strptime(date_str, fmt)\n    except ValueError:\n        return None",
                ],
                "quality_test": [
                    # 已知质量问题的代码模板
                    "def buggy_factorial(n):  # 逻辑错误：没有处理负数\n    result = 1\n    for i in range(2, n + 1):\n        result *= i\n    return result",
                    "def inefficient_fibonacci(n):  # 性能问题：指数级复杂度\n    if n <= 1:\n        return n\n    return inefficient_fibonacci(n - 1) + inefficient_fibonacci(n - 2)",
                    "def unsafe_password_check(password):  # 安全漏洞：简单的字符串比较\n    return password == 'admin123'",
                    "def confusing_function(x, y, z):  # 代码异味：过于复杂\n    if x > 0 and y < 10 or z == 'foo' and not (x < 5 and y > 2) or (x == y and z != 'bar'):\n        return True\n    else:\n        return False",
                    "def poorly_formatted(): # 风格违规：缺少空格，行过长\n    x=1;y=2;z=x+y;print(f'The sum of {x} and {y} is {z} but we should also check if it's even or odd or prime or something else')\n    return z",
                ],
                "stress_test": [
                    # 高计算复杂度任务
                    "def matrix_multiplication(a, b):\n    n = len(a)\n    result = [[0] * n for _ in range(n)]\n    for i in range(n):\n        for j in range(n):\n            for k in range(n):\n                result[i][j] += a[i][k] * b[k][j]\n    return result",
                    "def prime_sieve(limit):\n    sieve = [True] * (limit + 1)\n    sieve[0:2] = [False, False]\n    for i in range(2, int(limit**0.5) + 1):\n        if sieve[i]:\n            for j in range(i*i, limit + 1, i):\n                sieve[j] = False\n    return [i for i, is_prime in enumerate(sieve) if is_prime]",
                    "def recursive_tree_traversal(node):\n    if node is None:\n        return []\n    result = [node.value]\n    result.extend(recursive_tree_traversal(node.left))\n    result.extend(recursive_tree_traversal(node.right))\n    return result",
                ],
            },
        }

    def generate_dataset(
        self, size: int = 1000, config: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        生成测试数据集

        Args:
            size: 数据集大小（任务数量）
            config: 自定义配置（覆盖默认配置）

        Returns:
            测试任务列表
        """
        # 合并配置
        current_config = self.default_config.copy()
        if config:
            self._merge_configs(current_config, config)

        dataset = []
        task_types = list(current_config["task_type_distribution"].keys())
        task_probs = list(current_config["task_type_distribution"].values())

        for task_id in range(size):
            # 随机选择任务类型
            task_type = random.choices(task_types, weights=task_probs)[0]

            # 随机选择复杂度
            complexity_levels = list(current_config["complexity_distribution"].keys())
            complexity_probs = list(current_config["complexity_distribution"].values())
            complexity = random.choices(complexity_levels, weights=complexity_probs)[0]

            # 生成代码
            code = self._generate_code_sample(task_type, complexity, current_config)

            # 记录质量问题
            quality_issues = self._inject_quality_issues(
                code, task_type, current_config
            )

            # 创建任务记录
            task_record = {
                "task_id": f"test_{task_id:06d}",
                "task_type": task_type,
                "complexity": complexity,
                "code": code,
                "code_lines": len(code.split("\n")),
                "quality_issues": quality_issues,
                "generated_at": datetime.now().isoformat(),
                "metadata": {
                    "task_type_distribution": current_config["task_type_distribution"],
                    "complexity_distribution": current_config[
                        "complexity_distribution"
                    ],
                },
            }

            dataset.append(task_record)

        return dataset

    def _generate_code_sample(
        self, task_type: str, complexity: str, config: Dict[str, Any]
    ) -> str:
        """
        生成单个代码样本

        Args:
            task_type: 任务类型
            complexity: 复杂度等级
            config: 配置字典

        Returns:
            代码字符串
        """
        # 选择模板
        templates = config["templates"].get(task_type, [])
        if not templates:
            # 如果没有模板，生成简单占位符
            return f"def placeholder_{task_type}():\n    # This is a placeholder for {task_type} task\n    return None"

        template = random.choice(templates)

        # 根据复杂度调整代码
        min_lines, max_lines = config["code_lines_ranges"][complexity]
        current_lines = len(template.split("\n"))

        if current_lines < min_lines:
            # 扩展代码
            lines = template.split("\n")
            while len(lines) < min_lines:
                # 添加更多注释或简单语句
                if random.random() < 0.7:
                    comment_line = f"    # Additional code for complexity: {complexity}"
                    lines.append(comment_line)
                else:
                    var_name = f"temp_var_{len(lines)}"
                    lines.append(f"    {var_name} = {random.randint(1, 100)}")

            template = "\n".join(lines)

        elif current_lines > max_lines and max_lines > 10:
            # 截断代码（保留重要部分）
            lines = template.split("\n")
            if len(lines) > max_lines:
                # 保留函数定义和前几行
                important_lines = lines[:max_lines]
                important_lines.append("    # ... truncated for complexity control")
                template = "\n".join(important_lines)

        return template

    def _inject_quality_issues(
        self, code: str, task_type: str, config: Dict[str, Any]
    ) -> List[str]:
        """
        向代码中注入质量问题

        Args:
            code: 原始代码
            task_type: 任务类型
            config: 配置字典

        Returns:
            注入的质量问题列表
        """
        issues_config = config["quality_issues_config"]
        injected_issues = []

        # 对于质量测试任务，注入更多问题
        multiplier = 2.0 if task_type == "quality_test" else 1.0

        for issue_type, issue_config in issues_config.items():
            probability = issue_config["probability"] * multiplier
            if random.random() < probability:
                injected_issues.append(issue_type)

                # 实际注入问题（这里简化处理，只记录问题类型）
                # 在实际应用中，这里会修改代码以包含相应问题

        return injected_issues

    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """递归合并配置字典"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_configs(base[key], value)
            else:
                base[key] = value

    def save_dataset(
        self, dataset: List[Dict[str, Any]], name: str = "test_dataset"
    ) -> str:
        """
        保存数据集到文件

        Args:
            dataset: 数据集列表
            name: 数据集名称

        Returns:
            保存的文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)

        # 计算统计数据
        stats = self._calculate_dataset_stats(dataset)

        data_to_save = {
            "metadata": {
                "name": name,
                "generated_at": datetime.now().isoformat(),
                "size": len(dataset),
                "stats": stats,
            },
            "dataset": dataset,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=2, ensure_ascii=False)

        print(f"✅ 数据集已保存: {filepath}")
        print(f"   任务数量: {len(dataset)}")
        print(f"   任务类型分布: {stats['task_type_distribution']}")
        print(f"   复杂度分布: {stats['complexity_distribution']}")
        print(f"   质量问题统计: {stats['quality_issues_summary']}")

        return filepath

    def _calculate_dataset_stats(self, dataset: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算数据集统计信息"""
        task_type_counts = {}
        complexity_counts = {}
        quality_issue_counts = {}
        total_lines = 0

        for task in dataset:
            # 任务类型统计
            task_type = task.get("task_type", "unknown")
            task_type_counts[task_type] = task_type_counts.get(task_type, 0) + 1

            # 复杂度统计
            complexity = task.get("complexity", "unknown")
            complexity_counts[complexity] = complexity_counts.get(complexity, 0) + 1

            # 代码行数统计
            code_lines = task.get("code_lines", 0)
            total_lines += code_lines

            # 质量问题统计
            issues = task.get("quality_issues", [])
            for issue in issues:
                quality_issue_counts[issue] = quality_issue_counts.get(issue, 0) + 1

        # 计算百分比
        total_tasks = len(dataset)
        task_type_distribution = {
            k: round(v / total_tasks * 100, 1) for k, v in task_type_counts.items()
        }
        complexity_distribution = {
            k: round(v / total_tasks * 100, 1) for k, v in complexity_counts.items()
        }

        # 平均质量问题数
        total_issues = sum(quality_issue_counts.values())
        avg_issues_per_task = total_issues / total_tasks if total_tasks > 0 else 0

        return {
            "task_type_distribution": task_type_distribution,
            "complexity_distribution": complexity_distribution,
            "quality_issues_summary": {
                "total_issues": total_issues,
                "avg_issues_per_task": round(avg_issues_per_task, 2),
                "issue_type_counts": quality_issue_counts,
            },
            "code_size_stats": {
                "total_lines": total_lines,
                "avg_lines_per_task": (
                    round(total_lines / total_tasks, 1) if total_tasks > 0 else 0
                ),
            },
        }

    def load_dataset(
        self, filepath: str
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        从文件加载数据集

        Args:
            filepath: 数据集文件路径

        Returns:
            (数据集列表, 元数据)
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        dataset = data.get("dataset", [])
        metadata = data.get("metadata", {})

        print(f"📂 数据集已加载: {filepath}")
        print(f"   任务数量: {len(dataset)}")
        print(f"   生成时间: {metadata.get('generated_at', 'unknown')}")

        return dataset, metadata

    def generate_sample_config(self) -> Dict[str, Any]:
        """生成示例配置"""
        return self.default_config.copy()


def main():
    """主函数：生成测试数据集"""
    import argparse

    parser = argparse.ArgumentParser(description="MAREF沙箱测试数据集生成器")
    parser.add_argument(
        "--size", "-s", type=int, default=100, help="数据集大小（任务数量）"
    )
    parser.add_argument(
        "--output-dir", "-o", default="./test_datasets", help="输出目录"
    )
    parser.add_argument("--name", "-n", default="test_dataset", help="数据集名称")
    parser.add_argument("--config", "-c", help="配置文件路径（JSON格式）")
    parser.add_argument("--list-config", action="store_true", help="显示默认配置")

    args = parser.parse_args()

    if args.list_config:
        manager = TestDatasetManager()
        config = manager.generate_sample_config()
        print(json.dumps(config, indent=2, ensure_ascii=False))
        return

    # 加载自定义配置
    user_config = None
    if args.config and os.path.exists(args.config):
        with open(args.config, "r") as f:
            user_config = json.load(f)

    # 生成数据集
    manager = TestDatasetManager(args.output_dir)
    dataset = manager.generate_dataset(args.size, user_config)

    # 保存数据集
    filepath = manager.save_dataset(dataset, args.name)

    print(f"\n🎉 测试数据集生成完成！")
    print(f"   文件路径: {filepath}")
    print(f"   数据集大小: {args.size} 个任务")


if __name__ == "__main__":
    main()
