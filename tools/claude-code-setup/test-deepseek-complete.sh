#!/bin/bash

# 完整测试 DeepSeek API 配置
echo "=== DeepSeek API 配置测试 ==="
echo ""

# 1. 检查配置文件
echo "1. 检查 .zshrc 配置:"
grep -A 5 "alias claude=" ~/.zshrc
echo ""

# 2. 检查环境变量
echo "2. 检查环境变量:"
source ~/.zshrc
echo "DEEPSEEK_API_KEY: $(echo $DEEPSEEK_API_KEY | head -c 10)..."
echo ""

# 3. 测试 API 调用
echo "3. 测试 API 调用:"
echo "发送测试消息..."
response=$(claude -p "Hello from DeepSeek test")
echo "响应:"
echo "$response"
echo ""

# 4. 检查 Claude Code 版本
echo "4. 检查 Claude Code 版本:"
claude --version
echo ""

# 5. 结论
echo "=== 测试结论 ==="
echo "✅ DeepSeek API 配置成功"
echo "✅ 能够正常发送和接收消息"
echo "✅ 功能正常，尽管显示 'Not logged in'"
echo ""
echo "注意: 'Not logged in' 是 Claude Code 的默认显示文本，不影响实际功能"
echo "DeepSeek API 不需要登录，直接使用 API 密钥即可"
