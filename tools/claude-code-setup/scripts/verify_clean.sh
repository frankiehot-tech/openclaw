#!/bin/bash
# verify_clean.sh - 清理结果验证脚本

ERRORS=0

echo "🧹 验证清理结果..."

# 1. 目录检查（排除reference第三方）
if find . -type d -iname "*ai*" 2>/dev/null | grep -v node_modules | grep -v ".git" | grep -v "^./reference/" | grep -q .; then
    echo "❌ 失败: ai/ 或 .ai/ 目录仍存在"
    ERRORS=$((ERRORS + 1))
else
    echo "✅ 目录已清除"
fi

# 2. Git 历史检查
if git log --all --oneline --grep="[Cc]laude" 2>/dev/null | grep -q .; then
    echo "❌ 失败: Git 历史仍含 'Claude' 提交"
    ERRORS=$((ERRORS + 1))
else
    echo "✅ Git 历史已清理"
fi

# 3. 代码内容检查（排除reference第三方）
if grep -ri -E "(ai\s*code|generated\s*by\s*ai)" \
    --include="*.py" --include="*.js" --include="*.ts" --include="*.md" \
    --include="*.json" --include="*.yaml" --include="*.yml" --include="*.sh" \
    --include="*.txt" . 2>/dev/null | grep -v node_modules | grep -v ".git" | grep -v "^./reference/" | grep -q .; then
    echo "❌ 失败: 代码文件仍含标记"
    ERRORS=$((ERRORS + 1))
else
    echo "✅ 代码内容已清理"
fi

# 4. 环境变量检查
if grep -ri "ANTHROPIC\|AI" .env* 2>/dev/null | grep -q .; then
    echo "❌ 失败: 环境文件仍含敏感配置"
    ERRORS=$((ERRORS + 1))
else
    echo "✅ 环境变量已清理"
fi

# 5. .gitignore 检查
if ! grep -q "ai/" .gitignore 2>/dev/null; then
    echo "⚠️ 警告: .gitignore 未配置 ai/ 忽略规则"
else
    echo "✅ .gitignore 已配置"
fi

# 6. pre-commit 钩子检查
if [ ! -x ".git/hooks/pre-commit" ]; then
    echo "⚠️ 警告: pre-commit 钩子未激活"
else
    echo "✅ pre-commit 钩子已激活"
fi

if [ $ERRORS -eq 0 ]; then
    echo ""
    echo "🎉 验证通过！仓库已清零，可以安全推送到 GitHub。"
else
    echo ""
    echo "🚫 发现 $ERRORS 个问题，请重新清理。"
    exit 1
fi