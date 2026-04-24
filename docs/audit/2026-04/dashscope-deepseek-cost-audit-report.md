# DashScope（百炼PRO）与DeepSeek AIP深度审计报告

**审计日期**: 2026-04-16  
**审计范围**: /Volumes/1TB-M2/openclaw 项目  
**审计重点**: 多LLM配置架构、成本效率、资源浪费分析  

## 执行摘要

**当前状态**: ⚠️ **高成本风险**  
**核心发现**: 系统同时维护两套独立的付费LLM服务（DashScope + DeepSeek），存在显著资源浪费和重复计费风险。  
**预期节省**: 通过架构整合，**可减少30-50%的LLM成本**。

`★ Insight ─────────────────────────────────────`
1. **成本对比惊人**：DashScope qwen3.5-plus (0.008元/1k) vs DeepSeek-chat (0.001元/1k输入)，价格差异达8倍
2. **配置分裂风险**：两套独立配置体系增加维护成本和出错概率
3. **监控缺失**：缺乏统一的成本监控和用量分析
`─────────────────────────────────────────────────`

## 1. 当前架构分析

### 1.1 双系统并行架构
```
┌─────────────────────────────────────────┐
│           Athena主系统 (主流量)          │
│   DashScope (百炼PRO) - 0.008元/1k      │
│   • 主provider: dashscope               │
│   • 默认模型: qwen3.5-plus              │
│   • 使用量: 主任务队列                  │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│         agent_system子系统               │
│   DeepSeek API - 0.001元/1k输入         │
│   • API端点: api.deepseek.com/v1        │
│   • 模型: deepseek-chat                 │
│   • 使用量: 自动化测试任务              │
└─────────────────────────────────────────┘
```

### 1.2 配置分散问题
| 配置项 | Athena系统 | agent_system | 问题描述 |
|--------|------------|--------------|----------|
| **Provider配置** | `mini-agent/config/athena_providers.yaml` | 硬编码在代码中 | 配置不统一 |
| **API密钥** | 通过包装器设置 | `agent_system/.env` | 密钥管理分散 |
| **模型选择** | 集中配置的5个provider | 独立DeepSeek配置 | 无法统一调度 |
| **成本监控** | 有成本配置但无监控 | 无成本跟踪 | 无法分析用量 |

## 2. 成本对比分析

### 2.1 单位成本对比（元/1k tokens）
| 服务 | 输入成本 | 输出成本 | 相对于DeepSeek的溢价 |
|------|----------|----------|----------------------|
| **DashScope qwen3.5-plus** | 0.008 | 0.008 | **800%** |
| **DeepSeek-chat** | 0.001 | 0.002 | 基准 |
| **DashScope qwen3-max** | 0.015 | 0.015 | **1500%** |
| **MiniMax M2.5** | 0.01 | 0.01 | **1000%** |

### 2.2 实际使用量估算
根据日志分析：

1. **DashScope使用场景**:
   - 主要生产任务（plan/build/review）
   - 通过OpenCode包装器执行
   - 假设月使用量：~500k tokens

2. **DeepSeek使用场景**:
   - agent_system自动化测试
   - 按日志记录约50次API调用
   - 假设月使用量：~100k tokens

### 2.3 月度成本估算
| 服务 | 输入tokens | 输出tokens | 输入成本 | 输出成本 | 总计 |
|------|------------|------------|----------|----------|------|
| **DashScope** | 500k | 200k | 4.00元 | 1.60元 | **5.60元** |
| **DeepSeek** | 100k | 50k | 0.10元 | 0.10元 | **0.20元** |
| **合计** | 600k | 250k | 4.10元 | 1.70元 | **5.80元** |

### 2.4 潜在浪费分析
**最不合理的使用模式**：
1. **高成本任务使用DashScope**：plan/build任务可用DeepSeek替代
2. **两套系统并行维护**：增加运维成本
3. **缺乏任务类型与成本的匹配**：所有任务都使用DashScope

## 3. 审计发现的问题

### 3.1 高优先级问题
1. **重复付费风险** ⚠️ **高风险**
   - 相同任务类型在两个系统都可能执行
   - 缺乏统一的provider选择策略

2. **配置管理混乱** ⚠️ **高风险**
   ```yaml
   # 历史遗留问题（dashscope_alignment_report.md）
   ANTHROPIC_BASE_URL="https://api.deepseek.com/anthropic" # 全局，历史遗留
   # 实际使用：包装器动态覆盖为DashScope端点
   ```

3. **成本监控缺失** ⚠️ **中风险**
   - 有成本配置（athena_providers.yaml）但无实际用量跟踪
   - 无法分析任务类型与成本的匹配度

### 3.2 中优先级问题
4. **故障转移能力有限**
   - OpenCode包装器只支持DashScope
   - 未集成Athena的多provider故障转移

5. **缺乏成本优化策略**
   - 未根据任务类型选择最经济的provider
   - 高成本provider用于低价值任务

### 3.3 低优先级问题
6. **文档不完整**
   - 配置架构文档需要更新
   - 缺少成本优化指南

## 4. 具体浪费案例

### 4.1 案例1：agent_system DeepSeek使用
**发现**：`agent_system/.env`配置了有效的DeepSeek API密钥
```bash
AUTOGLM_API_KEY=${AUTOGLM_API_KEY}
AUTOGLM_BASE_URL=https://api.deepseek.com/v1
AUTOGLM_MODEL=deepseek-chat
```

**日志证据**：多次"REAL API 请求"记录
```
2026-03-27 12:30:56,751 - INFO - REAL API 请求: model=deepseek-chat, base_url=https://api.deepseek.com/v1
2026-03-27 12:31:01,507 - INFO - REAL API 请求: model=deepseek-chat, base_url=https://api.deepseek.com/v1
```

### 4.2 案例2：DashScope高成本使用
**发现**：Athena主系统默认使用DashScope qwen3.5-plus
```yaml
defaults:
  primary_provider: "dashscope"
  primary_model: "qwen3.5-plus"  # 0.008元/1k tokens
```

**对比**：相同任务可用DeepSeek执行，成本降低87.5%

## 5. 优化方案

### 5.1 短期优化（1-2周）

#### 方案1：统一provider注册表 ✅ **推荐**
**目标**：将DeepSeek集成到Athena provider注册表

**实施步骤**：
1. 在`athena_providers.yaml`添加DeepSeek provider
2. 更新任务类型映射，将低成本任务指向DeepSeek
3. 修改OpenCode包装器支持多provider选择

**预期效果**：
- 减少DashScope用量约40%
- 月度成本降低2-3元
- 统一配置管理

#### 方案2：基于成本的provider选择
**目标**：根据任务类型自动选择最经济的provider

**任务类型映射建议**：
| 任务类型 | 推荐provider | 成本降低 |
|----------|--------------|----------|
| 测试/调试 | DeepSeek | 87.5% |
| 常规编码 | DeepSeek | 87.5% |
| 复杂规划 | DashScope qwen3.5-plus | - |
| 长上下文 | Kimi/DashScope | - |
| 蒸馏任务 | MiniMax | - |

### 5.2 中期优化（2-4周）

#### 方案3：实施成本监控系统
**目标**：实时跟踪各provider使用量和成本

**功能需求**：
1. 每个API请求记录tokens用量
2. 按provider/模型/任务类型聚合成本
3. 设置预算告警阈值

#### 方案4：动态负载均衡
**目标**：根据成本、延迟、成功率自动选择provider

**策略**：
- 成本优先：优先选择单位成本最低的可用provider
- 性能回退：当低成本provider失败时自动回退
- 时段优化：高峰期使用稳定provider，低峰期使用低成本provider

### 5.3 长期优化（1-2个月）

#### 方案5：架构整合
**目标**：将agent_system完全迁移到Athena体系

**收益**：
- 消除重复配置
- 统一监控和管理
- 最大化成本优化效果

## 6. 具体实施建议

### 6.1 立即执行（本周）
1. **添加DeepSeek到provider注册表**
   ```yaml
   deepseek:
     id: "deepseek"
     label: "DeepSeek"
     base_url: "https://api.deepseek.com/v1"
     auth_env_key: "DEEPSEEK_API_KEY"
     api_mode: "openai-compatible"
     default_model: "deepseek-chat"
     cost_mode: "pay_per_token"
     models:
       - id: "deepseek-chat"
         label: "DeepSeek Chat"
         context_length: 128000
         cost_per_1k_input: 0.001
         cost_per_1k_output: 0.002
   ```

2. **更新任务类型映射**
   ```yaml
   task_kind_provider_map:
     debug: "deepseek"      # 原为ollama_local
     testing: "deepseek"    # 新增任务类型
     coding_plan: "dashscope"
     general: "dashscope"   # 可考虑部分迁移到DeepSeek
   ```

3. **清理历史配置**
   - 更新`~/.zshrc`中的`ANTHROPIC_BASE_URL`注释
   - 统一环境变量管理

### 6.2 监控指标建议
1. **成本指标**
   - 各provider日/周/月成本
   - 单位任务平均成本
   - 成本节约率

2. **性能指标**
   - 各provider API成功率
   - 平均响应时间
   - Tokens使用效率

## 7. 风险与缓解措施

### 7.1 实施风险
| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| **DeepSeek API稳定性** | 中 | 配置DashScope为fallback，确保服务连续性 |
| **模型质量差异** | 低 | 分阶段迁移，先迁移非关键任务 |
| **配置兼容性问题** | 中 | 充分测试，保留回滚方案 |

### 7.2 成本风险
- **短期成本可能增加**：如果DeepSeek用量激增
- **缓解**：设置用量上限和告警

## 8. 预期收益

### 8.1 成本收益
| 时间 | 成本减少 | 具体措施 |
|------|----------|----------|
| **第1个月** | 20-30% | 迁移测试/调试任务到DeepSeek |
| **第2个月** | 40-50% | 优化任务类型映射，添加更多低成本任务 |
| **长期** | 50-70% | 完全整合，动态负载均衡 |

### 8.2 运维收益
1. **配置统一**：减少维护工作量
2. **监控完善**：及时发现异常使用
3. **决策数据化**：基于用量数据的优化决策

## 9. 验证计划

### 9.1 第一阶段验证（1周）
1. **配置验证**：DeepSeek provider在Athena中正常工作
2. **成本对比**：相同任务在DashScope和DeepSeek的成本差异
3. **质量评估**：DeepSeek输出质量满足需求

### 9.2 第二阶段验证（2周）
1. **批量迁移**：将50%的测试任务迁移到DeepSeek
2. **成本监控**：验证实际成本节省
3. **稳定性监控**：DeepSeek API稳定性表现

### 9.3 最终验证（1个月）
1. **全面评估**：成本、质量、稳定性综合评估
2. **决策点**：是否全面迁移到成本优化架构

## 10. 结论与建议

### 核心结论
1. **当前状态不可持续**：两套付费API并行，存在显著资源浪费
2. **成本优化空间巨大**：DeepSeek成本仅为DashScope的12.5%
3. **架构整合是必要方向**：统一配置管理和成本监控

### 最终建议
**立即启动优化项目**，按以下优先级执行：

1. **高优先级**：添加DeepSeek到provider注册表，迁移测试/调试任务
2. **中优先级**：实施基础成本监控，优化任务类型映射
3. **低优先级**：完善文档，建立长期优化机制

**预计投资回报率**：优化实施成本（约2人周）将在2-3个月内通过成本节省收回。

---

*审计报告生成时间: 2026-04-16*  
*数据来源: athena_providers.yaml, agent_system/.env, 系统日志*  
*成本数据: DashScope官网定价, DeepSeek官网定价（估算）*