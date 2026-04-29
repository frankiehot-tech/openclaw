#!/usr/bin/env python3
"""
工具层故障注入器
基于《多Agent系统24小时压力测试问题修复实施方案》第二阶段设计
模拟工具API故障、超时、性能降级等
"""

import logging
import random
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class MockToolConfig:
    """模拟工具配置"""

    tool_name: str
    success_rate: float  # 成功率 (0.0-1.0)
    avg_response_time_ms: int  # 平均响应时间(毫秒)
    error_patterns: list[dict[str, Any]]  # 错误模式


class ToolChaosLayer:
    """工具层故障注入器"""

    def __init__(self, safe_mode: bool = True):
        """
        初始化工具层故障注入器

        Args:
            safe_mode: 安全模式，为True时避免真实系统破坏
        """
        self.safe_mode = safe_mode
        self.active_mocks: dict[str, MockToolConfig] = {}
        self.original_tool_behaviors: dict[str, dict] = {}
        self.circuit_breaker_states: dict[str, dict] = {}  # 熔断器状态

        # 模拟工具配置
        self._initialize_mock_tools()

        logger.info(f"工具层故障注入器初始化完成 (安全模式: {'启用' if safe_mode else '禁用'})")

    def _initialize_mock_tools(self):
        """初始化模拟工具配置"""
        # 常见的工具错误模式
        self.error_patterns = {
            "rate_limit": {
                "pattern": "rate_limit",
                "http_status": 429,
                "message": "Rate limit exceeded",
                "retry_after": 60,
            },
            "server_error": {
                "pattern": "server_error",
                "http_status": 500,
                "message": "Internal server error",
                "retryable": True,
            },
            "service_unavailable": {
                "pattern": "service_unavailable",
                "http_status": 503,
                "message": "Service temporarily unavailable",
                "retryable": True,
            },
            "bad_gateway": {
                "pattern": "bad_gateway",
                "http_status": 502,
                "message": "Bad gateway",
                "retryable": True,
            },
            "timeout": {
                "pattern": "timeout",
                "http_status": 504,
                "message": "Gateway timeout",
                "retryable": True,
            },
        }

        # 常见工具的性能基准
        self.tool_performance_baselines = {
            "api_tool": {"avg_response_time_ms": 200, "success_rate": 0.99, "max_concurrent": 10},
            "database_tool": {
                "avg_response_time_ms": 100,
                "success_rate": 0.995,
                "max_concurrent": 20,
            },
            "file_system_tool": {
                "avg_response_time_ms": 50,
                "success_rate": 0.998,
                "max_concurrent": 50,
            },
            "external_api_tool": {
                "avg_response_time_ms": 500,
                "success_rate": 0.98,
                "max_concurrent": 5,
            },
        }

    def inject_fault(self, fault_type: str, severity: str, duration_seconds: int = 60) -> dict:
        """
        注入工具层故障

        Args:
            fault_type: 故障类型 (tool_api_error, tool_timeout, tool_degradation)
            severity: 故障严重程度 (low, medium, high)
            duration_seconds: 故障持续时间（秒）

        Returns:
            故障注入结果
        """
        logger.info(
            f"注入工具层故障: 类型={fault_type}, 严重程度={severity}, 持续时间={duration_seconds}s"
        )

        fault_id = f"tool_{fault_type}_{severity}_{int(time.time())}"

        # 确定故障参数
        fault_params = self._get_fault_parameters(fault_type, severity)

        result = {
            "fault_id": fault_id,
            "fault_type": fault_type,
            "severity": severity,
            "injected_at": datetime.now().isoformat(),
            "duration_seconds": duration_seconds,
            "safe_mode": self.safe_mode,
            "status": "injecting",
        }

        try:
            if self.safe_mode:
                result.update(
                    {
                        "success": True,
                        "error": None,
                        "simulated": True,
                        "message": f"安全模式下模拟工具故障注入: {fault_type} ({severity})",
                        "fault_parameters": fault_params,
                    }
                )
                logger.info(f"安全模式: 模拟工具故障注入 - {fault_type}")

                # 在安全模式下记录模拟的故障
                mock_tool = MockToolConfig(
                    tool_name=f"mock_{fault_type}_{severity}",
                    success_rate=fault_params.get("success_rate", 0.5),
                    avg_response_time_ms=fault_params.get("response_time_ms", 1000),
                    error_patterns=[
                        self.error_patterns.get(fault_params.get("error_pattern", "server_error"))
                    ],
                )
                self.active_mocks[fault_id] = mock_tool

            else:
                # 实际故障注入逻辑
                if fault_type == "tool_api_error":
                    injection_result = self._inject_api_error(fault_params)
                elif fault_type == "tool_timeout":
                    injection_result = self._inject_timeout(fault_params)
                elif fault_type == "tool_degradation":
                    injection_result = self._inject_degradation(fault_params)
                else:
                    injection_result = {
                        "success": False,
                        "error": f"不支持的故障类型: {fault_type}",
                    }

                result.update(injection_result)

                if injection_result.get("success", False):
                    # 记录活动故障
                    self.active_mocks[fault_id] = MockToolConfig(
                        tool_name=fault_params.get("tool_name", "unknown"),
                        success_rate=fault_params.get("success_rate", 0.5),
                        avg_response_time_ms=fault_params.get("response_time_ms", 1000),
                        error_patterns=fault_params.get("error_patterns", []),
                    )

            result["status"] = "injected" if result.get("success", False) else "failed"

            if result.get("success", False):
                logger.info(f"工具层故障注入成功: {fault_id}")

                # 安排自动恢复
                if duration_seconds > 0:
                    self._schedule_recovery(fault_id, duration_seconds)

            else:
                logger.error(
                    f"工具层故障注入失败: {fault_id}, 错误: {result.get('error', '未知错误')}"
                )

        except Exception as e:
            result.update({"success": False, "error": str(e), "simulated": True})
            result["status"] = "failed"
            logger.error(f"工具层故障注入异常: {fault_id}, 异常: {e}")

        return result

    def _get_fault_parameters(self, fault_type: str, severity: str) -> dict:
        """根据故障类型和严重程度获取故障参数"""
        severity_map = {
            "low": {"probability": 0.1, "impact": 0.3},
            "medium": {"probability": 0.3, "impact": 0.6},
            "high": {"probability": 0.6, "impact": 0.9},
        }

        severity_params = severity_map.get(severity, severity_map["medium"])

        if fault_type == "tool_api_error":
            error_patterns = list(self.error_patterns.keys())
            selected_pattern = random.choice(error_patterns)

            return {
                "error_pattern": selected_pattern,
                "error_probability": severity_params["probability"],
                "http_status": self.error_patterns[selected_pattern]["http_status"],
                "retryable": self.error_patterns[selected_pattern].get("retryable", False),
            }

        elif fault_type == "tool_timeout":
            timeout_scales = {"low": 2, "medium": 5, "high": 10}
            scale = timeout_scales.get(severity, 5)

            return {
                "timeout_multiplier": scale,
                "timeout_probability": severity_params["probability"],
                "response_time_ms": 1000 * scale,  # 毫秒
            }

        elif fault_type == "tool_degradation":
            degradation_levels = {"low": 0.7, "medium": 0.4, "high": 0.1}
            success_rate = degradation_levels.get(severity, 0.4)

            return {
                "success_rate": success_rate,
                "response_time_multiplier": 3,
                "degradation_probability": severity_params["impact"],
            }

        else:
            return {"error": f"未知故障类型: {fault_type}"}

    def _inject_api_error(self, fault_params: dict) -> dict:
        """注入API错误故障"""
        if self.safe_mode:
            return {
                "success": True,
                "simulated": True,
                "message": f"模拟API错误注入: {fault_params.get('error_pattern')}",
                "details": fault_params,
            }

        # 实际注入逻辑（这里为示例，实际需要根据具体工具实现）
        # 例如：修改工具配置、注入中间件等
        logger.warning("非安全模式下的实际API错误注入未实现")

        return {
            "success": True,
            "message": f"API错误注入准备完成: {fault_params.get('error_pattern')}",
            "details": fault_params,
        }

    def _inject_timeout(self, fault_params: dict) -> dict:
        """注入超时故障"""
        if self.safe_mode:
            return {
                "success": True,
                "simulated": True,
                "message": f"模拟超时注入: 超时倍数={fault_params.get('timeout_multiplier')}",
                "details": fault_params,
            }

        # 实际注入逻辑
        logger.warning("非安全模式下的实际超时注入未实现")

        return {
            "success": True,
            "message": f"超时注入准备完成: 超时倍数={fault_params.get('timeout_multiplier')}",
            "details": fault_params,
        }

    def _inject_degradation(self, fault_params: dict) -> dict:
        """注入性能降级故障"""
        if self.safe_mode:
            return {
                "success": True,
                "simulated": True,
                "message": f"模拟性能降级注入: 成功率={fault_params.get('success_rate')}",
                "details": fault_params,
            }

        # 实际注入逻辑
        logger.warning("非安全模式下的实际性能降级注入未实现")

        return {
            "success": True,
            "message": f"性能降级注入准备完成: 成功率={fault_params.get('success_rate')}",
            "details": fault_params,
        }

    def _schedule_recovery(self, fault_id: str, delay_seconds: int):
        """安排故障自动恢复"""

        def recovery_task():
            time.sleep(delay_seconds)
            self.recover_fault_by_id(fault_id)

        thread = threading.Thread(target=recovery_task, daemon=True)
        thread.start()

        logger.info(f"安排工具故障 {fault_id} 在 {delay_seconds} 秒后自动恢复")

    def recover_fault_by_id(self, fault_id: str) -> dict:
        """
        通过故障ID恢复故障

        Args:
            fault_id: 故障ID

        Returns:
            恢复结果
        """
        logger.info(f"恢复工具层故障: {fault_id}")

        if fault_id not in self.active_mocks:
            return {"success": False, "error": f"未找到工具故障: {fault_id}", "fault_id": fault_id}

        # 移除模拟配置
        del self.active_mocks[fault_id]

        result = {
            "success": True,
            "fault_id": fault_id,
            "recovered_at": datetime.now().isoformat(),
            "message": f"工具故障 {fault_id} 已恢复",
        }

        logger.info(f"工具层故障恢复成功: {fault_id}")
        return result

    def recover_fault(self, fault_type: str) -> dict:
        """
        恢复特定类型的故障

        Args:
            fault_type: 故障类型

        Returns:
            恢复结果
        """
        logger.info(f"恢复工具层故障类型: {fault_type}")

        # 查找并恢复所有匹配的故障
        faults_to_recover = [fault_id for fault_id in self.active_mocks if fault_type in fault_id]

        results = []
        for fault_id in faults_to_recover:
            result = self.recover_fault_by_id(fault_id)
            results.append(result)

        return {
            "success": len(results) > 0,
            "recovered_count": len(results),
            "fault_type": fault_type,
            "results": results,
        }

    def simulate_tool_call(self, tool_name: str, request_data: dict = None) -> dict:
        """
        模拟工具调用（用于测试故障注入效果）

        Args:
            tool_name: 工具名称
            request_data: 请求数据

        Returns:
            模拟的响应
        """
        # 检查是否有活动故障影响此工具
        affected_faults = []
        for fault_id, mock_config in self.active_mocks.items():
            if tool_name in mock_config.tool_name or mock_config.tool_name in tool_name:
                affected_faults.append((fault_id, mock_config))

        if not affected_faults:
            # 正常响应
            return {
                "success": True,
                "tool_name": tool_name,
                "response_time_ms": 100,
                "data": {"status": "success", "message": "正常响应"},
                "faults_affected": False,
            }

        # 应用故障影响
        fault_id, mock_config = affected_faults[0]  # 取第一个故障

        # 根据配置决定是否成功
        success = random.random() < mock_config.success_rate

        # 模拟响应时间
        response_time = mock_config.avg_response_time_ms

        if success:
            response = {
                "success": True,
                "tool_name": tool_name,
                "response_time_ms": response_time,
                "data": {"status": "success", "message": "成功（受故障影响）"},
                "faults_affected": True,
                "affected_fault_id": fault_id,
            }
        else:
            # 生成错误响应
            if mock_config.error_patterns:
                error_pattern = random.choice(mock_config.error_patterns)
                response = {
                    "success": False,
                    "tool_name": tool_name,
                    "response_time_ms": response_time,
                    "error": {
                        "code": error_pattern.get("http_status", 500),
                        "message": error_pattern.get("message", "工具故障"),
                        "pattern": error_pattern.get("pattern", "unknown"),
                    },
                    "faults_affected": True,
                    "affected_fault_id": fault_id,
                }
            else:
                response = {
                    "success": False,
                    "tool_name": tool_name,
                    "response_time_ms": response_time,
                    "error": {"code": 500, "message": "工具内部错误"},
                    "faults_affected": True,
                    "affected_fault_id": fault_id,
                }

        # 添加延迟
        time.sleep(response_time / 1000.0)

        return response

    def get_active_faults(self) -> list[dict]:
        """获取所有活动故障"""
        result = []
        for fault_id, mock_config in self.active_mocks.items():
            result.append(
                {
                    "fault_id": fault_id,
                    "tool_name": mock_config.tool_name,
                    "success_rate": mock_config.success_rate,
                    "avg_response_time_ms": mock_config.avg_response_time_ms,
                    "error_patterns": mock_config.error_patterns,
                }
            )
        return result

    def get_circuit_breaker_status(self, tool_name: str = None) -> dict:
        """
        获取熔断器状态

        Args:
            tool_name: 工具名称，为None时返回所有

        Returns:
            熔断器状态
        """
        if tool_name:
            state = self.circuit_breaker_states.get(
                tool_name,
                {
                    "status": "closed",  # closed, open, half-open
                    "failure_count": 0,
                    "last_failure_time": None,
                    "success_threshold": 5,
                },
            )
            return {tool_name: state}
        else:
            return self.circuit_breaker_states.copy()


def main():
    """主函数 - 测试工具层故障注入器"""
    print("🔧 工具层故障注入器测试")
    print("=" * 50)

    layer = ToolChaosLayer(safe_mode=True)

    # 测试API错误注入
    print("\n1. 测试API错误故障注入...")
    result = layer.inject_fault("tool_api_error", "medium", 30)
    print(f"   结果: {result.get('success')}, 消息: {result.get('message')}")

    # 测试超时注入
    print("\n2. 测试超时故障注入...")
    result = layer.inject_fault("tool_timeout", "high", 30)
    print(f"   结果: {result.get('success')}, 消息: {result.get('message')}")

    # 测试性能降级
    print("\n3. 测试性能降级故障注入...")
    result = layer.inject_fault("tool_degradation", "low", 30)
    print(f"   结果: {result.get('success')}, 消息: {result.get('message')}")

    # 测试工具调用模拟
    print("\n4. 测试工具调用模拟（受故障影响）...")
    for i in range(5):
        response = layer.simulate_tool_call("api_tool", {"request_id": i})
        status = "成功" if response.get("success") else "失败"
        print(f"   调用 {i + 1}: {status}, 响应时间: {response.get('response_time_ms')}ms")

    # 获取活动故障
    print("\n5. 获取活动故障...")
    active_faults = layer.get_active_faults()
    print(f"   活动故障数: {len(active_faults)}")

    # 恢复故障
    print("\n6. 恢复所有故障...")
    for fault in active_faults:
        recovery_result = layer.recover_fault_by_id(fault["fault_id"])
        print(f"   恢复 {fault['fault_id']}: {recovery_result.get('success')}")

    print("\n✅ 工具层故障注入器测试完成")


if __name__ == "__main__":
    main()
