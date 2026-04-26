#!/bin/bash
# DashScope 适配器重启脚本
echo "🔄 重启 DashScope 适配器..."
lsof -ti:8080 | xargs kill 2>/dev/null
sleep 1
cd /Users/frankie/claude-code-setup
nohup python3 dashscope-adapter.py > /tmp/dashscope-adapter-v2.log 2>&1 &
sleep 3
echo "✅ 适配器已重启"
curl -s http://localhost:8080/health | python3 -m json.tool