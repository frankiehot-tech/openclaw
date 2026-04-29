#!/usr/bin/env python3
"""
模型层故障注入器
基于《多Agent系统24小时压力测试问题修复实施方案》第二阶段设计
模拟模型响应延迟、输出质量劣化、幻觉生成等故障
"""

import logging
import random
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, StrEnum

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# 定义故障严重程度枚举（临时解决方案）
class FaultSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ModelFaultType(StrEnum):
    """模型故障类型"""

    RESPONSE_DELAY = "response_delay"  # 响应延迟
    OUTPUT_DEGRADATION = "output_degradation"  # 输出质量劣化
    HALLUCINATION = "hallucination"  # 幻觉生成
    CONTEXT_LOSS = "context_loss"  # 上下文丢失
    PARAMETER_DRIFT = "parameter_drift"  # 参数漂移


@dataclass
class HallucinationPattern:
    """幻觉生成模式"""

    pattern_type: str  # "fabrication", "contradiction", "irrelevance", "nonsense"
    severity: float  # 0.0-1.0
    keywords: list[str] = field(default_factory=list)
    templates: list[str] = field(default_factory=list)


@dataclass
class DegradationProfile:
    """性能降级配置"""

    coherence_reduction: float = 0.0  # 连贯性降低 (0.0-1.0)
    relevance_reduction: float = 0.0  # 相关性降低 (0.0-1.0)
    accuracy_reduction: float = 0.0  # 准确性降低 (0.0-1.0)
    fluency_reduction: float = 0.0  # 流畅性降低 (0.0-1.0)


class ModelChaosLayer:
    """模型层故障注入器"""

    def __init__(self, safe_mode: bool = True):
        """
        初始化模型层故障注入器

        Args:
            safe_mode: 安全模式，为True时模拟故障而不实际影响模型
        """
        self.safe_mode = safe_mode
        self.active_faults: dict[str, dict] = {}
        self.original_response_times: dict[str, float] = {}
        self.hallucination_patterns: dict[str, HallucinationPattern] = {}
        self.degradation_profiles: dict[str, DegradationProfile] = {}

        # 初始化幻觉模式
        self._initialize_hallucination_patterns()

        # 初始化降级配置
        self._initialize_degradation_profiles()

        # 记录正常响应时间基准
        self._initialize_response_time_baselines()

        logger.info(f"模型层故障注入器初始化完成 (安全模式: {'启用' if safe_mode else '禁用'})")

    def _initialize_hallucination_patterns(self):
        """初始化幻觉生成模式"""
        self.hallucination_patterns = {
            "fabrication": HallucinationPattern(
                pattern_type="fabrication",
                severity=0.7,
                keywords=["研究表明", "据调查", "专家指出", "最新发现", "数据显示"],
                templates=[
                    "研究表明，{} 会导致 {} 的显著变化。",
                    "据调查显示，{} 与 {} 存在密切关联。",
                    "专家指出，{} 对 {} 有重要影响。",
                ],
            ),
            "contradiction": HallucinationPattern(
                pattern_type="contradiction",
                severity=0.8,
                keywords=["然而", "但是", "相反", "另一方面", "与此相反"],
                templates=[
                    "然而，也有观点认为 {} 实际上会导致 {}。",
                    "但是，最新的研究却显示 {} 与 {} 并无直接关联。",
                    "相反，{} 可能会对 {} 产生负面影响。",
                ],
            ),
            "irrelevance": HallucinationPattern(
                pattern_type="irrelevance",
                severity=0.5,
                keywords=["顺便提一下", "另外", "值得一提的是", "有趣的是"],
                templates=[
                    "顺便提一下，{} 与 {} 之间还有另一个有趣的现象。",
                    "另外，关于 {} 还有一个值得注意的方面。",
                    "有趣的是，{} 在某些情况下可能会影响 {}。",
                ],
            ),
            "nonsense": HallucinationPattern(
                pattern_type="nonsense",
                severity=0.9,
                keywords=["量子纠缠", "超弦理论", "多维空间", "意识场", "能量共振"],
                templates=[
                    "从量子纠缠的角度看，{} 与 {} 之间存在微妙的关联。",
                    "根据超弦理论，{} 可能通过 {} 影响整体系统。",
                    "在多维空间中，{} 和 {} 的相互作用更加复杂。",
                ],
            ),
        }

    def _initialize_degradation_profiles(self):
        """初始化降级配置"""
        self.degradation_profiles = {
            "low": DegradationProfile(
                coherence_reduction=0.1,
                relevance_reduction=0.15,
                accuracy_reduction=0.05,
                fluency_reduction=0.1,
            ),
            "medium": DegradationProfile(
                coherence_reduction=0.3,
                relevance_reduction=0.4,
                accuracy_reduction=0.2,
                fluency_reduction=0.3,
            ),
            "high": DegradationProfile(
                coherence_reduction=0.6,
                relevance_reduction=0.7,
                accuracy_reduction=0.5,
                fluency_reduction=0.6,
            ),
        }

    def _initialize_response_time_baselines(self):
        """初始化响应时间基准"""
        self.original_response_times = {
            "gpt-4": 2.5,  # 秒
            "gpt-3.5": 1.2,  # 秒
            "claude": 3.0,  # 秒
            "llama": 4.0,  # 秒
            "default": 2.0,  # 秒
        }

    def inject_fault(
        self,
        fault_type: ModelFaultType | str,
        severity: FaultSeverity,
        model_name: str = "default",
        duration_seconds: int = 60,
    ) -> dict:
        """
        注入模型故障

        Args:
            fault_type: 故障类型
            severity: 故障严重程度
            model_name: 模型名称
            duration_seconds: 故障持续时间（秒）

        Returns:
            故障注入结果
        """
        fault_type_str = fault_type.value if isinstance(fault_type, ModelFaultType) else fault_type

        logger.info(
            f"注入模型故障: 类型={fault_type_str}, 模型={model_name}, "
            f"严重程度={severity.value}, 持续时间={duration_seconds}s"
        )

        # 构造故障ID
        fault_id = f"model_{fault_type_str}_{severity.value}_{model_name}_{int(time.time())}"

        result = {
            "fault_id": fault_id,
            "layer": "model",
            "fault_type": fault_type_str,
            "model_name": model_name,
            "severity": severity.value,
            "injected_at": datetime.now().isoformat(),
            "duration_seconds": duration_seconds,
            "safe_mode": self.safe_mode,
        }

        try:
            # 根据故障类型执行注入
            if fault_type_str == ModelFaultType.RESPONSE_DELAY:
                fault_result = self._inject_response_delay(severity, model_name)
            elif fault_type_str == ModelFaultType.OUTPUT_DEGRADATION:
                fault_result = self._inject_output_degradation(severity, model_name)
            elif fault_type_str == ModelFaultType.HALLUCINATION:
                fault_result = self._inject_hallucination(severity, model_name)
            elif fault_type_str == ModelFaultType.CONTEXT_LOSS:
                fault_result = self._inject_context_loss(severity, model_name)
            elif fault_type_str == ModelFaultType.PARAMETER_DRIFT:
                fault_result = self._inject_parameter_drift(severity, model_name)
            else:
                fault_result = {
                    "success": False,
                    "error": f"不支持的模型故障类型: {fault_type_str}",
                }

            result.update(fault_result)

            if fault_result.get("success", False):
                # 记录活动故障
                self.active_faults[fault_id] = {
                    "fault_type": fault_type_str,
                    "model_name": model_name,
                    "severity": severity.value,
                    "injected_at": result["injected_at"],
                    "duration_seconds": duration_seconds,
                    "parameters": fault_result.get("parameters", {}),
                }

                # 安排自动恢复
                if duration_seconds > 0:
                    self._schedule_recovery(fault_id, duration_seconds)

                logger.info(f"模型故障注入成功: {fault_id}")
            else:
                logger.error(
                    f"模型故障注入失败: {fault_id}, 错误: {fault_result.get('error', '未知错误')}"
                )

        except Exception as e:
            result.update({"success": False, "error": str(e), "simulated": True})
            logger.error(f"模型故障注入异常: {fault_id}, 异常: {e}")

        return result

    def _inject_response_delay(self, severity: FaultSeverity, model_name: str) -> dict:
        """注入响应延迟故障"""
        # 根据严重程度确定延迟倍数
        delay_multipliers = {
            FaultSeverity.LOW: 2.0,  # 2倍延迟
            FaultSeverity.MEDIUM: 5.0,  # 5倍延迟
            FaultSeverity.HIGH: 10.0,  # 10倍延迟
        }

        multiplier = delay_multipliers.get(severity, 2.0)
        baseline_time = self.original_response_times.get(
            model_name, self.original_response_times["default"]
        )
        new_response_time = baseline_time * multiplier

        result = {
            "success": True,
            "fault_type": "response_delay",
            "model_name": model_name,
            "original_response_time": baseline_time,
            "new_response_time": new_response_time,
            "delay_multiplier": multiplier,
            "parameters": {
                "delay_multiplier": multiplier,
                "baseline_seconds": baseline_time,
                "expected_seconds": new_response_time,
            },
        }

        if self.safe_mode:
            result["simulated"] = True
            result["message"] = (
                f"模拟响应延迟注入: {model_name} 响应时间从{baseline_time}s增加到{new_response_time}s"
            )
        else:
            result["simulated"] = False
            result["message"] = f"响应延迟注入: {model_name} 响应时间已调整"

            # 实际注入逻辑（这里为示例）
            # 例如：调整模型推理参数、限流等

        return result

    def _inject_output_degradation(self, severity: FaultSeverity, model_name: str) -> dict:
        """注入输出质量劣化故障"""
        # 获取降级配置
        severity_str = severity.value.lower()
        degradation = self.degradation_profiles.get(
            severity_str, self.degradation_profiles["medium"]
        )

        # 计算降级后的质量指标
        quality_metrics = {
            "coherence": max(0.0, 1.0 - degradation.coherence_reduction),
            "relevance": max(0.0, 1.0 - degradation.relevance_reduction),
            "accuracy": max(0.0, 1.0 - degradation.accuracy_reduction),
            "fluency": max(0.0, 1.0 - degradation.fluency_reduction),
        }

        result = {
            "success": True,
            "fault_type": "output_degradation",
            "model_name": model_name,
            "quality_metrics": quality_metrics,
            "degradation_profile": {
                "coherence_reduction": degradation.coherence_reduction,
                "relevance_reduction": degradation.relevance_reduction,
                "accuracy_reduction": degradation.accuracy_reduction,
                "fluency_reduction": degradation.fluency_reduction,
            },
            "parameters": {"quality_metrics": quality_metrics},
        }

        if self.safe_mode:
            result["simulated"] = True
            result["message"] = f"模拟输出质量劣化注入: {model_name} 质量指标已降低"
        else:
            result["simulated"] = False
            result["message"] = f"输出质量劣化注入: {model_name} 输出质量已调整"

            # 实际注入逻辑（这里为示例）
            # 例如：调整温度参数、top_p参数等

        return result

    def _inject_hallucination(self, severity: FaultSeverity, model_name: str) -> dict:
        """注入幻觉生成故障"""
        # 根据严重程度选择幻觉模式
        hallucination_probabilities = {
            FaultSeverity.LOW: 0.1,  # 10%概率生成幻觉
            FaultSeverity.MEDIUM: 0.3,  # 30%概率生成幻觉
            FaultSeverity.HIGH: 0.6,  # 60%概率生成幻觉
        }

        probability = hallucination_probabilities.get(severity, 0.3)

        # 选择幻觉模式
        pattern_types = list(self.hallucination_patterns.keys())
        selected_pattern_type = random.choice(pattern_types)
        selected_pattern = self.hallucination_patterns[selected_pattern_type]

        result = {
            "success": True,
            "fault_type": "hallucination",
            "model_name": model_name,
            "hallucination_probability": probability,
            "hallucination_pattern": selected_pattern_type,
            "pattern_severity": selected_pattern.severity,
            "parameters": {
                "probability": probability,
                "pattern_type": selected_pattern_type,
                "keywords": selected_pattern.keywords,
                "templates": selected_pattern.templates,
            },
        }

        if self.safe_mode:
            result["simulated"] = True
            result["message"] = (
                f"模拟幻觉生成注入: {model_name} 幻觉概率={probability}, 模式={selected_pattern_type}"
            )
        else:
            result["simulated"] = False
            result["message"] = f"幻觉生成注入: {model_name} 幻觉机制已激活"

            # 实际注入逻辑（这里为示例）
            # 例如：修改prompt、调整生成参数等

        return result

    def _inject_context_loss(self, severity: FaultSeverity, model_name: str) -> dict:
        """注入上下文丢失故障"""
        # 根据严重程度确定上下文丢失比例
        context_loss_ratios = {
            FaultSeverity.LOW: 0.2,  # 丢失20%上下文
            FaultSeverity.MEDIUM: 0.5,  # 丢失50%上下文
            FaultSeverity.HIGH: 0.8,  # 丢失80%上下文
        }

        loss_ratio = context_loss_ratios.get(severity, 0.5)

        result = {
            "success": True,
            "fault_type": "context_loss",
            "model_name": model_name,
            "context_loss_ratio": loss_ratio,
            "parameters": {"loss_ratio": loss_ratio, "context_window_reduction": loss_ratio},
        }

        if self.safe_mode:
            result["simulated"] = True
            result["message"] = f"模拟上下文丢失注入: {model_name} 上下文丢失比例={loss_ratio}"
        else:
            result["simulated"] = False
            result["message"] = f"上下文丢失注入: {model_name} 上下文处理已受限"

            # 实际注入逻辑（这里为示例）
            # 例如：限制上下文窗口大小、截断历史对话等

        return result

    def _inject_parameter_drift(self, severity: FaultSeverity, model_name: str) -> dict:
        """注入参数漂移故障"""
        # 根据严重程度确定参数漂移程度
        drift_magnitudes = {
            FaultSeverity.LOW: 0.1,  # 10%参数漂移
            FaultSeverity.MEDIUM: 0.3,  # 30%参数漂移
            FaultSeverity.HIGH: 0.5,  # 50%参数漂移
        }

        drift_magnitude = drift_magnitudes.get(severity, 0.3)

        # 模拟参数漂移的影响
        affected_parameters = ["temperature", "top_p", "frequency_penalty", "presence_penalty"]

        result = {
            "success": True,
            "fault_type": "parameter_drift",
            "model_name": model_name,
            "drift_magnitude": drift_magnitude,
            "affected_parameters": affected_parameters,
            "parameters": {
                "drift_magnitude": drift_magnitude,
                "affected_params": affected_parameters,
            },
        }

        if self.safe_mode:
            result["simulated"] = True
            result["message"] = f"模拟参数漂移注入: {model_name} 漂移程度={drift_magnitude}"
        else:
            result["simulated"] = False
            result["message"] = f"参数漂移注入: {model_name} 模型参数已扰动"

            # 实际注入逻辑（这里为示例）
            # 例如：修改模型推理参数、添加噪声等

        return result

    def _schedule_recovery(self, fault_id: str, delay_seconds: int):
        """安排故障自动恢复"""

        def recovery_task():
            time.sleep(delay_seconds)
            self.recover_fault_by_id(fault_id)

        thread = threading.Thread(target=recovery_task, daemon=True)
        thread.start()

        logger.info(f"安排模型故障 {fault_id} 在 {delay_seconds} 秒后自动恢复")

    def recover_fault_by_id(self, fault_id: str) -> dict:
        """
        通过故障ID恢复故障

        Args:
            fault_id: 故障ID

        Returns:
            恢复结果
        """
        logger.info(f"恢复模型层故障: {fault_id}")

        if fault_id not in self.active_faults:
            return {"success": False, "error": f"未找到模型故障: {fault_id}", "fault_id": fault_id}

        # 获取故障信息
        fault_info = self.active_faults[fault_id]
        fault_type = fault_info["fault_type"]
        model_name = fault_info["model_name"]

        # 移除故障记录
        del self.active_faults[fault_id]

        result = {
            "success": True,
            "fault_id": fault_id,
            "fault_type": fault_type,
            "model_name": model_name,
            "recovered_at": datetime.now().isoformat(),
            "message": f"模型故障 {fault_id} 已恢复",
        }

        logger.info(f"模型层故障恢复成功: {fault_id}")
        return result

    def recover_fault(self, fault_type: ModelFaultType | str) -> dict:
        """
        恢复特定类型的故障

        Args:
            fault_type: 故障类型

        Returns:
            恢复结果
        """
        fault_type_str = fault_type.value if isinstance(fault_type, ModelFaultType) else fault_type

        logger.info(f"恢复模型层故障类型: {fault_type_str}")

        # 查找并恢复所有匹配的故障
        faults_to_recover = [
            fault_id
            for fault_id, fault_info in self.active_faults.items()
            if fault_info["fault_type"] == fault_type_str
        ]

        results = []
        for fault_id in faults_to_recover:
            result = self.recover_fault_by_id(fault_id)
            results.append(result)

        return {
            "success": len(results) > 0,
            "recovered_count": len(results),
            "fault_type": fault_type_str,
            "results": results,
        }

    def simulate_model_response(
        self, model_name: str, prompt: str, original_response: str = None
    ) -> dict:
        """
        模拟模型响应（用于测试故障注入效果）

        Args:
            model_name: 模型名称
            prompt: 输入提示
            original_response: 原始响应（如有）

        Returns:
            模拟的响应
        """
        # 检查是否有活动故障影响此模型
        affected_faults = []
        for fault_id, fault_info in self.active_faults.items():
            if fault_info["model_name"] == model_name or model_name in fault_id:
                affected_faults.append((fault_id, fault_info))

        if not affected_faults:
            # 正常响应
            if original_response:
                response = original_response
            else:
                # 生成模拟正常响应
                response = self._generate_normal_response(prompt)

            return {
                "success": True,
                "model_name": model_name,
                "response": response,
                "response_time_seconds": self.original_response_times.get(model_name, 2.0),
                "faults_affected": False,
                "quality_score": 0.95,
            }

        # 应用故障影响
        fault_id, fault_info = affected_faults[0]  # 取第一个故障
        fault_type = fault_info["fault_type"]

        # 根据故障类型处理响应
        if fault_type == ModelFaultType.RESPONSE_DELAY:
            # 应用响应延迟
            delay_params = fault_info.get("parameters", {})
            response_time = delay_params.get(
                "expected_seconds", self.original_response_times.get(model_name, 2.0) * 2
            )

            if original_response:
                response = original_response
            else:
                response = self._generate_normal_response(prompt)

            result = {
                "success": True,
                "model_name": model_name,
                "response": response,
                "response_time_seconds": response_time,
                "faults_affected": True,
                "affected_fault_id": fault_id,
                "fault_type": fault_type,
                "quality_score": 0.8,
            }

        elif fault_type == ModelFaultType.OUTPUT_DEGRADATION:
            # 应用输出质量劣化
            if original_response:
                degraded_response = self._degrade_response(original_response, fault_info)
            else:
                degraded_response = self._generate_degraded_response(prompt, fault_info)

            result = {
                "success": True,
                "model_name": model_name,
                "response": degraded_response,
                "response_time_seconds": self.original_response_times.get(model_name, 2.0),
                "faults_affected": True,
                "affected_fault_id": fault_id,
                "fault_type": fault_type,
                "quality_score": 0.6,
            }

        elif fault_type == ModelFaultType.HALLUCINATION:
            # 应用幻觉生成
            if original_response:
                hallucinated_response = self._add_hallucination(original_response, fault_info)
            else:
                hallucinated_response = self._generate_hallucinated_response(prompt, fault_info)

            result = {
                "success": True,
                "model_name": model_name,
                "response": hallucinated_response,
                "response_time_seconds": self.original_response_times.get(model_name, 2.0),
                "faults_affected": True,
                "affected_fault_id": fault_id,
                "fault_type": fault_type,
                "quality_score": 0.4,
            }

        else:
            # 其他故障类型
            if original_response:
                response = original_response
            else:
                response = self._generate_normal_response(prompt)

            result = {
                "success": True,
                "model_name": model_name,
                "response": response,
                "response_time_seconds": self.original_response_times.get(model_name, 2.0),
                "faults_affected": True,
                "affected_fault_id": fault_id,
                "fault_type": fault_type,
                "quality_score": 0.7,
            }

        # 应用延迟（如果需要）
        if result.get("response_time_seconds", 0) > 0:
            time.sleep(result["response_time_seconds"])

        return result

    def _generate_normal_response(self, prompt: str) -> str:
        """生成正常响应"""
        responses = [
            f"根据您的问题 '{prompt[:50]}...'，我的分析如下：这是一条正常的响应，提供了相关信息和解答。",
            f"关于'{prompt[:40]}...'的问题，我认为需要从多个角度考虑。正常响应的质量较高。",
            f"对于'{prompt[:30]}...'，我的回答是：这是一个经过仔细思考的正常响应。",
        ]
        return random.choice(responses)

    def _degrade_response(self, original_response: str, fault_info: dict) -> str:
        """劣化响应质量"""
        degradation_params = fault_info.get("parameters", {})
        degradation_params.get("quality_metrics", {})

        # 简单模拟劣化：添加语法错误、降低连贯性等
        words = original_response.split()
        if len(words) > 10:
            # 随机替换一些词语
            replace_count = max(1, int(len(words) * 0.1))
            for _ in range(replace_count):
                idx = random.randint(0, len(words) - 1)
                words[idx] = "[模糊词语]"

            # 添加语法错误
            if random.random() < 0.3:
                words.insert(random.randint(0, len(words)), "[语法错误]")

        return " ".join(words)

    def _add_hallucination(self, original_response: str, fault_info: dict) -> str:
        """添加幻觉内容"""
        fault_params = fault_info.get("parameters", {})
        probability = fault_params.get("probability", 0.3)

        if random.random() > probability:
            return original_response

        pattern_type = fault_params.get("pattern_type", "fabrication")
        pattern = self.hallucination_patterns.get(
            pattern_type, self.hallucination_patterns["fabrication"]
        )

        # 选择模板并填充
        template = random.choice(pattern.templates)
        keywords = pattern.keywords

        # 生成幻觉内容
        hallucination = template.format(
            random.choice(keywords) if keywords else "某些因素",
            random.choice(keywords) if keywords else "某些结果",
        )

        # 将幻觉内容插入到响应中
        insert_pos = random.randint(0, max(1, len(original_response) // 2))
        return (
            original_response[:insert_pos]
            + " "
            + hallucination
            + " "
            + original_response[insert_pos:]
        )

    def _generate_hallucinated_response(self, prompt: str, fault_info: dict) -> str:
        """生成包含幻觉的响应"""
        normal_response = self._generate_normal_response(prompt)
        return self._add_hallucination(normal_response, fault_info)

    def _generate_degraded_response(self, prompt: str, fault_info: dict) -> str:
        """生成劣化响应"""
        normal_response = self._generate_normal_response(prompt)
        return self._degrade_response(normal_response, fault_info)

    def get_active_faults(self) -> list[dict]:
        """获取所有活动故障"""
        return [
            {
                "fault_id": fault_id,
                "fault_type": info["fault_type"],
                "model_name": info["model_name"],
                "severity": info["severity"],
                "injected_at": info["injected_at"],
                "duration_seconds": info["duration_seconds"],
                "parameters": info.get("parameters", {}),
            }
            for fault_id, info in self.active_faults.items()
        ]

    def get_model_health_status(self, model_name: str = None) -> dict:
        """
        获取模型健康状态

        Args:
            model_name: 模型名称，为None时返回所有

        Returns:
            健康状态信息
        """
        if model_name:
            # 获取该模型的故障
            model_faults = [
                fault for fault in self.get_active_faults() if fault["model_name"] == model_name
            ]

            health_score = max(0.0, 1.0 - len(model_faults) * 0.2)

            return {
                "model_name": model_name,
                "health_score": health_score,
                "active_faults": len(model_faults),
                "fault_details": model_faults,
                "status": (
                    "healthy"
                    if health_score > 0.7
                    else "degraded"
                    if health_score > 0.4
                    else "unhealthy"
                ),
            }
        else:
            # 返回所有模型的健康状态
            all_models = {fault["model_name"] for fault in self.get_active_faults()}
            if not all_models:
                all_models = {"default"}

            status = {}
            for model in all_models:
                status[model] = self.get_model_health_status(model)

            return status


def test_model_chaos_layer():
    """测试模型层故障注入器"""
    print("🧠 测试模型层故障注入器")
    print("=" * 50)

    # 安全模式测试
    layer = ModelChaosLayer(safe_mode=True)

    # 测试响应延迟注入
    print("\n1. 测试响应延迟故障注入...")
    result = layer.inject_fault(
        fault_type=ModelFaultType.RESPONSE_DELAY,
        severity=FaultSeverity.MEDIUM,
        model_name="gpt-4",
        duration_seconds=30,
    )
    print(
        f"   结果: 成功={result.get('success', False)}, 延迟倍数={result.get('delay_multiplier', 1.0)}"
    )

    # 测试输出质量劣化
    print("\n2. 测试输出质量劣化故障注入...")
    result = layer.inject_fault(
        fault_type=ModelFaultType.OUTPUT_DEGRADATION,
        severity=FaultSeverity.HIGH,
        model_name="claude",
        duration_seconds=30,
    )
    print(
        f"   结果: 成功={result.get('success', False)}, 质量指标={result.get('quality_metrics', {})}"
    )

    # 测试幻觉生成
    print("\n3. 测试幻觉生成故障注入...")
    result = layer.inject_fault(
        fault_type=ModelFaultType.HALLUCINATION,
        severity=FaultSeverity.LOW,
        model_name="llama",
        duration_seconds=30,
    )
    print(
        f"   结果: 成功={result.get('success', False)}, 幻觉概率={result.get('hallucination_probability', 0)}"
    )

    # 测试模型响应模拟
    print("\n4. 测试模型响应模拟（受故障影响）...")
    for i in range(3):
        prompt = f"测试问题 {i + 1}: 请解释人工智能的基本原理"
        response = layer.simulate_model_response("gpt-4", prompt)
        quality = response.get("quality_score", 0)
        print(
            f"   响应 {i + 1}: 质量评分={quality:.2f}, 受影响={response.get('faults_affected', False)}"
        )

    # 获取活动故障
    print("\n5. 获取活动故障...")
    active_faults = layer.get_active_faults()
    print(f"   活动故障数: {len(active_faults)}")

    # 获取模型健康状态
    print("\n6. 获取模型健康状态...")
    health_status = layer.get_model_health_status()
    for model, status in health_status.items():
        print(
            f"   {model}: 健康评分={status.get('health_score', 0):.2f}, 状态={status.get('status', 'unknown')}"
        )

    # 恢复故障
    print("\n7. 恢复所有故障...")
    for fault in active_faults:
        recovery_result = layer.recover_fault_by_id(fault["fault_id"])
        print(f"   恢复 {fault['fault_id']}: {recovery_result.get('success')}")

    print("\n✅ 模型层故障注入器测试完成")


if __name__ == "__main__":
    test_model_chaos_layer()
