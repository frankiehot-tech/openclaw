# Athena 紧凑版Logo设计规范

## 1. 设计概念

### 1.1 使用场景定位
- **小尺寸应用**：社交媒体头像、移动端导航栏、浏览器标签
- **空间受限环境**：工具栏、状态栏、小按钮
- **快速识别需求**：需要瞬间品牌识别的场景

### 1.2 设计原则
1. **极简化**：移除次要细节，保留核心识别元素
2. **清晰度优先**：小尺寸下依然清晰可辨
3. **适应性**：适配不同背景和尺寸
4. **一致性**：与主Logo保持视觉关联

### 1.3 核心元素保留
- **智慧之眼**：核心识别元素，简化轮廓
- **数据光环**：简化为单环或点状
- **色彩体系**：保持品牌主色调

## 2. 设计变体

### 2.1 标准紧凑版
- **特征**：智慧之眼 + 单环数据光环
- **尺寸**：推荐48×48px，最小24×24px
- **适用**：移动应用图标、网站favicon

### 2.2 极简图标版
- **特征**：仅智慧之眼，无数据光环
- **尺寸**：推荐32×32px，最小16×16px
- **适用**：工具栏、状态栏、小按钮

### 2.3 文字组合版
- **特征**：紧凑Logo + "Athena"文字
- **文字字体**：科技感无衬线字体，高度与Logo相等
- **间距**：Logo与文字间距=Logo宽度的0.5倍
- **适用**：品牌标识、页面页眉

## 3. 规格参数

### 3.1 尺寸规范
| 使用场景 | 推荐尺寸 | 最小尺寸 | 最大尺寸 | 备注 |
|----------|----------|----------|----------|------|
| **Favicon** | 32×32px | 16×16px | 48×48px | 支持ICO多尺寸 |
| **移动应用图标** | 48×48px | 24×24px | 96×96px | iOS/Android标准 |
| **社交媒体头像** | 180×180px | 150×150px | 300×300px | 平台要求各异 |
| **浏览器扩展图标** | 38×38px | 19×19px | 128×128px | Chrome标准 |
| **工具栏图标** | 24×24px | 16×16px | 32×32px | 清晰可识别 |

### 3.2 文件格式要求
| 格式 | 用途 | 特别要求 |
|------|------|----------|
| **ICO** | Favicon | 包含16×16, 32×32, 48×48多尺寸 |
| **PNG** | 通用图标 | 透明背景，优化压缩 |
| **SVG** | 矢量应用 | 简化路径，小文件大小 |
| **PDF** | 印刷文档 | 高质量矢量 |

### 3.3 分辨率适配
- **标准屏幕**：72-96 DPI
- **视网膜屏幕**：@2x, @3x版本准备
- **打印使用**：300 DPI矢量版本

## 4. 使用规范

### 4.1 正确使用示例
✅ **深色背景**：
```css
.compact-logo {
  /* 使用标准紧凑版 */
  width: 48px;
  height: 48px;
  background: transparent;
}
```

✅ **浅色背景**：
```css
.compact-logo {
  /* 可能需要增加边框增强对比度 */
  width: 48px;
  height: 48px;
  border: 1px solid var(--athena-medium-gray);
  border-radius: 4px;
  padding: 2px;
}
```

✅ **极小尺寸**（<24px）：
```css
.compact-logo-tiny {
  /* 使用极简图标版 */
  width: 16px;
  height: 16px;
  /* 简化细节，增强对比度 */
}
```

### 4.2 禁止使用行为
❌ **禁止过度简化**：
- 失去核心识别特征
- 与品牌形象完全脱节
- 无法与主Logo建立关联

❌ **禁止随意修改比例**：
- 宽高比改变导致变形
- 元素间距随意调整
- 破坏视觉平衡

❌ **禁止不协调色彩**：
- 使用非品牌色系
- 低对比度色彩组合
- 影响可识别性

### 4.3 特殊场景处理
#### 单色应用
- **场景**：黑白打印、单色显示屏
- **方案**：使用单色版本或反白版本
- **测试**：确保黑白对比度足够

#### 动态应用
- **场景**：加载动画、状态指示
- **方案**：微动画，如数据光环旋转
- **原则**：简洁不干扰

#### 响应式调整
- **原则**：不同断点使用合适版本
- **大屏幕**：使用标准紧凑版
- **小屏幕**：切换到极简图标版

## 5. 技术实现

### 5.1 SVG优化实现
```svg
<!-- 标准紧凑版SVG -->
<svg class="athena-compact-logo" width="48" height="48" viewBox="0 0 48 48">
  <!-- 简化智慧之眼 -->
  <path class="compact-eye" d="M24,12 C30.627,12 36,17.373 36,24 C36,30.627 30.627,36 24,36 C17.373,36 12,30.627 12,24 C12,17.373 17.373,12 24,12 Z"
        fill="var(--athena-primary-blue)" />
  
  <!-- 简化数据环 -->
  <circle class="compact-halo" cx="24" cy="24" r="18"
          fill="none"
          stroke="var(--athena-data-green)"
          stroke-width="2"
          stroke-dasharray="3,3" />
  
  <!-- 瞳孔（简化） -->
  <circle class="compact-pupil" cx="24" cy="24" r="6"
          fill="var(--athena-dark-gray)" />
</svg>
```

### 5.2 CSS适配方案
```css
/* 基础样式 */
.athena-compact-logo {
  display: inline-block;
  vertical-align: middle;
  transition: all var(--athena-transition-fast) var(--athena-ease-out);
}

/* 尺寸变体 */
.athena-compact-logo.size-16 {
  width: 16px;
  height: 16px;
}

.athena-compact-logo.size-24 {
  width: 24px;
  height: 24px;
}

.athena-compact-logo.size-32 {
  width: 32px;
  height: 32px;
}

.athena-compact-logo.size-48 {
  width: 48px;
  height: 48px;
}

/* 深色模式适配 */
@media (prefers-color-scheme: dark) {
  .athena-compact-logo .compact-eye {
    fill: var(--athena-primary-blue);
  }
  
  .athena-compact-logo .compact-pupil {
    fill: var(--athena-light-gray);
  }
}

/* 高对比度模式 */
@media (prefers-contrast: high) {
  .athena-compact-logo .compact-halo {
    stroke-width: 3px;
    stroke-dasharray: none; /* 实线更清晰 */
  }
}
```

### 5.3 动态效果
```css
/* 微动画：数据环旋转 */
@keyframes compact-halo-rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.athena-compact-logo.loading .compact-halo {
  animation: compact-halo-rotate 8s linear infinite;
}

/* 悬浮效果 */
.athena-compact-logo:hover {
  transform: scale(1.1);
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2));
}
```

### 5.4 响应式策略
```css
/* 断点调整策略 */
@media (max-width: 768px) {
  /* 移动端使用更小尺寸 */
  .header-logo {
    width: 32px;
    height: 32px;
  }
  
  /* 简化细节 */
  .athena-compact-logo .compact-halo {
    stroke-width: 1.5px;
  }
}

@media (max-width: 480px) {
  /* 极小屏幕使用极简版 */
  .header-logo {
    width: 24px;
    height: 24px;
  }
  
  /* 隐藏数据环，仅保留眼睛 */
  .athena-compact-logo .compact-halo {
    display: none;
  }
}
```

## 6. Favicon特殊规范

### 6.1 ICO文件生成
```bash
# 使用ImageMagick生成多尺寸ICO
convert \
  athena_compact_16.png \
  athena_compact_32.png \
  athena_compact_48.png \
  athena_favicon.ico
```

### 6.2 HTML引用
```html
<!-- 标准Favicon引用 -->
<link rel="icon" href="/assets/favicon.ico" type="image/x-icon">
<link rel="icon" href="/assets/favicon-32.png" type="image/png" sizes="32x32">
<link rel="icon" href="/assets/favicon-16.png" type="image/png" sizes="16x16">

<!-- Apple Touch Icon -->
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">

<!-- Android Chrome图标 -->
<link rel="icon" type="image/png" sizes="192x192" href="/assets/android-chrome-192.png">
<link rel="icon" type="image/png" sizes="512x512" href="/assets/android-chrome-512.png">

<!-- Windows磁贴 -->
<meta name="msapplication-TileImage" content="/assets/mstile-144.png">
```

### 6.3 平台特定要求
| 平台 | 尺寸要求 | 格式 | 备注 |
|------|----------|------|------|
| **通用Favicon** | 16×16, 32×32, 48×48 | ICO | 多尺寸包含 |
| **Apple** | 180×180, 167×167, 152×152 | PNG | 圆角自动应用 |
| **Android** | 192×192, 512×512 | PNG | 自适应图标 |
| **Windows** | 144×144 | PNG | 磁贴图标 |

## 7. 质量检查清单

### 7.1 设计检查
- [ ] 小尺寸清晰可识别（16×16px测试）
- [ ] 与主Logo保持视觉关联
- [ ] 色彩对比度符合可访问性标准
- [ ] 简化适度，不失品牌特征
- [ ] 多尺寸版本一致性

### 7.2 技术检查
- [ ] SVG文件优化（< 5KB）
- [ ] ICO文件包含所有必要尺寸
- [ ] 跨平台显示一致性
- [ ] 视网膜屏适配良好
- [ ] 动画性能优化

### 7.3 使用场景检查
- [ ] 深色/浅色背景都适用
- [ ] 响应式调整策略有效
- [ ] 动态应用流畅自然
- [ ] 打印输出清晰
- [ ] 平台特定要求满足

## 8. 资源下载

### 8.1 标准紧凑版
| 尺寸 | SVG | PNG透明 | 适用场景 |
|------|-----|---------|----------|
| 48×48 | [下载](compact/athena_compact_48.svg) | [下载](compact/athena_compact_48.png) | 移动应用图标 |
| 32×32 | [下载](compact/athena_compact_32.svg) | [下载](compact/athena_compact_32.png) | Favicon、工具栏 |
| 24×24 | [下载](compact/athena_compact_24.svg) | [下载](compact/athena_compact_24.png) | 状态栏、小按钮 |
| 16×16 | [下载](compact/athena_compact_16.svg) | [下载](compact/athena_compact_16.png) | 极小尺寸应用 |

### 8.2 特殊格式
- **ICO文件**：`athena_favicon.ico`（16,32,48多尺寸）
- **Apple Touch Icon**：`apple-touch-icon.png`（180×180）
- **Android自适应图标**：`android-chrome-192.png`, `android-chrome-512.png`
- **Windows磁贴**：`mstile-144.png`

### 8.3 设计源文件
- **Figma组件**：`Athena Compact Logo.fig`
- **Sketch符号**：`Athena Compact Logo.sketch`
- **Adobe Illustrator**：`athena_compact_logo.ai`

## 9. 版本历史
| 版本 | 日期 | 变更说明 |
|------|------|----------|
| v1.0 | 2026-04-16 | 初始紧凑版规范建立 |
| v1.1 | 2026-05-01 | 增加Favicon特殊规范 |
| v1.2 | 2026-06-15 | 优化响应式策略和动画 |

---
**最后更新**：2026-04-16  
**维护团队**：Athena 设计系统团队  
**设计原则**：极简化 + 高识别度 + 多平台适配