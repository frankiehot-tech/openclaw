#!/bin/bash

# 中文项目工作流：使用 Qwen3.6-Plus 优化中文处理和代码生成
# 使用方式：claude-zh [claude-qwen-alt命令行参数]
#
# 注意：由于DashScope不提供LLM兼容模式，AI Assistant无法直接连接Qwen模型
# 此脚本使用OpenAI兼容API作为替代方案

echo "🇨🇳 中文项目工作流启动"
echo "📝 使用 Qwen3.6-Plus (阿里云) 进行中文优化"
echo "💡 提示：适用于中文文档、中文代码注释、中文业务逻辑"
echo "🔧 使用OpenAI兼容API作为替代方案（AI Assistant不兼容DashScope）"
echo ""

exec /Users/frankie/claude-code-setup/claude-qwen-alt.sh "$@"