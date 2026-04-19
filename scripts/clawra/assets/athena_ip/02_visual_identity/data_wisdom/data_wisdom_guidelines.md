# Athena 数据智慧体形象设计规范

## 1. 设计概念

### 1.1 核心理念：数据可视化人格化
- **数据驱动**：形象本身是数据的可视化表达
- **动态智能**：形态随数据内容和上下文变化
- **极简几何**：去除冗余，保留本质信息
- **功能导向**：设计服务于信息传达

### 1.2 设计定位
- **产品界面集成**：操作面板、数据仪表盘
- **实时信息展示**：状态监控、数据分析
- **技术文档说明**：概念图示、流程说明
- **开发工具整合**：IDE插件、CLI界面

### 1.3 目标用户需求
- **技术决策者**：需要清晰的数据洞察
- **开发工程师**：偏好功能性、不分散注意力
- **数据科学家**：欣赏数据美学和信息密度
- **产品经理**：需要直观的状态反馈

## 2. 视觉特征

### 2.1 基础形态体系
#### 核心形态：几何数据体
- **基本形状**：立方体、球体、圆柱体组合
- **层级结构**：嵌套几何表示数据层级
- **连接关系**：线条和节点表示数据关系
- **动态变形**：形状随数据变化而调整

#### 数据可视化特征
1. **尺寸编码**：几何体大小表示数据量
2. **颜色编码**：色彩表示数据类型或状态
3. **透明度编码**：透明度表示数据新鲜度
4. **运动编码**：运动速度和方向表示数据流

### 2.2 色彩系统
#### 数据类别色彩映射
| 数据类型 | 主色彩 | 辅助色彩 | 状态指示 |
|----------|--------|----------|----------|
| **用户数据** | `#4A90E2` | `#6BA0FF` | 活跃/静默 |
| **系统数据** | `#00D4AA` | `#30FFD4` | 正常/异常 |
| **网络数据** | `#7B61FF` | `#9B81FF` | 流入/流出 |
| **计算数据** | `#FF6B35` | `#FF8B55` | 繁忙/空闲 |

#### 状态色彩编码
- **正常**：绿色系（`#00D4AA`）
- **警告**：橙色系（`#FF6B35`）
- **错误**：红色系（`#FF4757`）
- **信息**：蓝色系（`#4A90E2`）
- **成功**：青色系（`#00D4AA`）

### 2.3 动态原则
#### 数据响应动态
- **实时更新**：数据变化立即反映在形态上
- **平滑过渡**：形态变化使用缓动动画
- **突出重点**：重要数据变化有视觉强调
- **减少干扰**：非关键变化视觉降级

#### 交互反馈动态
- **悬停反馈**：高亮相关数据元素
- **选择反馈**：突出显示选中元素
- **操作反馈**：操作结果立即可视化
- **状态转换**：状态变化有明确视觉过渡

## 3. 形态变体设计

### 3.1 标准数据体
- **形态**：中心球体 + 环绕环 + 数据流线
- **适用**：通用数据展示、系统状态
- **复杂度**：中等，平衡信息量和清晰度

```css
.standard-data-body {
  /* 中心球体 - 核心指标 */
  .core-sphere {
    fill: var(--athena-primary-blue);
    r: var(--core-metric);
  }
  
  /* 数据环 - 次级指标 */
  .data-ring {
    stroke: var(--athena-data-green);
    stroke-width: 2;
    stroke-dasharray: var(--secondary-metric);
  }
  
  /* 流线 - 数据流动 */
  .flow-lines {
    stroke: var(--athena-space-purple);
    stroke-width: 1;
    opacity: 0.6;
  }
}
```

### 3.2 网络节点体
- **形态**：节点网络 + 连接线 + 流量指示
- **适用**：网络拓扑、系统架构
- **复杂度**：可变，支持缩放细节

```css
.network-node-body {
  /* 节点 - 系统组件 */
  .node {
    fill: var(--node-status-color);
    r: var(--node-load);
  }
  
  /* 连接线 - 通信关系 */
  .connection {
    stroke: var(--connection-status-color);
    stroke-width: var(--bandwidth);
    stroke-dasharray: var(--latency);
  }
  
  /* 流量箭头 - 数据方向 */
  .flow-arrow {
    fill: var(--flow-direction-color);
  }
}
```

### 3.3 时间序列体
- **形态**：时间轴 + 数据点 + 趋势线
- **适用**：历史数据、趋势分析
- **复杂度**：时间密度相关

```css
.timeseries-body {
  /* 时间轴 */
  .timeline {
    stroke: var(--athena-medium-gray);
    stroke-width: 1;
  }
  
  /* 数据点 */
  .data-point {
    fill: var(--data-value-color);
    r: 3;
  }
  
  /* 趋势线 */
  .trend-line {
    stroke: var(--athena-energy-orange);
    stroke-width: 2;
    fill: none;
  }
  
  /* 置信区间 */
  .confidence-band {
    fill: var(--athena-energy-orange);
    opacity: 0.1;
  }
}
```

### 3.4 层级树体
- **形态**：树状结构 + 层级缩进 + 节点属性
- **适用**：组织结构、文件系统、分类体系
- **复杂度**：支持展开/折叠

```css
.hierarchy-tree-body {
  /* 根节点 */
  .root-node {
    fill: var(--athena-primary-blue);
    r: 8;
  }
  
  /* 分支节点 */
  .branch-node {
    fill: var(--athena-data-green);
    r: 6;
  }
  
  /* 叶节点 */
  .leaf-node {
    fill: var(--athena-space-purple);
    r: 4;
  }
  
  /* 连接线 */
  .tree-link {
    stroke: var(--athena-medium-gray);
    stroke-width: 1;
  }
}
```

## 4. 交互设计规范

### 4.1 鼠标交互
#### 悬停反馈
```css
.data-element:hover {
  /* 视觉突出 */
  filter: brightness(1.2);
  stroke-width: 3;
  
  /* 信息显示 */
  &::after {
    content: attr(data-tooltip);
    /* 工具提示实现 */
  }
}
```

#### 选择反馈
```css
.data-element.selected {
  /* 选中状态 */
  stroke: var(--athena-energy-orange);
  stroke-width: 3;
  filter: drop-shadow(0 0 8px rgba(255, 107, 53, 0.5));
  
  /* 相关元素高亮 */
  &.connected {
    stroke: var(--athena-data-green);
  }
}
```

#### 拖拽交互
```javascript
// 拖拽数据节点
function handleDragDataNode(event) {
  const node = event.target;
  const originalData = node.dataset.value;
  
  // 视觉反馈：半透明拖拽副本
  const dragGhost = node.cloneNode(true);
  dragGhost.style.opacity = '0.7';
  dragGhost.style.position = 'absolute';
  
  // 有效拖拽区域高亮
  highlightValidDropZones();
  
  // 拖拽结束：数据更新和形态调整
  event.dataTransfer.setData('application/json', JSON.stringify({
    nodeId: node.id,
    originalValue: originalData
  }));
}
```

### 4.2 触摸交互
#### 移动端适配
```css
@media (hover: none) and (pointer: coarse) {
  .data-element {
    /* 增大触摸目标 */
    min-width: 44px;
    min-height: 44px;
    
    /* 简化悬停效果 */
    &:active {
      transform: scale(0.95);
      transition: transform 0.1s;
    }
  }
  
  /* 长按菜单 */
  .data-element.long-press {
    animation: pulse 1s infinite;
  }
}
```

#### 手势支持
```javascript
// 手势识别
const gestureZone = document.getElementById('data-visualization');
const hammer = new Hammer(gestureZone);

// 捏合缩放
hammer.get('pinch').set({ enable: true });
hammer.on('pinch', (event) => {
  const scale = event.scale;
  updateVisualizationScale(scale);
});

// 旋转
hammer.get('rotate').set({ enable: true });
hammer.on('rotate', (event) => {
  const rotation = event.rotation;
  rotateDataPerspective(rotation);
});
```

### 4.3 键盘交互
```javascript
// 键盘导航
document.addEventListener('keydown', (event) => {
  const focusedElement = document.activeElement;
  
  if (!focusedElement.classList.contains('data-element')) {
    return;
  }
  
  switch (event.key) {
    case 'ArrowUp':
      navigateToNeighbor(focusedElement, 'up');
      break;
    case 'ArrowDown':
      navigateToNeighbor(focusedElement, 'down');
      break;
    case 'ArrowLeft':
      navigateToNeighbor(focusedElement, 'left');
      break;
    case 'ArrowRight':
      navigateToNeighbor(focusedElement, 'right');
      break;
    case 'Enter':
    case ' ':
      selectDataElement(focusedElement);
      break;
    case 'Escape':
      clearSelection();
      break;
  }
});
```

## 5. 数据映射规范

### 5.1 数值到视觉属性映射
#### 线性映射（连续数据）
```javascript
function mapValueToVisual(value, min, max, visualMin, visualMax) {
  // 线性插值
  const normalized = (value - min) / (max - min);
  return visualMin + normalized * (visualMax - visualMin);
}

// 应用示例：数据量→圆半径
const radius = mapValueToVisual(
  dataVolume, 
  minVolume, 
  maxVolume,
  5,  // 最小半径
  50  // 最大半径
);
```

#### 分类映射（离散数据）
```javascript
const categoryColors = {
  'user': '#4A90E2',
  'system': '#00D4AA',
  'network': '#7B61FF',
  'compute': '#FF6B35',
  'storage': '#8A8AA3'
};

function getColorForCategory(category) {
  return categoryColors[category] || '#8A8AA3'; // 默认灰色
}
```

#### 时间映射（时序数据）
```javascript
function mapTimeToPosition(timestamp, startTime, endTime, width) {
  const timeRange = endTime - startTime;
  const elapsed = timestamp - startTime;
  const position = (elapsed / timeRange) * width;
  
  // 添加缓动：最近时间更密集
  const recentBias = 0.7; // 70%空间给最近30%时间
  if (elapsed > timeRange * 0.7) {
    return position * recentBias;
  }
  
  return position;
}
```

### 5.2 多维度映射策略
#### 二维映射（大小+颜色）
```javascript
function create2DVisualEncoding(dataPoint) {
  return {
    // 大小表示数值
    size: mapValueToSize(dataPoint.value),
    
    // 颜色表示类别
    color: getColorForCategory(dataPoint.category),
    
    // 位置表示时间
    x: mapTimeToPosition(dataPoint.timestamp),
    y: mapValueToPosition(dataPoint.metric)
  };
}
```

#### 三维映射（大小+颜色+形状）
```javascript
function create3DVisualEncoding(dataPoint) {
  const encoding = create2DVisualEncoding(dataPoint);
  
  // 添加第三维：形状
  encoding.shape = getShapeForStatus(dataPoint.status);
  
  // 添加动画：运动速度
  encoding.velocity = mapValueToVelocity(dataPoint.rateOfChange);
  
  return encoding;
}
```

### 5.3 数据聚合可视化
#### 小尺度聚合（点簇）
```css
.data-cluster {
  /* 聚合点：更大，半透明 */
  .cluster-center {
    fill: var(--cluster-color);
    r: var(--cluster-size);
    opacity: 0.6;
  }
  
  /* 密度指示：点密度或热图 */
  .density-indicator {
    fill: url(#density-gradient);
  }
}
```

#### 大尺度聚合（统计图形）
```javascript
function createAggregateVisualization(dataPoints) {
  const stats = calculateStatistics(dataPoints);
  
  return {
    // 箱线图：分布情况
    boxPlot: createBoxPlot(stats),
    
    // 直方图：频率分布
    histogram: createHistogram(dataPoints),
    
    // 密度曲线：平滑分布
    densityCurve: createDensityCurve(dataPoints),
    
    // 统计摘要：文本叠加
    summaryText: createSummaryText(stats)
  };
}
```

## 6. 性能优化策略

### 6.1 数据量分级处理
#### 小数据量（< 1000点）
```javascript
// 完整渲染，所有交互
function renderSmallDataset(data) {
  data.forEach(point => {
    createDetailedDataPoint(point);
    enableFullInteractivity(point);
  });
}
```

#### 中等数据量（1000-10000点）
```javascript
// 简化渲染，有限交互
function renderMediumDataset(data) {
  // 采样显示
  const sampled = sampleData(data, 1000);
  
  sampled.forEach(point => {
    createSimplifiedDataPoint(point);
    enableBasicInteractivity(point);
  });
  
  // 聚合背景
  createAggregateBackground(data);
}
```

#### 大数据量（> 10000点）
```javascript
// 聚合渲染，批量交互
function renderLargeDataset(data) {
  // 分层聚合
  const aggregated = aggregateDataByLevel(data, 3);
  
  // 层级可视化
  createHierarchicalVisualization(aggregated);
  
  // 渐进式细节
  enableProgressiveDetail(data);
}
```

### 6.2 渲染优化技术
#### 虚拟滚动/视窗裁剪
```javascript
function renderVisibleData(container, viewport) {
  const visibleData = data.filter(point => 
    isInViewport(point, viewport)
  );
  
  // 只渲染可见部分
  renderDataPoints(visibleData);
  
  // 监听滚动，动态更新
  container.addEventListener('scroll', () => {
    const newViewport = calculateViewport(container);
    updateVisibleData(newViewport);
  });
}
```

#### Canvas渲染优化
```javascript
// 使用Canvas进行高性能渲染
const canvas = document.getElementById('data-canvas');
const ctx = canvas.getContext('2d');

function renderToCanvas(data) {
  // 清除画布
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  
  // 批量绘制
  data.forEach(point => {
    drawDataPoint(ctx, point);
  });
  
  // 使用requestAnimationFrame
  requestAnimationFrame(() => {
    renderToCanvas(updatedData);
  });
}
```

#### WebGL加速
```javascript
// 使用WebGL进行GPU加速
const gl = canvas.getContext('webgl');

function createDataPointBuffer(data) {
  // 创建顶点缓冲区
  const vertices = new Float32Array(data.flatMap(point => 
    [point.x, point.y, point.size, point.color.r, point.color.g, point.color.b]
  ));
  
  const buffer = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);
  
  return buffer;
}
```

### 6.3 内存管理
#### 数据生命周期
```javascript
class DataVisualizationManager {
  constructor() {
    this.activeData = new Map();
    this.cachedData = new Map();
    this.maxCacheSize = 1000;
  }
  
  addData(key, data) {
    // 添加到活动数据
    this.activeData.set(key, data);
    
    // 内存管理
    this.manageMemory();
  }
  
  manageMemory() {
    // 限制活动数据数量
    if (this.activeData.size > this.maxCacheSize) {
      const oldestKey = this.getOldestKey();
      this.moveToCache(oldestKey);
    }
  }
  
  moveToCache(key) {
    const data = this.activeData.get(key);
    this.cachedData.set(key, data);
    this.activeData.delete(key);
  }
}
```

#### 渐进式加载
```javascript
function loadDataProgressive(url, onProgress, onComplete) {
  const chunkSize = 1000;
  let loadedData = [];
  
  // 分块加载
  for (let offset = 0; offset < totalSize; offset += chunkSize) {
    fetch(`${url}?offset=${offset}&limit=${chunkSize}`)
      .then(response => response.json())
      .then(chunk => {
        loadedData = loadedData.concat(chunk);
        
        // 逐步渲染
        renderPartialData(loadedData);
        
        // 进度反馈
        onProgress(loadedData.length / totalSize);
      });
  }
  
  // 最终完成
  onComplete(loadedData);
}
```

## 7. 可访问性设计

### 7.1 屏幕阅读器支持
```html
<!-- 数据可视化语义结构 -->
<div role="region" aria-label="数据可视化图表">
  <svg aria-hidden="true" focusable="false">
    <!-- 视觉元素 -->
  </svg>
  
  <!-- 隐藏的文本描述 -->
  <div class="sr-only">
    <h2>数据可视化：系统状态</h2>
    <p>图表显示当前系统负载为65%，网络流量正常，存储使用率42%。</p>
    
    <ul>
      <li>CPU使用率：45%</li>
      <li>内存使用率：65%</li>
      <li>网络流入：120Mbps</li>
      <li>网络流出：85Mbps</li>
    </ul>
  </div>
</div>
```

### 7.2 键盘导航增强
```javascript
// 增强键盘导航
function enhanceKeyboardNavigation() {
  const dataElements = document.querySelectorAll('.data-element');
  
  // 设置tabindex
  dataElements.forEach((element, index) => {
    element.setAttribute('tabindex', '0');
    element.setAttribute('aria-label', `数据点 ${index + 1}`);
    
    // 键盘事件
    element.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        selectDataElement(element);
      }
    });
  });
  
  // 添加导航提示
  const navHint = document.createElement('div');
  navHint.className = 'keyboard-nav-hint';
  navHint.textContent = '使用方向键导航，Enter键选择';
  document.body.appendChild(navHint);
}
```

### 7.3 高对比度模式
```css
/* 高对比度模式适配 */
@media (prefers-contrast: high) {
  .data-element {
    /* 增强边框 */
    stroke: #000000 !important;
    stroke-width: 2px !important;
    
    /* 移除半透明 */
    opacity: 1 !important;
    fill-opacity: 1 !important;
    
    /* 简化动画 */
    animation: none !important;
  }
  
  .data-label {
    /* 增强文字对比度 */
    color: #000000 !important;
    background: #FFFFFF !important;
    padding: 2px 4px;
    border: 1px solid #000000;
  }
  
  /* 状态指示更明显 */
  .status-normal { fill: #006600 !important; }
  .status-warning { fill: #663300 !important; }
  .status-error { fill: #660000 !important; }
}
```

## 8. 质量检查清单

### 8.1 数据准确性检查
- [ ] 数据映射准确无误
- [ ] 比例尺正确应用
- [ ] 颜色编码一致清晰
- [ ] 数据更新实时反映
- [ ] 异常数据处理得当

### 8.2 视觉有效性检查
- [ ] 信息密度适中，不过载
- [ ] 色彩使用符合色盲友好
- [ ] 不同尺寸下清晰可读
- [ ] 动画效果自然不干扰
- [ ] 重点数据突出显示

### 8.3 交互可用性检查
- [ ] 鼠标交互响应及时
- [ ] 触摸交互目标足够大
- [ ] 键盘导航完整支持
- [ ] 屏幕阅读器兼容
- [ ] 性能在各种数据量下可接受

### 8.4 技术实现检查
- [ ] 代码结构清晰模块化
- [ ] 性能优化措施到位
- [ ] 内存管理合理
- [ ] 错误处理完善
- [ ] 测试覆盖充分

## 9. 资源下载

### 9.1 组件库
| 技术栈 | 组件 | 文档 | 示例 |
|--------|------|------|------|
| **React** | `DataWisdomVisualization` | [文档](components/react/README.md) | [示例](examples/react/) |
| **Vue 3** | `DataWisdomChart` | [文档](components/vue/README.md) | [示例](examples/vue/) |
| **Angular** | `AthenaDataVisComponent` | [文档](components/angular/README.md) | [示例](examples/angular/) |
| **Svelte** | `DataWisdom` | [文档](components/svelte/README.md) | [示例](examples/svelte/) |

### 9.2 设计资源
- **Figma组件库**：`Athena Data Visualization Kit.fig`
- **设计令牌**：`data-wisdom-design-tokens.json`
- **SVG图标集**：`data-visualization-icons.zip`
- **配色方案**：`data-colors-palette.ase`

### 9.3 开发工具
- **数据映射工具**：`data-mapper-tool.js`
- **性能分析器**：`performance-profiler.js`
- **可访问性检查器**：`a11y-checker.js`
- **测试数据生成器**：`test-data-generator.js`

## 10. 版本历史
| 版本 | 日期 | 变更说明 |
|------|------|----------|
| v1.0 | 2026-04-16 | 初始数据智慧体规范建立 |
| v1.1 | 2026-05-01 | 增加多维度映射和交互规范 |
| v1.2 | 2026-06-15 | 完善性能优化和可访问性设计 |

---
**最后更新**：2026-04-16  
**维护团队**：Athena 设计系统团队  
**设计原则**：数据驱动 + 功能美学 + 高效交互