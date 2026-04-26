#!/bin/bash

# 测试环境变量传递的脚本

echo "🧪 测试环境变量传递..."
echo "========================"

# 测试1: 检查当前环境变量
echo "测试1: 检查当前环境变量"
echo "GITHUB_TOKEN: ${GITHUB_TOKEN:-未设置}"
echo "GITHUB_USERNAME: ${GITHUB_USERNAME:-未设置}"
echo "DASHSCOPE_API_KEY: ${DASHSCOPE_API_KEY:-未设置}"

echo ""
echo "测试2: 运行 init-claude-env.sh 设置环境变量..."
# 在当前shell进程中设置环境变量
source <(./init-claude-env.sh --export)

echo ""
echo "测试3: 再次检查环境变量"
echo "GITHUB_TOKEN: ${GITHUB_TOKEN:0:10}..."
echo "GITHUB_USERNAME: $GITHUB_USERNAME"
echo "DASHSCOPE_API_KEY: ${DASHSCOPE_API_KEY:0:10}..."

echo ""
echo "测试4: 运行 GitHub 诊断工具（子进程）..."
# 注意：这里会在新的子进程中运行，所以环境变量应该会传递
./github-tools/github-diagnose.sh 2>&1 | grep -A5 "环境变量检查"