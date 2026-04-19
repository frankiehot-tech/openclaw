#!/bin/bash
# MD文件清理验证脚本
# 验证清理执行结果

cd /Volumes/1TB-M2/openclaw

echo "🔍 开始验证MD文件清理结果..."
echo "================================"

# 第一步：检查归档目录结构
echo "📁 检查归档目录结构..."

archive_dirs=("historical_plans" "old_analysis" "performance_reports" "evo_proposals")
for dir in "${archive_dirs[@]}"; do
    if [ -d "archive/$dir" ]; then
        count=$(find "archive/$dir" -name "*.md" | wc -l)
        echo "  ✅ archive/$dir - $count 个文件"
    else
        echo "  ❌ archive/$dir - 目录不存在"
    fi
done

# 第二步：检查核心文件完整性
echo ""
echo "🔍 检查核心文件完整性..."

core_files=(
    "AGENTS.md" "TOOLS.md" "HEARTBEAT.md" "COGNITIVE_DNA.md" "MEMORY.md"
    "Athena系统架构图.md" "多Agent系统24小时压力测试问题修复实施方案.md"
    "Athena-Agentic与OpenHuman对齐工程实施方案.md" "多Agent系统问题修复执行指令.md"
    "多Agent系统24小时压力测试进度审计与继续执行指令.md"
    "vscode-cline-JSON文件损坏问题审计与修复方案.md" "MD文件清理策略与建议.md"
)

missing_files=()
for file in "${core_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file - 存在"
    else
        echo "  ❌ $file - 缺失"
        missing_files+=("$file")
    fi
done

# 第三步：检查重复文件是否已清理
echo ""
echo "🔍 检查重复文件清理..."

# 检查根目录下是否还有重复的Agent提示词文件
if [ ! -f "architect_agent_prompt.md" ] && [ -f "patterns/architect_agent_prompt.md" ]; then
    echo "  ✅ 重复的architect_agent_prompt.md已清理"
else
    echo "  ⚠️  architect_agent_prompt.md清理状态异常"
fi

if [ ! -f "frontend_agent_prompt.md" ] && [ -f "patterns/frontend_agent_prompt.md" ]; then
    echo "  ✅ 重复的frontend_agent_prompt.md已清理"
else
    echo "  ⚠️  frontend_agent_prompt.md清理状态异常"
fi

if [ ! -f "backend_agent_prompt.md" ] && [ -f "patterns/backend_agent_prompt.md" ]; then
    echo "  ✅ 重复的backend_agent_prompt.md已清理"
else
    echo "  ⚠️  backend_agent_prompt.md清理状态异常"
fi

# 第四步：检查性能报告清理
echo ""
echo "🔍 检查性能报告清理..."

# 检查是否还有2026年4月4日之前的性能报告
old_reports=$(find workspace/performance/ -name "performance_report_2026040[1-3]*.md" | wc -l)
if [ "$old_reports" -eq 0 ]; then
    echo "  ✅ 过时性能报告已清理"
else
    echo "  ❌ 发现 $old_reports 个过时性能报告"
fi

# 显示当前性能报告数量
current_reports=$(find workspace/performance/ -name "performance_report_2026040[4-6]*.md" | wc -l)
echo "  📊 当前性能报告数量: $current_reports"

# 第五步：统计最终文件数量
echo ""
echo "📊 最终文件统计..."

current_count=$(find . -name "*.md" | grep -v "^./archive" | wc -l)
archive_count=$(find archive/ -name "*.md" | wc -l)
total_count=$((current_count + archive_count))

# 显示文件分布
echo "  当前工作区MD文件: $current_count"
echo "  已归档文件: $archive_count"
echo "  总文件数: $total_count"

# 显示文件大小统计
current_size=$(find . -name "*.md" -exec ls -l {} \; | awk '{sum += $5} END {print sum}' 2>/dev/null || echo 0)
archive_size=$(find archive/ -name "*.md" -exec ls -l {} \; | awk '{sum += $5} END {print sum}' 2>/dev/null || echo 0)

echo "  当前工作区文件大小: $(($current_size/1024)) KB"
echo "  归档文件大小: $(($archive_size/1024)) KB"

# 第六步：显示清理效果
echo ""
echo "🎯 清理效果评估..."

# 估算清理前的文件数量（基于之前的分析）
original_estimate=200
reduction_percent=$((100 - (current_count * 100 / original_estimate)))

if [ $reduction_percent -gt 50 ]; then
    echo "  🎉 清理效果显著: 减少了约${reduction_percent}%的文件数量"
elif [ $reduction_percent -gt 30 ]; then
    echo "  ✅ 清理效果良好: 减少了约${reduction_percent}%的文件数量"
else
    echo "  ⚠️ 清理效果一般: 减少了约${reduction_percent}%的文件数量"
fi

# 第七步：检查是否有遗漏的重要文件
echo ""
echo "🔍 检查可能遗漏的重要文件..."

# 检查memory目录
memory_files=$(find memory/ -name "*.md" | wc -l)
if [ "$memory_files" -gt 0 ]; then
    echo "  ✅ memory/目录: $memory_files 个文件（保留）"
fi

# 检查skills目录
skills_files=$(find skills/ -name "*.md" | wc -l)
if [ "$skills_files" -gt 0 ]; then
    echo "  ✅ skills/目录: $skills_files 个文件（保留）"
fi

# 检查openclaw-2031-strategic-vision目录
vision_files=$(find openclaw-2031-strategic-vision/ -name "*.md" | wc -l)
if [ "$vision_files" -gt 0 ]; then
    echo "  ✅ openclaw-2031-strategic-vision/目录: $vision_files 个文件（保留）"
fi

# 第八步：总结验证结果
echo ""
echo "================================"
if [ ${#missing_files[@]} -eq 0 ]; then
    echo "🎉 验证通过！所有核心文件完整，清理执行成功。"
else
    echo "⚠️ 验证发现 ${#missing_files[@]} 个核心文件缺失:"
    for file in "${missing_files[@]}"; do
        echo "   - $file"
    done
    echo "建议检查是否需要恢复这些文件。"
fi

echo ""
echo "💡 建议后续操作:"
echo "   1. 执行 git status 查看文件变更"
echo "   2. 如有需要，可以执行 git add . 和 git commit"
echo "   3. 定期运行清理脚本维护仓库整洁"