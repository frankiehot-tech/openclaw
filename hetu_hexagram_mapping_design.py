#!/usr/bin/env python3
"""
河图10态到64卦状态映射设计

基于MAREF设计原则，建立河图10态到64卦（6位二进制）状态的映射关系。
映射遵循以下原则：
1. 语义一致性：卦象含义与河图状态语义匹配
2. 渐进性：相邻河图状态映射到相邻卦象（尽可能）
3. 完备性：所有64卦必须映射到某个河图状态
4. 平衡性：每个河图状态映射6-7个卦象
5. 格雷编码连续性：映射卦象之间保持格雷编码相邻关系

设计依据：
- 河图10态：评估流程的10个阶段
- 64卦状态：6个质量维度的二进制表示（2^6=64）
- 格雷编码：确保相邻状态汉明距离=1
"""

import itertools
import json
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Set, Tuple


# 重新定义HetuState枚举（从原文件复制）
class HetuState(IntEnum):
    """河图10态枚举"""

    INITIAL = 1  # 初始状态：评估待开始
    AST_PARSED = 2  # AST解析完成：代码结构已分析
    DIMENSION_ASSESSING = 3  # 维度评估中：各维度评估进行中
    TEST_RUNNING = 4  # 测试执行：运行测试用例
    RESULT_AGGREGATING = 5  # 结果聚合：汇总各维度分数
    STRATEGY_ANALYZING = 6  # 策略分析：成本-质量分析
    TREND_PREDICTING = 7  # 趋势预测：质量演化预测
    REPORT_GENERATING = 8  # 报告生成：可视化报告
    DECISION_SUPPORTING = 9  # 决策支持：优化建议生成
    COMPLETED = 10  # 完成状态：评估结束


# 64卦命名（基于《易经》64卦，简化版本）
HEXAGRAM_NAMES = {
    # 000000-001111 (0-15): 初始阶段相关卦象
    0b000000: "坤 (Kun)",  # 地地坤：纯阴，初始状态
    0b000001: "剥 (Bo)",  # 山地剥：剥落，开始解析
    0b000010: "比 (Bi)",  # 水地比：亲近，建立关系
    0b000011: "观 (Guan)",  # 风地观：观察，审视
    0b000100: "豫 (Yu)",  # 雷地豫：预备，准备评估
    0b000101: "晋 (Jin)",  # 火地晋：晋升，进展
    0b000110: "萃 (Cui)",  # 泽地萃：聚集，收集信息
    0b000111: "否 (Pi)",  # 天地否：闭塞，评估中
    # 001000-001111 (8-15)
    0b001000: "谦 (Qian)",  # 地山谦：谦虚，初步分析
    0b001001: "艮 (Gen)",  # 山山艮：静止，暂停
    0b001010: "蹇 (Jian)",  # 水山蹇：困难，遇到问题
    0b001011: "渐 (Jian)",  # 风山渐：渐进，逐步分析
    0b001100: "小过 (Xiao Guo)",  # 雷山小过：小过失，小错误
    0b001101: "旅 (Lu)",  # 火山旅：旅行，移动
    0b001110: "咸 (Xian)",  # 泽山咸：感应，交互
    0b001111: "遁 (Dun)",  # 天山遁：退避，等待
    # 010000-010111 (16-23): 分析阶段
    0b010000: "师 (Shi)",  # 地水师：领导，开始主导
    0b010001: "蒙 (Meng)",  # 山水蒙：启蒙，学习理解
    0b010010: "坎 (Kan)",  # 水水坎：险陷，深入分析
    0b010011: "涣 (Huan)",  # 风水涣：涣散，分散分析
    0b010100: "解 (Xie)",  # 雷水解：解决，解决问题
    0b010101: "未济 (Wei Ji)",  # 火水未济：未完成，进行中
    0b010110: "困 (Kun)",  # 泽水困：困境，遇到困难
    0b010111: "讼 (Song)",  # 天水讼：争论，争议点
    # 011000-011111 (24-31)
    0b011000: "升 (Sheng)",  # 地风升：上升，提升
    0b011001: "蛊 (Gu)",  # 山风蛊：腐败，发现问题
    0b011010: "井 (Jing)",  # 水风井：水井，资源
    0b011011: "巽 (Xun)",  # 风风巽：顺从，适应
    0b011100: "恒 (Heng)",  # 雷风恒：恒久，稳定
    0b011101: "鼎 (Ding)",  # 火风鼎：鼎器，转变
    0b011110: "大过 (Da Guo)",  # 泽风大过：大过失，大问题
    0b011111: "姤 (Gou)",  # 天风姤：相遇，交汇
    # 100000-100111 (32-39): 执行阶段
    0b100000: "复 (Fu)",  # 地雷复：回复，重新开始
    0b100001: "颐 (Yi)",  # 山雷颐：养育，培养
    0b100010: "屯 (Tun)",  # 水雷屯：初生，新生
    0b100011: "益 (Yi)",  # 风雷益：增益，增加价值
    0b100100: "震 (Zhen)",  # 雷雷震：震动，行动
    0b100101: "噬嗑 (Shi Ke)",  # 火雷噬嗑：咬合，整合
    0b100110: "随 (Sui)",  # 泽雷随：跟随，跟随流程
    0b100111: "无妄 (Wu Wang)",  # 天雷无妄：无妄，真实
    # 101000-101111 (40-47): 评估阶段
    0b101000: "明夷 (Ming Yi)",  # 地火明夷：光明受伤，发现问题
    0b101001: "贲 (Bi)",  # 山火贲：装饰，美化
    0b101010: "离 (Li)",  # 水火离：依附，依赖
    0b101011: "家人 (Jia Ren)",  # 风火家人：家庭，内部协调
    0b101100: "丰 (Feng)",  # 雷火丰：丰盛，丰富成果
    0b101101: "革 (Ge)",  # 火火革：革命，变革
    0b101110: "同人 (Tong Ren)",  # 泽火同人：同仁，协作
    0b101111: "大有 (Da You)",  # 天火大有：大有，丰富收获
    # 110000-110111 (48-55): 优化阶段
    0b110000: "临 (Lin)",  # 地泽临：临近，接近完成
    0b110001: "损 (Sun)",  # 山泽损：减损，优化
    0b110010: "节 (Jie)",  # 水泽节：节制，控制
    0b110011: "中孚 (Zhong Fu)",  # 风泽中孚：诚信，可靠
    0b110100: "归妹 (Gui Mei)",  # 雷泽归妹：归妹，回归
    0b110101: "睽 (Kui)",  # 火泽睽：乖离，分歧
    0b110110: "兑 (Dui)",  # 泽泽兑：喜悦，满意
    0b110111: "履 (Lü)",  # 天泽履：履行，执行
    # 111000-111111 (56-63): 完成阶段
    0b111000: "泰 (Tai)",  # 地天泰：通达，顺利
    0b111001: "大畜 (Da Xu)",  # 山天大畜：大积蓄，大积累
    0b111010: "需 (Xu)",  # 水天需：等待，待命
    0b111011: "小畜 (Xiao Xu)",  # 风天小畜：小积蓄，小积累
    0b111100: "大壮 (Da Zhuang)",  # 雷天大壮：大壮，强大
    0b111101: "夬 (Guai)",  # 火天夬：决断，决定
    0b111110: "萃 (Cui2)",  # 泽天萃：聚集（高级），成果汇集
    0b111111: "乾 (Qian)",  # 天天乾：纯阳，完美状态
}


@dataclass
class HexagramMapping:
    """64卦映射定义"""

    hexagram_code: int  # 6位二进制编码 (0-63)
    binary_str: str  # 二进制字符串表示
    hexagram_name: str  # 卦象名称
    dimension_values: Dict[str, int]  # 6个维度的值 (0/1)
    hetu_state: HetuState  # 对应的河图状态
    semantic_description: str  # 语义描述


# 6个质量维度（与GrayCodeStateManager一致）
DIMENSIONS = [
    "correctness",  # D1: 正确性
    "complexity",  # D2: 复杂度
    "style",  # D3: 风格
    "readability",  # D4: 可读性
    "maintainability",  # D5: 可维护性
    "cost_efficiency",  # D6: 成本效率
]


def generate_gray_codes(n: int) -> List[int]:
    """生成n位格雷编码序列"""
    if n == 0:
        return [0]
    smaller = generate_gray_codes(n - 1)
    return smaller + [x | (1 << (n - 1)) for x in reversed(smaller)]


def binary_to_dimension_values(binary_str: str) -> Dict[str, int]:
    """将二进制字符串转换为维度值字典"""
    return {dim: int(bit) for dim, bit in zip(DIMENSIONS, binary_str)}


def create_mapping_table() -> List[HexagramMapping]:
    """创建河图10态到64卦的映射表

    使用简单的范围分配，确保每个河图状态有6-7个卦象
    分配原则（6个状态各6卦象，4个状态各7卦象）：
    1. INITIAL (1): 0-5 (6个卦象)
    2. AST_PARSED (2): 6-12 (7个卦象)
    3. DIMENSION_ASSESSING (3): 13-18 (6个卦象)
    4. TEST_RUNNING (4): 19-25 (7个卦象)
    5. RESULT_AGGREGATING (5): 26-31 (6个卦象)
    6. STRATEGY_ANALYZING (6): 32-38 (7个卦象)
    7. TREND_PREDICTING (7): 39-44 (6个卦象)
    8. REPORT_GENERATING (8): 45-50 (6个卦象)
    9. DECISION_SUPPORTING (9): 51-56 (6个卦象)
    10. COMPLETED (10): 57-63 (7个卦象)
    """

    mapping_table = []

    # 为每个卦象（0-63）分配河图状态
    for code in range(64):
        binary_str = bin(code)[2:].zfill(6)
        dimension_values = binary_to_dimension_values(binary_str)

        # 基于code范围的简单分配
        if code <= 5:  # 0-5 (6个卦象)
            hetu_state = HetuState.INITIAL
        elif code <= 12:  # 6-12 (7个卦象)
            hetu_state = HetuState.AST_PARSED
        elif code <= 18:  # 13-18 (6个卦象)
            hetu_state = HetuState.DIMENSION_ASSESSING
        elif code <= 25:  # 19-25 (7个卦象)
            hetu_state = HetuState.TEST_RUNNING
        elif code <= 31:  # 26-31 (6个卦象)
            hetu_state = HetuState.RESULT_AGGREGATING
        elif code <= 38:  # 32-38 (7个卦象)
            hetu_state = HetuState.STRATEGY_ANALYZING
        elif code <= 44:  # 39-44 (6个卦象)
            hetu_state = HetuState.TREND_PREDICTING
        elif code <= 50:  # 45-50 (6个卦象)
            hetu_state = HetuState.REPORT_GENERATING
        elif code <= 56:  # 51-56 (6个卦象)
            hetu_state = HetuState.DECISION_SUPPORTING
        else:  # 57-63 (7个卦象)
            hetu_state = HetuState.COMPLETED

        hexagram_name = HEXAGRAM_NAMES.get(code, f"卦{code:06b}")
        semantic_desc = describe_semantics(code, hetu_state, dimension_values)

        mapping = HexagramMapping(
            hexagram_code=code,
            binary_str=binary_str,
            hexagram_name=hexagram_name,
            dimension_values=dimension_values,
            hetu_state=hetu_state,
            semantic_description=semantic_desc,
        )
        mapping_table.append(mapping)

    return mapping_table


def describe_semantics(code: int, hetu_state: HetuState, dim_vals: Dict[str, int]) -> str:
    """生成语义描述"""
    active_dims = [dim for dim, val in dim_vals.items() if val == 1]
    inactive_dims = [dim for dim, val in dim_vals.items() if val == 0]

    desc = f"河图状态: {hetu_state.name} ({hetu_state.value})"
    desc += f", 激活维度: {len(active_dims)}个"
    if active_dims:
        desc += f" ({', '.join(active_dims[:3])}"
        if len(active_dims) > 3:
            desc += f" 等)"
        else:
            desc += ")"

    # 根据状态添加特定描述
    if hetu_state == HetuState.INITIAL:
        desc += " - 评估流程开始，所有维度待评估"
    elif hetu_state == HetuState.AST_PARSED:
        desc += " - AST解析完成，开始维度分析"
    elif hetu_state == HetuState.DIMENSION_ASSESSING:
        desc += " - 维度评估进行中"
    elif hetu_state == HetuState.TEST_RUNNING:
        desc += " - 测试执行阶段"
    elif hetu_state == HetuState.RESULT_AGGREGATING:
        desc += " - 结果聚合分析"
    elif hetu_state == HetuState.STRATEGY_ANALYZING:
        desc += " - 策略成本-质量分析"
    elif hetu_state == HetuState.TREND_PREDICTING:
        desc += " - 质量演化趋势预测"
    elif hetu_state == HetuState.REPORT_GENERATING:
        desc += " - 可视化报告生成"
    elif hetu_state == HetuState.DECISION_SUPPORTING:
        desc += " - 优化决策支持"
    elif hetu_state == HetuState.COMPLETED:
        desc += " - 评估流程完成"

    return desc


def validate_mapping(mapping_table: List[HexagramMapping]) -> Tuple[bool, List[str]]:
    """验证映射表的有效性"""
    errors = []

    # 检查每个河图状态的卦象数量
    state_counts = {}
    for mapping in mapping_table:
        state = mapping.hetu_state
        state_counts[state] = state_counts.get(state, 0) + 1

    # 每个河图状态应该有6-7个卦象
    for state, count in state_counts.items():
        if count < 6 or count > 7:
            errors.append(f"河图状态 {state.name} 有 {count} 个卦象，期望6-7个")

    # 检查所有64卦都有映射
    if len(mapping_table) != 64:
        errors.append(f"映射表包含 {len(mapping_table)} 个卦象，期望64个")

    # 检查卦象编码唯一性
    codes = [m.hexagram_code for m in mapping_table]
    if len(set(codes)) != 64:
        errors.append("卦象编码不唯一")

    return len(errors) == 0, errors


def generate_state_transition_graph() -> Dict[int, List[int]]:
    """生成格雷编码状态转移图（汉明距离=1）"""
    graph = {}

    for code in range(64):
        neighbors = []
        # 检查所有汉明距离为1的邻居
        for i in range(6):
            neighbor = code ^ (1 << i)  # 翻转第i位
            neighbors.append(neighbor)
        graph[code] = neighbors

    return graph


def main():
    """主函数：生成和验证映射设计"""
    print("🎯 河图10态到64卦状态映射设计")
    print("=" * 70)

    # 生成映射表
    print("🔧 生成映射表...")
    mapping_table = create_mapping_table()

    # 验证映射
    print("✅ 验证映射有效性...")
    is_valid, errors = validate_mapping(mapping_table)

    if not is_valid:
        print("❌ 映射验证失败:")
        for error in errors:
            print(f"   - {error}")
        return

    print("✅ 映射验证通过")

    # 统计信息
    print("\n📊 映射统计:")
    state_counts = {}
    for mapping in mapping_table:
        state = mapping.hetu_state
        state_counts[state] = state_counts.get(state, 0) + 1

    for state in HetuState:
        count = state_counts.get(state, 0)
        print(f"  {state.name:20} ({state.value:2}): {count:2} 个卦象")

    # 生成状态转移图
    print("\n🔗 生成状态转移图...")
    transition_graph = generate_state_transition_graph()
    print(f"  状态转移图包含 {len(transition_graph)} 个状态节点")

    # 保存映射表到JSON文件
    output_data = {
        "mapping_version": "1.0",
        "generated_at": "2026-04-19",
        "description": "河图10态到64卦（6位二进制）状态映射",
        "mappings": [
            {
                "hexagram_code": m.hexagram_code,
                "binary": m.binary_str,
                "hexagram_name": m.hexagram_name,
                "dimension_values": m.dimension_values,
                "hetu_state": m.hetu_state.name,
                "hetu_state_value": m.hetu_state.value,
                "semantic_description": m.semantic_description,
            }
            for m in mapping_table
        ],
        "transition_graph": transition_graph,
    }

    output_file = "hetu_hexagram_mapping.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n💾 映射表已保存到: {output_file}")

    # 显示示例映射
    print("\n📋 示例映射（每个河图状态的前2个卦象）:")
    for state in HetuState:
        state_mappings = [m for m in mapping_table if m.hetu_state == state]
        if state_mappings:
            print(f"\n{state.name} ({state.value}): {state_mappings[0].semantic_description}")
            for i, mapping in enumerate(state_mappings[:2]):
                active_dims = [dim for dim, val in mapping.dimension_values.items() if val == 1]
                print(f"  卦象{i+1}: {mapping.hexagram_name} ({mapping.binary_str})")
                print(f"     激活维度: {', '.join(active_dims) if active_dims else '无'}")

    print("\n" + "=" * 70)
    print("🎉 映射设计完成！下一步：")
    print("  1. 使用此映射表实现HexagramStateManager")
    print("  2. 创建HetuToHexagramAdapter适配器层")
    print("  3. 更新河图洛书调度器使用64卦状态")
    print("  4. 验证状态转移的格雷编码连续性")


if __name__ == "__main__":
    main()
