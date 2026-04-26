#!/bin/bash
# 方案 C 安装脚本：百炼 PRO + 自定义 MCP 服务器
# 用法: bash setup-mcp-tools.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MCP_SERVER="${SCRIPT_DIR}/stage1/mcp-servers/claude-tools-server.py"
AI_SETTINGS="$HOME/.ai-assistant/settings.json"

echo "=========================================="
echo "  百炼 PRO + MCP 服务器安装"
echo "=========================================="
echo ""

# 1. 检查 Python3
echo "📦 检查 Python3..."
if ! command -v python3 &>/dev/null; then
    echo "❌ 未找到 Python3"
    exit 1
fi
echo "   ✅ Python3: $(python3 --version)"

# 2. 检查 MCP 模块
echo "📦 检查 MCP 模块..."
if python3 -c "from mcp.server import Server" 2>/dev/null; then
    echo "   ✅ MCP 模块已安装"
else
    echo "   ⚠️  正在安装 MCP 模块..."
    pip3 install --user --break-system-packages "mcp>=1.0.0" 2>/dev/null || \
    pip3 install --user "mcp>=1.0.0" 2>/dev/null || \
    { echo "❌ MCP 安装失败，请手动安装"; exit 1; }
    echo "   ✅ MCP 模块已安装"
fi

# 3. 检查 MCP 服务器脚本
echo "📦 检查 MCP 服务器..."
if [ -f "$MCP_SERVER" ]; then
    echo "   ✅ MCP 服务器脚本: $MCP_SERVER"
else
    echo "   ❌ MCP 服务器脚本不存在: $MCP_SERVER"
    exit 1
fi

# 4. 测试 MCP 服务器
echo "📦 测试 MCP 服务器..."
if python3 -c "
import sys, os
sys.path.insert(0, os.path.dirname('$MCP_SERVER'))
exec(open('$MCP_SERVER').read().split('asyncio.run')[0])
print('   ✅ MCP 服务器加载成功')
" 2>/dev/null; then
    :
else
    echo "   ⚠️  无法验证服务器，但可能仍然可用"
fi

# 5. 配置 AI Assistant
echo "📦 配置 AI Assistant..."
cat > "$AI_SETTINGS" << EOF
{
  "outputStyle": "default",
  "language": "chinese",
  "skipAutoPermissionPrompt": true,
  "permissions": {
    "defaultMode": "bypassPermissions"
  },
  "mcpServers": {
    "claude-tools": {
      "command": "python3",
      "args": ["${MCP_SERVER}"]
    }
  }
}
EOF
echo "   ✅ AI Assistant 设置已更新: $AI_SETTINGS"

# 6. 配置环境变量
echo "📦 配置环境变量..."
echo ""
echo "   请将以下内容添加到 ~/.zshrc："
echo ""
echo "   # 百炼 PRO + MCP 配置"
echo "   export LLM_BASE_URL=http://localhost:8080"
echo "   export LLM_MODEL=qwen3.6-plus"
echo "   export DASHSCOPE_API_KEY=sk-8ab52e8a07e940bb8ac87d381dc3dd49"
echo "   export DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1"
echo "   export DASHSCOPE_TARGET_MODEL=qwen3.6-plus"
echo ""
echo "   然后运行: source ~/.zshrc"
echo ""

# 7. 启动适配器
echo "📦 检查 DashScope 适配器..."
if lsof -ti:8080 &>/dev/null; then
    echo "   ✅ 适配器已在运行 (端口 8080)"
else
    echo "   ⚠️  适配器未运行，请执行:"
    echo "      cd $SCRIPT_DIR && nohup python3 dashscope-adapter.py > /tmp/dashscope-adapter.log 2>&1 &"
fi

echo ""
echo "=========================================="
echo "  ✅ 安装完成！"
echo "=========================================="
echo ""
echo "📋 下一步："
echo "  1. 添加环境变量到 ~/.zshrc"
echo "  2. source ~/.zshrc"
echo "  3. 启动适配器（如果未运行）"
echo "  4. claude"
echo ""