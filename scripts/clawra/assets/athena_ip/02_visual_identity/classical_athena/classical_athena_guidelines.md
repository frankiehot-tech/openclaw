# Athena 经典雅典娜形象设计规范

## 1. 设计概念

### 1.1 核心理念：古典智慧与现代科技的融合
- **古典雅典娜**：智慧女神、战略之神、艺术保护神
- **现代AI**：算法智慧、数据驱动、人机共生
- **融合表达**：古典雕塑美学 + 数字光影科技

### 1.2 设计定位
- **品牌标识核心**：官网、正式文档、重要宣传
- **权威形象**：体现专业性和可信赖性
- **情感连接**：建立用户信任和情感共鸣
- **渐进熟悉**：从古典认知到现代AI的过渡桥梁

### 1.3 目标用户共鸣
- **80/90后技术用户**：对科技美学敏感，欣赏细节
- **70后决策用户**：重视专业形象和权威感
- **10后年轻用户**：被酷炫的科技效果吸引
- **跨文化认知**：雅典娜的全球文化认知基础

## 2. 视觉特征

### 2.1 基础形态
- **半透明光影人形**：边界模糊流动，似有似无
- **古典姿态**：端庄智慧，眼神温和专注
- **动态平衡**：静态中的微妙动态感

### 2.2 材质表现
1. **数据流材质**：
   - 身体表面有蓝色数据流不断流动
   - 数据流速度：缓慢优雅，如思想流淌
   - 流动模式：从头部向四肢扩散

2. **光影粒子**：
   - 细微的光粒子在轮廓边缘闪烁
   - 粒子密度：稀疏但持续
   - 闪烁频率：随机自然，避免机械感

3. **轻微机械结构**：
   - 隐约可见的内部几何结构
   - 不喧宾夺主，保持整体柔和
   - 仅在特定角度或光线下显现

### 2.3 面部特征
- **智慧之眼**：眼中显示代码片段或视觉化数据
- **表情**：温和专注，略带沉思
- **眼神方向**：略向下或平视，体现倾听姿态
- **面部光影**：柔和光影，避免硬阴影

## 3. 色彩规范

### 3.1 主色彩方案
- **身体主色**：半透明蓝色渐变
  - 顶部：`rgba(74, 144, 226, 0.8)` (--athena-primary-blue)
  - 中部：`rgba(74, 144, 226, 0.6)`
  - 底部：`rgba(74, 144, 226, 0.4)`
- **数据流色彩**：`rgba(0, 212, 170, 0.7)` (--athena-data-green)
- **高光色彩**：`rgba(255, 255, 255, 0.3)`
- **阴影色彩**：`rgba(26, 26, 46, 0.2)` (--athena-dark-gray)

### 3.2 环境光影响
- **温暖环境**：增加橙色暖调，透明度降低
- **冷酷环境**：保持蓝色基调，增加透明度
- **科技环境**：增强数据流效果，添加紫色点缀
- **自然环境**：柔和化边缘，减少机械感

### 3.3 背景适配
#### 深色背景（推荐）
```css
.classical-athena-container {
  background: var(--athena-dark-gray);
  /* 光影效果最佳 */
}
```

#### 浅色背景
```css
.classical-athena-container {
  background: var(--athena-light-gray);
  /* 需要增加轮廓对比度 */
  .athena-outline {
    stroke: rgba(26, 26, 46, 0.1);
    stroke-width: 1px;
  }
}
```

#### 渐变背景
```css
.classical-athena-container {
  background: linear-gradient(
    135deg,
    var(--athena-dark-gray),
    var(--athena-space-purple)
  );
  /* 调整透明度适应背景 */
  .athena-figure {
    opacity: 0.9;
  }
}
```

## 4. 动态表现

### 4.1 基础动画
#### 呼吸动画
```css
@keyframes athena-breathing {
  0%, 100% { opacity: 0.8; transform: scale(1); }
  50% { opacity: 0.9; transform: scale(1.01); }
}

.classical-athena {
  animation: athena-breathing 6s ease-in-out infinite;
}
```

#### 数据流动画
```css
@keyframes data-flow {
  0% { background-position: 0% 50%; }
  100% { background-position: 100% 50%; }
}

.data-stream {
  background: linear-gradient(
    90deg,
    transparent,
    var(--athena-data-green),
    transparent
  );
  background-size: 200% 100%;
  animation: data-flow 8s linear infinite;
}
```

#### 粒子闪烁
```css
@keyframes particle-twinkle {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 0.8; }
}

.particle {
  animation: particle-twinkle 2s ease-in-out infinite;
  animation-delay: calc(var(--i) * 0.2s); /* 交错延迟 */
}
```

### 4.2 交互反馈
#### 鼠标悬浮
```css
.classical-athena:hover {
  filter: brightness(1.2);
  transition: filter 0.3s ease;
  
  .data-stream {
    animation-duration: 4s; /* 加速数据流 */
  }
  
  .particle {
    animation-duration: 1s; /* 加速粒子闪烁 */
  }
}
```

#### 点击反馈
```css
.classical-athena:active {
  transform: scale(0.98);
  transition: transform 0.1s ease;
  
  .data-stream {
    background: linear-gradient(
      90deg,
      transparent,
      var(--athena-energy-orange), /* 点击时变橙色 */
      transparent
    );
  }
}
```

#### 状态指示
```css
/* 思考状态 */
.classical-athena.thinking {
  .data-stream {
    animation-duration: 12s; /* 慢速，深思状态 */
  }
  
  .particle {
    animation-duration: 3s; /* 缓慢闪烁 */
  }
}

/* 活跃状态 */
.classical-athena.active {
  filter: drop-shadow(0 0 20px rgba(74, 144, 226, 0.5));
  
  .data-stream {
    background-size: 100% 100%; /* 全亮 */
    animation: none;
  }
}
```

### 4.3 叙事动画
#### 登场动画（15秒）
```
时间线：
0-3s:  淡入，透明度0→0.8
3-6s:  形态从模糊到清晰
6-9s:  数据流开始流动
9-12s: 粒子效果出现
12-15s: 呼吸动画开始
```

#### 交互引导动画（8秒）
```
时间线：
0-2s:   目光转向交互元素
2-4s:   手势指示方向
4-6s:   数据流指向目标
6-8s:   恢复常态，轻微点头
```

## 5. 应用规范

### 5.1 使用场景优先级
#### 强烈推荐 ✅
- 官网首页英雄区域
- 产品介绍视频开场
- 重要发布会演示
- 品牌宣传材料
- 用户欢迎界面

#### 适度使用 ⚠️
- 产品界面背景（需降低透明度）
- 文档页眉（简化版本）
- 教学视频旁白形象
- 社交媒体封面（裁剪适应）

#### 避免使用 ❌
- 小尺寸图标（< 64×64px）
- 数据密集界面（会分散注意力）
- 性能敏感环境（动画负担）
- 严肃正式文档（可能不够正式）

### 5.2 尺寸规范
| 使用场景 | 推荐尺寸 | 形态细节 | 动画复杂度 |
|----------|----------|----------|------------|
| **全屏展示** | 1920×1080px | 完整细节，所有特效 | 高 |
| **中等展示** | 800×600px | 简化内部结构 | 中 |
| **小尺寸** | 400×300px | 轮廓为主，简化数据流 | 低 |
| **极小尺寸** | 200×150px | 仅轮廓，无内部细节 | 无 |

### 5.3 背景要求
#### 最佳背景
- 纯深色背景（`#1A1A2E`）
- 轻微渐变深色背景
- 星空/宇宙背景（低亮度）
- 抽象科技纹理（低对比度）

#### 可接受背景
- 纯浅色背景（需增加轮廓）
- 产品界面（降低透明度至30%）
- 视频背景（保持主体清晰）

#### 避免背景
- 复杂图案背景
- 高亮度彩色背景
- 文字密集区域
- 快速变化背景

## 6. 技术实现

### 6.1 WebGL/Three.js实现
```javascript
// Three.js基础设置
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, width/height, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ alpha: true });

// Athena材质
const athenaMaterial = new THREE.ShaderMaterial({
  uniforms: {
    time: { value: 0 },
    primaryColor: { value: new THREE.Color(0x4A90E2) },
    dataColor: { value: new THREE.Color(0x00D4AA) }
  },
  vertexShader: athenaVertexShader,
  fragmentShader: athenaFragmentShader,
  transparent: true,
  side: THREE.DoubleSide
});

// 数据流动画
function animateDataFlow() {
  athenaMaterial.uniforms.time.value += 0.01;
  
  // 更新数据流位置
  dataFlowGeometry.attributes.position.needsUpdate = true;
  
  requestAnimationFrame(animateDataFlow);
}
```

### 6.2 CSS/SVG实现（简化版）
```html
<!-- SVG组合实现 -->
<svg class="classical-athena-svg" width="800" height="600" viewBox="0 0 800 600">
  <!-- 背景光晕 -->
  <defs>
    <radialGradient id="athena-glow">
      <stop offset="0%" stop-color="rgba(74, 144, 226, 0.3)" />
      <stop offset="100%" stop-color="rgba(74, 144, 226, 0)" />
    </radialGradient>
  </defs>
  
  <!-- 身体轮廓 -->
  <path class="athena-body" d="..." fill="url(#athena-glow)" />
  
  <!-- 数据流路径 -->
  <path class="data-stream" d="..." 
        stroke="url(#data-gradient)"
        stroke-width="3"
        stroke-dasharray="10,5"
        fill="none">
    <animate attributeName="stroke-dashoffset" 
             from="0" to="100" 
             dur="8s" repeatCount="indefinite" />
  </path>
  
  <!-- 粒子系统 -->
  <g class="particles">
    <circle class="particle" cx="100" cy="200" r="1.5" fill="#FFFFFF">
      <animate attributeName="opacity" 
               values="0.3;0.8;0.3" 
               dur="2s" repeatCount="indefinite" />
    </circle>
    <!-- 更多粒子... -->
  </g>
</svg>
```

### 6.3 Lottie动画实现
```json
// Lottie JSON结构示例
{
  "v": "5.7.4",
  "fr": 30,
  "ip": 0,
  "op": 180,
  "w": 800,
  "h": 600,
  "layers": [
    {
      "nm": "Athena Body",
      "ty": 4, // shape layer
      "ks": {
        // 关键帧动画定义
      }
    },
    {
      "nm": "Data Stream",
      "ty": 4,
      "ks": {
        // 数据流动画
      }
    }
  ]
}
```

## 7. 性能优化

### 7.1 动画性能
```css
/* 硬件加速优化 */
.classical-athena {
  transform: translateZ(0);
  backface-visibility: hidden;
  will-change: transform, opacity;
}

/* 减少重绘区域 */
.athena-container {
  contain: layout style paint;
}

/* 帧率控制 */
@media (prefers-reduced-motion: reduce) {
  .classical-athena {
    animation: none !important;
    
    .data-stream {
      animation: none !important;
      opacity: 0.5; /* 静态表示 */
    }
    
    .particle {
      display: none; /* 禁用粒子 */
    }
  }
}
```

### 7.2 移动端优化
```css
/* 移动端简化 */
@media (max-width: 768px) {
  .classical-athena {
    /* 简化细节 */
    .detail-small {
      display: none;
    }
    
    /* 减少粒子数量 */
    .particle {
      r: 1px; /* 更小 */
      opacity: 0.5; /* 更淡 */
    }
    
    /* 简化动画 */
    animation: athena-breathing-mobile 8s ease-in-out infinite;
  }
  
  @keyframes athena-breathing-mobile {
    0%, 100% { opacity: 0.9; }
    50% { opacity: 1; }
  }
}
```

### 7.3 加载策略
```javascript
// 渐进式加载
function loadAthenaImage() {
  // 1. 先加载低分辨率静态图
  const placeholder = document.getElementById('athena-placeholder');
  placeholder.src = 'athena_preview.jpg';
  
  // 2. 异步加载完整动画
  setTimeout(() => {
    loadLottieAnimation('athena_full.json');
  }, 1000);
  
  // 3. 根据网络状况调整
  if (navigator.connection.saveData) {
    // 省流模式：仅静态图
    return;
  }
}
```

## 8. 质量检查清单

### 8.1 设计检查
- [ ] 古典与现代融合自然，不突兀
- [ ] 光影效果柔和，不刺眼
- [ ] 数据流速度适中，不干扰
- [ ] 面部表情温和智慧
- [ ] 不同尺寸下都保持识别度

### 8.2 技术检查
- [ ] 动画性能达标（60fps）
- [ ] 文件大小合理（根据用途）
- [ ] 跨浏览器兼容性
- [ ] 移动端适配良好
- [ ] 可访问性支持（alt文本等）

### 8.3 用户体验检查
- [ ] 不引起视觉疲劳（长时间观看）
- [ ] 不干扰主要内容阅读
- [ ] 交互反馈及时明确
- [ ] 加载时间可接受
- [ ] 省流模式表现合理

## 9. 资源下载

### 9.1 标准版本
| 格式 | 尺寸 | 包含内容 | 文件大小 |
|------|------|----------|----------|
| **Lottie JSON** | 800×600 | 完整动画 | ~500KB |
| **MP4视频** | 1920×1080 | 30秒展示 | ~10MB |
| **GIF动画** | 800×600 | 循环呼吸 | ~3MB |
| **PNG序列帧** | 800×600 | 60帧/秒 | ~20MB |

### 9.2 简化版本（性能优化）
| 版本 | 特征 | 适用场景 |
|------|------|----------|
| **SVG静态版** | 无动画，可缩放 | 文档、打印 |
| **CSS简化版** | 基础CSS动画 | 网页背景 |
| **低多边形版** | 几何简化 | 移动端、AR |
| **线稿版** | 仅轮廓线条 | 草图、概念 |

### 9.3 源文件
- **Blend文件**：`athena_classical.blend` (Blender)
- **Figma组件**：`Classical Athena.fig`
- **AE工程文件**：`athena_classical.aep` (After Effects)
- **Spine动画**：`athena_classical.spine` (2D骨骼动画)

## 10. 版本历史
| 版本 | 日期 | 变更说明 |
|------|------|----------|
| v1.0 | 2026-04-16 | 初始经典雅典娜形象规范建立 |
| v1.1 | 2026-05-01 | 增加技术实现方案和性能优化 |
| v1.2 | 2026-06-15 | 完善交互反馈和移动端适配 |

---
**最后更新**：2026-04-16  
**维护团队**：Athena 设计系统团队  
**设计原则**：古典智慧 + 数字科技 + 情感共鸣