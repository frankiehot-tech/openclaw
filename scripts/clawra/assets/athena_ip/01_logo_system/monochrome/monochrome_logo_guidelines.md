# Athena 单色版Logo设计规范

## 1. 设计概念

### 1.1 使用场景定位
- **单色印刷**：黑白打印、报纸广告、单色文档
- **特殊背景**：复杂背景、纹理背景、渐变背景
- **法律文件**：正式文档、合同、证书
- **品牌延伸**：纪念品、雕刻、刺绣
- **技术限制**：单色显示屏、LED屏幕、点阵打印

### 1.2 设计原则
1. **识别度优先**：单色环境下依然清晰可辨
2. **简化优化**：针对单色环境优化细节
3. **适应性**：适配不同单色表现方式
4. **一致性**：与彩色版本保持形态一致性

### 1.3 设计策略
- **轮廓强化**：增强边界清晰度
- **负空间利用**：巧妙利用空白区域
- **灰度层次**：通过密度表现层次（如点阵）
- **比例调整**：针对单色环境微调比例

## 2. 单色变体设计

### 2.1 纯黑色版本
- **特征**：纯黑色填充，白色背景
- **适用**：黑白打印、正式文档
- **规格**：100%黑色，无灰度
- **检查**：确保小尺寸清晰

### 2.2 纯白色版本
- **特征**：纯白色填充，黑色背景
- **适用**：深色背景、夜间模式
- **规格**：100%白色，无反色
- **检查**：深色背景对比度

### 2.3 反白版本
- **特征**：Logo区域镂空，背景色填充
- **适用**：彩色背景、特殊材质
- **规格**：保持轮廓完整性
- **检查**：轮廓连续不中断

### 2.4 线框版本
- **特征**：仅保留轮廓线，无填充
- **适用**：简约设计、水印效果
- **规格**：线条粗细一致
- **检查**：线条连接处完整

### 2.5 点阵/像素版本
- **特征**：适应低分辨率显示
- **适用**：LED屏幕、点阵打印
- **规格**：像素化优化
- **检查**：关键特征保留

## 3. 规格参数

### 3.1 文件格式要求
| 格式 | 用途 | 特别要求 |
|------|------|----------|
| **SVG** | 矢量应用 | 纯路径，无渐变/透明度 |
| **EPS** | 印刷设计 | CMYK颜色模式，100%黑 |
| **PDF** | 文档嵌入 | 矢量格式，印刷优化 |
| **PNG** | 数字应用 | 黑白二值或灰度 |
| **BMP** | 传统系统 | 1-bit或8-bit灰度 |

### 3.2 颜色模式规范
| 版本 | 颜色模式 | 色值 | 应用场景 |
|------|----------|------|----------|
| **纯黑版** | 灰度/位图 | K=100% | 黑白印刷、复印 |
| **纯白版** | 灰度/位图 | K=0% | 深色背景、反转显示 |
| **反白版** | 带透明通道 | 通道反转 | 彩色背景应用 |
| **灰度版** | 8-bit灰度 | 多级灰度 | 特殊印刷效果 |

### 3.3 分辨率要求
- **矢量格式**：无限缩放，优先使用
- **位图印刷**：≥600 DPI（精细印刷）
- **数字显示**：72-96 DPI
- **大尺寸输出**：根据输出设备调整

## 4. 使用规范

### 4.1 正确使用示例
✅ **黑白印刷文档**：
```css
/* 使用纯黑色版本 */
.monochrome-logo {
  fill: #000000; /* 100%黑色 */
  background: #FFFFFF; /* 白色背景 */
}
```

✅ **深色背景应用**：
```css
/* 使用纯白色版本 */
.dark-background .monochrome-logo {
  fill: #FFFFFF; /* 100%白色 */
  background: #000000; /* 黑色背景 */
}
```

✅ **彩色背景反白**：
```css
/* 使用反白版本 */
.colorful-background .monochrome-logo {
  fill: none;
  stroke: #FFFFFF; /* 白色轮廓 */
  background: transparent; /* 透明背景 */
}
```

✅ **低分辨率显示**：
```css
/* 使用点阵优化版本 */
.low-res-display .monochrome-logo {
  /* 像素化优化 */
  image-rendering: pixelated;
  image-rendering: crisp-edges;
}
```

### 4.2 禁止使用行为
❌ **禁止灰度滥用**：
- 随意添加灰度层次
- 使用非标准灰度值
- 破坏二值化清晰度

❌ **禁止轮廓破坏**：
- 随意修改轮廓粗细
- 断开重要连接点
- 增加不必要细节

❌ **禁止背景混淆**：
- 与背景对比度不足
- 在复杂背景上失去识别度
- 违反可访问性标准

### 4.3 特殊场景处理
#### 雕刻和蚀刻
- **材料**：金属、木材、石材
- **要求**：线条连续，无细小孤立元素
- **测试**：实际材料打样测试

#### 刺绣和纺织
- **工艺**：线绣、机绣、印花
- **要求**：简化细节，考虑针脚方向
- **最小尺寸**：考虑工艺限制

#### 屏幕显示限制
- **低分辨率**：像素化优化
- **单色LED**：考虑点间距
- **刷新率**：避免动态模糊

## 5. 技术实现

### 5.1 SVG优化实现
```svg
<!-- 纯黑色版本SVG -->
<svg class="athena-monochrome-black" width="120" height="120" viewBox="0 0 512 512">
  <!-- 纯黑色填充 -->
  <path class="monochrome-path" d="..." fill="#000000" />
  
  <!-- 无渐变、无透明度 -->
</svg>

<!-- 纯白色版本SVG -->
<svg class="athena-monochrome-white" width="120" height="120" viewBox="0 0 512 512">
  <!-- 纯白色填充 -->
  <path class="monochrome-path" d="..." fill="#FFFFFF" />
</svg>

<!-- 线框版本SVG -->
<svg class="athena-monochrome-outline" width="120" height="120" viewBox="0 0 512 512">
  <!-- 仅轮廓线 -->
  <path class="monochrome-outline" d="..." 
        fill="none"
        stroke="#000000"
        stroke-width="4" />
</svg>
```

### 5.2 CSS适配方案
```css
/* 基础单色样式 */
.athena-monochrome {
  /* 确保无颜色污染 */
  color: inherit !important;
  background-color: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

/* 打印优化 */
@media print {
  .athena-monochrome {
    /* 打印专用黑色 */
    fill: #000000 !important;
    stroke: #000000 !important;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
  
  /* 避免彩色污染 */
  * {
    -webkit-print-color-adjust: economy;
    print-color-adjust: economy;
  }
}

/* 深色模式适配 */
@media (prefers-color-scheme: dark) {
  .athena-monochrome-auto {
    /* 自动切换黑白 */
    fill: #FFFFFF;
  }
}

/* 高对比度模式 */
@media (prefers-contrast: high) {
  .athena-monochrome {
    /* 增强对比度 */
    stroke-width: 2px;
    fill-opacity: 1;
  }
}
```

### 5.3 打印特殊处理
```css
/* 打印样式表 */
@page {
  margin: 0.5in;
  marks: crop cross;
}

@media print {
  /* 强制黑白打印 */
  body {
    color: #000000 !important;
    background: #FFFFFF !important;
  }
  
  /* Logo打印优化 */
  .athena-logo-print {
    fill: #000000 !important;
    stroke: #000000 !important;
    stroke-width: 0.5pt !important;
    
    /* 避免分页切割 */
    page-break-inside: avoid;
    break-inside: avoid;
  }
  
  /* 隐藏不必要元素 */
  .no-print {
    display: none !important;
  }
}
```

### 5.4 点阵优化技术
```css
/* 像素化处理 */
.pixel-optimized {
  image-rendering: pixelated;
  image-rendering: crisp-edges;
  image-rendering: -moz-crisp-edges;
  image-rendering: -webkit-crisp-edges;
}

/* 低分辨率适配 */
@media (max-resolution: 96dpi) {
  .low-res-logo {
    /* 简化细节 */
    stroke-width: 2px;
    
    /* 移除细小元素 */
    .detail-small {
      display: none;
    }
  }
}

/* LED屏幕优化 */
.led-screen-optimized {
  /* 考虑点间距 */
  stroke-width: 2px;
  
  /* 避免抗锯齿 */
  shape-rendering: crispEdges;
  text-rendering: optimizeSpeed;
}
```

## 6. 生产应用指南

### 6.1 印刷准备
**文件准备清单**：
1. [ ] 使用CMYK颜色模式（K=100%）
2. [ ] 转换为轮廓（字体转曲）
3. [ ] 检查所有连接点
4. [ ] 设置适当的出血区域
5. [ ] 嵌入字体或转为路径

**印刷测试**：
- **小尺寸测试**：最小应用尺寸清晰度
- **反转测试**：黑白反转效果
- **缩放测试**：不同尺寸适应性
- **材料测试**：实际印刷材料效果

### 6.2 数字应用准备
**Web优化**：
```html
<!-- 根据背景自动选择 -->
<picture>
  <source srcset="athena_monochrome_white.svg" media="(prefers-color-scheme: dark)">
  <source srcset="athena_monochrome_black.svg" media="(prefers-color-scheme: light)">
  <img src="athena_monochrome_black.svg" alt="Athena Logo" class="monochrome-logo">
</picture>
```

**响应式策略**：
```css
/* 根据屏幕特性选择版本 */
@media (monochrome) {
  .logo {
    content: url('athena_monochrome_black.svg');
  }
}

@media (max-width: 768px) and (monochrome) {
  .logo {
    content: url('athena_monochrome_simplified.svg');
  }
}
```

### 6.3 特殊工艺适配
**雕刻工艺**：
- **文件格式**：DXF, DWG, AI
- **线条要求**：连续封闭路径
- **最小线宽**：≥0.5mm（取决于材料）
- **拐角处理**：适当圆角避免应力集中

**刺绣工艺**：
- **文件格式**：DST, EMB, PES
- **颜色限制**：通常单色或有限颜色
- **细节简化**：移除细小文字和元素
- **针脚方向**：考虑布料纹理

## 7. 质量检查清单

### 7.1 设计检查
- [ ] 单色环境下清晰可识别
- [ ] 与彩色版本形态一致
- [ ] 小尺寸应用（16×16px）测试通过
- [ ] 黑白反转测试效果良好
- [ ] 轮廓连续无中断

### 7.2 技术检查
- [ ] 文件纯黑白，无灰度污染
- [ ] 矢量文件路径优化
- [ ] 印刷分辨率足够
- [ ] 跨平台显示一致性
- [ ] 可访问性对比度达标

### 7.3 生产检查
- [ ] 实际印刷/制作测试
- [ ] 不同材料适配性
- [ ] 工艺限制考虑周全
- [ ] 成本控制合理
- [ ] 批量生产一致性

## 8. 资源下载

### 8.1 标准单色版本
| 版本 | SVG | EPS | PNG | 适用场景 |
|------|-----|-----|-----|----------|
| **纯黑版** | [下载](monochrome/athena_black.svg) | [下载](monochrome/athena_black.eps) | [下载](monochrome/athena_black.png) | 白底印刷、文档 |
| **纯白版** | [下载](monochrome/athena_white.svg) | [下载](monochrome/athena_white.eps) | [下载](monochrome/athena_white.png) | 黑底应用、夜间模式 |
| **反白版** | [下载](monochrome/athena_reverse.svg) | [下载](monochrome/athena_reverse.eps) | [下载](monochrome/athena_reverse.png) | 彩色背景、特殊效果 |
| **线框版** | [下载](monochrome/athena_outline.svg) | [下载](monochrome/athena_outline.eps) | [下载](monochrome/athena_outline.png) | 简约设计、水印 |

### 8.2 生产专用格式
- **雕刻用DXF**：`athena_logo_cnc.dxf`
- **刺绣用DST**：`athena_logo_embroidery.dst`
- **丝印用AI**：`athena_logo_silkscreen.ai`
- **3D打印STL**：`athena_logo_3d.stl`

### 8.3 设计源文件
- **单色专用AI**：`athena_monochrome_source.ai`
- **简化路径版本**：`athena_monochrome_simplified.svg`
- **像素优化版本**：`athena_monochrome_pixel.png`

## 9. 版本历史
| 版本 | 日期 | 变更说明 |
|------|------|----------|
| v1.0 | 2026-04-16 | 初始单色版规范建立 |
| v1.1 | 2026-05-01 | 增加特殊工艺适配指南 |
| v1.2 | 2026-06-15 | 优化打印和数字应用策略 |

---
**最后更新**：2026-04-16  
**维护团队**：Athena 设计系统团队  
**设计原则**：单色优化 + 多场景适配 + 生产就绪