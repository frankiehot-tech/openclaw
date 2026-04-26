# Claude Code 配置深度审计报告

> 生成时间：2026-04-23
> 审计范围：完整 AI 配置体系（含 3 个提供商、11 个模型、8 个别名）

---

## 一、整体架构概览

您的系统配置了一个**多模型智能路由体系**，包含以下层次：

```
用户命令 → .zshrc 别名 → 路由器 (claude-dual-model.sh) → DashScope 适配器 → 百炼 API
                                         → Ollama 本地服务
                                         → DeepSeek API
                                         → Anthropic API
```

**已配置的 3 个提供商：**
| 提供商 | 类型 | 基础 URL | API Key 来源 |
|--------|------|----------|-------------|
| 阿里云百炼 | DashScope | dashscope.aliyuncs.com | DASHSCOPE_API_KEY (Keychain) |
| DeepSeek | OpenAI 兼容 | api.deepseek.com | DEEPSEEK_API_KEY (Keychain) |
| Anthropic | 原生 | api.anthropic.com | ANTHROPIC_API_KEY (Keychain) |

**已定义的 11 个模型：**
- 百炼系列 (7)：qwen-max, qwen-plus, qwen-turbo, qwen-coder-plus, qwen-long, qwen3-235B-A22B, qwen3.6-plus
- DeepSeek 系列 (2)：deepseek-chat, deepseek-reasoner
- Anthropic 系列 (2)：claude-sonnet-4, claude-opus-4

---

## 二、问题清单（共发现 6 个问题）

### 严重问题（导致功能完全失效）

| # | 问题 | 影响范围 | 根因 | 修复建议 |
|---|------|----------|------|----------|
| 1 | **`claude-max` 别名指向不存在的脚本** | `claude-max` 完全不可用 | 别名指向 `claude-qwen-alt.sh`，但该文件不存在 | 改为 `claude-dual-model.sh 5` |
| 2 | **`claude-pro` 别名指向不存在的脚本** | `claude-pro` 完全不可用 | 别名指向 `claude-pro.sh`，但该文件不存在 | 注释或删除此行 |

### 中等问题（部分功能异常）

| # | 问题 | 影响范围 | 根因 | 修复建议 |
|---|------|----------|------|----------|
| 3 | **BAILIAN_API_KEY 硬编码为空** | 百炼直连模式失效 | `.zshrc` 第 182 行硬编码为空字符串 | 改为从 DASHSCOPE_API_KEY 继承 |
| 4 | **Secret 加载路径错误** | 密钥可能无法正确加载 | 指向 `~/.config/secret-env/load-keychain-secrets.sh`，文件不存在 | 改为使用存在的 `load-local-secrets.sh` |

### 轻微问题（体验/安全隐患）

| # | 问题 | 影响范围 | 根因 | 修复建议 |
|---|------|----------|------|----------|
| 5 | **claude-small 提示信息误导** | 用户可能误解为云端模型 | 提示语显示 `Gemma 4 E4B`，未标识为本地 Ollama | 添加 `[本地 Ollama]` 标识 |
| 6 | **旧修复报告未清理** | 磁盘浪费，可能产生误导 | `fix-summary-report.md` 是之前修复的遗留文档 | 可安全删除 |

---

## 三、别名映射关系全览

| 别名 | 实际行为 | 依赖服务 | 状态评估 |
|------|----------|----------|----------|
| `claude` | `claude-dual-model.sh`（自动路由） | 脚本存在 | 可用 |
| `claude-small` | 直接设置环境变量 → `gemma4-claude` @ Ollama | Ollama 本地服务 | 可用（需本地运行） |
| `claude-big` | 同 small | Ollama 本地服务 | 可用（需本地运行） |
| `claude-pro` | `claude-pro.sh` | 脚本不存在 | 不可用 |
| `claude-deepseek` | `claude-dual-model.sh 1` | DeepSeek API | 可用（需密钥） |
| `claude-backup` | `claude-dual-model.sh 2` | DeepSeek API | 可用（需密钥） |
| `claude-qwen` | `claude-dual-model.sh 3` | DashScope 适配器 | 可用 |
| `claude-bailian` | 自动启动适配器 + `dual-model.sh 5` | DashScope 适配器 | 可用（有自动恢复） |
| `claude-max` | `claude-qwen-alt.sh -m qwen3.6-plus` | 脚本不存在 | 不可用 |
| `claude-ollama` | `claude-dual-model.sh local` | Ollama | 可用 |

---

## 四、服务状态验证

### Ollama 本地服务
```
状态：运行中
模型列表：
  - gemma4-claude:latest (8.0B, Q4_K_M)
  - gemma4:e4b (8.0B, Q4_K_M)
  - gemma4:latest (8.0B, Q4_K_M)
  - qwen2.5:3b (3.1B, Q4_K_M)
  - nomic-embed-text:latest (137M, F16)
  - deepseek-r1:8b (8.2B, Q4_K_M)
```

### DashScope 适配器
```
状态：运行中 (版本 3.0)
监听地址：http://127.0.0.1:8080
默认模型：qwen-max
支持模型：qwen-max, qwen-plus, qwen-turbo, qwen-coder-plus, qwen-long, qwen3-235B-A22B, qwen3.6-plus
```

---

## 五、修复方案

### 手动修复步骤

请编辑 `~/.zshrc` 文件，进行以下修改：

#### 1. 修复 `claude-max` 别名（第170行）

**原配置：**
```bash
alias claude-max='/Users/frankie/claude-code-setup/claude-qwen-alt.sh -m qwen3.6-plus'
```

**修复为：**
```bash
alias claude-max='/Users/frankie/claude-code-setup/claude-dual-model.sh 5'
```

#### 2. 注释 `claude-pro` 别名（第148行）

**原配置：**
```bash
alias claude-pro="/Users/frankie/claude-pro.sh"
```

**修复为：**
```bash
# alias claude-pro="/Users/frankie/claude-pro.sh"  # 脚本不存在，已禁用
```

#### 3. 修复 `BAILIAN_API_KEY`（第182行）

**原配置：**
```bash
export BAILIAN_API_KEY=""  # 请在此填入阿里云百炼API密钥
```

**修复为：**
```bash
export BAILIAN_API_KEY="${DASHSCOPE_API_KEY:-}"  # 从 DASHSCOPE_API_KEY 继承
```

#### 4. 优化 `claude-small` 提示（第227行）

**原配置：**
```bash
echo "🚀 Gemma 4 E4B (128K ctx)"
```

**修复为：**
```bash
echo "🚀 [本地 Ollama] Gemma 4 E4B (128K ctx)"
```

#### 5. 修复 Secret 加载路径（第115-117行）

**原配置：**
```bash
if [ -f "$HOME/.config/secret-env/load-keychain-secrets.sh" ]; then
  source "$HOME/.config/secret-env/load-keychain-secrets.sh"
fi
```

**修复为：**
```bash
if [ -f "$HOME/claude-code-setup/load-local-secrets.sh" ]; then
  source "$HOME/claude-code-setup/load-local-secrets.sh"
fi
```

---

## 六、文件依赖关系图

```
.zshrc
├── claude-dual-model.sh          ✅ 存在且功能完整
├── start-dashscope-adapter.sh    ✅ 存在
├── dashscope-adapter.py          ✅ 存在且运行中 (v3.0)
├── claude-qwen-alt.sh            ❌ 不存在（claude-max 别名指向此处）
├── claude-pro.sh                 ❌ 不存在（claude-pro 别名指向此处）
├── load-local-secrets.sh         ✅ 存在
└── bailian-usage-monitor.sh      ✅ 存在

~/.claude/
├── settings.json                 ✅ 已审查（MCP 配置一致）
└── settings.local.json           ✅ 已审查

config/ai-config/
├── models.yaml                   ✅ 已审查
└── profiles/
    ├── bailian-pro.yaml          ✅ 存在
    └── deepseek.yaml             ✅ 存在
```

---

## 七、验证命令

修复完成后，运行以下命令验证配置：

```bash
# 1. 验证别名可用性
alias | grep claude

# 2. 验证密钥加载
bailian-test

# 3. 验证适配器状态
adapter-status

# 4. 验证 Ollama 状态
ollama-status

# 5. 运行完整诊断
bash /Users/frankie/claude-code-setup/diagnose-and-fix.sh
```

---

## 八、建议的下一步行动

1. ✅ 按照上述修复步骤编辑 `~/.zshrc`
2. ✅ 运行 `source ~/.zshrc` 使更改生效
3. ✅ 运行验证命令确认所有配置正常
4. ✅ 删除旧的 `fix-summary-report.md`（可选）
5. ✅ 考虑创建 `claude-config.sh` 以支持 `dual-model.sh` 和 `qwen-max.sh`（如需使用）
