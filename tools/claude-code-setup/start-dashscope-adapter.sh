#!/bin/bash
# 启动 DashScope 适配器 - 确保 API 密钥正确加载

# 从 Keychain 读取密钥
DASHSCOPE_API_KEY=$(security find-generic-password -w -a "${USER}" -s "env/DASHSCOPE_API_KEY" 2>/dev/null)

if [ -z "$DASHSCOPE_API_KEY" ]; then
    echo "❌ 无法从 Keychain 读取 DASHSCOPE_API_KEY"
    exit 1
fi

echo "🔑 API 密钥已加载: ${DASHSCOPE_API_KEY:0:10}..."

# 停止旧进程
pkill -f "dashscope-adapter.py" 2>/dev/null
sleep 1

# 启动新进程
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

DASHSCOPE_API_KEY="$DASHSCOPE_API_KEY" nohup python3 dashscope-adapter.py > /tmp/dashscope-adapter.log 2>&1 &
ADAPTER_PID=$!

sleep 2

# 验证启动
if curl -s http://127.0.0.1:8080/v1/health > /dev/null 2>&1; then
    echo "✅ 适配器已启动 (PID: $ADAPTER_PID)"
    echo "   监听: http://127.0.0.1:8080"
else
    echo "❌ 适配器启动失败"
    cat /tmp/dashscope-adapter.log
    exit 1
fi