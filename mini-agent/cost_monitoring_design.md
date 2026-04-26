# 成本监控系统设计文档

## 概述

基于审计报告的第二阶段优化建议，设计统一成本监控系统。系统将跟踪所有LLM API请求的成本，提供实时监控、聚合分析和告警功能。

## 当前状态分析

### 已有组件
1. **Provider Registry** (`provider_registry.py`)
   - 完整的provider和模型配置
   - `estimate_cost()` 函数：根据tokens估算成本
   - 成本数据：DashScope 0.008元/1k，DeepSeek 0.001元/1k等

2. **金融监控器** (`financial_monitor.py`)
   - 预算状态跟踪
   - 燃烧率计算
   - 告警系统
   - 但未与provider成本直接集成

3. **OpenCode包装器** (`/Volumes/1TB-M2/openclaw/bin/opencode-athena`)
   - API调用的入口点
   - 已支持多provider路由
   - 可捕获执行上下文

### 缺失功能
1. **Tokens使用量捕获**：API响应中提取input/output tokens
2. **成本记录存储**：持久化存储成本数据
3. **聚合分析**：按维度（provider/模型/任务类型）统计
4. **实时仪表板**：可视化展示成本和使用趋势

## 架构设计

### 1. 数据收集层
```
OpenCode包装器 → 成本跟踪器 → 数据存储
       ↓                ↓
   API响应       Provider Registry
   (tokens)     (成本计算)
```

### 2. 核心模块设计

#### 2.1 CostTracker类
```python
class CostTracker:
    def __init__(self, storage_backend="sqlite"):
        self.registry = get_registry()
        self.storage = StorageBackend(storage_backend)
    
    def record_request(self, request_id, provider_id, model_id, 
                       task_kind, input_tokens, output_tokens,
                       cost_estimation=None, metadata=None):
        """记录API请求成本"""
        
    def get_daily_summary(self, date=None):
        """获取每日成本摘要"""
        
    def get_provider_breakdown(self, start_date, end_date):
        """按provider分解成本"""
        
    def get_task_kind_analysis(self, period="daily"):
        """按任务类型分析成本"""
```

#### 2.2 存储后端
- **SQLite**：轻量级，适合本地部署
- **JSON文件**：简单，易于调试
- **结构**：
  ```sql
  CREATE TABLE cost_records (
      id TEXT PRIMARY KEY,
      timestamp DATETIME,
      provider_id TEXT,
      model_id TEXT,
      task_kind TEXT,
      input_tokens INTEGER,
      output_tokens INTEGER,
      estimated_cost REAL,
      actual_cost REAL,
      metadata JSON
  );
  ```

#### 2.3 集成点
1. **OpenCode包装器修改**：
   - 捕获API响应中的tokens使用量
   - 调用CostTracker.record_request()
   - 对于provider替代脚本，估算tokens（使用启发式方法）

2. **Provider Registry扩展**：
   - 添加成本历史查询接口
   - 支持成本趋势分析

3. **金融监控器集成**：
   - CostTracker提供数据给FinancialMonitor
   - 统一告警系统

### 3. Tokens使用量获取策略

#### 3.1 直接API响应
- OpenAI兼容API返回`usage`字段：
  ```json
  {
    "usage": {
      "prompt_tokens": 100,
      "completion_tokens": 50,
      "total_tokens": 150
    }
  }
  ```

#### 3.2 估算策略（备用）
当无法获取准确tokens时：
- 输入tokens：`len(text) / 4`（近似估算）
- 输出tokens：`len(response) / 4`
- 使用provider_registry的`estimate_cost()`计算

#### 3.3 Provider替代脚本适配
- 修改`claude-deepseek-alt.sh`和`claude-qwen-alt.sh`返回tokens信息
- 或通过包装器日志分析估算

### 4. 仪表板和报告

#### 4.1 命令行接口
```bash
# 查看今日成本
python -m agent.cost_tracker --today

# provider成本对比
python -m agent.cost_tracker --provider-breakdown --period=week

# 任务类型分析
python -m agent.cost_tracker --task-analysis --period=month

# 成本趋势
python -m agent.cost_tracker --trend --days=30
```

#### 4.2 可视化输出
```
📊 成本监控报告 (2026-04-16)
========================================
总成本: ¥8.42 (昨日: ¥12.15 ▼30.7%)

按Provider分解:
• DeepSeek:   ¥0.85 (10.1%) - 87.5%节省
• DashScope:  ¥7.57 (89.9%) - 主成本来源

按任务类型:
• debug:      ¥0.15 (1.8%)  - DeepSeek
• testing:    ¥0.70 (8.3%)  - DeepSeek  
• general:    ¥4.22 (50.1%) - DashScope
• coding_plan:¥3.35 (39.8%) - DashScope

💡 优化建议:
1. 将30%的general任务迁移到DeepSeek，可节省¥1.27/日
2. testing任务已优化完成，成本降低87.5%
```

#### 4.3 实时监控
- 每60秒更新一次指标
- Web界面可选（Flask简单服务）
- 预算告警集成到现有金融监控器

### 5. 成本优化策略引擎

#### 5.1 任务迁移建议
基于历史数据分析：
```python
def analyze_migration_potential(task_kind, target_provider):
    """分析将任务类型迁移到目标provider的潜在节省"""
    historical_cost = get_historical_cost(task_kind)
    target_cost = estimate_target_cost(task_kind, target_provider)
    savings = historical_cost - target_cost
    return {
        "task_kind": task_kind,
        "current_provider": current_provider,
        "target_provider": target_provider,
        "savings_percentage": savings / historical_cost,
        "monthly_savings": savings * 30
    }
```

#### 5.2 动态负载均衡策略
```python
class LoadBalancer:
    def select_provider(self, task_kind, constraints):
        """根据约束选择最优provider"""
        
        candidates = self._get_available_providers(task_kind)
        
        # 策略1: 成本优先
        if constraints.get("priority") == "cost":
            return self._select_lowest_cost(candidates)
        
        # 策略2: 性能优先  
        elif constraints.get("priority") == "performance":
            return self._select_highest_quality(candidates)
        
        # 策略3: 混合策略（默认）
        else:
            return self._select_balanced(candidates)
```

### 6. 实施计划

#### 阶段1：基础成本跟踪（1周）
1. 创建CostTracker核心类
2. 实现SQLite存储后端
3. 修改OpenCode包装器集成
4. 基础命令行报告

#### 阶段2：高级功能（1周）
1. 添加估算策略（当无准确tokens时）
2. 实现聚合分析功能
3. 创建可视化报告
4. 集成到金融监控器

#### 阶段3：优化引擎（2周）
1. 实现任务迁移分析
2. 开发动态负载均衡
3. 创建Web仪表板（可选）
4. 自动化优化建议

### 7. 技术栈
- **核心语言**：Python 3.11+
- **存储**：SQLite（轻量），可选PostgreSQL（生产）
- **数据分析**：pandas（可选，用于复杂分析）
- **可视化**：rich（命令行），Plotly（Web界面）
- **API**：FastAPI/Flask（Web仪表板）

### 8. 成功指标
1. **成本可见性**：100%的API请求成本可追踪
2. **节省量化**：准确计算DeepSeek迁移带来的节省
3. **决策支持**：提供数据驱动的优化建议
4. **自动化程度**：80%的成本优化决策可自动化

## 下一步行动

### 立即开始（本周）
1. [ ] 创建`agent/core/cost_tracker.py`模块
2. [ ] 设计数据库schema并实现存储层
3. [ ] 修改OpenCode包装器集成点
4. [ ] 创建基础报告生成器

### 后续优化
1. [ ] 实现provider替代脚本的tokens估算
2. [ ] 开发成本趋势分析
3. [ ] 集成动态负载均衡策略
4. [ ] 创建Web仪表板（可选）

## 风险与缓解

### 技术风险
| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Tokens获取不准确 | 成本估算误差 | 多层fallback：API响应 → 估算算法 → 默认值 |
| 性能开销 | API延迟增加 | 异步记录，批量写入，性能监控 |
| 数据丢失 | 历史成本数据不全 | 定期备份，数据验证，恢复机制 |

### 业务风险
| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 过度优化 | 质量下降 | A/B测试，质量监控，逐步迁移 |
| 供应商锁定 | 依赖单一provider | 多provider支持，定期评估 |
| 预算超支 | 意外成本 | 实时告警，用量限制，审批流程 |

---
*设计文档版本: 1.0*
*创建日期: 2026-04-16*
*基于审计报告第二阶段优化建议*