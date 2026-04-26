# Wiki 规约

## 页面类型

| 类型 | 前缀 | 用途 | 大小上限 |
|------|------|------|----------|
| 架构 | `ARCHITECTURE.md` | 系统组织、组件、数据流 | 400 行 |
| 决策 | `DECISIONS.md` | 设计决策记录 | 持续追加 |
| 概念 | `CONCEPTS.md` | 领域概念、术语定义 | 400 行 |
| 模式 | `PATTERNS.md` | 重复使用的方案、最佳实践 | 400 行 |
| 会话 | `sessions/YYYY-MM-DD.md` | 会话知识摘要 | 200 行 |

## 文件格式

### 所有页面必须遵守

1. **YAML frontmatter**（可选但推荐）：
   ```yaml
   ---
   type: architecture|decision|concept|pattern|session
   created: 2026-04-24
   updated: 2026-04-24
   tags: [tag1, tag2]
   ---
   ```

2. **Markdown 正文**：标准的 GitHub Flavored Markdown

3. **交叉引用**：使用 `[[PageName]]` 或 `[[PageName|显示文本]]` 格式的 wiki 链接

### 链接约定

- 同 wiki 内链接：`[[ARCHITECTURE]]` → 指向 `ARCHITECTURE.md`
- 带别名链接：`[[DECISIONS|为什么选了 SQLite]]`
- 外部链接：标准 Markdown `[文本](url)`

### 页面大小管理

- **软上限**：400 行
- **硬上限**：800 行
- 超过上限时，拆分为子页面（如 `DECISIONS/2026-04.md`）

## 操作规则

### 读取

1. 始终从 `INDEX.md` 开始语义查找
2. 读相关页面 → 跟踪 `[[wikilinks]]` → 合成回答
3. 引用来源：在回答中注明来自哪个 wiki 页面

### 写入

1. 新知识：追加到对应的已有页面，或创建新页面
2. 精炼知识：使用结构化替换更新已有内容（不重写整页）
3. 每次修改后：更新 `LOG.md`
4. 每 5 次修改后：重建 `INDEX.md`（添加新条目）

### 蒸馏条件

Agent 自动判断何时写入 wiki：

| 信号 | 操作 |
|------|------|
| 同一主题被讨论 ≥ 2 次 | 创建/更新概念或模式条目 |
| 做出架构决策 | 追加到 `DECISIONS.md` |
| 识别到重复模式 | 追加到 `PATTERNS.md` |
| 用户明确说"记住这个" | 立即写入相关页面 |
| 修复了反复出现的 bug | 追加到 `PATTERNS.md` 作为陷阱记录 |

## 知识保质期

- 每个页面有 `updated` 字段
- 超过 30 天未更新的页面，Agent 应标记为"可能过时"
- 超过 90 天未更新的页面，Agent 应提示是否需要审查
