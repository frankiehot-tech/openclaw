# OpenClaw 仓库 MD 文件清理策略与建议

## 📊 文件分析结果

### **总体情况**
- **总MD文件数**: 超过200个（搜索结果达到限制）
- **主要问题**: 大量过时、重复、临时文件堆积
- **清理潜力**: 约60-70%的文件可以安全删除或归档

## 🎯 文件分类与清理建议

### **第一类：必须保留的核心文件（保留）**

#### **系统核心文档**
| 文件路径 | 重要性 | 理由 |
|----------|--------|------|
| `AGENTS.md` | 🔴 关键 | 系统核心配置，Agent定义 |
| `TOOLS.md` | 🔴 关键 | 工具配置和技能定义 |
| `HEARTBEAT.md` | 🔴 关键 | 系统心跳和监控配置 |
| `COGNITIVE_DNA.md` | 🔴 关键 | 系统认知DNA定义 |
| `MEMORY.md` | 🔴 关键 | 长期记忆存储 |

#### **战略规划文档**
| 文件路径 | 重要性 | 理由 |
|----------|--------|------|
| `openclaw-2031-strategic-vision/` 下所有文件 | 🟡 重要 | 长期战略规划 |
| `碳硅基共生-从自动化到融合的范式跃迁.md` | 🟡 重要 | 核心哲学文档 |

#### **当前项目文档**
| 文件路径 | 重要性 | 理由 |
|----------|--------|------|
| `Athena系统架构图.md` | 🔴 关键 | 当前架构设计 |
| `多Agent系统24小时压力测试问题修复实施方案.md` | 🔴 关键 | 正在进行的重要项目 |
| `Athena-Agentic与OpenHuman对齐工程实施方案.md` | 🔴 关键 | 重要集成项目 |

### **第二类：可以归档的历史文件（移动到archive/）**

#### **历史实施计划**
```bash
# 需要归档的文件
mv "Athena_v1.1_第3周多轮重复执行计划与样本统计口径.md" archive/
mv "Athena_v1.1_第2周收口检查项与进入第3周的入口条件.md" archive/
mv "Athena_v1.1_首轮回归违规样本判定与处置规则.md" archive/
```

#### **历史分析报告**
```bash
# 归档历史分析
mv "athena_openhuman_research_analysis.md" archive/
mv "claude_code_research_phase2.md" archive/
mv "github_openspace_integration_analysis.md" archive/
```

### **第三类：可以安全删除的临时文件（删除）**

#### **重复的Agent提示词文件**
```bash
# 删除重复文件（保留patterns/目录下的版本）
rm "architect_agent_prompt.md"
rm "frontend_agent_prompt.md"  
rm "backend_agent_prompt.md"
# 保留：patterns/目录下的对应文件
```

#### **过时的性能报告**
```bash
# 删除2026年4月4日之前的性能报告（保留最近3天）
find workspace/performance/ -name "performance_report_2026040[1-3]*.md" -delete
# 保留：2026-04-04及之后的报告
```

#### **测试和实验文件**
```bash
# 删除测试文件
rm -rf "EVO/proposals/TEST*.md"
rm "EVO/proposals/GENE*.md"
rm "EVO/REVIEW_NEEDED.md"
```

#### **过时的实施计划**
```bash
# 删除已被新版本替代的计划
rm "codex_opencode_tuning_plan.md"
rm "athena_openhuman_inspector_red_tuning_plan.md"
rm "agent_system_interface_analysis.md"
```

## 🔧 清理执行指令

### **第一步：创建归档目录**
```bash
cd /Volumes/1TB-M2/openclaw
mkdir -p archive/historical_plans
mkdir -p archive/old_analysis
mkdir -p archive/performance_reports
```

### **第二步：执行安全清理（保留核心文件）**

```bash
#!/bin/bash
# MD文件安全清理脚本

cd /Volumes/1TB-M2/openclaw

echo "📋 开始MD文件清理..."

# 1. 归档历史实施计划
echo "📦 归档历史实施计划..."
mv "Athena_v1.1_第3周多轮重复执行计划与样本统计口径.md" archive/historical_plans/ 2>/dev/null || echo "文件不存在或已移动"
mv "Athena_v1.1_第2周收口检查项与进入第3周的入口条件.md" archive/historical_plans/ 2>/dev/null
mv "Athena_v1.1_首轮回归违规样本判定与处置规则.md" archive/historical_plans/ 2>/dev/null

# 2. 归档历史分析报告
echo "📦 归档历史分析报告..."
mv "athena_openhuman_research_analysis.md" archive/old_analysis/ 2>/dev/null
mv "claude_code_research_phase2.md" archive/old_analysis/ 2>/dev/null
mv "github_openspace_integration_analysis.md" archive/old_analysis/ 2>/dev/null

# 3. 删除重复的Agent提示词文件
echo "🗑️ 删除重复文件..."
if [ -f "patterns/architect_agent_prompt.md" ] && [ -f "architect_agent_prompt.md" ]; then
    rm "architect_agent_prompt.md"
    echo "✅ 删除重复的architect_agent_prompt.md"
fi

if [ -f "patterns/frontend_agent_prompt.md" ] && [ -f "frontend_agent_prompt.md" ]; then
    rm "frontend_agent_prompt.md"
    echo "✅ 删除重复的frontend_agent_prompt.md"
fi

if [ -f "patterns/backend_agent_prompt.md" ] && [ -f "backend_agent_prompt.md" ]; then
    rm "backend_agent_prompt.md"
    echo "✅ 删除重复的backend_agent_prompt.md"
fi

# 4. 清理过时的性能报告（保留最近3天）
echo "🗑️ 清理过时性能报告..."
find workspace/performance/ -name "performance_report_2026040[1-3]*.md" -delete 2>/dev/null
find workspace/performance/ -name "performance_report_202603*.md" -delete 2>/dev/null

# 5. 删除测试文件
echo "🗑️ 删除测试文件..."
rm -f "EVO/proposals/TEST*.md" 2>/dev/null
rm -f "EVO/proposals/GENE*.md" 2>/dev/null
rm -f "EVO/REVIEW_NEEDED.md" 2>/dev/null

# 6. 删除过时的实施计划
echo "🗑️ 删除过时实施计划..."
rm -f "codex_opencode_tuning_plan.md" 2>/dev/null
rm -f "athena_openhuman_inspector_red_tuning_plan.md" 2>/dev/null
rm -f "agent_system_interface_analysis.md" 2>/dev/null

echo "📊 清理完成统计:"
find . -name "*.md" | wc -l | xargs echo "当前MD文件总数:"
find archive/ -name "*.md" | wc -l | xargs echo "已归档文件数:"
```

### **第三步：验证清理结果**

```bash
#!/bin/bash
# 验证清理结果

cd /Volumes/1TB-M2/openclaw

echo "🔍 验证清理结果..."

# 检查核心文件是否存在
core_files=("AGENTS.md" "TOOLS.md" "HEARTBEAT.md" "COGNITIVE_DNA.md" "MEMORY.md")
for file in "${core_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file - 存在"
    else
        echo "❌ $file - 缺失"
    fi
done

# 检查重复文件是否已清理
if [ ! -f "architect_agent_prompt.md" ] && [ -f "patterns/architect_agent_prompt.md" ]; then
    echo "✅ 重复的Agent提示词文件已清理"
fi

# 检查归档目录
if [ -d "archive" ]; then
    echo "✅ 归档目录已创建"
    find archive/ -name "*.md" | head -5 | xargs echo "归档文件示例:"
fi

# 统计最终文件数
current_count=$(find . -name "*.md" | wc -l)
archive_count=$(find archive/ -name "*.md" | wc -l)

echo "📈 最终统计:"
echo "  当前工作区MD文件: $current_count"
echo "  已归档文件: $archive_count"
echo "  总文件数: $((current_count + archive_count))"
```

## 📈 清理效益分析

### **空间节省**
- **预计减少**: 60-70%的MD文件数量
- **文件数量**: 从200+减少到60-80个
- **可读性提升**: 核心文件更易查找和维护

### **维护效率提升**
1. **减少混淆**: 消除重复和过时文件
2. **明确版本**: 只保留最新有效版本
3. **快速定位**: 核心文档一目了然

### **风险管理**
- **安全归档**: 重要历史文件妥善保存
- **可恢复性**: 归档文件可随时查阅
- **版本控制**: 清晰的版本演进路径

## 🚀 推荐执行策略

### **立即执行（今日）**
1. **执行安全清理脚本** - 处理明显重复和过时文件
2. **验证核心文件完整性** - 确保关键文档存在
3. **创建归档结构** - 建立规范的归档体系

### **后续优化（本周内）**
1. **定期清理机制** - 设置每月自动清理
2. **文档生命周期管理** - 定义文档保留策略
3. **版本管理规范** - 建立文档版本控制

### **长期维护**
1. **文档分类标准** - 明确各类文档的保留期限
2. **自动化工具** - 开发文档生命周期管理工具
3. **团队规范** - 建立文档创建和清理规范

## 💡 重要提醒

### **不要删除的文件**
- 任何以 `.md` 结尾但可能是系统配置的文件
- `memory/` 目录下的日记文件（有历史价值）
- `skills/` 目录下的技能定义文件
- 任何您不确定用途的文件

### **备份原则**
- 执行清理前确保有git备份
- 重要文件先归档再删除
- 保留删除文件的记录

---

**清理建议版本**: v1.0  
**创建时间**: 2026-04-06  
**建议执行**: 立即开始安全清理阶段