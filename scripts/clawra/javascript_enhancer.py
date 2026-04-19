#!/usr/bin/env python3
"""
JavaScript执行增强模块
为豆包CLI提供增强的JavaScript执行功能

功能增强：
1. 重试机制：自动重试失败的执行
2. 错误处理：分类和恢复不同类型的错误
3. DOM元素定位：智能选择器策略
4. 执行状态监控：超时处理和状态跟踪
5. 性能优化：缓存和批量执行

设计原则：
- 向后兼容：保持现有API不变
- 渐进增强：默认使用增强功能，但可降级
- 模块化：可单独使用或集成到现有系统
"""

import json
import logging
import random
import re
import time
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class JavaScriptErrorType(Enum):
    """JavaScript错误类型"""

    SYNTAX_ERROR = "语法错误"  # JavaScript语法错误
    DOM_NOT_FOUND = "DOM元素未找到"  # 元素选择器未找到
    TIMEOUT = "执行超时"  # 执行时间过长
    APPLE_SCRIPT = "AppleScript错误"  # AppleScript层面错误
    PERMISSION_DENIED = "权限被拒绝"  # JavaScript执行权限问题
    NETWORK_ERROR = "网络错误"  # 页面加载或网络问题
    UNKNOWN = "未知错误"  # 其他错误


@dataclass
class ExecutionResult:
    """执行结果"""

    success: bool  # 是否成功
    output: str  # 输出内容
    error_type: Optional[JavaScriptErrorType]  # 错误类型
    error_message: str  # 错误消息
    execution_time: float  # 执行时间（秒）
    retry_count: int  # 重试次数
    timestamp: float  # 时间戳

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)


@dataclass
class DOMElement:
    """DOM元素信息"""

    selector: str  # 选择器
    tag_name: str  # 标签名
    element_type: str  # 元素类型（input, textarea, button等）
    attributes: Dict[str, str]  # 属性
    is_visible: bool  # 是否可见
    is_enabled: bool  # 是否启用
    bounding_rect: Optional[Dict]  # 边界矩形


class SelectorStrategy:
    """选择器策略管理器"""

    # 常见输入元素选择器（按优先级排序）
    INPUT_SELECTORS = [
        # 文本输入框
        "textarea",
        'input[type="text"]',
        'input[type="search"]',
        "input:not([type])",  # 默认type="text"
        "input",
        # 富文本编辑器
        '[contenteditable="true"]',
        ".ProseMirror",  # 常见富文本编辑器类
        ".DraftEditor-root",  # Draft.js编辑器
        # 豆包特定选择器（基于观察）
        ".input-area",
        ".chat-input",
        ".message-input",
        "#chat-input",
        "#message-input",
    ]

    # 按钮选择器
    BUTTON_SELECTORS = [
        "button",
        'input[type="submit"]',
        'input[type="button"]',
        '[role="button"]',
        ".send-button",
        ".submit-button",
        ".btn-primary",
        ".chat-send",
        "#send-button",
    ]

    @classmethod
    def get_input_selectors(cls) -> List[str]:
        """获取输入框选择器列表"""
        return cls.INPUT_SELECTORS.copy()

    @classmethod
    def get_button_selectors(cls) -> List[str]:
        """获取按钮选择器列表"""
        return cls.BUTTON_SELECTORS.copy()

    @classmethod
    def generate_selector_combinations(cls, element_type: str = "input") -> List[str]:
        """
        生成选择器组合

        Args:
            element_type: 元素类型（'input'或'button'）

        Returns:
            选择器组合列表
        """
        selectors = cls.INPUT_SELECTORS if element_type == "input" else cls.BUTTON_SELECTORS

        # 生成组合选择器
        combinations = []

        # 单个选择器
        combinations.extend(selectors)

        # 组合选择器（父元素 + 子元素）
        parent_selectors = ["body", "main", ".app-container", "#app"]
        for parent in parent_selectors:
            for selector in selectors:
                combinations.append(f"{parent} {selector}")

        return combinations

    @classmethod
    def create_smart_query(cls, element_type: str = "input") -> str:
        """
        创建智能查询JavaScript代码

        Args:
            element_type: 元素类型

        Returns:
            JavaScript代码
        """
        selectors = (
            cls.get_input_selectors() if element_type == "input" else cls.get_button_selectors()
        )

        js_code = """(function() {
            function findElement() {
                var selectors = %SELECTORS%;

                for (var i = 0; i < selectors.length; i++) {
                    var elements = document.querySelectorAll(selectors[i]);
                    if (elements.length > 0) {
                        // 找到第一个可见且启用的元素
                        for (var j = 0; j < elements.length; j++) {
                            var element = elements[j];
                            var style = window.getComputedStyle(element);

                            // 检查是否可见
                            var isVisible = element.offsetWidth > 0 &&
                                           element.offsetHeight > 0 &&
                                           style.display !== 'none' &&
                                           style.visibility !== 'hidden' &&
                                           style.opacity !== '0';

                            // 检查是否启用
                            var isEnabled = !element.disabled && !element.readOnly;

                            if (isVisible && isEnabled) {
                                return {
                                    selector: selectors[i],
                                    index: j,
                                    element: element,
                                    totalFound: elements.length
                                };
                            }
                        }
                    }
                }
                return null;
            }

            var result = findElement();
            if (result) {
                return JSON.stringify({
                    success: true,
                    selector: result.selector,
                    index: result.index,
                    totalFound: result.totalFound,
                    tagName: result.element.tagName,
                    type: result.element.type || 'unknown',
                    value: result.element.value || '',
                    placeholder: result.element.placeholder || '',
                    id: result.element.id || '',
                    className: result.element.className || ''
                });
            } else {
                return JSON.stringify({
                    success: false,
                    message: '未找到合适的元素'
                });
            }
        })()"""

        # 将选择器列表转换为JavaScript数组
        selectors_js = json.dumps(selectors)
        js_code = js_code.replace("%SELECTORS%", selectors_js)

        return js_code


class JavaScriptExecutor:
    """增强的JavaScript执行器"""

    def __init__(self, base_executor: Callable, max_retries: int = 3, timeout: int = 30):
        """
        初始化执行器

        Args:
            base_executor: 基础执行函数（如doubao_cli.execute_javascript）
            max_retries: 最大重试次数
            timeout: 超时时间（秒）
        """
        self.base_executor = base_executor
        self.max_retries = max_retries
        self.timeout = timeout
        self.selector_strategy = SelectorStrategy()

        # 执行统计
        self.execution_stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "retries": 0,
            "total_time": 0.0,
        }

        # 错误统计
        self.error_stats = {error_type: 0 for error_type in JavaScriptErrorType}

        # 缓存已找到的元素
        self.element_cache: Dict[str, DOMElement] = {}

    def execute_with_retry(
        self, js_code: str, window_idx: int = 1, tab_idx: int = 1, context: str = ""
    ) -> ExecutionResult:
        """
        带重试的JavaScript执行

        Args:
            js_code: JavaScript代码
            window_idx: 窗口索引
            tab_idx: 标签页索引
            context: 执行上下文描述（用于日志）

        Returns:
            ExecutionResult对象
        """
        start_time = time.time()
        retry_count = 0
        last_error = None

        for attempt in range(self.max_retries + 1):  # +1 包括第一次尝试
            try:
                # 执行JavaScript
                result = self.base_executor(window_idx, tab_idx, js_code)
                execution_time = time.time() - start_time

                # 分析结果
                if "JavaScript执行错误" in result:
                    error_info = self._analyze_error(result, js_code, context)
                    last_error = error_info

                    # 如果是可重试错误，则重试
                    if self._is_retryable_error(error_info["type"]):
                        if attempt < self.max_retries:
                            retry_count += 1
                            wait_time = self._calculate_backoff(attempt)
                            logger.warning(
                                f"执行失败，{wait_time}秒后重试 ({attempt+1}/{self.max_retries}): {error_info['message']}"
                            )
                            time.sleep(wait_time)
                            continue
                    # 不可重试错误，立即返回
                    return ExecutionResult(
                        success=False,
                        output=result,
                        error_type=error_info["type"],
                        error_message=error_info["message"],
                        execution_time=execution_time,
                        retry_count=retry_count,
                        timestamp=start_time,
                    )
                else:
                    # 成功执行
                    self.execution_stats["total"] += 1
                    self.execution_stats["success"] += 1
                    self.execution_stats["retries"] += retry_count
                    self.execution_stats["total_time"] += execution_time

                    return ExecutionResult(
                        success=True,
                        output=result,
                        error_type=None,
                        error_message="",
                        execution_time=execution_time,
                        retry_count=retry_count,
                        timestamp=start_time,
                    )

            except Exception as e:
                # 基础执行器抛出异常
                execution_time = time.time() - start_time
                error_info = self._analyze_exception(e, js_code, context)
                last_error = error_info

                if attempt < self.max_retries:
                    retry_count += 1
                    wait_time = self._calculate_backoff(attempt)
                    logger.warning(
                        f"执行异常，{wait_time}秒后重试 ({attempt+1}/{self.max_retries}): {error_info['message']}"
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    self.execution_stats["total"] += 1
                    self.execution_stats["failed"] += 1
                    self.error_stats[error_info["type"]] += 1

                    return ExecutionResult(
                        success=False,
                        output=str(e),
                        error_type=error_info["type"],
                        error_message=error_info["message"],
                        execution_time=execution_time,
                        retry_count=retry_count,
                        timestamp=start_time,
                    )

        # 所有重试都失败
        execution_time = time.time() - start_time
        self.execution_stats["total"] += 1
        self.execution_stats["failed"] += 1
        if last_error:
            self.error_stats[last_error["type"]] += 1

        return ExecutionResult(
            success=False,
            output="所有重试均失败",
            error_type=last_error["type"] if last_error else JavaScriptErrorType.UNKNOWN,
            error_message=last_error["message"] if last_error else "未知错误",
            execution_time=execution_time,
            retry_count=retry_count,
            timestamp=start_time,
        )

    def find_input_element(
        self, window_idx: int = 1, tab_idx: int = 1
    ) -> Tuple[Optional[DOMElement], ExecutionResult]:
        """
        智能查找输入元素

        Args:
            window_idx: 窗口索引
            tab_idx: 标签页索引

        Returns:
            (DOMElement, ExecutionResult) 元组
        """
        # 生成智能查询代码
        js_code = self.selector_strategy.create_smart_query("input")

        # 执行查询
        result = self.execute_with_retry(js_code, window_idx, tab_idx, "查找输入元素")

        if not result.success:
            return None, result

        # 解析结果
        try:
            # 从输出中提取JSON
            output = result.output
            # 移除前缀（如果有）
            if "JavaScript执行结果: " in output:
                json_str = output.split("JavaScript执行结果: ", 1)[1]
            else:
                json_str = output

            data = json.loads(json_str)

            if not data.get("success"):
                return None, ExecutionResult(
                    success=False,
                    output=output,
                    error_type=JavaScriptErrorType.DOM_NOT_FOUND,
                    error_message=data.get("message", "未找到元素"),
                    execution_time=result.execution_time,
                    retry_count=result.retry_count,
                    timestamp=result.timestamp,
                )

            # 创建DOMElement对象
            element = DOMElement(
                selector=data["selector"],
                tag_name=data["tagName"],
                element_type=data["type"],
                attributes={
                    "id": data.get("id", ""),
                    "className": data.get("className", ""),
                    "placeholder": data.get("placeholder", ""),
                    "value": data.get("value", ""),
                },
                is_visible=True,
                is_enabled=True,
                bounding_rect=None,
            )

            # 缓存元素
            cache_key = f"{window_idx}_{tab_idx}_input"
            self.element_cache[cache_key] = element

            return element, result

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"解析元素信息失败: {e}")
            return None, ExecutionResult(
                success=False,
                output=result.output,
                error_type=JavaScriptErrorType.UNKNOWN,
                error_message=f"解析失败: {str(e)}",
                execution_time=result.execution_time,
                retry_count=result.retry_count,
                timestamp=result.timestamp,
            )

    def fill_input(
        self, text: str, window_idx: int = 1, tab_idx: int = 1, element: Optional[DOMElement] = None
    ) -> ExecutionResult:
        """
        填充输入框

        Args:
            text: 要输入的文本
            window_idx: 窗口索引
            tab_idx: 标签页索引
            element: 可选的DOM元素（如未提供则自动查找）

        Returns:
            ExecutionResult对象
        """
        # 转义文本
        escaped_text = text.replace('"', '\\"').replace("'", "\\'").replace("\n", " ")

        if element is None:
            # 查找元素
            element, find_result = self.find_input_element(window_idx, tab_idx)
            if element is None:
                return find_result

        # 生成填充JavaScript
        js_code = f"""
        (function() {{
            try {{
                var elements = document.querySelectorAll("{element.selector}");
                if (elements.length > {element.attributes.get('index', 0)}) {{
                    var target = elements[{element.attributes.get('index', 0)}];

                    // 设置值
                    target.value = "{escaped_text}";

                    // 触发事件以确保UI更新
                    target.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    target.dispatchEvent(new Event('change', {{ bubbles: true }}));

                    // 聚焦（如果需要）
                    target.focus();

                    return "成功填充输入框，值: " + target.value.substring(0, 50) + (target.value.length > 50 ? "..." : "");
                }} else {{
                    return "错误: 元素未找到";
                }}
            }} catch (e) {{
                return "JavaScript错误: " + e.toString();
            }}
        }})()
        """

        return self.execute_with_retry(js_code, window_idx, tab_idx, "填充输入框")

    def click_button(
        self, button_text: Optional[str] = None, window_idx: int = 1, tab_idx: int = 1
    ) -> ExecutionResult:
        """
        点击按钮

        Args:
            button_text: 按钮文本（可选，用于更精确的定位）
            window_idx: 窗口索引
            tab_idx: 标签页索引

        Returns:
            ExecutionResult对象
        """
        # 生成按钮查找代码
        if button_text:
            # 根据文本查找按钮
            escaped_text = button_text.replace('"', '\\"').replace("'", "\\'")
            js_code = f"""
            (function() {{
                // 查找包含指定文本的按钮
                var buttons = Array.from(document.querySelectorAll('button, input[type="button"], input[type="submit"], [role="button"]'));
                var target = buttons.find(btn => {{
                    var text = btn.textContent || btn.value || btn.innerText || '';
                    return text.includes("{escaped_text}");
                }});

                if (target) {{
                    target.click();
                    return "成功点击按钮: " + target.textContent;
                }} else {{
                    return "未找到包含文本'{button_text}'的按钮";
                }}
            }})()
            """
            return self.execute_with_retry(js_code, window_idx, tab_idx, "点击按钮")
        else:
            # 使用智能选择器
            js_code = self.selector_strategy.create_smart_query("button")
            result = self.execute_with_retry(js_code, window_idx, tab_idx, "查找按钮")

            if not result.success:
                return result

            try:
                # 解析按钮信息并点击
                output = result.output
                if "JavaScript执行结果: " in output:
                    json_str = output.split("JavaScript执行结果: ", 1)[1]
                else:
                    json_str = output

                data = json.loads(json_str)

                if data.get("success"):
                    # 生成点击代码
                    js_click = f"""
                    (function() {{
                        var elements = document.querySelectorAll("{data['selector']}");
                        if (elements.length > {data['index']}) {{
                            elements[{data['index']}].click();
                            return "成功点击按钮";
                        }} else {{
                            return "按钮未找到";
                        }}
                    }})()
                    """
                    return self.execute_with_retry(js_click, window_idx, tab_idx, "点击按钮")
                else:
                    return ExecutionResult(
                        success=False,
                        output=output,
                        error_type=JavaScriptErrorType.DOM_NOT_FOUND,
                        error_message="未找到可点击的按钮",
                        execution_time=result.execution_time,
                        retry_count=result.retry_count,
                        timestamp=result.timestamp,
                    )

            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"解析按钮信息失败: {e}")
                return ExecutionResult(
                    success=False,
                    output=result.output,
                    error_type=JavaScriptErrorType.UNKNOWN,
                    error_message=f"解析失败: {str(e)}",
                    execution_time=result.execution_time,
                    retry_count=result.retry_count,
                    timestamp=result.timestamp,
                )

    def get_stats(self) -> Dict[str, Any]:
        """获取执行统计"""
        stats = self.execution_stats.copy()
        stats["error_stats"] = {k.value: v for k, v in self.error_stats.items()}

        # 计算平均时间
        if stats["total"] > 0:
            stats["avg_time"] = stats["total_time"] / stats["total"]
        else:
            stats["avg_time"] = 0.0

        # 计算成功率
        if stats["total"] > 0:
            stats["success_rate"] = (stats["success"] / stats["total"]) * 100
        else:
            stats["success_rate"] = 0.0

        return stats

    def _analyze_error(self, error_output: str, js_code: str, context: str) -> Dict:
        """
        分析错误输出

        Args:
            error_output: 错误输出
            js_code: 执行的JavaScript代码
            context: 执行上下文

        Returns:
            错误信息字典
        """
        error_msg = error_output.replace("JavaScript执行错误: ", "")

        # 常见错误模式
        if "syntax error" in error_msg.lower():
            return {
                "type": JavaScriptErrorType.SYNTAX_ERROR,
                "message": f"JavaScript语法错误: {error_msg}",
                "context": context,
            }
        elif "permission" in error_msg.lower() or "不允许" in error_msg:
            return {
                "type": JavaScriptErrorType.PERMISSION_DENIED,
                "message": f"权限错误: {error_msg}",
                "context": context,
            }
        elif "timeout" in error_msg.lower() or "超时" in error_msg:
            return {
                "type": JavaScriptErrorType.TIMEOUT,
                "message": f"执行超时: {error_msg}",
                "context": context,
            }
        elif "not found" in error_msg.lower() or "未找到" in error_msg:
            return {
                "type": JavaScriptErrorType.DOM_NOT_FOUND,
                "message": f"DOM元素未找到: {error_msg}",
                "context": context,
            }
        elif "network" in error_msg.lower() or "网络" in error_msg:
            return {
                "type": JavaScriptErrorType.NETWORK_ERROR,
                "message": f"网络错误: {error_msg}",
                "context": context,
            }
        else:
            return {
                "type": JavaScriptErrorType.UNKNOWN,
                "message": f"未知错误: {error_msg}",
                "context": context,
            }

    def _analyze_exception(self, exception: Exception, js_code: str, context: str) -> Dict:
        """
        分析异常

        Args:
            exception: 异常对象
            js_code: 执行的JavaScript代码
            context: 执行上下文

        Returns:
            错误信息字典
        """
        error_msg = str(exception)

        # 检查AppleScript错误
        if "AppleScript" in error_msg or "262:" in error_msg:
            return {
                "type": JavaScriptErrorType.APPLE_SCRIPT,
                "message": f"AppleScript错误: {error_msg}",
                "context": context,
            }
        elif "timeout" in error_msg.lower():
            return {
                "type": JavaScriptErrorType.TIMEOUT,
                "message": f"超时错误: {error_msg}",
                "context": context,
            }
        else:
            return {
                "type": JavaScriptErrorType.UNKNOWN,
                "message": f"异常: {error_msg}",
                "context": context,
            }

    def _is_retryable_error(self, error_type: JavaScriptErrorType) -> bool:
        """
        判断错误是否可重试

        Args:
            error_type: 错误类型

        Returns:
            是否可重试
        """
        retryable_errors = {
            JavaScriptErrorType.DOM_NOT_FOUND,  # DOM可能还未加载
            JavaScriptErrorType.TIMEOUT,  # 可能是临时性能问题
            JavaScriptErrorType.NETWORK_ERROR,  # 网络问题可能恢复
            JavaScriptErrorType.UNKNOWN,  # 未知错误可重试
        }

        return error_type in retryable_errors

    def _calculate_backoff(self, attempt: int) -> float:
        """
        计算退避时间（指数退避）

        Args:
            attempt: 尝试次数（从0开始）

        Returns:
            等待时间（秒）
        """
        base_delay = 1.0
        max_delay = 10.0
        delay = min(base_delay * (2**attempt) + random.uniform(0, 1), max_delay)
        return delay


# 兼容性包装器
class EnhancedDoubaoCLI:
    """增强版豆包CLI包装器"""

    def __init__(self, doubao_cli_instance):
        """
        初始化

        Args:
            doubao_cli_instance: 豆包CLI实例
        """
        self.doubao = doubao_cli_instance
        self.executor = JavaScriptExecutor(self._execute_js_wrapper)

    def _execute_js_wrapper(self, window_idx: int, tab_idx: int, js_code: str) -> str:
        """包装执行函数"""
        return self.doubao.execute_javascript(window_idx, tab_idx, js_code)

    def execute_javascript(
        self,
        window_idx: int = 1,
        tab_idx: int = 1,
        js_code: str = "document.title",
        use_enhanced: bool = True,
    ) -> str:
        """
        执行JavaScript（增强版）

        Args:
            window_idx: 窗口索引
            tab_idx: 标签页索引
            js_code: JavaScript代码
            use_enhanced: 是否使用增强功能

        Returns:
            执行结果
        """
        if not use_enhanced:
            # 降级到原始方法
            return self.doubao.execute_javascript(window_idx, tab_idx, js_code)

        result = self.executor.execute_with_retry(js_code, window_idx, tab_idx, "自定义JavaScript")

        if result.success:
            return result.output
        else:
            return f"JavaScript执行失败: {result.error_message}"

    def send_message_to_ai(self, message: str, use_enhanced: bool = True) -> str:
        """
        向豆包AI发送消息（增强版）

        Args:
            message: 消息内容
            use_enhanced: 是否使用增强功能

        Returns:
            执行结果
        """
        if not use_enhanced:
            return self.doubao.send_message_to_ai(message)

        # 使用增强功能
        logger.info(f"发送消息到豆包AI: {message[:50]}...")

        # 1. 确保在AI页面
        self.doubao.open_doubao_ai()
        time.sleep(2)  # 等待页面加载

        # 2. 智能查找并填充输入框
        fill_result = self.executor.fill_input(message)

        if not fill_result.success:
            logger.error(f"填充输入框失败: {fill_result.error_message}")
            return f"发送消息失败: {fill_result.error_message}"

        # 3. 查找并点击发送按钮
        click_result = self.executor.click_button("发送")

        if not click_result.success:
            logger.error(f"点击发送按钮失败: {click_result.error_message}")
            # 尝试其他按钮文本
            click_result = self.executor.click_button("Send")

        if click_result.success:
            logger.info("消息发送成功")
            return f"消息发送成功: {message[:50]}..."
        else:
            logger.error(f"发送消息最终失败: {click_result.error_message}")
            return f"发送消息失败: {click_result.error_message}"

    def get_stats(self) -> Dict[str, Any]:
        """获取执行统计"""
        return self.executor.get_stats()


# 测试函数
def test_enhanced_executor():
    """测试增强执行器"""
    print("=== 测试增强JavaScript执行器 ===")

    # 导入豆包CLI
    import os
    import sys

    sys.path.append(os.path.dirname(__file__))

    try:
        from external.ROMA.doubao_cli_prototype import DoubaoCLI

        # 创建实例
        doubao = DoubaoCLI()
        enhanced_doubao = EnhancedDoubaoCLI(doubao)

        print("\n1. 测试基础JavaScript执行...")
        result = enhanced_doubao.execute_javascript(1, 1, "document.title")
        print(f"结果: {result}")

        print("\n2. 测试智能元素查找...")
        element, find_result = enhanced_doubao.executor.find_input_element()
        if element:
            print(f"找到输入元素: {element.selector}")
        else:
            print(f"查找失败: {find_result.error_message}")

        print("\n3. 测试统计功能...")
        stats = enhanced_doubao.get_stats()
        print(f"执行统计: {stats}")

        print("\n=== 测试完成 ===")
        return True

    except Exception as e:
        print(f"测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 运行测试
    if test_enhanced_executor():
        print("\n✅ 增强执行器测试通过")
    else:
        print("\n❌ 增强执行器测试失败")
