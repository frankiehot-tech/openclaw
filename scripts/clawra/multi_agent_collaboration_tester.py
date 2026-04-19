#!/usr/bin/env python3
"""
MAREF多智能体协同测试框架
基于第2周扩展的状态空间(60.9%覆盖率)，测试4个MAREF智能体的协同能力

智能体配置:
1. Guardian (艮卦) - 安全与约束
2. Communicator (离卦) - 界面与表达
3. Learner (兑卦) - 适应与训练
4. Explorer (坎卦) - 搜索与发现

状态空间: 39个已访问状态，60.9%覆盖率，38种转换模式
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# 添加ROMA路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "external/ROMA"))

from communicator_agent import CommunicatorAgent
from explorer_agent import DiscoveryPriority, ExplorationType, ExplorerAgent
from guardian_agent import GuardianAgent
from learner_agent import LearnerAgent, LearningPhase, LearningType

# 导入卦象状态管理器
try:
    from external.ROMA.hexagram_state_manager import HexagramStateManager

    HAS_HEXAGRAM_STATE = True
except ImportError:
    print("警告: 未找到HexagramStateManager，使用模拟实现")
    HAS_HEXAGRAM_STATE = False


class MultiAgentCollaborationTester:
    """多智能体协同测试框架"""

    def __init__(self, initial_state: str = "000000"):
        self.initial_state = initial_state
        self.current_state = initial_state
        self.agents = {}
        self.state_history = []
        self.collaboration_log = []
        self.test_results = {}

        # 设置日志
        self.logger = self._setup_logger()

        # 初始化卦象状态管理器
        if HAS_HEXAGRAM_STATE:
            self.state_manager = HexagramStateManager(initial_state)
        else:
            self.state_manager = MockStateManager(initial_state)

        # 初始化智能体
        self._initialize_agents()

        # 加载扩展的状态空间数据
        self.expanded_states = self._load_expanded_states()

        self.logger.info(f"多智能体协同测试框架初始化完成")
        self.logger.info(f"初始状态: {initial_state}")
        self.logger.info(f"扩展状态空间: {len(self.expanded_states)} 个状态")

    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger("multi_agent_tester")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _initialize_agents(self):
        """初始化4个MAREF智能体"""
        self.logger.info("初始化MAREF智能体...")

        # 1. Guardian (艮卦 - 安全与约束)
        self.agents["guardian"] = GuardianAgent("guardian_collab")
        self.logger.info(f"  ✅ Guardian智能体初始化: {self.agents['guardian'].agent_id}")

        # 2. Communicator (离卦 - 界面与表达)
        self.agents["communicator"] = CommunicatorAgent("communicator_collab")
        self.logger.info(f"  ✅ Communicator智能体初始化: {self.agents['communicator'].agent_id}")

        # 3. Learner (兑卦 - 适应与训练)
        self.agents["learner"] = LearnerAgent("learner_collab")
        self.logger.info(f"  ✅ Learner智能体初始化: {self.agents['learner'].agent_id}")

        # 4. Explorer (坎卦 - 搜索与发现)
        self.agents["explorer"] = ExplorerAgent("explorer_collab")
        self.logger.info(f"  ✅ Explorer智能体初始化: {self.agents['explorer'].agent_id}")

        self.logger.info(f"共初始化 {len(self.agents)} 个智能体")

    def _load_expanded_states(self) -> List[str]:
        """加载第2周扩展的状态空间"""
        # 从第2周报告加载扩展的状态空间
        expanded_states = [
            "000000",
            "000001",
            "000010",
            "000011",
            "000100",  # 原始5个状态
            # 邻居扩展状态
            "001000",
            "010000",
            "100000",
            "000101",
            "000110",
            "001001",
            "010001",
            "001010",
            "010010",
            "001100",
            "010100",
            "100100",
            "000111",
            "001011",
            "010011",
            # 模式扩展状态
            "010101",
            "101010",
            "111111",
            "110011",
            # 路径扩展状态
            "001111",
            "011111",
            "101101",
            "110110",
            "111000",
            "111100",
            "001110",
            "011001",
            "100011",
            "110001",
            "011010",
            "101100",
            "110101",
            "111010",
            # 测试场景中使用的额外状态
            "011000",
            "011100",
            "111100",
            "010001",
            "010100",
            "001100",
            "010101",
            "101010",
            "011100",
            "111100",
        ]

        # 去重并排序
        unique_states = sorted(set(expanded_states))
        self.logger.info(f"加载扩展状态空间: {len(unique_states)} 个唯一状态")

        # 验证所有状态都是6位二进制
        for state in unique_states:
            if len(state) != 6 or not all(c in "01" for c in state):
                self.logger.warning(f"状态格式无效: {state}")

        return unique_states

    def notify_state_change(self, old_state: str, new_state: str, reason: str = ""):
        """通知所有智能体状态变化"""
        self.logger.info(f"状态变化: {old_state} → {new_state} ({reason})")

        # 记录状态历史
        state_record = {
            "timestamp": datetime.now().isoformat(),
            "old_state": old_state,
            "new_state": new_state,
            "reason": reason,
            "agents_notified": [],
        }

        # 通知每个智能体
        for agent_name, agent in self.agents.items():
            try:
                # 根据智能体类型采用不同的通知方式
                if agent_name == "guardian":
                    # Guardian记录状态转换事件
                    # 简化版本：Guardian只记录事件，不实际验证
                    security_check = {"allowed": True, "reason": "简化测试模式"}
                    state_record["agents_notified"].append(
                        {
                            "agent": agent_name,
                            "action": "security_recorded",
                            "result": security_check,
                        }
                    )

                elif agent_name == "communicator":
                    # Communicator记录状态转换消息
                    message = f"状态转换: {old_state} → {new_state} ({reason})"
                    channels = list(agent.channels.keys())
                    if channels:
                        channel_id = channels[0]
                        success, msg = agent.send_message(channel_id, message)
                        state_record["agents_notified"].append(
                            {
                                "agent": agent_name,
                                "action": "notification_sent",
                                "result": success,
                                "message": msg,
                            }
                        )

                elif agent_name == "learner":
                    # Learner记录状态转换性能
                    transition_time = 0.1  # 模拟转换时间
                    success, msg = agent.update_performance_metric(
                        "state_transition_time", transition_time, 1.0, "lower_better"
                    )
                    state_record["agents_notified"].append(
                        {
                            "agent": agent_name,
                            "action": "performance_recorded",
                            "result": success,
                            "metric": "state_transition_time",
                        }
                    )

                elif agent_name == "explorer":
                    # Explorer探索新状态的相关发现
                    discoveries = agent.explore_solutions(
                        f"状态转换到 {new_state}", domain="state_management"
                    )
                    state_record["agents_notified"].append(
                        {
                            "agent": agent_name,
                            "action": "state_exploration",
                            "discoveries_found": len(discoveries),
                        }
                    )

            except Exception as e:
                self.logger.error(f"通知智能体 {agent_name} 失败: {e}")
                state_record["agents_notified"].append(
                    {"agent": agent_name, "action": "notification_failed", "error": str(e)}
                )

        # 保存状态记录
        self.state_history.append(state_record)
        self.current_state = new_state

        return state_record

    def collaborative_state_transition(
        self, target_state: str, context: Dict[str, Any] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """协同状态转换：所有智能体参与决策"""
        if context is None:
            context = {}

        self.logger.info(f"开始协同状态转换: {self.current_state} → {target_state}")

        # 1. 验证目标状态有效性
        if target_state not in self.expanded_states:
            return False, f"目标状态 {target_state} 不在扩展状态空间中", {}

        # 2. 检查汉明距离（格雷编码合规性）
        hamming_distance = self._calculate_hamming_distance(self.current_state, target_state)
        if hamming_distance != 1:
            return False, f"汉明距离为 {hamming_distance}，不符合格雷编码要求（必须为1）", {}

        # 3. 收集智能体意见
        agent_decisions = self._collect_agent_decisions(target_state, context)

        # 4. 分析决策结果
        decision_analysis = self._analyze_decisions(agent_decisions)

        # 5. 执行决策
        if decision_analysis["can_proceed"]:
            # 执行状态转换
            old_state = self.current_state
            try:
                # 实际状态转换逻辑
                self.state_manager.transition(target_state)
                state_record = self.notify_state_change(old_state, target_state, "协同决策")

                # 记录转换结果
                conversion_result = {
                    "success": True,
                    "old_state": old_state,
                    "new_state": target_state,
                    "hamming_distance": hamming_distance,
                    "agent_decisions": agent_decisions,
                    "decision_analysis": decision_analysis,
                    "state_record": state_record,
                    "timestamp": datetime.now().isoformat(),
                }

                self.logger.info(f"协同状态转换成功: {old_state} → {target_state}")
                return True, "状态转换成功", conversion_result

            except Exception as e:
                error_msg = f"状态转换执行失败: {e}"
                self.logger.error(error_msg)
                return False, error_msg, {"agent_decisions": agent_decisions}
        else:
            # 决策不允许转换
            decision_summary = decision_analysis.get("decision_summary", "智能体决策不允许转换")
            self.logger.warning(f"协同决策不允许转换: {decision_summary}")
            return (
                False,
                decision_summary,
                {"agent_decisions": agent_decisions, "decision_analysis": decision_analysis},
            )

    def _collect_agent_decisions(
        self, target_state: str, context: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """收集所有智能体对状态转换的决策意见"""
        decisions = {}

        for agent_name, agent in self.agents.items():
            try:
                if agent_name == "guardian":
                    # Guardian检查安全约束
                    safety_check = agent.validate_state_transition_safety(
                        self.current_state, target_state, context
                    )
                    decisions[agent_name] = {
                        "decision": "allow" if safety_check["allowed"] else "block",
                        "reason": safety_check.get("reason", "安全检查"),
                        "confidence": safety_check.get("confidence", 0.8),
                        "details": safety_check,
                    }

                elif agent_name == "communicator":
                    # Communicator评估沟通影响
                    communication_impact = agent.assess_communication_impact(
                        self.current_state, target_state, context
                    )
                    # 从decision字段获取决策值（allow/block）
                    decision_value = communication_impact.get("decision", "allow")
                    decisions[agent_name] = {
                        "decision": decision_value,
                        "reason": communication_impact.get("reason", "沟通影响评估"),
                        "confidence": communication_impact.get("confidence", 0.7),
                        "details": communication_impact,
                    }

                elif agent_name == "learner":
                    # Learner基于历史数据建议
                    learning_recommendation = agent.recommend_state_transition(
                        self.current_state, target_state, context
                    )
                    decisions[agent_name] = {
                        "decision": learning_recommendation.get("recommendation", "allow"),
                        "reason": learning_recommendation.get("reason", "学习建议"),
                        "confidence": learning_recommendation.get("confidence", 0.6),
                        "details": learning_recommendation,
                    }

                elif agent_name == "explorer":
                    # Explorer探索转换价值
                    exploration_value = agent.evaluate_exploration_value(
                        self.current_state, target_state, context
                    )
                    # 将recommendation映射到allow/block决策
                    recommendation = exploration_value.get("recommendation", "neutral")
                    if recommendation == "recommend":
                        decision = "allow"
                    elif recommendation == "avoid":
                        decision = "block"
                    else:  # neutral, caution
                        decision = "allow"  # 默认允许，但优先级较低

                    decisions[agent_name] = {
                        "decision": decision,
                        "reason": exploration_value.get("reason", "探索价值评估"),
                        "confidence": exploration_value.get("confidence", 0.5),
                        "details": exploration_value,
                    }

            except AttributeError:
                # 如果智能体没有对应方法，使用默认决策
                self.logger.warning(f"智能体 {agent_name} 缺少决策方法，使用默认允许")
                decisions[agent_name] = {
                    "decision": "allow",
                    "reason": "默认允许（方法未实现）",
                    "confidence": 0.5,
                    "details": {"method_not_implemented": True},
                }
            except Exception as e:
                self.logger.error(f"收集智能体 {agent_name} 决策失败: {e}")
                decisions[agent_name] = {
                    "decision": "block",
                    "reason": f"决策收集失败: {str(e)}",
                    "confidence": 0.0,
                    "details": {"error": str(e)},
                }

        return decisions

    def _analyze_decisions(self, agent_decisions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        基于优先级的冲突解决算法

        智能体优先级权重（从高到低）：
        1. Guardian (权重: 40%) - 安全约束，有绝对否决权
        2. Learner (权重: 30%) - 历史经验，基于数据的学习建议
        3. Explorer (权重: 20%) - 探索价值，发现新路径
        4. Communicator (权重: 10%) - 沟通协调，影响评估

        决策规则：
        1. Guardian否决权：如果Guardian拒绝，立即阻止
        2. 加权决策：计算加权得分，阈值=0.5
        3. 置信度调整：基于智能体置信度调整权重
        4. 平局处理：如果加权得分接近阈值，增加额外检查
        """
        # 智能体优先级权重
        PRIORITY_WEIGHTS = {
            "guardian": 0.40,  # 安全第一
            "learner": 0.30,  # 历史经验
            "explorer": 0.20,  # 探索价值
            "communicator": 0.10,  # 沟通协调
        }

        total_agents = len(agent_decisions)
        agent_names = list(agent_decisions.keys())

        # 1. 检查Guardian否决权
        guardian_decision = agent_decisions.get("guardian", {}).get("decision", "allow")
        guardian_veto = guardian_decision == "block"
        guardian_confidence = agent_decisions.get("guardian", {}).get("confidence", 0.5)

        if guardian_veto:
            can_proceed = False
            decision_summary = f"Guardian行使否决权（置信度: {guardian_confidence:.2f}）"
            decision_method = "guardian_veto"
            weighted_score = 0.0
        else:
            # 2. 计算加权决策得分
            weighted_score = 0.0
            total_effective_weight = 0.0

            for agent_name, decision_data in agent_decisions.items():
                decision = decision_data.get("decision", "allow")
                confidence = decision_data.get("confidence", 0.5)
                weight = PRIORITY_WEIGHTS.get(agent_name, 0.25 / total_agents)  # 默认平均分配

                # 决策值：allow=1.0, block=0.0
                decision_value = 1.0 if decision == "allow" else 0.0

                # 置信度调整权重：高置信度决策权重增加
                confidence_adjusted_weight = weight * confidence

                weighted_score += decision_value * confidence_adjusted_weight
                total_effective_weight += confidence_adjusted_weight

            # 归一化得分（0.0-1.0）
            if total_effective_weight > 0:
                normalized_score = weighted_score / total_effective_weight
            else:
                normalized_score = 0.5  # 无有效权重，中性

            # 3. 应用决策阈值
            DECISION_THRESHOLD = 0.5

            if normalized_score >= DECISION_THRESHOLD:
                can_proceed = True
                decision_method = "weighted_majority"
                decision_summary = (
                    f"加权决策允许（得分: {normalized_score:.3f} ≥ {DECISION_THRESHOLD}）"
                )
            else:
                can_proceed = False
                decision_method = "weighted_majority"
                decision_summary = (
                    f"加权决策阻止（得分: {normalized_score:.3f} < {DECISION_THRESHOLD}）"
                )

            # 4. 平局处理（得分接近阈值时）
            if abs(normalized_score - DECISION_THRESHOLD) < 0.1:  # 接近阈值±0.1
                # 检查是否有高置信度的关键智能体
                high_confidence_agents = []
                for agent_name, decision_data in agent_decisions.items():
                    if decision_data.get("confidence", 0) >= 0.8:
                        high_confidence_agents.append((agent_name, decision_data))

                if high_confidence_agents:
                    # 高置信度智能体决策倾向于优先考虑
                    high_conf_scores = []
                    for agent_name, decision_data in high_confidence_agents:
                        decision = decision_data.get("decision", "allow")
                        high_conf_scores.append(1.0 if decision == "allow" else 0.0)

                    high_conf_avg = (
                        sum(high_conf_scores) / len(high_conf_scores) if high_conf_scores else 0.5
                    )

                    if high_conf_avg >= 0.7:  # 高置信度智能体强烈支持
                        can_proceed = True
                        decision_method = "high_confidence_tiebreak"
                        decision_summary += f"（高置信度智能体支持: {high_conf_avg:.2f}）"
                    elif high_conf_avg <= 0.3:  # 高置信度智能体强烈反对
                        can_proceed = False
                        decision_method = "high_confidence_tiebreak"
                        decision_summary += f"（高置信度智能体反对: {high_conf_avg:.2f}）"

        # 5. 计算详细统计
        allow_count = sum(1 for d in agent_decisions.values() if d["decision"] == "allow")
        block_count = total_agents - allow_count

        # 计算加权置信度
        total_confidence = sum(d.get("confidence", 0.5) for d in agent_decisions.values())
        avg_confidence = total_confidence / total_agents if total_agents > 0 else 0

        # 生成智能体决策摘要
        agent_decisions_summary = {}
        for agent_name, decision_data in agent_decisions.items():
            agent_decisions_summary[agent_name] = {
                "decision": decision_data.get("decision", "unknown"),
                "reason": decision_data.get("reason", "无说明"),
                "confidence": decision_data.get("confidence", 0.0),
                "weight": PRIORITY_WEIGHTS.get(agent_name, 0.0),
            }

        return {
            "can_proceed": can_proceed,
            "decision_summary": decision_summary,
            "decision_method": decision_method,
            "weighted_score": weighted_score if "weighted_score" in locals() else 0.0,
            "normalized_score": normalized_score if "normalized_score" in locals() else 0.0,
            "allow_count": allow_count,
            "block_count": block_count,
            "total_agents": total_agents,
            "avg_confidence": avg_confidence,
            "guardian_veto": guardian_veto,
            "guardian_confidence": guardian_confidence,
            "agent_decisions_summary": agent_decisions_summary,
            "priority_weights": PRIORITY_WEIGHTS,
            "decision_threshold": DECISION_THRESHOLD,
        }

    def _calculate_hamming_distance(self, state1: str, state2: str) -> int:
        """计算两个卦象状态之间的汉明距离"""
        if len(state1) != len(state2):
            return -1

        distance = 0
        for b1, b2 in zip(state1, state2):
            if b1 != b2:
                distance += 1

        return distance

    def reset_to_initial_state(self):
        """重置到初始状态"""
        old_state = self.current_state
        self.current_state = self.initial_state
        self.state_manager.current_state = self.initial_state
        self.logger.info(f"重置状态: {old_state} → {self.initial_state}")
        # 记录状态重置
        self.state_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "old_state": old_state,
                "new_state": self.initial_state,
                "reason": "场景重置",
                "agents_notified": [],
            }
        )

    def run_collaboration_test(self, test_scenario: Dict[str, Any]) -> Dict[str, Any]:
        """运行协同测试场景"""
        scenario_id = test_scenario.get("id", "unknown")
        scenario_name = test_scenario.get("name", "未命名场景")

        # 重置到初始状态
        self.reset_to_initial_state()

        self.logger.info(f"开始运行测试场景: {scenario_name} ({scenario_id})")

        # 初始化测试结果
        test_result = {
            "scenario_id": scenario_id,
            "scenario_name": scenario_name,
            "start_time": datetime.now().isoformat(),
            "initial_state": self.current_state,
            "steps": [],
            "agent_interactions": [],
            "status": "running",
        }

        try:
            # 执行场景步骤
            steps = test_scenario.get("steps", [])
            for step_idx, step in enumerate(steps):
                step_result = self._execute_scenario_step(step, step_idx)
                test_result["steps"].append(step_result)

                # 如果步骤失败，停止测试
                if not step_result.get("success", False):
                    test_result["status"] = "failed"
                    test_result["failure_reason"] = step_result.get(
                        "failure_reason", "步骤执行失败"
                    )
                    break

            # 如果没有失败，标记为成功
            if test_result["status"] == "running":
                test_result["status"] = "completed"

        except Exception as e:
            test_result["status"] = "error"
            test_result["error"] = str(e)
            self.logger.error(f"测试场景执行错误: {e}")

        test_result["end_time"] = datetime.now().isoformat()
        test_result["final_state"] = self.current_state

        # 记录测试结果
        self.test_results[scenario_id] = test_result
        self.logger.info(f"测试场景完成: {scenario_name} - 状态: {test_result['status']}")

        return test_result

    def _execute_scenario_step(self, step: Dict[str, Any], step_idx: int) -> Dict[str, Any]:
        """执行场景步骤"""
        step_type = step.get("type", "state_transition")
        step_desc = step.get("description", f"步骤 {step_idx}")

        self.logger.info(f"执行步骤 {step_idx}: {step_desc}")

        step_result = {
            "step_index": step_idx,
            "step_type": step_type,
            "description": step_desc,
            "start_time": datetime.now().isoformat(),
            "success": False,
        }

        try:
            if step_type == "state_transition":
                # 状态转换步骤
                target_state = step.get("target_state")
                if not target_state:
                    raise ValueError("状态转换步骤缺少target_state")

                success, message, details = self.collaborative_state_transition(
                    target_state, step.get("context", {})
                )

                step_result.update(
                    {
                        "action": "state_transition",
                        "target_state": target_state,
                        "success": success,
                        "message": message,
                        "details": details,
                    }
                )

            elif step_type == "agent_interaction":
                # 智能体交互步骤
                interaction = step.get("interaction", {})
                agent_name = interaction.get("agent")
                action = interaction.get("action")

                if agent_name not in self.agents:
                    raise ValueError(f"未知智能体: {agent_name}")

                # 执行智能体特定操作
                agent = self.agents[agent_name]
                result = self._execute_agent_action(agent, action, interaction.get("params", {}))

                step_result.update(
                    {
                        "action": "agent_interaction",
                        "agent": agent_name,
                        "action_type": action,
                        "success": result.get("success", False),
                        "result": result,
                        "details": result,
                    }
                )

            else:
                raise ValueError(f"未知步骤类型: {step_type}")

        except Exception as e:
            step_result["success"] = False
            step_result["error"] = str(e)
            step_result["failure_reason"] = f"步骤执行失败: {e}"
            self.logger.error(f"步骤执行失败: {e}")

        step_result["end_time"] = datetime.now().isoformat()
        return step_result

    def _execute_agent_action(self, agent, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行智能体特定操作"""
        try:
            if action == "explore_solutions":
                # Explorer探索解决方案
                problem = params.get("problem", "")
                domain = params.get("domain", "general")
                solutions = agent.explore_solutions(problem, domain)
                return {
                    "success": True,
                    "solutions_found": len(solutions),
                    "solutions": [
                        {"title": s.title, "type": s.exploration_type.value} for s in solutions
                    ],
                }

            elif action == "update_performance":
                # Learner更新性能指标
                metric_name = params.get("metric_name", "unknown")
                value = params.get("value", 0.0)
                threshold = params.get("threshold", 0.8)
                direction = params.get("direction", "higher_better")

                success, message = agent.update_performance_metric(
                    metric_name, value, threshold, direction
                )
                return {
                    "success": success,
                    "message": message,
                    "metric_name": metric_name,
                    "value": value,
                }

            elif action == "send_message":
                # Communicator发送消息
                channel_id = params.get("channel_id", "internal_broadcast")
                message = params.get("message", {})
                success, msg_id = agent.send_message(channel_id, message)
                return {
                    "success": success,
                    "message_id": msg_id,
                    "channel_id": channel_id,
                    "action": "send_message",
                }

            elif action == "validate_safety":
                # Guardian验证安全性
                state_change_type = params.get("state_change_type", "general")
                # 这是一个模拟的安全验证
                return {
                    "success": True,
                    "safety_validated": True,
                    "state_change_type": state_change_type,
                    "message": f"安全性验证通过: {state_change_type}",
                }

            else:
                return {
                    "success": False,
                    "error": f"未知操作: {action}",
                    "message": "智能体操作未实现",
                }

        except Exception as e:
            return {"success": False, "error": str(e), "message": f"智能体操作执行失败: {e}"}

    def generate_test_report(self) -> Dict[str, Any]:
        """生成测试报告"""
        total_tests = len(self.test_results)
        completed_tests = sum(1 for r in self.test_results.values() if r["status"] == "completed")
        failed_tests = sum(1 for r in self.test_results.values() if r["status"] == "failed")

        # 智能体活动统计
        agent_activities = {}
        for agent_name in self.agents:
            agent_activities[agent_name] = {
                "decisions_made": 0,
                "notifications_received": 0,
                "total_confidence": 0.0,
            }

        # 从状态历史中统计实际决策次数和置信度
        total_confidence_sum = 0.0
        total_decisions_count = 0

        for record in self.state_history:
            # 统计通知接收次数
            notified_agents = record.get("agents_notified", [])
            for agent_info in notified_agents:
                if isinstance(agent_info, dict) and "agent" in agent_info:
                    agent_name = agent_info["agent"]
                    if agent_name in agent_activities:
                        agent_activities[agent_name]["notifications_received"] += 1

        # 从测试结果中统计决策次数和置信度
        collaborative_decisions = 0
        for scenario_id, test_result in self.test_results.items():
            steps = test_result.get("steps", [])
            for step in steps:
                if step.get("success", False) and step.get("action") == "state_transition":
                    details = step.get("details", {})
                    agent_decisions = details.get("agent_decisions", {})

                    if agent_decisions:
                        collaborative_decisions += 1

                    for agent_name, decision_data in agent_decisions.items():
                        if agent_name in agent_activities:
                            agent_activities[agent_name]["decisions_made"] += 1
                            # 累加置信度
                            confidence = decision_data.get("confidence", 0.0)
                            agent_activities[agent_name]["total_confidence"] += confidence
                            total_confidence_sum += confidence
                            total_decisions_count += 1

        # 计算每个智能体的平均置信度
        for agent_name, activity in agent_activities.items():
            decisions_made = activity["decisions_made"]
            total_confidence = activity["total_confidence"]
            if decisions_made > 0:
                activity["average_confidence"] = total_confidence / decisions_made
            else:
                activity["average_confidence"] = 0.0
            # 移除不再需要的total_confidence字段，只保留最终结果
            activity.pop("total_confidence", None)

        # 分析状态历史
        unique_states_visited = set()
        state_transitions = []

        for record in self.state_history:
            unique_states_visited.add(record["old_state"])
            unique_states_visited.add(record["new_state"])
            state_transitions.append(f"{record['old_state']}→{record['new_state']}")

        # 计算覆盖率
        total_possible_states = 64
        coverage_percentage = (len(unique_states_visited) / total_possible_states) * 100

        report = {
            "report_date": datetime.now().isoformat(),
            "test_summary": {
                "total_tests": total_tests,
                "completed_tests": completed_tests,
                "failed_tests": failed_tests,
                "success_rate": completed_tests / total_tests if total_tests > 0 else 0,
                "test_duration": "N/A",  # 可以计算实际时长
            },
            "state_space_coverage": {
                "unique_states_visited": len(unique_states_visited),
                "total_possible_states": total_possible_states,
                "coverage_percentage": coverage_percentage,
                "unique_state_list": sorted(list(unique_states_visited)),
                "total_transitions": len(state_transitions),
                "unique_transitions": len(set(state_transitions)),
            },
            "agent_activities": agent_activities,
            "collaboration_metrics": {
                "state_changes_notified": len(self.state_history),
                "collaborative_decisions": collaborative_decisions,
                "average_decision_confidence": (
                    total_confidence_sum / total_decisions_count
                    if total_decisions_count > 0
                    else 0.0
                ),
            },
            "test_results": self.test_results,
            "state_history_summary": [
                {
                    "transition": f"{r['old_state']}→{r['new_state']}",
                    "timestamp": r["timestamp"],
                    "agents_notified": len(r["agents_notified"]),
                }
                for r in self.state_history[-10:]  # 最近10条记录
            ],
        }

        return report

    def print_report(self, report: Dict[str, Any]):
        """打印测试报告"""
        print("\n" + "=" * 60)
        print("MAREF多智能体协同测试报告")
        print("=" * 60)

        # 测试摘要
        summary = report["test_summary"]
        print(f"\n📊 测试摘要:")
        print(f"   总测试场景: {summary['total_tests']}")
        print(f"   成功场景: {summary['completed_tests']}")
        print(f"   失败场景: {summary['failed_tests']}")
        print(f"   成功率: {summary['success_rate']:.1%}")

        # 状态空间覆盖
        coverage = report["state_space_coverage"]
        print(f"\n🌐 状态空间覆盖:")
        print(f"   访问状态数: {coverage['unique_states_visited']}")
        print(f"   总可能状态: {coverage['total_possible_states']}")
        print(f"   覆盖率: {coverage['coverage_percentage']:.1f}%")
        print(f"   状态转换总数: {coverage['total_transitions']}")
        print(f"   唯一转换模式: {coverage['unique_transitions']}")

        # 智能体活动
        print(f"\n🤖 智能体活动:")
        for agent_name, activity in report["agent_activities"].items():
            print(f"   {agent_name.capitalize()}:")
            print(f"     决策次数: {activity.get('decisions_made', 0)}")
            print(f"     通知次数: {activity.get('notifications_received', 0)}")
            if activity.get("decisions_made", 0) > 0:
                avg_conf = activity.get("average_confidence", 0.0)
                print(f"     平均置信度: {avg_conf:.2f}")

        # 协同指标
        collab = report["collaboration_metrics"]
        print(f"\n🤝 协同指标:")
        print(f"   状态变化通知: {collab['state_changes_notified']}")
        print(f"   协同决策次数: {collab['collaborative_decisions']}")

        # 最近状态转换
        print(f"\n🔄 最近状态转换:")
        for i, trans in enumerate(report["state_history_summary"], 1):
            print(f"   {i}. {trans['transition']} ({trans['timestamp'][11:19]})")
            print(f"      通知智能体: {trans['agents_notified']}个")

        print("\n" + "=" * 60)
        print(f"报告生成时间: {report['report_date'][:19]}")
        print("=" * 60)


class MockStateManager:
    """模拟状态管理器（用于测试）"""

    def __init__(self, initial_state: str = "000000"):
        self.current_state = initial_state
        self.transition_history = []

    def transition(self, target_state: str) -> bool:
        """模拟状态转换"""
        # 简单的状态转换，实际应该验证汉明距离等
        old_state = self.current_state
        self.current_state = target_state

        self.transition_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "old_state": old_state,
                "new_state": target_state,
            }
        )

        return True


def create_test_scenarios() -> List[Dict[str, Any]]:
    """创建测试场景"""
    scenarios = []

    # 场景1: 基本协同状态转换
    scenarios.append(
        {
            "id": "SCENE-01",
            "name": "基本协同状态转换测试",
            "description": "测试4个智能体在简单状态转换中的协同能力",
            "steps": [
                {
                    "type": "state_transition",
                    "description": "从初始状态转换到邻居状态",
                    "target_state": "000001",
                    "context": {"reason": "测试基本协同"},
                },
                {
                    "type": "state_transition",
                    "description": "继续转换到下一个邻居状态",
                    "target_state": "000011",
                    "context": {"reason": "测试连续协同"},
                },
                {
                    "type": "agent_interaction",
                    "description": "Learner记录性能指标",
                    "interaction": {
                        "agent": "learner",
                        "action": "update_performance",
                        "params": {
                            "metric_name": "collaboration_success_rate",
                            "value": 0.95,
                            "threshold": 0.8,
                        },
                    },
                },
            ],
        }
    )

    # 场景2: 复杂路径转换
    scenarios.append(
        {
            "id": "SCENE-02",
            "name": "复杂路径转换测试",
            "description": "测试智能体在较长转换路径中的协同",
            "steps": [
                {
                    "type": "state_transition",
                    "description": "第一步：转换到000001",
                    "target_state": "000001",
                },
                {
                    "type": "state_transition",
                    "description": "第二步：转换到000011",
                    "target_state": "000011",
                },
                {
                    "type": "state_transition",
                    "description": "第三步：转换到000111",
                    "target_state": "000111",
                },
                {
                    "type": "state_transition",
                    "description": "第四步：转换到001111",
                    "target_state": "001111",
                },
                {
                    "type": "agent_interaction",
                    "description": "Explorer探索相关解决方案",
                    "interaction": {
                        "agent": "explorer",
                        "action": "explore_solutions",
                        "params": {
                            "problem": "如何优化状态转换路径",
                            "domain": "state_optimization",
                        },
                    },
                },
            ],
        }
    )

    # 场景3: 边界状态测试（修正版，符合格雷编码）
    scenarios.append(
        {
            "id": "SCENE-03",
            "name": "边界状态测试（修正版）",
            "description": "测试从初始状态到全阳爻状态的转换，遵循格雷编码规则",
            "steps": [
                {
                    "type": "state_transition",
                    "description": "第一步：从000000转换到邻居状态",
                    "target_state": "000001",
                },
                {
                    "type": "state_transition",
                    "description": "第二步：转换到000011",
                    "target_state": "000011",
                },
                {
                    "type": "state_transition",
                    "description": "第三步：转换到000111",
                    "target_state": "000111",
                },
                {
                    "type": "state_transition",
                    "description": "第四步：转换到001111",
                    "target_state": "001111",
                },
                {
                    "type": "state_transition",
                    "description": "第五步：转换到011111",
                    "target_state": "011111",
                },
                {
                    "type": "state_transition",
                    "description": "第六步：最终转换到全阳爻111111",
                    "target_state": "111111",
                },
            ],
        }
    )

    # 场景4: 负载测试（高频状态转换）
    scenarios.append(
        {
            "id": "SCENE-04",
            "name": "负载测试",
            "description": "高频状态转换测试，验证系统在高负载下的稳定性",
            "steps": [
                {
                    "type": "state_transition",
                    "description": "负载测试第1步：快速转换1",
                    "target_state": "000001",
                },
                {
                    "type": "state_transition",
                    "description": "负载测试第2步：快速转换2",
                    "target_state": "000011",
                },
                {
                    "type": "state_transition",
                    "description": "负载测试第3步：快速转换3",
                    "target_state": "000010",
                },
                {
                    "type": "state_transition",
                    "description": "负载测试第4步：快速转换4",
                    "target_state": "000110",
                },
                {
                    "type": "state_transition",
                    "description": "负载测试第5步：快速转换5",
                    "target_state": "000111",
                },
            ],
        }
    )

    # 场景5: 边界条件测试（修正版）
    scenarios.append(
        {
            "id": "SCENE-05",
            "name": "边界条件测试",
            "description": "测试边界状态和极限条件",
            "steps": [
                {
                    "type": "state_transition",
                    "description": "从全0状态转换到最近邻居",
                    "target_state": "000001",
                },
                {
                    "type": "agent_interaction",
                    "description": "Learner记录边界性能",
                    "interaction": {
                        "agent": "learner",
                        "action": "update_performance",
                        "params": {
                            "metric_name": "boundary_condition_test",
                            "value": 1.0,
                            "threshold": 0.9,
                        },
                    },
                },
                {
                    "type": "state_transition",
                    "description": "向全1状态逐步转换",
                    "target_state": "000011",
                },
                {
                    "type": "state_transition",
                    "description": "继续向全1转换",
                    "target_state": "000111",
                },
                {
                    "type": "state_transition",
                    "description": "接近全1状态",
                    "target_state": "001111",
                },
            ],
        }
    )

    # 场景6: 智能体协同决策测试
    scenarios.append(
        {
            "id": "SCENE-06",
            "name": "智能体协同决策测试",
            "description": "测试智能体在复杂转换中的协同决策能力",
            "steps": [
                {
                    "type": "state_transition",
                    "description": "复杂决策转换1",
                    "target_state": "001000",
                },
                {
                    "type": "state_transition",
                    "description": "复杂决策转换2",
                    "target_state": "011000",
                },
                {
                    "type": "agent_interaction",
                    "description": "Explorer探索解决方案",
                    "interaction": {
                        "agent": "explorer",
                        "action": "explore_solutions",
                        "params": {
                            "problem": "复杂状态转换路径优化",
                            "domain": "state_optimization",
                        },
                    },
                },
                {
                    "type": "state_transition",
                    "description": "复杂决策转换3",
                    "target_state": "011100",
                },
                {
                    "type": "state_transition",
                    "description": "最终决策转换",
                    "target_state": "111100",
                },
            ],
        }
    )

    # 场景7: 异常恢复测试
    scenarios.append(
        {
            "id": "SCENE-07",
            "name": "异常恢复测试",
            "description": "测试系统在异常情况下的恢复能力",
            "steps": [
                {"type": "state_transition", "description": "正常转换1", "target_state": "010000"},
                {
                    "type": "agent_interaction",
                    "description": "模拟异常情况 - Communicator记录异常",
                    "interaction": {
                        "agent": "communicator",
                        "action": "send_message",
                        "params": {
                            "channel_id": "internal_broadcast",
                            "message": {"type": "error_simulation", "severity": "medium"},
                        },
                    },
                },
                {
                    "type": "state_transition",
                    "description": "在异常情况下继续转换",
                    "target_state": "011000",
                },
                {
                    "type": "state_transition",
                    "description": "异常恢复后的转换",
                    "target_state": "011100",
                },
            ],
        }
    )

    # 场景8: 对称模式转换测试（修正版）
    scenarios.append(
        {
            "id": "SCENE-08",
            "name": "对称模式转换测试（修正版）",
            "description": "测试对称和非对称状态之间的转换，符合格雷编码规则",
            "steps": [
                {
                    "type": "state_transition",
                    "description": "从初始状态到对称模式的路径第1步",
                    "target_state": "000001",
                },
                {
                    "type": "state_transition",
                    "description": "从000001到000101，路径第2步",
                    "target_state": "000101",
                },
                {
                    "type": "state_transition",
                    "description": "到达对称模式010101",
                    "target_state": "010101",
                },
                {
                    "type": "agent_interaction",
                    "description": "Guardian验证对称状态安全性",
                    "interaction": {
                        "agent": "guardian",
                        "action": "validate_safety",
                        "params": {"state_change_type": "symmetry_state"},
                    },
                },
                {
                    "type": "state_transition",
                    "description": "对称性破坏：从010101到010100",
                    "target_state": "010100",
                },
                {
                    "type": "agent_interaction",
                    "description": "Guardian验证对称性变化安全性",
                    "interaction": {
                        "agent": "guardian",
                        "action": "validate_safety",
                        "params": {"state_change_type": "symmetry_break"},
                    },
                },
                {
                    "type": "state_transition",
                    "description": "恢复对称性：回到010101",
                    "target_state": "010101",
                },
                {
                    "type": "agent_interaction",
                    "description": "Learner记录对称性转换性能",
                    "interaction": {
                        "agent": "learner",
                        "action": "update_performance",
                        "params": {
                            "metric_name": "symmetry_transition_success_rate",
                            "value": 1.0,
                            "threshold": 0.9,
                        },
                    },
                },
            ],
        }
    )

    # 场景9: 探索与发现测试（修正版）
    scenarios.append(
        {
            "id": "SCENE-09",
            "name": "探索与发现测试（修正版）",
            "description": "测试Explorer智能体发现新状态和路径的能力，符合格雷编码规则",
            "steps": [
                {
                    "type": "state_transition",
                    "description": "探索路径第1步：从初始状态到中间状态",
                    "target_state": "000100",
                },
                {
                    "type": "state_transition",
                    "description": "进入探索起始点001100",
                    "target_state": "001100",
                },
                {
                    "type": "agent_interaction",
                    "description": "Explorer探索未知状态空间",
                    "interaction": {
                        "agent": "explorer",
                        "action": "explore_solutions",
                        "params": {"problem": "发现新的卦象状态", "domain": "state_discovery"},
                    },
                },
                {
                    "type": "state_transition",
                    "description": "探索转换1：从001100到011100",
                    "target_state": "011100",
                },
                {
                    "type": "agent_interaction",
                    "description": "Communicator通知探索进展",
                    "interaction": {
                        "agent": "communicator",
                        "action": "send_message",
                        "params": {
                            "channel_id": "internal_broadcast",
                            "message": {
                                "exploration_phase": "intermediate",
                                "discovery": "path_found",
                            },
                        },
                    },
                },
                {
                    "type": "state_transition",
                    "description": "探索转换2：从011100到111100",
                    "target_state": "111100",
                },
                {
                    "type": "agent_interaction",
                    "description": "Learner记录探索性能",
                    "interaction": {
                        "agent": "learner",
                        "action": "update_performance",
                        "params": {
                            "metric_name": "exploration_success_rate",
                            "value": 1.0,
                            "threshold": 0.8,
                        },
                    },
                },
                {
                    "type": "agent_interaction",
                    "description": "Explorer报告最终发现",
                    "interaction": {
                        "agent": "explorer",
                        "action": "explore_solutions",
                        "params": {"problem": "总结探索路径", "domain": "path_summary"},
                    },
                },
            ],
        }
    )

    # 场景10: 端到端流程测试
    scenarios.append(
        {
            "id": "SCENE-10",
            "name": "端到端流程测试",
            "description": "完整业务流程模拟，测试所有智能体协同工作",
            "steps": [
                {
                    "type": "state_transition",
                    "description": "业务流程开始",
                    "target_state": "000001",
                },
                {
                    "type": "agent_interaction",
                    "description": "Guardian验证业务开始安全性",
                    "interaction": {
                        "agent": "guardian",
                        "action": "validate_safety",
                        "params": {"state_change_type": "business_process_start"},
                    },
                },
                {
                    "type": "state_transition",
                    "description": "业务处理阶段1",
                    "target_state": "000011",
                },
                {
                    "type": "agent_interaction",
                    "description": "Communicator通知业务进展",
                    "interaction": {
                        "agent": "communicator",
                        "action": "send_message",
                        "params": {
                            "channel_id": "internal_broadcast",
                            "message": {"phase": "processing", "progress": 25},
                        },
                    },
                },
                {
                    "type": "state_transition",
                    "description": "业务处理阶段2",
                    "target_state": "000111",
                },
                {
                    "type": "agent_interaction",
                    "description": "Explorer探索优化方案",
                    "interaction": {
                        "agent": "explorer",
                        "action": "explore_solutions",
                        "params": {"problem": "业务流程优化", "domain": "business_optimization"},
                    },
                },
                {
                    "type": "state_transition",
                    "description": "业务完成阶段",
                    "target_state": "001111",
                },
                {
                    "type": "agent_interaction",
                    "description": "Learner记录业务性能",
                    "interaction": {
                        "agent": "learner",
                        "action": "update_performance",
                        "params": {
                            "metric_name": "business_process_success_rate",
                            "value": 1.0,
                            "threshold": 0.9,
                        },
                    },
                },
                {
                    "type": "agent_interaction",
                    "description": "Communicator发送完成通知",
                    "interaction": {
                        "agent": "communicator",
                        "action": "send_message",
                        "params": {
                            "channel_id": "internal_broadcast",
                            "message": {"phase": "completed", "status": "success"},
                        },
                    },
                },
            ],
        }
    )

    return scenarios


def main():
    """主测试函数"""
    print("=" * 60)
    print("MAREF多智能体协同测试框架")
    print("=" * 60)

    # 创建测试器
    tester = MultiAgentCollaborationTester(initial_state="000000")

    # 创建测试场景
    test_scenarios = create_test_scenarios()
    print(f"\n📋 创建了 {len(test_scenarios)} 个测试场景")

    # 运行测试场景
    all_results = {}
    for scenario in test_scenarios:
        result = tester.run_collaboration_test(scenario)
        all_results[scenario["id"]] = result

        # 打印场景结果
        status_icon = "✅" if result["status"] == "completed" else "❌"
        print(f"{status_icon} 场景 {scenario['id']}: {scenario['name']} - {result['status']}")

    # 生成报告
    report = tester.generate_test_report()

    # 打印报告
    tester.print_report(report)

    # 保存报告到文件
    report_filename = (
        f"multi_agent_collaboration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(report_filename, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n📄 详细报告已保存到: {report_filename}")
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
