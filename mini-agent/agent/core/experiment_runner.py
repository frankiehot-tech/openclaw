#!/usr/bin/env python3
"""
实验运行器 - 自动化运行实验收集样本数据

基于阶段4A计划，自动化收集100+实验样本，用于：
1. 成本节省统计显著性分析
2. 代码质量对比评估
3. 迁移决策支持

功能：
1. 加载代表性测试用例库
2. 模拟实验分配和任务执行
3. 记录完整的实验数据（分配、执行、成本、质量）
4. 确保样本分布平衡
5. 支持批量运行和进度跟踪
"""

import asyncio
import json
import logging
import os
import random
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 导入请求ID生成器
from .request_id_generator import (
    generate_experiment_request_id,
    get_request_id_generator,
)

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 导入项目模块
try:
    from agent.core.cost_tracker import CostRecord
    from agent.core.cost_tracker_integration import CostTrackingIntegration
    from agent.core.experiment_logger import ExperimentLogger, get_experiment_logger
    from agent.core.experiment_router import ExperimentRouter, get_experiment_router
except ImportError as e:
    logger.error(f"导入依赖模块失败: {e}")
    sys.exit(1)


# ==================== 测试用例定义 ====================


@dataclass
class TestCase:
    """测试用例"""

    id: str  # 测试用例ID
    task_kind: str  # 任务类型
    name: str  # 用例名称
    description: str  # 用例描述
    prompt: str  # 输入prompt
    expected_output: str  # 期望输出（用于质量评估）
    difficulty: str  # 难度等级：easy/medium/hard
    tags: List[str]  # 标签（如：python, algorithm, refactoring）

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "task_kind": self.task_kind,
            "name": self.name,
            "description": self.description,
            "prompt": self.prompt,
            "expected_output": self.expected_output,
            "difficulty": self.difficulty,
            "tags": self.tags,
        }


class TestCaseLibrary:
    """测试用例库"""

    def __init__(self):
        self.test_cases: List[TestCase] = []
        self._load_default_test_cases()

    def _load_default_test_cases(self):
        """加载默认测试用例（10个代表性coding_plan任务）"""
        # 用例1: 简单函数 - 计算阶乘
        self.test_cases.append(
            TestCase(
                id="tc_001",
                task_kind="coding_plan",
                name="计算阶乘函数",
                description="编写一个Python函数计算给定整数的阶乘",
                prompt="编写一个Python函数计算给定整数的阶乘。函数名应为factorial，接受一个整数参数n，返回n的阶乘。需要考虑边界情况：n小于0时返回None，n等于0时返回1。",
                expected_output="def factorial(n):\n    if n < 0:\n        return None\n    if n == 0:\n        return 1\n    result = 1\n    for i in range(1, n + 1):\n        result *= i\n    return result",
                difficulty="easy",
                tags=["python", "function", "algorithm", "factorial"],
            )
        )

        # 用例2: 列表操作 - 去重并排序
        self.test_cases.append(
            TestCase(
                id="tc_002",
                task_kind="coding_plan",
                name="列表去重排序",
                description="编写一个函数对列表进行去重和排序",
                prompt="编写一个Python函数remove_duplicates_and_sort，接受一个列表作为参数，返回去重后按升序排序的新列表。不能使用内置的set()函数。",
                expected_output="def remove_duplicates_and_sort(lst):\n    # 去重\n    unique_lst = []\n    for item in lst:\n        if item not in unique_lst:\n            unique_lst.append(item)\n    # 排序（使用冒泡排序）\n    n = len(unique_lst)\n    for i in range(n):\n        for j in range(0, n - i - 1):\n            if unique_lst[j] > unique_lst[j + 1]:\n                unique_lst[j], unique_lst[j + 1] = unique_lst[j + 1], unique_lst[j]\n    return unique_lst",
                difficulty="medium",
                tags=["python", "list", "algorithm", "sorting"],
            )
        )

        # 用例3: 文件操作 - 读取CSV并计算统计
        self.test_cases.append(
            TestCase(
                id="tc_003",
                task_kind="coding_plan",
                name="CSV文件统计",
                description="编写一个函数读取CSV文件并计算基本统计信息",
                prompt="编写一个Python函数analyze_csv，接受CSV文件路径作为参数，返回包含以下统计信息的字典：行数、列数、每列的平均值（如果是数值列）。假设CSV文件第一行是表头。",
                expected_output="import csv\nimport statistics\n\ndef analyze_csv(file_path):\n    try:\n        with open(file_path, 'r', encoding='utf-8') as f:\n            reader = csv.reader(f)\n            rows = list(reader)\n            \n        if not rows:\n            return {'error': 'Empty file'}\n            \n        header = rows[0]\n        data_rows = rows[1:]\n        \n        # 初始化结果\n        result = {\n            'row_count': len(data_rows),\n            'column_count': len(header),\n            'columns': {}\n        }\n        \n        # 分析每列\n        for col_idx, col_name in enumerate(header):\n            column_values = []\n            for row in data_rows:\n                if col_idx < len(row):\n                    try:\n                        value = float(row[col_idx])\n                        column_values.append(value)\n                    except ValueError:\n                        pass\n            \n            if column_values:\n                result['columns'][col_name] = {\n                    'count': len(column_values),\n                    'mean': statistics.mean(column_values),\n                    'min': min(column_values),\n                    'max': max(column_values)\n                }\n            \n        return result\n        \n    except Exception as e:\n        return {'error': str(e)}",
                difficulty="hard",
                tags=["python", "file", "csv", "statistics"],
            )
        )

        # 用例4: 字符串处理 - 反转字符串中的单词
        self.test_cases.append(
            TestCase(
                id="tc_004",
                task_kind="coding_plan",
                name="反转字符串中的单词",
                description="编写一个函数反转字符串中每个单词的顺序",
                prompt="编写一个Python函数reverse_words，接受一个字符串作为参数，返回一个新字符串，其中每个单词都被反转，但单词顺序保持不变。单词由空格分隔。例如：'hello world' -> 'olleh dlrow'。",
                expected_output="def reverse_words(s):\n    words = s.split(' ')\n    reversed_words = [word[::-1] for word in words]\n    return ' '.join(reversed_words)",
                difficulty="easy",
                tags=["python", "string", "algorithm"],
            )
        )

        # 用例5: 数据结构 - 实现栈
        self.test_cases.append(
            TestCase(
                id="tc_005",
                task_kind="coding_plan",
                name="实现栈数据结构",
                description="使用Python类实现栈数据结构",
                prompt="使用Python类实现一个栈（Stack）数据结构，包含以下方法：push(item) - 压入元素，pop() - 弹出并返回栈顶元素，peek() - 返回栈顶元素但不弹出，is_empty() - 检查栈是否为空，size() - 返回栈中元素数量。",
                expected_output="class Stack:\n    def __init__(self):\n        self.items = []\n    \n    def push(self, item):\n        self.items.append(item)\n    \n    def pop(self):\n        if not self.is_empty():\n            return self.items.pop()\n        else:\n            raise IndexError('pop from empty stack')\n    \n    def peek(self):\n        if not self.is_empty():\n            return self.items[-1]\n        else:\n            raise IndexError('peek from empty stack')\n    \n    def is_empty(self):\n        return len(self.items) == 0\n    \n    def size(self):\n        return len(self.items)",
                difficulty="medium",
                tags=["python", "data-structure", "stack", "class"],
            )
        )

        # 用例6: 算法 - 二分查找
        self.test_cases.append(
            TestCase(
                id="tc_006",
                task_kind="coding_plan",
                name="二分查找算法",
                description="实现二分查找算法",
                prompt="编写一个Python函数binary_search，接受一个已排序的列表和一个目标值作为参数，返回目标值在列表中的索引（如果存在），否则返回-1。使用迭代方式实现。",
                expected_output="def binary_search(sorted_list, target):\n    left, right = 0, len(sorted_list) - 1\n    \n    while left <= right:\n        mid = (left + right) // 2\n        if sorted_list[mid] == target:\n            return mid\n        elif sorted_list[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    \n    return -1",
                difficulty="medium",
                tags=["python", "algorithm", "search", "binary-search"],
            )
        )

        # 用例7: 网络请求 - 获取API数据
        self.test_cases.append(
            TestCase(
                id="tc_007",
                task_kind="coding_plan",
                name="HTTP GET请求封装",
                description="编写一个函数执行HTTP GET请求并处理响应",
                prompt="编写一个Python函数fetch_url，接受一个URL字符串作为参数，使用requests库执行GET请求，返回响应内容。需要添加超时处理和错误处理。如果请求失败，返回错误信息字典。",
                expected_output="import requests\n\ndef fetch_url(url, timeout=10):\n    try:\n        response = requests.get(url, timeout=timeout)\n        response.raise_for_status()  # 检查HTTP错误\n        return {\n            'status_code': response.status_code,\n            'content': response.text,\n            'headers': dict(response.headers),\n            'success': True\n        }\n    except requests.exceptions.Timeout:\n        return {'error': 'Request timeout', 'success': False}\n    except requests.exceptions.RequestException as e:\n        return {'error': str(e), 'success': False}",
                difficulty="medium",
                tags=["python", "network", "http", "api"],
            )
        )

        # 用例8: 日期时间处理 - 计算工作日
        self.test_cases.append(
            TestCase(
                id="tc_008",
                task_kind="coding_plan",
                name="计算两个日期之间的工作日数",
                description="编写一个函数计算两个日期之间的工作日数（排除周末）",
                prompt="编写一个Python函数count_weekdays，接受两个日期字符串（格式：YYYY-MM-DD）作为参数，返回这两个日期之间的工作日数（周一至周五）。使用datetime模块。",
                expected_output="from datetime import datetime, timedelta\n\ndef count_weekdays(start_date_str, end_date_str):\n    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')\n    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')\n    \n    if start_date > end_date:\n        start_date, end_date = end_date, start_date\n    \n    weekdays = 0\n    current_date = start_date\n    \n    while current_date <= end_date:\n        # 周一至周五是工作日（0=周一，4=周五）\n        if current_date.weekday() < 5:\n            weekdays += 1\n        current_date += timedelta(days=1)\n    \n    return weekdays",
                difficulty="medium",
                tags=["python", "datetime", "business-logic"],
            )
        )

        # 用例9: 正则表达式 - 提取邮箱地址
        self.test_cases.append(
            TestCase(
                id="tc_009",
                task_kind="coding_plan",
                name="使用正则表达式提取邮箱地址",
                description="编写一个函数从文本中提取所有邮箱地址",
                prompt="编写一个Python函数extract_emails，接受一个字符串作为参数，使用正则表达式提取所有有效的邮箱地址，返回邮箱地址列表。邮箱地址格式应为：local-part@domain。",
                expected_output="import re\n\ndef extract_emails(text):\n    # 简单的邮箱正则表达式\n    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}'\n    emails = re.findall(email_pattern, text)\n    return emails",
                difficulty="easy",
                tags=["python", "regex", "text-processing"],
            )
        )

        # 用例10: 递归算法 - 计算斐波那契数列
        self.test_cases.append(
            TestCase(
                id="tc_010",
                task_kind="coding_plan",
                name="递归计算斐波那契数列",
                description="使用递归实现斐波那契数列计算",
                prompt="编写一个Python函数fibonacci，接受一个整数n作为参数，使用递归计算第n个斐波那契数。斐波那契数列定义：F(0)=0, F(1)=1, F(n)=F(n-1)+F(n-2) for n>1。",
                expected_output="def fibonacci(n):\n    if n < 0:\n        return None\n    if n == 0:\n        return 0\n    if n == 1:\n        return 1\n    return fibonacci(n-1) + fibonacci(n-2)",
                difficulty="easy",
                tags=["python", "recursion", "algorithm", "fibonacci"],
            )
        )

        logger.info(f"测试用例库已加载: {len(self.test_cases)} 个测试用例")

    def get_test_cases(
        self, difficulty: Optional[str] = None, tags: Optional[List[str]] = None
    ) -> List[TestCase]:
        """获取测试用例，支持过滤"""
        filtered_cases = self.test_cases

        if difficulty:
            filtered_cases = [tc for tc in filtered_cases if tc.difficulty == difficulty]

        if tags:
            filtered_cases = [tc for tc in filtered_cases if any(tag in tc.tags for tag in tags)]

        return filtered_cases

    def get_random_test_case(self, difficulty: Optional[str] = None) -> TestCase:
        """随机获取一个测试用例"""
        filtered_cases = self.get_test_cases(difficulty)
        if not filtered_cases:
            return random.choice(self.test_cases)
        return random.choice(filtered_cases)


# ==================== 任务执行模拟器 ====================


class TaskExecutor:
    """任务执行模拟器

    模拟OpenCode包装器的执行，生成合理的输出和性能数据。
    在真实环境中，可以替换为实际调用OpenCode包装器。
    """

    def __init__(self, enable_cost_tracking: bool = True):
        self.response_templates = self._load_response_templates()
        self.enable_cost_tracking = enable_cost_tracking

        # 初始化成本跟踪集成（如果启用）
        self.cost_integration = None
        if enable_cost_tracking:
            try:
                from agent.core.cost_tracker_integration import CostTrackingIntegration

                self.cost_integration = CostTrackingIntegration()
                logger.info("成本跟踪集成已初始化")
            except Exception as e:
                logger.warning(f"成本跟踪集成初始化失败: {e}")
                self.cost_integration = None

    def _load_response_templates(self) -> Dict[str, List[str]]:
        """加载响应模板（基于测试用例的预期输出变体）"""
        return {
            "factorial": [
                "def factorial(n):\n    if n < 0:\n        return None\n    result = 1\n    for i in range(2, n + 1):\n        result *= i\n    return result",
                "def factorial(n):\n    if n < 0:\n        return None\n    elif n == 0:\n        return 1\n    return n * factorial(n-1)",
                "def factorial(n):\n    import math\n    if n < 0:\n        return None\n    return math.factorial(n)",
            ],
            "list_operation": [
                "def remove_duplicates(lst):\n    return list(dict.fromkeys(lst))",
                "def unique_sorted(lst):\n    return sorted(set(lst))",
                "def process_list(lst):\n    unique = []\n    for item in lst:\n        if item not in unique:\n            unique.append(item)\n    return sorted(unique)",
            ],
            "file_operation": [
                "import pandas as pd\n\ndef analyze_csv(file_path):\n    df = pd.read_csv(file_path)\n    return df.describe().to_dict()",
                "import csv\n\ndef read_csv_stats(file_path):\n    with open(file_path, 'r') as f:\n        reader = csv.reader(f)\n        rows = list(reader)\n    return {'rows': len(rows)-1, 'cols': len(rows[0]) if rows else 0}",
            ],
            "default": ["# 函数实现\n# 这是一个示例实现，实际实现可能因具体需求而有所不同"],
        }

    def execute_task(
        self,
        test_case: TestCase,
        provider: str,
        model: str,
        experiment_id: Optional[str] = None,
        group_name: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """执行任务并返回结果

        模拟真实执行，生成：
        1. 输出响应（基于预期输出的变体）
        2. 执行时间（模拟不同provider的性能差异）
        3. Tokens使用量（模拟不同模型的token消耗）
        4. 成本信息（基于provider定价）

        Args:
            test_case: 测试用例
            provider: provider ID
            model: 模型ID
            experiment_id: 实验ID（可选，用于成本记录）
            group_name: 分组名称（可选，用于成本记录）
            request_id: 请求ID（可选，用于与实验记录关联）
        """
        start_time = time.time()

        # 模拟执行时间（秒）：DeepSeek稍快，DashScope稍慢
        if provider == "deepseek":
            execution_time = random.uniform(0.5, 2.0)
        else:
            execution_time = random.uniform(1.0, 3.0)

        # 模拟tokens使用量
        input_tokens = len(test_case.prompt) // 3  # 粗略估算
        output_tokens = random.randint(50, 300)

        # 基于provider和模型计算成本
        cost_info = self._calculate_cost(provider, model, input_tokens, output_tokens)

        # 生成输出响应（基于预期输出的变体）
        output_response = self._generate_output_response(test_case, provider)

        # 确保响应不为空
        if not output_response:
            output_response = test_case.expected_output

        # 模拟实际执行时间
        time.sleep(min(execution_time, 0.1))  # 实际等待时间较短，避免测试过慢

        # 创建真实的成本记录（如果启用成本跟踪）
        cost_record_id = None
        if self.cost_integration:
            try:
                # 使用传入的request_id或生成新的（确保成本记录与实验记录关联）
                cost_request_id = request_id
                if not cost_request_id:
                    cost_request_id = (
                        f"exp_req_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
                    )

                # 记录成本
                cost_record_id = self.cost_integration.record_provider_request(
                    provider_id=provider,
                    model_id=model,
                    task_kind=test_case.task_kind,
                    input_text=test_case.prompt,
                    output_text=output_response,
                    request_id=cost_request_id,
                    estimated_tokens=True,
                    metadata={
                        "test_case_id": test_case.id,
                        "experiment_id": (
                            experiment_id if experiment_id else "experiment_integration_test"
                        ),
                        "group_name": group_name if group_name else "unknown",
                        "simulated_execution": True,
                        "simulated_tokens": True,
                    },
                )

                if cost_record_id:
                    logger.debug(f"成本记录创建成功: {cost_record_id} for {provider}/{model}")
                else:
                    logger.warning(f"成本记录创建失败 for {provider}/{model}")

            except Exception as e:
                logger.error(f"成本记录创建异常: {e}")
                cost_record_id = None

        return {
            "output_response": output_response,
            "execution_time": execution_time,
            "tokens_used": {"input": input_tokens, "output": output_tokens},
            "cost_info": cost_info,
            "cost_record_id": cost_record_id,
            "metadata": {
                "provider": provider,
                "model": model,
                "test_case_id": test_case.id,
                "simulated": True,
                "executed_at": datetime.now().isoformat(),
                "cost_record_created": cost_record_id is not None,
            },
        }

    def _calculate_cost(
        self, provider: str, model: str, input_tokens: int, output_tokens: int
    ) -> Dict[str, Any]:
        """计算成本信息"""
        # 定价（人民币/1K tokens）
        pricing = {
            "dashscope": {
                "qwen3.5-plus": 0.008,  # ¥0.008/1K tokens
                "input_rate": 0.008,
                "output_rate": 0.008,
            },
            "deepseek": {
                "deepseek-coder": 0.001,  # ¥0.001/1K tokens
                "input_rate": 0.001,
                "output_rate": 0.001,
            },
        }

        if provider in pricing and model in pricing[provider]:
            rate = pricing[provider][model]
        elif provider in pricing:
            rate = pricing[provider].get("input_rate", 0.008)
        else:
            rate = 0.008  # 默认

        total_tokens = input_tokens + output_tokens
        estimated_cost = (total_tokens / 1000) * rate

        return {
            "estimated_cost": estimated_cost,
            "currency": "CNY",
            "provider": provider,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "rate_per_1k": rate,
            "calculation_timestamp": datetime.now().isoformat(),
        }

    def _generate_output_response(self, test_case: TestCase, provider: str) -> str:
        """生成输出响应（基于测试用例和provider）"""
        # 根据测试用例类型选择模板
        template_key = "default"

        if "factorial" in test_case.tags:
            template_key = "factorial"
        elif "list" in test_case.tags or "sort" in test_case.tags:
            template_key = "list_operation"
        elif "file" in test_case.tags or "csv" in test_case.tags:
            template_key = "file_operation"

        templates = self.response_templates.get(template_key, self.response_templates["default"])

        # 选择模板并添加provider特定注释
        response = random.choice(templates)

        # 添加provider标识（模拟不同模型的输出风格）
        if provider == "deepseek":
            header = f"# 使用DeepSeek Coder生成的代码\n# 任务: {test_case.name}\n# 难度: {test_case.difficulty}\n\n"
        else:
            header = f"# 使用DashScope Qwen生成的代码\n# 任务: {test_case.name}\n# 难度: {test_case.difficulty}\n\n"

        return header + response


# ==================== 实验运行器主类 ====================


class ExperimentRunner:
    """实验运行器主类"""

    def __init__(
        self,
        experiment_id: str = "coding_plan_deepseek_coder_ab",
        target_samples: int = 100,
        batch_size: int = 10,
        enable_quality_assessment: bool = False,
    ):
        self.experiment_id = experiment_id
        self.target_samples = target_samples
        self.batch_size = batch_size
        self.enable_quality_assessment = enable_quality_assessment

        # 初始化组件
        self.experiment_router = get_experiment_router()
        self.experiment_logger = get_experiment_logger()
        self.test_case_lib = TestCaseLibrary()
        self.task_executor = TaskExecutor()

        # 跟踪状态
        self.completed_samples = 0
        self.group_counts = {"control": 0, "treatment": 0}
        self.start_time = None
        self.results = []

        logger.info(f"实验运行器初始化完成，目标样本数: {target_samples}")

    def run_experiment(self) -> bool:
        """运行实验"""
        logger.info(f"开始运行实验: {self.experiment_id}")
        self.start_time = time.time()

        try:
            # 分批运行，避免资源耗尽
            batches = (self.target_samples + self.batch_size - 1) // self.batch_size

            for batch_num in range(1, batches + 1):
                logger.info(f"运行批次 {batch_num}/{batches}")

                batch_samples = min(self.batch_size, self.target_samples - self.completed_samples)
                if batch_samples <= 0:
                    break

                self._run_batch(batch_num, batch_samples)

                # 批次间延迟，避免过载
                if batch_num < batches:
                    time.sleep(1)

            # 生成实验摘要
            self._generate_summary()

            elapsed_time = time.time() - self.start_time
            logger.info(f"实验运行完成，总时间: {elapsed_time:.1f}秒")
            logger.info(f"完成样本数: {self.completed_samples}/{self.target_samples}")
            logger.info(f"分组分布: {self.group_counts}")

            return True

        except Exception as e:
            logger.error(f"实验运行失败: {e}")
            import traceback

            traceback.print_exc()
            return False

    def _run_batch(self, batch_num: int, batch_size: int):
        """运行一个批次"""
        # 获取请求ID生成器
        id_generator = get_request_id_generator()

        for i in range(batch_size):
            try:
                # 生成唯一请求ID（使用统一格式）
                request_id = id_generator.generate(
                    prefix=id_generator.PREFIX_EXPERIMENT, unique_id=f"{batch_num:03d}_{i:03d}"
                )

                # 随机选择测试用例（平衡难度分布）
                difficulty = random.choice(["easy", "medium", "hard"])
                test_case = self.test_case_lib.get_random_test_case(difficulty)

                # 1. 实验分配
                assignment = self.experiment_router.assign_to_experiment(
                    task_kind=test_case.task_kind, request_id=request_id
                )

                if not assignment:
                    logger.warning(f"请求 {request_id} 未分配到实验，跳过")
                    continue

                # 记录分组分配
                self.group_counts[assignment.group_name] = (
                    self.group_counts.get(assignment.group_name, 0) + 1
                )

                # 2. 记录实验分配
                input_context = {
                    "prompt": test_case.prompt,
                    "test_case_id": test_case.id,
                    "difficulty": test_case.difficulty,
                    "tags": test_case.tags,
                }

                record_id = self.experiment_logger.log_experiment_assignment(
                    task_kind=test_case.task_kind,
                    request_id=request_id,
                    assignment_metadata=assignment.metadata,
                    input_context=input_context,
                )

                if not record_id:
                    logger.warning(f"实验分配记录失败: {request_id}")
                    continue

                # 3. 获取provider和model（从实验配置）
                provider, model = self.experiment_router.get_provider_for_experiment(
                    task_kind=test_case.task_kind,
                    request_id=request_id,
                    default_provider="dashscope",
                    default_model="qwen3.5-plus",
                )

                # 4. 执行任务（传递实验ID、分组信息和请求ID）
                execution_result = self.task_executor.execute_task(
                    test_case=test_case,
                    provider=provider,
                    model=model,
                    experiment_id=assignment.experiment_id,
                    group_name=assignment.group_name,
                    request_id=request_id,  # 传递相同的请求ID以确保关联
                )

                # 5. 记录执行结果
                success = self.experiment_logger.log_experiment_execution(
                    request_id=request_id,
                    execution_result=execution_result,
                    cost_record_id=execution_result.get("cost_record_id"),  # 使用真实的成本记录ID
                )

                if not success:
                    logger.warning(f"执行结果记录失败: {request_id}")

                # 6. 模拟质量评估（如果启用）
                if self.enable_quality_assessment:
                    quality_assessment = self._assess_quality(
                        test_case, execution_result["output_response"]
                    )
                    quality_success = self.experiment_logger.log_experiment_quality(
                        request_id=request_id, quality_assessment=quality_assessment
                    )

                    if not quality_success:
                        logger.warning(f"质量评估记录失败: {request_id}")

                # 7. 标记实验完成
                completion_success = self.experiment_logger.complete_experiment(request_id)

                if not completion_success:
                    logger.warning(f"实验完成标记失败: {request_id}")

                # 更新计数
                self.completed_samples += 1

                # 保存结果
                self.results.append(
                    {
                        "request_id": request_id,
                        "test_case_id": test_case.id,
                        "group_name": assignment.group_name,
                        "provider": provider,
                        "model": model,
                        "execution_time": execution_result["execution_time"],
                        "cost": execution_result["cost_info"]["estimated_cost"],
                        "recorded_at": datetime.now().isoformat(),
                    }
                )

                # 进度日志
                if self.completed_samples % 10 == 0:
                    logger.info(f"进度: {self.completed_samples}/{self.target_samples} 样本完成")

            except Exception as e:
                logger.error(f"处理请求 {request_id} 时出错: {e}")
                continue

    def _assess_quality(self, test_case: TestCase, actual_output: str) -> Dict[str, Any]:
        """评估代码质量（模拟）

        在实际应用中，应使用真实的代码质量评估器。
        这里模拟评估过程，基于与预期输出的相似度。
        """
        # 简单相似度计算（模拟）
        similarity_score = self._calculate_similarity(test_case.expected_output, actual_output)

        # 基础质量评分（0-10）
        base_score = similarity_score * 10

        # 添加随机波动（±1.5分）
        final_score = max(0, min(10, base_score + random.uniform(-1.5, 1.5)))

        # 分解评分
        breakdown = {
            "correctness": final_score * random.uniform(0.8, 1.0),
            "readability": final_score * random.uniform(0.7, 1.0),
            "efficiency": final_score * random.uniform(0.6, 1.0),
            "style": final_score * random.uniform(0.7, 1.0),
        }

        # 归一化
        for key in breakdown:
            breakdown[key] = max(0, min(10, breakdown[key]))

        return {
            "quality_score": round(final_score, 1),
            "quality_breakdown": {k: round(v, 1) for k, v in breakdown.items()},
            "quality_assessor": "auto_simulated",
            "metadata": {
                "test_case_id": test_case.id,
                "similarity_score": similarity_score,
                "assessed_at": datetime.now().isoformat(),
            },
        }

    def _calculate_similarity(self, expected: str, actual: str) -> float:
        """计算字符串相似度（简单实现）"""

        # 移除空格和注释进行比较
        def normalize_code(code):
            lines = []
            for line in code.split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    lines.append(line)
            return " ".join(lines)

        expected_norm = normalize_code(expected)
        actual_norm = normalize_code(actual)

        if not expected_norm or not actual_norm:
            return 0.5  # 默认相似度

        # 简单相似度：共同单词比例
        expected_words = set(expected_norm.split())
        actual_words = set(actual_norm.split())

        if not expected_words or not actual_words:
            return 0.5

        intersection = expected_words.intersection(actual_words)
        union = expected_words.union(actual_words)

        return len(intersection) / len(union) if union else 0.5

    def _generate_summary(self):
        """生成实验运行摘要"""
        if not self.results:
            return

        # 计算统计信息
        total_cost = sum(r["cost"] for r in self.results)
        avg_execution_time = sum(r["execution_time"] for r in self.results) / len(self.results)

        # 按分组统计
        group_stats = {}
        for result in self.results:
            group = result["group_name"]
            if group not in group_stats:
                group_stats[group] = {
                    "count": 0,
                    "total_cost": 0,
                    "avg_execution_time": 0,
                    "providers": {},
                }

            stats = group_stats[group]
            stats["count"] += 1
            stats["total_cost"] += result["cost"]
            stats["avg_execution_time"] += result["execution_time"]

            provider = result["provider"]
            stats["providers"][provider] = stats["providers"].get(provider, 0) + 1

        # 计算平均值
        for group in group_stats:
            count = group_stats[group]["count"]
            if count > 0:
                group_stats[group]["avg_execution_time"] /= count

        # 保存摘要
        summary = {
            "experiment_id": self.experiment_id,
            "total_samples": self.completed_samples,
            "group_distribution": self.group_counts,
            "total_cost": total_cost,
            "avg_execution_time": avg_execution_time,
            "group_stats": group_stats,
            "run_start_time": (
                datetime.fromtimestamp(self.start_time).isoformat() if self.start_time else None
            ),
            "run_end_time": datetime.now().isoformat(),
            "results_file": self._save_results(),
        }

        # 保存摘要到文件
        summary_file = f"/tmp/experiment_summary_{self.experiment_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        logger.info(f"实验摘要已保存: {summary_file}")

        # 打印关键指标
        print("\n" + "=" * 60)
        print("📊 实验运行摘要")
        print("=" * 60)
        print(f"实验ID: {self.experiment_id}")
        print(f"完成样本数: {self.completed_samples}")
        print(f"分组分布: {self.group_counts}")
        print(f"总成本: ¥{total_cost:.6f}")
        print(f"平均执行时间: {avg_execution_time:.2f}秒")

        # 按分组显示成本
        for group, stats in group_stats.items():
            print(f"\n分组 {group}:")
            print(f"  样本数: {stats['count']}")
            print(f"  总成本: ¥{stats['total_cost']:.6f}")
            print(f"  平均成本/样本: ¥{stats['total_cost']/stats['count']:.6f}")
            print(f"  平均执行时间: {stats['avg_execution_time']:.2f}秒")
            print(f"  Provider分布: {stats['providers']}")

        print("=" * 60)

    def _save_results(self) -> str:
        """保存详细结果到文件"""
        if not self.results:
            return ""

        results_file = f"/tmp/experiment_results_{self.experiment_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        return results_file

    def get_status(self) -> Dict[str, Any]:
        """获取运行状态"""
        return {
            "experiment_id": self.experiment_id,
            "target_samples": self.target_samples,
            "completed_samples": self.completed_samples,
            "progress_percentage": (
                (self.completed_samples / self.target_samples * 100)
                if self.target_samples > 0
                else 0
            ),
            "group_counts": self.group_counts,
            "start_time": (
                datetime.fromtimestamp(self.start_time).isoformat() if self.start_time else None
            ),
            "elapsed_time": time.time() - self.start_time if self.start_time else 0,
            "estimated_time_remaining": self._estimate_time_remaining(),
        }

    def _estimate_time_remaining(self) -> float:
        """估计剩余时间"""
        if not self.start_time or self.completed_samples == 0:
            return 0

        elapsed_time = time.time() - self.start_time
        samples_per_second = self.completed_samples / elapsed_time

        remaining_samples = self.target_samples - self.completed_samples
        if samples_per_second > 0:
            return remaining_samples / samples_per_second

        return 0


# ==================== 命令行接口 ====================


def main():
    """命令行接口"""
    import argparse

    parser = argparse.ArgumentParser(description="实验运行器")
    subparsers = parser.add_subparsers(dest="command", help="命令")

    # 运行实验命令
    run_parser = subparsers.add_parser("run", help="运行实验")
    run_parser.add_argument(
        "--experiment-id", default="coding_plan_deepseek_coder_ab", help="实验ID"
    )
    run_parser.add_argument("--samples", type=int, default=100, help="目标样本数")
    run_parser.add_argument("--batch-size", type=int, default=10, help="批次大小")
    run_parser.add_argument("--enable-quality", action="store_true", help="启用质量评估")

    # 状态检查命令
    status_parser = subparsers.add_parser("status", help="检查运行状态")
    status_parser.add_argument(
        "--experiment-id", default="coding_plan_deepseek_coder_ab", help="实验ID"
    )

    args = parser.parse_args()

    if args.command == "run":
        runner = ExperimentRunner(
            experiment_id=args.experiment_id,
            target_samples=args.samples,
            batch_size=args.batch_size,
            enable_quality_assessment=args.enable_quality,
        )

        print(f"🚀 开始运行实验: {args.experiment_id}")
        print(f"目标样本数: {args.samples}")
        print(f"批次大小: {args.batch_size}")
        print(f"启用质量评估: {args.enable_quality}")
        print("=" * 60)

        success = runner.run_experiment()

        if success:
            print("✅ 实验运行完成")
            sys.exit(0)
        else:
            print("❌ 实验运行失败")
            sys.exit(1)

    elif args.command == "status":
        # 这里需要实现状态检查，简化处理
        print("状态检查功能待实现")
        sys.exit(0)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
