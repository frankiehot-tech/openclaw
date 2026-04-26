#!/bin/bash

# 新功能开发工作流：先用 DeepSeek R1 进行架构设计
# 使用方式：claude-dev [claude命令行参数]

echo "🚀 新功能开发工作流启动"
echo "📐 第一阶段：使用 DeepSeek Reasoner (R1) 进行架构设计"
echo "💡 提示：完成设计后，可切换至 DeepSeek Chat (V3) 进行快速编码"
echo ""

exec /Users/frankie/claude-code-setup/claude-dual-model.sh 2 "$@"