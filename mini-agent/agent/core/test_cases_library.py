#!/usr/bin/env python3
"""
测试用例库 - 包含代表性编程任务，用于质量评估

提供10-20个不同难度和类型的编程任务，覆盖常见编码场景：
1. 算法实现（排序、搜索、数学计算）
2. 数据处理（字符串处理、列表操作、字典处理）
3. 面向对象编程（类设计、继承、多态）
4. 文件操作和I/O处理
5. 错误处理和边界情况
6. API设计和使用
7. 并发和异步编程（基础）

每个测试用例包含：
- 任务描述（prompt）
- 参考解决方案（用于质量评估）
- 测试用例或验证方法（可选）
- 难度级别（1-5，1最简单，5最难）
- 类别标签
"""

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class TaskCategory(Enum):
    """任务类别"""

    ALGORITHM = "algorithm"  # 算法实现
    DATA_STRUCTURE = "data_structure"  # 数据结构
    STRING_MANIPULATION = "string"  # 字符串处理
    MATH_COMPUTATION = "math"  # 数学计算
    FILE_IO = "file_io"  # 文件操作
    OOP = "oop"  # 面向对象编程
    ERROR_HANDLING = "error"  # 错误处理
    API_INTEGRATION = "api"  # API集成
    CONCURRENCY = "concurrency"  # 并发编程


class DifficultyLevel(Enum):
    """难度级别"""

    BEGINNER = 1  # 初学者（简单函数）
    EASY = 2  # 容易（基础算法）
    INTERMEDIATE = 3  # 中等（组合任务）
    ADVANCED = 4  # 高级（复杂设计）
    EXPERT = 5  # 专家（系统设计）


@dataclass
class TestCase:
    """测试用例定义"""

    name: str
    input_data: Any
    expected_output: Any
    description: str = ""
    is_hidden: bool = False  # 是否为隐藏测试用例


@dataclass
class ProgrammingTask:
    """编程任务定义"""

    id: str  # 任务ID
    title: str  # 任务标题
    prompt: str  # 任务描述（用户看到的prompt）
    category: TaskCategory  # 任务类别
    difficulty: DifficultyLevel  # 难度级别
    reference_solution: str  # 参考解决方案（用于质量评估）
    test_cases: List[TestCase] = field(default_factory=list)  # 测试用例列表
    constraints: List[str] = field(default_factory=list)  # 约束条件
    hints: List[str] = field(default_factory=list)  # 提示
    tags: List[str] = field(default_factory=list)  # 标签
    description: str = ""  # 详细描述

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        # 使用自定义字典工厂处理类型对象
        from dataclasses import _is_dataclass_instance

        def convert_value(obj):
            """转换值以便JSON序列化"""
            if isinstance(obj, type):
                # 类型对象转换为字符串
                return obj.__name__
            elif _is_dataclass_instance(obj):
                # dataclass实例递归转换
                return {
                    f.name: convert_value(getattr(obj, f.name))
                    for f in obj.__dataclass_fields__.values()
                }
            elif isinstance(obj, list):
                return [convert_value(item) for item in obj]
            elif isinstance(obj, dict):
                return {key: convert_value(value) for key, value in obj.items()}
            else:
                return obj

        # 手动构建字典，避免asdict的类型问题
        data = {
            "id": self.id,
            "title": self.title,
            "prompt": self.prompt,
            "category": self.category.value,
            "difficulty": self.difficulty.value,
            "reference_solution": self.reference_solution,
            "test_cases": [convert_value(tc) for tc in self.test_cases],
            "constraints": self.constraints.copy(),
            "hints": self.hints.copy(),
            "tags": self.tags.copy(),
            "description": self.description,
        }
        return data


class TestCaseLibrary:
    """测试用例库"""

    def __init__(self):
        self.tasks = self._create_tasks()
        self._task_dict = {task.id: task for task in self.tasks}

    def _create_tasks(self) -> List[ProgrammingTask]:
        """创建测试任务列表"""
        tasks = []

        # 1. 斐波那契数列（基础算法）
        tasks.append(
            ProgrammingTask(
                id="fibonacci",
                title="计算斐波那契数列",
                category=TaskCategory.ALGORITHM,
                difficulty=DifficultyLevel.BEGINNER,
                prompt="编写一个Python函数计算斐波那契数列的第n项。函数应高效处理较大的n值，并包含适当的错误处理。",
                reference_solution="""
def fibonacci(n):
    \"\"\"计算斐波那契数列的第n项\"\"\"
    if not isinstance(n, int):
        raise TypeError("输入必须是整数")
    if n < 0:
        raise ValueError("输入必须是非负整数")
    if n <= 1:
        return n

    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

# 测试用例
if __name__ == "__main__":
    test_cases = [(0, 0), (1, 1), (2, 1), (3, 2), (5, 5), (10, 55)]
    for n, expected in test_cases:
        result = fibonacci(n)
        assert result == expected, f"fibonacci({n}) = {result}, expected {expected}"
    print("所有测试通过")
""",
                test_cases=[
                    TestCase("基础测试-0", 0, 0),
                    TestCase("基础测试-1", 1, 1),
                    TestCase("基础测试-5", 5, 5),
                    TestCase("基础测试-10", 10, 55),
                    TestCase("错误处理-负值", -1, ValueError, is_hidden=True),
                    TestCase("错误处理-非整数", "5", TypeError, is_hidden=True),
                ],
                constraints=["时间复杂度O(n)", "空间复杂度O(1)"],
                tags=["递归", "迭代", "动态规划", "错误处理"],
            )
        )

        # 2. 字符串反转（字符串处理）
        tasks.append(
            ProgrammingTask(
                id="reverse_string",
                title="字符串反转",
                category=TaskCategory.STRING_MANIPULATION,
                difficulty=DifficultyLevel.BEGINNER,
                prompt="编写一个函数，反转输入字符串。支持Unicode字符，保持特殊字符不变。",
                reference_solution="""
def reverse_string(s):
    \"\"\"反转字符串\"\"\"
    if not isinstance(s, str):
        raise TypeError("输入必须是字符串")
    return s[::-1]

# 测试用例
def test_reverse_string():
    assert reverse_string("hello") == "olleh"
    assert reverse_string("") == ""
    assert reverse_string("a") == "a"
    assert reverse_string("你好世界") == "界世好你"
    assert reverse_string("hello world!") == "!dlrow olleh"
    print("所有测试通过")

if __name__ == "__main__":
    test_reverse_string()
""",
                test_cases=[
                    TestCase("英文单词", "hello", "olleh"),
                    TestCase("空字符串", "", ""),
                    TestCase("单个字符", "a", "a"),
                    TestCase("中文字符", "你好世界", "界世好你"),
                    TestCase("带空格和标点", "hello world!", "!dlrow olleh"),
                ],
                tags=["字符串", "切片", "Unicode"],
            )
        )

        # 3. 列表去重（数据处理）
        tasks.append(
            ProgrammingTask(
                id="remove_duplicates",
                title="列表去重",
                category=TaskCategory.DATA_STRUCTURE,
                difficulty=DifficultyLevel.EASY,
                prompt="编写一个函数，移除列表中的重复元素，保持原始顺序。",
                reference_solution="""
def remove_duplicates(lst):
    \"\"\"移除列表中的重复元素，保持原始顺序\"\"\"
    if not isinstance(lst, list):
        raise TypeError("输入必须是列表")

    seen = set()
    result = []
    for item in lst:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result

# 测试用例
if __name__ == "__main__":
    test_cases = [
        ([1, 2, 3, 2, 1], [1, 2, 3]),
        ([], []),
        ([1, 1, 1, 1], [1]),
        (["a", "b", "a", "c"], ["a", "b", "c"]),
        ([1, "1", 1], [1, "1"]),  # 类型不同不算重复
    ]

    for input_list, expected in test_cases:
        result = remove_duplicates(input_list)
        assert result == expected, f"{input_list} -> {result}, expected {expected}"
    print("所有测试通过")
""",
                test_cases=[
                    TestCase("整数列表", [1, 2, 3, 2, 1], [1, 2, 3]),
                    TestCase("空列表", [], []),
                    TestCase("全重复列表", [1, 1, 1, 1], [1]),
                    TestCase("字符串列表", ["a", "b", "a", "c"], ["a", "b", "c"]),
                    TestCase("混合类型", [1, "1", 1], [1, "1"]),
                ],
                constraints=["保持原始顺序", "时间复杂度O(n)"],
                tags=["列表", "集合", "顺序保持"],
            )
        )

        # 4. 质数判断（数学计算）
        tasks.append(
            ProgrammingTask(
                id="is_prime",
                title="质数判断",
                category=TaskCategory.MATH_COMPUTATION,
                difficulty=DifficultyLevel.EASY,
                prompt="编写一个函数判断一个数是否为质数。优化性能以处理较大的数。",
                reference_solution="""
import math

def is_prime(n):
    \"\"\"判断一个数是否为质数\"\"\"
    if not isinstance(n, int):
        raise TypeError("输入必须是整数")
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False

    # 只需检查到平方根
    sqrt_n = int(math.isqrt(n))
    for i in range(3, sqrt_n + 1, 2):
        if n % i == 0:
            return False
    return True

# 测试用例
if __name__ == "__main__":
    primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]
    non_primes = [1, 4, 6, 8, 9, 10, 12, 14, 15, 16]

    for p in primes:
        assert is_prime(p), f"{p} 应该是质数"
    for np in non_primes:
        assert not is_prime(np), f"{np} 应该不是质数"

    # 边界测试
    assert not is_prime(-1)
    assert not is_prime(0)
    assert not is_prime(1)

    print("所有测试通过")
""",
                test_cases=[
                    TestCase("小质数", 7, True),
                    TestCase("小合数", 9, False),
                    TestCase("边界-2", 2, True),
                    TestCase("边界-1", 1, False),
                    TestCase("边界-0", 0, False),
                    TestCase("中等质数", 997, True),
                    TestCase("中等合数", 999, False),
                ],
                constraints=["时间复杂度O(√n)", "优化偶数检查"],
                tags=["数学", "质数", "优化"],
            )
        )

        # 5. 文件行数统计（文件操作）
        tasks.append(
            ProgrammingTask(
                id="count_lines",
                title="统计文件行数",
                category=TaskCategory.FILE_IO,
                difficulty=DifficultyLevel.INTERMEDIATE,
                prompt="编写一个函数统计文本文件的行数。处理大文件时内存使用要高效。",
                reference_solution="""
def count_lines(filename):
    \"\"\"统计文本文件的行数\"\"\"
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            line_count = 0
            for line in f:
                line_count += 1
        return line_count
    except FileNotFoundError:
        raise FileNotFoundError(f"文件未找到: {filename}")
    except IOError as e:
        raise IOError(f"读取文件时出错: {e}")
    except Exception as e:
        raise RuntimeError(f"未知错误: {e}")

# 测试用例（需要实际文件，这里用模拟）
if __name__ == "__main__":
    import tempfile
    import os

    # 创建测试文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("第一行\\n")
        f.write("第二行\\n")
        f.write("第三行\\n")
        test_file = f.name

    try:
        assert count_lines(test_file) == 3

        # 测试空文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            empty_file = f.name
        assert count_lines(empty_file) == 0

        # 测试文件不存在
        try:
            count_lines("nonexistent.txt")
            assert False, "应该抛出FileNotFoundError"
        except FileNotFoundError:
            pass

        print("所有测试通过")
    finally:
        # 清理测试文件
        if os.path.exists(test_file):
            os.unlink(test_file)
        if os.path.exists(empty_file):
            os.unlink(empty_file)
""",
                test_cases=[],
                constraints=["内存高效", "错误处理完善", "支持大文件"],
                tags=["文件操作", "IO", "错误处理", "内存管理"],
            )
        )

        # 6. 学生成绩管理系统（OOP）
        tasks.append(
            ProgrammingTask(
                id="student_management",
                title="学生成绩管理系统",
                category=TaskCategory.OOP,
                difficulty=DifficultyLevel.INTERMEDIATE,
                prompt="设计一个学生成绩管理系统。包含Student类、GradeBook类，支持添加学生、记录成绩、计算平均分等功能。",
                reference_solution="""
class Student:
    \"\"\"学生类\"\"\"
    def __init__(self, student_id, name):
        if not student_id or not name:
            raise ValueError("学生ID和姓名不能为空")
        self.student_id = student_id
        self.name = name
        self.grades = {}  # 课程名: 成绩

    def add_grade(self, course, grade):
        \"\"\"添加成绩\"\"\"
        if not isinstance(grade, (int, float)):
            raise TypeError("成绩必须是数字")
        if grade < 0 or grade > 100:
            raise ValueError("成绩必须在0-100之间")
        self.grades[course] = grade

    def get_average(self):
        \"\"\"计算平均成绩\"\"\"
        if not self.grades:
            return 0.0
        return sum(self.grades.values()) / len(self.grades)

    def __str__(self):
        avg = self.get_average()
        return f"学生: {self.name} (ID: {self.student_id}), 平均分: {avg:.1f}"

    def __repr__(self):
        return f"Student(student_id='{self.student_id}', name='{self.name}')"


class GradeBook:
    \"\"\"成绩册类\"\"\"
    def __init__(self):
        self.students = {}

    def add_student(self, student):
        \"\"\"添加学生\"\"\"
        if not isinstance(student, Student):
            raise TypeError("只能添加Student对象")
        if student.student_id in self.students:
            raise ValueError(f"学生ID已存在: {student.student_id}")
        self.students[student.student_id] = student

    def get_student(self, student_id):
        \"\"\"获取学生\"\"\"
        if student_id not in self.students:
            raise KeyError(f"学生不存在: {student_id}")
        return self.students[student_id]

    def get_class_average(self):
        \"\"\"计算班级平均分\"\"\"
        if not self.students:
            return 0.0
        averages = [s.get_average() for s in self.students.values()]
        return sum(averages) / len(averages)

    def get_top_student(self):
        \"\"\"获取最高分学生\"\"\"
        if not self.students:
            return None
        return max(self.students.values(), key=lambda s: s.get_average())


# 测试用例
if __name__ == "__main__":
    # 创建学生
    s1 = Student("001", "张三")
    s1.add_grade("数学", 85)
    s1.add_grade("英语", 90)

    s2 = Student("002", "李四")
    s2.add_grade("数学", 78)
    s2.add_grade("英语", 92)

    # 创建成绩册
    gradebook = GradeBook()
    gradebook.add_student(s1)
    gradebook.add_student(s2)

    # 测试
    assert abs(s1.get_average() - 87.5) < 0.001
    assert abs(gradebook.get_class_average() - (87.5 + 85) / 2) < 0.001
    assert gradebook.get_top_student().name == "张三"

    print("所有测试通过")
""",
                test_cases=[],
                constraints=["完整的OOP设计", "数据验证", "清晰的接口"],
                tags=["面向对象", "类设计", "数据建模", "错误处理"],
            )
        )

        # 7. 简单的Web API客户端（API集成）
        tasks.append(
            ProgrammingTask(
                id="api_client",
                title="Web API客户端",
                category=TaskCategory.API_INTEGRATION,
                difficulty=DifficultyLevel.ADVANCED,
                prompt="编写一个简单的HTTP API客户端，支持GET/POST请求，包含错误重试和超时处理。",
                reference_solution="""
import requests
import time
from typing import Optional, Dict, Any


class APIClient:
    \"\"\"简单的HTTP API客户端\"\"\"

    def __init__(self, base_url: str, timeout: int = 10, max_retries: int = 3):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()

    def get(self, endpoint: str, params: Optional[Dict] = None, headers: Optional[Dict] = None):
        \"\"\"发送GET请求\"\"\"
        return self._request('GET', endpoint, params=params, headers=headers)

    def post(self, endpoint: str, data: Optional[Dict] = None,
             json_data: Optional[Dict] = None, headers: Optional[Dict] = None):
        \"\"\"发送POST请求\"\"\"
        return self._request('POST', endpoint, data=data, json=json_data, headers=headers)

    def _request(self, method: str, endpoint: str, **kwargs):
        \"\"\"发送HTTP请求，包含重试逻辑\"\"\"
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        for attempt in range(self.max_retries):
            try:
                response = self.session.request(
                    method, url,
                    timeout=self.timeout,
                    **kwargs
                )
                response.raise_for_status()  # 检查HTTP错误
                return response.json() if response.content else {}

            except requests.exceptions.Timeout:
                if attempt == self.max_retries - 1:
                    raise TimeoutError(f"请求超时，URL: {url}")
                time.sleep(2 ** attempt)  # 指数退避

            except requests.exceptions.HTTPError as e:
                # 4xx错误不重试，5xx错误重试
                if 400 <= response.status_code < 500:
                    raise ValueError(f"客户端错误 {response.status_code}: {response.text}")
                elif attempt == self.max_retries - 1:
                    raise RuntimeError(f"服务器错误 {response.status_code}: {response.text}")
                time.sleep(2 ** attempt)

            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise ConnectionError(f"网络错误: {e}")
                time.sleep(2 ** attempt)

        raise RuntimeError(f"请求失败，最大重试次数: {self.max_retries}")

    def close(self):
        \"\"\"关闭会话\"\"\"
        self.session.close()


# 使用示例
if __name__ == "__main__":
    # 注意：实际使用时需要真实API端点
    client = APIClient("https://api.example.com")
    try:
        # 模拟GET请求
        # data = client.get("users", params={"page": 1})
        # print(f"获取的用户数据: {data}")

        # 模拟POST请求
        # result = client.post("users", json_data={"name": "张三", "age": 25})
        # print(f"创建用户结果: {result}")
        pass
    finally:
        client.close()
    print("API客户端示例完成")
""",
                test_cases=[],
                constraints=["错误重试机制", "超时处理", "连接池管理", "安全的资源清理"],
                tags=["HTTP", "API", "错误处理", "重试逻辑", "连接管理"],
            )
        )

        # 8. 多线程下载器（并发编程基础）
        tasks.append(
            ProgrammingTask(
                id="threaded_downloader",
                title="多线程文件下载器",
                category=TaskCategory.CONCURRENCY,
                difficulty=DifficultyLevel.ADVANCED,
                prompt="编写一个支持多线程下载的文件下载器。支持分块下载、进度显示和错误恢复。",
                reference_solution="""
import threading
import requests
import os
import time
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed


class DownloadWorker(threading.Thread):
    \"\"\"下载工作线程\"\"\"
    def __init__(self, url: str, start_byte: int, end_byte: int,
                 filename: str, part_num: int):
        super().__init__()
        self.url = url
        self.start_byte = start_byte
        self.end_byte = end_byte
        self.filename = filename
        self.part_num = part_num
        self.downloaded = 0
        self.error = None

    def run(self):
        \"\"\"执行下载\"\"\"
        try:
            headers = {'Range': f'bytes={self.start_byte}-{self.end_byte}'}
            response = requests.get(self.url, headers=headers, stream=True)
            response.raise_for_status()

            with open(f"{self.filename}.part{self.part_num}", 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        self.downloaded += len(chunk)
        except Exception as e:
            self.error = str(e)


class ThreadedDownloader:
    \"\"\"多线程下载器\"\"\"
    def __init__(self, url: str, filename: str, num_threads: int = 4):
        self.url = url
        self.filename = filename
        self.num_threads = num_threads
        self.total_size = 0
        self.workers = []

    def get_file_size(self) -> int:
        \"\"\"获取文件大小\"\"\"
        try:
            response = requests.head(self.url)
            response.raise_for_status()
            self.total_size = int(response.headers.get('content-length', 0))
            return self.total_size
        except Exception as e:
            raise ConnectionError(f"无法获取文件大小: {e}")

    def calculate_ranges(self) -> List[Dict]:
        \"\"\"计算每个线程的下载范围\"\"\"
        if self.total_size == 0:
            return [{'start': 0, 'end': 0, 'part': 1}]

        chunk_size = self.total_size // self.num_threads
        ranges = []

        for i in range(self.num_threads):
            start = i * chunk_size
            end = start + chunk_size - 1 if i < self.num_threads - 1 else self.total_size - 1
            ranges.append({
                'start': start,
                'end': end,
                'part': i + 1
            })

        return ranges

    def download(self) -> bool:
        \"\"\"执行下载\"\"\"
        try:
            # 获取文件大小
            self.get_file_size()
            print(f"文件大小: {self.total_size} bytes")

            if self.total_size == 0:
                print("文件大小为0，无法下载")
                return False

            # 计算范围并创建worker
            ranges = self.calculate_ranges()
            self.workers = [
                DownloadWorker(self.url, r['start'], r['end'],
                             self.filename, r['part'])
                for r in ranges
            ]

            # 启动所有worker
            print(f"开始使用 {len(self.workers)} 个线程下载...")
            for worker in self.workers:
                worker.start()

            # 等待所有worker完成
            for worker in self.workers:
                worker.join()
                if worker.error:
                    print(f"线程 {worker.part_num} 错误: {worker.error}")
                    return False

            # 合并文件
            self._merge_parts()

            # 清理临时文件
            self._cleanup_parts()

            print(f"下载完成: {self.filename}")
            return True

        except Exception as e:
            print(f"下载失败: {e}")
            return False

    def _merge_parts(self):
        \"\"\"合并下载的部分\"\"\"
        with open(self.filename, 'wb') as outfile:
            for i in range(1, len(self.workers) + 1):
                part_file = f"{self.filename}.part{i}"
                if os.path.exists(part_file):
                    with open(part_file, 'rb') as infile:
                        outfile.write(infile.read())

    def _cleanup_parts(self):
        \"\"\"清理临时文件\"\"\"
        for i in range(1, len(self.workers) + 1):
            part_file = f"{self.filename}.part{i}"
            if os.path.exists(part_file):
                os.remove(part_file)


# 使用示例
if __name__ == "__main__":
    # 注意：实际使用时需要真实的URL
    # downloader = ThreadedDownloader(
    #     "https://example.com/large-file.zip",
    #     "large-file.zip",
    #     num_threads=4
    # )
    # success = downloader.download()
    # print(f"下载{'成功' if success else '失败'}")
    print("多线程下载器示例代码 - 需要真实URL进行测试")
""",
                test_cases=[],
                constraints=["线程安全", "资源清理", "错误恢复", "进度跟踪"],
                tags=["多线程", "并发", "下载", "分块", "错误处理"],
            )
        )

        # 9. 简单的缓存装饰器（高阶函数）
        tasks.append(
            ProgrammingTask(
                id="cache_decorator",
                title="缓存装饰器",
                category=TaskCategory.ALGORITHM,
                difficulty=DifficultyLevel.INTERMEDIATE,
                prompt="编写一个缓存装饰器，可以缓存函数的结果。支持缓存过期、最大缓存大小和基于参数的缓存键。",
                reference_solution="""
import functools
import time
from typing import Any, Dict, Tuple, Optional
from collections import OrderedDict


class CacheDecorator:
    \"\"\"缓存装饰器类\"\"\"

    def __init__(self, max_size: int = 100, ttl: Optional[int] = None):
        \"\"\"
        初始化缓存装饰器

        Args:
            max_size: 最大缓存条目数
            ttl: 缓存过期时间（秒），None表示永不过期
        \"\"\"
        self.max_size = max_size
        self.ttl = ttl
        self.cache = OrderedDict()  # 维护插入顺序

    def __call__(self, func):
        \"\"\"作为装饰器使用\"\"\"
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = self._make_cache_key(func.__name__, args, kwargs)

            # 检查缓存
            if cache_key in self.cache:
                cached_result, timestamp = self.cache[cache_key]

                # 检查是否过期
                if self.ttl is None or (time.time() - timestamp) < self.ttl:
                    # 更新访问顺序（LRU）
                    self.cache.move_to_end(cache_key)
                    return cached_result
                else:
                    # 过期，删除
                    del self.cache[cache_key]

            # 执行函数
            result = func(*args, **kwargs)

            # 缓存结果
            self.cache[cache_key] = (result, time.time())

            # 如果超过最大大小，删除最旧的条目（LRU）
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)

            return result

        # 添加缓存管理方法
        wrapper.clear_cache = self.clear_cache
        wrapper.get_cache_info = self.get_cache_info
        wrapper.get_cache_size = lambda: len(self.cache)

        return wrapper

    def _make_cache_key(self, func_name: str, args: Tuple, kwargs: Dict) -> str:
        \"\"\"生成缓存键\"\"\"
        # 简单实现：转换为字符串表示
        # 注意：对于复杂对象可能需要更智能的序列化
        args_repr = repr(args)
        kwargs_repr = repr(sorted(kwargs.items())) if kwargs else ''
        return f"{func_name}:{args_repr}:{kwargs_repr}"

    def clear_cache(self):
        \"\"\"清空缓存\"\"\"
        self.cache.clear()

    def get_cache_info(self) -> Dict[str, Any]:
        \"\"\"获取缓存信息\"\"\"
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'ttl': self.ttl,
            'cache_keys': list(self.cache.keys())
        }


# 使用示例
if __name__ == "__main__":
    # 创建缓存装饰器
    cache = CacheDecorator(max_size=10, ttl=60)  # 最大10条，60秒过期

    @cache
    def fibonacci(n):
        \"\"\"计算斐波那契数（使用缓存）\"\"\"
        if n <= 1:
            return n
        return fibonacci(n-1) + fibonacci(n-2)

    # 测试
    print("第一次计算fibonacci(30)（会实际计算）")
    start = time.time()
    result1 = fibonacci(30)
    time1 = time.time() - start
    print(f"结果: {result1}, 时间: {time1:.4f}秒")

    print("\\n第二次计算fibonacci(30)（从缓存读取）")
    start = time.time()
    result2 = fibonacci(30)
    time2 = time.time() - start
    print(f"结果: {result2}, 时间: {time2:.4f}秒")

    print(f"\\n缓存命中: {result1 == result2}, 加速比: {time1/time2:.1f}倍")

    # 查看缓存信息
    info = fibonacci.get_cache_info()
    print(f"\\n缓存信息: {info}")
""",
                test_cases=[],
                constraints=["LRU缓存策略", "缓存过期", "线程安全（基础）", "灵活的缓存键生成"],
                tags=["装饰器", "缓存", "LRU", "性能优化", "高阶函数"],
            )
        )

        # 10. 数据验证器（装饰器和元编程）
        tasks.append(
            ProgrammingTask(
                id="data_validator",
                title="数据验证装饰器",
                category=TaskCategory.ERROR_HANDLING,
                difficulty=DifficultyLevel.INTERMEDIATE,
                prompt="编写一个数据验证装饰器，可以验证函数参数的类型和值范围。支持自定义验证规则和错误消息。",
                reference_solution="""
import functools
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from inspect import signature, Parameter


class ValidationError(ValueError):
    \"\"\"验证错误\"\"\"
    def __init__(self, param_name: str, value: Any, rule: str, message: str = ""):
        self.param_name = param_name
        self.value = value
        self.rule = rule
        self.message = message or f"参数 '{param_name}' 验证失败: {value} 不符合规则 {rule}"
        super().__init__(self.message)


class Validator:
    \"\"\"验证器基类\"\"\"
    def __init__(self, rule: str, error_message: str = ""):
        self.rule = rule
        self.error_message = error_message

    def validate(self, value: Any) -> bool:
        \"\"\"验证值，返回True/False\"\"\"
        raise NotImplementedError

    def __call__(self, value: Any):
        if not self.validate(value):
            raise ValidationError("", value, self.rule, self.error_message)


class TypeValidator(Validator):
    \"\"\"类型验证器\"\"\"
    def __init__(self, expected_type: Union[type, Tuple[type, ...]], error_message: str = ""):
        rule = f"type:{expected_type}"
        super().__init__(rule, error_message)
        self.expected_type = expected_type

    def validate(self, value: Any) -> bool:
        return isinstance(value, self.expected_type)


class RangeValidator(Validator):
    \"\"\"范围验证器\"\"\"
    def __init__(self, min_val: Optional[float] = None, max_val: Optional[float] = None,
                 error_message: str = ""):
        rule_parts = []
        if min_val is not None:
            rule_parts.append(f"min:{min_val}")
        if max_val is not None:
            rule_parts.append(f"max:{max_val}")
        rule = ",".join(rule_parts)
        super().__init__(rule, error_message)
        self.min_val = min_val
        self.max_val = max_val

    def validate(self, value: Any) -> bool:
        if not isinstance(value, (int, float)):
            return False
        if self.min_val is not None and value < self.min_val:
            return False
        if self.max_val is not None and value > self.max_val:
            return False
        return True


class RegexValidator(Validator):
    \"\"\"正则表达式验证器\"\"\"
    def __init__(self, pattern: str, error_message: str = ""):
        import re
        rule = f"regex:{pattern}"
        super().__init__(rule, error_message)
        self.pattern = pattern
        self.regex = re.compile(pattern)

    def validate(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        return bool(self.regex.match(value))


def validate_params(**validators: Dict[str, Validator]):
    \"\"\"参数验证装饰器\"\"\"
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 获取函数签名
            sig = signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # 验证每个参数
            for param_name, value in bound_args.arguments.items():
                if param_name in validators:
                    validator = validators[param_name]
                    if not validator.validate(value):
                        raise ValidationError(
                            param_name, value, validator.rule, validator.error_message
                        )

            # 调用原函数
            return func(*args, **kwargs)

        return wrapper
    return decorator


# 使用示例
if __name__ == "__main__":
    # 定义验证器
    age_validator = RangeValidator(min_val=0, max_val=150, error_message="年龄必须在0-150之间")
    name_validator = RegexValidator(r'^[A-Za-z\u4e00-\u9fa5]+$', error_message="姓名只能包含字母和汉字")
    score_validator = RangeValidator(min_val=0, max_val=100, error_message="成绩必须在0-100之间")

    @validate_params(
        name=name_validator,
        age=age_validator,
        score=score_validator
    )
    def create_student(name: str, age: int, score: float) -> Dict:
        \"\"\"创建学生记录\"\"\"
        return {
            'name': name,
            'age': age,
            'score': score,
            'passed': score >= 60
        }

    # 测试有效输入
    try:
        result = create_student("张三", 20, 85.5)
        print(f"创建成功: {result}")
    except ValidationError as e:
        print(f"验证失败: {e}")

    # 测试无效输入
    try:
        result = create_student("张3", 20, 85.5)  # 姓名包含数字
        print(f"创建成功: {result}")
    except ValidationError as e:
        print(f"验证失败（预期）: {e}")

    try:
        result = create_student("张三", 200, 85.5)  # 年龄超出范围
        print(f"创建成功: {result}")
    except ValidationError as e:
        print(f"验证失败（预期）: {e}")

    try:
        result = create_student("张三", 20, 150)  # 成绩超出范围
        print(f"创建成功: {result}")
    except ValidationError as e:
        print(f"验证失败（预期）: {e}")
""",
                test_cases=[],
                constraints=["灵活的验证规则", "清晰的错误信息", "支持多种验证类型", "易于扩展"],
                tags=["装饰器", "验证", "类型检查", "参数验证", "错误处理"],
            )
        )

        return tasks

    def get_task(self, task_id: str) -> Optional[ProgrammingTask]:
        """根据ID获取任务"""
        return self._task_dict.get(task_id)

    def get_tasks_by_category(self, category: TaskCategory) -> List[ProgrammingTask]:
        """根据类别获取任务"""
        return [task for task in self.tasks if task.category == category]

    def get_tasks_by_difficulty(self, difficulty: DifficultyLevel) -> List[ProgrammingTask]:
        """根据难度获取任务"""
        return [task for task in self.tasks if task.difficulty == difficulty]

    def get_all_tasks(self) -> List[ProgrammingTask]:
        """获取所有任务"""
        return self.tasks.copy()

    def get_task_count(self) -> int:
        """获取任务总数"""
        return len(self.tasks)

    def export_to_json(self, filepath: str) -> bool:
        """导出为JSON文件"""
        try:
            data = {
                "tasks": [task.to_dict() for task in self.tasks],
                "total_tasks": len(self.tasks),
                "categories": [cat.value for cat in TaskCategory],
                "difficulty_levels": [diff.value for diff in DifficultyLevel],
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"导出失败: {e}")
            import traceback

            traceback.print_exc()
            return False

    def print_summary(self):
        """打印库摘要"""
        print(f"测试用例库摘要:")
        print(f"  总任务数: {self.get_task_count()}")

        # 按类别统计
        category_counts = {}
        for task in self.tasks:
            cat = task.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1

        print(f"  类别分布:")
        for cat, count in sorted(category_counts.items()):
            print(f"    {cat}: {count}个任务")

        # 按难度统计
        difficulty_counts = {}
        for task in self.tasks:
            diff = task.difficulty.value
            difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 1

        print(f"  难度分布:")
        for diff in sorted(difficulty_counts.keys()):
            level_name = {1: "初学者", 2: "容易", 3: "中等", 4: "高级", 5: "专家"}.get(
                diff, f"等级{diff}"
            )
            print(f"    {level_name}: {difficulty_counts[diff]}个任务")


# 全局实例
_test_case_library_instance = None


def get_test_case_library() -> TestCaseLibrary:
    """获取全局测试用例库实例"""
    global _test_case_library_instance
    if _test_case_library_instance is None:
        _test_case_library_instance = TestCaseLibrary()
    return _test_case_library_instance


if __name__ == "__main__":
    # 测试代码
    library = get_test_case_library()
    library.print_summary()

    print("\n前3个任务示例:")
    for i, task in enumerate(library.tasks[:3]):
        print(f"\n{i+1}. {task.title} (ID: {task.id})")
        print(f"   类别: {task.category.value}")
        print(f"   难度: {task.difficulty.value}")
        print(f"   描述: {task.prompt[:100]}...")
        print(f"   参考解决方案长度: {len(task.reference_solution)}字符")

    # 导出为JSON
    import os
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        json_file = f.name

    try:
        if library.export_to_json(json_file):
            print(f"\n✅ 测试用例库已导出到: {json_file}")
            with open(json_file, "r") as f:
                data = json.load(f)
                print(f"   导出任务数: {data['total_tasks']}")
    finally:
        if os.path.exists(json_file):
            os.unlink(json_file)
