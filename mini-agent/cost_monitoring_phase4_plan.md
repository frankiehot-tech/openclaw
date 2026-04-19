# 成本监控系统阶段4：决策和执行计划

## 基于实验结果制定全面迁移决策

**计划版本**: 1.0  
**创建日期**: 2026-04-17  
**基于数据**: 成本优化分析报告 (2026-04-17)  
**相关文档**: `cost_monitoring_design.md` (阶段1-3设计)

## 📊 当前状态分析（基于成本分析报告）

### ✅ 已完成的工作（阶段1-3）
1. **完整成本监控系统部署**
   - CostTracker核心类 ✅
   - SQLite存储后端 ✅
   - OpenCode包装器集成 ✅
   - 金融监控器对接 ✅

2. **实验框架部署和验证**
   - A/B测试实验框架 ✅
   - Provider动态路由 ✅
   - 请求一致性分配 ✅
   - 成本数据收集 ✅

3. **成本分析能力**
   - Provider成本对比 ✅
   - 任务类型分析 ✅
   - 实验效果评估 ✅
   - 优化建议生成 ✅

### 📈 实验数据分析结果

**实验**: `coding_plan_deepseek_coder_ab`  
**目标**: 对比DeepSeek Coder与DashScope的成本和质量差异

| 指标 | 控制组 (DashScope) | 实验组 (DeepSeek Coder) | 改善效果 |
|------|-------------------|----------------------|----------|
| 请求数 | 5 | 4 | 50/50分配接近预期 |
| 平均成本 | ¥0.000416 | ¥0.000269 | **-35.3%** |
| 平均输入tokens | 2.0 | 4.0 | +100% |
| 平均输出tokens | 50.0 | 132.5 | +165% |
| 总成本 | ¥0.002080 | ¥0.001076 | **-48.3%** |

**关键发现**:
1. **成本节省显著**: DeepSeek Coder相比DashScope节省35.3%平均成本
2. **输出更详细**: DeepSeek Coder平均输出tokens更多(132.5 vs 50.0)
3. **样本不足**: 仅9个实验样本，需要100+样本获得统计显著性

### 💰 整体成本节省情况

| 指标 | 数值 | 说明 |
|------|------|------|
| 总请求数 | 34 | 全部记录 |
| DashScope占比 | 57.3% | 仍为主要成本来源 |
| DeepSeek占比 | 42.7% | 已迁移部分 |
| 实际节省 | 25.36% | ¥0.003063 |
| 理论最大节省 | 87.5% | ¥0.044408 |

**coding_plan任务状态**:
- 当前DashScope占比: 62.6% (¥0.012008)
- 当前DeepSeek占比: 37.4% (¥0.007171)
- 完全迁移潜在节省: ¥0.010507

## 🎯 阶段4目标

基于实验数据制定科学的迁移决策，最大化成本节省同时保证代码质量。

### 核心目标
1. **数据驱动决策**: 收集足够实验样本(100+)，获得统计显著性
2. **质量评估体系**: 建立代码质量评分机制，验证DeepSeek Coder质量
3. **全面迁移执行**: 如果质量达标，全面迁移coding_plan任务到DeepSeek
4. **监控和优化**: 建立迁移后监控，持续优化成本-质量平衡

### 成功指标
1. **实验数据量**: ≥100个样本（每个分组50+）
2. **统计显著性**: p-value < 0.05（95%置信度）
3. **质量达标标准**: DeepSeek Coder质量评分 ≥ DashScope的90%
4. **成本节省目标**: 实际节省 ≥ 理论节省的80%（即70%+总节省）
5. **迁移完成度**: coding_plan任务中DeepSeek占比 ≥ 90%

## 📋 阶段4详细实施计划

### 阶段4A：扩大实验规模（2天）
**目标**: 收集100+实验样本，获得统计显著性数据

**任务**:
1. **增强实验日志记录** (`experiment_logger.py`)
   - 记录每次实验分配的详细上下文
   - 保存输入prompt和完整输出
   - 添加执行时间和质量评分

2. **自动化实验运行** (`experiment_runner.py`)
   - 创建代表性测试用例库（10个典型coding_plan任务）
   - 自动运行实验收集数据
   - 确保样本分布平衡

3. **数据验证和质量控制**
   - 验证每个样本的数据完整性
   - 检查异常值（极高/极低成本样本）
   - 确保分组分配的随机性

### 阶段4B：质量评估体系建立（3天）
**目标**: 建立客观的代码质量评估标准，对比DeepSeek和DashScope输出

**任务**:
1. **质量评分模型设计** (`quality_assessment.py`)
   - 代码正确性评分（通过测试用例）
   - 代码复杂度分析（圈复杂度、行数）
   - 代码风格检查（PEP8、最佳实践）
   - 可读性评估（注释、命名规范）

2. **测试用例库建设**
   - 创建10-20个代表性编程任务
   - 每个任务有明确的验收标准
   - 包含单元测试验证正确性

3. **评估自动化** (`quality_evaluator.py`)
   - 自动运行质量评估流程
   - 生成质量对比报告
   - 统计显著性检验

### 阶段4C：迁移决策制定（1天）
**目标**: 基于充分数据做出科学迁移决策

**任务**:
1. **统计分析报告** (`statistical_analysis.py`)
   - 计算成本节省的统计显著性
   - 分析质量差异的置信区间
   - 生成数据驱动决策报告

2. **决策框架设计** (`migration_decision_framework.py`)
   - 定义决策标准（成本阈值、质量阈值）
   - 风险评估（质量风险、成本风险）
   - 备选方案分析

3. **决策制定会议**
   - 准备决策材料
   - 分析各选项的利弊
   - 制定迁移时间表和回滚计划

### 阶段4D：全面迁移执行（2天）
**目标**: 安全、可控地全面迁移coding_plan任务到DeepSeek

**任务**:
1. **迁移计划制定** (`migration_plan.py`)
   - 分阶段迁移策略（25% → 50% → 75% → 100%）
   - 迁移时间表和检查点
   - 回滚机制设计

2. **配置更新** (`experiments.yaml`)
   - 修改实验配置：100%分配到DeepSeek Coder
   - 保留实验监控框架（用于质量跟踪）
   - 更新provider注册表默认配置

3. **监控和告警设置**
   - 迁移期间增强监控
   - 关键指标告警（错误率、质量下降、成本异常）
   - 每日迁移进展报告

### 阶段4E：迁移后优化和监控（持续）
**目标**: 确保迁移稳定，持续优化成本-质量平衡

**任务**:
1. **后迁移评估** (`post_migration_evaluation.py`)
   - 迁移后1周、1个月评估
   - 成本节省实际效果验证
   - 质量跟踪和用户反馈

2. **持续优化框架**
   - 动态provider选择算法（基于实时成本和质量）
   - 自适应预算分配
   - 自动化优化建议

3. **仪表板和报告增强**（可选）
   - 实时成本监控仪表板
   - 质量趋势可视化
   - 自动化报告生成

## 🔧 技术实现细节

### 1. 实验数据收集增强
```python
# experiment_logger.py
class ExperimentLogger:
    def log_experiment_result(self, assignment, request_context, response, 
                              execution_time, quality_score=None):
        """记录完整实验数据"""
        record = {
            'experiment_id': assignment.experiment_id,
            'group_name': assignment.group_name,
            'request_id': request_context['request_id'],
            'task_kind': request_context['task_kind'],
            'input_prompt': request_context.get('prompt', ''),
            'model_response': response,
            'execution_time': execution_time,
            'quality_score': quality_score,
            'cost_info': request_context.get('cost_info', {}),
            'metadata': assignment.metadata
        }
        self.storage.save(record)
```

### 2. 质量评估体系
```python
# quality_assessment.py
class CodeQualityAssessor:
    def assess_code_quality(self, code, test_cases=None):
        """评估代码质量"""
        scores = {
            'correctness': self._assess_correctness(code, test_cases),
            'complexity': self._assess_complexity(code),
            'style': self._assess_style(code),
            'readability': self._assess_readability(code),
            'maintainability': self._assess_maintainability(code)
        }
        overall_score = self._calculate_overall_score(scores)
        return {'overall': overall_score, 'breakdown': scores}
```

### 3. 统计分析
```python
# statistical_analysis.py
class ExperimentStatistician:
    def analyze_experiment_results(self, experiment_id):
        """分析实验结果统计显著性"""
        data = self._load_experiment_data(experiment_id)
        
        # 成本对比T检验
        control_costs = data[data['group'] == 'control']['cost']
        treatment_costs = data[data['group'] == 'treatment']['cost']
        t_stat, p_value = ttest_ind(control_costs, treatment_costs)
        
        # 效应量计算
        effect_size = self._calculate_effect_size(control_costs, treatment_costs)
        
        return {
            'sample_size': len(data),
            'control_mean': control_costs.mean(),
            'treatment_mean': treatment_costs.mean(),
            'cost_reduction_percent': (1 - treatment_costs.mean()/control_costs.mean()) * 100,
            't_statistic': t_stat,
            'p_value': p_value,
            'effect_size': effect_size,
            'statistical_significance': p_value < 0.05,
            'confidence_interval': self._calculate_ci(control_costs, treatment_costs)
        }
```

### 4. 迁移决策框架
```python
# migration_decision_framework.py
class MigrationDecisionMaker:
    def make_migration_decision(self, experiment_data, quality_data):
        """基于数据做出迁移决策"""
        # 成本节省分析
        cost_savings = self._analyze_cost_savings(experiment_data)
        
        # 质量对比分析
        quality_comparison = self._analyze_quality_comparison(quality_data)
        
        # 风险评估
        risks = self._assess_migration_risks(experiment_data, quality_data)
        
        # 决策逻辑
        decision = self._apply_decision_logic(cost_savings, quality_comparison, risks)
        
        return {
            'recommendation': decision['recommendation'],
            'confidence': decision['confidence'],
            'expected_savings': cost_savings['expected_savings'],
            'quality_impact': quality_comparison['impact'],
            'risks': risks,
            'mitigation_strategies': decision['mitigation_strategies']
        }
```

## 🧪 测试和验证计划

### 单元测试
- 实验日志记录功能测试
- 质量评估算法测试
- 统计分析计算验证
- 迁移决策逻辑测试

### 集成测试
- 端到端实验数据收集流程
- 质量评估集成测试
- 统计分析报告生成
- 决策框架集成测试

### 数据验证
- 实验数据完整性检查
- 质量评分一致性验证
- 统计计算准确性验证
- 迁移决策可重现性

## ⚠️ 风险和缓解措施

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 实验样本不足 | 决策缺乏统计显著性 | 自动化实验运行，目标100+样本 |
| 质量评估主观性 | 评估结果不可靠 | 多维度客观评估，测试用例验证 |
| 迁移后质量下降 | 用户体验变差 | 分阶段迁移，实时监控，快速回滚 |
| 成本估算误差 | 实际节省不如预期 | 持续监控真实成本，定期校准 |
| 供应商模型变化 | 价格或质量变化 | 持续监控provider变化，多provider备选 |

## 📅 实施时间表（总：8天）

### 第1周：数据收集和质量评估（5天）
- 周一-周二：阶段4A（扩大实验规模）
- 周三-周四：阶段4B（质量评估体系）
- 周五：阶段4B剩余任务

### 第2周：决策和执行（3天）
- 周一：阶段4C（迁移决策制定）
- 周二：阶段4D（全面迁移执行）
- 周三：阶段4D剩余任务和阶段4E启动

## 📁 关键文件路径

**新建文件（6个）**:
1. `/Volumes/1TB-M2/openclaw/mini-agent/agent/core/experiment_logger.py`
2. `/Volumes/1TB-M2/openclaw/mini-agent/agent/core/experiment_runner.py`
3. `/Volumes/1TB-M2/openclaw/mini-agent/agent/core/quality_assessment.py`
4. `/Volumes/1TB-M2/openclaw/mini-agent/agent/core/quality_evaluator.py`
5. `/Volumes/1TB-M2/openclaw/mini-agent/agent/core/statistical_analysis.py`
6. `/Volumes/1TB-M2/openclaw/mini-agent/agent/core/migration_decision_framework.py`

**修改文件（2个）**:
1. `/Volumes/1TB-M2/openclaw/mini-agent/config/experiments.yaml`（迁移时修改）
2. `/Volumes/1TB-M2/openclaw/mini-agent/agent/core/experiment_router.py`（增强日志）

## 🎯 交付成果

1. **实验数据分析报告**（≥100样本，统计显著性验证）
2. **质量对比评估报告**（客观质量评分对比）
3. **迁移决策建议报告**（数据驱动决策文档）
4. **迁移执行计划**（分阶段迁移时间表和检查点）
5. **迁移后监控体系**（成本和质量持续跟踪）

## 🔗 相关文档

- 原始设计: `cost_monitoring_design.md`
- 成本分析脚本: `/tmp/cost_optimization_analysis.py`
- 实验配置: `config/experiments.yaml`
- 成本跟踪数据库: `data/cost_tracking.db`

---

*计划审核人*: Claude (AI助手)  
*下一步行动*: 立即开始阶段4A实施，扩大实验规模到100+样本