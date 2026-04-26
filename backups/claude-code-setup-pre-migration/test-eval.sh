#!/bin/bash

echo "测试1: 运行 eval \$(./init-claude-env.sh --export)"
eval "$(./init-claude-env.sh --export)"

echo ""
echo "测试2: 检查环境变量"
echo "GITHUB_TOKEN: ${GITHUB_TOKEN:0:10}..."
echo "GITHUB_USERNAME: $GITHUB_USERNAME"
echo "GITHUB_EMAIL: $GITHUB_EMAIL"

echo ""
echo "测试3: 运行诊断工具片段"
./github-tools/github-diagnose.sh 2>&1 | grep -B2 -A3 "环境变量检查"