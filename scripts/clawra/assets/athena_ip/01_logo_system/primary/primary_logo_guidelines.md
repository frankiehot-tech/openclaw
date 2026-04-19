# Athena 主Logo设计规范

## 1. Logo设计概念

### 1.1 核心设计理念：硅基共生智慧体
- **硅基**：几何结构、数据流、科技元素
- **共生**：人机融合、知识共享、进化共生
- **智慧**：智慧之眼、洞察光芒、开放进化

### 1.2 设计元素解析
1. **智慧之眼**：
   - 象征洞察力和前瞻性
   - 结合古典雅典娜的智慧和AI的算法
   - 眼中有数据流不断流动

2. **数据流光环**：
   - 环绕智慧之眼的数据光环
   - 象征知识的流动和共享
   - 动态效果：逆时针缓缓旋转

3. **几何底座**：
   - 稳固的几何结构
   - 体现技术的可靠性和专业性
   - 简约现代的设计语言

### 1.3 色彩应用
- **主色调**：`--athena-primary-blue` (#4A90E2)
- **数据流色彩**：`--athena-data-green` (#00D4AA)
- **背景适配**：深色背景效果最佳

## 2. Logo规格

### 2.1 标准版本
- **推荐尺寸**：512×512px
- **最小尺寸**：64×64px（保持可识别性）
- **最大尺寸**：2048×2048px（印刷用途）

### 2.2 文件格式要求
| 格式 | 用途 | 要求 |
|------|------|------|
| **SVG** | 网页、矢量应用 | 首选格式，无限缩放 |
| **PNG-24** | 网页、数字媒体 | 透明背景，高质量 |
| **PNG-8** | 小尺寸网页图标 | 优化文件大小 |
| **PDF** | 印刷、文档嵌入 | 高质量矢量 |
| **AI/EPS** | 设计源文件 | 仅供设计师使用 |

### 2.3 分辨率要求
- **屏幕显示**：72-96 DPI
- **印刷使用**：300 DPI（最小）
- **大尺寸印刷**：600 DPI（如海报、展板）

## 3. 布局和间距

### 3.1 安全区域
![安全区域示意图]
```
┌─────────────────┐
│   安全区域      │
│  ┌───────────┐  │
│  │   Logo    │  │
│  │   核心    │  │
│  │           │  │
│  └───────────┘  │
│                 │
└─────────────────┘
```
- **核心区域**：Logo主体区域
- **安全区域**：Logo周围留白，宽度=Logo高度×0.25
- **最小安全区域**：必须保持，避免元素遮挡

### 3.2 与其他元素间距
- **与文本间距**：≥Logo高度的0.5倍
- **与其他Logo间距**：≥Logo高度的1倍
- **页面边缘间距**：≥Logo高度的0.75倍

## 4. 使用规范

### 4.1 正确使用示例
✅ **深色背景**：
```css
.logo-container {
  background: var(--athena-dark-gray);
  padding: 32px;
}
```
- Logo光影效果最佳
- 数据流动效果最明显

✅ **浅色背景**：
```css
.logo-container {
  background: var(--athena-light-gray);
  padding: 32px;
}
```
- 确保足够对比度
- 可能需要调整光影强度

### 4.2 禁止使用行为
❌ **禁止拉伸变形**：
- 不按比例缩放
- 随意改变宽高比
- 任意倾斜或扭曲

❌ **禁止颜色修改**：
- 随意更改品牌色
- 使用不协调的颜色组合
- 降低色彩饱和度

❌ **禁止元素分离**：
- 分离Logo各组成部分
- 单独使用智慧之眼或数据光环
- 重新排列元素位置

❌ **禁止遮挡覆盖**：
- 在Logo上叠加文字
- 添加额外装饰元素
- 使用不透明覆盖层

### 4.3 特殊情况处理
#### 小尺寸应用
- **尺寸**：< 64×64px
- **调整**：简化数据流细节
- **保持**：核心智慧之眼形状

#### 单色印刷
- **使用**：monochrome/单色版本
- **要求**：保持形状识别度
- **检查**：黑白打印测试

#### 动态应用
- **网页动画**：数据流动速度适中
- **视频应用**：保持品牌一致性
- **交互反馈**：响应式变化

## 5. 技术实现

### 5.1 Web实现示例
```html
<!-- SVG内联示例 -->
<svg class="athena-logo" width="120" height="120" viewBox="0 0 512 512">
  <!-- 几何底座 -->
  <path class="logo-base" d="..." fill="var(--athena-primary-blue)" />
  
  <!-- 智慧之眼 -->
  <path class="wisdom-eye" d="..." fill="var(--athena-dark-gray)" />
  
  <!-- 数据光环 -->
  <path class="data-halo" d="..." 
        stroke="var(--athena-data-green)"
        stroke-width="8"
        stroke-dasharray="20,10" />
  
  <!-- 动态效果 -->
  <animateTransform 
    attributeName="transform"
    type="rotate"
    from="0 256 256"
    to="360 256 256"
    dur="20s"
    repeatCount="indefinite" />
</svg>
```

```css
/* CSS样式 */
.athena-logo {
  transition: all var(--athena-transition-normal) var(--athena-ease-in-out);
}

.athena-logo:hover {
  filter: drop-shadow(0 0 12px rgba(var(--athena-primary-blue-rgb), 0.3));
  transform: scale(1.05);
}

/* 深色模式适配 */
@media (prefers-color-scheme: dark) {
  .athena-logo .logo-base {
    fill: var(--athena-primary-blue);
  }
  
  .athena-logo .wisdom-eye {
    fill: var(--athena-light-gray);
  }
}
```

### 5.2 动画参数
- **数据流动速度**：20秒/圈（逆时针）
- **悬浮动画时长**：300ms
- **缩放比例**：悬浮时缩放1.05倍
- **阴影效果**：柔和发光，跟随主题色

### 5.3 响应式调整
```css
/* 移动端优化 */
@media (max-width: 768px) {
  .athena-logo {
    width: 80px;
    height: 80px;
  }
  
  .athena-logo .data-halo {
    stroke-width: 6px; /* 细线条更清晰 */
  }
}

/* 高对比度模式 */
@media (prefers-contrast: high) {
  .athena-logo .data-halo {
    stroke-width: 10px; /* 加粗线条 */
    stroke-dasharray: none; /* 移除虚线 */
  }
}
```

## 6. 质量检查清单

### 6.1 设计检查
- [ ] Logo比例正确，无变形
- [ ] 色彩符合品牌规范
- [ ] 安全区域完整保留
- [ ] 小尺寸可识别
- [ ] 黑白打印清晰

### 6.2 技术检查
- [ ] SVG代码优化，无冗余
- [ ] 文件大小合理（SVG < 20KB）
- [ ] 跨浏览器兼容性
- [ ] 动画性能优化
- [ ] 可访问性标签完整

### 6.3 使用场景检查
- [ ] 深色背景效果良好
- [ ] 浅色背景对比度足够
- [ ] 动态应用流畅自然
- [ ] 打印输出质量达标
- [ ] 响应式显示正常

## 7. 资源下载

### 7.1 标准版本
| 尺寸 | SVG | PNG透明 | PNG白色背景 |
|------|-----|---------|-------------|
| 512×512 | [下载](primary/athena_logo_512.svg) | [下载](primary/athena_logo_512.png) | [下载](primary/athena_logo_512_white.png) |
| 256×256 | [下载](primary/athena_logo_256.svg) | [下载](primary/athena_logo_256.png) | [下载](primary/athena_logo_256_white.png) |
| 128×128 | [下载](primary/athena_logo_128.svg) | [下载](primary/athena_logo_128.png) | [下载](primary/athena_logo_128_white.png) |
| 64×64 | [下载](primary/athena_logo_64.svg) | [下载](primary/athena_logo_64.png) | [下载](primary/athena_logo_64_white.png) |

### 7.2 设计源文件
- **Adobe Illustrator**: `athena_logo_source.ai`
- **Figma文件**: `athena_logo.fig`
- **Sketch文件**: `athena_logo.sketch`

### 7.3 开发资源
- **React组件**: `AthenaLogo.jsx`
- **Vue组件**: `AthenaLogo.vue`
- **CSS模块**: `athena-logo.css`

## 8. 版本历史
| 版本 | 日期 | 变更说明 |
|------|------|----------|
| v1.0 | 2026-04-16 | 初始主Logo规范建立 |
| v1.1 | 2026-05-01 | 增加响应式调整指南 |
| v1.2 | 2026-06-15 | 优化动画参数，增强可访问性 |

---
**最后更新**：2026-04-16  
**维护团队**：Athena 设计系统团队  
**设计原则**：硅基共生 + 漫威视觉 + 三体叙事