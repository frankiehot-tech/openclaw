#!/bin/bash
# Claude Code 配置修复脚本
# 生成时间：2026-04-23
# 用法：source zshrc-fixes.sh

echo "🔧 Claude Code 配置修复工具"
echo "=============================="

# 修复 1: claude-max 别名指向不存在的脚本
# 原配置：alias claude-max='/Users/frankie/claude-code-setup/claude-qwen-alt.sh -m qwen3.6-plus'
# 问题：claude-qwen-alt.sh 不存在
# 修复：改为使用 claude-dual-model.sh 5（百炼默认模式，等同于 qwen3.6-plus）
echo ""
echo "1️⃣ 修复 claude-max 别名"
echo "   原配置指向不存在的 claude-qwen-alt.sh"
echo "   建议替换为："
echo '   alias claude-max="/Users/frankie/claude-code-setup/claude-dual-model.sh 5"'
echo "   （使用 claude-dual-model.sh 的百炼默认模式）"

# 修复 2: claude-pro 别名指向不存在的脚本
echo ""
echo "2️⃣ 修复 claude-pro 别名"
echo "   原配置：alias claude-pro=\"/Users/frankie/claude-pro.sh\""
echo "   问题：claude-pro.sh 不存在"
echo "   建议：注释或删除此行"

# 修复 3: BAILIAN_API_KEY 为空
echo ""
echo "3️⃣ 修复 BAILIAN_API_KEY"
echo "   当前：export BAILIAN_API_KEY=\"\""
echo "   说明：系统实际使用 DASHSCOPE_API_KEY（从 Keychain 加载）"
echo "   建议替换为："
echo '   export BAILIAN_API_KEY="${DASHSCOPE_API_KEY:-}"  # 从 DASHSCOPE_API_KEY 继承'

# 修复 4: claude-small 提示信息优化
echo ""
echo "4️⃣ 优化 claude-small 提示"
echo "   当前提示：🚀 Gemma 4 E4B (128K ctx)"
echo "   建议添加 [本地 Ollama] 标识，避免误解为云端模型"
echo '   建议替换为：echo "🚀 [本地 Ollama] Gemma 4 E4B (128K ctx)"'

# 修复 5: Secret 加载路径
echo ""
echo "5️⃣ 修复 Secret 加载路径"
echo "   当前路径：~/.config/secret-env/load-keychain-secrets.sh"
echo "   状态：文件不存在"
echo "   现有文件：~/claude-code-setup/load-local-secrets.sh"
echo "   建议：创建软链接或修正路径"

echo ""
echo "=============================="
echo "📋 手动修复步骤："
echo ""
echo "请编辑 ~/.zshrc 文件，进行以下修改："
echo ""
echo "【第148行】注释 claude-pro："
echo "   # alias claude-pro=\"/Users/frankie/claude-pro.sh\""
echo ""
echo "【第170行】修复 claude-max："
echo '   alias claude-max="/Users/frankie/claude-code-setup/claude-dual-model.sh 5"'
echo ""
echo "【第182行】修复 BAILIAN_API_KEY："
echo '   export BAILIAN_API_KEY="${DASHSCOPE_API_KEY:-}"'
echo ""
echo "【第227行】优化 claude-small 提示："
echo '   echo "🚀 [本地 Ollama] Gemma 4 E4B (128K ctx)"'
echo ""
echo "【第115-117行】修复 secret 加载路径："
echo '   if [ -f "$HOME/claude-code-setup/load-local-secrets.sh" ]; then'
echo '     source "$HOME/claude-code-setup/load-local-secrets.sh"'
echo '   fi'
echo ""
