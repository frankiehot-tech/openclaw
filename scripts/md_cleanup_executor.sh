#!/bin/bash
# MD文件清理执行脚本
# 基于《MD文件清理策略与建议.md》执行安全清理

cd /Volumes/1TB-M2/openclaw

echo "🚀 开始执行MD文件清理..."
echo "================================"

# 第一步：创建归档目录结构
echo "📁 创建归档目录结构..."
mkdir -p archive/historical_plans
mkdir -p archive/old_analysis
mkdir -p archive/performance_reports
mkdir -p archive/evo_proposals

echo "✅ 归档目录创建完成"

# 第二步：归档历史实施计划
echo "📦 归档历史实施计划..."

historical_plans=(
    "Athena_v1.1_第3周多轮重复执行计划与样本统计口径.md"
    "Athena_v1.1_第2周收口检查项与进入第3周的入口条件.md"
    "Athena_v1.1_首轮回归违规样本判定与处置规则.md"
    "Athena_v1.1_首轮回归输出物与命名规范.md"
    "Athena_v1.1_任务级执行记录映射表.md"
    "Athena_v1.1_回归测试集（首版）.md"
    "Athena_v1.1_第1周完成情况检查表_第2周入口条件确认单.md"
    "Athena_v1.1_Week1_Baseline_Package.md"
)

for plan in "${historical_plans[@]}"; do
    if [ -f "$plan" ]; then
        mv "$plan" archive/historical_plans/
        echo "  ✅ 归档: $plan"
    else
        echo "  ℹ️  不存在: $plan"
    fi
done

# 第三步：归档历史分析报告
echo "📦 归档历史分析报告..."

old_analysis=(
    "athena_openhuman_research_analysis.md"
    "claude_code_research_phase2.md"
    "github_openspace_integration_analysis.md"
    "athena_autoresearch_integration_analysis.md"
    "athena_openhuman_competitive_mapping_prd.md"
    "athena_openhuman_business_model_alignment.md"
    "athena_ip_marketing_prd.md"
    "athena_openhuman_optimized_architecture_prd.md"
    "Athena架构优化增量工程化研究报告.md"
)

for analysis in "${old_analysis[@]}"; do
    if [ -f "$analysis" ]; then
        mv "$analysis" archive/old_analysis/
        echo "  ✅ 归档: $analysis"
    else
        echo "  ℹ️  不存在: $analysis"
    fi
done

# 第四步：归档EVO提案文件
echo "📦 归档EVO提案文件..."

if [ -d "EVO/proposals" ]; then
    mv EVO/proposals/*.md archive/evo_proposals/ 2>/dev/null || echo "  ℹ️  EVO提案目录为空"
    echo "  ✅ EVO提案文件已归档"
fi

# 第五步：删除重复的Agent提示词文件
echo "🗑️ 删除重复的Agent提示词文件..."

# 检查并删除根目录下与patterns/目录重复的文件
if [ -f "patterns/architect_agent_prompt.md" ] && [ -f "architect_agent_prompt.md" ]; then
    rm "architect_agent_prompt.md"
    echo "  ✅ 删除重复: architect_agent_prompt.md"
fi

if [ -f "patterns/frontend_agent_prompt.md" ] && [ -f "frontend_agent_prompt.md" ]; then
    rm "frontend_agent_prompt.md"
    echo "  ✅ 删除重复: frontend_agent_prompt.md"
fi

if [ -f "patterns/backend_agent_prompt.md" ] && [ -f "backend_agent_prompt.md" ]; then
    rm "backend_agent_prompt.md"
    echo "  ✅ 删除重复: backend_agent_prompt.md"
fi

# 第六步：清理过时的性能报告（保留最近3天）
echo "🗑️ 清理过时性能报告..."

# 删除2026年4月4日之前的性能报告
find workspace/performance/ -name "performance_report_2026040[1-3]*.md" -delete 2>/dev/null
find workspace/performance/ -name "performance_report_202603*.md" -delete 2>/dev/null
find workspace/performance/ -name "performance_report_202602*.md" -delete 2>/dev/null

echo "  ✅ 过时性能报告已清理"

# 第七步：删除过时的实施计划
echo "🗑️ 删除过时实施计划..."

outdated_plans=(
    "codex_opencode_tuning_plan.md"
    "athena_openhuman_inspector_red_tuning_plan.md"
    "agent_system_interface_analysis.md"
    "openhuman_stitch_integration_implementation_plan.md"
    "openhuman_stitch_prompts.md"
    "mvp_test_env_summary.md"
    "google_stitch_vibe_design_research_report.md"
    "automaton_athena_integration_mvp_plan.md"
    "openclaw_automaton_compliance_athena_incremental_value_analysis.md"
    "phase2_analysis_output.md"
    "athena_agent_optimization_priority_plan.md"
    "openclaw_4.2_athena_upgrade_risk_analysis.md"
)

for plan in "${outdated_plans[@]}"; do
    if [ -f "$plan" ]; then
        rm "$plan"
        echo "  ✅ 删除: $plan"
    else
        echo "  ℹ️  不存在: $plan"
    fi
done

echo ""
echo "================================"
echo "🎉 MD文件清理执行完成！"
echo "================================"

# 显示清理统计
echo "📊 清理统计:"
current_count=$(find . -name "*.md" | grep -v "^./archive" | wc -l)
archive_count=$(find archive/ -name "*.md" | wc -l)

echo "  当前工作区MD文件: $current_count"
echo "  已归档文件: $archive_count"
echo "  总文件数: $((current_count + archive_count))"

# 检查核心文件完整性
echo ""
echo "🔍 核心文件完整性检查:"
core_files=("AGENTS.md" "TOOLS.md" "HEARTBEAT.md" "COGNITIVE_DNA.md" "MEMORY.md")
for file in "${core_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file - 存在"
    else
        echo "  ❌ $file - 缺失"
    fi
done

echo ""
echo "💡 清理完成！建议执行验证脚本确认结果。"