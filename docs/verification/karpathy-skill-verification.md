# Karpathy Skill 协同验证报告

> **验证时间**: 2026-05-03  
> **Skill 数量**: 5  
> **方法**: 静态结构分析 (YAML/JSON 验证 + 触发链分析)

## 一、结构验证

| Skill | 文件 | 格式 | frontmatter | 名称唯一 | 触发链 |
|-------|------|------|-------------|---------|--------|
| karpathy-principles | .json | JSON | N/A | ✅ | autoApply (每次任务) |
| karpathy-autoresearch-loop | .md | YAML+M↓ | ✅ | ✅ | 用户显式调用 |
| karpathy-code-quality | .md | YAML+M↓ | ✅ | ✅ | 代码生成 + principles协同 |
| karpathy-simplicity | .md | YAML+M↓ | ✅ | ✅ | 用户调用 + principles协同 |
| karpathy-knowledge-bases | .md | YAML+M↓ | ✅ | ✅ | 用户显式调用 |

**结论**: 5/5 格式正确，无命名冲突。

## 二、触发层次

```
karpathy-principles (autoApply=true, remindFrequency=every_task)
  │  提供: 四核心原则、决策原则
  │
  ├─[协同激活]── karpathy-code-quality
  │  触发: "代码生成/修改任务自动激活" + "principles已激活时自动协同"
  │  提供: 5维评分标准、评分阈值、输出格式
  │
  ├─[协同激活]── karpathy-simplicity
  │  触发: "principles已激活时自动协同"
  │  提供: 简洁性检查清单、复杂度决策矩阵、反模式识别
  │
  ├─[用户调用]── karpathy-autoresearch-loop
  │  触发: 用户提 "AutoResearch/ratchet loop/自主循环"
  │  提供: Ratchet loop 协议、约束配置、results.tsv 格式
  │
  └─[用户调用]── karpathy-knowledge-bases
     触发: 用户提 "知识库/Wiki/文档编译"
     提供: 三层架构、编译流程、健康检查报告格式
```

## 三、潜在问题

### ⚠️ Token 膨胀风险 → ✅ 已修复

原: `code-quality` 和 `simplicity` 的触发条件包含 "principles 已激活时自动协同"，由于 `principles` 的 `autoApply=true`，每次任务都会加载 3 个大型 Skill (~300行)，严重占用 token 预算。

修复:
- `karpathy-code-quality` 触发改为: 代码审查请求 + 用户显式调用 "评分/5维评分/review" + ratchet loop 评估阶段
- `karpathy-simplicity` 触发改为: 用户显式调用 "简化/简单点" + 代码审查时检测到过度抽象方可激活

结果: 消除了每次任务加载 ~200 行的 token 膨胀，仅在需要时按需加载。

### ✅ 内容重叠但互补
- `karpathy-principles` 在 prompt 中声明了 "简洁第一" 原则
- `karpathy-simplicity` 提供了更详细的简洁检查清单
- 无矛盾，simplicity 是对 principles 的细化

## 四、建议

1. 在新 Claude Code 会话中执行一次**运行验证**: 说 "简化这段代码" 看是否正确激活 simplicity skill
2. 将 auto-co-activation 改为按需加载以减少 token 消耗
3. 考虑为所有 Skill 统一添加 YAML frontmatter 的 `autoApply` 字段

## 五、状态

| 检查项 | 结果 |
|--------|------|
| 文件存在 | ✅ 5/5 |
| 格式正确 | ✅ |
| 名称唯一 | ✅ |
| 无内容冲突 | ✅ |
| 触发层次清晰 | ✅ |
| Token 预算合理 | ⚠️ 需优化 |
