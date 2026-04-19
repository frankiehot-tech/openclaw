#!/usr/bin/env python3
"""
格雷编码状态管理器
基于MAREF格雷编码理念的6维状态空间管理系统

特性：
- 6维超立方体状态空间（2^6=64个状态）
- 格雷编码：相邻状态汉明距离=1
- 连续演化：每次只改变一个维度
- 状态可视化：支持状态空间图形表示
"""

import hashlib
import json
import math
import typing as t
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class QualityDimension(Enum):
    """质量评估维度（6维超立方体）"""

    CORRECTNESS = "correctness"  # D1: 正确性
    COMPLEXITY = "complexity"  # D2: 复杂度
    STYLE = "style"  # D3: 风格
    READABILITY = "readability"  # D4: 可读性
    MAINTAINABILITY = "maintainability"  # D5: 可维护性
    COST_EFFICIENCY = "cost_efficiency"  # D6: 成本效率


@dataclass
class StateEvolution:
    """状态演化记录"""

    from_state: int  # 起始状态（二进制表示）
    to_state: int  # 目标状态
    changed_dimension: str  # 改变的维度
    change_magnitude: float  # 变化幅度
    timestamp: datetime  # 演化时间
    context: dict = field(default_factory=dict)  # 演化上下文


@dataclass
class StateAnalysis:
    """状态分析结果"""

    state_code: int  # 状态编码
    binary_representation: str  # 二进制表示
    gray_code_representation: str  # 格雷编码表示
    dimension_values: t.Dict[str, int]  # 各维度值（0或1）
    quality_score: float  # 质量评分
    evolution_distance: int  # 距离完美状态的距离
    improvement_suggestions: t.List[str] = field(default_factory=list)
    optimal_path: t.List[int] = field(default_factory=list)  # 到完美状态的最优路径


class GrayCodeStateManager:
    """格雷编码状态管理器"""

    def __init__(self, dimensions: t.List[QualityDimension] = None):
        # 默认6个维度
        self.dimensions = dimensions or [
            QualityDimension.CORRECTNESS,
            QualityDimension.COMPLEXITY,
            QualityDimension.STYLE,
            QualityDimension.READABILITY,
            QualityDimension.MAINTAINABILITY,
            QualityDimension.COST_EFFICIENCY,
        ]

        self.n_dimensions = len(self.dimensions)
        self.state_space = 2**self.n_dimensions

        # 生成格雷编码序列
        self.gray_codes = self._generate_gray_codes(self.n_dimensions)

        # 状态映射：格雷编码 -> 二进制
        self.gray_to_binary = {
            gray: bin(gray)[2:].zfill(self.n_dimensions) for gray in self.gray_codes
        }

        # 二进制 -> 格雷编码
        self.binary_to_gray = {bin_str: gray for gray, bin_str in self.gray_to_binary.items()}

        # 状态历史
        self.state_history: t.List[StateEvolution] = []

        # 维度权重（用于计算质量评分）
        self.dimension_weights = {
            QualityDimension.CORRECTNESS.value: 0.25,
            QualityDimension.COMPLEXITY.value: 0.15,
            QualityDimension.STYLE.value: 0.10,
            QualityDimension.READABILITY.value: 0.15,
            QualityDimension.MAINTAINABILITY.value: 0.15,
            QualityDimension.COST_EFFICIENCY.value: 0.20,
        }

        # 完美状态：所有维度都为1
        self.perfect_state = self.state_space - 1

        print(f"🔧 格雷编码状态管理器初始化完成")
        print(f"   维度数: {self.n_dimensions}")
        print(f"   状态空间: {self.state_space} 个状态")
        print(f"   完美状态: {bin(self.perfect_state)[2:].zfill(self.n_dimensions)}")

    def _generate_gray_codes(self, n: int) -> t.List[int]:
        """生成n位格雷编码序列"""
        if n == 0:
            return [0]

        # 递归生成格雷编码
        smaller = self._generate_gray_codes(n - 1)

        # 反转并添加最高位
        return smaller + [x | (1 << (n - 1)) for x in reversed(smaller)]

    def get_state_from_scores(self, scores: t.Dict[str, float], threshold: float = 6.0) -> int:
        """从维度评分计算状态"""
        state_code = 0

        for i, dimension in enumerate(self.dimensions):
            dim_name = dimension.value
            score = scores.get(dim_name, 0.0)

            # 如果评分超过阈值，设置对应位为1
            if score >= threshold:
                state_code |= 1 << i

        return state_code

    def get_state_from_binary(self, binary_str: str) -> int:
        """从二进制字符串获取状态"""
        # 确保长度正确
        if len(binary_str) != self.n_dimensions:
            raise ValueError(
                f"二进制字符串长度必须为 {self.n_dimensions}，实际为 {len(binary_str)}"
            )

        # 转换为整数
        return int(binary_str, 2)

    def get_gray_code(self, state: int) -> int:
        """获取状态的格雷编码"""
        if state < 0 or state >= self.state_space:
            raise ValueError(f"状态值必须在 0 到 {self.state_space-1} 之间")

        # 查找格雷编码
        for gray, binary in self.gray_to_binary.items():
            if int(binary, 2) == state:
                return gray

        # 如果没有直接匹配，计算格雷编码
        return self._binary_to_gray(state)

    def _binary_to_gray(self, n: int) -> int:
        """二进制转格雷编码"""
        return n ^ (n >> 1)

    def evolve_state(
        self,
        current_state: int,
        dimension: str,
        improvement: float,
        context: t.Optional[dict] = None,
    ) -> t.Tuple[int, StateEvolution]:
        """在指定维度上演化状态"""
        # 查找维度索引
        dim_index = None
        for i, dim in enumerate(self.dimensions):
            if dim.value == dimension:
                dim_index = i
                break

        if dim_index is None:
            raise ValueError(f"未知维度: {dimension}")

        # 获取当前维度的值
        current_bit = (current_state >> dim_index) & 1

        # 根据改进程度决定是否翻转位
        # 如果改进显著（> 0.5），则翻转位（0->1 或 1->0）
        new_bit = 1 - current_bit if improvement > 0.5 else current_bit

        # 计算新状态
        if new_bit != current_bit:
            # 翻转对应位
            new_state = current_state ^ (1 << dim_index)
            change_magnitude = 1.0
        else:
            # 位不变，但记录改进
            new_state = current_state
            change_magnitude = improvement

        # 验证汉明距离
        hamming_distance = bin(current_state ^ new_state).count("1")
        if hamming_distance > 1:
            print(f"⚠️  注意：演化距离为 {hamming_distance}，大于1")

        # 创建演化记录
        evolution = StateEvolution(
            from_state=current_state,
            to_state=new_state,
            changed_dimension=dimension,
            change_magnitude=change_magnitude,
            timestamp=datetime.now(),
            context=context or {},
        )

        # 添加到历史
        self.state_history.append(evolution)

        return new_state, evolution

    def analyze_state(self, state: int) -> StateAnalysis:
        """分析状态"""
        # 二进制表示
        binary_repr = bin(state)[2:].zfill(self.n_dimensions)

        # 格雷编码表示
        gray_code = self.get_gray_code(state)
        gray_repr = bin(gray_code)[2:].zfill(self.n_dimensions)

        # 提取各维度值
        dimension_values = {}
        for i, dimension in enumerate(self.dimensions):
            bit_value = (state >> i) & 1
            dimension_values[dimension.value] = bit_value

        # 计算质量评分
        quality_score = self._calculate_quality_score(state)

        # 计算到完美状态的距离
        evolution_distance = self._calculate_distance_to_perfect(state)

        # 生成改进建议
        improvement_suggestions = self._generate_improvement_suggestions(state)

        # 计算到完美状态的最优路径
        optimal_path = self._find_optimal_path_to_perfect(state)

        return StateAnalysis(
            state_code=state,
            binary_representation=binary_repr,
            gray_code_representation=gray_repr,
            dimension_values=dimension_values,
            quality_score=quality_score,
            evolution_distance=evolution_distance,
            improvement_suggestions=improvement_suggestions,
            optimal_path=optimal_path,
        )

    def _calculate_quality_score(self, state: int) -> float:
        """计算状态的质量评分"""
        total_weight = 0.0
        weighted_sum = 0.0

        for i, dimension in enumerate(self.dimensions):
            bit_value = (state >> i) & 1
            weight = self.dimension_weights.get(dimension.value, 0.0)

            weighted_sum += bit_value * weight * 10  # 转换为0-10分制
            total_weight += weight

        if total_weight == 0:
            return 0.0

        return weighted_sum / total_weight

    def _calculate_distance_to_perfect(self, state: int) -> int:
        """计算到完美状态的汉明距离"""
        return bin(state ^ self.perfect_state).count("1")

    def _generate_improvement_suggestions(self, state: int) -> t.List[str]:
        """生成改进建议"""
        suggestions = []

        for i, dimension in enumerate(self.dimensions):
            bit_value = (state >> i) & 1

            if bit_value == 0:  # 该维度需要改进
                dim_name = dimension.value

                suggestion_map = {
                    "correctness": "增加测试覆盖率，修复边界条件",
                    "complexity": "降低圈复杂度，拆分大型函数",
                    "style": "遵循编码规范，统一命名约定",
                    "readability": "添加注释，改善变量命名",
                    "maintainability": "减少耦合，提高模块化",
                    "cost_efficiency": "优化算法，减少资源消耗",
                }

                suggestion = suggestion_map.get(dim_name, f"改进{dim_name}维度")
                suggestions.append(f"{dim_name}: {suggestion}")

        # 如果所有维度都为1，添加保持建议
        if state == self.perfect_state:
            suggestions.append("所有维度优秀，保持当前实践")

        return suggestions

    def _find_optimal_path_to_perfect(self, start_state: int) -> t.List[int]:
        """找到到完美状态的最优路径（格雷编码路径）"""
        if start_state == self.perfect_state:
            return [start_state]

        # 使用BFS在格雷编码空间中搜索
        from collections import deque

        visited = {start_state}
        queue = deque([(start_state, [start_state])])

        while queue:
            current_state, path = queue.popleft()

            # 生成所有可能的下一步状态（汉明距离=1）
            next_states = self._get_neighbor_states(current_state)

            for next_state in next_states:
                if next_state in visited:
                    continue

                new_path = path + [next_state]

                if next_state == self.perfect_state:
                    return new_path

                visited.add(next_state)
                queue.append((next_state, new_path))

        # 如果没有找到路径，返回空列表
        return []

    def _get_neighbor_states(self, state: int) -> t.List[int]:
        """获取所有邻居状态（汉明距离=1）"""
        neighbors = []

        for i in range(self.n_dimensions):
            neighbor = state ^ (1 << i)  # 翻转第i位
            neighbors.append(neighbor)

        return neighbors

    def get_evolution_history(self, limit: t.Optional[int] = None) -> t.List[StateEvolution]:
        """获取演化历史"""
        if limit:
            return self.state_history[-limit:]
        return self.state_history

    def visualize_state_space(self, highlight_states: t.List[int] = None) -> str:
        """可视化状态空间（返回文本表示）"""
        highlight_states = highlight_states or []

        lines = []
        lines.append("=" * 60)
        lines.append("🔄 6维格雷编码状态空间可视化")
        lines.append("=" * 60)
        lines.append("")

        # 显示维度映射
        lines.append("维度映射:")
        for i, dimension in enumerate(self.dimensions):
            lines.append(f"  D{i+1}: {dimension.value}")
        lines.append("")

        # 显示完美状态
        perfect_analysis = self.analyze_state(self.perfect_state)
        lines.append(f"✨ 完美状态:")
        lines.append(f"   二进制: {perfect_analysis.binary_representation}")
        lines.append(f"   格雷码: {perfect_analysis.gray_code_representation}")
        lines.append(f"   质量评分: {perfect_analysis.quality_score:.2f}/10")
        lines.append("")

        # 显示高亮状态
        if highlight_states:
            lines.append("🔍 高亮状态:")
            for state in highlight_states[:5]:  # 最多显示5个
                analysis = self.analyze_state(state)
                lines.append(f"   状态 {state} ({analysis.binary_representation}):")
                lines.append(f"     质量: {analysis.quality_score:.2f}/10")
                lines.append(f"     距离完美: {analysis.evolution_distance} 步")

                # 显示需要改进的维度
                weak_dims = [dim for dim, val in analysis.dimension_values.items() if val == 0]
                if weak_dims:
                    lines.append(f"     待改进: {', '.join(weak_dims[:3])}")
                lines.append("")

        # 显示状态空间统计
        lines.append("📊 状态空间统计:")
        lines.append(f"   总状态数: {self.state_space}")
        lines.append(f"   已记录演化: {len(self.state_history)}")

        if self.state_history:
            recent = self.state_history[-1]
            lines.append(f"   最近演化: {recent.changed_dimension} ({recent.change_magnitude:.2f})")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)

    def save_state_history(self, filepath: str):
        """保存状态历史到文件"""
        history_data = []

        for evolution in self.state_history:
            history_data.append(
                {
                    "from_state": evolution.from_state,
                    "to_state": evolution.to_state,
                    "from_binary": bin(evolution.from_state)[2:].zfill(self.n_dimensions),
                    "to_binary": bin(evolution.to_state)[2:].zfill(self.n_dimensions),
                    "changed_dimension": evolution.changed_dimension,
                    "change_magnitude": evolution.change_magnitude,
                    "timestamp": evolution.timestamp.isoformat(),
                    "context": evolution.context,
                }
            )

        data = {
            "dimensions": [dim.value for dim in self.dimensions],
            "state_space_size": self.state_space,
            "perfect_state": self.perfect_state,
            "perfect_state_binary": bin(self.perfect_state)[2:].zfill(self.n_dimensions),
            "state_history": history_data,
            "saved_at": datetime.now().isoformat(),
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"💾 状态历史已保存到: {filepath}")

    def load_state_history(self, filepath: str) -> bool:
        """从文件加载状态历史"""
        import os

        if not os.path.exists(filepath):
            print(f"⚠️  文件不存在: {filepath}")
            return False

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 验证维度匹配
            loaded_dimensions = data.get("dimensions", [])
            current_dimensions = [dim.value for dim in self.dimensions]

            if loaded_dimensions != current_dimensions:
                print(f"⚠️  维度不匹配: 加载的 {loaded_dimensions} vs 当前的 {current_dimensions}")
                return False

            # 加载演化历史
            self.state_history = []
            for evolution_data in data.get("state_history", []):
                evolution = StateEvolution(
                    from_state=evolution_data["from_state"],
                    to_state=evolution_data["to_state"],
                    changed_dimension=evolution_data["changed_dimension"],
                    change_magnitude=evolution_data["change_magnitude"],
                    timestamp=datetime.fromisoformat(evolution_data["timestamp"]),
                    context=evolution_data.get("context", {}),
                )
                self.state_history.append(evolution)

            print(f"📥 已加载 {len(self.state_history)} 个演化记录")
            return True

        except Exception as e:
            print(f"❌ 加载失败: {e}")
            return False


# 使用示例
if __name__ == "__main__":
    print("🚀 格雷编码状态管理器演示")
    print("=" * 60)

    # 创建状态管理器
    state_manager = GrayCodeStateManager()

    # 示例：初始状态（中等质量）
    initial_scores = {
        "correctness": 7.5,
        "complexity": 6.0,
        "style": 8.0,
        "readability": 7.0,
        "maintainability": 6.5,
        "cost_efficiency": 5.5,
    }

    # 获取初始状态
    initial_state = state_manager.get_state_from_scores(initial_scores, threshold=6.5)
    initial_analysis = state_manager.analyze_state(initial_state)

    print(f"\n📊 初始状态分析:")
    print(f"   状态编码: {initial_state}")
    print(f"   二进制: {initial_analysis.binary_representation}")
    print(f"   格雷码: {initial_analysis.gray_code_representation}")
    print(f"   质量评分: {initial_analysis.quality_score:.2f}/10")
    print(f"   距离完美: {initial_analysis.evolution_distance} 步")

    print(f"\n📝 维度值:")
    for dim, value in initial_analysis.dimension_values.items():
        status = "✅" if value == 1 else "❌"
        print(f"   {status} {dim}: {value}")

    print(f"\n💡 改进建议:")
    for suggestion in initial_analysis.improvement_suggestions[:3]:
        print(f"   • {suggestion}")

    # 演化：改进成本效率
    print(f"\n🔄 演化：改进成本效率维度...")
    new_state, evolution = state_manager.evolve_state(
        current_state=initial_state,
        dimension="cost_efficiency",
        improvement=0.8,  # 显著改进
        context={"improvement_type": "algorithm_optimization"},
    )

    new_analysis = state_manager.analyze_state(new_state)
    print(f"   新状态: {new_state}")
    print(f"   新二进制: {new_analysis.binary_representation}")
    print(f"   新质量评分: {new_analysis.quality_score:.2f}/10")
    print(f"   改进维度: {evolution.changed_dimension}")

    # 再次演化：改进可维护性
    print(f"\n🔄 演化：改进可维护性维度...")
    final_state, evolution2 = state_manager.evolve_state(
        current_state=new_state,
        dimension="maintainability",
        improvement=0.6,
        context={"improvement_type": "code_refactoring"},
    )

    final_analysis = state_manager.analyze_state(final_state)
    print(f"   最终状态: {final_state}")
    print(f"   最终二进制: {final_analysis.binary_representation}")
    print(f"   最终质量评分: {final_analysis.quality_score:.2f}/10")
    print(f"   距离完美: {final_analysis.evolution_distance} 步")

    # 显示到完美状态的最优路径
    print(f"\n🗺️  到完美状态的最优路径 ({initial_state} → {state_manager.perfect_state}):")
    optimal_path = state_manager._find_optimal_path_to_perfect(final_state)
    if optimal_path:
        print(f"   需要 {len(optimal_path)-1} 步:")
        for i, state in enumerate(optimal_path[:5]):  # 最多显示5步
            binary = bin(state)[2:].zfill(state_manager.n_dimensions)
            print(f"     步骤{i}: {state} ({binary})")

        if len(optimal_path) > 5:
            print(f"     ... 还有 {len(optimal_path)-5} 步")
    else:
        print("   未找到路径")

    # 可视化状态空间
    print(f"\n" + "=" * 60)
    visualization = state_manager.visualize_state_space(
        highlight_states=[initial_state, new_state, final_state]
    )
    print(visualization)

    # 保存状态历史
    state_manager.save_state_history("/tmp/gray_code_state_history.json")

    print(f"\n🎉 演示完成！")
    print(f"   演化历史已保存到 /tmp/gray_code_state_history.json")
