#!/bin/bash
# audit_ai_traces.sh - AI工具痕迹诊断脚本

echo "🔍 扫描 AI工具痕迹..."
echo ""

# 1. 目录级痕迹
echo "📁 可疑目录："
find . -type d -iname "*claude*" 2>/dev/null | grep -v node_modules | grep -v ".git"

# 2. 文件级痕迹
echo ""
echo "📄 可疑文件："
find . -type f \( -iname "*claude*" -o -iname "*anthropic*" \) 2>/dev/null | grep -v node_modules | grep -v ".git"

# 3. Git 提交历史
echo ""
echo "📜 提交记录中的关键词："
git log --all --oneline --grep="[Cc]laude\|[Aa]nthropic" 2>/dev/null | head -20

# 4. 代码内容扫描
echo ""
echo "📝 代码文件中的标记："
grep -ri -E "(claude\s*code|generated\s*by\s*claude|anthropic\s*api|CLAUDE_|ANTHROPIC_)" \
    --include="*.py" --include="*.js" --include="*.ts" --include="*.md" \
    --include="*.json" --include="*.yaml" --include="*.yml" --include="*.sh" \
    --include="*.txt" --include="*.ini" --include="*.toml" \
    . 2>/dev/null | grep -v node_modules | grep -v ".git" | head -30

# 5. 环境变量文件
echo ""
echo "🔐 环境变量检查："
grep -ri "ANTHROPIC\|CLAUDE" .env* 2>/dev/null || echo "  无.env文件"

# 6. 依赖文件
echo ""
echo "📦 依赖检查："
grep -i "anthropic\|claude" package.json requirements.txt 2>/dev/null || echo "  无相关依赖"

echo ""
echo "✅ 诊断完成。请根据上方结果执行对应清理步骤。"