#!/usr/bin/env python3
"""
卦象缓存模块 - Phase 22优化措施1: 卦象缓存机制

提供汉明距离矩阵、最短路径缓存和河图-卦象最优映射缓存，
将实时计算从O(n)降低到O(1)查找。
"""

import time
from typing import Dict, List, Optional, Set, Tuple
from enum import IntEnum

from integrated_hexagram_state_manager import HetuState, IntegratedHexagramStateManager


class HammingDistanceMatrix:
    """64×64汉明距离缓存矩阵"""

    def __init__(self):
        # 使用字节数组存储，每个距离值0-6，3位足够
        # 64×64 = 4096字节 ≈ 4KB
        self.matrix = bytearray(64 * 64)
        self._precomputed = False

    def precompute(self) -> None:
        """预计算所有卦象对之间的汉明距离"""
        if self._precomputed:
            return

        print("  预计算汉明距离矩阵...")
        start_time = time.time()

        for i in range(64):
            bin_i = f"{i:06b}"  # 6位二进制表示
            for j in range(64):
                bin_j = f"{j:06b}"
                # 计算汉明距离
                distance = 0
                for bit_i, bit_j in zip(bin_i, bin_j):
                    if bit_i != bit_j:
                        distance += 1
                self.matrix[i * 64 + j] = distance

        elapsed = time.time() - start_time
        print(f"  汉明距离矩阵预计算完成，耗时 {elapsed:.3f}秒")
        self._precomputed = True

    def get(self, hexagram1: int, hexagram2: int) -> int:
        """获取两个卦象编码之间的汉明距离"""
        if not self._precomputed:
            self.precompute()
        return self.matrix[hexagram1 * 64 + hexagram2]

    def get_by_binary(self, bin1: str, bin2: str) -> int:
        """通过二进制字符串获取汉明距离"""
        i = int(bin1, 2)
        j = int(bin2, 2)
        return self.get(i, j)

    def get_all_distances_from(self, source_hexagram: int) -> List[int]:
        """获取从源卦象到所有卦象的距离列表"""
        if not self._precomputed:
            self.precompute()

        start_idx = source_hexagram * 64
        return list(self.matrix[start_idx : start_idx + 64])

    def memory_usage(self) -> int:
        """返回内存使用量（字节）"""
        return len(self.matrix)


class ShortestPathMatrix:
    """64×64最短路径缓存矩阵"""

    def __init__(self, hexagram_manager: IntegratedHexagramStateManager):
        self.hexagram_manager = hexagram_manager
        # 存储下一跳状态，-1表示直接可达或不可达
        # 使用有向图，因为路径可能不对称（格雷编码约束）
        self.next_hop = [-1] * (64 * 64)  # 使用-1表示None，减少内存
        self.distance = bytearray(64 * 64)  # 存储距离值
        self._precomputed = False

    def _build_transition_graph(self) -> Dict[int, List[int]]:
        """构建状态转移图（格雷编码约束）"""
        graph = {i: [] for i in range(64)}

        for i in range(64):
            bin_i = f"{i:06b}"
            # 生成所有可能的下一步状态（只改变1位）
            for bit_idx in range(6):
                bits = list(bin_i)
                bits[bit_idx] = "1" if bits[bit_idx] == "0" else "0"
                bin_j = "".join(bits)
                j = int(bin_j, 2)

                # 检查是否为有效状态
                if self.hexagram_manager._validate_state(bin_j):
                    graph[i].append(j)

        return graph

    def precompute(self) -> None:
        """预计算所有状态对的最短路径（Dijkstra算法）"""
        if self._precomputed:
            return

        print("  预计算最短路径矩阵...")
        start_time = time.time()

        graph = self._build_transition_graph()

        # 对每个状态作为起点运行BFS（因为所有边权重为1，BFS即可）
        for source in range(64):
            self._bfs_from_source(source, graph)

        elapsed = time.time() - start_time
        print(f"  最短路径矩阵预计算完成，耗时 {elapsed:.3f}秒")
        self._precomputed = True

    def _bfs_from_source(self, source: int, graph: Dict[int, List[int]]) -> None:
        """从源状态运行BFS，填充距离和下一跳"""
        from collections import deque

        visited = [False] * 64
        distance = [-1] * 64
        next_hop = [-1] * 64

        queue = deque([source])
        visited[source] = True
        distance[source] = 0
        next_hop[source] = source  # 自环

        while queue:
            current = queue.popleft()

            for neighbor in graph[current]:
                if not visited[neighbor]:
                    visited[neighbor] = True
                    distance[neighbor] = distance[current] + 1

                    # 记录下一跳：如果是从源直接可达，记录neighbor
                    # 否则记录与current相同的下一跳
                    if current == source:
                        next_hop[neighbor] = neighbor
                    else:
                        next_hop[neighbor] = next_hop[current]

                    queue.append(neighbor)

        # 保存到矩阵
        for target in range(64):
            idx = source * 64 + target
            self.distance[idx] = (
                distance[target] if distance[target] != -1 else 255
            )  # 255表示不可达
            self.next_hop[idx] = next_hop[target]

    def get_path(self, from_hexagram: int, to_hexagram: int) -> List[int]:
        """获取最短路径（卦象编码列表）"""
        if not self._precomputed:
            self.precompute()

        if from_hexagram == to_hexagram:
            return [from_hexagram]

        path = [from_hexagram]
        current = from_hexagram

        while current != to_hexagram:
            next_state = self.next_hop[current * 64 + to_hexagram]
            if next_state == -1:  # 不可达
                return []

            # 避免无限循环
            if next_state == current:
                return []

            path.append(next_state)
            current = next_state

        return path

    def get_path_binary(self, from_state: str, to_state: str) -> List[str]:
        """获取最短路径（二进制字符串列表）"""
        from_code = int(from_state, 2)
        to_code = int(to_state, 2)

        path_codes = self.get_path(from_code, to_code)
        return [f"{code:06b}" for code in path_codes]

    def get_distance(self, from_hexagram: int, to_hexagram: int) -> int:
        """获取最短距离"""
        if not self._precomputed:
            self.precompute()

        distance = self.distance[from_hexagram * 64 + to_hexagram]
        return distance if distance != 255 else -1  # -1表示不可达

    def memory_usage(self) -> int:
        """返回内存使用量（字节）"""
        return len(self.next_hop) * 4 + len(self.distance)  # next_hop是int列表


class HetuHexagramOptimalMapping:
    """河图状态到卦象的最优映射缓存"""

    def __init__(self, hexagram_manager: IntegratedHexagramStateManager):
        self.hexagram_manager = hexagram_manager
        # 缓存结构: (current_hexagram_code, hetu_state_value) -> target_hexagram_code
        self.mapping_cache = {}
        self._precomputed = False

    def precompute(self) -> None:
        """预计算每个卦象到每个河图状态的最优目标"""
        if self._precomputed:
            return

        print("  预计算河图-卦象最优映射...")
        start_time = time.time()

        # 首先构建河图状态到卦象集合的映射
        hetu_to_hexagrams = {}
        for state in HetuState:
            hexagrams = self.hexagram_manager.get_states_by_hetu(state)
            hetu_to_hexagrams[state.value] = [int(h, 2) for h in hexagrams]

        # 为每个可能的当前卦象计算到每个河图状态的最优目标
        hamming_matrix = HammingDistanceMatrix()
        hamming_matrix.precompute()

        for current_code in range(64):
            # 获取当前卦象到所有卦象的距离
            distances = hamming_matrix.get_all_distances_from(current_code)

            for hetu_value, target_codes in hetu_to_hexagrams.items():
                if not target_codes:
                    continue

                # 找到距离最小的目标卦象
                min_distance = float("inf")
                best_target = current_code  # 默认返回当前

                for target_code in target_codes:
                    dist = distances[target_code]
                    if dist < min_distance:
                        min_distance = dist
                        best_target = target_code

                self.mapping_cache[(current_code, hetu_value)] = best_target

        elapsed = time.time() - start_time
        print(f"  河图-卦象最优映射预计算完成，耗时 {elapsed:.3f}秒")
        self._precomputed = True

    def get_nearest(self, current_hexagram: str, target_hetu: HetuState) -> str:
        """获取最近的目标卦象（二进制字符串）"""
        if not self._precomputed:
            self.precompute()

        current_code = int(current_hexagram, 2)
        key = (current_code, target_hetu.value)

        target_code = self.mapping_cache.get(key, current_code)  # 默认返回当前
        return f"{target_code:06b}"

    def memory_usage(self) -> int:
        """返回内存使用量（字节）"""
        # 每个条目：(int, int) -> int，估算
        return len(self.mapping_cache) * (4 + 4 + 4)  # 两个键int + 值int


class HexagramCacheManager:
    """卦象缓存统一管理器"""

    def __init__(self, hexagram_manager: IntegratedHexagramStateManager):
        self.hexagram_manager = hexagram_manager
        self.hamming_matrix = HammingDistanceMatrix()
        self.path_matrix = ShortestPathMatrix(hexagram_manager)
        self.hetu_mapping = HetuHexagramOptimalMapping(hexagram_manager)

        # 初始化标志和版本控制
        self._initialized = False
        self.cache_version = 0

    def initialize(self, force: bool = False) -> None:
        """初始化所有缓存（惰性初始化）"""
        if self._initialized and not force:
            return

        print("🔧 初始化卦象缓存管理器...")
        start_time = time.time()

        self.hamming_matrix.precompute()
        self.path_matrix.precompute()
        self.hetu_mapping.precompute()

        self._initialized = True
        self.cache_version += 1

        elapsed = time.time() - start_time
        print(
            f"✅ 卦象缓存管理器初始化完成，版本 {self.cache_version}，耗时 {elapsed:.3f}秒"
        )

        # 打印内存使用统计
        self.print_memory_usage()

    def hamming_distance(self, state1: str, state2: str) -> int:
        """使用缓存的汉明距离"""
        if not self._initialized:
            self.initialize()
        return self.hamming_matrix.get_by_binary(state1, state2)

    def find_path(self, from_state: str, to_state: str) -> List[str]:
        """使用缓存的最短路径"""
        if not self._initialized:
            self.initialize()
        return self.path_matrix.get_path_binary(from_state, to_state)

    def select_nearest_hexagram(
        self, current_hexagram: str, target_hetu: HetuState
    ) -> str:
        """使用缓存的最优映射"""
        if not self._initialized:
            self.initialize()
        return self.hetu_mapping.get_nearest(current_hexagram, target_hetu)

    def get_distance(self, from_state: str, to_state: str) -> int:
        """获取两个状态之间的最短距离"""
        if not self._initialized:
            self.initialize()

        from_code = int(from_state, 2)
        to_code = int(to_state, 2)
        return self.path_matrix.get_distance(from_code, to_code)

    def is_reachable(self, from_state: str, to_state: str) -> bool:
        """检查是否可达"""
        distance = self.get_distance(from_state, to_state)
        return distance >= 0

    def print_memory_usage(self) -> None:
        """打印内存使用统计"""
        hamming_mem = self.hamming_matrix.memory_usage()
        path_mem = self.path_matrix.memory_usage()
        mapping_mem = self.hetu_mapping.memory_usage()
        total_mem = hamming_mem + path_mem + mapping_mem

        print("📊 缓存内存使用统计:")
        print(f"  汉明距离矩阵: {hamming_mem:,} 字节 ({hamming_mem/1024:.1f} KB)")
        print(f"  最短路径矩阵: {path_mem:,} 字节 ({path_mem/1024:.1f} KB)")
        print(f"  河图-卦象映射: {mapping_mem:,} 字节 ({mapping_mem/1024:.1f} KB)")
        print(f"  总计: {total_mem:,} 字节 ({total_mem/1024:.1f} KB)")


def test_cache_performance() -> None:
    """测试缓存性能"""
    print("=== 卦象缓存性能测试 ===")

    try:
        # 创建卦象管理器
        manager = IntegratedHexagramStateManager("hetu_hexagram_mapping.json")
        manager.initialize_state("000000")

        # 创建缓存管理器
        cache = HexagramCacheManager(manager)
        cache.initialize()

        # 测试1: 汉明距离性能
        print("\n🔍 测试1: 汉明距离计算性能")
        test_pairs = [
            ("000000", "000001"),  # 距离1
            ("000000", "111111"),  # 距离6
            ("010101", "101010"),  # 距离6
            ("001001", "110110"),  # 距离5
        ]

        for state1, state2 in test_pairs:
            distance = cache.hamming_distance(state1, state2)
            print(f"  {state1} → {state2}: 距离 = {distance}")

        # 测试2: 路径查找性能
        print("\n🔍 测试2: 最短路径查找性能")
        test_paths = [
            ("000000", "111111"),  # 最远路径
            ("010101", "101010"),  # 对称路径
            ("001001", "110110"),  # 中等路径
        ]

        for from_state, to_state in test_paths:
            path = cache.find_path(from_state, to_state)
            distance = cache.get_distance(from_state, to_state)
            print(f"  {from_state} → {to_state}:")
            print(f"    距离 = {distance}, 路径长度 = {len(path)}")
            if path and len(path) <= 10:
                print(f"    路径: {' → '.join(path)}")

        # 测试3: 河图-卦象映射性能
        print("\n🔍 测试3: 河图-卦象最优映射")
        test_cases = [
            ("000000", HetuState.INITIAL),
            ("010101", HetuState.COMPLETED),
            ("111111", HetuState.AST_PARSED),
        ]

        for current_hexagram, target_hetu in test_cases:
            nearest = cache.select_nearest_hexagram(current_hexagram, target_hetu)
            print(f"  当前: {current_hexagram}, 目标河图: {target_hetu.name}")
            print(f"    最近卦象: {nearest}")

        # 测试4: 批量性能测试
        print("\n🔍 测试4: 批量计算性能")
        import random

        # 生成1000个随机卦象对
        random_pairs = []
        for _ in range(1000):
            i = random.randint(0, 63)
            j = random.randint(0, 63)
            random_pairs.append((f"{i:06b}", f"{j:06b}"))

        # 测量汉明距离计算时间
        start_time = time.time()
        for state1, state2 in random_pairs:
            _ = cache.hamming_distance(state1, state2)
        hamming_time = time.time() - start_time

        # 测量路径查找时间（只测100个）
        path_pairs = random.sample(random_pairs, 100)
        start_time = time.time()
        for state1, state2 in path_pairs:
            _ = cache.find_path(state1, state2)
        path_time = time.time() - start_time

        print(
            f"  汉明距离计算 (1000次): {hamming_time:.3f}秒 ({hamming_time/1000*1000:.1f}ms/千次)"
        )
        print(f"  路径查找 (100次): {path_time:.3f}秒 ({path_time/100*1000:.1f}ms/次)")

        print("\n🎉 卦象缓存性能测试完成！")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_cache_performance()
