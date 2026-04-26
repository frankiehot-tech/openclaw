#!/bin/bash

# AI Assistant 环境初始化脚本
# 输出当前环境中的相关变量，避免再注入历史硬编码值。

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
SECRET_LOADER="$HOME/.config/secret-env/load-keychain-secrets.sh"

show_help() {
    cat << 'EOF'
AI Assistant 环境初始化脚本

用法:
  ./init-claude-env.sh [选项]

选项:
  -e, --export    输出 export 命令，可用于在当前 shell 中恢复 AI 相关环境变量
  -h, --help      显示帮助

示例:
  eval "$(./init-claude-env.sh --export)"
EOF
    exit 0
}

emit_export() {
    printf 'export %s=%q\n' "$1" "$2"
}

case "${1:-}" in
    -h|--help)
        show_help
        ;;
    -e|--export)
        echo "[ -f \"$SECRET_LOADER\" ] && source \"$SECRET_LOADER\""
        emit_export GITHUB_USERNAME "${GITHUB_USERNAME:-frankiehot-tech}"
        emit_export GITHUB_EMAIL "${GITHUB_EMAIL:-frankiehot@hotmail.com}"
        emit_export AI_AUTOCOMPACT_PCT_OVERRIDE "${AI_AUTOCOMPACT_PCT_OVERRIDE:-60}"
        emit_export AI_CODE_AUTO_COMPACT_WINDOW "${AI_CODE_AUTO_COMPACT_WINDOW:-120000}"
        emit_export AI_BARE_MODE "${AI_BARE_MODE:-true}"
        emit_export AI_ENHANCED "${AI_ENHANCED:-true}"
        emit_export AI_CODE_BARE "${AI_CODE_BARE:-1}"
        emit_export AI_CODE_SKIP_KEYCHAIN "${AI_CODE_SKIP_KEYCHAIN:-1}"
        echo 'echo "✅ AI Assistant 环境变量已导出"'
        exit 0
        ;;
esac

echo "🚀 检查 AI Assistant 环境..."
echo "================================"
echo "项目目录: $PROJECT_ROOT"
echo ""

export AI_AUTOCOMPACT_PCT_OVERRIDE="${AI_AUTOCOMPACT_PCT_OVERRIDE:-60}"
export AI_CODE_AUTO_COMPACT_WINDOW="${AI_CODE_AUTO_COMPACT_WINDOW:-120000}"
export AI_BARE_MODE="${AI_BARE_MODE:-true}"
export AI_ENHANCED="${AI_ENHANCED:-true}"
export AI_CODE_BARE="${AI_CODE_BARE:-1}"
export AI_CODE_SKIP_KEYCHAIN="${AI_CODE_SKIP_KEYCHAIN:-1}"

if [ -f "$SECRET_LOADER" ]; then
    # shellcheck source=/dev/null
    source "$SECRET_LOADER"
fi

echo "1. 环境变量状态..."
[ -n "${GITHUB_TOKEN:-}" ] && echo "   ✓ GITHUB_TOKEN 已设置" || echo "   ⚠ GITHUB_TOKEN 未设置"
[ -n "${DASHSCOPE_API_KEY:-}" ] && echo "   ✓ DASHSCOPE_API_KEY 已设置" || echo "   ⚠ DASHSCOPE_API_KEY 未设置"
[ -n "${DEEPSEEK_API_KEY:-}" ] && echo "   ✓ DEEPSEEK_API_KEY 已设置" || echo "   ⚠ DEEPSEEK_API_KEY 未设置"

echo "2. 核心脚本状态..."
for script in \
    claude-config.sh \
    claude-dual-model.sh \
    start-claude.sh \
    claude-qwen-alt.sh \
    dashscope-adapter.py
do
    if [ -f "$PROJECT_ROOT/$script" ]; then
        echo "   ✓ $script"
    else
        echo "   ✗ $script"
    fi
done

echo ""
echo "✅ 检查完成"
echo "如需在当前 shell 导出这些变量，请运行:"
echo "  eval \"\$($PROJECT_ROOT/init-claude-env.sh --export)\""
