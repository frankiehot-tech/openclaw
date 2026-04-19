#!/usr/bin/env python3
"""
状态空间扩展测试器
基于扩展策略执行状态空间扩展测试，提升状态空间覆盖率
"""

import json
import os
import statistics
import sys
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# 添加当前目录到路径
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), "external/ROMA"))

try:
    from hexagram_state_manager import HexagramStateManager

    HAS_STATE_MANAGER = True
except ImportError:
    print("⚠️  无法导入HexagramStateManager，将使用简化版本")
    HAS_STATE_MANAGER = False


class StateSpaceExpansionTester:
    """状态空间扩展测试器"""

    def __init__(self, initial_state: str = "000000", db_path: str = None):
        """
        初始化扩展测试器

        Args:
            initial_state: 初始状态
            db_path: 内存数据库路径（用于加载现有状态）
        """
        if HAS_STATE_MANAGER:
            self.state_manager = HexagramStateManager(initial_state)
        else:
            self.state_manager = None

        self.initial_state = initial_state
        self.current_state = initial_state
        self.db_path = db_path

        # 状态记录
        self.visited_states = set([initial_state])
        self.transition_history = []
        self.test_results = []

        # 扩展策略配置
        self.expansion_priority = self._init_expansion_priority()

        print(f"✅ 状态空间扩展测试器初始化完成")
        print(f"   初始状态: {initial_state}")
        print(f"   状态管理器: {'可用' if HAS_STATE_MANAGER else '不可用'}")

    def _init_expansion_priority(self) -> List[Dict[str, Any]]:
        """初始化扩展优先级配置"""
        # 基于扩展策略设计文档的优先级
        priority_list = [
            # 一级优先级：邻居扩展
            {
                "state": "001000",
                "name": "地山谦",
                "priority": 9.2,
                "strategy": "邻居优先",
                "reason": "000000的邻居",
            },
            {
                "state": "010000",
                "name": "地水师",
                "priority": 9.0,
                "strategy": "邻居优先",
                "reason": "000000的邻居",
            },
            {
                "state": "100000",
                "name": "地山剥",
                "priority": 8.8,
                "strategy": "邻居优先",
                "reason": "000000的邻居",
            },
            {
                "state": "000101",
                "name": "火地晋",
                "priority": 8.5,
                "strategy": "邻居优先",
                "reason": "000001/000100的邻居",
            },
            {
                "state": "000110",
                "name": "风地观",
                "priority": 8.3,
                "strategy": "邻居优先",
                "reason": "000010/000100的邻居",
            },
            {
                "state": "001001",
                "name": "雷山小过",
                "priority": 8.0,
                "strategy": "邻居优先",
                "reason": "000001的邻居",
            },
            {
                "state": "010001",
                "name": "雷水解",
                "priority": 7.8,
                "strategy": "邻居优先",
                "reason": "000001的邻居",
            },
            {
                "state": "001010",
                "name": "水山蹇",
                "priority": 7.6,
                "strategy": "邻居优先",
                "reason": "000010的邻居",
            },
            # 二级优先级：模式扩展
            {
                "state": "010101",
                "name": "火水未济",
                "priority": 9.5,
                "strategy": "模式优先",
                "reason": "交替模式重要卦象",
            },
            {
                "state": "101010",
                "name": "水火既济",
                "priority": 9.3,
                "strategy": "模式优先",
                "reason": "互补交替模式",
            },
            {
                "state": "111111",
                "name": "乾为天",
                "priority": 9.8,
                "strategy": "边界优先",
                "reason": "全阳爻，状态空间最大值",
            },
            {
                "state": "001100",
                "name": "艮为山",
                "priority": 8.7,
                "strategy": "邻居优先",
                "reason": "000100的邻居，对称模式",
            },
            # 三级优先级：其他重要状态
            {
                "state": "000111",
                "name": "天地否",
                "priority": 7.5,
                "strategy": "邻居优先",
                "reason": "000011的邻居",
            },
            {
                "state": "001011",
                "name": "泽山咸",
                "priority": 7.3,
                "strategy": "邻居优先",
                "reason": "000011的邻居",
            },
            {
                "state": "010011",
                "name": "泽水困",
                "priority": 7.1,
                "strategy": "邻居优先",
                "reason": "000011的邻居",
            },
            {
                "state": "010100",
                "name": "山水蒙",
                "priority": 7.0,
                "strategy": "邻居优先",
                "reason": "000100的邻居",
            },
            {
                "state": "011011",
                "name": "兑为泽",
                "priority": 8.2,
                "strategy": "模式优先",
                "reason": "对称模式",
            },
            {
                "state": "100100",
                "name": "艮为山",
                "priority": 6.8,
                "strategy": "邻居优先",
                "reason": "000100的邻居",
            },
            {
                "state": "101101",
                "name": "离为火",
                "priority": 8.6,
                "strategy": "模式优先",
                "reason": "对称模式",
            },
            {
                "state": "110011",
                "name": "泽风大过",
                "priority": 8.4,
                "strategy": "模式优先",
                "reason": "对称模式",
            },
        ]

        # 按优先级排序
        priority_list.sort(key=lambda x: x["priority"], reverse=True)
        return priority_list

    def hamming_distance(self, state1: str, state2: str) -> int:
        """计算汉明距离"""
        if len(state1) != len(state2):
            raise ValueError(f"状态长度不一致: {len(state1)} != {len(state2)}")
        return sum(bit1 != bit2 for bit1, bit2 in zip(state1, state2))

    def get_neighbor_states(self, state: str) -> List[str]:
        """获取某个状态的所有邻居状态（汉明距离=1）"""
        neighbors = []
        for i in range(6):
            bits = list(state)
            bits[i] = "1" if bits[i] == "0" else "0"
            neighbor = "".join(bits)
            neighbors.append(neighbor)
        return neighbors

    def find_path_to_state(
        self, start_state: str, target_state: str, max_steps: int = 10
    ) -> List[str]:
        """寻找从起始状态到目标状态的路径（BFS）"""
        if start_state == target_state:
            return [start_state]

        queue = deque([(start_state, [start_state])])
        visited = {start_state}

        while queue:
            current, path = queue.popleft()

            if len(path) > max_steps:
                continue

            if current == target_state:
                return path

            # 生成邻居状态
            neighbors = self.get_neighbor_states(current)
            for neighbor in neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return []  # 未找到路径

    def load_existing_states(self) -> Set[str]:
        """从数据库加载现有状态"""
        existing_states = set()

        if not self.db_path:
            print("⚠️  未提供数据库路径，使用初始状态")
            return {self.initial_state}

        db_file = Path(self.db_path)
        if not db_file.exists():
            print(f"⚠️  数据库不存在: {db_file}，使用初始状态")
            return {self.initial_state}

        try:
            import sqlite3

            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row

            query = """
            SELECT DISTINCT json_extract(content_json, '$.from_state') as state
            FROM memory_entries
            WHERE entry_type = 'state_transition' AND json_extract(content_json, '$.from_state') IS NOT NULL
            UNION
            SELECT DISTINCT json_extract(content_json, '$.to_state') as state
            FROM memory_entries
            WHERE entry_type = 'state_transition' AND json_extract(content_json, '$.to_state') IS NOT NULL
            """

            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()

            for row in rows:
                state = row["state"]
                if state and len(state) == 6 and all(bit in "01" for bit in state):
                    existing_states.add(state)

            conn.close()

            print(f"📊 从数据库加载了 {len(existing_states)} 个现有状态")
            return existing_states

        except Exception as e:
            print(f"❌ 加载数据库状态失败: {e}")
            return {self.initial_state}

    def execute_transition(self, target_state: str, reason: str = "扩展测试") -> Dict[str, Any]:
        """执行状态转换并记录结果"""
        start_time = time.time()

        try:
            # 验证状态格式
            if len(target_state) != 6 or not all(bit in "01" for bit in target_state):
                raise ValueError(f"无效状态格式: {target_state}")

            # 计算汉明距离
            distance = self.hamming_distance(self.current_state, target_state)

            # 检查格雷编码合规性
            if distance != 1:
                result = {
                    "success": False,
                    "from_state": self.current_state,
                    "to_state": target_state,
                    "distance": distance,
                    "reason": reason,
                    "error": f"汉明距离不为1: {distance}",
                    "execution_time": time.time() - start_time,
                }
            else:
                # 执行转换
                if HAS_STATE_MANAGER and self.state_manager:
                    success = self.state_manager.transition(target_state)
                else:
                    # 模拟转换
                    success = True

                if success:
                    self.visited_states.add(target_state)
                    self.current_state = target_state

                    # 记录转换
                    transition_record = {
                        "from_state": self.current_state if success else self.current_state,
                        "to_state": target_state,
                        "distance": distance,
                        "success": success,
                        "timestamp": time.time(),
                        "reason": reason,
                    }
                    self.transition_history.append(transition_record)

                result = {
                    "success": success,
                    "from_state": (
                        self.transition_history[-1]["from_state"]
                        if self.transition_history
                        else self.current_state
                    ),
                    "to_state": target_state,
                    "distance": distance,
                    "reason": reason,
                    "error": None if success else "状态转换失败",
                    "execution_time": time.time() - start_time,
                }

        except Exception as e:
            result = {
                "success": False,
                "from_state": self.current_state,
                "to_state": target_state,
                "distance": -1,
                "reason": reason,
                "error": str(e),
                "execution_time": time.time() - start_time,
            }

        self.test_results.append(result)
        return result

    def run_neighbor_expansion_test(self, existing_states: Set[str]) -> List[Dict[str, Any]]:
        """运行邻居扩展测试"""
        print(f"\n🔍 开始邻居扩展测试")
        print(f"   现有状态数: {len(existing_states)}")

        results = []
        visited_pairs = set()

        # 对每个现有状态，测试其邻居
        for state in list(existing_states)[:10]:  # 限制测试数量
            neighbors = self.get_neighbor_states(state)
            print(f"   状态 {state} 有 {len(neighbors)} 个邻居")

            for neighbor in neighbors:
                pair_key = f"{state}→{neighbor}"
                if pair_key in visited_pairs:
                    continue

                # 检查是否已访问过
                if neighbor in existing_states:
                    continue

                # 尝试转换
                print(f"     测试转换: {state} → {neighbor}")
                result = self.execute_transition(neighbor, f"邻居扩展测试: {state} → {neighbor}")
                results.append(result)
                visited_pairs.add(pair_key)

                if result["success"]:
                    print(f"       ✅ 成功 (距离: {result['distance']})")
                else:
                    print(f"       ❌ 失败: {result.get('error', '未知错误')}")

                # 短暂暂停
                time.sleep(0.1)

        print(f"   邻居扩展测试完成: {len(results)} 个测试")
        return results

    def run_priority_expansion_test(self) -> List[Dict[str, Any]]:
        """运行优先级扩展测试"""
        print(f"\n🎯 开始优先级扩展测试")
        print(f"   目标状态数: {len(self.expansion_priority)}")

        results = []
        successful_expansions = 0

        for i, target in enumerate(self.expansion_priority[:15], 1):  # 测试前15个
            target_state = target["state"]
            target_name = target["name"]
            priority = target["priority"]
            strategy = target["strategy"]

            print(
                f"   测试 {i:2d}: {target_state} ({target_name}) - 优先级: {priority}, 策略: {strategy}"
            )

            # 寻找路径
            path = self.find_path_to_state(self.current_state, target_state, max_steps=6)

            if not path:
                print(f"       ⚠️  未找到有效路径")
                result = {
                    "success": False,
                    "from_state": self.current_state,
                    "to_state": target_state,
                    "distance": -1,
                    "reason": f"优先级扩展: {strategy}",
                    "error": "未找到有效路径",
                    "execution_time": 0,
                }
                results.append(result)
                continue

            # 执行路径上的转换
            path_success = True
            path_results = []

            for step in range(1, len(path)):
                from_state = path[step - 1]
                to_state = path[step]

                # 如果当前状态不是路径起始点，先切换到起始点
                if self.current_state != from_state:
                    # 寻找从当前状态到from_state的路径
                    adjust_path = self.find_path_to_state(
                        self.current_state, from_state, max_steps=3
                    )
                    if adjust_path:
                        for adj_step in range(1, len(adjust_path)):
                            adj_result = self.execute_transition(
                                adjust_path[adj_step],
                                f"路径调整: {adjust_path[adj_step-1]} → {adjust_path[adj_step]}",
                            )
                            path_results.append(adj_result)
                            if not adj_result["success"]:
                                path_success = False
                                break
                    else:
                        path_success = False
                        break

                # 执行路径转换
                result = self.execute_transition(
                    to_state, f"优先级扩展步骤 {step}/{len(path)-1}: {from_state} → {to_state}"
                )
                path_results.append(result)

                if not result["success"]:
                    path_success = False
                    break

                # 短暂暂停
                time.sleep(0.05)

            # 记录整体结果
            overall_result = {
                "success": path_success,
                "from_state": path[0],
                "to_state": target_state,
                "distance": self.hamming_distance(path[0], target_state) if path_success else -1,
                "reason": f"优先级扩展: {strategy} - {target_name}",
                "error": None if path_success else "路径执行失败",
                "execution_time": sum(r.get("execution_time", 0) for r in path_results),
                "path_length": len(path) - 1,
                "path_states": path,
            }

            results.append(overall_result)

            if path_success:
                successful_expansions += 1
                print(f"       ✅ 成功扩展 (路径长度: {len(path)-1})")
            else:
                print(f"       ❌ 扩展失败")

        print(f"   优先级扩展测试完成: {successful_expansions}/{len(results)} 成功")
        return results

    def run_path_expansion_test(self) -> List[Dict[str, Any]]:
        """运行路径扩展测试"""
        print(f"\n🔄 开始路径扩展测试")

        # 定义测试路径
        test_paths = [
            {
                "name": "邻居扩展主线",
                "states": ["000000", "001000", "001001", "001011", "001111"],
                "description": "测试连续邻居扩展",
            },
            {
                "name": "模式扩展主线",
                "states": ["000000", "010000", "010001", "010101", "111111"],
                "description": "测试模式扩展路径",
            },
            {
                "name": "循环扩展测试",
                "states": ["000000", "000001", "000011", "000010", "000000"],
                "description": "测试循环路径稳定性",
            },
        ]

        results = []

        for path_idx, path_def in enumerate(test_paths, 1):
            path_name = path_def["name"]
            path_states = path_def["states"]
            description = path_def["description"]

            print(f"   路径 {path_idx}: {path_name} - {description}")
            print(f"     路径: {' → '.join(path_states)}")

            path_success = True
            path_results = []

            # 确保从当前状态开始
            start_state = path_states[0]
            if self.current_state != start_state:
                # 切换到路径起始点
                adjust_path = self.find_path_to_state(self.current_state, start_state, max_steps=3)
                if adjust_path:
                    for step in range(1, len(adjust_path)):
                        result = self.execute_transition(
                            adjust_path[step],
                            f"路径{path_idx}调整: {adjust_path[step-1]} → {adjust_path[step]}",
                        )
                        path_results.append(result)
                        if not result["success"]:
                            path_success = False
                            break
                else:
                    path_success = False

            # 执行路径转换
            if path_success:
                for step in range(1, len(path_states)):
                    from_state = path_states[step - 1]
                    to_state = path_states[step]

                    result = self.execute_transition(
                        to_state, f"路径{path_idx}步骤{step}: {from_state} → {to_state}"
                    )
                    path_results.append(result)

                    if not result["success"]:
                        path_success = False
                        break

                    time.sleep(0.05)

            # 记录路径结果
            path_result = {
                "path_name": path_name,
                "path_states": path_states,
                "success": path_success,
                "total_steps": len(path_states) - 1,
                "successful_steps": sum(1 for r in path_results if r.get("success", False)),
                "execution_time": sum(r.get("execution_time", 0) for r in path_results),
                "description": description,
            }

            results.append(path_result)

            if path_success:
                print(f"       ✅ 路径执行成功 ({len(path_states)-1}步)")
            else:
                print(f"       ❌ 路径执行失败")

        print(f"   路径扩展测试完成: {len(results)} 条路径测试")
        return results

    def generate_expansion_report(self) -> Dict[str, Any]:
        """生成扩展测试报告"""
        # 计算统计数据
        total_tests = len(self.test_results)
        successful_tests = sum(1 for r in self.test_results if r.get("success", False))
        success_rate = successful_tests / total_tests if total_tests > 0 else 0

        # 状态空间覆盖率
        total_possible_states = 64
        coverage_percentage = len(self.visited_states) / total_possible_states * 100

        # 转换多样性
        unique_transitions = set()
        for trans in self.transition_history:
            key = f"{trans.get('from_state', '')}→{trans.get('to_state', '')}"
            unique_transitions.add(key)

        transition_diversity = (
            len(unique_transitions) / len(self.transition_history) * 100
            if self.transition_history
            else 0
        )

        # 汉明距离统计
        distances = [r.get("distance", 0) for r in self.test_results if r.get("distance", 0) > 0]
        avg_distance = statistics.mean(distances) if distances else 0

        # 生成报告
        report = {
            "summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "success_rate": success_rate,
                "initial_state": self.initial_state,
                "final_state": self.current_state,
                "visited_states_count": len(self.visited_states),
                "state_space_coverage": coverage_percentage,
                "unique_transitions": len(unique_transitions),
                "transition_diversity": transition_diversity,
                "average_hamming_distance": avg_distance,
                "generation_timestamp": time.time(),
            },
            "state_space_analysis": {
                "visited_states": list(self.visited_states),
                "total_possible_states": total_possible_states,
                "coverage_percentage": coverage_percentage,
                "remaining_states": total_possible_states - len(self.visited_states),
            },
            "test_results_summary": {
                "neighbor_expansion_tests": sum(
                    1 for r in self.test_results if "邻居扩展" in str(r.get("reason", ""))
                ),
                "priority_expansion_tests": sum(
                    1 for r in self.test_results if "优先级扩展" in str(r.get("reason", ""))
                ),
                "path_expansion_tests": sum(
                    1 for r in self.test_results if "路径" in str(r.get("reason", ""))
                ),
                "by_success_rate": {
                    "neighbor": self._calculate_category_success_rate("邻居扩展"),
                    "priority": self._calculate_category_success_rate("优先级扩展"),
                    "path": self._calculate_category_success_rate("路径"),
                },
            },
            "detailed_results": self.test_results[-50:],  # 最近50个结果
            "recommendations": self._generate_recommendations(),
        }

        return report

    def _calculate_category_success_rate(self, category_keyword: str) -> float:
        """计算特定类别的成功率"""
        category_tests = [
            r for r in self.test_results if category_keyword in str(r.get("reason", ""))
        ]
        if not category_tests:
            return 0
        successful = sum(1 for r in category_tests if r.get("success", False))
        return successful / len(category_tests)

    def _generate_recommendations(self) -> List[str]:
        """生成扩展建议"""
        recommendations = []

        # 基于覆盖率
        coverage = len(self.visited_states) / 64 * 100
        if coverage < 15:
            recommendations.append("状态空间覆盖率较低 (<15%)，建议继续执行邻居扩展测试")
        elif coverage < 25:
            recommendations.append("状态空间覆盖率接近目标 (15-25%)，建议增加模式扩展测试")
        else:
            recommendations.append("状态空间覆盖率良好 (≥25%)，建议进行复杂路径和智能体集成测试")

        # 基于成功率
        success_rate = self._calculate_overall_success_rate()
        if success_rate < 0.8:
            recommendations.append(
                f"测试成功率较低 ({success_rate:.1%})，建议检查状态转换逻辑和错误处理"
            )
        elif success_rate < 0.95:
            recommendations.append(f"测试成功率良好 ({success_rate:.1%})，可继续扩展测试范围")
        else:
            recommendations.append(f"测试成功率优秀 ({success_rate:.1%})，系统稳定性良好")

        # 基于多样性
        if len(self.visited_states) < 10:
            recommendations.append("访问状态数量较少，建议扩展更多不同区域的状态")

        return recommendations

    def _calculate_overall_success_rate(self) -> float:
        """计算总体成功率"""
        if not self.test_results:
            return 0
        successful = sum(1 for r in self.test_results if r.get("success", False))
        return successful / len(self.test_results)

    def print_report(self, report: Dict[str, Any], output_file: str = None):
        """打印和保存报告"""
        summary = report["summary"]
        state_analysis = report["state_space_analysis"]

        print("\n" + "=" * 70)
        print("状态空间扩展测试报告")
        print("=" * 70)

        print(f"\n📊 总体统计:")
        print(f"   总测试数: {summary['total_tests']}")
        print(f"   成功测试: {summary['successful_tests']}")
        print(f"   成功率: {summary['success_rate']:.1%}")
        print(f"   初始状态: {summary['initial_state']}")
        print(f"   最终状态: {summary['final_state']}")

        print(f"\n🌐 状态空间覆盖:")
        print(f"   访问状态数: {summary['visited_states_count']}")
        print(f"   总可能状态: {state_analysis['total_possible_states']}")
        print(f"   覆盖率: {state_analysis['coverage_percentage']:.1f}%")
        print(f"   剩余状态: {state_analysis['remaining_states']}")

        print(f"\n🔄 转换多样性:")
        print(f"   唯一转换数: {summary['unique_transitions']}")
        print(f"   转换多样性: {summary['transition_diversity']:.1f}%")
        print(f"   平均汉明距离: {summary['average_hamming_distance']:.2f}")

        # 测试类别统计
        test_summary = report["test_results_summary"]
        print(f"\n🧪 测试类别统计:")
        print(f"   邻居扩展测试: {test_summary['neighbor_expansion_tests']}")
        print(f"   优先级扩展测试: {test_summary['priority_expansion_tests']}")
        print(f"   路径扩展测试: {test_summary['path_expansion_tests']}")

        # 成功率分类
        success_rates = test_summary["by_success_rate"]
        print(f"   各类别成功率:")
        for category, rate in success_rates.items():
            print(f"     {category}: {rate:.1%}")

        # 建议
        recommendations = report.get("recommendations", [])
        if recommendations:
            print(f"\n🎯 扩展建议:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")

        # 保存报告
        if output_file:
            try:
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(report, f, ensure_ascii=False, indent=2)
                print(f"\n📄 详细报告已保存到: {output_file}")
            except Exception as e:
                print(f"❌ 保存报告失败: {e}")

    def run_full_expansion_test(self, output_dir: str = None) -> Dict[str, Any]:
        """运行完整的状态空间扩展测试"""
        print(f"\n🚀 开始完整的状态空间扩展测试")
        print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"初始状态: {self.initial_state}")

        # 加载现有状态
        existing_states = self.load_existing_states()
        self.visited_states.update(existing_states)
        print(f"现有状态加载完成: {len(existing_states)} 个状态")

        # 运行各种扩展测试
        print(f"\n=== 执行扩展测试套件 ===")

        # 1. 邻居扩展测试
        neighbor_results = self.run_neighbor_expansion_test(existing_states)

        # 2. 优先级扩展测试
        priority_results = self.run_priority_expansion_test()

        # 3. 路径扩展测试
        path_results = self.run_path_expansion_test()

        # 生成报告
        print(f"\n📈 生成扩展测试报告...")
        report = self.generate_expansion_report()

        # 确定输出目录
        if output_dir is None:
            output_dir = Path.cwd() / "expansion_test_reports"
        else:
            output_dir = Path(output_dir)

        output_dir.mkdir(exist_ok=True)

        # 生成输出文件名
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"state_space_expansion_report_{timestamp}.json"

        # 打印报告
        self.print_report(report, str(output_file))

        # 返回测试结果
        return report


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="状态空间扩展测试器")
    parser.add_argument("--initial-state", default="000000", help="初始状态")
    parser.add_argument("--db-path", help="内存数据库路径")
    parser.add_argument("--output-dir", help="报告输出目录")

    args = parser.parse_args()

    # 创建测试器
    tester = StateSpaceExpansionTester(initial_state=args.initial_state, db_path=args.db_path)

    # 运行完整测试
    try:
        report = tester.run_full_expansion_test(args.output_dir)

        # 检查是否达到目标
        coverage = report["state_space_analysis"]["coverage_percentage"]
        success_rate = report["summary"]["success_rate"]

        print(f"\n{'='*70}")
        print("扩展测试完成!")

        if coverage >= 25 and success_rate >= 0.9:
            print("🎉 达到第2周扩展目标!")
            print(f"   状态空间覆盖率: {coverage:.1f}% (目标: ≥25%)")
            print(f"   测试成功率: {success_rate:.1%} (目标: ≥90%)")
            return 0
        else:
            print("⚠️  未完全达到扩展目标")
            print(f"   状态空间覆盖率: {coverage:.1f}% (目标: ≥25%)")
            print(f"   测试成功率: {success_rate:.1%} (目标: ≥90%)")
            return 1

    except Exception as e:
        print(f"❌ 扩展测试过程中出现异常: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
