#!/usr/bin/env python3
"""状态转换测试场景设计
测试64卦状态管理器的各种转换场景"""

import os
import sys

sys.path.append(os.path.dirname(__file__))


def test_basic_state_validation():
    """测试基本状态验证"""
    print("=== 测试基本状态验证 ===")

    from external.ROMA.hexagram_state_manager import HexagramStateManager

    # 测试1: 有效状态初始化
    try:
        manager = HexagramStateManager("000000")
        print("✅ 有效状态初始化成功: 000000")
    except Exception as e:
        print(f"❌ 有效状态初始化失败: {e}")
        return False

    # 测试2: 无效状态初始化（长度错误）
    try:
        manager = HexagramStateManager("00000")  # 5位
        print("❌ 无效状态（长度错误）初始化成功，应该失败")
        return False
    except ValueError as e:
        print(f"✅ 无效状态（长度错误）正确拒绝: {e}")

    # 测试3: 无效状态初始化（非法字符）
    try:
        manager = HexagramStateManager("00000a")  # 包含非0/1字符
        print("❌ 无效状态（非法字符）初始化成功，应该失败")
        return False
    except ValueError as e:
        print(f"✅ 无效状态（非法字符）正确拒绝: {e}")

    # 测试4: 无效状态初始化（不在64卦中）
    try:
        manager = HexagramStateManager("101010")  # 检查是否在HEXAGRAMS中
        # 注意：101010可能是一个有效卦象，需要检查
        print(f"✅ 状态初始化成功（可能在64卦中）")
    except ValueError as e:
        print(f"✅ 无效卦象状态正确拒绝: {e}")

    return True


def test_hamming_distance():
    """测试汉明距离计算"""
    print("\n=== 测试汉明距离计算 ===")

    from external.ROMA.hexagram_state_manager import HexagramStateManager

    test_cases = [
        ("000000", "000000", 0),  # 相同状态
        ("000000", "000001", 1),  # 最后一位不同
        ("000000", "100000", 1),  # 第一位不同
        ("010101", "101010", 6),  # 所有位都不同
        ("111111", "111110", 1),  # 一位不同
        ("001100", "001101", 1),  # 一位不同
    ]

    all_passed = True
    for state1, state2, expected in test_cases:
        try:
            distance = HexagramStateManager.hamming_distance(state1, state2)
            if distance == expected:
                print(f"✅ 汉明距离: {state1} -> {state2} = {distance} (期望: {expected})")
            else:
                print(f"❌ 汉明距离错误: {state1} -> {state2} = {distance} (期望: {expected})")
                all_passed = False
        except Exception as e:
            print(f"❌ 计算汉明距离时异常: {state1} -> {state2}: {e}")
            all_passed = False

    # 测试长度不一致的错误处理
    try:
        HexagramStateManager.hamming_distance("00000", "000000")
        print("❌ 长度不一致应该抛出异常")
        all_passed = False
    except ValueError as e:
        print(f"✅ 长度不一致正确抛出异常: {e}")

    return all_passed


def test_valid_transitions():
    """测试有效转换获取"""
    print("\n=== 测试有效转换获取 ===")

    from external.ROMA.hexagram_state_manager import HexagramStateManager

    # 测试从坤卦(000000)出发的有效转换
    manager = HexagramStateManager("000000")
    valid_transitions = manager.get_valid_transitions()

    print(f"当前状态: {manager.current_state} ({manager.get_hexagram_name()})")
    print(f"有效转换数量: {len(valid_transitions)}")

    # 坤卦(000000)应该有6个有效转换（改变任何一位）
    if len(valid_transitions) == 6:
        print("✅ 有效转换数量正确: 6")
    else:
        print(f"❌ 有效转换数量错误: {len(valid_transitions)} (期望: 6)")
        return False

    # 验证每个转换的汉明距离都为1
    for state in valid_transitions:
        distance = HexagramStateManager.hamming_distance(manager.current_state, state)
        if distance == 1:
            print(f"  ✅ {state} ({manager.get_hexagram_name(state)}) - 汉明距离: 1")
        else:
            print(f"  ❌ {state} - 汉明距离: {distance} (应该为1)")
            return False

    # 测试从其他状态出发
    test_states = ["111111", "010101", "101010"]
    for test_state in test_states:
        try:
            manager2 = HexagramStateManager(test_state)
            transitions = manager2.get_valid_transitions()
            print(
                f"\n状态 {test_state} ({manager2.get_hexagram_name()}) 的有效转换: {len(transitions)} 个"
            )

            # 验证每个转换
            valid_count = 0
            for state in transitions:
                distance = HexagramStateManager.hamming_distance(test_state, state)
                if distance == 1:
                    valid_count += 1

            if valid_count == len(transitions):
                print(f"  ✅ 所有转换汉明距离为1")
            else:
                print(f"  ❌ {len(transitions)-valid_count} 个转换汉明距离不为1")
                return False

        except Exception as e:
            print(f"❌ 测试状态 {test_state} 时出错: {e}")
            return False

    return True


def test_state_transitions():
    """测试状态转换执行"""
    print("\n=== 测试状态转换执行 ===")

    from external.ROMA.hexagram_state_manager import HexagramStateManager

    # 测试1: 有效转换（汉明距离=1）
    manager = HexagramStateManager("000000")
    print(f"初始状态: {manager.current_state} ({manager.get_hexagram_name()})")

    # 转换到有效状态（改变最后一位）
    success = manager.transition("000001")
    if success:
        print(f"✅ 有效转换成功: 000000 -> 000001 ({manager.get_hexagram_name()})")
        print(f"   当前状态: {manager.current_state}")
    else:
        print("❌ 有效转换失败")
        return False

    # 测试2: 无效转换（汉明距离>1）
    success = manager.transition("000111")  # 汉明距离=2
    if not success:
        print("✅ 无效转换（汉明距离=2）正确拒绝")
    else:
        print("❌ 无效转换（汉明距离=2）不应该成功")
        return False

    # 测试3: 无效状态转换
    success = manager.transition("00000a")  # 非法字符
    if not success:
        print("✅ 无效状态（非法字符）转换正确拒绝")
    else:
        print("❌ 无效状态转换不应该成功")
        return False

    # 测试4: 序列转换
    manager2 = HexagramStateManager("000000")
    transition_sequence = ["000001", "000011", "000010", "000000"]

    print(f"\n测试序列转换:")
    print(f"  起始: {manager2.current_state} ({manager2.get_hexagram_name()})")

    all_success = True
    for i, next_state in enumerate(transition_sequence, 1):
        success = manager2.transition(next_state)
        if success:
            print(f"  步骤{i}: -> {next_state} ({manager2.get_hexagram_name()})")
        else:
            print(f"  步骤{i}: 转换到 {next_state} 失败")
            all_success = False
            break

    if all_success:
        print("✅ 序列转换全部成功")
    else:
        print("❌ 序列转换失败")
        return False

    # 检查状态历史
    if len(manager2.state_history) == len(transition_sequence):
        print(f"✅ 状态历史记录正确: {len(manager2.state_history)} 条记录")
    else:
        print(
            f"❌ 状态历史记录错误: {len(manager2.state_history)} 条记录 (期望: {len(transition_sequence)})"
        )
        return False

    return True


def test_gray_code_compliance():
    """测试格雷编码合规性"""
    print("\n=== 测试格雷编码合规性 ===")

    # 测试随机状态转换序列的格雷码合规性
    import random

    from external.ROMA.hexagram_state_manager import HexagramStateManager

    manager = HexagramStateManager("000000")
    states = list(manager.HEXAGRAMS.keys())

    # 选择一些随机测试
    test_count = 10
    compliant_count = 0

    print(f"执行 {test_count} 次随机状态转换测试:")

    for i in range(test_count):
        # 随机选择一个起始状态
        start_state = random.choice(states)
        manager = HexagramStateManager(start_state)

        # 获取有效转换
        valid_transitions = manager.get_valid_transitions()
        if not valid_transitions:
            print(f"  测试{i+1}: 状态 {start_state} 无有效转换，跳过")
            continue

        # 随机选择一个有效转换
        next_state = random.choice(valid_transitions)

        # 执行转换
        success = manager.transition(next_state)

        if success:
            # 检查汉明距离
            distance = HexagramStateManager.hamming_distance(start_state, next_state)
            if distance == 1:
                compliant_count += 1
                print(f"  测试{i+1}: ✅ {start_state} -> {next_state} (距离: {distance})")
            else:
                print(f"  测试{i+1}: ❌ {start_state} -> {next_state} (距离: {distance}, 应该为1)")
        else:
            print(f"  测试{i+1}: ❌ 转换失败: {start_state} -> {next_state}")

    compliance_rate = compliant_count / test_count if test_count > 0 else 0
    print(f"\n格雷编码合规率: {compliance_rate:.1%} ({compliant_count}/{test_count})")

    if compliance_rate == 1.0:
        print("✅ 所有随机转换符合格雷编码")
        return True
    else:
        print(f"⚠️  部分转换不符合格雷编码")
        # 注意：如果起始状态没有有效转换，这不一定是失败
        return compliant_count == test_count  # 所有实际执行的转换都合规


def test_edge_cases():
    """测试边界情况"""
    print("\n=== 测试边界情况 ===")

    from external.ROMA.hexagram_state_manager import HexagramStateManager

    # 测试全0到全1的转换（应该失败，汉明距离=6）
    manager = HexagramStateManager("000000")
    success = manager.transition("111111")
    if not success:
        print("✅ 全0到全1转换正确拒绝（汉明距离=6）")
    else:
        print("❌ 全0到全1转换不应该成功")
        return False

    # 测试相同状态转换（应该失败，汉明距离=0）
    success = manager.transition("000000")
    if not success:
        print("✅ 相同状态转换正确拒绝（汉明距离=0）")
    else:
        print("❌ 相同状态转换不应该成功")
        return False

    # 测试有效边界转换
    # 从全0转换到只改变一位的状态
    test_cases = [
        ("000000", "100000"),  # 改变第一位
        ("000000", "010000"),  # 改变第二位
        ("000000", "001000"),  # 改变第三位
        ("111111", "011111"),  # 从全1改变第一位
        ("111111", "101111"),  # 从全1改变第二位
    ]

    for from_state, to_state in test_cases:
        try:
            manager = HexagramStateManager(from_state)
            success = manager.transition(to_state)
            if success:
                print(f"✅ 边界转换 {from_state} -> {to_state} 成功")
            else:
                print(f"❌ 边界转换 {from_state} -> {to_state} 失败（应该成功）")
                return False
        except Exception as e:
            print(f"❌ 边界转换 {from_state} -> {to_state} 异常: {e}")
            return False

    return True


def main():
    """主测试函数"""
    print("开始状态转换测试场景验证")
    print("=" * 60)

    test_functions = [
        ("基本状态验证", test_basic_state_validation),
        ("汉明距离计算", test_hamming_distance),
        ("有效转换获取", test_valid_transitions),
        ("状态转换执行", test_state_transitions),
        ("格雷编码合规性", test_gray_code_compliance),
        ("边界情况测试", test_edge_cases),
    ]

    results = []
    for test_name, test_func in test_functions:
        try:
            print(f"\n{'='*60}")
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ 测试 {test_name} 异常: {e}")
            import traceback

            traceback.print_exc()
            results.append((test_name, False))

    # 汇总结果
    print(f"\n{'='*60}")
    print("测试结果汇总:")
    all_passed = True
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {test_name}: {status}")
        if not success:
            all_passed = False

    if all_passed:
        print("\n🎉 所有状态转换测试通过！")
        # 更新Task #26状态
        print("\n状态转换测试场景设计完成，可以更新Task #26为completed")
    else:
        print("\n❌ 部分测试失败，需要修复")
        sys.exit(1)


if __name__ == "__main__":
    main()
