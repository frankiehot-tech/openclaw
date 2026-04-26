#!/bin/bash
#
# Claude Code + 百炼 Pro 诊断和修复脚本 v3
# 诊断无输出问题，测试各模型可用性
#

set -e

API_KEY="${DASHSCOPE_API_KEY:-sk-921103e3b7bb4d4bb1d97308c43c71fc}"
BASE_URL="http://localhost:8080"
DASHSCOPE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

pass() { echo -e "  ${GREEN}✅ $1${NC}"; }
fail() { echo -e "  ${RED}❌ $1${NC}"; }
warn() { echo -e "  ${YELLOW}⚠️  $1${NC}"; }
info() { echo -e "  ${BLUE}ℹ️  $1${NC}"; }

echo "=============================================="
echo "  Claude Code + 百炼 Pro 诊断工具 v3"
echo "=============================================="
echo ""

ISSUES=0

# 1. 检查适配器状态
echo "📊 1. 检查适配器状态..."
HEALTH=$(curl -s --connect-timeout 5 "$BASE_URL/health" 2>/dev/null)
if [ $? -eq 0 ] && [ -n "$HEALTH" ]; then
    pass "适配器运行正常"
    VERSION=$(echo "$HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('version','?'))" 2>/dev/null)
    MODEL=$(echo "$HEALTH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('default_model') or d.get('model','?'))" 2>/dev/null)
    info "版本: $VERSION, 默认模型: $MODEL"
else
    fail "适配器未运行"
    echo "   修复: cd /Users/frankie/claude-code-setup && nohup python3 dashscope-adapter.py > /tmp/dashscope-adapter-v3.log 2>&1 &"
    ISSUES=$((ISSUES + 1))
fi
echo ""

# 2. 检查 API Key
echo "📊 2. 检查 API Key..."
if [ -n "$API_KEY" ] && [ "$API_KEY" != "sk-921103e3b7bb4d4bb1d97308c43c71fc" ]; then
    pass "API Key 已配置: ${API_KEY:0:8}..."
else
    warn "使用默认 API Key"
fi
echo ""

# 3. 测试直连百炼 API（验证 Key 有效）
echo "📊 3. 测试直连百炼 API..."
RESPONSE=$(curl -s --connect-timeout 10 "$DASHSCOPE_URL/chat/completions" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"model":"qwen-max","messages":[{"role":"user","content":"OK"}],"max_tokens":5}' 2>/dev/null)

if echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'choices' in d" 2>/dev/null; then
    pass "百炼 API 连接正常"
    TOKENS=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); u=d.get('usage',{}); print(f'输入:{u.get(\"prompt_tokens\",0)}, 输出:{u.get(\"completion_tokens\",0)}')" 2>/dev/null)
    info "Token 使用: $TOKENS"
else
    fail "百炼 API 连接失败"
    info "响应: $(echo "$RESPONSE" | head -c 200)"
    ISSUES=$((ISSUES + 1))
fi
echo ""

# 4. 测试适配器非流式
echo "📊 4. 测试适配器非流式 (qwen-max)..."
RESPONSE=$(curl -s --connect-timeout 5 "$BASE_URL/v1/messages" \
    -X POST -H "Content-Type: application/json" -H "x-api-key: $API_KEY" \
    -d '{"model":"qwen-max","messages":[{"role":"user","content":"OK"}],"max_tokens":5,"stream":false}' 2>/dev/null)

if echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('content')" 2>/dev/null; then
    pass "非流式响应正常"
    MODEL=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('model','?'))" 2>/dev/null)
    info "返回模型: $MODEL"
else
    fail "非流式响应异常"
    info "响应: $(echo "$RESPONSE" | head -c 200)"
    ISSUES=$((ISSUES + 1))
fi
echo ""

# 5. 测试适配器流式（关键测试）
echo "📊 5. 测试适配器流式 (qwen-max)..."
# 使用 curl 输出到文件，避免 BrokenPipeError
STREAM_FILE=$(mktemp /tmp/stream-test-XXXXXX.txt)
curl -s --connect-timeout 5 --max-time 15 "$BASE_URL/v1/messages" \
    -X POST -H "Content-Type: application/json" -H "x-api-key: $API_KEY" \
    -d '{"model":"qwen-max","messages":[{"role":"user","content":"OK"}],"max_tokens":5,"stream":true}' \
    > "$STREAM_FILE" 2>/dev/null &
STREAM_PID=$!
sleep 8
kill $STREAM_PID 2>/dev/null || true

if [ -f "$STREAM_FILE" ] && grep -q "content_block_delta" "$STREAM_FILE" 2>/dev/null; then
    pass "流式响应正常"
else
    fail "流式响应异常"
    ISSUES=$((ISSUES + 1))
fi
rm -f "$STREAM_FILE"
echo ""

# 6. 测试各模型可用性
echo "📊 6. 测试百炼 Pro 可用模型..."
MODELS=("qwen-max" "qwen-plus" "qwen-turbo" "qwen-coder-plus" "qwen-long")
for MODEL in "${MODELS[@]}"; do
    RESP=$(curl -s --connect-timeout 5 --max-time 30 "$BASE_URL/v1/messages" \
        -X POST -H "Content-Type: application/json" -H "x-api-key: $API_KEY" \
        -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"OK\"}],\"max_tokens\":5,\"stream\":false}" 2>/dev/null)
    
    if echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('content')" 2>/dev/null; then
        TOKENS=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); u=d.get('usage',{}); print(u.get('output_tokens',0))" 2>/dev/null)
        pass "$MODEL (输出 $TOKENS tokens)"
    else
        fail "$MODEL 不可用"
    fi
done
echo ""

# 7. 检查 Claude Code 配置
echo "📊 7. 检查 Claude Code 配置..."
SETTINGS_FILE="$HOME/.claude/settings.local.json"
if [ -f "$SETTINGS_FILE" ]; then
    pass "配置文件存在: $SETTINGS_FILE"
    BASE=$(python3 -c "import json; f=open('$SETTINGS_FILE'); d=json.load(f); print(d.get('anthropic',{}).get('baseUrl') or d.get('env',{}).get('ANTHROPIC_BASE_URL','?'))" 2>/dev/null)
    MODEL=$(python3 -c "import json; f=open('$SETTINGS_FILE'); d=json.load(f); print(d.get('anthropic',{}).get('model') or d.get('env',{}).get('ANTHROPIC_MODEL','?'))" 2>/dev/null)
    info "baseUrl: $BASE"
    info "model: $MODEL"
    
    if [ "$BASE" = "http://localhost:8080" ]; then
        pass "配置指向适配器"
    else
        warn "配置未指向适配器: $BASE"
    fi
else
    fail "配置文件不存在: $SETTINGS_FILE"
    ISSUES=$((ISSUES + 1))
fi
echo ""

# 8. 检查 MCP Server
echo "📊 8. 检查 MCP Server..."
MCP_SCRIPT="/Users/frankie/claude-code-setup/stage1/mcp-servers/claude-tools-server.py"
if [ -f "$MCP_SCRIPT" ]; then
    pass "MCP Server 脚本存在"
else
    warn "MCP Server 脚本不存在: $MCP_SCRIPT"
fi
echo ""

# 总结
echo "=============================================="
if [ $ISSUES -eq 0 ]; then
    echo -e "${GREEN}✅ 所有检查通过！Claude Code 应该可以正常工作${NC}"
else
    echo -e "${RED}⚠️  发现 $ISSUES 个问题${NC}"
    echo ""
    echo "建议修复步骤："
    echo "  1. 重启适配器: bash restart-adapter.sh"
    echo "  2. 检查 API Key 是否有效"
    echo "  3. 检查 Claude Code 配置: cat $SETTINGS_FILE"
    echo "  4. 查看适配器日志: tail -f /tmp/dashscope-adapter-v3.log"
fi
echo "=============================================="