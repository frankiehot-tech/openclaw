#!/bin/bash

# Bug修复工作流：使用 DeepSeek Chat (V3) 快速定位和修复问题
# 使用方式：claude-fix [claude命令行参数]

echo "🔧 Bug修复工作流启动"
echo "🔍 使用 DeepSeek Chat (V3) 快速定位问题"
echo "💡 提示：适用于日常bug修复、问题排查"
echo ""

exec /Users/frankie/claude-code-setup/claude-dual-model.sh 1 "$@"