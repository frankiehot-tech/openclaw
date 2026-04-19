# Athena 音效库规范

## 1. 设计理念

### 1.1 核心理念：数据驱动的听觉体验
- **科技感优先**：清晰、精准、现代的数字音效
- **情感化设计**：音效传达系统状态和情感反馈
- **一致性原则**：所有音效遵循统一的听觉语言
- **功能性导向**：每个音效都有明确的交互目的

### 1.2 声音特征
- **音色**：数字合成音色，避免过于"有机"的自然声音
- **时长**：短促精准（100-500ms为主）
- **频率**：中高频为主，清晰穿透不刺耳
- **动态**：适度的动态范围，避免过大的音量变化

### 1.3 技术标准
| 参数 | 标准值 | 备注 |
|------|--------|------|
| **采样率** | 44.1kHz | 标准CD音质 |
| **位深度** | 16-bit | 高质量数字音频 |
| **格式** | WAV/MP3/OGG | 根据使用场景选择 |
| **声道** | 单声道/立体声 | 交互音效单声道，环境音效立体声 |

## 2. 音效分类体系

### 2.1 交互反馈音效（核心类别）
#### 操作确认
| 音效ID | 使用场景 | 听觉特征 | 时长 | 技术参数 |
|--------|----------|----------|------|----------|
| `ui_confirm_01` | 按钮点击 | 清脆"滴"声，轻微上升音调 | 150ms | 440Hz → 523Hz |
| `ui_select_01` | 选项选择 | 柔和"噗"声，轻微衰减 | 120ms | 300Hz衰减 |
| `ui_hover_01` | 鼠标悬停 | 微弱"嘶"声，平滑出现 | 100ms | 白噪声滤波 |

#### 状态变化
| 音效ID | 使用场景 | 听觉特征 | 时长 | 技术参数 |
|--------|----------|----------|------|----------|
| `state_on_01` | 功能开启 | 上升琶音，明亮感 | 300ms | C大调和弦上升 |
| `state_off_01` | 功能关闭 | 下降琶音，温和感 | 300ms | C大调和弦下降 |
| `state_toggle_01` | 开关切换 | 短促双音，明确反馈 | 200ms | 440Hz → 554Hz |

### 2.2 系统状态音效
#### 处理状态
| 音效ID | 使用场景 | 听觉特征 | 时长 | 技术参数 |
|--------|----------|----------|------|----------|
| `process_start_01` | 处理开始 | 数据流启动声 | 400ms | 低频扫频上升 |
| `process_complete_01` | 处理完成 | 完成确认声 | 500ms | 上升和弦解决 |
| `process_error_01` | 处理错误 | 警示声但不刺耳 | 600ms | 不和谐音短暂出现 |

#### 加载状态
| 音效ID | 使用场景 | 听觉特征 | 时长 | 技术参数 |
|--------|----------|----------|------|----------|
| `loading_start_01` | 加载开始 | 轻微启动脉冲 | 200ms | 短脉冲，快速衰减 |
| `loading_loop_01` | 加载循环 | 平稳循环音 | 持续 | 200-400Hz正弦波调制 |
| `loading_finish_01` | 加载完成 | 完成释放声 | 400ms | 滤波器释放，音高上升 |

### 2.3 通知提醒音效
#### 消息通知
| 音效ID | 使用场景 | 听觉特征 | 时长 | 技术参数 |
|--------|----------|----------|------|----------|
| `notification_info_01` | 信息通知 | 温和提醒声 | 250ms | 铃声音色，中等音量 |
| `notification_warning_01` | 警告通知 | 注意但不惊吓 | 350ms | 重复短音，中等音量 |
| `notification_success_01` | 成功通知 | 积极肯定声 | 400ms | 上升和弦，明亮感 |

#### 重要提醒
| 音效ID | 使用场景 | 听觉特征 | 时长 | 技术参数 |
|--------|----------|----------|------|----------|
| `alert_important_01` | 重要提醒 | 需要关注但不紧急 | 500ms | 重复模式，适中音量 |
| `alert_critical_01` | 关键提醒 | 需要立即关注 | 800ms | 持续声音，适当音量 |

### 2.4 叙事和情感音效
#### 情感反馈
| 音效ID | 使用场景 | 听觉特征 | 时长 | 技术参数 |
|--------|----------|----------|------|----------|
| `emotion_positive_01` | 积极反馈 | 温暖上升音 | 600ms | 和弦进行，温暖音色 |
| `emotion_neutral_01` | 中性反馈 | 平稳中性音 | 400ms | 单音，中性音色 |
| `emotion_encourage_01` | 鼓励反馈 | 激励上升音 | 700ms | 上升琶音，明亮感 |

#### 品牌叙事
| 音效ID | 使用场景 | 听觉特征 | 时长 | 技术参数 |
|--------|----------|----------|------|----------|
| `brand_intro_01` | 品牌介绍 | Athena登场音 | 3s | 渐强渐弱，科技感旋律 |
| `brand_transition_01` | 场景过渡 | 平滑过渡音 | 2s | 滤波器扫频，空间感 |
| `brand_highlight_01` | 重点强调 | 突出关键内容 | 1s | 频率突出，短暂混响 |

### 2.5 环境氛围音效
#### 工作环境
| 音效ID | 使用场景 | 听觉特征 | 时长 | 技术参数 |
|--------|----------|----------|------|----------|
| `ambient_work_01` | 工作背景 | 轻微数据流动声 | 持续 | 低频脉冲，极低音量 |
| `ambient_focus_01` | 专注模式 | 白噪声增强 | 持续 | 粉红噪声，轻微滤波 |

#### 休息环境
| 音效ID | 使用场景 | 听觉特征 | 时长 | 技术参数 |
|--------|----------|----------|------|----------|
| `ambient_calm_01` | 平静模式 | 舒缓环境声 | 持续 | 环境音景，极低动态 |

## 3. 技术实现规范

### 3.1 音效生成工具
#### 推荐工具
```yaml
synthesis_tools:
  primary: "Surge XT"  # 数字合成器
  secondary: "Vital"    # 波表合成器
  effects: "Valhalla DSP"  # 效果处理
  mastering: "iZotope Ozone"  # 母带处理
```

#### 预设管理
```json
{
  "preset_naming": "athena_[category]_[function]_[variant].fxp",
  "parameter_ranges": {
    "attack": "5-50ms",
    "decay": "50-300ms",
    "sustain": "-12 to -6dB",
    "release": "100-500ms"
  }
}
```

### 3.2 音效处理流程
```
原始合成 → 动态处理 → 均衡调整 → 空间效果 → 标准化 → 格式转换
```

#### 处理参数标准
```yaml
processing_chain:
  compression:
    ratio: 2:1
    threshold: -20dB
    attack: 10ms
    release: 100ms
  
  eq:
    low_cut: 80Hz
    high_cut: 12kHz
    presence_boost: 2kHz, +3dB, Q=1.5
  
  reverb:
    size: "small room"
    decay: 1.2s
    mix: 15%
  
  normalization:
    target_lufs: -16 LUFS
    true_peak: -1.0dB
```

### 3.3 文件格式管理
#### 格式矩阵
| 使用场景 | 主要格式 | 备选格式 | 比特率 | 特点 |
|----------|----------|----------|--------|------|
| **Web应用** | OGG Vorbis | MP3 | 96kbps | 小文件，良好压缩 |
| **桌面应用** | WAV | FLAC | 无损 | 高质量，无压缩 |
| **移动应用** | AAC | MP3 | 64kbps | 高效率，移动优化 |
| **视频制作** | WAV 24-bit | AIFF | 无损 | 专业制作质量 |

#### 文件命名规范
```
athena_[category]_[function]_[variant]_[duration]ms.[format]
示例: athena_ui_confirm_01_150ms.ogg
```

## 4. 使用指南

### 4.1 交互音效使用原则
#### 响应时间要求
```yaml
response_timing:
  immediate_feedback: "< 100ms"  # 点击、悬停等立即反馈
  process_feedback: "100-300ms"  # 处理开始/结束反馈
  notification: "300-500ms"      # 通知提醒
  narrative: "500ms-3s"          # 叙事音效
```

#### 音量层级
```yaml
volume_hierarchy:
  primary_interaction: "-12dB"   # 主要交互音效
  secondary_feedback: "-18dB"    # 次要反馈
  background_ambient: "-24dB"    # 背景环境音
  notification: "-15dB"          # 通知音效
```

### 4.2 场景化使用示例
#### Web应用集成
```javascript
class AthenaSoundManager {
  constructor() {
    this.sounds = new Map();
    this.masterVolume = 0.7;
    this.context = new (window.AudioContext || window.webkitAudioContext)();
  }
  
  async loadSound(id, url) {
    const response = await fetch(url);
    const arrayBuffer = await response.arrayBuffer();
    const audioBuffer = await this.context.decodeAudioData(arrayBuffer);
    
    this.sounds.set(id, audioBuffer);
  }
  
  playSound(id, options = {}) {
    const audioBuffer = this.sounds.get(id);
    if (!audioBuffer) return;
    
    const source = this.context.createBufferSource();
    source.buffer = audioBuffer;
    
    const gainNode = this.context.createGain();
    gainNode.gain.value = (options.volume || 1.0) * this.masterVolume;
    
    source.connect(gainNode);
    gainNode.connect(this.context.destination);
    
    source.start();
  }
}
```

#### React组件示例
```jsx
import { useEffect, useRef } from 'react';

const AthenaButton = ({ onClick, soundId = 'ui_confirm_01' }) => {
  const audioRef = useRef(null);
  
  const handleClick = (e) => {
    // 播放音效
    if (audioRef.current) {
      audioRef.current.currentTime = 0;
      audioRef.current.play().catch(console.error);
    }
    
    // 执行原有点击处理
    onClick?.(e);
  };
  
  return (
    <>
      <button onClick={handleClick} className="athena-button">
        点击我
      </button>
      <audio 
        ref={audioRef} 
        src={`/sounds/${soundId}.ogg`}
        preload="auto"
      />
    </>
  );
};
```

### 4.3 可访问性考虑
#### 音效开关控制
```html
<div class="sound-settings">
  <label>
    <input type="checkbox" id="sound-toggle" checked>
    启用交互音效
  </label>
  
  <label>
    音效音量
    <input type="range" id="sound-volume" min="0" max="100" value="70">
  </label>
</div>
```

#### 静音模式检测
```javascript
// 检测用户是否开启了系统级静音偏好
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
const prefersReducedSound = window.matchMedia('(prefers-reduced-sound: reduce)');

if (prefersReducedSound.matches || prefersReducedMotion.matches) {
  // 自动降低音效音量或禁用某些音效
  soundManager.setMasterVolume(0.3);
  soundManager.disableBackgroundSounds();
}
```

## 5. 质量保证

### 5.1 技术质量检查清单
- [ ] 文件格式符合标准，无压缩伪影
- [ ] 采样率和位深度符合规范
- [ ] 无削波失真（True Peak < -1.0dB）
- [ ] 响度标准化（-16 LUFS ±1）
- [ ] 起始无爆音，结束无咔嗒声

### 5.2 听觉质量检查清单
- [ ] 音效清晰可辨，不模糊
- [ ] 音调适中，不刺耳
- [ ] 动态范围适当，不过于突兀
- [ ] 与视觉反馈同步协调
- [ ] 品牌一致性良好

### 5.3 用户体验检查清单
- [ ] 音效提供有用反馈，不干扰
- [ ] 不同音效之间区分度明显
- [ ] 音量层级合理，主次分明
- [ ] 可访问性选项完整
- [ ] 性能影响可接受（加载时间、内存占用）

## 6. 资源下载

### 6.1 标准音效包
| 包名称 | 包含内容 | 文件数量 | 总大小 | 适用场景 |
|--------|----------|----------|--------|----------|
| **核心交互包** | 基础UI音效、通知音效 | 20个 | 2MB | Web/移动应用 |
| **完整音效包** | 所有类别音效 | 50个 | 10MB | 桌面应用、游戏 |
| **高质量包** | 24-bit WAV格式 | 50个 | 50MB | 专业视频制作 |
| **精简包** | 关键交互音效 | 10个 | 1MB | 性能敏感场景 |

### 6.2 源文件资源
- **合成器预设**：`athena_synth_presets.zip` - Surge XT/Vital预设
- **工程文件**：`sound_design_projects.zip` - DAW工程文件
- **采样库**：`athena_samples_library.zip` - 原始采样

### 6.3 开发资源
- **Web Audio API示例**：`web_audio_examples/`
- **Unity音频集成**：`unity_integration/`
- **React音效组件**：`react_sound_components/`

## 7. 版本管理

### 7.1 版本策略
| 版本类型 | 更新频率 | 变更范围 | 向后兼容 |
|----------|----------|----------|----------|
| **主版本** | 每年1-2次 | 重大设计变更，新类别 | 不保证 |
| **次版本** | 每季度1次 | 新增音效，改进现有 | 保证 |
| **补丁版本** | 按需发布 | 错误修复，技术优化 | 保证 |

### 7.2 变更日志格式
```markdown
## v1.1.0 - 2026-07-01
### 新增
- 添加叙事音效类别（5个新音效）
- 添加环境氛围音效（3个新音效）

### 改进
- 优化所有音效的响度一致性
- 改进UI音效的清晰度

### 修复
- 修复process_error_01中的削波问题
- 修复文件命名不一致问题
```

## 8. 维护和更新

### 8.1 用户反馈收集
```yaml
feedback_channels:
  - "应用内反馈表单"
  - "GitHub Issues"
  - "用户调查问卷"
  - "A/B测试数据"
```

### 8.2 更新流程
1. **需求收集**：从用户反馈、产品需求中收集音效需求
2. **设计评审**：设计新音效，评审是否符合品牌规范
3. **技术实现**：合成、处理、优化音效
4. **质量测试**：技术质量、听觉质量、用户体验测试
5. **发布部署**：打包发布，更新文档
6. **效果评估**：收集使用数据，评估改进效果

---

**文档版本**: v1.0  
**最后更新**: 2026-04-16  
**音效总数**: 50+  
**覆盖场景**: 5大类，20+子类  
**质量等级**: 专业级音效设计  
**维护团队**: Athena 用户体验团队  
**设计原则**: 科技感 + 情感化 + 功能性