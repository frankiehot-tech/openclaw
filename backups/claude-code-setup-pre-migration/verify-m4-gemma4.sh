#!/bin/bash

echo "🔍 M4 + Gemma 4 + Claude Code 验证脚本"
echo "=========================================="
echo ""

PASS=0
FAIL=0
WARN=0

check_pass() {
    echo -e "✅ $1"
    PASS=$((PASS + 1))
}

check_fail() {
    echo -e "❌ $1"
    FAIL=$((FAIL + 1))
}

check_warn() {
    echo -e "⚠️  $1"
    WARN=$((WARN + 1))
}

# 1. 检查 Ollama
if command -v ollama &> /dev/null; then
    OLLAMA_VERSION=$(ollama --version 2>&1 | head -1)
    check_pass "Ollama: $OLLAMA_VERSION"
else
    check_fail "Ollama 未安装"
    echo "   安装命令: curl -fsSL https://ollama.com/install.sh | sh"
fi
echo ""

# 2. 检查模型
if ollama list | grep -q "gemma4-claude"; then
    MODEL_SIZE=$(ollama list | grep "gemma4-claude" | awk '{print $4, $5}')
    check_pass "模型 gemma4-claude 已就绪 ($MODEL_SIZE)"
else
    check_fail "gemma4-claude 未创建"
    echo "   请运行: ollama create gemma4-claude -f ~/Modelfile-gemma4-claude"
fi

if ollama list | grep -q "gemma4:e4b"; then
    check_pass "基础模型 gemma4:e4b 已下载"
else
    check_warn "基础模型 gemma4:e4b 未找到"
fi
echo ""

# 3. 检查 Ollama 服务
if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    check_pass "Ollama 服务运行中 (http://localhost:11434)"
else
    check_fail "Ollama 服务未运行"
    echo "   启动命令: brew services start ollama"
fi
echo ""

# 4. 检查环境变量
if [ "$ANTHROPIC_BASE_URL" = "http://localhost:11434" ]; then
    check_pass "ANTHROPIC_BASE_URL 配置正确"
else
    check_warn "ANTHROPIC_BASE_URL 未设置或配置错误"
    echo "   使用别名 claude-local 自动配置"
fi

if [ -z "$ANTHROPIC_API_KEY" ] 2>/dev/null || [ "$ANTHROPIC_API_KEY" = "" ]; then
    check_pass "ANTHROPIC_API_KEY 为空（本地模式正确）"
else
    check_warn "ANTHROPIC_API_KEY 非空，本地模式应设为空字符串"
fi
echo ""

# 5. 检查 claude-dual-model.sh
if [ -x "$HOME/claude-code-setup/claude-dual-model.sh" ]; then
    check_pass "claude-dual-model.sh 已安装且可执行"
else
    check_fail "claude-dual-model.sh 未找到或无执行权限"
fi
echo ""

# 6. 检查 .zshrc 别名配置
if grep -q "claude-local" ~/.zshrc 2>/dev/null; then
    check_pass "~/.zshrc Ollama 别名已配置"
else
    check_warn "~/.zshrc 中未找到 Ollama 别名"
fi
echo ""

# 7. 测试推理（仅当 Ollama 服务运行时）
if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "🧪 发送测试请求..."
    RESPONSE=$(curl -s -m 30 http://localhost:11434/api/generate -d '{
      "model": "gemma4-claude",
      "prompt": "Say ready and nothing else.",
      "stream": false
    }')
    if echo "$RESPONSE" | grep -q "ready"; then
        check_pass "模型响应正常"
    else
        check_fail "模型测试失败"
        echo "   响应: $RESPONSE"
    fi
else
    check_warn "跳过推理测试（Ollama 服务未运行）"
fi
echo ""

# 8. 检查硬件（M4）
CHIP=$(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo "Unknown")
if echo "$CHIP" | grep -qi "M4\|Apple"; then
    MEMORY=$(sysctl -n hw.memsize 2>/dev/null | awk '{print $1/1073741824 "GB"}')
    check_pass "Apple Silicon 芯片，内存: ${MEMORY}"
else
    check_warn "非 Apple Silicon 或无法检测芯片: $CHIP"
fi
echo ""

# 总结
echo "=========================================="
echo "📊 检查结果汇总"
echo "=========================================="
echo -e "✅ 通过: $PASS"
echo -e "❌ 失败: $FAIL"
echo -e "⚠️  警告: $WARN"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "🎉 全部通过！运行以下命令启动："
    echo ""
    echo "   claude-local    # Ollama 本地模式（推荐）"
    echo "   claude-big      # Ollama 26B 模式（复杂任务）"
    echo "   claude          # 默认云端模式"
    echo ""
else
    echo -e "🔧 请先修复上述失败项"
fi