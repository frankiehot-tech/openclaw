# 卦象缓存机制设计文档

**设计目标**: 减少实时卦象计算开销，将汉明距离计算、路径查找和卦象选择等操作从O(n)降低到O(1)
**预期效果**: 将卦象状态计算开销从2.0%降低到0.2%

## 1. 缓存数据结构设计

### 1.1 汉明距离矩阵 (HammingDistanceMatrix)
```python
class HammingDistanceMatrix:
    """64×64汉明距离缓存矩阵"""
    
    def __init__(self):
        # 使用字节数组存储，每个距离值0-6，3位足够
        self.matrix = bytearray(64 * 64)  # 4096 bytes ≈ 4KB
    
    def precompute(self):
        """预计算所有卦象对之间的汉明距离"""
        for i in range(64):
            bin_i = f"{i:06b}"  # 6位二进制表示
            for j in range(64):
                bin_j = f"{j:06b}"
                distance = sum(bit_i != bit_j for bit_i, bit_j in zip(bin_i, bin_j))
                self.set(i, j, distance)
    
    def get(self, hexagram1: int, hexagram2: int) -> int:
        """获取两个卦象之间的汉明距离"""
        return self.matrix[hexagram1 * 64 + hexagram2]
    
    def set(self, hexagram1: int, hexagram2: int, distance: int):
        """设置汉明距离"""
        self.matrix[hexagram1 * 64 + hexagram2] = distance
    
    def get_by_binary(self, bin1: str, bin2: str) -> int:
        """通过二进制字符串获取汉明距离"""
        i = int(bin1, 2)
        j = int(bin2, 2)
        return self.get(i, j)
```

**内存占用**: 64×64 = 4096字节（4KB）
**查找时间复杂度**: O(1)
**预计算时间**: 64×64×6 = 24,576次比较（可忽略）

### 1.2 最短路径矩阵 (ShortestPathMatrix)
```python
class ShortestPathMatrix:
    """64×64最短路径缓存矩阵"""
    
    def __init__(self):
        # 存储下一跳状态，None表示直接可达或不可达
        # 使用有向图，因为路径可能不对称（格雷编码约束）
        self.next_hop = [None] * (64 * 64)
        self.distance = bytearray(64 * 64)  # 存储距离值
    
    def precompute(self, hexagram_manager):
        """预计算所有状态对的最短路径（Dijkstra算法）"""
        # 构建状态转移图（格雷编码约束）
        graph = self._build_transition_graph(hexagram_manager)
        
        # 对每个状态作为起点运行Dijkstra
        for source in range(64):
            self._dijkstra(source, graph)
    
    def get_path(self, from_hexagram: int, to_hexagram: int) -> List[int]:
        """获取最短路径（卦象编码列表）"""
        if from_hexagram == to_hexagram:
            return [from_hexagram]
        
        path = [from_hexagram]
        current = from_hexagram
        
        while current != to_hexagram:
            next_state = self.next_hop[current * 64 + to_hexagram]
            if next_state is None:
                return []  # 不可达
            path.append(next_state)
            current = next_state
            
        return path
    
    def get_distance(self, from_hexagram: int, to_hexagram: int) -> int:
        """获取最短距离"""
        return self.distance[from_hexagram * 64 + to_hexagram]
```

**内存占用**: 64×64×(1字节距离+1指针) ≈ 8KB（使用优化存储）
**路径重建**: O(L)其中L为路径长度

### 1.3 河图-卦象最优映射缓存 (HetuHexagramOptimalMapping)
```python
class HetuHexagramOptimalMapping:
    """河图状态到卦象的最优映射缓存"""
    
    def __init__(self, hexagram_manager):
        self.hexagram_manager = hexagram_manager
        # 缓存结构: hetu_state -> {hexagram -> nearest_hexagram_for_each_hetu}
        self.mapping_cache = {}
        
    def precompute(self):
        """预计算每个卦象到每个河图状态的最优目标"""
        for hetu_state in HetuState:
            target_hexagrams = self.hexagram_manager.get_states_by_hetu(hetu_state)
            if not target_hexagrams:
                continue
                
            # 为每个可能的当前卦象计算最近目标
            for current_hexagram in range(64):
                bin_current = f"{current_hexagram:06b}"
                # 找到最近的目标卦象
                nearest = self._find_nearest(bin_current, target_hexagrams)
                self.mapping_cache[(current_hexagram, hetu_state.value)] = nearest
    
    def get_nearest(self, current_hexagram: str, target_hetu: HetuState) -> str:
        """获取最近的目标卦象"""
        current_code = int(current_hexagram, 2)
        key = (current_code, target_hetu.value)
        return self.mapping_cache.get(key, current_hexagram)  # 默认返回当前
```

**内存占用**: 64卦象 × 10河图状态 = 640个映射（每个映射存储目标卦象编码）
**查找时间复杂度**: O(1)

## 2. 缓存集成设计

### 2.1 缓存管理器 (HexagramCacheManager)
```python
class HexagramCacheManager:
    """卦象缓存统一管理器"""
    
    def __init__(self, hexagram_manager):
        self.hexagram_manager = hexagram_manager
        self.hamming_matrix = HammingDistanceMatrix()
        self.path_matrix = ShortestPathMatrix()
        self.hetu_mapping = HetuHexagramOptimalMapping(hexagram_manager)
        
        # 初始化标志
        self._initialized = False
        
    def initialize(self):
        """初始化所有缓存（惰性初始化）"""
        if self._initialized:
            return
            
        print("🔧 初始化卦象缓存...")
        start_time = time.time()
        
        self.hamming_matrix.precompute()
        self.path_matrix.precompute(self.hexagram_manager)
        self.hetu_mapping.precompute()
        
        elapsed = time.time() - start_time
        print(f"✅ 卦象缓存初始化完成，耗时 {elapsed:.3f}秒")
        self._initialized = True
        
    def hamming_distance(self, state1: str, state2: str) -> int:
        """使用缓存的汉明距离"""
        if not self._initialized:
            self.initialize()
        return self.hamming_matrix.get_by_binary(state1, state2)
    
    def find_path(self, from_state: str, to_state: str) -> List[str]:
        """使用缓存的最短路径"""
        if not self._initialized:
            self.initialize()
            
        from_code = int(from_state, 2)
        to_code = int(to_state, 2)
        
        path_codes = self.path_matrix.get_path(from_code, to_code)
        return [f"{code:06b}" for code in path_codes]
    
    def select_nearest_hexagram(self, current_hexagram: str, target_hetu: HetuState) -> str:
        """使用缓存的最优映射"""
        if not self._initialized:
            self.initialize()
        return self.hetu_mapping.get_nearest(current_hexagram, target_hetu)
```

### 2.2 与现有系统的集成

#### 集成点1: 替换实时汉明距离计算
```python
# integrated_hexagram_state_manager.py 修改
class IntegratedHexagramStateManager:
    def __init__(self, mapping_file_path: str = "hetu_hexagram_mapping.json"):
        # ... 现有初始化 ...
        self.cache_manager = HexagramCacheManager(self)
        
    def hamming_distance(self, state1: str, state2: str) -> int:
        """使用缓存版本（可选）"""
        # 保持静态方法兼容性，但内部使用缓存
        return self.cache_manager.hamming_distance(state1, state2)
```

#### 集成点2: 优化路径查找
```python
# hetu_hexagram_adapter.py 修改
class HetuToHexagramAdapter:
    def _find_hexagram_path(self, from_hexagram: str, to_hexagram: str, max_steps: int = 10) -> List[str]:
        """使用缓存路径查找"""
        # 首先尝试从缓存获取
        cached_path = self.hexagram_manager.cache_manager.find_path(from_hexagram, to_hexagram)
        if cached_path:
            return cached_path
            
        # 缓存未命中，回退到BFS（应该很少发生）
        return self._find_hexagram_path_fallback(from_hexagram, to_hexagram, max_steps)
```

#### 集成点3: 优化卦象选择
```python
# hetu_hexagram_adapter.py 修改
class HetuToHexagramAdapter:
    def _select_nearest_hexagram(self, current_hexagram: str, target_hexagrams: Set[str]) -> str:
        """使用缓存的最优映射（如果目标河图状态明确）"""
        # 如果target_hexagrams对应单个河图状态，使用缓存
        # 否则回退到原算法
        if len(target_hexagrams) > 0:
            # 尝试推断河图状态
            sample_hexagram = next(iter(target_hexagrams))
            hetu_state = self.hexagram_manager.get_hetu_state(sample_hexagram)
            if hetu_state:
                # 使用缓存映射
                return self.hexagram_manager.cache_manager.select_nearest_hexagram(
                    current_hexagram, hetu_state
                )
        
        # 回退到原算法
        return self._select_nearest_hexagram_fallback(current_hexagram, target_hexagrams)
```

## 3. 缓存更新与失效策略

### 3.1 缓存版本控制
```python
class CacheVersion:
    """缓存版本控制"""
    
    def __init__(self):
        self.mapping_version = 0  # 卦象映射版本
        self.graph_version = 0    # 状态图版本
        
    def update_mapping_version(self):
        """卦象映射更新时调用"""
        self.mapping_version += 1
        
    def update_graph_version(self):
        """状态转移图更新时调用"""
        self.graph_version += 1
```

### 3.2 惰性重新计算
```python
class HexagramCacheManager:
    def __init__(self, hexagram_manager):
        # ... 现有初始化 ...
        self.version = CacheVersion()
        self.last_mapping_version = -1
        
    def check_and_refresh(self):
        """检查并刷新缓存（如果需要）"""
        current_version = self.hexagram_manager.get_mapping_version()
        if current_version != self.last_mapping_version:
            print("🔄 卦象映射已更新，重新计算缓存...")
            self.initialize()
            self.last_mapping_version = current_version
```

## 4. 性能基准测试方案

### 4.1 测试指标
1. **汉明距离计算速度**: 10,000次随机卦象对计算时间
2. **路径查找速度**: 1,000次随机起点-终点对路径查找时间  
3. **卦象选择速度**: 5,000次随机当前卦象到随机河图状态选择时间
4. **内存占用**: 缓存数据结构内存使用量
5. **初始化时间**: 缓存预计算总时间

### 4.2 对比基准
- **基线**: 当前实时计算版本
- **优化后**: 缓存版本
- **预期提升**: 10-100倍速度提升

### 4.3 测试数据生成
```python
def generate_performance_test_data():
    """生成性能测试数据"""
    return {
        "hamming_pairs": [(f"{i:06b}", f"{j:06b}") for i in range(64) for j in range(64)],
        "path_queries": random.sample([(f"{i:06b}", f"{j:06b}") for i in range(64) for j in range(64)], 1000),
        "selection_queries": [(f"{random.randint(0,63):06b}", random.choice(list(HetuState))) for _ in range(5000)]
    }
```

## 5. 实施计划

### 阶段1: 基础缓存实现（1天）
1. 实现`HammingDistanceMatrix`类
2. 集成到`IntegratedHexagramStateManager`
3. 性能基准测试验证

### 阶段2: 路径缓存实现（1-2天）
1. 实现`ShortestPathMatrix`类
2. 集成到`HetuToHexagramAdapter`
3. 路径查找性能测试

### 阶段3: 最优映射缓存（1天）
1. 实现`HetuHexagramOptimalMapping`类
2. 优化卦象选择算法
3. 集成测试

### 阶段4: 缓存管理器统一集成（1天）
1. 实现`HexagramCacheManager`
2. 添加版本控制和刷新机制
3. 综合性能测试

## 6. 风险与缓解

### 6.1 技术风险
- **缓存一致性**: 卦象映射变更可能导致缓存失效
  - 缓解: 版本控制 + 惰性重新计算
- **内存开销**: 多个缓存矩阵可能增加内存使用
  - 缓解: 使用紧凑数据结构，实测内存占用
- **初始化延迟**: 预计算可能增加启动时间
  - 缓解: 后台线程初始化，惰性加载

### 6.2 集成风险
- **API变更**: 需要修改现有方法签名
  - 缓解: 保持向后兼容，使用适配器模式
- **测试覆盖**: 缓存可能绕过现有测试路径
  - 缓解: 增加缓存特定测试用例

## 7. 预期收益

| 优化项 | 当前复杂度 | 缓存后复杂度 | 预期加速比 |
|--------|------------|--------------|------------|
| 汉明距离计算 | O(n) n=6 | O(1) | 5-10倍 |
| 路径查找 | O(64) BFS | O(L) 查表 | 10-100倍 |
| 卦象选择 | O(m log m) m≈6.4 | O(1) | 20-50倍 |
| **总计算开销** | **~2.0%** | **~0.2%** | **10倍降低** |

**结论**: 卦象缓存机制是Phase 22优化的核心，预计可将卦象状态计算开销从2.0%降低到0.2%，为实现总体5%→1%的性能优化目标奠定基础。