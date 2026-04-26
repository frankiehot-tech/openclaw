#!/bin/bash
# =============================================================================
# AI 配置管理器 - 统一管理 Claude Code AI 配置
# 用法: bash scripts/ai-config-manager.sh <command> [options]
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="$PROJECT_DIR/config/ai-config"
PROFILES_DIR="$CONFIG_DIR/profiles"
CLAUDE_SETTINGS="$HOME/.claude/settings.local.json"
CLAUDE_SETTINGS_GLOBAL="$HOME/.claude/settings.json"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------
pass() { echo -e "${GREEN}✅ $1${NC}"; }
fail() { echo -e "${RED}❌ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
info() { echo -e "${BLUE}ℹ️  $1${NC}"; }

# ---------------------------------------------------------------------------
# 加载密钥
# ---------------------------------------------------------------------------
load_secrets() {
    if [ -f "$HOME/.config/secret-env/load-keychain-secrets.sh" ]; then
        source "$HOME/.config/secret-env/load-keychain-secrets.sh"
    fi
}

# ---------------------------------------------------------------------------
# 列出可用配置档案
# ---------------------------------------------------------------------------
cmd_list() {
    echo -e "${BOLD}${BLUE}━━━ 可用配置档案 ━━━${NC}"
    echo ""

    for profile_file in "$PROFILES_DIR"/*.yaml; do
        local name
        name=$(basename "$profile_file" .yaml)
        local profile_name
        profile_name=$(python3 -c "
import yaml, sys
try:
    with open('$profile_file') as f:
        d = yaml.safe_load(f)
    print(d.get('profile', {}).get('name', '$name'))
except:
    print('$name')
" 2>/dev/null || echo "$name")

        local description
        description=$(python3 -c "
import yaml
try:
    with open('$profile_file') as f:
        d = yaml.safe_load(f)
    print(d.get('profile', {}).get('description', ''))
except:
    print('')
" 2>/dev/null || echo "")

        local is_active="  "
        if [ -f "$CLAUDE_SETTINGS" ]; then
            local current_model
            current_model=$(python3 -c "
import json
try:
    with open('$CLAUDE_SETTINGS') as f:
        d = json.load(f)
    print(d.get('anthropic', {}).get('model', '') or d.get('env', {}).get('ANTHROPIC_MODEL', ''))
except:
    print('')
" 2>/dev/null || echo "")

            local primary_model
            primary_model=$(python3 -c "
import yaml
try:
    with open('$profile_file') as f:
        d = yaml.safe_load(f)
    print(d.get('primary_model', ''))
except:
    print('')
" 2>/dev/null || echo "")

            if [ "$current_model" = "$primary_model" ]; then
                is_active="${GREEN}●${NC} "
            fi
        fi

        echo -e "  ${is_active}${BOLD}$name${NC}"
        echo -e "     名称: $profile_name"
        [ -n "$description" ] && echo -e "     描述: $description"
        echo ""
    done
}

# ---------------------------------------------------------------------------
# 激活配置档案
# ---------------------------------------------------------------------------
cmd_activate() {
    local profile="${1:-}"
    if [ -z "$profile" ]; then
        echo -e "${RED}用法: $0 activate <profile_name>${NC}"
        echo ""
        echo "可用配置:"
        for f in "$PROFILES_DIR"/*.yaml; do
            basename "$f" .yaml
        done
        exit 1
    fi

    local profile_file="$PROFILES_DIR/${profile}.yaml"
    if [ ! -f "$profile_file" ]; then
        fail "配置档案不存在: $profile"
        exit 1
    fi

    echo -e "${BOLD}${BLUE}━━━ 激活配置: $profile ━━━${NC}"
    echo ""

    # 加载密钥
    load_secrets

    # 生成 settings.local.json
    echo "生成 Claude Code 配置..."
    python3 -c "
import yaml, json, os, sys

profile_file = '$profile_file'
output_file = '$CLAUDE_SETTINGS'

with open(profile_file) as f:
    config = yaml.safe_load(f)

# 提取 claude_settings 模板
claude_settings = config.get('claude_settings', {})

# 替换环境变量
def resolve_env_vars(obj):
    if isinstance(obj, dict):
        return {k: resolve_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [resolve_env_vars(v) for v in obj]
    elif isinstance(obj, str) and obj.startswith('\${') and obj.endswith('}'):
        env_var = obj[2:-1]
        return os.environ.get(env_var, '')
    return obj

claude_settings = resolve_env_vars(claude_settings)

# 写入文件
os.makedirs(os.path.dirname(output_file), exist_ok=True)
with open(output_file, 'w') as f:
    json.dump(claude_settings, f, indent=2, ensure_ascii=False)

print(f'✅ 配置已写入: {output_file}')

# 打印关键信息
profile_info = config.get('profile', {})
print(f'   名称: {profile_info.get(\"name\", \"\")}')
print(f'   主模型: {config.get(\"primary_model\", \"\")}')
print(f'   降级链: {\" -> \".join(config.get(\"fallback_chain\", []))}')
" 2>/dev/null || {
        fail "配置生成失败，请检查 YAML 语法"
        exit 1
    }

    echo ""

    # 启动适配器（如果需要）
    local use_adapter
    use_adapter=$(python3 -c "
import yaml
with open('$profile_file') as f:
    d = yaml.safe_load(f)
print(d.get('api', {}).get('use_adapter', False))
" 2>/dev/null || echo "false")

    if [ "$use_adapter" = "True" ]; then
        info "检查 DashScope 适配器..."
        if ! curl -s --connect-timeout 3 http://127.0.0.1:8080/health > /dev/null 2>&1; then
            warn "适配器未运行，正在启动..."
            cd "$PROJECT_DIR" && nohup python3 dashscope-adapter.py > /tmp/dashscope-adapter.log 2>&1 &
            sleep 2
            if curl -s --connect-timeout 3 http://127.0.0.1:8080/health > /dev/null 2>&1; then
                pass "适配器已启动"
            else
                fail "适配器启动失败"
            fi
        else
            pass "适配器已运行"
        fi
    fi

    # 显示当前配置
    echo ""
    info "当前 Claude Code 配置:"
    if [ -f "$CLAUDE_SETTINGS" ]; then
        python3 -c "
import json
with open('$CLAUDE_SETTINGS') as f:
    d = json.load(f)
base = d.get('anthropic', {}).get('baseUrl', '') or d.get('env', {}).get('ANTHROPIC_BASE_URL', '')
model = d.get('anthropic', {}).get('model', '') or d.get('env', {}).get('ANTHROPIC_MODEL', '')
print(f'  baseUrl: {base}')
print(f'  model:   {model}')
" 2>/dev/null
    fi

    echo ""
    pass "配置 $profile 已激活！"
    echo ""
    info "重启 Claude Code 使配置生效"
}

# ---------------------------------------------------------------------------
# 诊断当前配置
# ---------------------------------------------------------------------------
cmd_diagnose() {
    echo -e "${BOLD}${BLUE}━━━ 配置诊断 ━━━${NC}"
    echo ""

    load_secrets

    # 1. 检查配置文件
    section "1. Claude Code 配置"
    if [ -f "$CLAUDE_SETTINGS" ]; then
        pass "配置文件存在: $CLAUDE_SETTINGS"
        python3 -c "
import json
with open('$CLAUDE_SETTINGS') as f:
    d = json.load(f)
base = d.get('anthropic', {}).get('baseUrl', '') or d.get('env', {}).get('ANTHROPIC_BASE_URL', '')
model = d.get('anthropic', {}).get('model', '') or d.get('env', {}).get('ANTHROPIC_MODEL', '')
key = d.get('anthropic', {}).get('apiKey', '') or d.get('env', {}).get('ANTHROPIC_AUTH_TOKEN', '')
print(f'  baseUrl: {base}')
print(f'  model:   {model}')
if key:
    masked = key[:8] + '...' + key[-4:] if len(key) > 12 else '***'
    print(f'  apiKey:  {masked}')
else:
    print('  apiKey:  (未设置)')
" 2>/dev/null
    else
        fail "配置文件不存在: $CLAUDE_SETTINGS"
    fi

    # 2. 检查 API Keys
    section "2. API Keys"
    for key_name in DASHSCOPE_API_KEY DEEPSEEK_API_KEY ANTHROPIC_API_KEY; do
        local key_value="${!key_name:-}"
        if [ -n "$key_value" ]; then
            local masked="${key_value:0:8}...${key_value: -4}"
            pass "$key_name: $masked"
        else
            warn "$key_name: 未设置"
        fi
    done

    # 3. 检查适配器
    section "3. DashScope 适配器"
    if curl -s --connect-timeout 3 http://127.0.0.1:8080/health > /dev/null 2>&1; then
        pass "适配器运行正常"
        curl -s http://127.0.0.1:8080/health | python3 -m json.tool 2>/dev/null | sed 's/^/  /'
    else
        fail "适配器未运行"
        info "启动: python3 $PROJECT_DIR/dashscope-adapter.py &"
    fi

    # 4. 检查模型列表
    section "4. 可用模型"
    local adapter_running=false
    if curl -s --connect-timeout 3 http://127.0.0.1:8080/health > /dev/null 2>&1; then
        adapter_running=true
        curl -s http://127.0.0.1:8080/v1/models 2>/dev/null | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    models = [m.get('id', m.get('name', '?')) for m in d.get('models', [])]
    for m in models:
        print(f'  ✅ {m}')
except:
    print('  (无法获取模型列表)')
" 2>/dev/null || echo "  (无法获取模型列表)"
    else
        warn "适配器未运行，无法获取模型列表"
    fi

    echo ""
    pass "诊断完成"
}

# ---------------------------------------------------------------------------
# 帮助
# ---------------------------------------------------------------------------
cmd_help() {
    echo -e "${BOLD}AI 配置管理器${NC}"
    echo ""
    echo "用法: $0 <command> [options]"
    echo ""
    echo "命令:"
    echo "  list                  列出所有可用配置档案"
    echo "  activate <profile>    激活指定配置档案"
    echo "  diagnose              诊断当前配置状态"
    echo "  validate [model]      验证模型配置"
    echo "  help                  显示帮助"
    echo ""
    echo "示例:"
    echo "  $0 list                           # 列出所有配置"
    echo "  $0 activate bailian-pro           # 激活百炼 Pro 配置"
    echo "  $0 activate deepseek              # 激活 DeepSeek 配置"
    echo "  $0 diagnose                       # 诊断当前配置"
    echo "  $0 validate qwen-max              # 验证单个模型"
    echo "  $0 validate                       # 全量验证所有模型"
}

# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
section() { echo -e "\n${CYAN}${BOLD}━━━ $1 ━━━${NC}"; }

COMMAND="${1:-help}"
shift || true

case "$COMMAND" in
    list)       cmd_list ;;
    activate)   cmd_activate "$@" ;;
    diagnose)   cmd_diagnose ;;
    validate)
        if [ $# -gt 0 ]; then
            bash "$SCRIPT_DIR/ai-validate-model.sh" "$@"
        else
            bash "$SCRIPT_DIR/ai-validate-all.sh" all
        fi
        ;;
    help|*)     cmd_help ;;
esac